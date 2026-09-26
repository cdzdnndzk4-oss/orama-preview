"""PostgreSQL catalog; SQLite is permitted only for isolated local tests."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(72), primary_key=True)
    brand: Mapped[str] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120))
    color_code: Mapped[str | None] = mapped_column(String(40))
    frame_color: Mapped[str | None] = mapped_column(String(120))
    material: Mapped[str | None] = mapped_column(String(120))
    material_review: Mapped[str] = mapped_column(String(32), default="pending_review")
    audience: Mapped[str | None] = mapped_column(String(60))
    audience_review: Mapped[str] = mapped_column(String(32), default="pending_review")
    category: Mapped[str] = mapped_column(String(60))
    selection: Mapped[bool] = mapped_column(Boolean, default=False)
    price_cents: Mapped[int] = mapped_column(Integer)
    lens: Mapped[int] = mapped_column(Integer)
    bridge: Mapped[int] = mapped_column(Integer)
    temple: Mapped[int] = mapped_column(Integer)
    availability: Mapped[dict] = mapped_column(JSON, default=dict)
    description: Mapped[str] = mapped_column(Text, default="")
    description_review: Mapped[str] = mapped_column(String(32), default="pending_review")
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    legacy_images: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    photos: Mapped[list["Photo"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (UniqueConstraint("product_id", "view"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    view: Mapped[str] = mapped_column(String(20))
    original_key: Mapped[str] = mapped_column(String(200))
    processed_key: Mapped[str | None] = mapped_column(String(200))
    chosen: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    product: Mapped[Product] = relationship(back_populates="photos")


class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Session(Base):
    __tablename__ = "admin_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id"))
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
