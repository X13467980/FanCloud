from fastapi import APIRouter, HTTPException
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from model.oshi import SearchQuery, OshiRequest, UserOshiRequest, UserOshiAndGenresRequest
from model.genres import UserOshiGenresRequest
from dotenv import load_dotenv
import os

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

def get_user_id(email):
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data.data[0]['id']

def fetch_wikipedia_info(oshi_name):
    wiki_url = "https://ja.wikipedia.org/w/api.php"
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
    return page_url

def parse_wikipedia_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    nationality = "Nationality not found"
    infobox = soup.find("table", class_="infobox")
    if infobox:
        nationality_tag = infobox.find("th", text="国籍")
        if nationality_tag:
            nationality_data = nationality_tag.find_next_sibling("td")
            if nationality_data:
                nationality = nationality_data.get_text(strip=True)
    official_site_tag = soup.find(class_="official-website")
    official_site_url = official_site_tag.a['href'] if official_site_tag and official_site_tag.a else "Official site not found"
    sns_links = extract_sns_links(soup)
    image_url = None
    if infobox:
        image_tag = infobox.find("img")
        if image_tag:
            image_url = f"https:{image_tag['src']}"
            if "Flag_of" in image_url:
                image_url = "https://www.shoshinsha-design.com/wp-content/uploads/2020/05/%E3%83%8E%E3%83%BC%E3%82%A4%E3%83%A1%E3%83%BC%E3%82%B7%E3%82%99-760x460.png"
        else:
            image_url = "Image not found"
    profession = "Profession not found"
    if infobox:
        profession_tag = infobox.find("th", text="職業")
        if profession_tag:
            profession_data = profession_tag.find_next_sibling("td")
            if profession_data:
                professions = profession_data.get_text(strip=True).split('、')
                profession = ', '.join(professions)
    summary = "Summary not found"
    content_div = soup.find("div", class_="mw-parser-output")
    if content_div:
        summary_tag = content_div.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else "Summary not found"
    return {
        "official_site_url": official_site_url,
        "sns_links": sns_links,
        "image_url": image_url,
        "profession": profession,
        "summary": summary,
    }

def extract_sns_links(soup):
    sns_links = {"youtube": None, "spotify": None, "soundcloud": None, "x": None, "instagram": None, "applemusic": None, "facebook": None}
    for link in soup.find_all('a', href=True):
        href = link['href']
        if "references" in link.get('class', []):
            continue
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

@router.post("/search-oshi")
async def search_oshi(query: SearchQuery):
    wikipedia_url = "https://ja.wikipedia.org/w/api.php"
    params = {'action': 'query', 'list': 'search', 'srsearch': query.query, 'format': 'json', 'srlimit': 4}
    response = requests.get(wikipedia_url, params=params)
    data = response.json()
    if 'query' in data and 'search' in data['query']:
        search_results = data['query']['search']
        titles = [result['title'] for result in search_results]
        return {'titles': titles}
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve search results from Wikipedia")

@router.post("/fetch-oshi-info")
async def fetch_oshi_info(request: OshiRequest):
    oshi_name = request.oshi_name
    page_url = fetch_wikipedia_info(oshi_name)
    wiki_info = parse_wikipedia_page(page_url)
    is_japanese = "Japan" in wiki_info.get("nationality", "")
    display_name = oshi_name if is_japanese else oshi_name
    return {
        "oshi_name": display_name,
        "wikipedia_url": page_url,
        **wiki_info
    }

@router.post("/save-oshi-info-and-genres")
async def save_oshi_info_and_genres(request: UserOshiAndGenresRequest):
    email = request.email
    oshi_name = request.oshi_name
    genre = request.genre
    user_id = get_user_id(email)
    page_url = fetch_wikipedia_info(oshi_name)
    wiki_info = parse_wikipedia_page(page_url)
    valid_genres = supabase.table('genres').select('genre_name').execute()
    valid_genre_names = {genre['genre_name'] for genre in valid_genres.data}
    if genre not in valid_genre_names:
        raise HTTPException(status_code=400, detail=f"Invalid genre: {genre}")
    wiki_info['official_site'] = wiki_info.pop('official_site_url', None)
    oshi_data = supabase.table('oshi').select('id').eq('user_id', user_id).eq('oshi_name', oshi_name).execute()
    if oshi_data.data and oshi_data.data[0]:
        oshi_id = oshi_data.data[0]['id']
        response = supabase.table('oshi').update({**wiki_info, 'genres': genre}).eq('id', oshi_id).execute()
    else:
        response = supabase.table('oshi').insert({'user_id': user_id, 'oshi_name': oshi_name, 'genres': genre, **wiki_info}).execute()
    if response.data:
        return {"message": "Oshi information and genre saved successfully", "genre": genre}
    else:
        raise HTTPException(status_code=500, detail="Failed to save oshi information and genre")

@router.post("/get-user-oshi-genres")
async def get_user_oshi_genres(request: UserOshiGenresRequest):
    email = request.email
    user_id = get_user_id(email)
    oshi_data = supabase.table('oshi').select('oshi_name', 'genres', 'image_url').eq('user_id', user_id).execute()
    oshi_genres = [{"oshi_name": oshi['oshi_name'], "genre": oshi['genres'], "image_url": oshi['image_url']} for oshi in oshi_data.data]
    return {"oshi": oshi_genres}

@router.post("/delete-oshi")
async def delete_oshi(request: UserOshiRequest):
    email = request.email
    oshi_names = request.oshi_names
    user_id = get_user_id(email)

    deleted_oshi = []
    not_found_oshi = []

    for oshi_name in oshi_names:
        oshi_data = supabase.table('oshi').select('id').eq('user_id', user_id).eq('oshi_name', oshi_name).execute()
        if not oshi_data.data or not oshi_data.data[0]:
            not_found_oshi.append(oshi_name)
            continue

        oshi_id = oshi_data.data[0]['id']
        response = supabase.table('oshi').delete().eq('id', oshi_id).execute()
        if response.data:
            deleted_oshi.append(oshi_name)
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete oshi {oshi_name}")
        
    if deleted_oshi and not not_found_oshi:
        return {
            "status": "success",
            "message": "All selected oshi deleted successfully.",
            "deleted": deleted_oshi
        }
    elif deleted_oshi and not_found_oshi:
        return {
            "status": "partial_success",
            "message": "Some oshi were deleted successfully, but some were not found.",
            "deleted": deleted_oshi,
            "not_found": not_found_oshi
        }
    elif not deleted_oshi and not_found_oshi:
        return {
            "status": "failure",
            "message": "No oshi were deleted. All specified oshi were not found.",
            "not_found": not_found_oshi
        }
    else:
        raise HTTPException(status_code=500, detail="Unexpected error during oshi deletion.")
