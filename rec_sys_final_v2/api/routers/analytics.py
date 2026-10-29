from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Genre, Interaction, Movie, Rating, User
from recommender.catalog import split_genres

router = APIRouter(prefix="/analytics", tags=["analytics"])

COLUMNS = ["id", "title", "original_language", "release_year", "popularity", "vote_average", "vote_count",
           "revenue", "runtime", "genres_text"]
NUMERIC = ["release_year", "popularity", "vote_average", "vote_count", "revenue", "runtime"]
Axis = Literal["popularity", "vote_average", "vote_count", "revenue", "runtime"]
TOP_GROUPS = 8


class Filters:
    def __init__(self, genre: str | None = None, year_from: int | None = None, year_to: int | None = None,
                 min_votes: int = Query(0, ge=0)):
        self.genre = genre
        self.year_from = year_from
        self.year_to = year_to
        self.min_votes = min_votes

    def apply(self, frame):
        mask = frame["vote_count"] >= self.min_votes
        if self.year_from is not None:
            mask &= frame["release_year"] >= self.year_from
        if self.year_to is not None:
            mask &= frame["release_year"] <= self.year_to
        if self.genre:
            mask &= frame["genre_list"].map(lambda names: self.genre in names)
        return frame[mask]


def catalog_frame(db):
    rows = db.execute(select(
        Movie.id, Movie.title, Movie.original_language, Movie.release_year, Movie.popularity,
        Movie.vote_average, Movie.vote_count, Movie.revenue, Movie.runtime, Movie.genres_text,
    )).all()
    frame = pd.DataFrame([tuple(row) for row in rows], columns=COLUMNS)
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["genre_list"] = frame["genres_text"].fillna("").map(split_genres)
    return frame


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    first_year, last_year = db.execute(select(func.min(Movie.release_year), func.max(Movie.release_year))).one()
    return {
        "movies": db.scalar(select(func.count(Movie.id))) or 0,
        "genres": db.scalar(select(func.count(Genre.id))) or 0,
        "users": db.scalar(select(func.count(User.id))) or 0,
        "ratings": db.scalar(select(func.count(Rating.id))) or 0,
        "interactions": db.scalar(select(func.count(Interaction.id))) or 0,
        "year_min": first_year,
        "year_max": last_year,
    }


@router.get("/rating-distribution")
def rating_distribution(bins: int = Query(20, ge=5, le=50), filters: Filters = Depends(),
                        db: Session = Depends(get_db)):
    frame = filters.apply(catalog_frame(db))
    values = frame.loc[frame["vote_count"] > 0, "vote_average"].to_numpy(dtype=float)
    counts, edges = np.histogram(values, bins=bins, range=(0.0, 10.0))
    return {"edges": [round(float(edge), 3) for edge in edges], "counts": [int(count) for count in counts],
            "total": int(len(values))}


@router.get("/genres")
def genre_stats(metric: Literal["count", "avg_rating", "avg_popularity", "total_revenue"] = "count",
                top: int = Query(12, ge=3, le=30), filters: Filters = Depends(), db: Session = Depends(get_db)):
    frame = filters.apply(catalog_frame(db))
    exploded = frame.explode("genre_list").dropna(subset=["genre_list"])
    if exploded.empty:
        return []
    if metric == "count":
        series = exploded.groupby("genre_list").size()
    elif metric == "avg_rating":
        series = exploded[exploded["vote_count"] > 0].groupby("genre_list")["vote_average"].mean()
    elif metric == "avg_popularity":
        series = exploded.groupby("genre_list")["popularity"].mean()
    else:
        series = exploded.groupby("genre_list")["revenue"].sum()
    series = series.sort_values(ascending=False).head(top)
    return [{"genre": name, "value": round(float(value), 3)} for name, value in series.items()]


@router.get("/timeline")
def timeline(metric: Literal["count", "avg_rating", "total_revenue"] = "count", filters: Filters = Depends(),
             db: Session = Depends(get_db)):
    frame = filters.apply(catalog_frame(db)).dropna(subset=["release_year"])
    if frame.empty:
        return []
    grouped = frame.groupby("release_year")
    if metric == "count":
        series = grouped.size()
    elif metric == "avg_rating":
        series = frame[frame["vote_count"] > 0].groupby("release_year")["vote_average"].mean()
    else:
        series = grouped["revenue"].sum()
    return [{"year": int(year), "value": round(float(value), 3)} for year, value in series.sort_index().items()]


@router.get("/scatter")
def scatter(x: Axis = "popularity", y: Axis = "vote_average", color: Literal["genre", "language"] = "genre",
            limit: int = Query(400, ge=50, le=2000), filters: Filters = Depends(), db: Session = Depends(get_db)):
    frame = filters.apply(catalog_frame(db)).dropna(subset=[x, y])
    frame = frame[(frame[x] > 0) & (frame[y] > 0)].nlargest(limit, "popularity")
    if color == "genre":
        groups = frame["genre_list"].map(lambda names: names[0] if names else "Без жанра")
    else:
        groups = frame["original_language"].fillna("н/д")
    leaders = set(groups.value_counts().head(TOP_GROUPS).index)
    groups = groups.map(lambda name: name if name in leaders else "Другое")
    points = [
        {"title": title, "x": float(px), "y": float(py), "group": group,
         "year": None if pd.isna(year) else int(year)}
        for title, px, py, group, year in zip(frame["title"], frame[x], frame[y], groups, frame["release_year"])
    ]
    return {"x": x, "y": y, "points": points}
