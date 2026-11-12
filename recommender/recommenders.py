from abc import ABC, abstractmethod

import numpy as np


def normalize(values):
    if len(values) == 0:
        return values
    low, high = float(values.min()), float(values.max())
    if high - low < 1e-9:
        return np.full(len(values), 0.5)
    return (values - low) / (high - low)


class BaseRecommender(ABC):
    name = "base"

    @abstractmethod
    def score(self, context):
        raise NotImplementedError

    def __mul__(self, weight):
        if not isinstance(weight, (int, float)):
            return NotImplemented
        return HybridRecommender([(self, float(weight))])

    __rmul__ = __mul__

    def __add__(self, other):
        if not isinstance(other, BaseRecommender):
            return NotImplemented
        return HybridRecommender([(self, 1.0)]) + other

    def __repr__(self):
        return f"{type(self).__name__}()"


class PopularityRecommender(BaseRecommender):
    name = "popularity"

    def score(self, context):
        return context.catalog.popularity


class ContentRecommender(BaseRecommender):
    name = "content"

    def score(self, context):
        return normalize(context.content_scores)


class CollaborativeRecommender(BaseRecommender):
    name = "collaborative"

    def score(self, context):
        return normalize(context.collaborative_scores)


class HybridRecommender(BaseRecommender):
    name = "hybrid"

    def __init__(self, components):
        self.components = [(recommender, float(weight)) for recommender, weight in components if weight > 0]
        if not self.components:
            raise ValueError("Для гибрида нужен хотя бы один компонент с положительным весом")

    def score(self, context):
        total = sum(weight for _, weight in self.components)
        combined = sum(weight * recommender.score(context) for recommender, weight in self.components)
        return combined / total

    def __add__(self, other):
        if isinstance(other, HybridRecommender):
            extra = other.components
        elif isinstance(other, BaseRecommender):
            extra = [(other, 1.0)]
        else:
            return NotImplemented
        return HybridRecommender(self.components + extra)

    def __len__(self):
        return len(self.components)

    def __iter__(self):
        return iter(self.components)

    def __repr__(self):
        parts = ", ".join(f"{weight:g}*{recommender!r}" for recommender, weight in self.components)
        return f"HybridRecommender({parts})"


def build_recommender(name, enough):
    popularity = PopularityRecommender()
    content = ContentRecommender()
    collaborative = CollaborativeRecommender()
    if name == "popularity":
        return popularity
    if name == "content":
        return 0.75 * content + 0.25 * popularity
    if name == "collaborative":
        if enough:
            return 0.75 * collaborative + 0.15 * content + 0.10 * popularity
        return 0.65 * content + 0.35 * popularity
    if enough:
        return 0.50 * popularity + 0.35 * content + 0.15 * collaborative
    return 0.60 * popularity + 0.40 * content
