import pytest
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QMessageBox, QDialog
from PyQt6.QtCore import Qt
from unittest.mock import MagicMock, patch
import sys
import os
import tempfile

from crypto import CryptoManager
from db_manager import DatabaseManager
from main import MainWindow
from models import Settings

@pytest.fixture
def app(qapp):
    """
    Используем фикстуру qapp из pytest-qt вместо создания своего QApplication
    """
    return qapp

@pytest.fixture
def temp_db():
    """
    Создаем временную базу данных для тестов
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def main_window(app, temp_db):
    """
    Фикстура для создания главного окна с моками
    """
    # Мокаем WindowManager
    with patch('window_manager.WindowManager') as mock_window_manager:
        # Настраиваем мок WindowManager
        manager_instance = mock_window_manager.return_value
        manager_instance.clipboard_timeout = 30
        manager_instance.get_active_window_info.return_value = {
            'class': 'TestApp',
            'name': 'Test Window'
        }
        
        # Инициализируем менеджеры с тестовыми данными
        crypto = CryptoManager("test_password")
        db = DatabaseManager(temp_db, crypto)
        
        # Мокаем методы базы данных
        db.log_password_usage = MagicMock()
        db.update_password = MagicMock(return_value=True)
        db.delete_password = MagicMock(return_value=True)
        
        # Инициализируем базовые настройки
        with db.Session() as session:
            settings = Settings(
                key="clipboard_timeout",
                value="30"
            )
            session.add(settings)
            settings = Settings(
                key="2fa_secret",
                value=""
            )
            session.add(settings)
            session.commit()
        
        # Создаем главное окно с существующей базой данных
        window = MainWindow(existing_db=db)
        
        # Подменяем менеджеры на тестовые
        window.window_manager = manager_instance
        
        # Мокаем tray_icon
        window.tray_icon = MagicMock()
        
        yield window
        
        # Очистка после тестов
        window.close()

def test_copy_password_success(main_window):
    """
    Тест успешного копирования пароля
    """
    # Добавляем тестовый пароль в базу
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="SecretPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем search_passwords и get_password
    with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
        with patch.object(main_window.db, 'get_password', return_value=password_entry):
            # Вызываем функцию копирования
            main_window.copy_password()
            
            # Проверяем, что пароль был скопирован
            main_window.window_manager.copy_to_clipboard.assert_called_once_with("SecretPass123!")
            
            # Проверяем, что использование было залогировано
            main_window.db.log_password_usage.assert_called_once_with(
                password_entry.id,
                "TestApp",
                "Test Window"
            )
            
            # Проверяем, что было показано уведомление
            main_window.tray_icon.showMessage.assert_called_once()

def test_copy_password_no_selection(main_window):
    """
    Тест копирования без выбранного пароля
    """
    # Не выбираем пароль
    main_window.password_list.setCurrentItem(None)
    
    # Вызываем функцию копирования
    main_window.copy_password()
    
    # Проверяем, что копирование не произошло
    main_window.window_manager.copy_to_clipboard.assert_not_called()
    
    # Проверяем, что логирование не произошло
    main_window.db.log_password_usage.assert_not_called()

def test_copy_password_not_found(main_window):
    """
    Тест копирования несуществующего пароля
    """
    # Создаем элемент списка с несуществующим паролем
    item = QListWidgetItem("Non Existent Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем search_passwords чтобы он возвращал пустой список
    with patch.object(main_window.db, 'search_passwords', return_value=[]):
        # Мокаем QMessageBox
        with patch.object(QMessageBox, 'warning') as mock_warning:
            # Вызываем функцию копирования
            main_window.copy_password()
            
            # Проверяем, что было показано предупреждение
            mock_warning.assert_called_once()
            
            # Проверяем, что копирование не произошло
            main_window.window_manager.copy_to_clipboard.assert_not_called()
            
            # Проверяем, что логирование не произошло
            main_window.db.log_password_usage.assert_not_called()

def test_copy_password_database_error(main_window):
    """
    Тест обработки ошибки базы данных
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="SecretPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем search_passwords и get_password
    with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
        with patch.object(main_window.db, 'get_password', return_value=None):
            # Мокаем QMessageBox
            with patch.object(QMessageBox, 'warning') as mock_warning:
                # Вызываем функцию копирования
                main_window.copy_password()
                
                # Проверяем, что было показано предупреждение
                mock_warning.assert_called_once()
                
                # Проверяем, что копирование не произошло
                main_window.window_manager.copy_to_clipboard.assert_not_called()
                
                # Проверяем, что логирование не произошло
                main_window.db.log_password_usage.assert_not_called()

