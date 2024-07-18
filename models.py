from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True)
    city = Column(String, index=True)
