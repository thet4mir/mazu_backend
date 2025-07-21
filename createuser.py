from database import SessionLocal  # your SQLAlchemy session
from models import User
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

user = User(
    id=uuid.uuid4(),
    email="tamiraatsogbayar@gmail.com",
    name="Tamir Tsogbayar",
    password=pwd_context.hash("tamir1022"),
    is_admin=True,
    is_staff=True
)

db.add(user)
db.commit()
