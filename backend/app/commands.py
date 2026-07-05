"""
CLI commands for Flask application.
Usage:
  flask create-admin <name> <email> <password> <is_super_admin>
  flask init-db
  flask seed-demo
  flask repair-alembic
"""
import click
from flask.cli import with_appcontext

from .extensions import db


# ─── create-admin ─────────────────────────────────────────────────────────────

@click.command('create-admin')
@click.argument('name')
@click.argument('email')
@click.argument('password')
@click.argument('super_admin', default='false')
@with_appcontext
def create_admin(name: str, email: str, password: str, super_admin: str):
    """Create an admin user. SUPER_ADMIN: true or false."""
    from .models import User

    is_super = super_admin.strip().lower() in ('true', '1', 'yes')
    role = 'super_admin' if is_super else 'admin'

    existing = User.query.filter_by(email=email).first()
    if existing:
        click.echo(f'[!] User with email "{email}" already exists.')
        return

    user = User(name=name, email=email, role=role, is_active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(
        f'[+] {role} user "{name}" <{email}> created (id={user.id}).'
    )


# ─── init-db ──────────────────────────────────────────────────────────────────

@click.command('init-db')
@with_appcontext
def init_db():
    """Create all database tables (development only)."""
    db.create_all()
    click.echo('[+] Database tables created.')


# ─── seed-demo ────────────────────────────────────────────────────────────────

@click.command('seed-demo')
@with_appcontext
def seed_demo():
    """Seed the database with demo data for the library catalog."""
    from .models import User, Book

    # Admin user
    if not User.query.filter_by(email='admin@biblioteca.uy').first():
        admin = User(
            name='Admin Biblioteca',
            email='admin@biblioteca.uy',
            role='admin',
            is_active=True,
        )
        admin.set_password('Admin1234!')
        db.session.add(admin)
        click.echo('[+] Admin user created: admin@biblioteca.uy / Admin1234!')

    # Sample books – Biblioteca Municipal Lavalleja
    sample_books = [
        {
            'title': 'Cien años de soledad',
            'author': 'Gabriel García Márquez',
            'isbn': '978-84-376-0494-7',
            'genre': 'Novela',
            'year': 1967,
            'publisher': 'Editorial Sudamericana',
            'total_copies': 3,
            'available_copies': 2,
            'description': 'Obra cumbre del realismo mágico latinoamericano.',
            'location': 'Estante A-1',
        },
        {
            'title': 'El túnel',
            'author': 'Ernesto Sábato',
            'isbn': '978-950-731-000-1',
            'genre': 'Novela',
            'year': 1948,
            'publisher': 'Sur',
            'total_copies': 2,
            'available_copies': 2,
            'description': 'Novela psicológica del escritor argentino.',
            'location': 'Estante A-2',
        },
        {
            'title': 'La vorágine',
            'author': 'José Eustasio Rivera',
            'isbn': '978-958-05-0032-4',
            'genre': 'Novela',
            'year': 1924,
            'publisher': 'Cromos',
            'total_copies': 1,
            'available_copies': 0,
            'description': 'Clásico de la literatura latinoamericana.',
            'location': 'Estante A-3',
        },
        {
            'title': 'Historia del Uruguay',
            'author': 'Eduardo Acevedo',
            'isbn': None,
            'genre': 'Historia',
            'year': 1933,
            'publisher': 'A. Barreiro y Ramos',
            'total_copies': 2,
            'available_copies': 2,
            'description': 'Obra de referencia sobre la historia del Uruguay.',
            'location': 'Estante B-1',
        },
        {
            'title': 'Ariel',
            'author': 'José Enrique Rodó',
            'isbn': '978-950-895-080-7',
            'genre': 'Ensayo',
            'year': 1900,
            'publisher': 'Dornaleche y Reyes',
            'total_copies': 3,
            'available_copies': 3,
            'description': 'Ensayo clásico del modernismo latinoamericano.',
            'location': 'Estante C-1',
        },
    ]

    added = 0
    for b in sample_books:
        if not Book.query.filter_by(title=b['title']).first():
            book = Book(**b)
            db.session.add(book)
            added += 1

    db.session.commit()
    click.echo(f'[+] {added} demo books added.')


# ─── repair-alembic ───────────────────────────────────────────────────────────

@click.command('repair-alembic')
@with_appcontext
def repair_alembic():
    """Stamp alembic_version to head (use when migrations are out of sync)."""
    from flask_migrate import stamp
    stamp()
    click.echo('[+] Alembic stamped to head.')
