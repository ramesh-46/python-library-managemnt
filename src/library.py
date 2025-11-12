# src/library.py
from datetime import datetime, timedelta
from src.book import Book
from src.borrower import Borrower, BorrowedRecord
from typing import Dict, List, Optional
from pathlib import Path
import json


DEFAULT_DATA_FILE = Path(__file__).resolve().parents[1] / "data.json"


class Library:
    def __init__(self, loan_days: int = 14, data_file: Optional[str] = None):
        # books_by_isbn: isbn -> Book
        self.books_by_isbn: Dict[str, Book] = {}
        # borrowers_by_id: membership_id -> Borrower
        self.borrowers_by_id: Dict[str, Borrower] = {}
        self.loan_days = loan_days
        self.data_path = Path(data_file) if data_file else DEFAULT_DATA_FILE
        # load existing data (if any)
        self._load()

    # ---- Book management ----
    def add_book(self, title: str, author: str, isbn: str, genre: str, quantity: int):
        if isbn in self.books_by_isbn:
            # If exists, increment quantity
            book = self.books_by_isbn[isbn]
            book.update(quantity=book.quantity + quantity)
        else:
            book = Book(title=title, author=author, isbn=isbn, genre=genre, quantity=quantity)
            self.books_by_isbn[isbn] = book
        self._save()
        return book

    def update_book(self, isbn: str, **kwargs):
        if isbn not in self.books_by_isbn:
            raise KeyError("Book not found")
        book = self.books_by_isbn[isbn]
        book.update(**kwargs)
        self._save()
        return book

    def remove_book(self, isbn: str):
        if isbn not in self.books_by_isbn:
            raise KeyError("Book not found")
        del self.books_by_isbn[isbn]
        self._save()
        return True

    def get_book(self, isbn: str) -> Optional[Book]:
        return self.books_by_isbn.get(isbn)

    def list_books(self) -> List[Book]:
        return list(self.books_by_isbn.values())

    # ---- Borrower management ----
    def add_borrower(self, name: str, contact: str, membership_id: str = None):
        borrower = Borrower(name=name, contact=contact, membership_id=membership_id)
        self.borrowers_by_id[borrower.membership_id] = borrower
        self._save()
        return borrower

    def update_borrower(self, membership_id: str, **kwargs):
        if membership_id not in self.borrowers_by_id:
            raise KeyError("Borrower not found")
        borrower = self.borrowers_by_id[membership_id]
        borrower.update(**kwargs)
        self._save()
        return borrower

    def remove_borrower(self, membership_id: str):
        if membership_id not in self.borrowers_by_id:
            raise KeyError("Borrower not found")
        del self.borrowers_by_id[membership_id]
        self._save()
        return True

    def get_borrower(self, membership_id: str) -> Optional[Borrower]:
        return self.borrowers_by_id.get(membership_id)

    def list_borrowers(self) -> List[Borrower]:
        return list(self.borrowers_by_id.values())

    # ---- Borrow / Return ----
    def borrow_book(self, membership_id: str, isbn: str):
        if membership_id not in self.borrowers_by_id:
            raise KeyError("Borrower not found")
        if isbn not in self.books_by_isbn:
            raise KeyError("Book not found")

        book = self.books_by_isbn[isbn]
        if book.quantity <= 0:
            raise ValueError("No copies available")

        borrower = self.borrowers_by_id[membership_id]
        # create record
        borrowed_on = datetime.now()
        due_date = borrowed_on + timedelta(days=self.loan_days)
        record = BorrowedRecord(isbn=isbn, borrowed_on=borrowed_on, due_date=due_date)

        borrower.borrowed_books.append(record)
        book.quantity -= 1
        self._save()
        return record

    def return_book(self, membership_id: str, isbn: str):
        if membership_id not in self.borrowers_by_id:
            raise KeyError("Borrower not found")
        if isbn not in self.books_by_isbn:
            raise KeyError("Book not found")

        borrower = self.borrowers_by_id[membership_id]
        # Find the borrowed record
        found = None
        for rec in borrower.borrowed_books:
            if rec.isbn == isbn:
                found = rec
                break
        if not found:
            raise ValueError("This borrower did not borrow this book")

        borrower.borrowed_books.remove(found)
        self.books_by_isbn[isbn].quantity += 1
        self._save()
        # check overdue
        now = datetime.now()
        overdue = now > found.due_date
        return {"returned": True, "overdue": overdue, "due_date": found.due_date.isoformat()}

    # ---- Persistence ----
    def _load(self):
        # create file if missing
        if not self.data_path.exists():
            self._save()
            return
        try:
            with self.data_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}

        # load books
        for b in data.get('books', []):
            try:
                book = Book(**b)
                self.books_by_isbn[book.isbn] = book
            except Exception:
                # skip malformed
                continue

        # load borrowers
        for br in data.get('borrowers', []):
            try:
                borrowed = []
                for rec in br.get('borrowed_books', []):
                    borrowed.append(BorrowedRecord(
                        isbn=rec['isbn'],
                        borrowed_on=datetime.fromisoformat(rec['borrowed_on']),
                        due_date=datetime.fromisoformat(rec['due_date'])
                    ))
                borrower = Borrower(name=br['name'], contact=br['contact'], membership_id=br.get('membership_id'), borrowed_books=borrowed)
                self.borrowers_by_id[borrower.membership_id] = borrower
            except Exception:
                continue

    def _save(self):
        data = {
            'books': [b.to_dict() for b in self.books_by_isbn.values()],
            'borrowers': [br.to_dict() for br in self.borrowers_by_id.values()]
        }
        try:
            with self.data_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            # best-effort: ignore save errors (could log)
            pass

    # ---- Search & availability ----
    def search_books(self, query: str = "", field: str = "title"):
        q = query.strip().lower()
        results = []
        for book in self.books_by_isbn.values():
            if not q:
                results.append(book)
                continue
            if field == "title" and q in book.title.lower():
                results.append(book)
            elif field == "author" and q in book.author.lower():
                results.append(book)
            elif field == "genre" and q in book.genre.lower():
                results.append(book)
        return results

    def availability(self, isbn: str):
        book = self.books_by_isbn.get(isbn)
        if not book:
            raise KeyError("Book not found")
        return {"isbn": isbn, "available_copies": book.quantity}
