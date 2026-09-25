"""Хранение данных приложения в JSON-файлах."""

import json
import os

from history import is_valid_record

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "watchlist.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def load_json_list(path: str) -> list:
    """Прочитать список из JSON-файла.

    Отсутствие файла — обычная ситуация при первом запуске, поэтому
    возвращается пустой список. О повреждённом или недоступном файле
    выводится сообщение, программа продолжает работу.
    """
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"  Ошибка: файл {path} содержит некорректный JSON")
        return []
    except OSError as error:
        print(f"  Ошибка чтения файла {path}: {error}")
        return []

    if not isinstance(data, list):
        print(f"  Ошибка: в файле {path} ожидался список")
        return []
    return data


def save_json(data: list, path: str) -> bool:
    """Записать список в JSON-файл. Возвращает False при ошибке записи."""
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except OSError:
        return False
    return True


def is_valid_model(item: object) -> bool:
    """Проверить, что запись списка отслеживания содержит id и название."""
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
    )


def load_watchlist(path: str = DATA_FILE) -> list[dict]:
    """Загрузить список отслеживаемых моделей.

    Некорректные записи пропускаются.
    """
    return [item for item in load_json_list(path) if is_valid_model(item)]


def save_watchlist(models: list[dict], path: str = DATA_FILE) -> bool:
    """Сохранить список моделей. Возвращает False при ошибке записи."""
    return save_json(models, path)


def load_history(path: str = HISTORY_FILE) -> list[dict]:
    """Загрузить историю проверок. Некорректные записи пропускаются."""
    return [item for item in load_json_list(path) if is_valid_record(item)]


def save_history(history: list[dict], path: str = HISTORY_FILE) -> bool:
    """Сохранить историю проверок. Возвращает False при ошибке записи."""
    return save_json(history, path)


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
