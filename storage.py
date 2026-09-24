"""Хранение списка отслеживаемых моделей в JSON-файле."""

import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "watchlist.json")


def load_watchlist(path: str = DATA_FILE) -> list[dict]:
    """Загрузить список отслеживаемых моделей.

    Если файла нет или он повреждён, возвращается пустой список.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        print(f"  Ошибка: файл {path} содержит некорректный JSON")
        return []
    if not isinstance(data, list):
        return []
    return data


def save_watchlist(models: list[dict], path: str = DATA_FILE) -> bool:
    """Сохранить список моделей. Возвращает False при ошибке записи."""
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(models, file, ensure_ascii=False, indent=2)
    except OSError:
        return False
    return True


def is_watched(models: list[dict], model_id: str) -> bool:
    """Есть ли модель в списке отслеживаемых."""
    for model in models:
        if model["id"] == model_id:
            return True
    return False


def add_model(models: list[dict], model_id: str, name: str) -> bool:
    """Добавить модель в список. Возвращает False, если она уже есть."""
    if is_watched(models, model_id):
        return False
    models.append({"id": model_id, "name": name})
    return True


def remove_model(models: list[dict], model_id: str) -> bool:
    """Удалить модель из списка. Возвращает False, если её не было."""
    for model in models:
        if model["id"] == model_id:
            models.remove(model)
            return True
    return False
