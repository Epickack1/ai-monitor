"""История проверок моделей и статистика их доступности."""

from collections.abc import Iterator
from datetime import datetime

from monitor import STATUS_AVAILABLE

MAX_RECORDS = 1000
TIME_FORMAT = "%Y-%m-%d %H:%M"


def make_record(
    model_id: str,
    status: str,
    uptime: float | None,
    checked_at: str | None = None,
) -> dict:
    """Сформировать запись о проверке модели.

    Если время проверки не передано, берётся текущее.
    """
    if checked_at is None:
        checked_at = datetime.now().strftime(TIME_FORMAT)
    return {
        "model_id": model_id,
        "status": status,
        "uptime": uptime,
        "checked_at": checked_at,
    }


def is_valid_record(item: object) -> bool:
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


def add_record(
    history: list[dict], record: dict, limit: int = MAX_RECORDS
) -> None:
    """Добавить запись в историю.

    Чтобы файл не рос бесконечно, самые старые записи сверх limit удаляются.
    """
    history.append(record)
    if len(history) > limit:
        del history[:len(history) - limit]


def iter_records(history: list[dict], model_id: str) -> Iterator[dict]:
    """Генератор: по одной выдаёт записи истории указанной модели."""
    for record in history:
        if record["model_id"] == model_id:
            yield record


def last_record(history: list[dict], model_id: str) -> dict | None:
    """Последняя запись о проверке модели или None, если проверок не было."""
    last = None
    for record in iter_records(history, model_id):
        last = record
    return last


def last_uptime(history: list[dict], model_id: str) -> float | None:
    """Аптайм модели по последней проверке."""
    record = last_record(history, model_id)
    if record is None:
        return None
    return record["uptime"]


def model_stats(history: list[dict], model_id: str) -> dict | None:
    """Статистика проверок одной модели или None, если проверок не было."""
    checks = available = 0
    uptimes = []
    last_status = None
    for record in iter_records(history, model_id):
        checks += 1
        if record["status"] == STATUS_AVAILABLE:
            available += 1
        if record["uptime"] is not None:
            uptimes.append(record["uptime"])
        last_status = record["status"]

    if checks == 0:
        return None
    return {
        "model_id": model_id,
        "checks": checks,
        "available": available,
        "percent": available / checks * 100,
        "avg_uptime": sum(uptimes) / len(uptimes) if uptimes else None,
        "last_status": last_status,
    }


def collect_stats(history: list[dict]) -> list[dict]:
    """Статистика по всем моделям из истории.

    Модели упорядочены от самой стабильной к самой проблемной:
    по доле успешных проверок, затем по среднему аптайму.
    """
    model_ids = sorted({record["model_id"] for record in history})
    stats = [model_stats(history, model_id) for model_id in model_ids]
    return sorted(
        stats,
        key=lambda item: (item["percent"], item["avg_uptime"] or 0.0),
        reverse=True,
    )


def sort_models(
    models: list[dict], history: list[dict], by_uptime: bool = False
) -> list[dict]:
    """Отсортировать модели по названию или по аптайму последней проверки.

    При сортировке по аптайму модели без данных оказываются в конце.
    """
    if not by_uptime:
        return sorted(models, key=lambda model: model["name"].lower())

    uptimes = {
        model["id"]: last_uptime(history, model["id"]) for model in models
    }
    return sorted(
        models,
        key=lambda model: (
            uptimes[model["id"]] is not None,
            uptimes[model["id"]] or 0.0,
        ),
        reverse=True,
    )
