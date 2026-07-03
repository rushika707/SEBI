import jwt
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import List

from app.core.database import get_db
from app.core.config import settings
from app.models.models import User, Organization
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login-form")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def check_role(roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action forbidden for role '{current_user.role}'. Required roles: {roles}"
            )
        return current_user
    return role_checker

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check/Create Organization if organization_id is not specified
    org_id = user_in.organization_id
    if not org_id:
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Default Intermediary")
            db.add(org)
            db.commit()
            db.refresh(org)
        org_id = org.id

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        password_hash=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role,
        organization_id=org_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    # Simple check & seed if DB is completely empty
    seed_users(db)

    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(data={"sub": user.email})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

# OAuth2 compatible login for OpenAPI docs
from fastapi.security import OAuth2PasswordRequestForm
@router.post("/login-form", response_model=Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    seed_users(db)
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    token = create_access_token(data={"sub": user.email})
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

def seed_users(db: Session):
    # Inserts a default organization and user for testing
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="SEBI Intermediary Corp")
        db.add(org)
        db.commit()
        db.refresh(org)
    
    user = db.query(User).filter(User.email == "compliance@sebicopilot.com").first()
    if not user:
        hashed_pw = get_password_hash("password")
        user = User(
            email="compliance@sebicopilot.com",
            password_hash=hashed_pw,
            full_name="Compliance Officer Primary",
            role="Compliance Officer",
            organization_id=org.id
        )
        db.add(user)
        
        # Add a default auditor user
        auditor_pw = get_password_hash("password")
        auditor = User(
            email="auditor@sebicopilot.com",
            password_hash=auditor_pw,
            full_name="External Auditor Agent",
            role="Auditor",
            organization_id=org.id
        )
        db.add(auditor)
        db.commit()
