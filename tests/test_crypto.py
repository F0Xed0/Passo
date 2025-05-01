import pytest
from src.crypto import CryptoManager
import os

def test_encryption_decryption():
    # Тест базового шифрования/дешифрования
    crypto = CryptoManager("test_password")
    original_data = "sensitive data"
    
    encrypted = crypto.encrypt(original_data)
    decrypted = crypto.decrypt(encrypted)
    
    assert decrypted == original_data
    assert encrypted != original_data.encode()

def test_different_passwords():
    # Тест с разными паролями
    crypto1 = CryptoManager("password1")
    crypto2 = CryptoManager("password2")
    
    data = "test data"
    encrypted = crypto1.encrypt(data)
    
    # Попытка расшифровать другим паролем должна вызвать ошибку
    with pytest.raises(ValueError):
        crypto2.decrypt(encrypted)

def test_salt_consistency():
    # Тест консистентности с одинаковой солью
    salt = os.urandom(16)
    crypto1 = CryptoManager("same_password", salt)
    crypto2 = CryptoManager("same_password", salt)
    
    data = "test data"
    encrypted = crypto1.encrypt(data)
    decrypted = crypto2.decrypt(encrypted)
    
    assert decrypted == data

def test_export_import():
    # Тест экспорта/импорта данных
    crypto = CryptoManager("test_password")
    original_data = {"key": "value", "number": 123}
    
    encrypted, salt = crypto.export_encrypted_data(original_data)
    
    # Создаем новый экземпляр с той же солью
    new_crypto = CryptoManager("test_password", salt)
    decrypted_data = CryptoManager.import_encrypted_data("test_password", encrypted, salt)
    
    assert decrypted_data == original_data

def test_master_password_change():
    # Тест смены мастер-пароля
    crypto = CryptoManager("old_password")
    data = "test data"
    
    # Шифруем данные старым паролем
    encrypted = crypto.encrypt(data)
    
    # Меняем пароль
    success = crypto.change_master_password("old_password", "new_password")
    assert success
    
    # Пробуем расшифровать новым паролем
    decrypted = crypto.decrypt(encrypted)
    assert decrypted == data
    
    # Проверяем, что старый пароль больше не работает
    with pytest.raises(ValueError):
        old_crypto = CryptoManager("old_password", crypto.salt)
        old_crypto.decrypt(encrypted)

def test_password_validation():
    # Тест валидации мастер-пароля
    # Слишком короткий
    assert not CryptoManager.verify_master_password("short")
    
    # Без цифр
    assert not CryptoManager.verify_master_password("LongPasswordNoNumbers!")
    
    # Без спецсимволов
    assert not CryptoManager.verify_master_password("LongPassword123")
    
    # Без заглавных букв
    assert not CryptoManager.verify_master_password("longpassword123!")
    
    # Валидный пароль
    assert CryptoManager.verify_master_password("StrongP@ssw0rd123")

def test_edge_cases():
    crypto = CryptoManager("test_password")
    
    # Пустая строка
    empty = ""
    encrypted_empty = crypto.encrypt(empty)
    assert crypto.decrypt(encrypted_empty) == empty
    
    # Очень длинная строка
    long_string = "a" * 10000
    encrypted_long = crypto.encrypt(long_string)
    assert crypto.decrypt(encrypted_long) == long_string
    
    # Строка со спецсимволами
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    encrypted_special = crypto.encrypt(special_chars)
    assert crypto.decrypt(encrypted_special) == special_chars
    
    # Юникод
    unicode_string = "привет 你好 مرحبا"
    encrypted_unicode = crypto.encrypt(unicode_string)
    assert crypto.decrypt(encrypted_unicode) == unicode_string

def test_error_handling():
    crypto = CryptoManager("test_password")
    
    # Некорректные входные данные для расшифровки
    with pytest.raises(ValueError):
        crypto.decrypt(b"invalid data")
    
    # Попытка изменить пароль с неверным старым паролем
    assert not crypto.change_master_password("wrong_password", "new_password")
    
    # Некорректная соль
    with pytest.raises(ValueError):
        CryptoManager("test_password", b"invalid salt") 