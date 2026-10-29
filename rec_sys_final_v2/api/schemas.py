from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    genres: list[str] = []


class RatingIn(BaseModel):
    user_id: int
    movie_id: int
    rating: float = Field(ge=0.5, le=5.0)


class InteractionIn(BaseModel):
    user_id: int
    movie_id: int
    action: str
    recommendation_id: int | None = None


class FeedbackIn(BaseModel):
    recommendation_id: int
    feedback: int = Field(ge=1, le=5)


class EvaluationIn(BaseModel):
    k: int = Field(10, ge=1, le=50)
    min_ratings: int = Field(8, ge=3, le=200)
    test_ratio: float = Field(0.3, gt=0.05, lt=0.6)
    max_users: int = Field(40, ge=1, le=200)
    seed: int = 42
