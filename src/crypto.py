import base64
import os
from typing import Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class CryptoManager:
    def __init__(self, master_password: str, salt: bytes = None):
        """
        Инициализация менеджера шифрования.
        
        :param master_password: Мастер-пароль для шифрования
        :param salt: Соль для генерации ключа (если None, генерируется новая)
        """
        if salt is not None and len(salt) != 16:
            raise ValueError("Некорректная длина соли. Должно быть 16 байт.")
            
        self.salt = salt if salt else os.urandom(16)
        self.key = self._derive_key(master_password)
        self.fernet = Fernet(base64.urlsafe_b64encode(self.key))

    def _derive_key(self, password: str) -> bytes:
        """
        Генерация ключа шифрования из мастер-пароля.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt(self, data: str) -> bytes:
        """
        Шифрование данных.
        """
        return self.fernet.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Расшифровка данных.
        """
        try:
            return self.fernet.decrypt(encrypted_data).decode()
        except Exception as e:
            raise ValueError("Ошибка расшифровки. Возможно, неверный мастер-пароль.") from e

    def export_encrypted_data(self, data: dict) -> Tuple[bytes, bytes]:
        """
        Экспорт зашифрованных данных с солью.
        """
        encrypted = self.encrypt(str(data))
        return encrypted, self.salt

    @classmethod
    def import_encrypted_data(cls, master_password: str, encrypted_data: bytes, salt: bytes) -> dict:
        """
        Импорт и расшифровка данных.
        """
        crypto = cls(master_password, salt)
        decrypted = crypto.decrypt(encrypted_data)
        return eval(decrypted)  # Безопасно только для доверенных данных

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """
        Смена мастер-пароля.
        """
        try:
            # Проверяем старый пароль
            old_key = self._derive_key(old_password)
            if old_key != self.key:
                return False
            
            # Генерируем новый ключ
            self.salt = os.urandom(16)
            self.key = self._derive_key(new_password)
            self.fernet = Fernet(base64.urlsafe_b64encode(self.key))
            return True
        except Exception:
            return False

    @staticmethod
    def generate_salt() -> bytes:
        """
        Генерация новой соли.
        """
        return os.urandom(16)

    @staticmethod
    def verify_master_password(password: str) -> bool:
        """
        Проверка сложности мастер-пароля.
        """
        if len(password) < 12:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        return all([has_upper, has_lower, has_digit, has_special]) 