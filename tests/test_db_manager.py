import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import tempfile

from crypto import CryptoManager
from db_manager import DatabaseManager
from models import Base, Password, Tag, UsageHistory, Settings

@pytest.fixture
def db_manager():
    """
    Создаем временную базу данных для тестов
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    crypto = CryptoManager("test_password")
    manager = DatabaseManager(db_path, crypto)
    
    yield manager
    
    if os.path.exists(db_path):
        os.unlink(db_path)

def test_add_password(db_manager):
    """
    Тест добавления пароля
    """
    password = db_manager.add_password(
        title="Test Account",
        password="TestP@ss123",
        website="test.com",
        notes="Test notes",
        tags=["test", "account"],
        association_words=["test", "account"]
    )
    
    assert password is not None
    assert password.title == "Test Account"
    assert password.website == "test.com"
    assert len(password.tags) == 2
    assert password.notes == "Test notes"
    assert password.association_words == "test,account"

def test_get_password(db_manager):
    """
    Тест получения пароля
    """
    # Добавляем тестовый пароль
    added = db_manager.add_password(
        title="Test",
        password="TestP@ss123",
        website="test.com"
    )
    
    # Получаем пароль
    password = db_manager.get_password(added.id)
    
    assert password is not None
    assert password.title == "Test"
    assert password.website == "test.com"
    assert db_manager.crypto.decrypt(password.encrypted_password) == "TestP@ss123"

def test_update_password(db_manager):
    """
    Тест обновления пароля
    """
    # Добавляем тестовый пароль
    password = db_manager.add_password(
        title="Old Title",
        password="OldP@ss123",
        website="old.com"
    )
    
    # Обновляем пароль
    success = db_manager.update_password(
        password.id,
        title="New Title",
        password="NewP@ss123",
        website="new.com"
    )
    
    assert success
    
    # Проверяем обновление
    updated = db_manager.get_password(password.id)
    assert updated.title == "New Title"
    assert updated.website == "new.com"
    assert db_manager.crypto.decrypt(updated.encrypted_password) == "NewP@ss123"

def test_delete_password(db_manager):
    """
    Тест удаления пароля
    """
    # Добавляем тестовый пароль
    password = db_manager.add_password(
        title="To Delete",
        password="DeleteMe123!",
        website="delete.com"
    )
    
    # Удаляем пароль
    success = db_manager.delete_password(password.id)
    assert success
    
    # Проверяем, что пароль удален
    deleted = db_manager.get_password(password.id)
    assert deleted is None

def test_search_passwords(db_manager):
    """
    Тест поиска паролей
    """
    # Добавляем тестовые пароли
    db_manager.add_password(
        title="Gmail Account",
        password="GmailP@ss123",
        website="gmail.com",
        tags=["email", "google"]
    )
    
    db_manager.add_password(
        title="GitHub Account",
        password="GitHubP@ss123",
        website="github.com",
        tags=["dev", "git"]
    )
    
    # Поиск по названию
    results = db_manager.search_passwords(query="Gmail")
    assert len(results) == 1
    assert results[0].website == "gmail.com"
    
    # Поиск по тегу
    results = db_manager.search_passwords(tag="dev")
    assert len(results) == 1
    assert results[0].title == "GitHub Account"

def test_password_usage_history(db_manager):
    """
    Тест истории использования пароля
    """
    # Добавляем пароль
    password = db_manager.add_password(
        title="Test Usage",
        password="TestP@ss123",
        website="test.com"
    )
    
    # Логируем использование
    db_manager.log_password_usage(
        password.id,
        "Firefox",
        "Login Page"
    )
    
    # Получаем историю использования
    history = db_manager.get_usage_history(password_id=password.id)
    
    assert len(history) == 1
    assert history[0]['app_name'] == "Firefox"
    assert history[0]['window_title'] == "Login Page"

def test_favorite_passwords(db_manager):
    """
    Тест избранных паролей
    """
    # Добавляем пароль
    password = db_manager.add_password(
        title="Favorite Test",
        password="FavP@ss123",
        website="favorite.com"
    )
    
    # Добавляем в избранное
    success = db_manager.toggle_favorite(password.id)
    assert success
    
    # Проверяем статус
    password_info = db_manager.get_password(password.id)
    assert password_info.is_favorite
    
    # Убираем из избранного
    success = db_manager.toggle_favorite(password.id)
    assert success
    
    # Проверяем статус
    password_info = db_manager.get_password(password.id)
    assert not password_info.is_favorite

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