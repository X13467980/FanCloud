from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import uuid
import hashlib
import requests
from bs4 import BeautifulSoup

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticのモデル
class UserCreate(BaseModel):
    username: str  # ユーザーネームを追加
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

class OshiRequest(BaseModel):
    oshi_name: str
    
# 特定のSNSリンクをフィルタリングするためのヘルパー関数
def extract_sns_links(soup):
    sns_links = {
        "youtube": None,
        "spotify": None,
        "soundcloud": None,
        "x": None,           # X (旧Twitter)
        "instagram": None,
        "applemusic": None,
        "facebook": None
    }
    
    # すべての<a>タグを探す
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link['href']
        
        # references クラスのリンクはスキップ
        if "references" in link.get('class', []):
            continue
        
        # 各SNSのURLを判定して格納
        if "youtube.com" in href:
            sns_links["youtube"] = href
        elif "spotify.com" in href:
            sns_links["spotify"] = href
        elif "soundcloud.com" in href:
            sns_links["soundcloud"] = href
        elif "twitter.com" in href or "x.com" in href:  # Twitter (X) のドメイン
            sns_links["x"] = href
        elif "instagram.com" in href:
            sns_links["instagram"] = href
        elif "music.apple.com" in href:
            sns_links["applemusic"] = href
        elif "facebook.com" in href:
            sns_links["facebook"] = href
    
    return sns_links

@app.post("/get-wikipedia-and-sns-urls")
async def get_wikipedia_and_sns_urls(request: OshiRequest):
    oshi_name = request.oshi_name
    wiki_url = "https://ja.wikipedia.org/w/api.php"
    
    # Wikipedia APIを使って推しのページURLを取得
    params = {
        "action": "query",
        "format": "json",
        "prop": "info",
        "titles": oshi_name,
        "inprop": "url"
    }
    
    response = requests.get(wiki_url, params=params)
    data = response.json()
    
    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise HTTPException(status_code=404, detail="Wikipedia page not found")

    page = next(iter(pages.values()))
    page_url = page.get("fullurl")
    
    if not page_url:
        raise HTTPException(status_code=404, detail="Wikipedia URL not found")
    
    # WikipediaのページHTMLを取得
    html_response = requests.get(page_url)
    soup = BeautifulSoup(html_response.content, 'html.parser')

    # クラス名が official-website のリンクを探す
    official_site_tag = soup.find(class_="official-website")
    official_site_url = official_site_tag.a['href'] if official_site_tag and official_site_tag.a else None

    if not official_site_url:
        official_site_url = "Official website not found"

    # SNSリンクを抽出
    sns_links = extract_sns_links(soup)
    
    # Wikipedia URL、公式サイトURL、SNSリンクをレスポンスとして返す
    return {
        "wikipedia_url": page_url,
        "official_site_url": official_site_url,
        "sns_links": sns_links
    }
    
# パスワードのハッシュ化
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Google検索結果からSNSリンクを抽出
def extract_sns_links_from_search(search_results: list) -> dict:
    sns_links = {}
    for item in search_results:
        link = item.get('link', '')
        if 'twitter.com' in link:
            sns_links['twitter'] = link
        elif 'instagram.com' in link:
            sns_links['instagram'] = link
        elif 'youtube.com' in link:
            sns_links['youtube'] = link
        elif 'spotify.com' in link:
            sns_links['spotify'] = link
        elif 'music.apple.com' in link:
            sns_links['apple_music'] = link
    return sns_links

# Wikipedia APIを使ってページIDを取得する
def get_wikipedia_page_id(oshi_name: str) -> str:
    wikipedia_api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': oshi_name,
        'format': 'json'
    }
    
    response = requests.get(wikipedia_api_url, params=params)
    data = response.json()
    
    if 'query' in data and 'search' in data['query']:
        search_results = data['query']['search']
        if search_results:
            # 最初の結果からページIDを取得
            page_id = search_results[0]['pageid']
            return page_id
        else:
            raise HTTPException(status_code=404, detail="Wikipediaの検索結果が見つかりませんでした")
    else:
        raise HTTPException(status_code=500, detail="Wikipedia APIからデータを取得できませんでした")

# WikipediaページのHTMLを取得して外部リンクを抽出する
def scrape_external_links_from_wikipedia(page_id: str) -> dict:
    wikipedia_page_url = f"https://en.wikipedia.org/?curid={page_id}"
    
    # WikipediaページのHTMLを取得
    response = requests.get(wikipedia_page_url)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # 外部リンクを抽出 (すべての <a> タグの href 属性)
    external_links = {}
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # 外部リンクかどうかを確認 (Wikipedia内リンクを除外)
        if href.startswith('http'):
            if 'twitter.com' in href:
                external_links['twitter'] = href
            elif 'instagram.com' in href:
                external_links['instagram'] = href
            elif 'youtube.com' in href:
                external_links['youtube'] = href
            elif 'spotify.com' in href:
                external_links['spotify'] = href
            elif 'music.apple.com' in href:
                external_links['apple_music'] = href
    
    return external_links

# Google Custom Search APIを使って推し情報を取得（「Official Website」を追加して検索）
def fetch_oshi_info_from_google(oshi_name: str) -> OshiInfo:
    google_search_url = f"https://www.googleapis.com/customsearch/v1"
    search_query = f"{oshi_name} Official Website"
    params = {
        'q': search_query,
        'cx': SEARCH_ENGINE_ID,
        'key': GOOGLE_API_KEY
    }
    
    response = requests.get(google_search_url, params=params)
    data = response.json()

    search_results = data.get('items', [])
    
    if search_results:
        official_site = search_results[0].get('link', '')
    else:
        official_site = '公式サイトが見つかりませんでした'
    
    sns_links = extract_sns_links_from_search(search_results)
    
    # SNSリンクが見つからない場合のデフォルト処理
    if not sns_links:
        sns_links = {"twitter": "N/A", "instagram": "N/A"}

    summary = f"{oshi_name}に関する情報"
    
    return OshiInfo(
        name=oshi_name,
        summary=summary,
        official_site=official_site,
        sns_links=sns_links
    )

# ユーザー登録エンドポイント
@app.post("/register")
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
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user_id = user.data[0]['id']
    genre_entries = [{'user_id': user_id, 'genre_name': genre} for genre in user_genres.genres]
    response = supabase.table('user_genres').insert(genre_entries).execute()

    if response.data:
        return {"message": "ジャンルが正常に選択されました", "selected_genres": user_genres.genres}
    else:
        raise HTTPException(status_code=500, detail="ジャンルの保存に失敗しました")

# 推し検索エンドポイント
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
        raise HTTPException(status_code=500, detail="Wikipediaから検索結果を取得できませんでした")

@app.post("/select-oshi")
async def select_oshi(selected_oshi: SelectedOshi):
    # ユーザーの取得
    user = supabase.table('users').select('id').filter('email', 'eq', selected_oshi.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user_id = user.data[0]['id']

    # 推しの情報を取得
    oshi_info = fetch_oshi_info_from_google(selected_oshi.oshi_name)

    # 推しの情報を取得または更新
    existing_oshi = supabase.table('oshi').select('id').filter('oshi_name', 'eq', selected_oshi.oshi_name).execute()