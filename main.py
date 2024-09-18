from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import uuid
import hashlib
import requests
from bs4 import BeautifulSoup

# .envファイルを読み込む
load_dotenv()

# 環境変数からSupabaseのURLとキーを取得
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabaseクライアントの設定
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# Pydanticモデル
class UserCreate(BaseModel):
    email: str
    password: str

class UserGenres(BaseModel):
    email: str
    genres: list[str]

class SearchQuery(BaseModel):
    query: str

class SelectedOshi(BaseModel):
    email: str
    oshi_name: str

class OshiInfo(BaseModel):
    name: str
    summary: str
    official_site: str
    sns_links: dict

# パスワードをハッシュ化する関数
def hash_password(password: str) -> str:
    """ パスワードをハッシュ化する関数 """
    return hashlib.sha256(password.encode()).hexdigest()

# SNSリンクを抽出する関数
def extract_sns_links(html_content: str) -> dict:
    """WikipediaページのHTMLからSNSリンクを抽出する関数"""
    soup = BeautifulSoup(html_content, 'html.parser')
    sns_links = {}

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if 'twitter.com' in href:
            sns_links['twitter'] = href
        elif 'instagram.com' in href:
            sns_links['instagram'] = href
        elif 'youtube.com' in href:
            sns_links['youtube'] = href
        elif 'spotify.com' in href:
            sns_links['spotify'] = href
        elif 'music.apple.com' in href:
            sns_links['apple_music'] = href

    return sns_links

# 推しの詳細情報を取得する関数
def fetch_oshi_info(oshi_name: str) -> OshiInfo:
    wikipedia_url = f"https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'titles': oshi_name,
        'prop': 'extracts',
        'exintro': True,
        'format': 'json'
    }
    response = requests.get(wikipedia_url, params=params)
    data = response.json()

    pages = data.get('query', {}).get('pages', {})
    page = next(iter(pages.values()), {})
    summary = page.get('extract', '')

    # WikipediaのHTMLを取得してSNSリンクを抽出
    page_url = f"https://en.wikipedia.org/wiki/{oshi_name}"
    page_response = requests.get(page_url)
    page_html = page_response.text
    sns_links = extract_sns_links(page_html)

    return OshiInfo(
        name=oshi_name,
        summary=summary,
        official_site=page_url,
        sns_links=sns_links
    )

# ユーザー作成エンドポイント
@app.post("/register")
async def register_user(user: UserCreate):
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user.password)

    response = supabase.table('users').insert({
        'id': user_id,
        'email': user.email,
        'password': hashed_password
    }).execute()

    if response.data:
        return {"message": "User created successfully"}
    else:
        raise HTTPException(status_code=500, detail="User creation failed")

# ジャンル選択エンドポイント
@app.post("/select-genres")
async def select_genres(user_genres: UserGenres):
    valid_genres = supabase.table('genres').select('genre_name').execute()
    valid_genre_names = {genre['genre_name'] for genre in valid_genres.data}

    for genre in user_genres.genres:
        if genre not in valid_genre_names:
            raise HTTPException(status_code=400, detail=f"無効なジャンル: {genre}")

    user = supabase.table('users').select('id').filter('email', 'eq', user_genres.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.data[0]['id']
    genre_entries = [{'user_id': user_id, 'genre_name': genre} for genre in user_genres.genres]
    response = supabase.table('user_genres').insert(genre_entries).execute()

    if response.data:
        return {"message": "Genre selected successfully", "selected_genres": user_genres.genres}
    else:
        raise HTTPException(status_code=500, detail="failed to preserve Genre")

@app.post("/search-oshi")
async def search_oshi(query: SearchQuery):
    wikipedia_url = f"https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query.query,
        'format': 'json',
        'srlimit': 4
    }
    response = requests.get(wikipedia_url, params=params)
    data = response.json()

    if 'query' in data and 'search' in data['query']:
        search_results = data['query']['search']
        titles = [result['title'] for result in search_results]
        return {'titles': titles}
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch search results from Wikipedia")

# 推し選択エンドポイント
@app.post("/select-oshi")
async def select_oshi(selected_oshi: SelectedOshi):
    user = supabase.table('users').select('id').filter('email', 'eq', selected_oshi.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.data[0]['id']
    oshi_info = fetch_oshi_info(selected_oshi.oshi_name)

    response = supabase.table('oshi').insert({
        'user_id': user_id,
        'oshi_name': oshi_info.name,
        'summary': oshi_info.summary,
        'official_site': oshi_info.official_site,
        'sns_links': oshi_info.sns_links
    }).execute()

    if response.data:
        return {"message": "Oshi selected and information saved successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save oshi information")

# ルートエンドポイント（オプション）
@app.get("/")
async def root():
    return {"message": "Welcome to FanCloud"}

# アプリケーションを起動するためのスクリプト
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)