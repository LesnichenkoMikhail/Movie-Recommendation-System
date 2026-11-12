from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


def utcnow():
    return datetime.now(timezone.utc)


class ReprMixin:
    repr_fields = ("id",)

    def __repr__(self):
        values = ", ".join(f"{name}={getattr(self, name, None)!r}" for name in self.repr_fields)
        return f"{type(self).__name__}({values})"


class User(ReprMixin, Base):
    __tablename__ = "users"
    repr_fields = ("id", "name")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    preferences = relationship("UserGenrePreference", back_populates="user", cascade="all, delete-orphan")


class Movie(ReprMixin, Base):
    __tablename__ = "movies"
    repr_fields = ("id", "title", "release_year")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    original_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    release_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    vote_average: Mapped[float] = mapped_column(Float, default=0.0)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tagline: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres_text: Mapped[str] = mapped_column(Text, default="")
    genres = relationship("Genre", secondary="movie_genres", back_populates="movies")
    ratings = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")


class Genre(ReprMixin, Base):
    __tablename__ = "genres"
    repr_fields = ("id", "name")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    movies = relationship("Movie", secondary="movie_genres", back_populates="genres")


class MovieGenre(Base):
    __tablename__ = "movie_genres"
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)


class UserGenrePreference(ReprMixin, Base):
    __tablename__ = "user_genre_preferences"
    repr_fields = ("user_id", "genre_id", "weight")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user = relationship("User", back_populates="preferences")
    genre = relationship("Genre")


class Rating(ReprMixin, Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_rating_user_movie"),
        CheckConstraint("rating >= 0.5 AND rating <= 5.0", name="ck_rating_range"),
    )
    repr_fields = ("user_id", "movie_id", "rating")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    rating: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    movie = relationship("Movie", back_populates="ratings")


class Interaction(ReprMixin, Base):
    __tablename__ = "interactions"
    __table_args__ = (Index("ix_interactions_user_time", "user_id", "timestamp"),)
    repr_fields = ("user_id", "movie_id", "action")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Recommendation(ReprMixin, Base):
    __tablename__ = "recommendations"
    repr_fields = ("id", "user_id", "movie_id", "model")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    model: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    feedback = relationship("RecommendationFeedback", back_populates="recommendation", cascade="all, delete-orphan")


class RecommendationFeedback(ReprMixin, Base):
    __tablename__ = "recommendation_feedback"
    repr_fields = ("id", "recommendation_id", "feedback")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"), index=True)
    feedback: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    recommendation = relationship("Recommendation", back_populates="feedback")


class ModelRun(ReprMixin, Base):
    __tablename__ = "model_runs"
    repr_fields = ("id", "model_name", "ndcg_at_k")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(80))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    precision_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    ndcg_at_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
