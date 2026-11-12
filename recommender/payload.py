def movie_payload(movie, score=None, model=None):
    return {
        "id": movie.id,
        "title": movie.title,
        "release_year": movie.release_year,
        "genres": movie.genres_text or "",
        "overview": movie.overview or "",
        "popularity": float(movie.popularity or 0),
        "vote_average": float(movie.vote_average or 0),
        "vote_count": int(movie.vote_count or 0),
        "runtime": movie.runtime,
        "original_language": movie.original_language,
        "tagline": movie.tagline,
        "score": float(score) if score is not None else None,
        "model": model,
    }
