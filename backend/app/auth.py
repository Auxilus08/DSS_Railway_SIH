"""
Authentication system for Railway Traffic Management API
JWT-based authentication for controllers
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from .db import get_session
from .models import Controller
from .schemas import TokenData

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "railway-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRES_IN", "3600")) // 60

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    if not hashed_password:
        return False
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id: str = payload.get("sub")
        controller_id: int = payload.get("controller_id")
        
        if employee_id is None:
            return None
            
        token_data = TokenData(employee_id=employee_id, controller_id=controller_id)
        return token_data
    except JWTError:
        return None


def authenticate_controller(db: Session, employee_id: str, password: str) -> Optional[Controller]:
    """Authenticate controller with employee_id and password"""
    controller = db.query(Controller).filter(
        Controller.employee_id == employee_id,
        Controller.active == True
    ).first()
    
    if not controller:
        return None
    
    # Check if controller has a password hash
    if not controller.password_hash:
        return None
    
    # Verify password
    if not verify_password(password, controller.password_hash):
        return None
    
    return controller


async def get_current_controller(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
) -> Controller:
    """Get current authenticated controller"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    controller = db.query(Controller).filter(
        Controller.employee_id == token_data.employee_id,
        Controller.active == True
    ).first()
    
    if controller is None:
        raise credentials_exception
    
    return controller


async def get_current_active_controller(
    current_controller: Controller = Depends(get_current_controller)
) -> Controller:
    """Get current active controller"""
    if not current_controller.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive controller"
        )
    return current_controller


# Alias for compatibility with existing code
async def get_current_user(
    current_controller: Controller = Depends(get_current_active_controller)
) -> Controller:
    """Get current authenticated user (controller) - alias for compatibility"""
    return current_controller


def check_controller_permissions(
    controller: Controller,
    required_sections: Optional[list] = None,
    min_auth_level: str = "operator"
) -> bool:
    """Check if controller has required permissions"""
    auth_levels = {"operator": 1, "supervisor": 2, "manager": 3, "admin": 4}
    
    controller_level = auth_levels.get(controller.auth_level.value, 0)
    required_level = auth_levels.get(min_auth_level, 1)
    
    if controller_level < required_level:
        return False
    
    if required_sections and controller.section_responsibility:
        # Check if controller has responsibility for required sections
        if not any(section in controller.section_responsibility for section in required_sections):
            return False
    
    return True


class PermissionChecker:
    """Dependency class for checking permissions"""
    
    def __init__(self, min_auth_level: str = "operator", required_sections: Optional[list] = None):
        self.min_auth_level = min_auth_level
        self.required_sections = required_sections
    
    def __call__(self, controller: Controller = Depends(get_current_active_controller)):
        if not check_controller_permissions(
            controller, 
            self.required_sections, 
            self.min_auth_level
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return controller


# Common permission dependencies
require_operator = PermissionChecker("operator")
require_supervisor = PermissionChecker("supervisor")
require_manager = PermissionChecker("manager")
require_admin = PermissionChecker("admin")


def create_demo_passwords(db: Session):
    """Create demo passwords for existing controllers (development only)"""
    controllers = db.query(Controller).filter(Controller.active == True).all()
    
    demo_credentials = {}
    for controller in controllers:
        demo_password = f"password_{controller.employee_id}"
        demo_credentials[controller.employee_id] = demo_password
    
    return demo_credentials