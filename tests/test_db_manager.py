import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import tempfile

from crypto import CryptoManager
from db_manager import DatabaseManager
from models import Base, Password, Tag, UsageHistory, Settings

# Тестовые константы
TEST_PASSWORD = "TestPass123!"
TEST_MASTER_PASSWORD = "MasterPass123!"

@pytest.fixture
def db_manager(test_passwords):
    """
    Фикстура для создания тестового менеджера БД.
    """
    crypto = CryptoManager(test_passwords['master'])
    return DatabaseManager(":memory:", crypto)

@pytest.fixture
def test_password(db_manager, test_passwords, test_db_data):
    """
    Фикстура для создания тестового пароля.
    """
    return db_manager.add_password(
        title=test_db_data['title'],
        password=test_passwords['test'],
        website=test_db_data['website'],
        notes=test_db_data['notes'],
        tags=test_db_data['tags']
    )

def test_add_password(db_manager, test_passwords, test_db_data):
    """
    Тест добавления пароля.
    """
    password = db_manager.add_password(
        title=test_db_data['title'],
        password=test_passwords['test'],
        website=test_db_data['website']
    )
    assert password is not None
    assert password.title == test_db_data['title']
    assert password.website == test_db_data['website']

def test_get_password(db_manager, test_password):
    """
    Тест получения пароля.
    """
    password = db_manager.get_password(test_password.id)
    assert password is not None
    assert password.title == "Test Account"
    assert db_manager.crypto.decrypt(password.encrypted_password) == TEST_PASSWORD

def test_update_password(db_manager, test_password):
    """
    Тест обновления пароля.
    """
    updated = db_manager.update_password(
        test_password.id,
        title="Updated Account",
        password=TEST_PASSWORD,
        website="updated.com"
    )
    assert updated
    password = db_manager.get_password(test_password.id)
    assert password.title == "Updated Account"
    assert password.website == "updated.com"

def test_delete_password(db_manager, test_password):
    """
    Тест удаления пароля.
    """
    assert db_manager.delete_password(test_password.id)
    assert db_manager.get_password(test_password.id) is None

def test_search_passwords(db_manager):
    """
    Тест поиска паролей.
    """
    # Добавляем тестовые пароли с разными тегами
    db_manager.add_password(
        title="Email Account",
        password=TEST_PASSWORD,
        website="email.com",
        tags=["email"]
    )
    
    db_manager.add_password(
        title="Work Account",
        password=TEST_PASSWORD,
        website="work.com",
        tags=["work"]
    )
    
    # Поиск по заголовку
    results = db_manager.search_passwords("email")
    assert len(results) == 1
    assert results[0].title == "Email Account"
    
    # Поиск по тегу
    results = db_manager.search_passwords("work")
    assert len(results) == 1
    assert results[0].title == "Work Account"

def test_password_usage(db_manager, test_password, test_db_data):
    """
    Тест логирования использования пароля.
    """
    db_manager.log_password_usage(
        test_password.id,
        test_db_data['apps']['name'],
        test_db_data['apps']['window']
    )
    
    history = db_manager.get_usage_history(test_password.id)
    assert len(history) == 1
    assert history[0].app_name == test_db_data['apps']['name']
    assert history[0].window_title == test_db_data['apps']['window']

def test_favorite_toggle(db_manager, test_password):
    """
    Тест переключения избранного статуса.
    """
    # Проверяем начальное состояние
    assert not test_password.is_favorite
    
    # Включаем избранное
    db_manager.toggle_favorite(test_password.id, True)
    password = db_manager.get_password(test_password.id)
    assert password.is_favorite
    
    # Выключаем избранное
    db_manager.toggle_favorite(test_password.id, False)
    password = db_manager.get_password(test_password.id)
    assert not password.is_favorite

def test_tags_management(db_manager):
    """
    Тест управления тегами
    """
    # Добавляем пароли с тегами
    db_manager.add_password(
        title="Test1",
        password="Test1P@ss",
        tags=["tag1", "tag2"]
    )
    
    db_manager.add_password(
        title="Test2",
        password="Test2P@ss",
        tags=["tag2", "tag3"]
    )
    
    # Получаем все теги
    tags = db_manager.get_all_tags()
    assert len(tags) == 3
    assert set(tags) == {"tag1", "tag2", "tag3"}
    
    # Удаляем пароли и проверяем очистку неиспользуемых тегов
    passwords = db_manager.search_passwords()
    for p in passwords:
        db_manager.delete_password(p.id)
    
    # Проверяем, что все теги удалены
    tags = db_manager.get_all_tags()
    assert len(tags) == 0

def test_edge_cases(db_manager):
    """
    Тест граничных случаев
    """
    # Тест с несуществующим паролем
    assert db_manager.get_password(999) is None
    assert not db_manager.update_password(999, title="New")
    assert not db_manager.delete_password(999)
    
    # Тест с пустыми значениями
    password = db_manager.add_password(
        title="Empty Test",
        password="EmptyP@ss123",
        website="",
        notes="",
        tags=[],
        association_words=[]
    )
    
    assert password is not None
    assert password.website == ""
    assert password.notes == ""
    assert len(password.tags) == 0
    assert password.association_words == ""
    
    # Тест с дубликатами тегов
    password = db_manager.add_password(
        title="Duplicate Tags",
        password="DupP@ss123",
        tags=["tag1", "tag1", "tag1"]
    )
    
    assert password is not None
    assert len(password.tags) == 1  # Дубликаты должны быть удалены 