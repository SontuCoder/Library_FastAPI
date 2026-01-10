from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
from enum import Enum

class BookRequest_Status(str, Enum):
    requested = "requested"
    approved = "approved"
    rejected = "rejected"
    returned = "returned"
    renewed = "renewed"
    return_requested = "return_requested"
    renew_requested = "renew_requested"
    renew_rejected = "renew_rejected"

class IssuedBook(BaseModel):
    email: EmailStr
    book_id: str
    issue_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    request_date: datetime = datetime.utcnow()
    status: BookRequest_Status = BookRequest_Status.requested
    previous_status: Optional[BookRequest_Status] = None


class request_Book(BaseModel):
    book_id: str

class approve_Reject_Book_Request(BaseModel):
    request_id: str
    action: str


class BookCategori(str, Enum):
    math = "mathematics"
    cs = "computer_science"
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

