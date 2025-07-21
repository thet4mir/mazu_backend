# schemas.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class QueryRequest(BaseModel):
    query: str
    
class complainAnswer(BaseModel):
    session_id: UUID
    text: str

class Complain(BaseModel):
    id: UUID
    session_id: UUID
    email: UUID 
    name: UUID 
    text: str

class LoginRequest(BaseModel):
    username: str
    password: str

class sessionCreate(BaseModel):
    message: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Facebook login auth
class GoogleAuth(BaseModel):
    id_token: str

# User table
class UserBase(BaseModel):
    email: str
    name: str
    is_admin: bool

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: UUID
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    user: UserBase

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
