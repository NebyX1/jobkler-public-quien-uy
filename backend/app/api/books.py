"""
Books API – Catálogo Biblioteca Municipal de Casa de la Cultura de Lavalleja
  GET    /api/books                – listar libros (paginado, filtros)
  GET    /api/books/<id>           – obtener libro
  GET    /api/books/<id>/availability – consultar disponibilidad
  POST   /api/books                – crear libro (admin)
  PUT    /api/books/<id>           – actualizar libro (admin)
  DELETE /api/books/<id>           – eliminar libro (admin)
"""
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import or_

from . import api_bp
from ..extensions import db
from ..models import Book, User


# ─── helpers ──────────────────────────────────────────────────────────────────

def _bad(msg: str, code: int = 400):
    return {"error": msg}, code


def _ok(data: dict, code: int = 200):
    return data, code


def _require_admin():
    """Returns (user, error_response). If error_response is not None, return it."""
    user_id = int(get_jwt_identity())
    user: User | None = User.query.get(user_id)
    if not user or not user.is_admin:
        return None, _bad("Permiso denegado. Se requiere rol de administrador.", 403)
    return user, None


def _require_full_token():
    """Verifica que el JWT sea de tipo 'access' completo, no pending 2FA."""
    claims = get_jwt()
    if claims.get("type") == "2fa_pending":
        return _bad("Autenticación incompleta. Verifique su código 2FA.", 403)
    return None


# ─── rutas ────────────────────────────────────────────────────────────────────

@api_bp.route('/books', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_books():
    """Lista libros con paginación y filtros opcionales."""
    err = _require_full_token()
    if err:
        return err

    page = max(1, request.args.get('page', 1, type=int))
    per_page = min(100, max(1, request.args.get('per_page', 20, type=int)))
    search = (request.args.get('search') or '').strip()
    genre = (request.args.get('genre') or '').strip()
    availability = request.args.get('availability', 'all')

    query = Book.query

    if search:
        like = f'%{search}%'
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.isbn.ilike(like),
                Book.publisher.ilike(like),
            )
        )

    if genre:
        query = query.filter(Book.genre.ilike(f'%{genre}%'))

    if availability == 'available':
        query = query.filter(Book.available_copies > 0)
    elif availability == 'unavailable':
        query = query.filter(Book.available_copies == 0)

    query = query.order_by(Book.title.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return _ok({
        'items': [b.to_dict() for b in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages,
    })


@api_bp.route('/books/<int:book_id>', methods=['GET'], strict_slashes=False)
@jwt_required()
def get_book(book_id: int):
    err = _require_full_token()
    if err:
        return err

    book: Book | None = Book.query.get(book_id)
    if not book:
        return _bad("Libro no encontrado.", 404)

    return _ok({'book': book.to_dict()})


@api_bp.route('/books/<int:book_id>/availability', methods=['GET'], strict_slashes=False)
@jwt_required()
def check_availability(book_id: int):
    """Consulta rápida de disponibilidad de un libro."""
    err = _require_full_token()
    if err:
        return err

    book: Book | None = Book.query.get(book_id)
    if not book:
        return _bad("Libro no encontrado.", 404)

    return _ok({
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'total_copies': book.total_copies,
        'available_copies': book.available_copies,
        'is_available': book.is_available,
    })


@api_bp.route('/books', methods=['POST'], strict_slashes=False)
@jwt_required()
def create_book():
    err = _require_full_token()
    if err:
        return err

    _, err = _require_admin()
    if err:
        return err

    body = request.get_json(silent=True) or {}

    title = (body.get('title') or '').strip()
    author = (body.get('author') or '').strip()
    if not title or not author:
        return _bad("El título y el autor son obligatorios.")

    isbn = (body.get('isbn') or '').strip() or None
    if isbn and Book.query.filter_by(isbn=isbn).first():
        return _bad("Ya existe un libro con ese ISBN.")

    total = int(body.get('total_copies') or 1)
    if total < 1:
        return _bad("La cantidad de ejemplares debe ser al menos 1.")

    book = Book(
        title=title,
        author=author,
        isbn=isbn,
        genre=(body.get('genre') or '').strip() or None,
        year=body.get('year') or None,
        publisher=(body.get('publisher') or '').strip() or None,
        total_copies=total,
        available_copies=total,
        description=(body.get('description') or '').strip() or None,
        location=(body.get('location') or '').strip() or None,
    )
    db.session.add(book)
    db.session.commit()

    return _ok({'book': book.to_dict()}, 201)


@api_bp.route('/books/<int:book_id>', methods=['PUT'], strict_slashes=False)
@jwt_required()
def update_book(book_id: int):
    err = _require_full_token()
    if err:
        return err

    _, err = _require_admin()
    if err:
        return err

    book: Book | None = Book.query.get(book_id)
    if not book:
        return _bad("Libro no encontrado.", 404)

    body = request.get_json(silent=True) or {}

    if 'title' in body:
        title = (body['title'] or '').strip()
        if not title:
            return _bad("El título no puede estar vacío.")
        book.title = title

    if 'author' in body:
        author = (body['author'] or '').strip()
        if not author:
            return _bad("El autor no puede estar vacío.")
        book.author = author

    if 'isbn' in body:
        isbn = (body['isbn'] or '').strip() or None
        if isbn and isbn != book.isbn:
            existing = Book.query.filter_by(isbn=isbn).first()
            if existing and existing.id != book_id:
                return _bad("Ya existe un libro con ese ISBN.")
        book.isbn = isbn

    if 'genre' in body:
        book.genre = (body['genre'] or '').strip() or None

    if 'year' in body:
        book.year = body['year'] or None

    if 'publisher' in body:
        book.publisher = (body['publisher'] or '').strip() or None

    if 'description' in body:
        book.description = (body['description'] or '').strip() or None

    if 'location' in body:
        book.location = (body['location'] or '').strip() or None

    if 'total_copies' in body:
        total = int(body['total_copies'] or 1)
        if total < 1:
            return _bad("La cantidad de ejemplares debe ser al menos 1.")
        diff = total - book.total_copies
        book.total_copies = total
        book.available_copies = max(0, book.available_copies + diff)

    if 'available_copies' in body:
        avail = int(body['available_copies'] or 0)
        if avail < 0 or avail > book.total_copies:
            return _bad(
                f"Los ejemplares disponibles deben estar entre 0 y {book.total_copies}."
            )
        book.available_copies = avail

    db.session.commit()
    return _ok({'book': book.to_dict()})


@api_bp.route('/books/<int:book_id>', methods=['DELETE'], strict_slashes=False)
@jwt_required()
def delete_book(book_id: int):
    err = _require_full_token()
    if err:
        return err

    _, err = _require_admin()
    if err:
        return err

    book: Book | None = Book.query.get(book_id)
    if not book:
        return _bad("Libro no encontrado.", 404)

    db.session.delete(book)
    db.session.commit()

    return _ok({'message': f'Libro "{book.title}" eliminado correctamente.'})


@api_bp.route('/books/genres', methods=['GET'], strict_slashes=False)
@jwt_required()
def list_genres():
    """Devuelve la lista de géneros únicos registrados."""
    err = _require_full_token()
    if err:
        return err

    genres = (
        db.session.query(Book.genre)
        .filter(Book.genre.isnot(None))
        .distinct()
        .order_by(Book.genre.asc())
        .all()
    )
    return _ok({'genres': [g[0] for g in genres if g[0]]})
