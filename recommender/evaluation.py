import math


def precision_at_k(recommended, relevant, k=10):
    recommended = list(recommended)[:k]
    if not recommended:
        return 0.0
    relevant = set(relevant)
    return sum(1 for item in recommended if item in relevant) / len(recommended)


def recall_at_k(recommended, relevant, k=10):
    relevant = set(relevant)
    if not relevant:
        return 0.0
    recommended = list(recommended)[:k]
    return sum(1 for item in recommended if item in relevant) / len(relevant)


def ndcg_at_k(recommended, relevant, k=10):
    relevant = set(relevant)
    recommended = list(recommended)[:k]
    dcg = sum(1.0 / math.log2(position + 2) for position, item in enumerate(recommended) if item in relevant)
    ideal_hits = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(position + 2) for position in range(ideal_hits))
    return dcg / ideal if ideal else 0.0


def evaluate(recommended, relevant, k=10):
    return {
        f"precision@{k}": precision_at_k(recommended, relevant, k),
        f"recall@{k}": recall_at_k(recommended, relevant, k),
        f"ndcg@{k}": ndcg_at_k(recommended, relevant, k),
    }


def hit_rate_at_k(recommended, relevant, k=10):
    relevant = set(relevant)
    return 1.0 if any(item in relevant for item in list(recommended)[:k]) else 0.0


def average_precision_at_k(recommended, relevant, k=10):
    relevant = set(relevant)
    if not relevant:
        return 0.0
    hits = 0
    total = 0.0
    for position, item in enumerate(list(recommended)[:k], start=1):
        if item in relevant:
            hits += 1
            total += hits / position
    return total / min(len(relevant), k)


def reciprocal_rank_at_k(recommended, relevant, k=10):
    relevant = set(relevant)
    for position, item in enumerate(list(recommended)[:k], start=1):
        if item in relevant:
            return 1.0 / position
    return 0.0


METRIC_KEYS = ("precision", "recall", "ndcg", "hit_rate", "map", "mrr")


def evaluate_all(recommended, relevant, k=10):
    return {
        "precision": precision_at_k(recommended, relevant, k),
        "recall": recall_at_k(recommended, relevant, k),
        "ndcg": ndcg_at_k(recommended, relevant, k),
        "hit_rate": hit_rate_at_k(recommended, relevant, k),
        "map": average_precision_at_k(recommended, relevant, k),
        "mrr": reciprocal_rank_at_k(recommended, relevant, k),
    }
