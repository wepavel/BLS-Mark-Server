import time
from uuid import UUID

from sqlmodel import Field

from app.db.base_class import Base

# NEW_UUID = lambda: str(uuid.uuid4())


# class DMCode(Base, table=True):
#     id: UUID | None = Field(primary_key=True, index=True, unique=True, default=ULID.from_timestamp(time.time()))
#     gtin: str | None = Field(unique=True, index=True, nullable=False, foreign_key='gtin.id')
#     login: str | None = Field(unique=True, index=True, nullable=False)
#     country_id: int | None = Field(default=1, foreign_key='country.id')


import re
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class Country(str, Enum):
    RUSSIA = "Russia"
    BELARUS = "Belarus"
    KAZAKHSTAN = "Kazakhstan"
    ARMENIA = "Armenia"
    KYRGYZSTAN = "Kyrgyzstan"


class DataMatrixAttrs(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    gtin: str = Field(default="", max_length=14)
    serial_number: str = Field(default="", max_length=5)
    country_code: int = Field(default=0)
    country: Country = Field(default=Country.RUSSIA)
    verification_key: str = Field(default="", max_length=4)
    verification_key_value: str = Field(default="", max_length=44)
    is_long_format: bool = Field(default=False)


def parse_data_matrix(data_matrix: str) -> DataMatrixAttrs:
    result = DataMatrixAttrs()

    clean_code = normalize_gs(data_matrix)
    groups = clean_code.split("<GS>")
    print(groups)

    for group in groups:
        if group.startswith("01"):
            result.gtin = group[2:16]
            if len(group) > 16:
                remainder = group[16:]
                if remainder.startswith("21"):
                    country_code = int(remainder[2:3])
                    result.country_code = country_code
                    result.country = Country(f"{Country(country_code).name.capitalize()}")
                    result.serial_number = remainder[3:8]
        elif group.startswith("91"):
            result.verification_key = group[2:6]
            result.is_long_format = True
        elif group.startswith("92"):
            result.verification_key_value = group[2:]
            result.is_long_format = True
        elif group.startswith("93"):
            result.verification_key = group[2:6]
            result.is_long_format = False

    return result

def validate_data_matrix(data_matrix: str) -> tuple[bool, Optional[DataMatrixAttrs]]:
    normalized_code = normalize_gs(data_matrix)

    long_format_regex = r"^01\d{14}21[0-5].{5,12}<GS>91.{4}<GS>92.{44}$"
    short_format_regex = r"^01\d{14}21[0-5].{5,12}<GS>93.{4}$"

    if re.match(long_format_regex, normalized_code) or re.match(short_format_regex, normalized_code):
        attrs = parse_data_matrix(normalized_code)

        if len(attrs.gtin) != 14 or not attrs.gtin.isdigit():
            return False, None

        if len(attrs.serial_number) != 5:
            return False, None

        if attrs.country_code < 1 or attrs.country_code > 5:
            return False, None

        if attrs.is_long_format:
            if len(attrs.verification_key) != 4:
                return False, None
            if len(attrs.verification_key_value) != 44:
                return False, None
        else:
            if len(attrs.verification_key) != 4:
                return False, None
            if attrs.verification_key_value != "-":
                return False, None

        return True, attrs

    return False, None

def prepare_data_matrix(code: str) -> str:
    return chr(29) + code.replace("<GS>", chr(29))

def normalize_gs(input_str: str) -> str:
    if input_str.startswith(chr(232)) or input_str.startswith(chr(29)):
        input_str = input_str[1:]
    return input_str.replace(chr(29), "<GS>")