# import subprocess
# import hashlib
# import winreg
#
# class LicenseManager:
#     _default_salt = 'KIPiA_2025'
#     def __init__(self):
#         pass
#
#     # Функция для получения серийного номера материнской платы
#     @staticmethod
#     def get_motherboard_serial():
#         try:
#             process = subprocess.run(
#                 ["wmic", "baseboard", "get", "serialnumber"],
#                 capture_output=True, text=True, check=True
#             )
#             lines = list(filter(None, process.stdout.splitlines()))
#             if len(lines) >= 2:
#                 serial = lines[1].strip()
#                 if serial and serial != "To be filled by O.E.M.":
#                     return serial
#         except Exception:
#             pass
#
#         # Если серийный номер недоступен, используем UUID системы
#         try:
#             process = subprocess.run(
#                 ["wmic", "csproduct", "get", "uuid"],
#                 capture_output=True, text=True, check=True
#             )
#             lines = process.stdout.splitlines()
#             if len(lines) >= 2:
#                 return lines[1].strip()
#         except Exception:
#             pass
#
#         return ""
#
#     # Функция для создания аугментированного хэша
#     @staticmethod
#     def create_augmented_hash(input_data, salt):
#         augmented_input = input_data + salt
#         return hashlib.sha256(augmented_input.encode()).hexdigest()
#
#     # Функция для записи хеша в реестр
#     @staticmethod
#     def write_hash_to_registry(hash_value):
#         key_path = r"SOFTWARE\BLSEngineering\BLSMark"
#         try:
#             with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
#                 winreg.SetValueEx(key, "LicenseHash", 0, winreg.REG_SZ, hash_value)
#         except PermissionError:
#             print("Недостаточно прав для записи в реестр.")
#
#     # Функция для чтения хеша из реестра
#     @staticmethod
#     def read_hash_from_registry():
#         key_path = r"SOFTWARE\BLSEngineering\BLSMark"
#         try:
#             with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
#                 value, _ = winreg.QueryValueEx(key, "LicenseHash")
#                 return value
#         except FileNotFoundError:
#             return ""
#
#     # Проверка лицензии
#     def check_license(self, salt):
#         serial = self.get_motherboard_serial()
#         current_hash = self.create_augmented_hash(serial, salt)
#         stored_hash = self.read_hash_from_registry()
#         return current_hash == stored_hash
#
#     # Удаление ключа или значения из реестра
#     @staticmethod
#     def remove_from_registry(key, value_name=None):
#         key_path = r"SOFTWARE\BLSEngineering\BLSMark"
#         try:
#             with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS) as reg_key:
#                 if value_name:
#                     winreg.DeleteValue(reg_key, value_name)
#                 else:
#                     winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
#             return True
#         except FileNotFoundError:
#             return False
#         except PermissionError:
#             print("Недостаточно прав для удаления из реестра.")
#             return False

import subprocess
import hashlib
import winreg
from app.core.logging import logger

class LicenseManager:
    _default_salt = 'KIPiA_2025'

    def __init__(self):
        pass

    # Функция для получения серийного номера материнской платы
    @staticmethod
    def get_motherboard_serial():
        def get_command_output(command):
            try:
                process = subprocess.run(
                    command,
                    capture_output=True, text=True, check=True
                )
                lines = list(filter(None, process.stdout.splitlines()))
                return lines[1].strip() if len(lines) >= 2 else None
            except Exception:
                return None

        # Пробуем получить серийный номер
        serial = get_command_output(["wmic", "baseboard", "get", "serialnumber"])
        if serial and serial != "To be filled by O.E.M.":
            return serial

        # Если серийный номер недоступен, пробуем получить UUID
        uuid = get_command_output(["wmic", "csproduct", "get", "uuid"])
        return uuid or ""

    # Функция для создания аугментированного хэша
    @staticmethod
    def create_augmented_hash(input_data, salt):
        return hashlib.sha256((input_data + salt).encode()).hexdigest()

    # Универсальная функция для записи хэша в реестр (обе ветки)
    @staticmethod
    def write_hash_to_registry(hash_value):
        def write_to_registry(hive, path):
            try:
                with winreg.CreateKey(hive, path) as key:
                    winreg.SetValueEx(key, "LicenseHash", 0, winreg.REG_SZ, hash_value)
            except PermissionError:
                print(f"Insufficient rights to work with the registry: {path}")

        write_to_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BLSEngineering\BLSMark")
        write_to_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\BLSEngineering\BLSMark")

    # Универсальная функция для чтения хэша из реестра с проверкой валидности
    @staticmethod
    def read_hash_from_registry_with_validation(serial, salt):
        def read_from_registry(hive, path):
            try:
                with winreg.OpenKey(hive, path) as key:
                    value, _ = winreg.QueryValueEx(key, "LicenseHash")
                    return value
            except FileNotFoundError:
                return None

        def validate_hash(hash_value):
            # Проверяем, соответствует ли хэш ожидаемому значению
            expected_hash = LicenseManager.create_augmented_hash(serial, salt)
            return hash_value == expected_hash

        # Сначала читаем из 64-битной ветки
        hash64 = read_from_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BLSEngineering\BLSMark")
        if hash64 and validate_hash(hash64):
            return hash64  # Если хэш в 64-битной ветке корректен, возвращаем его

        # Затем читаем из 32-битной ветки
        hash32 = read_from_registry(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\BLSEngineering\BLSMark")
        if hash32 and validate_hash(hash32):
            return hash32  # Если хэш в 32-битной ветке корректен, возвращаем его

        return None  # Возвращаем None, если корректный хэш не найден

    # Универсальная функция для удаления ключа или значения из реестра (обе ветки)
    @staticmethod
    def remove_from_registry(value_name=None):
        def remove_from_registry_path(hive, path):
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                    if value_name:
                        winreg.DeleteValue(reg_key, value_name)
                    else:
                        winreg.DeleteKey(hive, path)
                return True
            except FileNotFoundError:
                return False
            except PermissionError:
                logger.warning(f"Insufficient rights to work with the registry: {path}")
                return False

        result64 = remove_from_registry_path(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BLSEngineering\BLSMark")
        result32 = remove_from_registry_path(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\BLSEngineering\BLSMark")
        return result64 or result32

    # Проверка лицензии
    def check_license(self, salt = _default_salt):
        serial = self.get_motherboard_serial()
        current_hash = self.create_augmented_hash(serial, salt)
        stored_hash = self.read_hash_from_registry_with_validation(serial, salt)
        return current_hash == stored_hash

