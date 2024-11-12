from pydantic import BaseModel
from typing import List, Union

class TextContent(BaseModel):
    type: str
    text: str
    fontSize: int
    alignment: str
    order_index: int

class ImageContent(BaseModel):
    type: str
    src: str
    size: int
    order_index: int

class EventContent(BaseModel):
    type: str
    title: str
    start_date: str
    end_date: Union[str, None]
    order_index: int

ContentData = Union[TextContent, ImageContent, EventContent]

class CreateContentRequest(BaseModel):
    email: str
    oshi_name: str
    content: List[ContentData]  # コンテンツのリストとして受け取る

class FetchContentRequest(BaseModel):
    email: str
    oshi_name: str