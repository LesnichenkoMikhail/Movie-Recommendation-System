import math
import random
from collections import defaultdict

from sqlalchemy import select

from core.decorators import timed
from database.models import Rating
from recommender.config import BASELINE_MODELS, LIKE_THRESHOLD, MODELS
from recommender.context import UserContext
from recommender.engine import get_catalog
from recommender.evaluation import METRIC_KEYS, evaluate_all
from recommender.ratings import RatingMatrix
from recommender.recommenders import build_recommender

DEFAULT_NEGATIVES = 100


def mean(values):
    return sum(values) / len(values) if values else 0.0


def confidence_interval(values):
    """Полуширина 95% доверительного интервала для среднего (нормальное приближение)."""
    if len(values) < 2:
        return 0.0
    average = mean(values)
    variance = sum((value - average) ** 2 for value in values) / (len(values) - 1)
    return 1.96 * math.sqrt(variance / len(values))


def split_user_ratings(ratings, test_ratio, generator):
    """Делит оценки пользователя на обучающую и отложенную части.

    Если среди отложенных нет ни одного понравившегося фильма, но он есть в обучающей части,
    один такой фильм переносится в отложенные, а взамен в обучение уходит непонравившийся.
    Размеры частей при этом не меняются. Возвращает None, если понравившихся фильмов нет совсем.
    """
    movie_ids = sorted(ratings)
    generator.shuffle(movie_ids)
    cut = min(max(1, int(len(movie_ids) * test_ratio)), len(movie_ids) - 1)
    if cut < 1:
        return None
    test_ids, train_ids = movie_ids[:cut], movie_ids[cut:]

    def liked(movie_id):
        return ratings[movie_id] >= LIKE_THRESHOLD

    if not any(liked(movie_id) for movie_id in test_ids):
        promoted = next((movie_id for movie_id in train_ids if liked(movie_id)), None)
        if promoted is None:
            return None
        demoted = test_ids[0]
        test_ids = [promoted] + test_ids[1:]
        train_ids = [demoted if movie_id == promoted else movie_id for movie_id in train_ids]
    return train_ids, test_ids


def rank_candidates(scores, catalog, candidate_ids, generator, k):
    """Сортирует кандидатов по убыванию оценки; равные оценки расходятся случайно."""
    order = list(candidate_ids)
    generator.shuffle(order)
    order.sort(key=lambda movie_id: scores[catalog[movie_id]], reverse=True)
    return order[:k]


def model_labels():
    return {**MODELS, **BASELINE_MODELS}


@timed("benchmark")
def run_benchmark(db, k=10, min_ratings=8, test_ratio=0.3, max_users=40, seed=42, negatives=DEFAULT_NEGATIVES):
    """Оценивает модели на отложенных оценках.

    negatives > 0: каждая модель ранжирует отложенные фильмы пользователя вместе с `negatives`
    случайными фильмами, которые он не оценивал (и которые оценил кто-то из пользователей).
    negatives = 0: модель ранжирует весь каталог за вычетом уже виденного.
    """
    empty = {"k": k, "protocol": "sampled" if negatives else "full", "negatives": negatives,
             "users_eligible": 0, "users_evaluated": 0, "users_skipped": 0, "models": []}
    catalog = get_catalog(db)
    rows = db.execute(select(Rating.user_id, Rating.movie_id, Rating.rating)).all()
    if catalog is None or not rows:
        return empty

    by_user = defaultdict(dict)
    for user_id, movie_id, value in rows:
        by_user[user_id][movie_id] = float(value)

    eligible = sorted(user_id for user_id, items in by_user.items() if len(items) >= min_ratings)
    selector = random.Random(seed)
    selector.shuffle(eligible)
    selected = eligible[:max_users]

    item_pool = sorted({movie_id for _, movie_id, _ in rows if movie_id in catalog})
    full_matrix = RatingMatrix.from_rows(catalog, rows)
    names = list(MODELS) + list(BASELINE_MODELS)
    collected = {name: {key: [] for key in METRIC_KEYS} for name in names}
    evaluated = 0

    for user_id in selected:
        generator = random.Random(f"{seed}-{user_id}")
        split = split_user_ratings(by_user[user_id], test_ratio, generator)
        if split is None:
            continue
        train_ids, test_ids = split
        relevant = [movie_id for movie_id in test_ids if by_user[user_id][movie_id] >= LIKE_THRESHOLD]
        train = {movie_id: by_user[user_id][movie_id] for movie_id in train_ids}
        matrix = full_matrix.hide(user_id, test_ids)
        context = UserContext(catalog, train, matrix, {}, train_ids)

        if negatives:
            known = set(by_user[user_id])
            available = [movie_id for movie_id in item_pool if movie_id not in known]
            sampled = generator.sample(available, min(negatives, len(available)))
            candidate_ids = [movie_id for movie_id in test_ids if movie_id in catalog] + sampled
        else:
            candidate_ids = [catalog.ids[position] for position in context.candidates]
        if not candidate_ids:
            continue

        for name in names:
            if name in BASELINE_MODELS:
                shuffled = list(candidate_ids)
                generator.shuffle(shuffled)
                recommended = shuffled[:k]
            else:
                scores = build_recommender(name, context.enough).score(context)
                recommended = rank_candidates(scores, catalog, candidate_ids, generator, k)
            for key, value in evaluate_all(recommended, relevant, k).items():
                collected[name][key].append(value)
        evaluated += 1

    if not evaluated:
        return {**empty, "users_eligible": len(eligible), "users_skipped": len(selected)}

    models = []
    for name, values in collected.items():
        item = {"model": name, **{key: mean(values[key]) for key in METRIC_KEYS},
                "ci": {key: confidence_interval(values[key]) for key in METRIC_KEYS}}
        models.append(item)
    return {"k": k, "protocol": "sampled" if negatives else "full", "negatives": negatives,
            "users_eligible": len(eligible), "users_evaluated": evaluated,
            "users_skipped": len(selected) - evaluated, "models": models}


def main():
    import argparse

    from database.connection import SessionLocal

    parser = argparse.ArgumentParser(description="Оценка качества моделей из командной строки")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--min-ratings", type=int, default=8)
    parser.add_argument("--test-ratio", type=float, default=0.3)
    parser.add_argument("--max-users", type=int, default=40)
    parser.add_argument("--negatives", type=int, default=DEFAULT_NEGATIVES, help="0 = ранжировать весь каталог")
    parser.add_argument("--seed", type=int, default=42)
    arguments = parser.parse_args()

    with SessionLocal() as db:
        result = run_benchmark(db, k=arguments.k, min_ratings=arguments.min_ratings,
                               test_ratio=arguments.test_ratio, max_users=arguments.max_users,
                               seed=arguments.seed, negatives=arguments.negatives)
    if not result["models"]:
        raise SystemExit("Недостаточно данных: нужны пользователи с оценками (python -m etl.seed_demo).")
    labels = model_labels()
    print(f"Пользователей: {result['users_evaluated']}, K={result['k']}, негативов: {result['negatives']}")
    header = f"{'Модель':38}" + "".join(f"{key:>11}" for key in METRIC_KEYS)
    print(header)
    for item in result["models"]:
        print(f"{labels[item['model']]:38}" + "".join(f"{item[key]:>11.4f}" for key in METRIC_KEYS))


if __name__ == "__main__":
    main()
