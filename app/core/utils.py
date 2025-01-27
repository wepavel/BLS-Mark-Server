from datetime import datetime
from app.models import DataMatrixCode, CountryEnum, Country, DataMatrixCodePublic
import re

# import ulid
#
#
# def generate_id(datetime_flag: bool = False, current_time: datetime = datetime.now()) -> str:
#     if datetime_flag:
#         return current_time.strftime('%y_%m_%d_%H%M_') + ulid.from_timestamp(current_time.timestamp()).randomness().str
#     return ulid.new().str


# def parse_data_matrix(dm_code: str) -> DataMatrixCode:
#     clean_code = normalize_gs(dm_code)
#     groups = clean_code.split("<GS>")
#
#     result = DataMatrixCode(
#         dm_code=dm_code,
#         upload_date=datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
#     )
#
#     for group in groups:
#         if group.startswith("01"):
#             result.gtin = group[2:16]
#             if len(group) > 16:
#                 remainder = group[16:]
#                 if remainder.startswith("21"):
#                     country_id = int(remainder[2:3])
#                     result.country_id = country_id if country_id in CountryEnum.get_all_codes() else CountryEnum.UNKNOWN.code
#                     result.serial_number = remainder[3:8]
#         elif group.startswith("91"):
#             result.verification_key = group[2:6]
#             result.is_long_format = True
#         elif group.startswith("92"):
#             result.verification_key_value = group[2:]
#             result.is_long_format = True
#         elif group.startswith("93"):
#             result.verification_key = group[2:6]
#             result.is_long_format = False
#             result.verification_key_value = None  # Explicitly set to None for short format
#
#     return result
#
#
# def validate_data_matrix(data_matrix: str) -> DataMatrixCode | None:
#     normalized_code = normalize_gs(data_matrix)
#
#     long_format_regex = r'^01\d{14}21[0-5].{5,12}<GS>91.{4}<GS>92.{44}$'
#     short_format_regex = r'^01\d{14}21[0-5].{5,12}<GS>93.{4}$'
#
#     long_format_regex_no_country = r'^01\d{14}21[A-Za-z].{5,13}<GS>91.{4}<GS>92.{44}$'
#     short_format_regex_no_country = r'^01\d{14}21[A-Za-z].{5,13}<GS>93.{4}$'
#
#     if re.match(long_format_regex, normalized_code) or re.match(short_format_regex, normalized_code):
#         dm_code = parse_data_matrix(normalized_code)
#
#         if len(dm_code.gtin) != 14 or not dm_code.gtin.isdigit():
#             return None
#
#         if len(dm_code.serial_number) != 5:
#             return None
#
#         if dm_code.country_id < 0 or dm_code.country_id > 5:
#             return None
#
#         if dm_code.is_long_format:
#             if len(dm_code.verification_key) != 4:
#                 return None
#             if len(dm_code.verification_key_value) != 44:
#                 return None
#         else:
#             if len(dm_code.verification_key) != 4:
#                 return None
#             if dm_code.verification_key_value is not None:
#                 return None
#
#         return dm_code
#     elif re.match(long_format_regex_no_country, normalized_code) or \
#          re.match(short_format_regex_no_country, normalized_code):
#         dm_code = parse_data_matrix(normalized_code)
#
#         if len(dm_code.gtin) != 14 or not dm_code.gtin.isdigit():
#             return None
#
#         if len(dm_code.serial_number) != 5:
#             return None
#
#         if dm_code.is_long_format:
#             if len(dm_code.verification_key) != 4:
#                 return None
#             if len(dm_code.verification_key_value) != 44:
#                 return None
#         else:
#             if len(dm_code.verification_key) != 4:
#                 return None
#             if dm_code.verification_key_value is not None:
#                 return None
#
#         return dm_code
#
#     return None


def parse_data_matrix(data_matrix: str) -> DataMatrixCode:
    clean_code = normalize_gs(data_matrix)
    groups = clean_code.split("<GS>")

    result = DataMatrixCode(
        dm_code=data_matrix,
        upload_date=datetime.utcnow().strftime("%Y_%m_%d_%H%M%S")
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


def to_public_data_matrix_code(dm_code: DataMatrixCode) -> DataMatrixCodePublic:
    return DataMatrixCodePublic(
        dm_code=dm_code.dm_code,
        gtin=dm_code.gtin,
        serial_number=dm_code.serial_number,
        country=CountryEnum.from_code(dm_code.country_id).label if dm_code.country_id is not None else CountryEnum.UNKNOWN.label,
        is_long_format=dm_code.is_long_format,
        verification_key=dm_code.verification_key,
        verification_key_value=dm_code.verification_key_value,
        upload_date=dm_code.upload_date,
        entry_time=dm_code.entry_time
    )
