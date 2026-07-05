"""
IDL Boilerplate – Flask HTML Admin Panel
Routes at /admin/...

Auth flow:
  GET/POST /admin/login    – email + password + math captcha → sends 2FA code
  GET/POST /admin/2fa      – verify 6-digit code → Flask-Login session
  GET      /admin/logout   – clear session

Protected routes (login_required + admin/super_admin role):
  GET      /admin/              → /admin/dashboard
  GET      /admin/dashboard     – KPI cards + recent activity
  GET/POST /admin/users         – list + create user
  GET/POST /admin/users/<id>/edit   – edit user
  POST     /admin/users/<id>/toggle  – toggle is_active
  GET      /admin/logs          – activity log (super_admin only)
"""
import random
from datetime import datetime, timezone
from functools import wraps

from flask import (
    render_template,
    redirect,
    url_for,
    request,
    flash,
    session,
    current_app,
    abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from . import admin_bp
from .forms import (
    AdminLoginForm,
    TwoFAForm,
    CreateUserForm,
    EditUserForm,
    CreateBookForm,
    EditBookForm,
)
from ..extensions import db
from ..models import User, TwoFactorCode, ActivityLog, Book
from ..services.email_service import send_2fa_email

# ─── helpers ──────────────────────────────────────────────────────────────────


def _require_admin_role(f):
    """Decorator: allow only admin and super_admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _require_super_admin(f):
    """Decorator: allow only super_admin users."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _log_admin(action: str, details: str | None = None):
    log = ActivityLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        username=current_user.name if current_user.is_authenticated else "SISTEMA",
        action=f"admin:{action}",
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
    )
    db.session.add(log)


# ─── login ────────────────────────────────────────────────────────────────────


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for("admin.dashboard"))

    # Generate fresh math captcha on every GET
    if request.method == "GET" or "captcha_answer" not in session:
        a, b = random.randint(1, 20), random.randint(1, 20)
        session["captcha_answer"] = a + b
        session["captcha_question"] = f"{a} + {b} = ?"

    form = AdminLoginForm()
    if form.validate_on_submit():
        # Validate captcha first (before DB hit)
        if form.captcha.data != session.get("captcha_answer"):
            flash("Verificación de seguridad incorrecta.", "error")
            a, b = random.randint(1, 20), random.randint(1, 20)
            session["captcha_answer"] = a + b
            session["captcha_question"] = f"{a} + {b} = ?"
            return render_template("login.html", form=form,
                                   captcha_question=session["captcha_question"])

        user: User | None = User.query.filter_by(
            email=form.email.data.strip().lower(), is_active=True
        ).first()

        if not user or not user.check_password(form.password.data):
            flash("Credenciales incorrectas.", "error")
            a, b = random.randint(1, 20), random.randint(1, 20)
            session["captcha_answer"] = a + b
            session["captcha_question"] = f"{a} + {b} = ?"
            return render_template("login.html", form=form,
                                   captcha_question=session["captcha_question"])

        if not user.is_admin:
            flash("No tienes permisos de administrador.", "error")
            return render_template("login.html", form=form,
                                   captcha_question=session["captcha_question"])

        # Invalidate old pending codes, generate new
        TwoFactorCode.query.filter_by(user_id=user.id).filter(
            TwoFactorCode.consumed_at.is_(None)
        ).delete(synchronize_session=False)
        code_entry = TwoFactorCode.generate(user)
        db.session.commit()

        try:
            send_2fa_email(user.email, user.name, code_entry.code,
                           current_app._get_current_object())
        except Exception as exc:
            current_app.logger.error(f"Admin 2FA email error for {user.email}: {exc}")

        session["admin_pending_user_id"] = user.id
        session.pop("captcha_answer", None)
        session.pop("captcha_question", None)
        return redirect(url_for("admin.verify_2fa"))

    return render_template(
        "login.html",
        form=form,
        captcha_question=session.get("captcha_question", "? + ? = ?"),
    )


