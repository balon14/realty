#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер квартир realt.by
Фильтр: 1–2 комнатные, 50 000–120 000 USD, Минск.
CSV сохраняется в ту же папку, где лежит скрипт.
"""

import sys
import os
import re
import csv
import time
import json
from datetime import datetime
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("=" * 50)
    print("ОШИБКА: не установлена библиотека requests")
    print("Установите:  pip install requests")
    print("или:         python -m pip install requests")
    print("=" * 50)
    input("Нажмите Enter, чтобы закрыть...")
    sys.exit(1)


# Минск
MINSK_TOWN_UUID = "4cb07174-7b00-11eb-8943-0cc47adabd66"
# 840 = USD (ISO 4217)
PRICE_TYPE_USD = "840"

BASE_URL = "https://realt.by/sale/flats/"


def get_script_dir():
    """Папка, в которой лежит этот скрипт (папка проекта)."""
    return os.path.dirname(os.path.abspath(__file__))


def build_url(page: int = 1) -> str:
    """URL с фильтрами: Минск, 1–2 комнаты, 50k–120k USD."""
    # addressV2 как JSON в query
    address = json.dumps([{"townUuid": MINSK_TOWN_UUID}], separators=(",", ":"))
    params = [
        ("addressV2", address),
        ("rooms", "1"),
        ("rooms", "2"),
        ("priceFrom", "50000"),
        ("priceTo", "120000"),
        ("priceType", PRICE_TYPE_USD),
    ]
    if page > 1:
        params.append(("page", str(page)))
    return BASE_URL + "?" + urlencode(params)


def fetch_page(page: int, session: requests.Session) -> dict:
    """Загружает страницу и достаёт данные из __NEXT_DATA__."""
    url = build_url(page)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }
    print(f"  Загрузка страницы {page}...")
    resp = session.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text,
        re.DOTALL,
    )
    if not m:
        raise RuntimeError("Не найден __NEXT_DATA__ — структура сайта изменилась")

    data = json.loads(m.group(1))
    return data["props"]["pageProps"]


def get_price_usd(obj: dict):
    """Цена в USD из priceRates (код 840)."""
    rates = obj.get("priceRates") or {}
    val = rates.get("840") or rates.get(840)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    if obj.get("priceCurrency") in (840, "840", "USD"):
        try:
            return float(obj.get("price"))
        except (TypeError, ValueError):
            pass
    return None


def matches_filters(obj: dict) -> bool:
    """Доп. проверка: 1–2 комнаты, 50–120 тыс. USD."""
    rooms = obj.get("rooms")
    try:
        rooms = int(rooms) if rooms is not None else None
    except (TypeError, ValueError):
        rooms = None
    if rooms not in (1, 2):
        return False

    usd = get_price_usd(obj)
    if usd is None:
        return False
    return 50000 <= usd <= 120000


def flatten_object(obj: dict) -> dict:
    images = obj.get("images") or []
    photo = ""
    if images:
        first = images[0]
        if isinstance(first, dict):
            photo = first.get("src") or first.get("url") or first.get("path") or ""
        else:
            photo = str(first)

    rates = obj.get("priceRates") or {}
    price_usd = rates.get("840") or rates.get(840)
    price_byn = rates.get("933") or rates.get(933)

    uuid = obj.get("uuid") or ""
    url = f"https://realt.by/sale-flats/object/{uuid}/" if uuid else ""
    # иногда code используется в URL
    code = obj.get("code")
    if code and not uuid:
        url = f"https://realt.by/sale-flats/object/{code}/"

    phones = obj.get("contactPhones")
    if isinstance(phones, list):
        phones = "; ".join(str(p) for p in phones)

    return {
        "uuid": uuid,
        "code": code,
        "url": url,
        "title": obj.get("title") or obj.get("headline"),
        "price": obj.get("price"),
        "price_currency": obj.get("priceCurrency"),
        "price_usd": price_usd,
        "price_byn": price_byn,
        "price_per_m2": obj.get("pricePerM2"),
        "rooms": obj.get("rooms"),
        "storey": obj.get("storey"),
        "storeys": obj.get("storeys"),
        "area_total": obj.get("areaTotal"),
        "area_living": obj.get("areaLiving"),
        "area_kitchen": obj.get("areaKitchen"),
        "address": obj.get("address"),
        "town_name": obj.get("townName"),
        "street_name": obj.get("streetName"),
        "house_number": obj.get("houseNumber"),
        "state_region": obj.get("stateRegionName"),
        "state_district": obj.get("stateDistrictName"),
        "metro_station": obj.get("metroStationName"),
        "metro_time": obj.get("metroTime"),
        "building_year": obj.get("buildingYear"),
        "wall_material": obj.get("wallMaterial"),
        "repair_state": obj.get("repairState"),
        "agency_name": obj.get("agencyName"),
        "contact_name": obj.get("contactName"),
        "contact_phones": phones,
        "photo": photo,
        "created_at": obj.get("createdAt"),
        "updated_at": obj.get("updatedAt"),
        "description": (obj.get("description") or "")[:500],
    }


def save_to_csv(rows: list, output_path: str):
    if not rows:
        print("Нет данных для сохранения!")
        return

    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("=" * 60)
    print(f"ГОТОВО! Сохранено объявлений: {len(rows)}")
    print(f"Файл находится здесь:")
    print(f"  {output_path}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("Парсер квартир realt.by")
    print("Фильтр: 1–2 комн., 50 000–120 000 USD, Минск")
    print("=" * 60)
    print()

    # ========== НАСТРОЙКИ ==========
    MAX_PAGES = None  # None = все страницы; или число, например 10
    # ================================

    script_dir = get_script_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(script_dir, f"realt.csv")

    print(f"Папка проекта: {script_dir}")
    print(f"Файл будет сохранён как: {output_file}")
    print()

    session = requests.Session()
    all_objects = []

    try:
        first = fetch_page(1, session)
        total = first.get("totalCount") or 0
        pagination = first.get("pagination") or {}
        page_size = pagination.get("pageSize") or 30
        objects = first.get("objects") or []
        all_objects.extend(objects)

        print(f"По фильтру сайта найдено: {total}")
        print(f"На 1-й странице: {len(objects)} (pageSize={page_size})")

        total_pages = max(1, (total + page_size - 1) // page_size) if page_size else 1
        if MAX_PAGES is None:
            pages_to_load = total_pages
        else:
            pages_to_load = min(MAX_PAGES, total_pages)
        print(f"Всего страниц по фильтру: {total_pages}")
        print(f"Будет загружено страниц: {pages_to_load}")

        for page in range(2, pages_to_load + 1):
            time.sleep(0.8)
            props = fetch_page(page, session)
            objs = props.get("objects") or []
            all_objects.extend(objs)
            print(f"    +{len(objs)} (всего сырых {len(all_objects)})")

        # Жёсткая фильтрация по USD и комнатам
        filtered = [o for o in all_objects if matches_filters(o)]
        print(f"\nПосле проверки (1–2 комн., 50–120k USD): {len(filtered)}")

        rows = [flatten_object(o) for o in filtered]
        save_to_csv(rows, output_file)

    except requests.exceptions.RequestException as e:
        print()
        print("ОШИБКА сети:")
        print(e)
    except Exception as e:
        print()
        print("НЕОЖИДАННАЯ ОШИБКА:")
        print(type(e).__name__, "→", e)

    print()
    input("Нажмите Enter, чтобы закрыть окно...")


if __name__ == "__main__":
    main()
