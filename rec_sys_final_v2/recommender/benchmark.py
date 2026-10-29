import random
from collections import defaultdict

from sqlalchemy import select

from core.decorators import timed
from database.models import Rating
from recommender.config import LIKE_THRESHOLD, MODELS
from recommender.context import UserContext
from recommender.engine import get_catalog, rank_scores
from recommender.evaluation import ndcg_at_k, precision_at_k, recall_at_k
from recommender.ratings import RatingMatrix
from recommender.recommenders import build_recommender


def mean(values):
    return sum(values) / len(values) if values else 0.0


@timed("benchmark")
def run_benchmark(db, k=10, min_ratings=8, test_ratio=0.3, max_users=40, seed=42):
    catalog = get_catalog(db)
    rows = db.execute(select(Rating.user_id, Rating.movie_id, Rating.rating)).all()
    if catalog is None or not rows:
        return {"k": k, "users_eligible": 0, "users_evaluated": 0, "models": []}

    by_user = defaultdict(dict)
    for user_id, movie_id, value in rows:
        by_user[user_id][movie_id] = float(value)

    eligible = sorted(user_id for user_id, items in by_user.items() if len(items) >= min_ratings)
    generator = random.Random(seed)
    generator.shuffle(eligible)
    selected = eligible[:max_users]

    full_matrix = RatingMatrix.from_rows(catalog, rows)
    collected = {name: {"precision": [], "recall": [], "ndcg": []} for name in MODELS}
    evaluated = 0

    for user_id in selected:
        movie_ids = sorted(by_user[user_id])
        generator.shuffle(movie_ids)
        cut = max(1, int(len(movie_ids) * test_ratio))
        test_ids, train_ids = movie_ids[:cut], movie_ids[cut:]
        relevant = [movie_id for movie_id in test_ids if by_user[user_id][movie_id] >= LIKE_THRESHOLD]
        if not relevant or not train_ids:
            continue
        train = {movie_id: by_user[user_id][movie_id] for movie_id in train_ids}
        matrix = full_matrix.hide(user_id, test_ids)
        context = UserContext(catalog, train, matrix, {}, train_ids)
        for name in MODELS:
            scores = build_recommender(name, context.enough).score(context)
            recommended = [item.movie_id for item in rank_scores(scores, context, name, k)]
            collected[name]["precision"].append(precision_at_k(recommended, relevant, k))
            collected[name]["recall"].append(recall_at_k(recommended, relevant, k))
            collected[name]["ndcg"].append(ndcg_at_k(recommended, relevant, k))
        evaluated += 1

    models = [
        {"model": name, "precision": mean(values["precision"]), "recall": mean(values["recall"]),
         "ndcg": mean(values["ndcg"])}
        for name, values in collected.items()
    ]
    return {"k": k, "users_eligible": len(eligible), "users_evaluated": evaluated,
            "models": models if evaluated else []}
