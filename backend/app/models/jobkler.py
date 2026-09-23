from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint, Index

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.String(64), primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    email_private = db.Column(db.String(254))
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    picture_url = db.Column(db.String(500))
    status = db.Column(db.String(16), nullable=False, default="active")
    is_moderator = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    identities = db.relationship("Identity", back_populates="account", cascade="all, delete-orphan")
    profile = db.relationship("Profile", back_populates="owner", uselist=False)

    __table_args__ = (CheckConstraint("status IN ('active', 'disabled')", name="ck_account_status"),)


class Identity(db.Model):
    __tablename__ = "identities"

    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(64), db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    provider = db.Column(db.String(32), nullable=False)
    issuer = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    account = db.relationship("Account", back_populates="identities")

    __table_args__ = (
        UniqueConstraint("provider", "issuer", "subject", name="uq_identity_provider_issuer_subject"),
        Index("ix_identity_account_id", "account_id"),
    )


class AuthSession(db.Model):
    __tablename__ = "auth_sessions"

    token_hash = db.Column(db.String(64), primary_key=True)
    account_id = db.Column(db.String(64), db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    provider = db.Column(db.String(32), nullable=False)
    csrf_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)
    account = db.relationship("Account")

    __table_args__ = (Index("ix_auth_sessions_account_expiry", "account_id", "expires_at"),)


class SeedState(db.Model):
    __tablename__ = "seed_state"

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.String(80), nullable=False)
    applied_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    description = db.Column(db.String(500), nullable=False, default="")
    icon = db.Column(db.String(40), nullable=False, default="Briefcase")
    featured = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), nullable=False, unique=True)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    localities = db.relationship("Locality", back_populates="department", cascade="all, delete-orphan")


class Locality(db.Model):
    __tablename__ = "localities"

    id = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    department_id = db.Column(db.String(80), db.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    department = db.relationship("Department", back_populates="localities")

    __table_args__ = (
        UniqueConstraint("department_id", "slug", name="uq_locality_department_slug"),
        Index("ix_localities_department", "department_id"),
    )


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.String(64), primary_key=True)
    slug = db.Column(db.String(180), nullable=False, unique=True)
    owner_id = db.Column(db.String(64), db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, unique=True)
    display_name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.String(80), db.ForeignKey("categories.id"), nullable=False)
    profession = db.Column(db.String(120), nullable=False)
    profession_normalized = db.Column(db.String(140), nullable=False)
    department_id = db.Column(db.String(80), db.ForeignKey("departments.id"), nullable=False)
    locality_id = db.Column(db.String(80), db.ForeignKey("localities.id"), nullable=False)
    short_description = db.Column(db.String(240), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(500), nullable=False, default="")
    phone = db.Column(db.String(40), nullable=False, default="")
    whatsapp = db.Column(db.String(40), nullable=False, default="")
    contact_email = db.Column(db.String(254), nullable=False, default="")
    website = db.Column(db.String(500), nullable=False, default="")
    instagram = db.Column(db.String(200), nullable=False, default="")
    address = db.Column(db.String(240), nullable=False, default="")
    service_area = db.Column(db.JSON, nullable=False, default=list)
    tags = db.Column(db.JSON, nullable=False, default=list)
    availability = db.Column(db.String(100), nullable=False, default="")
    years_experience = db.Column(db.Integer, nullable=False, default=0)
    featured = db.Column(db.Boolean, nullable=False, default=False)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    is_demo_fixture = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    status = db.Column(db.String(16), nullable=False, default="active")
    search_text = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = db.relationship("Account", back_populates="profile")
    category = db.relationship("Category")
    department = db.relationship("Department")
    locality = db.relationship("Locality")
    reviews = db.relationship("Review", back_populates="profile", cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_profile_status"),
        CheckConstraint("years_experience >= 0", name="ck_profile_experience_nonnegative"),
        Index("ix_profiles_public_search", "status", "department_id", "locality_id", "category_id"),
    )


class ProfileCoverage(db.Model):
    """Explicit, catalog-backed areas served by a profile."""

    __tablename__ = "profile_coverages"

    profile_id = db.Column(db.String(64), db.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    scope_key = db.Column(db.String(170), primary_key=True)
    department_id = db.Column(db.String(80), db.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    locality_id = db.Column(db.String(80), db.ForeignKey("localities.id", ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("(department_id IS NULL) != (locality_id IS NULL)", name="ck_profile_coverage_one_scope"),
        Index("ix_profile_coverages_locality", "locality_id"),
        Index("ix_profile_coverages_department", "department_id"),
    )


class ProfileSearchDocument(db.Model):
    __tablename__ = "profile_search_documents"

    profile_id = db.Column(db.String(64), db.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    source_hash = db.Column(db.String(64), nullable=False)
    search_text = db.Column(db.Text, nullable=False)
    profession = db.Column(db.Text, nullable=False, default="")
    category = db.Column(db.Text, nullable=False, default="")
    short_description = db.Column(db.Text, nullable=False, default="")
    description = db.Column(db.Text, nullable=False, default="")
    tags = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class ProfileSearchChunk(db.Model):
    __tablename__ = "profile_search_chunks"

    chunk_id = db.Column(db.String(64), primary_key=True)
    profile_id = db.Column(db.String(64), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    source_hash = db.Column(db.String(64), nullable=False)
    source_field = db.Column(db.String(32), nullable=False)
    literal_text = db.Column(db.Text, nullable=False)
    start_char = db.Column(db.Integer, nullable=False)
    end_char = db.Column(db.Integer, nullable=False)
    encoder_model = db.Column(db.String(160), nullable=False)
    encoder_revision = db.Column(db.String(64), nullable=False)
    vector_dimension = db.Column(db.Integer, nullable=False)
    vector_dtype = db.Column(db.String(24), nullable=False)
    vector_bytes = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_profile_search_chunks_profile_revision", "profile_id", "source_hash"),
        Index("ix_profile_search_chunks_encoder", "encoder_model", "encoder_revision"),
    )


class ProfileSearchIndexJob(db.Model):
    __tablename__ = "profile_search_index_jobs"

    id = db.Column(db.String(36), primary_key=True)
    profile_id = db.Column(db.String(64), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    source_hash = db.Column(db.String(64), nullable=False)
    encoder_model = db.Column(db.String(160), nullable=False)
    encoder_revision = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="pending")
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    last_error = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("profile_id", "source_hash", "encoder_model", "encoder_revision", name="uq_profile_index_revision"),
        CheckConstraint("status IN ('pending', 'running', 'succeeded', 'failed', 'superseded')", name="ck_profile_index_job_status"),
        Index("ix_profile_index_jobs_queue", "status", "next_attempt_at", "created_at"),
    )


class AdvancedSearchRateEvent(db.Model):
    __tablename__ = "advanced_search_rate_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account_id = db.Column(db.String(64), db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    __table_args__ = (Index("ix_advanced_search_rate_account_time", "account_id", "created_at"),)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.String(64), primary_key=True)
    profile_id = db.Column(db.String(64), db.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.String(64), db.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="published")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    profile = db.relationship("Profile", back_populates="reviews")
    author = db.relationship("Account")

    __table_args__ = (
        UniqueConstraint("profile_id", "author_id", name="uq_review_profile_author"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        CheckConstraint("status IN ('published', 'hidden')", name="ck_review_status"),
        Index("ix_reviews_profile_status", "profile_id", "status"),
        Index("ix_reviews_author", "author_id"),
    )
