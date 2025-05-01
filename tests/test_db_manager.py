import pytest
import os
from datetime import datetime, timedelta
from src.db_manager import DatabaseManager
from src.crypto import CryptoManager
from src.models import Base

@pytest.fixture
def db_manager():
    # Создаем временную базу данных для тестов
    test_db_path = "test_passwords.db"
    crypto = CryptoManager("test_password")
    
    # Создаем менеджер базы данных
    manager = DatabaseManager(test_db_path, crypto)
    
    yield manager
    
    # Удаляем тестовую базу после завершения
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

def test_add_password(db_manager):
    # Тест добавления пароля
    password = db_manager.add_password(
        title="Test Account",
        password="TestP@ss123",
        website="test.com",
        notes="Test notes",
        tags=["test", "account"],
        association_words=["test", "account"]
    )
    
    assert password.title == "Test Account"
    assert password.website == "test.com"
    assert len(password.tags) == 2

def test_get_password(db_manager):
    # Добавляем тестовый пароль
    added = db_manager.add_password(
        title="Test",
        password="TestP@ss123",
        website="test.com"
    )
    
    # Получаем пароль
    password = db_manager.get_password(added.id)
    
    assert password is not None
    assert password['title'] == "Test"
    assert password['password'] == "TestP@ss123"
    assert password['website'] == "test.com"

def test_update_password(db_manager):
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
    assert updated['title'] == "New Title"
    assert updated['password'] == "NewP@ss123"
    assert updated['website'] == "new.com"

def test_delete_password(db_manager):
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
    assert db_manager.get_password(password.id) is None

def test_search_passwords(db_manager):
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
    assert results[0]['website'] == "gmail.com"
    
    # Поиск по тегам
    results = db_manager.search_passwords(tags=["dev"])
    assert len(results) == 1
    assert results[0]['website'] == "github.com"
    
    # Поиск по сайту
    results = db_manager.search_passwords(website="github")
    assert len(results) == 1
    assert results[0]['title'] == "GitHub Account"

def test_password_usage_history(db_manager):
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
    assert history[0]['application_name'] == "Firefox"
    assert history[0]['window_title'] == "Login Page"

def test_favorite_passwords(db_manager):
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
    assert password_info['is_favorite']
    
    # Убираем из избранного
    success = db_manager.toggle_favorite(password.id)
    assert success
    
    # Проверяем статус
    password_info = db_manager.get_password(password.id)
    assert not password_info['is_favorite']

def test_tags_management(db_manager):
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
        db_manager.delete_password(p['id'])
    
    cleaned = db_manager.cleanup_unused_tags()
    assert cleaned == 3  # Должно быть удалено 3 тега
    
    tags = db_manager.get_all_tags()
    assert len(tags) == 0

def test_edge_cases(db_manager):
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
    
    # Тест с дубликатами тегов
    db_manager.add_password(
        title="Duplicate Tags",
        password="DupP@ss123",
        tags=["tag1", "tag1", "tag1"]
    )
    
    tags = db_manager.get_all_tags()
    assert tags.count("tag1") == 1  # Теги должны быть уникальными 