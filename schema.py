# schemas.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class sessionCreate(BaseModel):
    message: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str

# Facebook login auth
class GoogleAuth(BaseModel):
    id_token: str

# User table
class UserBase(BaseModel):
    email: str
    name: str

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID
    created_at: datetime

# session model
class SessionBase(BaseModel):
    user_id: UUID

class Session(SessionBase):
    id: UUID
    title: str
    started_at: datetime

    class Config:
        orm_mode = True

# message model
class MessageBase(BaseModel):
    text: str
    is_from_user: bool

class MessageCreate(BaseModel):
    session_id: UUID
    text: str

class Message(MessageBase):
    id: UUID
    timestamp: datetime

    class Config:
        orm_mode = True
