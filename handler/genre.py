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
    valid_genres = supabase.table('genres').select('genre_name').execute()
    valid_genre_names = {genre['genre_name'] for genre in valid_genres.data}

    for genre in user_genres.genres:
        if genre not in valid_genre_names:
            raise HTTPException(status_code=400, detail=f"Invalid genre: {genre}")

    user = supabase.table('users').select('id').filter('email', 'eq', user_genres.email).execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user.data[0]['id']
    genre_entries = [{'user_id': user_id, 'genre_name': genre} for genre in user_genres.genres]
    response = supabase.table('user_genres').insert(genre_entries).execute()

    if response.data:
        return {"message": "Genres selected successfully", "selected_genres": user_genres.genres}
    else:
        raise HTTPException(status_code=500, detail="Failed to save genres")

@router.post("/get-user-genres")
async def get_user_genres(request: EmailRequest):
    email = request.email
    user_data = supabase.table('users').select('id').eq('email', email).execute()
    if not user_data.data or not user_data.data[0]:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user_data.data[0]['id']
    genres_data = supabase.table('user_genres').select('genre_name').eq('user_id', user_id).execute()
    if not genres_data.data:
        return []

    genres = [genre['genre_name'] for genre in genres_data.data]
    return genres