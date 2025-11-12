# src/borrower.py
from dataclasses import dataclass, asdict
from typing import List
import uuid
from datetime import datetime

@dataclass
class BorrowedRecord:
    isbn: str
    borrowed_on: datetime
    due_date: datetime

    def to_dict(self):
        return {
            "isbn": self.isbn,
            "borrowed_on": self.borrowed_on.isoformat(),
            "due_date": self.due_date.isoformat()
        }

@dataclass
class Borrower:
    name: str
    contact: str
    membership_id: str = None
    borrowed_books: List[BorrowedRecord] = None

    def __post_init__(self):
        if not self.membership_id:
            self.membership_id = str(uuid.uuid4())[:8]
        if self.borrowed_books is None:
            self.borrowed_books = []

    def to_dict(self):
        return {
            "name": self.name,
            "contact": self.contact,
            "membership_id": self.membership_id,
            "borrowed_books": [b.to_dict() for b in self.borrowed_books]
        }

    def update(self, name=None, contact=None):
        if name:
            self.name = name
        if contact:
            self.contact = contact
