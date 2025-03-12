# from datetime import datetime
# from app.models import DataMatrixCode, CountryEnum, Country, DataMatrixCodePublic
# import re
import logging

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

from ping3 import ping
from datetime import datetime, timezone
import pytz
import asyncio

async def ping_device(ip_address: str) -> bool:
    try:
        response_time = await asyncio.to_thread(ping, ip_address, timeout=1)
        # print(f'Address: {ip_address} ping time: {response_time}')

        return response_time is not None and response_time is not False

    except Exception as e:
        logging.warning(f"Error pinging {ip_address}: {e}")
        return False



current_timezone = pytz.timezone('Europe/Moscow')

def timezone_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = current_timezone.localize(dt)
    return dt.astimezone(timezone.utc)