# ─── 2FA verification ─────────────────────────────────────────────────────────


@admin_bp.route("/2fa", methods=["GET", "POST"])
def verify_2fa():
    pending_id = session.get("admin_pending_user_id")
    if not pending_id:
        return redirect(url_for("admin.login"))

    form = TwoFAForm()
    if form.validate_on_submit():
        code_entry: TwoFactorCode | None = (
            TwoFactorCode.query
            .filter_by(user_id=pending_id)
            .filter(TwoFactorCode.consumed_at.is_(None))
            .order_by(TwoFactorCode.id.desc())
            .first()
        )
        if not code_entry or not code_entry.is_valid(form.code.data.strip()):
            flash("Código inválido o expirado.", "error")
            return render_template("verify_2fa.html", form=form)

        code_entry.used = True
        user: User = User.query.get(pending_id)
        user.last_login = datetime.now(timezone.utc)

        login_user(user, remember=False)
        session.pop("admin_pending_user_id", None)

        _log_admin("login_success")
        db.session.commit()

        return redirect(url_for("admin.dashboard"))

    return render_template("verify_2fa.html", form=form)


# ─── logout ───────────────────────────────────────────────────────────────────


@admin_bp.route("/logout")
@login_required
def logout():
    _log_admin("logout")
    db.session.commit()
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("admin.login"))


# ─── dashboard ────────────────────────────────────────────────────────────────


@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@_require_admin_role
def dashboard():
    total_users = User.query.filter_by(is_active=True).count()
    total_books = Book.query.count()
    available_books = Book.query.filter(Book.available_copies > 0).count()

    recent_logs = (
        ActivityLog.query
        .order_by(ActivityLog.timestamp.desc())
        .limit(15)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_users=total_users,
        total_books=total_books,
        available_books=available_books,
        recent_logs=recent_logs,
    )


