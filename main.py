from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from handler.user import router as user_router
from handler.genre import router as genre_router
from handler.oshi import router as oshi_router
from handler.system import router as system_router
from handler.content import router as content_router

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("GOOGLE_CSE_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(debug=True)

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

@app.get("/", tags=["Default"])
async def root():
    return {
        "message": (
            "Welcome to FanCloud!\n\n"
            "FanCloudは、あなたの推し情報をまとめ、ジャンル別に管理できるプラットフォームです。\n"
            "ユーザーはお気に入りのアーティストやキャラクターに関するノートを作成し、"
            "画像やイベント情報を追加できます。\n"
            "シンプルでおしゃれなUIが、楽しいファンライフをサポートします。\n\n"
            "主な機能:\n"
            "- ユーザー認証とGoogleログイン\n"
            "- ジャンル別に推し情報を管理\n"
            "- 画像やイベントの追加機能\n"
            "- シンプルでおしゃれなUIデザイン\n\n"
            "📄 詳細なAPIドキュメントは /docs で確認できます。"
        )
    }

app.include_router(system_router, tags=["System"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(genre_router, prefix="/genre", tags=["Genre"])
app.include_router(oshi_router, prefix="/oshi", tags=["Oshi"])
app.include_router(content_router, prefix="/content", tags=["Content"])