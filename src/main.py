import sys
import os
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
from password_generator import PasswordGenerator
from window_manager import WindowManager

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Passo - Менеджер паролей")
        self.setMinimumSize(800, 600)
        
        # Инициализация менеджеров
        self.setup_managers()
        
        # Создание GUI
        self.setup_ui()
        
        # Настройка системного трея
        self.setup_tray()
        
        # Таймер для проверки буфера обмена
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)  # Проверка каждую секунду

    def setup_managers(self):
        """
        Инициализация всех менеджеров.
        """
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, 'passwords.db')
        
        # Запрашиваем мастер-пароль при запуске
        login_dialog = LoginDialog(self)
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)
            
        master_password = login_dialog.password_input.text()
        totp_code = login_dialog.totp_input.text()
        
        self.crypto = CryptoManager(master_password)
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
            self.password_list.addItem(f"{password['title']} ({password['website']})")

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
            
        # TODO: Implement password editing

    def delete_password(self):
        """
        Удаление пароля.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
            
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить этот пароль?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement password deletion
            self.update_password_list()

    def copy_password(self):
        """
        Копирование пароля в буфер обмена.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
            
        # TODO: Implement password copying

    def autotype_password(self):
        """
        Автоматический ввод пароля.
        """
        current_item = self.password_list.currentItem()
        if not current_item:
            return
            
        # TODO: Implement password auto-typing

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