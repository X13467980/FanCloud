from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
import uuid
import hashlib
import os
from dotenv import load_dotenv
import supabase
from model.user import UserCreate, UserLogin
from fastapi.responses import RedirectResponse
from fastapi import Request

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/register")
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)

    response = supabase.table('users').insert({
        'id': user_id,
        'email': user.email,
        'password': hashed_password,
        'username': user.username
    }).execute()

    if response.data:
        return {
            "message": "User successfully created",
            "user": {
                "username": user.username,
                "email": user.email,
                "password": user.password
            }
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.post("/login")
async def login(user: UserLogin):

    response = supabase.table('users').select('email', 'password', 'username').eq('email', user.email).execute()

    if not response.data or not response.data[0]:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    saved_password_hash = response.data[0]['password']

    input_password_hash = hash_password(user.password)

    if saved_password_hash != input_password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
            "username": response.data[0]['username'],
            "email": user.email
    }
    
@router.get("/login/google")
async def google_login():
    redirect_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=http://localhost:8000/user/auth/callback"
    return  RedirectResponse(url=redirect_url)

@router.get("/auth/callback")
async def google_auth_callback(request: Request, token: str = None):
    if token is None:
        print(f"Request: {request.query_params}")
        raise HTTPException(status_code=400, detail="Token is missing")
    
    user_info = supabase.auth.api.get_user(token)

    if not user_info:
        raise HTTPException(status_code=401, detail="Google authentication failed")

    return {
        "message": "Google authentication successful",
        "email": user_info.user.email,
        "username": user_info.user.user_metadata.get('full_name', 'GoogleUser')
    }