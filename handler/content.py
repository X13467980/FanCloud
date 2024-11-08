from fastapi import APIRouter, HTTPException
from typing import Union
from uuid import UUID
from supabase import create_client, Client
import os
from model.content import ContentData, TextContent, ImageContent, EventContent

router = APIRouter()
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@router.post("/create-content")
async def create_content(oshi_id: UUID, content: ContentData):
    try:
        # content テーブルに挿入
        content_data = {
            "oshi_id": str(oshi_id),
            "type": content.type,
            "order_index": content.order_index,
        }
        response = supabase.table("content").insert(content_data).execute()
        content_id = response.data[0]["id"]

        # テキストデータの場合
        if isinstance(content, TextContent):
            text_data = {
                "id": content_id,
                "text": content.text,
                "font_size": content.fontSize,
                "alignment": content.alignment,
            }
            supabase.table("text_data").insert(text_data).execute()

        # 画像データの場合
        elif isinstance(content, ImageContent):
            image_data = {
                "id": content_id,
                "src": content.src,
                "size": content.size,
            }
            supabase.table("image_data").insert(image_data).execute()

        # イベントデータの場合
        elif isinstance(content, EventContent):
            event_data = {
                "id": content_id,
                "title": content.title,
                "start_date": content.start_date,
                "end_date": content.end_date,
            }
            supabase.table("event_data").insert(event_data).execute()

        return {"message": "Content created successfully", "content_id": content_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-content")
async def fetch_content(oshi_id: UUID):
    try:
        # content テーブルからデータを取得
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