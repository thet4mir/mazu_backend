from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from database import Base
from enum import Enum as PyEnum
from sqlalchemy import Enum


class SessionType(PyEnum):
    CHAT = 'chat'
    COMPLAIN = 'complain'

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(Text)
    password = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_staff = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey('department.id'), nullable=True)
    started_at = Column(DateTime, default=datetime.now())

class Organization(Base):
    __tablename__ = "organization"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text)
    started_at = Column(DateTime, default=datetime.now())

class Department(Base):
    __tablename__ = "department"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'))
    started_at = Column(DateTime, default=datetime.now())

class Context(Base):
    __tablename__ = "context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text)
    content = Column(Text)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organization.id'))
    department_id = Column(UUID(as_uuid=True), ForeignKey('department.id'))
    started_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now())


class Categories(Base):
    __tablename__ = "categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text)
    name = Column(Text)
    started_at = Column(DateTime, default=datetime.now())

class Businesses(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(UUID(as_uuid=True), ForeignKey('categories.id'))
    description = Column(Text)
    content = Column(Text)
    location = Column(Text)
    started_at = Column(DateTime, default=datetime.now())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    type = Column(Enum(SessionType, name="sessiontype"), nullable=False, default=SessionType.CHAT)
    title = Column(Text, nullable=False)
    started_at = Column(DateTime, default=datetime.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'))
    text = Column(Text, nullable=False)
    is_from_user = Column(Boolean, nullable=False)  # True=user, False=bot
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    timestamp = Column(DateTime, default=datetime.now())

