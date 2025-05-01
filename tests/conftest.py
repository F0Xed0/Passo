import pytest

@pytest.fixture
def test_passwords():
    """Фикстура с тестовыми паролями"""
    return {
        'valid': "TestPassword123!",
        'short': "short",
        'no_numbers': "no_numbers",
        'no_lowercase': "NOPASSWORD_1",
        'no_uppercase': "nopassword_1",
        'no_special': "NoSpecial1",
        'test': "TestPass123!",
        'master': "MasterPass123!"
    }

@pytest.fixture
def test_data():
    """Фикстура с тестовыми данными"""
    return {
        'simple_string': "sensitive data",
        'dict_data': {"key": "value", "number": 123},
        'new_data': "new test data"
    }

@pytest.fixture
def test_db_data():
    """Фикстура с тестовыми данными для базы данных"""
    return {
        'title': "Test Account",
        'website': "test.com",
        'notes': "Test notes",
        'tags': ["test"],
        'apps': {
            'name': "TestApp",
            'window': "Test Window"
        }
    } 