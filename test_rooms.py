import pandas as pd

def check_rooms_file(path: str):
    df = pd.read_excel(path)

    assert "rooms" in df.columns, f"В {path} отсутствует колонка rooms"

    allowed = {1, 2}

    s = df["rooms"].dropna()

    # Приведение к int, чтобы отработало 1.0/2.0 тоже
    try:
        s = s.astype(int)
    except ValueError:
        bad_preview = sorted(set(df["rooms"].dropna().unique()))[:20]
        raise AssertionError(f"В {path} rooms содержит нецелые значения: {bad_preview}")

    bad = set(s.unique()) - allowed
    assert not bad, f"В {path} найдены недопустимые значения rooms: {bad}"

def test_rooms_contains_only_1_or_2_in_both_files():
    for path in ["r.xlsx", "y.xlsx"]:
        check_rooms_file(path)