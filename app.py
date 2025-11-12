
# app.py
try:
    from flask import Flask, jsonify, request, send_from_directory
except ModuleNotFoundError:
    raise SystemExit(
        "Missing dependency 'flask'. Install dependencies with: py -3 -m pip install -r requirements.txt"
    )

from src.library import Library
import os
from datetime import datetime

app = Flask(__name__, static_folder="src/static", static_url_path="/")
# allow CORS (safe for local dev). If Flask-Cors isn't installed we continue without it
try:
    from flask_cors import CORS
    # Explicitly allow all origins for /api/* (development only)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    cors_enabled = True
except Exception:
    cors_enabled = False
    print("Warning: flask_cors not installed; proceeding without Flask-Cors. To enable, run: py -3 -m pip install Flask-Cors")


@app.after_request
def add_cors_headers(response):
    # Ensure all necessary CORS headers are present for debugging
    response.headers.setdefault('Access-Control-Allow-Origin', '*')
    response.headers.setdefault('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.setdefault('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    return response

library = Library(loan_days=14)

# ---- Serve frontend ----
@app.route("/")
def index():
    return send_from_directory('src/static', 'index.html')

# ---- Book endpoints ----
@app.route("/api/books", methods=["GET", "POST"])
def books():
    if request.method == "GET":
        books = [b.to_dict() for b in library.list_books()]
        return jsonify({"books": books}), 200
    else:
        data = request.get_json()
        required = ["title", "author", "isbn", "genre", "quantity"]
        for r in required:
            if r not in data:
                return jsonify({"error": f"Missing {r}"}), 400
        try:
            book = library.add_book(
                title=data["title"],
                author=data["author"],
                isbn=data["isbn"],
                genre=data["genre"],
                quantity=int(data["quantity"])
            )
            return jsonify({"book": book.to_dict()}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@app.route("/api/books/<isbn>", methods=["GET", "PUT", "DELETE"])
def book_detail(isbn):
    if request.method == "GET":
        book = library.get_book(isbn)
        if not book:
            return jsonify({"error": "Book not found"}), 404
        return jsonify({"book": book.to_dict()}), 200
    elif request.method == "PUT":
        data = request.get_json()
        try:
            book = library.update_book(isbn, **data)
            return jsonify({"book": book.to_dict()}), 200
        except KeyError:
            return jsonify({"error": "Book not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:  # DELETE
        try:
            library.remove_book(isbn)
            return jsonify({"deleted": True}), 200
        except KeyError:
            return jsonify({"error": "Book not found"}), 404

# ---- Borrower endpoints ----
@app.route("/api/borrowers", methods=["GET", "POST"])
def borrowers():
    if request.method == "GET":
        borrowers = [b.to_dict() for b in library.list_borrowers()]
        return jsonify({"borrowers": borrowers}), 200
    else:
        data = request.get_json()
        if not data.get("name") or not data.get("contact"):
            return jsonify({"error": "Missing name or contact"}), 400
        borrower = library.add_borrower(name=data["name"], contact=data["contact"], membership_id=data.get("membership_id"))
        return jsonify({"borrower": borrower.to_dict()}), 201

@app.route("/api/borrowers/<membership_id>", methods=["GET", "PUT", "DELETE"])
def borrower_detail(membership_id):
    if request.method == "GET":
        borrower = library.get_borrower(membership_id)
        if not borrower:
            return jsonify({"error": "Borrower not found"}), 404
        return jsonify({"borrower": borrower.to_dict()}), 200
    elif request.method == "PUT":
        data = request.get_json()
        try:
            borrower = library.update_borrower(membership_id, **data)
            return jsonify({"borrower": borrower.to_dict()}), 200
        except KeyError:
            return jsonify({"error": "Borrower not found"}), 404
    else:
        try:
            library.remove_borrower(membership_id)
            return jsonify({"deleted": True}), 200
        except KeyError:
            return jsonify({"error": "Borrower not found"}), 404

# ---- Borrow & return ----
@app.route("/api/borrow", methods=["POST"])
def borrow():
    data = request.get_json()
    if not data or "membership_id" not in data or "isbn" not in data:
        return jsonify({"error": "membership_id and isbn required"}), 400
    try:
        record = library.borrow_book(membership_id=data["membership_id"], isbn=data["isbn"])
        return jsonify({"borrowed": record.to_dict()}), 200
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/return", methods=["POST"])
def return_book():
    data = request.get_json()
    if not data or "membership_id" not in data or "isbn" not in data:
        return jsonify({"error": "membership_id and isbn required"}), 400
    try:
        res = library.return_book(membership_id=data["membership_id"], isbn=data["isbn"])
        return jsonify(res), 200
    except KeyError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- Search ----
@app.route("/api/search", methods=["GET"])
def search():
    q = request.args.get("q", "")
    field = request.args.get("field", "title")
    results = library.search_books(query=q, field=field)
    return jsonify({"results": [b.to_dict() for b in results]}), 200

# ---- Availability ----
@app.route("/api/availability/<isbn>", methods=["GET"])
def availability(isbn):
    try:
        a = library.availability(isbn)
        return jsonify(a), 200
    except KeyError:
        return jsonify({"error": "Book not found"}), 404

# ---- Debug route to seed data (optional) ----
@app.route("/api/seed", methods=["POST"])
def seed():
    try:
        library.add_book(title="1984", author="George Orwell", isbn="9780451524935", genre="Dystopia", quantity=3)
        library.add_book(title="Python Crash Course", author="Eric Matthes", isbn="9781593279288", genre="Programming", quantity=2)
        b = library.add_borrower(name="Alice", contact="alice@example.com")
        return jsonify({"seeded": True, "sample_borrower": b.to_dict()}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'ok', 'time': datetime.utcnow().isoformat()}), 200


@app.route('/api/headers', methods=['GET'])
def headers():
    # Return request headers for debugging CORS/origin
    return jsonify({k: v for k, v in request.headers.items()}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)




