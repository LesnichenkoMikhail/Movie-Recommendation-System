import ast

import pandas as pd


def parse_genres(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (ValueError, SyntaxError):
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


def to_int(value, default=0):
    try:
        if pd.isna(value) or value == "":
            return default
        return int(float(value))
    except (ValueError, TypeError):
        return default


def to_float(value, default=0.0):
    try:
        if pd.isna(value) or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def clean_text(value, limit=None):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = str(value)
    return text[:limit] if limit else text
