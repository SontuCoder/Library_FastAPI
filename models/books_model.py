from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
from enum import Enum

class IssuedBook(BaseModel):
    email: EmailStr
    book_id: str
    issue_date: datetime
    return_date: datetime


class BookCategori(str, Enum):
    math = "mathematics"
    cs = "computer science"
    physics = "physics"
    literature = "literature"
    others = "others"


class Books(BaseModel):
    title: str
    author: str
    description: str
    edition: int
    quantity : int
    available : Optional[int] = None
    category: List[BookCategori] = [BookCategori.others]
    added_at: datetime = datetime.utcnow()

class Delete_book(BaseModel):
    id:str
    quantity:int