# ─── users ────────────────────────────────────────────────────────────────────


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@_require_admin_role
def users():
    form = CreateUserForm()

    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash("Ya existe un usuario con ese correo.", "error")
        else:
            new_user = User(
                name=form.name.data.strip(),
                email=form.email.data.strip().lower(),
                role=form.role.data,
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            _log_admin("create_user", f"email={new_user.email} role={new_user.role}")
            db.session.commit()
            flash(f"Usuario «{new_user.name}» creado exitosamente.", "success")
            return redirect(url_for("admin.users"))

    page = request.args.get("page", 1, type=int)
    per_page = 20
    pagination = (
        User.query
        .order_by(User.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    return render_template(
        "users.html",
        users=pagination.items,
        pagination=pagination,
        form=form,
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@_require_admin_role
def edit_user(user_id: int):
    user: User = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        if user.is_super_admin and not current_user.is_super_admin:
            flash("No puedes editar un super administrador.", "error")
            return redirect(url_for("admin.users"))

        user.name = form.name.data.strip()
        user.role = form.role.data

        _log_admin("edit_user", f"user_id={user.id} name={user.name} role={user.role}")
        db.session.commit()
        flash(f"Usuario «{user.name}» actualizado.", "success")
        return redirect(url_for("admin.users"))

    return render_template("edit_user.html", form=form, edit_user=user)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@_require_admin_role
def toggle_user(user_id: int):
    user: User = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "error")
        return redirect(url_for("admin.users"))
    if user.is_super_admin and not current_user.is_super_admin:
        flash("No puedes desactivar a un super administrador.", "error")
        return redirect(url_for("admin.users"))

    user.is_active = not user.is_active
    action = "activate_user" if user.is_active else "deactivate_user"
    _log_admin(action, f"user_id={user.id} email={user.email}")
    db.session.commit()
    state = "activado" if user.is_active else "desactivado"
    flash(f"Usuario «{user.name}» {state}.", "success")
    return redirect(url_for("admin.users"))


# ─── logs ─────────────────────────────────────────────────────────────────────


@admin_bp.route("/logs")
@login_required
@_require_super_admin
def logs():
    page = request.args.get("page", 1, type=int)
    per_page = 50
    action_filter = request.args.get("action", "").strip()
    user_filter = request.args.get("user_id", "", type=str).strip()

    q = ActivityLog.query
    if action_filter:
        q = q.filter(ActivityLog.action.ilike(f"%{action_filter}%"))
    if user_filter.isdigit():
        q = q.filter(ActivityLog.user_id == int(user_filter))

    pagination = q.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    all_users = User.query.order_by(User.name).all()

    return render_template(
        "logs.html",
        logs=pagination.items,
        pagination=pagination,
        action_filter=action_filter,
        user_filter=user_filter,
        all_users=all_users,
    )


# ─── books ────────────────────────────────────────────────────────────────────


@admin_bp.route("/books", methods=["GET", "POST"])
@login_required
@_require_admin_role
def books():
    form = CreateBookForm()

    if form.validate_on_submit():
        isbn = (form.isbn.data or "").strip() or None
        if isbn and Book.query.filter_by(isbn=isbn).first():
            flash("Ya existe un libro con ese ISBN.", "error")
        else:
            book = Book(
                title=form.title.data.strip(),
                author=form.author.data.strip(),
                isbn=isbn,
                genre=(form.genre.data or "").strip() or None,
                year=form.year.data or None,
                publisher=(form.publisher.data or "").strip() or None,
                total_copies=form.total_copies.data,
                available_copies=form.total_copies.data,
                description=(form.description.data or "").strip() or None,
                location=(form.location.data or "").strip() or None,
            )
            db.session.add(book)
            _log_admin("create_book", f"title={book.title}")
            db.session.commit()
            flash(f"Libro «{book.title}» creado exitosamente.", "success")
            return redirect(url_for("admin.books"))

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()
    query = Book.query
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.isbn.ilike(like),
            )
        )
    pagination = query.order_by(Book.title.asc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template(
        "admin/books.html",
        books=pagination.items,
        pagination=pagination,
        form=form,
        search=search,
    )


@admin_bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
@_require_admin_role
def edit_book(book_id: int):
    book: Book = Book.query.get_or_404(book_id)
    form = EditBookForm(obj=book)

    if form.validate_on_submit():
        isbn = (form.isbn.data or "").strip() or None
        existing = Book.query.filter_by(isbn=isbn).first() if isbn else None
        if existing and existing.id != book.id:
            flash("Ya existe un libro con ese ISBN.", "error")
        elif form.available_copies.data > form.total_copies.data:
            flash("Los ejemplares disponibles no pueden superar el total.", "error")
        else:
            book.title = form.title.data.strip()
            book.author = form.author.data.strip()
            book.isbn = isbn
            book.genre = (form.genre.data or "").strip() or None
            book.year = form.year.data or None
            book.publisher = (form.publisher.data or "").strip() or None
            book.total_copies = form.total_copies.data
            book.available_copies = form.available_copies.data
            book.description = (form.description.data or "").strip() or None
            book.location = (form.location.data or "").strip() or None
            _log_admin("edit_book", f"book_id={book.id} title={book.title}")
            db.session.commit()
            flash(f"Libro «{book.title}» actualizado.", "success")
            return redirect(url_for("admin.books"))

    return render_template("admin/edit_book.html", form=form, book=book)


@admin_bp.route("/books/<int:book_id>/delete", methods=["POST"])
@login_required
@_require_admin_role
def delete_book(book_id: int):
    book: Book = Book.query.get_or_404(book_id)
    title = book.title
    _log_admin("delete_book", f"book_id={book.id} title={title}")
    db.session.delete(book)
    db.session.commit()
    flash(f"Libro «{title}» eliminado.", "success")
    return redirect(url_for("admin.books"))
