"""Оценка доступности моделей по данным провайдеров OpenRouter."""

STABLE_UPTIME = 90.0

STATUS_AVAILABLE = "Доступна"
STATUS_UNSTABLE = "Нестабильна"
STATUS_DOWN = "Недоступна"
STATUS_NOT_FOUND = "Не найдена"


def is_provider_working(endpoint: dict) -> bool:
    """Провайдер работает, если его статус равен 0.

    Отрицательный статус OpenRouter выставляет при сбоях провайдера.
    """
    return endpoint.get("status", -1) == 0


def best_uptime(endpoints: list[dict], field: str) -> float | None:
    """Лучший аптайм среди работающих провайдеров за указанный период."""
    best = None
    for endpoint in endpoints:
        value = endpoint.get(field)
        if not is_provider_working(endpoint) or value is None:
            continue
        if best is None or value > best:
            best = value
    return best


def current_uptime(endpoints: list[dict] | None) -> float | None:
    """Текущий аптайм модели.

    Берётся лучший аптайм за 5 минут, а если данных нет — за 30 минут.
    """
    if not endpoints:
        return None
    uptime = best_uptime(endpoints, "uptime_last_5m")
    if uptime is None:
        uptime = best_uptime(endpoints, "uptime_last_30m")
    return uptime


def get_model_status(endpoints: list[dict] | None) -> str:
    """Определить статус модели по списку её провайдеров."""
    if not endpoints:
        return STATUS_NOT_FOUND

    working = count_working(endpoints)
    if working == 0:
        return STATUS_DOWN

    uptime = current_uptime(endpoints)
    if uptime is None or uptime >= STABLE_UPTIME:
        return STATUS_AVAILABLE
    return STATUS_UNSTABLE


def count_working(endpoints: list[dict]) -> int:
    """Сколько провайдеров модели сейчас работает."""
    working = 0
    for endpoint in endpoints:
        if is_provider_working(endpoint):
            working += 1
    return working


def format_uptime(value: float | None) -> str:
    """Отформатировать аптайм в процентах, например 99.5%."""
    if value is None:
        return "нет данных"
    return f"{value:.1f}%"


def is_free(model: dict) -> bool:
    """Бесплатная ли модель: суффикс :free или нулевая цена."""
    if model.get("id", "").endswith(":free"):
        return True
    pricing = model.get("pricing", {})
    prompt = float(pricing.get("prompt", "1") or 0)
    completion = float(pricing.get("completion", "1") or 0)
    return prompt == 0 and completion == 0


def search_models(
    catalog: list[dict], query: str, free_only: bool = False
) -> list[dict]:
    """Найти модели, в id или названии которых есть подстрока query."""
    query_lower = query.lower().strip()
    found = []
    for model in catalog:
        text = (model.get("id", "") + " " + model.get("name", "")).lower()
        if query_lower not in text:
            continue
        if free_only and not is_free(model):
            continue
        found.append(model)
    return found


def find_in_catalog(catalog: list[dict], model_id: str) -> dict | None:
    """Найти модель в каталоге по точному id."""
    for model in catalog:
        if model.get("id") == model_id:
            return model
    return None
