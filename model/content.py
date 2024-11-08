from pydantic import BaseModel
from typing import Union

# テキストコンテンツモデル
class TextContent(BaseModel):
    type: str
    text: str
    fontSize: int
    alignment: str
    order_index: int

# 画像コンテンツモデル
class ImageContent(BaseModel):
    type: str
    src: str
    size: int
    order_index: int

# イベントコンテンツモデル
class EventContent(BaseModel):
    type: str
    title: str
    start_date: str
    end_date: Union[str, None]
    order_index: int

# Union型のContentData
ContentData = Union[TextContent, ImageContent, EventContent]