def test_edit_password_success(main_window):
    """
    Тест успешного редактирования пароля
    """
    # Добавляем тестовый пароль в базу
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="OldPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем диалог редактирования
    with patch('src.main.EditPasswordDialog') as mock_dialog:
        mock_instance = mock_dialog.return_value
        mock_instance.exec.return_value = QDialog.DialogCode.Accepted
        mock_instance.get_password_data.return_value = {
            'title': "Updated Password",
            'password': "NewPass123!",
            'website': "updated.com",
            'tags': ["test", "new"],
            'notes': "Updated notes"
        }
        
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Вызываем функцию редактирования
                main_window.edit_password()
                
                # Проверяем, что пароль был обновлен
                main_window.db.update_password.assert_called_once()

def test_edit_password_no_selection(main_window):
    """
    Тест редактирования без выбранного пароля
    """
    # Не выбираем пароль
    main_window.password_list.setCurrentItem(None)
    
    # Вызываем функцию редактирования
    main_window.edit_password()
    
    # Проверяем, что редактирование не произошло
    main_window.db.update_password.assert_not_called()

def test_edit_password_not_found(main_window):
    """
    Тест редактирования несуществующего пароля
    """
    # Создаем элемент списка с несуществующим паролем
    item = QListWidgetItem("Non Existent Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем search_passwords чтобы он возвращал пустой список
    with patch.object(main_window.db, 'search_passwords', return_value=[]):
        # Мокаем QMessageBox
        with patch.object(QMessageBox, 'warning') as mock_warning:
            # Вызываем функцию редактирования
            main_window.edit_password()
            
            # Проверяем, что было показано предупреждение
            mock_warning.assert_called_once()
            
            # Проверяем, что редактирование не произошло
            main_window.db.update_password.assert_not_called()

def test_edit_password_database_error(main_window):
    """
    Тест обработки ошибки базы данных при редактировании
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="OldPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем диалог редактирования
    with patch('src.main.EditPasswordDialog') as mock_dialog:
        mock_instance = mock_dialog.return_value
        mock_instance.exec.return_value = QDialog.DialogCode.Accepted
        mock_instance.get_password_data.return_value = {
            'title': "Updated Password",
            'password': "NewPass123!",
            'website': "updated.com",
            'tags': [],
            'notes': ""
        }
        
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Мокаем update_password чтобы он вызывал исключение
                main_window.db.update_password.side_effect = Exception("DB Error")
                
                # Мокаем QMessageBox
                with patch.object(QMessageBox, 'critical') as mock_critical:
                    # Вызываем функцию редактирования
                    main_window.edit_password()
                    
                    # Проверяем, что было показано сообщение об ошибке
                    mock_critical.assert_called_once()

def test_autotype_password_success(main_window):
    """
    Тест успешного автоввода пароля
    """
    # Добавляем тестовый пароль в базу
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.information для имитации нажатия OK
    with patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok):
        # Мокаем QTimer.singleShot для немедленного выполнения
        with patch('PyQt6.QtCore.QTimer.singleShot', side_effect=lambda timeout, callback: callback()):
            # Мокаем search_passwords и get_password
            with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
                with patch.object(main_window.db, 'get_password', return_value=password_entry):
                    # Вызываем функцию автоввода
                    main_window.autotype_password()
                    
                    # Проверяем, что пароль был введен
                    main_window.window_manager.type_text.assert_called_once_with("TestPass123!")
                    
                    # Проверяем, что использование было залогировано
                    main_window.db.log_password_usage.assert_called_once_with(
                        password_entry.id,
                        "TestApp",
                        "Test Window"
                    )

def test_autotype_password_cancel(main_window):
    """
    Тест отмены автоввода пароля
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.information для имитации нажатия Cancel
    with patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Cancel):
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Вызываем функцию автоввода
                main_window.autotype_password()
                
                # Проверяем, что пароль не был введен
                main_window.window_manager.type_text.assert_not_called()
                
                # Проверяем, что использование не было залогировано
                main_window.db.log_password_usage.assert_not_called()

