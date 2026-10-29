MODELS = {
    "hybrid": "Гибридная модель",
    "popularity": "Популярные фильмы",
    "content": "По содержанию",
    "collaborative": "Коллаборативная фильтрация",
}

ACTIONS = ("view", "click", "skip", "like", "dislike", "rate")
SEEN_ACTIONS = ("view", "skip", "like", "dislike", "rate")
ACTION_DELTAS = {"like": 0.15, "dislike": -0.2, "view": 0.03, "skip": -0.03, "click": 0.02}

RATING_NEUTRAL = 3.0
FEEDBACK_NEUTRAL = 3
RATING_DELTA_FACTOR = 0.08
FEEDBACK_DELTA_FACTOR = 0.025

PREFERENCE_MIN = 0.1
PREFERENCE_MAX = 3.0
PREFERENCE_STEP = 0.25
INITIAL_PREFERENCE = 1.5
DEFAULT_GENRE_WEIGHT = 1.5
GENRE_ADJUSTMENT_SCALE = 0.18

MAX_LIMIT = 100
MIN_USERS_FOR_CF = 3
MIN_RATINGS_FOR_CF = 10
CATALOG_TTL_SECONDS = 300
LIKE_THRESHOLD = 4.0
