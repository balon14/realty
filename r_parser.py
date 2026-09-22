#!/usr/bin/env python3
"""
Парсер квартир с r.onliner.by/pk/
Сохраняет результат в CSV рядом со скриптом (или в указанную папку).
"""

import requests
import time
import csv
import os
from datetime import datetime

BASE_URL = "https://pk.api.onliner.by/search/apartments"

def get_apartments(page=1, **filters):
    params = {"page": page, **filters}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    response = requests.get(BASE_URL, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()

def parse_all(max_pages=None, **filters):
    first = get_apartments(page=1, **filters)
    last_page = first.get("page", {}).get("last", 1)
    if max_pages:
        last_page = min(last_page, max_pages)

    all_aparts = first.get("apartments", [])
    print(f"Всего страниц по фильтру: {last_page}")

    for page in range(2, last_page + 1):
        print(f"  страница {page}/{last_page}...")
        data = get_apartments(page=page, **filters)
        all_aparts.extend(data.get("apartments", []))
        time.sleep(0.6)

    return all_aparts

def flatten_apartment(apt: dict) -> dict:
    price = apt.get("price", {}) or {}
    area = apt.get("area", {}) or {}
    location = apt.get("location", {}) or {}
    seller = apt.get("seller", {}) or {}
    auction = apt.get("auction_bid", {}) or {}
    converted = price.get("converted") or {}

    return {
        "id": apt.get("id"),
        "url": apt.get("url"),
        "price_amount": price.get("amount"),
        "price_currency": price.get("currency"),
        "price_usd": (converted.get("USD") or {}).get("amount"),
        "price_byn": (converted.get("BYN") or {}).get("amount"),
        "number_of_rooms": apt.get("number_of_rooms"),
        "floor": apt.get("floor"),
        "number_of_floors": apt.get("number_of_floors"),
        "area_total": area.get("total"),
        "area_living": area.get("living"),
        "area_kitchen": area.get("kitchen"),
        "address": location.get("address"),
        "user_address": location.get("user_address"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "seller_type": seller.get("type"),
        "resale": apt.get("resale"),
        "photo": apt.get("photo"),
        "created_at": apt.get("created_at"),
        "last_time_up": apt.get("last_time_up"),
        "auction_bid_amount": auction.get("amount"),
        "auction_bid_currency": auction.get("currency"),
    }

def save_to_csv(apartments: list, output_path: str = None) -> str:
    if not apartments:
        print("Нет данных для сохранения")
        return None

    if output_path is None:
        # Сохраняем рядом со скриптом
        script_dir = os.path.dirname(os.path.abspath(__file__))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(script_dir, f"apartments_{timestamp}.csv")

    # Создаём папку, если нужно
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    rows = [flatten_apartment(apt) for apt in apartments]
    fieldnames = list(rows[0].keys())

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    abs_path = os.path.abspath(output_path)
    print(f"\n✓ Сохранено {len(rows)} объявлений")
    print(f"  Файл: {abs_path}")
    return abs_path


if __name__ == "__main__":
    # ========== НАСТРОЙКИ ==========
    filters = {
        "price[min]": 50000,
        "price[max]": 120000,
        "currency": "usd",
        "number_of_rooms[]": [1, 2],
        # область Минска (можно убрать, если нужны все объявления)
        "bounds[lb][lat]": 53.76,
        "bounds[lb][long]": 27.26,
        "bounds[rt][lat]": 54.04,
        "bounds[rt][long]": 27.76,
        # "only_owner": "true",   # только от собственника
    }

    MAX_PAGES = None          # сколько страниц парсить (None = все)
    # ================================

    print("Начинаю парсинг...")
    apartments = parse_all(max_pages=MAX_PAGES, **filters)
    print(f"Найдено объявлений: {len(apartments)}")

    # Сохраняем в CSV рядом со скриптом
    save_to_csv(apartments, r"D:\Pet_projekts\realty\realty\r.csv")