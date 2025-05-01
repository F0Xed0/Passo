import pytest
from src.password_generator import PasswordGenerator

def test_password_generation():
    generator = PasswordGenerator()
    words = ["кофе", "вечер", "дождь"]
    
    # Тест базовой генерации
    password, transformations = generator.generate_from_associations(words)
    assert len(password) >= 12
    assert any(c.isdigit() for c in password)
    assert any(c in generator.special_chars for c in password)
    assert any(c.isupper() for c in password)
    
    # Тест без цифр
    password, _ = generator.generate_from_associations(words, include_numbers=False)
    assert not any(c.isdigit() for c in password)
    
    # Тест без спецсимволов
    password, _ = generator.generate_from_associations(words, include_special=False)
    assert not any(c in generator.special_chars for c in password)
    
    # Тест без заглавных букв
    password, _ = generator.generate_from_associations(words, include_caps=False)
    assert not any(c.isupper() for c in password)
    
    # Тест минимальной длины
    min_length = 20
    password, _ = generator.generate_from_associations(words, min_length=min_length)
    assert len(password) >= min_length

def test_password_transformation_explanation():
    generator = PasswordGenerator()
    words = ["тест"]
    
    # Генерируем пароль и получаем объяснение
    password, transformations = generator.generate_from_associations(words)
    explanation = generator.explain_transformation(words, transformations)
    
    # Проверяем, что объяснение содержит исходное слово
    assert "тест" in explanation
    
    # Проверяем, что объяснение содержит информацию о преобразованиях
    for word in words:
        if word in transformations:
            for original, transformed in transformations[word].items():
                if original != transformed:
                    assert f"'{original}' заменено на '{transformed}'" in explanation

def test_password_strength_validation():
    generator = PasswordGenerator()
    
    # Тест слабого пароля
    is_valid, message = generator.validate_password_strength("weak")
    assert not is_valid
    assert "длина" in message.lower()
    
    # Тест пароля без цифр
    is_valid, message = generator.validate_password_strength("LongPasswordWithoutNumbers!")
    assert not is_valid
    assert "цифры" in message.lower()
    
    # Тест пароля без спецсимволов
    is_valid, message = generator.validate_password_strength("LongPassword123")
    assert not is_valid
    assert "специальные символы" in message.lower()
    
    # Тест пароля без заглавных букв
    is_valid, message = generator.validate_password_strength("longpassword123!")
    assert not is_valid
    assert "заглавные буквы" in message.lower()
    
    # Тест сильного пароля
    is_valid, message = generator.validate_password_strength("StrongP@ssw0rd123")
    assert is_valid
    assert "соответствует всем требованиям" in message.lower()

def test_consistent_generation():
    """
    Проверяем, что одинаковые входные данные дают разные пароли
    для обеспечения уникальности.
    """
    generator = PasswordGenerator()
    words = ["тест"]
    
    # Генерируем несколько паролей с одинаковыми входными данными
    passwords = set()
    for _ in range(5):
        password, _ = generator.generate_from_associations(words)
        passwords.add(password)
    
    # Проверяем, что все пароли разные
    assert len(passwords) == 5

def test_edge_cases():
    generator = PasswordGenerator()
    
    # Тест с пустым списком слов
    password, _ = generator.generate_from_associations([])
    assert len(password) >= 12
    
    # Тест с очень длинным словом
    long_word = "а" * 100
    password, _ = generator.generate_from_associations([long_word])
    assert len(password) >= 12
    
    # Тест со специальными символами в исходных словах
    special_word = "test!@#$%"
    password, _ = generator.generate_from_associations([special_word])
    assert len(password) >= 12
    
    # Тест с цифрами в исходных словах
    numeric_word = "test123"
    password, _ = generator.generate_from_associations([numeric_word])
    assert len(password) >= 12 