import pytest
from src.crypto import CryptoManager
import os

# Тестовые константы
TEST_VALID_PASSWORD = "TestPassword123!"
TEST_SHORT_PASSWORD = "short"
TEST_NO_NUMBERS = "no_numbers"
TEST_NO_LOWERCASE = "NOPASSWORD_1"
TEST_NO_UPPERCASE = "nopassword_1"
TEST_NO_SPECIAL = "NoSpecial1"

def test_encryption_decryption(test_passwords, test_data):
    # Тест базового шифрования/дешифрования
    crypto = CryptoManager(test_passwords['valid'])
    original_data = test_data['simple_string']
    
    encrypted = crypto.encrypt(original_data)
    decrypted = crypto.decrypt(encrypted)
    
    assert decrypted == original_data
    assert encrypted != original_data.encode()

def test_different_passwords(test_passwords):
    # Тест с разными паролями
    crypto1 = CryptoManager("password1")
    crypto2 = CryptoManager("password2")
    
    data = "test data"
    encrypted = crypto1.encrypt(data)
    
    # Попытка расшифровать другим паролем должна вызвать ошибку
    with pytest.raises(ValueError):
        crypto2.decrypt(encrypted)

def test_salt_consistency(test_passwords):
    # Тест консистентности с одинаковой солью
    salt = os.urandom(16)
    crypto1 = CryptoManager(test_passwords['valid'], salt)
    crypto2 = CryptoManager(test_passwords['valid'], salt)
    
    data = "test data"
    encrypted = crypto1.encrypt(data)
    decrypted = crypto2.decrypt(encrypted)
    
    assert decrypted == data

def test_export_import(test_passwords, test_data):
    # Тест экспорта/импорта данных
    crypto = CryptoManager(test_passwords['valid'])
    original_data = test_data['dict_data']
    
    encrypted, salt = crypto.export_encrypted_data(original_data)
    
    # Создаем новый экземпляр с той же солью
    new_crypto = CryptoManager(test_passwords['valid'], salt)
    decrypted_data = CryptoManager.import_encrypted_data(test_passwords['valid'], encrypted, salt)
    
    assert decrypted_data == original_data

def test_master_password_change(test_passwords, test_data):
    """
    Тест смены мастер-пароля
    """
    crypto = CryptoManager("old_password")
    data = test_data['simple_string']
    
    # Шифруем данные старым паролем
    encrypted = crypto.encrypt(data)
    
    # Меняем пароль
    success = crypto.change_master_password("old_password", "new_password")
    assert success
    
    # Шифруем новые данные новым паролем
    new_data = test_data['new_data']
    new_encrypted = crypto.encrypt(new_data)
    
    # Проверяем, что можем расшифровать новые данные
    decrypted = crypto.decrypt(new_encrypted)
    assert decrypted == new_data
    
    # Проверяем, что не можем расшифровать старые данные
    with pytest.raises(ValueError):
        crypto.decrypt(encrypted)

def test_master_password_validation(test_passwords):
    """
    Тест валидации мастер-пароля.
    """
    # Валидный пароль
    assert CryptoManager.verify_master_password(test_passwords['valid'])

def test_edge_cases(test_passwords):
    """
    Тест граничных случаев для паролей.
    """
    crypto = CryptoManager(test_passwords['valid'])
    
    assert not crypto.verify_master_password(test_passwords['short'])      # Слишком короткий
    assert not crypto.verify_master_password(test_passwords['no_numbers']) # Нет цифр
    assert not crypto.verify_master_password(test_passwords['no_lowercase']) # Нет строчных букв
    assert not crypto.verify_master_password(test_passwords['no_uppercase']) # Нет заглавных букв
    assert not crypto.verify_master_password(test_passwords['no_special'])   # Нет спецсимволов

def test_error_handling(test_passwords):
    """
    Тест обработки ошибок
    """
    crypto = CryptoManager(test_passwords['valid'])
    
    # Некорректные входные данные для расшифровки
    with pytest.raises(ValueError):
        crypto.decrypt(b"invalid data")
    
    # Попытка изменить пароль с неверным старым паролем
    assert not crypto.change_master_password("wrong_password", "new_password")
    
    # Проверка валидации пароля
    assert not crypto.verify_master_password(test_passwords['short'])      # Слишком короткий
    assert not crypto.verify_master_password(test_passwords['no_numbers']) # Нет цифр
    assert not crypto.verify_master_password(test_passwords['no_lowercase']) # Нет заглавных букв
    assert not crypto.verify_master_password(test_passwords['no_uppercase']) # Нет строчных букв
    assert not crypto.verify_master_password(test_passwords['no_special'])   # Нет спецсимволов
    
    # Некорректная соль
    with pytest.raises(ValueError):
        CryptoManager(test_passwords['valid'], b"short_salt")  # Соль неправильной длины 