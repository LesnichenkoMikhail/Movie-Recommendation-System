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
