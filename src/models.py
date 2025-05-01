from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from typing import List

Base = declarative_base()

# Таблица связи между паролями и тегами
password_tags = Table('password_tags', Base.metadata,
    Column('password_id', Integer, ForeignKey('passwords.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)

class Password(Base):
    __tablename__ = 'passwords'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    website = Column(String)
    notes = Column(String)
    creation_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_used = Column(DateTime)
    is_favorite = Column(Boolean, default=False)
    association_words = Column(String)
    
    tags = relationship('Tag', secondary=password_tags, back_populates='passwords')
    usage_history = relationship('UsageHistory', back_populates='password', cascade='all, delete-orphan')

class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    passwords = relationship('Password', secondary=password_tags, back_populates='tags')

class UsageHistory(Base):
    __tablename__ = 'usage_history'
    
    id = Column(Integer, primary_key=True)
    password_id = Column(Integer, ForeignKey('passwords.id', ondelete='CASCADE'))
    app_name = Column(String, nullable=False)
    window_title = Column(String)
    usage_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    password = relationship('Password', back_populates='usage_history')

class Settings(Base):
    __tablename__ = 'settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String) 