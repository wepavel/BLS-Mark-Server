from app.db.base_class import Base
from datetime import datetime, timezone
from .country import CountryEnum

from sqlmodel import Field, SQLModel, Column, DateTime
from typing import Optional
import re
from app.core.utils import current_timezone

class DataMatrixCodeBase(SQLModel, table=False):
    dm_code: str

class DataMatrixCodeCreate(DataMatrixCodeBase, table=False):
    pass

class DataMatrixCodeUpdate(DataMatrixCodeBase, table=False):
    entry_time: datetime | None = Field(default=None)
    export_time: datetime | None = Field(default=None)

class DataMatrixCodeDatetime(DataMatrixCodeBase, table=False):
    upload_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entry_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DataMatrixCodePublic(DataMatrixCodeBase, table=False):
    dm_code: str
    gtin: str
    product_name: str
    serial_number: str
    country: str
    is_long_format: bool
    verification_key: str
    verification_key_value: str | None
    upload_time: str
    entry_time: str | None
    export_time: str | None

class DataMatrixCodeProblem(DataMatrixCodeBase, table=False):
    problem: str

class DataMatrixCode(Base, table=True):
    id: int | None = Field(default=None, primary_key=True, index=True)
    dm_code: str = Field(default=None, unique=True, nullable=True)
    gtin: str = Field(index=True, max_length=14, foreign_key="gtin.code")
    serial_number: str = Field(max_length=13)
    country_id: int = Field(foreign_key="country.id")
    verification_key: str = Field(max_length=4)
    verification_key_value: str | None = Field(default=None, max_length=44)
    is_long_format: bool = Field(default=False)
    upload_time: datetime = Field(sa_column=Column(DateTime(timezone=True)), default_factory=lambda: datetime.now(timezone.utc))
    entry_time: datetime | None = Field(sa_column=Column(DateTime(timezone=True)),default=None)
    export_time: datetime | None = Field(sa_column=Column(DateTime(timezone=True)),default=None)


    def to_public_data_matrix_code(self) -> DataMatrixCodePublic:
        def format_time(dt):
            if dt is None:
                return None
            time = dt.astimezone(current_timezone)
            return time.strftime("%Y_%m_%d_%H%M%S")

        return DataMatrixCodePublic(
            dm_code=self.dm_code,
            gtin=self.gtin,
            product_name="Unknown Product",
            serial_number=self.serial_number,
            country=CountryEnum.from_code(
                self.country_id).label if self.country_id is not None else CountryEnum.UNKNOWN.label,
            is_long_format=self.is_long_format,
            verification_key=self.verification_key,
            verification_key_value=self.verification_key_value,
            upload_time=format_time(self.upload_time),
            entry_time=format_time(self.entry_time),
            export_time = format_time(self.export_time),
        )

    @classmethod
    def from_data_matrix_code_create(cls, data: DataMatrixCodeCreate) -> Optional['DataMatrixCode']:
        parsed_data = validate_data_matrix(data.dm_code)
        return parsed_data if parsed_data else None

    @classmethod
    def empty_code(cls) -> Optional['DataMatrixCode']:
        return DataMatrixCode(
            dm_code='',
            gtin='',
            product_name="Unknown Product",
            serial_number='',
            country=0,
            is_long_format=False,
            verification_key='',
            verification_key_value='',
            upload_time=datetime.now(timezone.utc),
            entry_time=None,
            export_time=None,
        )


def parse_data_matrix(data_matrix: str) -> DataMatrixCode:
    clean_code = normalize_gs(data_matrix)
    groups = clean_code.split("<GS>")

    result = DataMatrixCode(
        dm_code=data_matrix,
        upload_time=datetime.now(timezone.utc)
    )

    for group in groups:
        if group.startswith("01"):
            result.gtin = group[2:16]
            if len(group) > 16:
                remainder = group[16:]
                if remainder.startswith("21"):
                    if remainder[2].isdigit():
                        country_id = int(remainder[2])
                        result.country_id = country_id
                        # result.country = CountryEnum.from_code(country_id).label
                        result.serial_number = remainder[3:]
                    else:
                        result.country_id = 0
                        # result.country = CountryEnum.UNKNOWN.label
                        result.serial_number = remainder[2:]
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


def validate_data_matrix(data_matrix: str) -> DataMatrixCode | None:
    normalized_code = normalize_gs(data_matrix)

    long_format_regex = r'^01\d{14}21[0-5].{5,12}<GS>91.{4}<GS>92.{44}$'
    short_format_regex = r'^01\d{14}21[0-5].{5,12}<GS>93.{4}$'
    long_format_regex_no_country = r'^01\d{14}21[A-Za-z].{5,13}<GS>91.{4}<GS>92.{44}$'
    short_format_regex_no_country = r'^01\d{14}21[A-Za-z].{5,13}<GS>93.{4}$'

    if (re.match(long_format_regex, normalized_code) or
            re.match(short_format_regex, normalized_code) or
            re.match(long_format_regex_no_country, normalized_code) or
            re.match(short_format_regex_no_country, normalized_code)):

        attrs = parse_data_matrix(normalized_code)

        if len(attrs.gtin) != 14 or not attrs.gtin.isdigit():
            return None

        if len(attrs.serial_number) < 5 or len(attrs.serial_number) > 13:
            return None

        if attrs.country_id not in CountryEnum.get_all_codes():
            return None

        if attrs.is_long_format:
            if len(attrs.verification_key) != 4:
                return None
            if len(attrs.verification_key_value) != 44:
                return None
        else:
            if len(attrs.verification_key) != 4:
                return None
            if attrs.verification_key_value != "-":
                attrs.verification_key_value = "-"

        return attrs

    return None


def normalize_gs(input_str: str) -> str:
    if input_str.startswith(chr(232)) or input_str.startswith(chr(29)):
        input_str = input_str[1:]
    return input_str.replace(chr(29), "<GS>")

def export_normalize_gs(input_str: str) -> str:
    if input_str.startswith(chr(232)):
        input_str = input_str[1:]
        input_str = chr(29) + input_str
    elif input_str.startswith(chr(29)):
        pass
    else:
        input_str = chr(29) + input_str
    return input_str