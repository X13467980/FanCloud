from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
import uuid
import hashlib
import os
from dotenv import load_dotenv
import supabase
from model.user import UserCreate, UserLogin

# 環境変数をロード
load_dotenv()

# Supabase URLとキーを取得
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabaseクライアントを作成
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

# パスワードのハッシュ化
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ユーザー登録エンドポイント
@router.post("/register")
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)

    response = supabase.table('users').insert({
        'id': user_id,
        'email': user.email,
        'password': hashed_password,
        'username': user.username  # ユーザーネームを登録
    }).execute()

    if response.data:
        return {
            "message": "ユーザーが正常に作成されました",
            "user": {
                "username": user.username,
                "email": user.email,
                "password": user.password  # 注意: パスワードを含めるのはセキュリティ上推奨されません
            }
        }
    else:
        raise HTTPException(status_code=500, detail="ユーザー作成に失敗しました")

# ユーザーログインエンドポイント
@router.post("/login")
async def login(user: UserLogin):
    # Supabaseからユーザーのデータを取得
    response = supabase.table('users').select('email', 'password', 'username').eq('email', user.email).execute()

    # ユーザーが見つからない場合
    if not response.data or not response.data[0]:
        raise HTTPException(status_code=401, detail="emailまたはpasswordが違います")

    # データベースに保存されているハッシュ化されたパスワード
    saved_password_hash = response.data[0]['password']

    # 入力されたパスワードをハッシュ化
    input_password_hash = hash_password(user.password)

    # ハッシュ化されたパスワードを比較
    if saved_password_hash != input_password_hash:
        raise HTTPException(status_code=401, detail="emailまたはpasswordが違います")

    # ログイン成功時のレスポンス
    return {
            "username": response.data[0]['username'],
            "email": user.email
    }