def test_autotype_password_error(main_window):
    """
    Тест обработки ошибки при автовводе пароля
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.information для имитации нажатия OK
    with patch.object(QMessageBox, 'information', return_value=QMessageBox.StandardButton.Ok):
        # Мокаем QTimer.singleShot для немедленного выполнения
        with patch('PyQt6.QtCore.QTimer.singleShot', side_effect=lambda timeout, callback: callback()):
            # Мокаем search_passwords и get_password
            with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
                with patch.object(main_window.db, 'get_password', return_value=password_entry):
                    # Мокаем type_text чтобы он вызывал исключение
                    main_window.window_manager.type_text.side_effect = Exception("Type Error")
                    
                    # Мокаем QMessageBox.critical
                    with patch.object(QMessageBox, 'critical') as mock_critical:
                        # Вызываем функцию автоввода
                        main_window.autotype_password()
                        
                        # Проверяем, что было показано сообщение об ошибке
                        mock_critical.assert_called_once()
                        
                        # Проверяем, что использование не было залогировано
                        main_window.db.log_password_usage.assert_not_called()

def test_delete_password_success(main_window):
    """
    Тест успешного удаления пароля
    """
    # Добавляем тестовый пароль в базу
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com",
        tags=["test", "delete"],
        notes="Test notes"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.question для имитации нажатия Yes
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Вызываем функцию удаления
                main_window.delete_password()
                
                # Проверяем, что пароль был удален
                main_window.db.delete_password.assert_called_once_with(password_entry.id)

def test_delete_password_cancel(main_window):
    """
    Тест отмены удаления пароля
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.question для имитации нажатия No
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Вызываем функцию удаления
                main_window.delete_password()
                
                # Проверяем, что пароль не был удален
                main_window.db.delete_password.assert_not_called()

def test_delete_password_error(main_window):
    """
    Тест обработки ошибки при удалении пароля
    """
    # Добавляем тестовый пароль
    password_entry = main_window.db.add_password(
        title="Test Password",
        password="TestPass123!",
        website="test.com"
    )
    
    # Создаем элемент списка
    item = QListWidgetItem("Test Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем QMessageBox.question для имитации нажатия Yes
    with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
        # Мокаем search_passwords и get_password
        with patch.object(main_window.db, 'search_passwords', return_value=[password_entry]):
            with patch.object(main_window.db, 'get_password', return_value=password_entry):
                # Мокаем delete_password чтобы он вызывал исключение
                main_window.db.delete_password.side_effect = Exception("Delete Error")
                
                # Мокаем QMessageBox.critical
                with patch.object(QMessageBox, 'critical') as mock_critical:
                    # Вызываем функцию удаления
                    main_window.delete_password()
                    
                    # Проверяем, что было показано сообщение об ошибке
                    mock_critical.assert_called_once()

def test_delete_password_not_found(main_window):
    """
    Тест удаления несуществующего пароля
    """
    # Создаем элемент списка с несуществующим паролем
    item = QListWidgetItem("Non Existent Password (test.com)")
    main_window.password_list.addItem(item)
    main_window.password_list.setCurrentItem(item)
    
    # Мокаем search_passwords чтобы он возвращал пустой список
    with patch.object(main_window.db, 'search_passwords', return_value=[]):
        # Мокаем QMessageBox
        with patch.object(QMessageBox, 'warning') as mock_warning:
            # Вызываем функцию удаления
            main_window.delete_password()
            
            # Проверяем, что было показано предупреждение
            mock_warning.assert_called_once()
            
            # Проверяем, что удаление не произошло
            main_window.db.delete_password.assert_not_called() 