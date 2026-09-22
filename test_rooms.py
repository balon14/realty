# test_rooms.py
import pandas as pd

def test_rooms_contains_only_1_or_2():
    df = pd.read_excel("r.xlsx")  # <-- важно: read_excel, не read_csv

    assert "rooms" in df.columns, "Колонка rooms отсутствует в r.xlsx"

    allowed = {1, 2}

    # На случай, если rooms пришел как float (1.0/2.0)
    s = df["rooms"].dropna()
    try:
        s = s.astype(int)
    except ValueError:
        # если там реально строки/дробные — покажем уникальные значения для диагностики
        bad_preview = sorted(set(df["rooms"].dropna().unique()))[:20]
        raise AssertionError(f"rooms содержит нецелые значения: {bad_preview}")

    bad = set(s.unique()) - allowed
    assert not bad, f"Найдено недопустимые значения в rooms: {bad}"