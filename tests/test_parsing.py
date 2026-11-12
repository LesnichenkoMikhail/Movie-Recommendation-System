from etl.parsing import clean_text, parse_genres, to_float, to_int


def test_parse_genres_formats():
    assert parse_genres("['Drama', 'Comedy']") == ["Drama", "Comedy"]
    assert parse_genres("Drama, Comedy") == ["Drama", "Comedy"]
    assert parse_genres(["Action", " "]) == ["Action"]
    assert parse_genres(None) == []
    assert parse_genres(float("nan")) == []
    assert parse_genres("") == []


def test_numeric_helpers():
    assert to_int("12.0") == 12
    assert to_int(None, 5) == 5
    assert to_int("abc", 7) == 7
    assert to_float("3.5") == 3.5
    assert to_float(float("nan"), 1.0) == 1.0


def test_clean_text():
    assert clean_text(None) is None
    assert clean_text(float("nan")) is None
    assert clean_text("abcdef", 3) == "abc"
