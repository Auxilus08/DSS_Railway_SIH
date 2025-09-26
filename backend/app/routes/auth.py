"""
Authentication API routes
Controller login and token management
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from ..db import get_session
from ..models import Controller
from ..schemas import LoginRequest, LoginResponse, ControllerResponse, APIResponse
from ..auth import (
    authenticate_controller, create_access_token, get_current_active_controller,
    ACCESS_TOKEN_EXPIRE_MINUTES, create_demo_passwords
)
from ..redis_client import get_redis, RedisClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login_controller(
    login_request: LoginRequest,
    db: Session = Depends(get_session),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Controller authentication endpoint
    
    Returns JWT access token for authenticated controllers
    
    Demo credentials:
    - employee_id: CTR001, password: password_CTR001
    - employee_id: CTR002, password: password_CTR002
    - etc.
    """
    
    try:
        # Authenticate controller
        controller = authenticate_controller(
            db, 
            login_request.employee_id, 
            login_request.password
        )
        
        if not controller:
            # Log failed login attempt
            logger.warning(f"Failed login attempt for employee_id: {login_request.employee_id}")
            
            # Cache failed attempt for rate limiting
            failed_key = f"failed_login:{login_request.employee_id}"
            await redis_client.increment_counter(failed_key, 3600)  # 1 hour TTL
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid employee ID or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if controller is active
        if not controller.active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Controller account is inactive"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": controller.employee_id,
                "controller_id": controller.id,
                "auth_level": controller.auth_level.value,
                "sections": controller.section_responsibility or []
            },
            expires_delta=access_token_expires
        )
        
        # Cache successful login
        login_key = f"login_success:{controller.employee_id}"
        await redis_client.set(login_key, {
            "controller_id": controller.id,
            "login_time": datetime.utcnow().isoformat(),
            "auth_level": controller.auth_level.value
        }, ttl=ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        # Log successful login
        logger.info(f"Successful login for controller: {controller.employee_id} ({controller.name})")
        
        # Build controller response
        controller_response = ControllerResponse(
            id=controller.id,
            name=controller.name,
            employee_id=controller.employee_id,
            auth_level=controller.auth_level.value,
            section_responsibility=controller.section_responsibility,
            active=controller.active,
            created_at=controller.created_at
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            controller=controller_response
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login for {login_request.employee_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during authentication"
        )


@router.post("/logout", response_model=APIResponse)
async def logout_controller(
    current_controller: Controller = Depends(get_current_active_controller),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Controller logout endpoint
    
    Invalidates the current session (clears cached login data)
    """
    
    try:
        # Clear cached login data
        login_key = f"login_success:{current_controller.employee_id}"
        await redis_client.delete(login_key)
        
        # Log logout
        logger.info(f"Controller logged out: {current_controller.employee_id} ({current_controller.name})")
        
        return APIResponse(
            success=True,
            message="Successfully logged out",
            data={
                "controller_id": current_controller.id,
                "employee_id": current_controller.employee_id
            }
        )
    
    except Exception as e:
        logger.error(f"Error during logout for {current_controller.employee_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during logout"
        )


@router.get("/me", response_model=ControllerResponse)
async def get_current_controller_info(
    current_controller: Controller = Depends(get_current_active_controller)
):
    """
    Get current authenticated controller information
    """
    
    return ControllerResponse(
        id=current_controller.id,
        name=current_controller.name,
        employee_id=current_controller.employee_id,
        auth_level=current_controller.auth_level.value,
        section_responsibility=current_controller.section_responsibility,
        active=current_controller.active,
        created_at=current_controller.created_at
    )


@router.get("/demo-credentials", response_model=APIResponse)
async def get_demo_credentials(
    db: Session = Depends(get_session)
):
    """
    Get demo credentials for testing (development only)
    
    This endpoint should be disabled in production
    """
    
    try:
        demo_creds = create_demo_passwords(db)
        
        return APIResponse(
            success=True,
            message="Demo credentials generated",
            data={
                "note": "These are demo credentials for development/testing only",
                "credentials": demo_creds,
                "usage": "Use employee_id as username and the corresponding password"
            }
        )
    
    except Exception as e:
        logger.error(f"Error generating demo credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating demo credentials"
        )


@router.get("/validate-token", response_model=APIResponse)
async def validate_token(
    current_controller: Controller = Depends(get_current_active_controller)
):
    """
    Validate current JWT token
    
    Returns controller information if token is valid
    """
    
    return APIResponse(
        success=True,
        message="Token is valid",
        data={
            "controller": {
                "id": current_controller.id,
                "name": current_controller.name,
                "employee_id": current_controller.employee_id,
                "auth_level": current_controller.auth_level.value,
                "section_responsibility": current_controller.section_responsibility,
                "active": current_controller.active
            },
            "token_status": "valid"
        }
    )


@router.get("/permissions", response_model=APIResponse)
async def get_controller_permissions(
    current_controller: Controller = Depends(get_current_active_controller)
):
    """
    Get current controller's permissions and capabilities
    """
    
    # Define permission levels
    permissions = {
        "operator": [
            "view_train_positions",
            "update_train_status",
            "create_basic_decisions"
        ],
        "supervisor": [
            "view_train_positions",
            "update_train_status", 
            "create_basic_decisions",
            "resolve_conflicts",
            "manage_section_operations",
            "approve_operator_decisions"
        ],
        "manager": [
            "view_train_positions",
            "update_train_status",
            "create_basic_decisions", 
            "resolve_conflicts",
            "manage_section_operations",
            "approve_operator_decisions",
            "schedule_maintenance",
            "manage_train_priorities",
            "access_analytics"
        ],
        "admin": [
            "full_system_access",
            "manage_controllers",
            "system_configuration",
            "view_all_sections",
            "emergency_override"
        ]
    }
    
    controller_permissions = permissions.get(current_controller.auth_level.value, [])
    
    return APIResponse(
        success=True,
        message="Controller permissions retrieved",
        data={
            "controller_id": current_controller.id,
            "auth_level": current_controller.auth_level.value,
            "section_responsibility": current_controller.section_responsibility,
            "permissions": controller_permissions,
            "can_access_sections": current_controller.section_responsibility or [],
            "global_access": current_controller.auth_level.value in ["manager", "admin"]
        }
    )