from fastapi import APIRouter, HTTPException
from typing import List
from uuid import UUID
from supabase import create_client, Client
import os
from model.content import CreateContentRequest, FetchContentRequest, ContentData

router = APIRouter()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

async def get_oshi_id(email: str, oshi_name: str):
    user_response = supabase.table("users").select("id").eq("email", email).execute()
    if not user_response.data:
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user_response.data[0]["id"]

    oshi_response = supabase.table("oshi").select("id").eq("user_id", user_id).eq("oshi_name", oshi_name).execute()
    if not oshi_response.data:
        raise HTTPException(status_code=404, detail="Oshi not found")

    return oshi_response.data[0]["id"]

@router.post("/create-content")
async def create_content(request: CreateContentRequest):
    try:
        oshi_id = await get_oshi_id(request.email, request.oshi_name)

        for content in request.content:
            content_data = {
                "oshi_id": str(oshi_id),
                "type": content.type,
                "order_index": content.order_index,
            }
            response = supabase.table("content").insert(content_data).execute()
            content_id = response.data[0]["id"]

            if content.type == "text":
                text_data = {
                    "id": content_id,
                    "text": content.text,
                    "font_size": content.fontSize,
                    "alignment": content.alignment,
                }
                supabase.table("text_data").insert(text_data).execute()

            elif content.type == "image":
                image_data = {
                    "id": content_id,
                    "src": content.src,
                    "size": content.size,
                }
                supabase.table("image_data").insert(image_data).execute()

            elif content.type == "event":
                event_data = {
                    "id": content_id,
                    "title": content.title,
                    "start_date": content.start_date,
                    "end_date": content.end_date,
                }
                supabase.table("event_data").insert(event_data).execute()

        return {"message": "All content created successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch-content")
async def fetch_content(request: FetchContentRequest):
    try:
        oshi_id = await get_oshi_id(request.email, request.oshi_name)

        content_response = supabase.table("content").select("*").eq("oshi_id", str(oshi_id)).order("order_index").execute()
        content_list = []

        for content in content_response.data:
            content_id = content["id"]
            content_type = content["type"]

            if content_type == "text":
                text_data = supabase.table("text_data").select("*").eq("id", content_id).execute().data[0]
                content_list.append({**content, **text_data})

            elif content_type == "image":
                image_data = supabase.table("image_data").select("*").eq("id", content_id).execute().data[0]
                content_list.append({**content, **image_data})

            elif content_type == "event":
                event_data = supabase.table("event_data").select("*").eq("id", content_id).execute().data[0]
                content_list.append({**content, **event_data})

        return {"content": content_list}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))