"""#!/bin/bash

# Останавливать выполнение, если какой-либо скрипт завершился с ошибкой
set -e

echo "=== Запуск пайплайна ==="

# 1. Запуск r_parser
echo "Шаг 1: Запуск r_parser..."
python3 r_parser.py

# 2. Запуск y_parser
echo "Шаг 2: Запуск y_parser..."
python3 y_parser.py

# 3. Запуск test_rooms.py
echo "Шаг 3: Запуск test_rooms.py..."
python3 test_rooms.py

# 4. Запуск ноутбука realty_ipynpb.ipynb
echo "Шаг 4: Запуск ноутбука realty_ipunpb.ipynb"
jupyter nbconvert --to notebook --execute --inplace realty_ipynpb.ipynb

echo "=== Пайплайн успешно завершен! ==="
"""
import subprocess
import sys
from pathlib import Path

FILES = [
    "r_parser.py",
    "y_parser.py",
    "test_rooms.py",
    "realty_ipynb.ipynb",
]

def run_file(path: str) -> None:
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"Не найден файл: {p.resolve()}")

    # Расширения/типы
    if p.suffix == ".py":
        cmd = [sys.executable, str(p)]  # python file
    elif p.suffix == ".ipynb":
        # запуск notebook через jupyter
        cmd = ["jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace", str(p)]
    else:
        # если вдруг это не .py/.ipynb — можно расширить логику по требованию
        raise ValueError(f"Неизвестный тип файла: {p.name}")

    print(f"\n=== Запуск: {p} ===")
    subprocess.run(cmd, check=True)

def main():
    for f in FILES:
        run_file(f)
    print("\n✅ Все файлы успешно выполнены по очереди.")

if __name__ == "__main__":
    main()