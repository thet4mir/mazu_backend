from openai import OpenAI
from datetime import datetime, timedelta
import os
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, HTTPException, Depends, status, Path
from database import engine, SessionLocal
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, and_
from typing import Annotated
from models import Session as SessionModel, User, Message as MessageModel, Base, SessionType
from schema import QueryRequest, complainAnswer, GoogleAuth, Token, RefreshTokenRequest, Session, Message as MessageSchema, MessageCreate, sessionCreate, LoginRequest, Complain
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from typing import List
from uuid import UUID
from dotenv import load_dotenv
from rag import Rag
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()
origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
RAG = Rag()
RAG.setup()

db_dependency = Annotated[Session, Depends(get_db)]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper functions
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now() + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(db: db_dependency, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        print(f"{token} token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    print(email)
    user = db.query(User).filter(User.email == email).first()
    print(user)
    if user is None:
        raise credentials_exception
    return user

@app.post("/auth/email", response_model=Token)
async def email_auth(db: db_dependency, form_data: LoginRequest):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.email},  # You can include more user data here
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=refresh_token_expires
    )
    print(user)
    print(access_token)
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token, "user": {"email": user.email, "name": user.name, "is_admin": user.is_admin}}


@app.get("/auth/verify")
async def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify if the provided JWT token is valid.
    Returns basic user information if valid.
    """
    return {
        "user": {
            "email": current_user.email,
            "name": current_user.name,
            "is_admin": current_user.is_admin,
        },
        "status": "authenticated"
    }


@app.post("/auth/google", response_model=Token)
async def google_auth(googleAuth: GoogleAuth, db: db_dependency):
    try:
        idinfo = id_token.verify_oauth2_token(
            googleAuth.id_token,
            grequests.Request(),
            GOOGLE_CLIENT_ID
        )
        # Get or create user in your database
        user_email = idinfo['email']
        name = idinfo['name']
        print(user_email)
        print(db)
        try:
            user = get_or_create_user(
                {'email': user_email, 'name': name},
                db
            )
        except Exception as e:
            print(e)

        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        access_token = create_access_token(
            data={"sub": user_email},  # You can include more user data here
            expires_delta=access_token_expires
        )

        refresh_token = create_refresh_token(
            data={"sub": user_email},
            expires_delta=refresh_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token, "user": {"email": user.email, "name": user.name, "is_admin": user.is_admin}}
    
    except Exception:
        print("error")
        raise HTTPException(status_code=401, detail="Facebook verification failed")


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(
            request.refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": request.refresh_token  # Same refresh token
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

@app.post("/complain/list", response_model=List[Complain])
async def complainList(db: db_dependency, current_user: User = Depends(get_current_user)):
    try:
        first_message_subquery = (
            db.query(
                MessageModel.session_id,
                func.min(MessageModel.timestamp).label("min_timestamp")
            )
            .join(Session, MessageModel.session_id == Session.id)
            .filter(Session.type == SessionType.COMPLAIN)
            .group_by(MessageModel.session_id)
            .subquery()
        )

        # Alias for joining message again
        MessageAlias = aliased(MessageModel)

        # Final query to get details of the first message per session
        results = (
            db.query(
                MessageAlias.id,
                MessageAlias.session_id,
                User.email,
                User.name,
                MessageAlias.text,
            )
            .join(Session, MessageAlias.session_id == Session.id)
            .join(User, Session.user_id == User.id)
            .join(
                first_message_subquery,
                and_(
                    MessageAlias.session_id == first_message_subquery.c.session_id,
                    MessageAlias.timestamp == first_message_subquery.c.min_timestamp
                )
            )
            .all()
        )
        return results
    
    except Exception as e:
        print(e)
        return []


@app.post("/complain/answer")
async def generateAsnwer(request: QueryRequest, _: User = Depends(get_current_user)):
    try:
        return StreamingResponse(
            RAG.generate(query=request.query),
            media_type="text/event-stream",
        )
    except Exception as e:
        print(f"error from send{e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create message"
        )

@app.post("/session/list", response_model=List[Session])
async def sessionList(db: db_dependency, current_user: User = Depends(get_current_user)):
    try:
        sessions = db.query(SessionModel).filter(SessionModel.user_id == current_user.id).all()
        print(sessions)
        return sessions
    except Exception as e:
        print(e)
        return []


@app.get("/message/list/{session_id}", response_model=List)
async def sessionList(db: db_dependency, _: None = Depends(get_current_user), session_id: UUID = Path(..., description="Session ID to filter messages by")):
    try:
        response = []
        messages = db.query(MessageModel).filter(MessageModel.session_id == session_id).all()

        for message in messages:
            if message.is_from_user:
                response.append({"user": message.text})
            else:
                response.append({"system": message.text})
        print(response)
        return response
    
    except Exception as e:
        print(e)
        return []
    


@app.post("/session/create", response_model=str)
async def sessionCreateRequest(message: sessionCreate, db: db_dependency, current_user: User = Depends(get_current_user)):
    try:
        new_session = SessionModel(user_id=current_user.id, title=message.message)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
    except Exception as e:
        print(e)

    return str(new_session.id)


@app.post("/message/send")
async def messageCreate(messageData: MessageCreate, db: db_dependency, current_user: User = Depends(get_current_user)):
    try:
        
        answer = RAG.retriever(query=messageData.text)

        return {"status": "success", "message": answer}
    except Exception as e:
        print(f"error from send{e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create message"
        )


@app.post("/voice/send")
async def voicemessage(request: sessionCreate, current_user: User = Depends(get_current_user)):
    try:
        return StreamingResponse(
            RAG.retriever(query=request.message),
            media_type="text/event-stream",
        )
    except Exception as e:
        print(f"error from send{e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create message"
        )


def get_or_create_user(user_data: dict, db: Session):
    print("function is called!")
    """Get or create a user in the database"""
    user = db.query(User).filter(User.email == user_data['email']).first()
    
    if not user:
        user = User(
            email=user_data['email'],
            name=user_data.get('name'),
            started_at=datetime.now()
        )
        print(user)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user
