from fastapi import APIRouter, HTTPException
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from model.oshi import SearchQuery, OshiRequest, UserOshiRequest, UserOshiAndGenresRequest
from model.genres import UserOshiGenresRequest
from dotenv import load_dotenv
import os

# 環境変数をロード
load_dotenv()

# Supabase URLとキーを取得
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabaseクライアントを作成
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# APIRouterのインスタンスを作成
router = APIRouter()

# 特定のSNSリンクをフィルタリングするためのヘルパー関数
def extract_sns_links(soup):
    sns_links = {
        "youtube": None,
        "spotify": None,
        "soundcloud": None,
        "x": None,
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
        elif "twitter.com" in href or "x.com" in href:
            sns_links["x"] = href
        elif "instagram.com" in href:
            sns_links["instagram"] = href
        elif "music.apple.com" in href:
            sns_links["applemusic"] = href
        elif "facebook.com" in href:
            sns_links["facebook"] = href
    
    return sns_links

# 推し検索エンドポイント
@router.post("/search-oshi")
async def search_oshi(query: SearchQuery):
    wikipedia_url = "https://ja.wikipedia.org/w/api.php"

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

# 推し情報取得エンドポイント
@router.post("/fetch-oshi-info")
async def fetch_oshi_info(request: OshiRequest):
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
        raise HTTPException(status_code=404, detail="Wikipediaのページが見つかりませんでした")

    page = next(iter(pages.values()))
    page_url = page.get("fullurl")
    
    if not page_url:
        raise HTTPException(status_code=404, detail="WikipediaのURLが見つかりませんでした")
    
    # WikipediaのページHTMLを取得
    html_response = requests.get(page_url)
    soup = BeautifulSoup(html_response.content, 'html.parser')

    # クラス名が official-website のリンクを探す
    official_site_tag = soup.find(class_="official-website")
    official_site_url = official_site_tag.a['href'] if official_site_tag and official_site_tag.a else None

    if not official_site_url:
        official_site_url = "Official websiteが見つかりませんでした"
    
    # SNSリンクを抽出
    sns_links = extract_sns_links(soup)
    
    # 推しの画像リンクを取得
    image_tag = soup.find("table", class_="infobox").find("img")
    if image_tag:
        image_url = f"https:{image_tag['src']}"
        # URLに"Flag_of"が含まれている場合、別の画像に置き換える
        if "Flag_of" in image_url:
            image_url = "https://www.shoshinsha-design.com/wp-content/uploads/2020/05/%E3%83%8E%E3%83%BC%E3%82%A4%E3%83%A1%E3%83%BC%E3%82%B7%E3%82%99-760x460.png"  # ここに置き換える画像のURLを入力
    else:
        image_url = "画像が見つかりませんでした"
        
    # 推しの職業を取得
    infobox = soup.find("table", class_="infobox")
    if infobox:
        profession_tag = infobox.find("th", text="職業")  # 日本語のWikipediaでは「職業」と表示されることが多い
        if profession_tag:
            profession_data = profession_tag.find_next_sibling("td")
            if profession_data:
                professions = profession_data.get_text(strip=True).split('、')  # 日本語では職業が「、」で区切られることが多い
                profession = ', '.join(professions)  # カンマで区切る
            else:
                profession = "職業が見つかりませんでした"
        else:
            profession = "職業が見つかりませんでした"
    else:
        profession = "職業が見つかりませんでした"
    
    # 推しの概要を取得（ページ本文の最初の段落）
    summary_tag = soup.find("div", class_="mw-parser-output").find("p")
    summary = summary_tag.get_text(strip=True) if summary_tag else "概要が見つかりませんでした"
    
    # Wikipedia URL、公式サイトURL、SNSリンク、画像リンク、職業、概要をレスポンスとして返す
    return {
        "oshi_name": oshi_name,
        "wikipedia_url": page_url,
        "official_site_url": official_site_url,
        "sns_links": sns_links,
        "image_url": image_url,
        "profession": profession,
        "summary": summary
    }

# 推し情報とジャンル保存エンドポイント
@router.post("/save-oshi-info-and-genres")
async def save_oshi_info_and_genres(request: UserOshiAndGenresRequest):
    email = request.email
    oshi_name = request.oshi_name
    genre = request.genre  # 単一のジャンル

    # SupabaseからユーザーIDを取得
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user_id = user_data.data[0]['id']

    # Wikipedia APIを使って推しのページURLを取得
    params = {
        "action": "query",
        "format": "json",
        "prop": "info",
        "titles": oshi_name,
        "inprop": "url"
    }

    response = requests.get("https://ja.wikipedia.org/w/api.php", params=params)
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        raise HTTPException(status_code=404, detail="Wikipediaページが見つかりません")

    page = next(iter(pages.values()))
    page_url = page.get("fullurl")

    if not page_url:
        raise HTTPException(status_code=404, detail="WikipediaのURLが見つかりません")

    # WikipediaのページHTMLを取得
    html_response = requests.get(page_url)
    soup = BeautifulSoup(html_response.content, 'html.parser')

    # クラス名が official-website のリンクを探す
    official_site_tag = soup.find(class_="official-website")
    official_site_url = official_site_tag.a['href'] if official_site_tag and official_site_tag.a else "公式サイトが見つかりません"

    # SNSリンクを抽出
    sns_links = extract_sns_links(soup)

    # 推しの画像リンクを取得
    infobox = soup.find("table", class_="infobox")
    if infobox:
        image_tag = infobox.find("img")
        if image_tag:
            image_url = f"https:{image_tag['src']}"
            # URLに"Flag_of"が含まれている場合、別の画像に置き換える
            if "Flag_of" in image_url:
                image_url = "https://www.shoshinsha-design.com/wp-content/uploads/2020/05/%E3%83%8E%E3%83%BC%E3%82%A4%E3%83%A1%E3%83%BC%E3%82%B7%E3%82%99-760x460.png"  # ここに置き換える画像のURLを入力
        else:
            image_url = "画像が見つかりません"
    else:
        image_url = "画像が見つかりません"  

    # 推しの職業を取得
    if infobox:
        profession_tag = infobox.find("th", text="職業")
        if profession_tag:
            profession_data = profession_tag.find_next_sibling("td")
            if profession_data:
                professions = profession_data.get_text(strip=True).split('、')
                profession = ', '.join(professions)
            else:
                profession = "職業が見つかりません"
        else:
            profession = "職業が見つかりません"
    else:
        profession = "Infoboxが見つかりません"

    # 推しの概要を取得（ページ本文の最初の段落）
    content_div = soup.find("div", class_="mw-parser-output")
    if content_div:
        summary_tag = content_div.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else "概要が見つかりません"
    else:
        summary = "コンテンツが見つかりません"

    # 同じユーザーが既にその推しを登録しているか確認（user_idとoshi_nameの組み合わせで確認）
    oshi_data = supabase.table('oshi').select('id').eq('user_id', user_id).eq('oshi_name', oshi_name).execute()

    if oshi_data.data and oshi_data.data[0]:
        oshi_id = oshi_data.data[0]['id']

        # ジャンルの検証
        valid_genres = supabase.table('genres').select('genre_name').execute()
        valid_genre_names = {genre['genre_name'] for genre in valid_genres.data}

        if genre not in valid_genre_names:
            raise HTTPException(status_code=400, detail=f"無効なジャンル: {genre}")

        # oshiテーブルの genres カラムに選択されたジャンルを格納
        response = supabase.table('oshi').update({
            'summary': summary,
            'official_site': official_site_url,
            'sns_links': sns_links,
            'image_url': image_url,
            'profession': profession,
            'genres': genre
        }).eq('id', oshi_id).execute()

        if response.data:
            return {"message": "推しの情報とジャンルが正常に保存されました", "genre": genre}
        else:
            raise HTTPException(status_code=500, detail="推しの情報とジャンルの保存に失敗しました")
    else:
        # oshi情報が存在しない場合は新規追加
        response = supabase.table('oshi').insert({
            'user_id': user_id,
            'oshi_name': oshi_name,
            'summary': summary,
            'official_site': official_site_url,
            'sns_links': sns_links,
            'image_url': image_url,
            'profession': profession,
            'genres': genre
        }).execute()

        if response.data:
            return {"message": "推しの情報とジャンルが正常に保存されました", "genre": genre}
        else:
            raise HTTPException(status_code=500, detail="推しの情報とジャンルの保存に失敗しました")

# ユーザーの推しとジャンル情報を取得するエンドポイント
@router.post("/get-user-oshi-genres")
async def get_user_oshi_genres(request: UserOshiGenresRequest):
    
    email = request.email
    
    # ユーザーIDをメールから取得
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    
    user_id = user_data.data[0]['id']
    
    # ユーザーの推し情報を取得
    oshi_data = supabase.table('oshi').select('oshi_name', 'genres', 'image_url').eq('user_id', user_id).execute()
    
    if not oshi_data.data:
        return {"oshi": []}  # 推し情報が見つからない場合
    
    # 推しの名前、ジャンル、画像URLを含むリストを返す
    oshi_genres = [
        {"oshi_name": oshi['oshi_name'], "genre": oshi['genres'], "image_url": oshi['image_url']}
        for oshi in oshi_data.data
    ]
    
    return {"oshi": oshi_genres}

# 推し情報取得エンドポイント
@router.post("/get-oshi-info")
async def get_oshi_info(request: UserOshiRequest):
    email = request.email
    oshi_name = request.oshi_name
    
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="Userが見つかりません")
    
    user_id = user_data.data[0]['id']
    
    oshi_data = supabase.table('oshi').select('*').eq('user_id', user_id).eq('oshi_name', oshi_name).execute()
    
    if not oshi_data.data or not oshi_data.data[0]:
        raise HTTPException(status_code=404, detail="このユーザーの推しが見つかりませんでした")
    
    oshi_info = oshi_data.data[0]
    return {
        "oshi_name": oshi_info['oshi_name'],
        "summary": oshi_info['summary'],
        "official_site": oshi_info['official_site'],
        "sns_links": oshi_info['sns_links'],
        "image_url": oshi_info['image_url'],
        "profession": oshi_info['profession'],
        "genres": oshi_info['genres']
    }

# 推し削除エンドポイント
@router.post("/delete-oshi")
async def delete_oshi(request: UserOshiRequest):
    email = request.email
    oshi_name = request.oshi_name

    # ユーザーIDを取得する
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user_id = user_data.data[0]['id']

    # 該当する推しが存在するか確認
    oshi_data = supabase.table('oshi').select('id').eq('user_id', user_id).eq('oshi_name', oshi_name).execute()
    if not oshi_data.data or not oshi_data.data[0]:
        raise HTTPException(status_code=404, detail="該当する推しが見つかりません")

    oshi_id = oshi_data.data[0]['id']

    # 推しを削除
    response = supabase.table('oshi').delete().eq('id', oshi_id).execute()

    if response.data:
        return {"message": f"{oshi_name} の推しが正常に削除されました"}
    else:
        raise HTTPException(status_code=500, detail="推しの削除に失敗しました")
    
