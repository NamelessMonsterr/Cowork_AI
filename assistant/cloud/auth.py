"""
W19.1 Cloud Identity & Auth.
Mock implementation of Email OTP flow.
In production, this would talk to a real auth service (Firebase/Auth0/Custom).
"""
import uuid
import logging
import random
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger("CloudAuth")
router = APIRouter(prefix="/cloud/auth", tags=["Cloud Auth"])

# Mock Storage
# OTP Store: {email: {"otp": "123456", "expires": timestamp}}
OTP_STORE: Dict[str, Dict] = {}
# Session Store: {token: {"user_id": "u_...", "email": "..."}}
SESSIONS: Dict[str, Dict] = {}

class AuthRequest(BaseModel):
    email: str

class VerifyRequest(BaseModel):
    email: str
    otp: str

class AuthUser(BaseModel):
    user_id: str
    email: str
    token: Optional[str] = None

# Current User (In-memory singleton for MVP, per process)
current_user: Optional[AuthUser] = None

@router.post("/request_otp")
async def request_otp(req: AuthRequest, background_tasks: BackgroundTasks):
    """Generate and 'send' OTP."""
    otp = f"{random.randint(100000, 999999)}"
    OTP_STORE[req.email] = {"otp": otp}
    
    # Mock Email Sending
    logger.info(f"📧 [MOCK EMAIL] To: {req.email}, OTP: {otp}")
    print(f"📧 [MOCK EMAIL] To: {req.email}, OTP: {otp}") # Print for test visibility
    
    return {"message": "OTP sent to email (check console)"}

@router.post("/verify_otp")
async def verify_otp(req: VerifyRequest):
    """Verify OTP and login."""
    global current_user
    
    record = OTP_STORE.get(req.email)
    if not record or record["otp"] != req.otp:
        raise HTTPException(401, "Invalid or expired OTP")
        
    # Success - Create Session
    user_id = f"u_{uuid.uuid5(uuid.NAMESPACE_DNS, req.email).hex[:8]}"
    token = f"tok_{uuid.uuid4().hex}"
    
    session = {"user_id": user_id, "email": req.email, "token": token}
    SESSIONS[token] = session
    
    current_user = AuthUser(**session)
    # Clear OTP
    del OTP_STORE[req.email]
    
    logger.info(f"✅ User Logged In: {req.email} ({user_id})")
    return current_user

@router.post("/logout")
async def logout():
    """Clear session."""
    global current_user
    if current_user:
        logger.info(f"User Logged Out: {current_user.email}")
    current_user = None
    return {"message": "Logged out"}

@router.get("/status")
async def get_status():
    """Get current auth status."""
    if current_user:
        return {"authenticated": True, "user": current_user}
    return {"authenticated": False}

def get_current_user() -> Optional[AuthUser]:
    return current_user
