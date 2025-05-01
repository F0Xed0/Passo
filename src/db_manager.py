import os
from datetime import datetime, timezone
from typing import List, Optional, Dict
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import Session, sessionmaker
from models import Base, Password, Tag, UsageHistory, Settings
from crypto import CryptoManager

class DatabaseManager:
    def __init__(self, db_path: str, crypto: CryptoManager):
        """
        Инициализация менеджера базы данных.
        """
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.crypto = crypto

    def add_password(self, title: str, password: str, website: str = "", notes: str = "",
                    tags: List[str] = None, association_words: List[str] = None) -> Optional[Password]:
        """
        Добавление нового пароля.
        """
        tags = tags or []
        association_words = association_words or []
        
        with self.Session() as session:
            # Создаем новый пароль
            new_password = Password(
                title=title,
                encrypted_password=self.crypto.encrypt(password),
                website=website,
                notes=notes,
                creation_date=datetime.now(timezone.utc),
                association_words=",".join(association_words)
            )
            
            session.add(new_password)
            
            # Добавляем теги
            for tag_name in set(tags):  # Используем set для удаления дубликатов
                tag = session.scalars(select(Tag).filter_by(name=tag_name)).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                new_password.tags.append(tag)
            
            session.commit()
            
            # Загружаем связанные объекты
            session.refresh(new_password)
            for tag in new_password.tags:
                session.refresh(tag)
            
            return new_password

    def get_password(self, password_id: int) -> Optional[Password]:
        """
        Получение пароля по ID.
        """
        with self.Session() as session:
            password = session.get(Password, password_id)
            if password:
                # Загружаем связанные объекты
                session.refresh(password)
                for tag in password.tags:
                    session.refresh(tag)
            return password

    def update_password(self, password_id: int, **kwargs) -> bool:
        """
        Обновление пароля.
        """
        with self.Session() as session:
            password = session.get(Password, password_id)
            if not password:
                return False
            
            # Обновляем поля
            for key, value in kwargs.items():
                if key == 'password':
                    password.encrypted_password = self.crypto.encrypt(value)
                elif key == 'tags':
                    password.tags.clear()
                    for tag_name in set(value):  # Используем set для удаления дубликатов
                        tag = session.scalars(select(Tag).filter_by(name=tag_name)).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            session.add(tag)
                        password.tags.append(tag)
                elif key == 'association_words':
                    password.association_words = ",".join(value)
                elif hasattr(password, key):
                    setattr(password, key, value)
            
            session.commit()
            
            # Загружаем связанные объекты
            session.refresh(password)
            for tag in password.tags:
                session.refresh(tag)
            
            return True

    def delete_password(self, password_id: int) -> bool:
        """
        Удаление пароля.
        """
        with self.Session() as session:
            password = session.get(Password, password_id)
            if not password:
                return False
            
            # Сохраняем теги для проверки
            tags_to_check = [tag.id for tag in password.tags]
            
            # Удаляем пароль
            session.delete(password)
            session.commit()
            
            # Удаляем неиспользуемые теги
            for tag_id in tags_to_check:
                tag = session.get(Tag, tag_id)
                if tag and not tag.passwords:
                    session.delete(tag)
            
            session.commit()
            return True

    def search_passwords(self, query: str = "", tag: str = "") -> List[Password]:
        """
        Поиск паролей по запросу и/или тегу.
        """
        with self.Session() as session:
            stmt = select(Password)
            
            if query:
                stmt = stmt.filter(
                    (Password.title.ilike(f"%{query}%")) |
                    (Password.website.ilike(f"%{query}%")) |
                    (Password.notes.ilike(f"%{query}%")) |
                    (Password.association_words.ilike(f"%{query}%"))
                )
            
            if tag:
                stmt = stmt.join(Password.tags).filter(Tag.name == tag)
            
            passwords = session.scalars(stmt).all()
            
            # Загружаем связанные объекты
            for password in passwords:
                session.refresh(password)
                for tag in password.tags:
                    session.refresh(tag)
            
            return passwords

    def log_password_usage(self, password_id: int, app_name: str, window_title: str) -> bool:
        """
        Логирование использования пароля.
        """
        with self.Session() as session:
            password = session.get(Password, password_id)
            if not password:
                return False
            
            usage = UsageHistory(
                password_id=password_id,
                app_name=app_name,
                window_title=window_title,
                usage_date=datetime.now(timezone.utc)
            )
            
            password.last_used = usage.usage_date
            session.add(usage)
            session.commit()
            
            # Загружаем связанные объекты
            session.refresh(password)
            session.refresh(usage)
            
            return True

    def get_usage_history(self, password_id: Optional[int] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Получение истории использования паролей.
        """
        with self.Session() as session:
            stmt = select(UsageHistory)
            
            if password_id:
                stmt = stmt.filter_by(password_id=password_id)
            
            if start_date:
                stmt = stmt.filter(UsageHistory.usage_date >= start_date)
            
            if end_date:
                stmt = stmt.filter(UsageHistory.usage_date <= end_date)
            
            history = session.scalars(stmt.order_by(UsageHistory.usage_date.desc())).all()
            
            return [{
                'password_id': h.password_id,
                'app_name': h.app_name,
                'window_title': h.window_title,
                'usage_date': h.usage_date
            } for h in history]

    def toggle_favorite(self, password_id: int) -> bool:
        """
        Переключение избранного статуса пароля.
        """
        with self.Session() as session:
            password = session.get(Password, password_id)
            if not password:
                return False
            
            password.is_favorite = not password.is_favorite
            session.commit()
            session.refresh(password)
            return True

    def get_all_tags(self) -> List[str]:
        """
        Получение всех тегов.
        """
        with self.Session() as session:
            tags = session.scalars(select(Tag)).all()
            return [tag.name for tag in tags]

    def get_setting(self, key: str) -> str | None:
        """
        Получить значение настройки по ключу.
        """
        with self.Session() as session:
            setting = session.scalars(select(Settings).filter_by(key=key)).first()
            return setting.value if setting else None

    def set_setting(self, key: str, value: str):
        """
        Установить или обновить значение настройки по ключу.
        """
        with self.Session() as session:
            setting = session.scalars(select(Settings).filter_by(key=key)).first()
            if setting:
                setting.value = value
            else:
                setting = Settings(key=key, value=value)
                session.add(setting)
            session.commit()

    def delete_setting(self, key: str):
        """
        Удалить настройку по ключу.
        """
        with self.Session() as session:
            setting = session.scalars(select(Settings).filter_by(key=key)).first()
            if setting:
                session.delete(setting)
                session.commit() 