from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Base, Password, Tag, UsageHistory, Settings
from crypto import CryptoManager

class DatabaseManager:
    def __init__(self, db_path: str, crypto_manager: CryptoManager):
        """
        Инициализация менеджера базы данных.
        
        :param db_path: Путь к файлу базы данных
        :param crypto_manager: Экземпляр CryptoManager для шифрования
        """
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.crypto = crypto_manager

    def add_password(self, title: str, password: str, website: str = None,
                    notes: str = None, tags: List[str] = None,
                    association_words: List[str] = None) -> Password:
        """
        Добавление нового пароля в базу данных.
        """
        with self.Session() as session:
            # Шифруем пароль
            encrypted_password = self.crypto.encrypt(password)
            
            # Создаем запись пароля
            password_entry = Password(
                title=title,
                encrypted_password=encrypted_password,
                website=website,
                notes=notes,
                association_words=",".join(association_words) if association_words else None,
                creation_date=datetime.utcnow()
            )
            
            # Добавляем теги
            if tags:
                for tag_name in tags:
                    tag = session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                    password_entry.tags.append(tag)
            
            session.add(password_entry)
            session.commit()
            return password_entry

    def get_password(self, password_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение пароля по ID.
        """
        with self.Session() as session:
            password = session.query(Password).filter_by(id=password_id).first()
            if not password:
                return None
            
            return {
                'id': password.id,
                'title': password.title,
                'password': self.crypto.decrypt(password.encrypted_password),
                'website': password.website,
                'notes': password.notes,
                'association_words': password.association_words.split(',') if password.association_words else [],
                'tags': [tag.name for tag in password.tags],
                'creation_date': password.creation_date,
                'last_used': password.last_used
            }

    def update_password(self, password_id: int, **kwargs) -> bool:
        """
        Обновление существующего пароля.
        """
        with self.Session() as session:
            password = session.query(Password).filter_by(id=password_id).first()
            if not password:
                return False
            
            if 'password' in kwargs:
                kwargs['encrypted_password'] = self.crypto.encrypt(kwargs.pop('password'))
            
            if 'tags' in kwargs:
                password.tags.clear()
                for tag_name in kwargs['tags']:
                    tag = session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                    password.tags.append(tag)
                kwargs.pop('tags')
            
            if 'association_words' in kwargs:
                kwargs['association_words'] = ','.join(kwargs['association_words'])
            
            for key, value in kwargs.items():
                setattr(password, key, value)
            
            session.commit()
            return True

    def delete_password(self, password_id: int) -> bool:
        """
        Удаление пароля.
        """
        with self.Session() as session:
            password = session.query(Password).filter_by(id=password_id).first()
            if not password:
                return False
            
            session.delete(password)
            session.commit()
            return True

    def search_passwords(self, query: str = None, tags: List[str] = None,
                        website: str = None) -> List[Dict[str, Any]]:
        """
        Поиск паролей по различным критериям.
        """
        with self.Session() as session:
            q = session.query(Password)
            
            if query:
                q = q.filter(Password.title.ilike(f'%{query}%'))
            
            if website:
                q = q.filter(Password.website.ilike(f'%{website}%'))
            
            if tags:
                for tag in tags:
                    q = q.filter(Password.tags.any(Tag.name == tag))
            
            passwords = q.all()
            
            return [{
                'id': p.id,
                'title': p.title,
                'website': p.website,
                'tags': [tag.name for tag in p.tags],
                'creation_date': p.creation_date,
                'last_used': p.last_used,
                'is_favorite': p.is_favorite
            } for p in passwords]

    def log_password_usage(self, password_id: int, application_name: str,
                          window_title: str = None) -> None:
        """
        Логирование использования пароля.
        """
        with self.Session() as session:
            password = session.query(Password).filter_by(id=password_id).first()
            if password:
                usage = UsageHistory(
                    password_id=password_id,
                    application_name=application_name,
                    window_title=window_title,
                    timestamp=datetime.utcnow()
                )
                password.last_used = datetime.utcnow()
                session.add(usage)
                session.commit()

    def get_usage_history(self, password_id: Optional[int] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Получение истории использования паролей.
        """
        with self.Session() as session:
            q = session.query(UsageHistory)
            
            if password_id:
                q = q.filter_by(password_id=password_id)
            
            if start_date:
                q = q.filter(UsageHistory.timestamp >= start_date)
            
            if end_date:
                q = q.filter(UsageHistory.timestamp <= end_date)
            
            history = q.order_by(UsageHistory.timestamp.desc()).all()
            
            return [{
                'password_id': h.password_id,
                'application_name': h.application_name,
                'window_title': h.window_title,
                'timestamp': h.timestamp
            } for h in history]

    def toggle_favorite(self, password_id: int) -> bool:
        """
        Переключение статуса "избранное" для пароля.
        """
        with self.Session() as session:
            password = session.query(Password).filter_by(id=password_id).first()
            if not password:
                return False
            
            password.is_favorite = not password.is_favorite
            session.commit()
            return True

    def get_all_tags(self) -> List[str]:
        """
        Получение списка всех тегов.
        """
        with self.Session() as session:
            tags = session.query(Tag).all()
            return [tag.name for tag in tags]

    def cleanup_unused_tags(self) -> int:
        """
        Удаление неиспользуемых тегов.
        """
        with self.Session() as session:
            unused_tags = session.query(Tag).filter(~Tag.passwords.any()).all()
            count = len(unused_tags)
            for tag in unused_tags:
                session.delete(tag)
            session.commit()
            return count 