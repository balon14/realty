#!/usr/bin/env python3
import requests
import time
import csv
import os
import re
from datetime import datetime

BASE_URL = "https://pk.api.onliner.by/search/apartments"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
}

# Регулярка: "Панельный дом 2015 года", "Кирпичный дом 1987 г." и т.п.
YEAR_RE = re.compile(
    r"(панельн\w*|кирпичн\w*|монолитн\w*|блочн\w*|каркасн\w*|деревянн\w*)?\s*"
    r"дом\s+(\d{4})\s*(?:года|г\.?)?",
    re.IGNORECASE,
)


def get_apartments(page=1, **filters):
    params = {"page": page, **filters}
    response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=20)
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


def fetch_building_info(url: str) -> tuple[str | None, int | None]:
    """
    Парсит HTML страницы объявления.
    Возвращает (тип_дома, год_постройки) или (None, None).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Ищем все пункты опций
        options = re.findall(
            r'class="apartment-options__item"[^>]*>([^<]+)',
            html,
        )
        for opt in options:
            opt = opt.strip()
            m = YEAR_RE.search(opt)
            if m:
                building_type = (m.group(1) or "").strip().lower() or None
                year = int(m.group(2))
                # Нормализуем тип
                if building_type:
                    if "панел" in building_type:
                        building_type = "панельный"
                    elif "кирпич" in building_type:
                        building_type = "кирпичный"
                    elif "монолит" in building_type:
                        building_type = "монолитный"
                    elif "блоч" in building_type:
                        building_type = "блочный"
                    elif "каркас" in building_type:
                        building_type = "каркасный"
                    elif "дерев" in building_type:
                        building_type = "деревянный"
                return building_type, year

        # Запасной вариант: просто год рядом со словом "дом"
        m2 = re.search(r"дом\s+(\d{4})", html, re.IGNORECASE)
        if m2:
            return None, int(m2.group(1))

    except Exception as e:
        print(f"  ⚠️ не удалось получить год для {url}: {e}")
    return None, None


def enrich_with_building_year(apartments: list, delay: float = 0.5) -> list:
    """Добавляет building_year и building_type к каждому объявлению."""
    total = len(apartments)
    print(f"\nПолучаю год постройки для {total} объявлений...")

    for i, apt in enumerate(apartments, 1):
        url = apt.get("url")
        if not url:
            continue
        if i % 20 == 0 or i == total:
            print(f"  {i}/{total}...")
        building_type, year = fetch_building_info(url)
        apt["building_type"] = building_type
        apt["building_year"] = year
        time.sleep(delay)

    return apartments

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
        "building_type": apt.get("building_type"),   # ← новое
        "building_year": apt.get("building_year"),   # ← новое
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
        script_dir = os.path.dirname(os.path.abspath(file))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(script_dir, f"apartments_{timestamp}.csv")

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

    # Получаем год постройки (запросы на каждую страницу)
    apartments = enrich_with_building_year(apartments, delay=0.5)

    # Сохраняем в CSV
    save_to_csv(apartments, r"D:\Pet_projekts\realty\realty\r.csv")