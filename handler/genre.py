from fastapi import APIRouter, HTTPException
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from model.genres import UserGenres, EmailRequest

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

router = APIRouter()

@router.post("/select-genres")
async def select_genres(user_genres: UserGenres):
    genre_response = supabase.table('genres').select('genre_name').execute()
    if not genre_response.data:
        raise HTTPException(status_code=500, detail="Failed to fetch valid genres")

    valid_genre_names = {genre['genre_name'] for genre in genre_response.data}
    invalid_genres = [genre for genre in user_genres.genres if genre not in valid_genre_names]
    if invalid_genres:
        raise HTTPException(status_code=400, detail=f"Invalid genres: {', '.join(invalid_genres)}")

    user_response = supabase.table('users').select('id').filter('email', 'eq', user_genres.email).execute()
    if not user_response.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user_response.data[0]['id']
    genre_entries = [{'user_id': user_id, 'genre_name': genre} for genre in user_genres.genres]
    insert_response = supabase.table('user_genres').insert(genre_entries).execute()

    if insert_response.data:
        return {"message": "Genres selected successfully", "selected_genres": user_genres.genres}
    else:
        raise HTTPException(status_code=500, detail="Failed to save genres")

@router.post("/get-user-genres")
async def get_user_genres(request: EmailRequest):
    user_response = supabase.table('users').select('id').eq('email', request.email).execute()
    if not user_response.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user_response.data[0]['id']
    genres_response = supabase.table('user_genres').select('genre_name').eq('user_id', user_id).execute()
    if not genres_response.data:
        return {"genres": []}

    genres = [genre['genre_name'] for genre in genres_response.data]
    return {"genres": genres}