from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from handler.user import router as user_router
from handler.genre import router as genre_router
from handler.oshi import router as oshi_router
from handler.system import router as system_router

# 環境変数をロード
load_dotenv()

# Supabase URLとキーを取得
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_CSE_ID")

# Supabaseクライアントを作成
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPIアプリケーションのインスタンス
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fancloud.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
) 

app.get("/")
async def root():
    return {"message": "Hello World"}

app.include_router(user_router, prefix="/user")
app.include_router(genre_router, prefix="/genre")
app.include_router(oshi_router, prefix="/oshi")
app.include_router(system_router)