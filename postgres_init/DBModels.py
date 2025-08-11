from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

# Ассоциативная таблица для связи многие-ко-многим между организацией и телефонами
organization_phones = Table(
    'organization_phones',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True),
    Column('phone_id', Integer, ForeignKey('phones.id'), primary_key=True)
)

# Ассоциативная таблица для связи многие-ко-многим между организацией и деятельностью
organization_activities = Table(
    'organization_activities',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organizations.id'), primary_key=True),
    Column('activity_id', Integer, ForeignKey('activities.id'), primary_key=True)
)


class Building(Base):
    """Модель для здания"""
    __tablename__ = 'buildings'

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False, comment="Адрес здания")
    latitude = Column(Float, nullable=False, comment="Широта")
    longitude = Column(Float, nullable=False, comment="Долгота")

    # Обратная связь с организациями
    organizations = relationship("Organization", back_populates="building")


class Phone(Base):
    """Модель для телефона"""
    __tablename__ = 'phones'

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, nullable=False, unique=True, comment="Номер телефона")

    # Связь многие-ко-многим с организациями
    organizations = relationship("Organization", secondary=organization_phones, back_populates="phones")


class Activity(Base):
    """Модель для деятельности"""
    __tablename__ = 'activities'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, comment="Название деятельности")
    parent_id = Column(Integer, ForeignKey('activities.id'), nullable=True, comment="ID родительской деятельности")

    # Самоссылающаяся связь для древовидной структуры
    parent = relationship("Activity", remote_side=[id], back_populates="children")
    children = relationship("Activity", back_populates="parent")

    # Связь многие-ко-многим с организациями
    organizations = relationship("Organization", secondary=organization_activities, back_populates="activities")


class Organization(Base):
    """Модель для организации"""
    __tablename__ = 'organizations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, comment="Название организации")
    building_id = Column(Integer, ForeignKey('buildings.id'), nullable=False, comment="ID здания")

    # Связи
    building = relationship("Building", back_populates="organizations")
    phones = relationship("Phone", secondary=organization_phones, back_populates="organizations")
    activities = relationship("Activity", secondary=organization_activities, back_populates="organizations")
