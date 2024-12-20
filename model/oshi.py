from pydantic import BaseModel
from typing import List

class SearchQuery(BaseModel):
    query: str
    
class OshiRequest(BaseModel):
    oshi_name: str
    
class UserOshiRequest(BaseModel):
    email: str
    oshi_names: List[str]  

class UserOshiAndGenresRequest(BaseModel):
    email: str
    oshi_name: str
    genre: str  