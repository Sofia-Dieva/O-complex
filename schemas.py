from pydantic import BaseModel, Field

class SearchHistoryCreate(BaseModel):
    city: str

class SearchHistory(BaseModel):
    id: int
    ip_address: str
    city: str

    class Config:
        from_attributes = True

class CityCount(BaseModel):
    city: str
    count: int
