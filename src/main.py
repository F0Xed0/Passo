import sys
import os
import base64
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLabel, QLineEdit, QPushButton,
                           QListWidget, QMessageBox, QTabWidget, QComboBox,
                           QCheckBox, QSpinBox, QTextEdit, QSystemTrayIcon,
                           QMenu, QDialog, QInputDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QAction
import pyotp

from crypto import CryptoManager
from db_manager import DatabaseManager
import db_manager
print('DatabaseManager loaded from:', db_manager.__file__)
print('DatabaseManager methods:', dir(db_manager.DatabaseManager))
from password_generator import PasswordGenerator
from window_manager import WindowManager
from models import Settings

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в Passo")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Поле для мастер-пароля
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(QLabel("Мастер-пароль:"))
        layout.addWidget(self.password_input)
        
        # Поле для 2FA (если включено)
        self.totp_input = QLineEdit()
        self.totp_input.setPlaceholderText("Код двухфакторной аутентификации")
        layout.addWidget(QLabel("2FA код (если включен):"))
        layout.addWidget(self.totp_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Войти")
        self.cancel_button = QPushButton("Отмена")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

class PasswordGeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генерация пароля")
        self.setModal(True)
        
        self.generator = PasswordGenerator()
        
        layout = QVBoxLayout()
        
        # Поля для ассоциативных слов
        self.word_inputs = []
        for i in range(3):
            word_input = QLineEdit()
            word_input.setPlaceholderText(f"Ассоциативное слово {i+1}")
            self.word_inputs.append(word_input)
            layout.addWidget(word_input)
        
        # Настройки генерации
        self.include_numbers = QCheckBox("Включить цифры")
        self.include_special = QCheckBox("Включить спецсимволы")
        self.include_caps = QCheckBox("Включить заглавные буквы")
        self.length = QSpinBox()
        self.length.setRange(8, 32)
        self.length.setValue(16)
        
        layout.addWidget(self.include_numbers)
        layout.addWidget(self.include_special)
        layout.addWidget(self.include_caps)
        layout.addWidget(QLabel("Минимальная длина:"))
        layout.addWidget(self.length)
        
        # Результат
        self.result = QLineEdit()
        self.result.setReadOnly(True)
        layout.addWidget(QLabel("Сгенерированный пароль:"))
        layout.addWidget(self.result)
        
        # Объяснение
        self.explanation = QTextEdit()
        self.explanation.setReadOnly(True)
        layout.addWidget(QLabel("Как был сформирован пароль:"))
        layout.addWidget(self.explanation)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.generate_button = QPushButton("Генерировать")
        self.accept_button = QPushButton("Использовать")
        self.cancel_button = QPushButton("Отмена")
        
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.accept_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Подключаем сигналы
        self.generate_button.clicked.connect(self.generate_password)
        self.accept_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        # Генерируем начальный пароль
        self.generate_password()

    def generate_password(self):
        words = [w.text() for w in self.word_inputs if w.text()]
        if not words:
            words = ["passo"]  # Дефолтное слово, если ничего не введено
            
        password, transformations = self.generator.generate_from_associations(
            words,
            min_length=self.length.value(),
            include_numbers=self.include_numbers.isChecked(),
            include_special=self.include_special.isChecked(),
            include_caps=self.include_caps.isChecked()
        )
        
        self.result.setText(password)
        self.explanation.setText(self.generator.explain_transformation(words, transformations))

class EditPasswordDialog(QDialog):
    def __init__(self, password_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование пароля")
        self.setModal(True)
        self.password_info = password_info
        
        layout = QVBoxLayout()
        
        # Название
        self.title_input = QLineEdit()
        self.title_input.setText(password_info['title'])
        layout.addWidget(QLabel("Название:"))
        layout.addWidget(self.title_input)
        
        # Сайт
        self.website_input = QLineEdit()
        self.website_input.setText(password_info.get('website', ''))
        layout.addWidget(QLabel("Сайт:"))
        layout.addWidget(self.website_input)
        
        # Пароль
        password_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setText(password_info['password'])
        self.show_password = QPushButton("👁")
        self.show_password.setFixedWidth(30)
        self.show_password.clicked.connect(self.toggle_password_visibility)
        self.generate_password = QPushButton("🎲")
        self.generate_password.setFixedWidth(30)
        self.generate_password.clicked.connect(self.open_password_generator)
        
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.show_password)
        password_layout.addWidget(self.generate_password)
        
        layout.addWidget(QLabel("Пароль:"))
        layout.addLayout(password_layout)
        
        # Теги
        self.tags_input = QLineEdit()
        self.tags_input.setText(", ".join(password_info.get('tags', [])))
        self.tags_input.setPlaceholderText("Разделяйте теги запятыми")
        layout.addWidget(QLabel("Теги:"))
        layout.addWidget(self.tags_input)
        
        # Заметки
        self.notes_input = QTextEdit()
        self.notes_input.setText(password_info.get('notes', ''))
        layout.addWidget(QLabel("Заметки:"))
        layout.addWidget(self.notes_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.cancel_button = QPushButton("Отмена")
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Подключаем сигналы
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
    def toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_password.setText("🔒")
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_password.setText("👁")
    
    def open_password_generator(self):
        dialog = PasswordGeneratorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.password_input.setText(dialog.result.text())
    
    def get_password_data(self):
        return {
            'title': self.title_input.text(),
            'password': self.password_input.text(),
            'website': self.website_input.text(),
            'tags': [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()],
            'notes': self.notes_input.toPlainText()
        }

class MainWindow(QMainWindow):
    def __init__(self, existing_db=None):
        super().__init__()
        self.setWindowTitle("Passo - Менеджер паролей")
        self.setMinimumSize(800, 600)
        
        # Инициализация менеджеров
        self.setup_managers(existing_db)
        
        # Создание GUI
        self.setup_ui()
        
        # Настройка системного трея
        self.setup_tray()
        
        # Таймер для проверки буфера обмена
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)  # Проверка каждую секунду

    def setup_managers(self, existing_db=None):
        """
        Инициализация всех менеджеров.
        """
        if existing_db:
            self.db = existing_db
            self.crypto = existing_db.crypto
            self.window_manager = WindowManager()
            return
            
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, 'passwords.db')
        
        # Создаем временный CryptoManager для инициализации базы данных
        temp_crypto = CryptoManager("temp")
        temp_db = DatabaseManager(db_path, temp_crypto)
        
        # Проверяем, есть ли настройки в базе данных
        with temp_db.Session() as session:
            settings = session.query(Settings).first()
            is_first_run = settings is None
        
        # Запрашиваем мастер-пароль при запуске
        login_dialog = LoginDialog(self)
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
            
        master_password = login_dialog.password_input.text()
        totp_code = login_dialog.totp_input.text()
        
        if is_first_run:
            # Первый запуск - создаем настройки
            self.crypto = CryptoManager(master_password)
            self.db = DatabaseManager(db_path, self.crypto)
            
            with self.db.Session() as session:
                session.add(Settings(key="master_password_hash", value=base64.b64encode(self.crypto.key).decode()))
                session.add(Settings(key="salt", value=base64.b64encode(self.crypto.salt).decode()))
                session.add(Settings(key="two_factor_enabled", value="false"))
                session.commit()
        else:
            # Получаем значения salt и master_password_hash из отдельных записей
            salt = base64.b64decode(temp_db.get_setting("salt"))
            stored_key = base64.b64decode(temp_db.get_setting("master_password_hash"))
            
            # Создаем CryptoManager с сохраненной солью
            self.crypto = CryptoManager(master_password, salt)
            
            if self.crypto.key != stored_key:
                QMessageBox.critical(self, "Ошибка", "Неверный мастер-пароль")
                sys.exit(1)
            
            self.db = DatabaseManager(db_path, self.crypto)
        
        self.window_manager = WindowManager()

    def setup_ui(self):
        """
        Настройка пользовательского интерфейса.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Создаем вкладки
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Вкладка паролей
        passwords_tab = QWidget()
        passwords_layout = QVBoxLayout(passwords_tab)
        
        # Поиск
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию, тегам или сайту...")
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("Поиск")
        search_layout.addWidget(self.search_button)
        passwords_layout.addLayout(search_layout)
        
        # Список паролей
        self.password_list = QListWidget()
        passwords_layout.addWidget(self.password_list)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.edit_button = QPushButton("Изменить")
        self.delete_button = QPushButton("Удалить")
        self.copy_button = QPushButton("Копировать")
        self.autotype_button = QPushButton("Автоввод")
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.copy_button)
        buttons_layout.addWidget(self.autotype_button)
        passwords_layout.addLayout(buttons_layout)
        
        tabs.addTab(passwords_tab, "Пароли")
        
        # Вкладка настроек
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # Настройки безопасности
        settings_layout.addWidget(QLabel("Настройки безопасности"))
        
        self.change_master_button = QPushButton("Сменить мастер-пароль")
        settings_layout.addWidget(self.change_master_button)
        
        self.enable_2fa = QCheckBox("Включить двухфакторную аутентификацию")
        settings_layout.addWidget(self.enable_2fa)
        
        # Настройки автоочистки
        settings_layout.addWidget(QLabel("Автоматическая очистка буфера обмена (секунд):"))
        self.clipboard_timeout = QSpinBox()
        self.clipboard_timeout.setRange(5, 300)
        self.clipboard_timeout.setValue(30)
        settings_layout.addWidget(self.clipboard_timeout)
        
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "Настройки")
        
        # Подключаем сигналы
        self.connect_signals()
        
        # Обновляем список паролей
        self.update_password_list()

    def setup_tray(self):
        """
        Настройка иконки в системном трее.
        """
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon.fromTheme("dialog-password"))  # Используем системную иконку
        self.tray_icon.setToolTip("Passo")
        
        # Создаем контекстное меню
        tray_menu = QMenu()
        
        show_action = QAction("Показать", self)
        quit_action = QAction("Выход", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def connect_signals(self):
        """
        Подключение сигналов к слотам.
        """
        self.search_input.textChanged.connect(self.update_password_list)
        self.search_button.clicked.connect(self.update_password_list)
        
        self.add_button.clicked.connect(self.add_password)
        self.edit_button.clicked.connect(self.edit_password)
        self.delete_button.clicked.connect(self.delete_password)
        self.copy_button.clicked.connect(self.copy_password)
        self.autotype_button.clicked.connect(self.autotype_password)
        
        self.change_master_button.clicked.connect(self.change_master_password)
        self.enable_2fa.stateChanged.connect(self.toggle_2fa)
        
        self.clipboard_timeout.valueChanged.connect(self.update_clipboard_timeout)

    def update_password_list(self):
        """
        Обновление списка паролей.
        """
        search_query = self.search_input.text()
        passwords = self.db.search_passwords(query=search_query)
        
        self.password_list.clear()
        for password in passwords:
            self.password_list.addItem(f"{password.title} ({password.website})")

    def add_password(self):
        """
        Добавление нового пароля.
        """
        # Диалог генерации пароля
        gen_dialog = PasswordGeneratorDialog(self)
        if gen_dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Запрашиваем дополнительную информацию
        title, ok = QInputDialog.getText(self, "Новый пароль", "Название:")
        if not ok or not title:
            return
            
        website, ok = QInputDialog.getText(self, "Новый пароль", "Сайт:")
        if not ok:
            website = ""
            
        tags, ok = QInputDialog.getText(self, "Новый пароль", "Теги (через запятую):")
        if not ok:
            tags = ""
            
        # Добавляем пароль в базу
        self.db.add_password(
            title=title,
            password=gen_dialog.result.text(),
            website=website,
            tags=tags.split(",") if tags else None,
            association_words=[w.text() for w in gen_dialog.word_inputs if w.text()]
        )
        
        self.update_password_list()

    def edit_password(self):
        """
        Редактирование существующего пароля.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
        
        # Получаем название пароля из текста элемента списка
        title = current_item.text().split(" (")[0]
        
        # Ищем пароль в базе данных
        passwords = self.db.search_passwords(query=title)
        if not passwords:
            QMessageBox.warning(self, "Ошибка", "Пароль не найден в базе данных")
            return
        
        # Получаем полную информацию о пароле
        password_info = self.db.get_password(passwords[0].id)
        if not password_info:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить информацию о пароле")
            return
        
        # Создаем диалог редактирования
        dialog = EditPasswordDialog({
            'title': password_info.title,
            'password': self.crypto.decrypt(password_info.encrypted_password),
            'website': password_info.website,
            'tags': [tag.name for tag in password_info.tags],
            'notes': password_info.notes
        }, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Получаем обновленные данные
                updated_data = dialog.get_password_data()
                
                # Обновляем пароль в базе данных
                success = self.db.update_password(
                    password_info.id,
                    password=updated_data['password'],
                    title=updated_data['title'],
                    website=updated_data['website'],
                    tags=updated_data['tags'],
                    notes=updated_data['notes']
                )
                
                if success:
                    # Обновляем список паролей
                    self.update_password_list()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось обновить пароль")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при обновлении пароля: {str(e)}")

    def delete_password(self):
        """
        Удаление пароля.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
        
        # Получаем название пароля из текста элемента списка
        title = current_item.text().split(" (")[0]
        
        # Ищем пароль в базе данных
        passwords = self.db.search_passwords(query=title)
        if not passwords:
            QMessageBox.warning(self, "Ошибка", "Пароль не найден в базе данных")
            return
        
        # Получаем полную информацию о пароле
        password_info = self.db.get_password(passwords[0].id)
        if not password_info:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить информацию о пароле")
            return
        
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы действительно хотите удалить пароль для {password_info.title}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Удаляем пароль
                success = self.db.delete_password(password_info.id)
                
                if success:
                    # Обновляем список паролей
                    self.update_password_list()
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось удалить пароль")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при удалении пароля: {str(e)}")

    def copy_password(self):
        """
        Копирование пароля в буфер обмена.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
        
        # Получаем название пароля из текста элемента списка
        title = current_item.text().split(" (")[0]
        
        # Ищем пароль в базе данных
        passwords = self.db.search_passwords(query=title)
        if not passwords:
            QMessageBox.warning(self, "Ошибка", "Пароль не найден в базе данных")
            return
        
        # Получаем полную информацию о пароле
        password_info = self.db.get_password(passwords[0].id)
        if not password_info:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить информацию о пароле")
            return
        
        # Копируем пароль в буфер обмена
        decrypted_password = self.crypto.decrypt(password_info.encrypted_password)
        self.window_manager.copy_to_clipboard(decrypted_password)
        
        # Логируем использование
        window_info = self.window_manager.get_active_window_info()
        self.db.log_password_usage(
            password_info.id,
            window_info['class'],
            window_info['name']
        )
        
        # Показываем уведомление
        self.tray_icon.showMessage(
            "Пароль скопирован",
            f"Пароль для {password_info.title} скопирован в буфер обмена",
            QSystemTrayIcon.MessageIcon.Information,
            2000  # Показываем на 2 секунды
        )

    def autotype_password(self):
        """
        Автоматический ввод пароля в активное окно.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
        
        # Получаем название пароля из текста элемента списка
        title = current_item.text().split(" (")[0]
        
        # Ищем пароль в базе данных
        passwords = self.db.search_passwords(query=title)
        if not passwords:
            QMessageBox.warning(self, "Ошибка", "Пароль не найден в базе данных")
            return
        
        # Получаем полную информацию о пароле
        password_info = self.db.get_password(passwords[0].id)
        if not password_info:
            QMessageBox.warning(self, "Ошибка", "Не удалось получить информацию о пароле")
            return
        
        # Запрашиваем подтверждение
        reply = QMessageBox.information(
            self,
            "Автоввод пароля",
            "Нажмите OK, когда будете готовы к вводу пароля. У вас будет 3 секунды, чтобы переключиться на нужное окно.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok
        )
        
        if reply == QMessageBox.StandardButton.Ok:
            # Даем пользователю 3 секунды на переключение окна
            QTimer.singleShot(3000, lambda: self._perform_autotype(password_info))

    def _perform_autotype(self, password_info):
        """
        Выполняет автоввод пароля.
        """
        try:
            decrypted_password = self.crypto.decrypt(password_info.encrypted_password)
            self.window_manager.type_text(decrypted_password)
            
            # Логируем использование
            window_info = self.window_manager.get_active_window_info()
            self.db.log_password_usage(
                password_info.id,
                window_info['class'],
                window_info['name']
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при вводе пароля: {str(e)}")

    def change_master_password(self):
        """
        Смена мастер-пароля.
        """
        old_password, ok = QInputDialog.getText(
            self, "Смена пароля",
            "Введите текущий мастер-пароль:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return
            
        new_password, ok = QInputDialog.getText(
            self, "Смена пароля",
            "Введите новый мастер-пароль:",
            QLineEdit.EchoMode.Password
        )
        if not ok:
            return
            
        if self.crypto.change_master_password(old_password, new_password):
            QMessageBox.information(self, "Успех", "Мастер-пароль успешно изменен")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить мастер-пароль")

    def toggle_2fa(self, state):
        """
        Включение/выключение двухфакторной аутентификации.
        """
        if state:
            # Генерируем новый секрет для TOTP
            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            
            # Показываем QR-код и секрет пользователю
            QMessageBox.information(
                self, "2FA",
                f"Секретный ключ: {secret}\n"
                f"Добавьте его в ваше приложение для 2FA"
            )
            
            # TODO: Save 2FA settings
        else:
            # Отключаем 2FA после подтверждения
            reply = QMessageBox.question(
                self, "Отключение 2FA",
                "Вы уверены, что хотите отключить двухфакторную аутентификацию?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # TODO: Disable and clear 2FA settings
                QMessageBox.information(self, "2FA", "Двухфакторная аутентификация отключена")

    def update_clipboard_timeout(self, value):
        """
        Обновление таймаута очистки буфера обмена.
        """
        self.window_manager.clipboard_timeout = value

    def check_clipboard(self):
        """
        Проверка необходимости очистки буфера обмена.
        """
        self.window_manager._check_clipboard_timeout()

    def closeEvent(self, event):
        """
        Обработка закрытия окна.
        """
        if hasattr(self, '_force_quit'):
            # Если установлен флаг принудительного закрытия, закрываем приложение
            event.accept()
            # Очищаем ресурсы перед закрытием
            self.cleanup_resources()
        else:
            # Иначе сворачиваем в трей
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Passo",
                "Приложение продолжает работать в фоне",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def cleanup_resources(self):
        """
        Очистка ресурсов перед закрытием приложения.
        """
        # Очищаем буфер обмена
        self.window_manager.clear_clipboard()
        # Закрываем соединение с базой данных
        self.db.Session.close_all()

    def quit_application(self):
        """
        Полное закрытие приложения.
        """
        reply = QMessageBox.question(
            self, "Подтверждение выхода",
            "Вы уверены, что хотите закрыть Passo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Устанавливаем флаг принудительного закрытия
            self._force_quit = True
            # Закрываем окно
            self.close()
            # Завершаем приложение
            QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 