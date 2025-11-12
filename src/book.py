# src/book.py
from dataclasses import dataclass, asdict

@dataclass
class Book:
    title: str
    author: str
    isbn: str
    genre: str
    quantity: int

    def to_dict(self):
        return asdict(self)

    def update(self, title=None, author=None, genre=None, quantity=None):
        if title is not None:
            self.title = title
        if author is not None:
            self.author = author
        if genre is not None:
            self.genre = genre
        if quantity is not None:
            if quantity < 0:
                raise ValueError("Quantity cannot be negative")
            self.quantity = quantity

    def is_available(self):
        return self.quantity > 0
