from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from api.schemas import EvaluationIn
from database.connection import get_db
from database.models import ModelRun
from recommender.benchmark import run_benchmark

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/run")
def run_evaluation(payload: EvaluationIn, db: Session = Depends(get_db)):
    result = run_benchmark(db, k=payload.k, min_ratings=payload.min_ratings, test_ratio=payload.test_ratio,
                           max_users=payload.max_users, seed=payload.seed, negatives=payload.negatives)
    parameters = {"k": payload.k, "min_ratings": payload.min_ratings, "test_ratio": payload.test_ratio,
                  "max_users": payload.max_users, "seed": payload.seed, "negatives": payload.negatives,
                  "users_evaluated": result["users_evaluated"]}
    for item in result["models"]:
        extra = {key: item[key] for key in ("hit_rate", "map", "mrr")}
        db.add(ModelRun(model_name=item["model"], parameters={**parameters, "extra_metrics": extra},
                        precision_at_k=item["precision"],
                        recall_at_k=item["recall"], ndcg_at_k=item["ndcg"]))
    db.commit()
    return result


@router.get("/runs")
def list_runs(limit: int = Query(60, ge=1, le=500), db: Session = Depends(get_db)):
    runs = db.scalars(select(ModelRun).order_by(desc(ModelRun.created_at), desc(ModelRun.id)).limit(limit)).all()
    return [
        {
            "id": run.id,
            "created_at": run.created_at.isoformat(),
            "model": run.model_name,
            "k": (run.parameters or {}).get("k"),
            "users": (run.parameters or {}).get("users_evaluated"),
            "precision": run.precision_at_k,
            "recall": run.recall_at_k,
            "ndcg": run.ndcg_at_k,
            "negatives": (run.parameters or {}).get("negatives"),
            "hit_rate": ((run.parameters or {}).get("extra_metrics") or {}).get("hit_rate"),
            "map": ((run.parameters or {}).get("extra_metrics") or {}).get("map"),
            "mrr": ((run.parameters or {}).get("extra_metrics") or {}).get("mrr"),
        }
        for run in runs
    ]
