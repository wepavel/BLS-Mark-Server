import subprocess
import hashlib
import winreg

class LicenseManager:
    _default_salt = 'KIPiA_2025'
    def __init__(self):
        pass

    # Функция для получения серийного номера материнской платы
    @staticmethod
    def get_motherboard_serial():
        try:
            process = subprocess.run(
                ["wmic", "baseboard", "get", "serialnumber"],
                capture_output=True, text=True, check=True
            )
            lines = list(filter(None, process.stdout.splitlines()))
            if len(lines) >= 2:
                serial = lines[1].strip()
                if serial and serial != "To be filled by O.E.M.":
                    return serial
        except Exception:
            pass

        # Если серийный номер недоступен, используем UUID системы
        try:
            process = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True, text=True, check=True
            )
            lines = process.stdout.splitlines()
            if len(lines) >= 2:
                return lines[1].strip()
        except Exception:
            pass

        return ""

    # Функция для создания аугментированного хэша
    @staticmethod
    def create_augmented_hash(input_data, salt):
        augmented_input = input_data + salt
        return hashlib.sha256(augmented_input.encode()).hexdigest()

    # Функция для записи хеша в реестр
    @staticmethod
    def write_hash_to_registry(hash_value):
        key_path = r"SOFTWARE\BLSEngineering\BLSMark"
        try:
            with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                winreg.SetValueEx(key, "LicenseHash", 0, winreg.REG_SZ, hash_value)
        except PermissionError:
            print("Недостаточно прав для записи в реестр.")

    # Функция для чтения хеша из реестра
    @staticmethod
    def read_hash_from_registry():
        key_path = r"SOFTWARE\BLSEngineering\BLSMark"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "LicenseHash")
                return value
        except FileNotFoundError:
            return ""

    # Проверка лицензии
    def check_license(self, salt):
        serial = self.get_motherboard_serial()
        current_hash = self.create_augmented_hash(serial, salt)
        stored_hash = self.read_hash_from_registry()
        return current_hash == stored_hash

    # Удаление ключа или значения из реестра
    @staticmethod
    def remove_from_registry(key, value_name=None):
        key_path = r"SOFTWARE\BLSEngineering\BLSMark"
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                if value_name:
                    winreg.DeleteValue(reg_key, value_name)
                else:
                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            return True
        except FileNotFoundError:
            return False
        except PermissionError:
            print("Недостаточно прав для удаления из реестра.")
            return False
