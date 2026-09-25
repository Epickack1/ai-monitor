"""Хранение данных в JSON-файлах и преобразование JSON в объекты и обратно."""

import json
import os

from models import AIModel, CheckResult

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


def is_valid_model_data(item: object) -> bool:
    """Проверить, что запись списка отслеживания содержит id и название."""
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
    )


def is_valid_result_data(item: object) -> bool:
    """Проверить, что запись истории содержит нужные поля нужных типов."""
    if not isinstance(item, dict):
        return False
    uptime = item.get("uptime")
    return (
        isinstance(item.get("model_id"), str)
        and isinstance(item.get("status"), str)
        and isinstance(item.get("checked_at"), str)
        and (uptime is None or isinstance(uptime, (int, float)))
    )


def load_watchlist(path: str = DATA_FILE) -> list[AIModel]:
    """Загрузить список отслеживаемых моделей как объекты AIModel.

    Некорректные записи пропускаются.
    """
    return [
        AIModel.from_data(item) for item in load_json_list(path)
        if is_valid_model_data(item)
    ]


def save_watchlist(models: list[AIModel], path: str = DATA_FILE) -> bool:
    """Сохранить список моделей. Возвращает False при ошибке записи."""
    return save_json([model.to_data() for model in models], path)


def load_history(
    models: list[AIModel], path: str = HISTORY_FILE
) -> list[CheckResult]:
    """Загрузить историю проверок как объекты CheckResult.

    По model_id из JSON находится объект модели из списка отслеживания.
    Если модель уже удалена из отслеживания, её история сохраняется:
    для неё создаётся один объект AIModel с названием, равным id.
    Некорректные записи пропускаются.
    """
    known = {model.id: model for model in models}
    history = []
    for item in load_json_list(path):
        if not is_valid_result_data(item):
            continue
        model_id = item["model_id"]
        if model_id not in known:
            known[model_id] = AIModel(model_id, model_id)
        history.append(CheckResult.from_data(item, known[model_id]))
    return history


def save_history(
    history: list[CheckResult], path: str = HISTORY_FILE
) -> bool:
    """Сохранить историю проверок. Возвращает False при ошибке записи."""
    return save_json([result.to_data() for result in history], path)
