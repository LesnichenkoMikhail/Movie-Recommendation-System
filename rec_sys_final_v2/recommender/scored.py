from functools import total_ordering


@total_ordering
class ScoredMovie:
    __slots__ = ("movie_id", "score", "model")

    def __init__(self, movie_id, score, model):
        self.movie_id = movie_id
        self.score = float(score)
        self.model = model

    def __eq__(self, other):
        if not isinstance(other, ScoredMovie):
            return NotImplemented
        return (self.movie_id == other.movie_id and self.model == other.model
                and abs(self.score - other.score) < 1e-12)

    def __lt__(self, other):
        if not isinstance(other, ScoredMovie):
            return NotImplemented
        return self.score < other.score

    def __hash__(self):
        return hash((self.movie_id, self.model))

    def __float__(self):
        return self.score

    def __repr__(self):
        return f"ScoredMovie(movie_id={self.movie_id}, score={self.score:.4f}, model={self.model!r})"
