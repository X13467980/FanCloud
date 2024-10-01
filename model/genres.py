from pydantic import BaseModel

class UserGenres(BaseModel):
    email: str
    genres: list[str]    

class UserOshiGenresRequest(BaseModel):
    email: str   