from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from typing import List

Base = declarative_base()

# Связующая таблица для тегов и паролей
password_tags = Table(
    "password_tags",
    Base.metadata,
    Column("password_id", Integer, ForeignKey("passwords.id")),
    Column("tag_id", Integer, ForeignKey("tags.id")),
)

class Password(Base):
    __tablename__ = "passwords"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    website = Column(String)
    notes = Column(String)
    association_words = Column(String)  # Хранение слов-ассоциаций
    creation_date = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_favorite = Column(Boolean, default=False)
    
    # Связи
    tags = relationship("Tag", secondary=password_tags, back_populates="passwords")
    usage_history = relationship("UsageHistory", back_populates="password")

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    passwords = relationship("Password", secondary=password_tags, back_populates="tags")

class UsageHistory(Base):
    __tablename__ = "usage_history"

    id = Column(Integer, primary_key=True)
    password_id = Column(Integer, ForeignKey("passwords.id"))
    application_name = Column(String, nullable=False)
    window_title = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    password = relationship("Password", back_populates="usage_history")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    master_password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String)
    clipboard_clear_timeout = Column(Integer, default=30)  # в секундах
    auto_lock_timeout = Column(Integer, default=300)  # в секундах 