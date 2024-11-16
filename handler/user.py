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
import bcrypt

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
REDIRECT_URL = os.getenv("REDIRECT_URL")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

@router.post("/register")
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)

    try:
        response = supabase.table('users').insert({
            'id': user_id,
            'email': user.email,
            'password': hashed_password,
            'username': user.username
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "User successfully created",
        "user": {
            "username": user.username,
            "email": user.email,
            "password": user.password
        }
    }
    
    

@router.post("/login")
async def login(user: UserLogin):
    response = supabase.table('users').select('email', 'password', 'username').eq('email', user.email).execute()

    if not response.data or not response.data[0]:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    saved_password_hash = response.data[0]['password']

    if not verify_password(user.password, saved_password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "username": response.data[0]['username'],
        "email": user.email
    }

    
@router.get("/login/google")
async def google_login():
    redirect_url = f"{SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to={REDIRECT_URL}"
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