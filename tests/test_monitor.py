"""Тесты оценки доступности моделей и поиска по каталогу."""

from monitor import (
    STATUS_AVAILABLE,
    STATUS_DOWN,
    STATUS_NOT_FOUND,
    STATUS_UNSTABLE,
    best_uptime,
    count_working,
    current_uptime,
    find_in_catalog,
    format_uptime,
    get_model_status,
    is_free,
    search_models,
)


def provider(status: int, uptime_5m: float | None) -> dict:
    return {"status": status, "uptime_last_5m": uptime_5m}


def test_status_not_found_when_no_endpoints() -> None:
    assert get_model_status(None) == STATUS_NOT_FOUND
    assert get_model_status([]) == STATUS_NOT_FOUND


def test_status_available() -> None:
    assert get_model_status([provider(0, 99.5)]) == STATUS_AVAILABLE


def test_status_unstable_when_uptime_low() -> None:
    assert get_model_status([provider(0, 60.0)]) == STATUS_UNSTABLE


def test_status_down_when_all_providers_failed() -> None:
    endpoints = [provider(-2, 35.0), provider(-1, None)]
    assert get_model_status(endpoints) == STATUS_DOWN


def test_status_uses_best_working_provider() -> None:
    endpoints = [provider(-2, 100.0), provider(0, 50.0), provider(0, 95.0)]
    assert get_model_status(endpoints) == STATUS_AVAILABLE


def test_status_available_without_uptime_data() -> None:
    assert get_model_status([provider(0, None)]) == STATUS_AVAILABLE


def test_best_uptime_ignores_failed_providers() -> None:
    endpoints = [provider(-2, 100.0), provider(0, 80.0)]
    assert best_uptime(endpoints, "uptime_last_5m") == 80.0


def test_current_uptime_falls_back_to_30m() -> None:
    endpoints = [{"status": 0, "uptime_last_5m": None,
                  "uptime_last_30m": 88.0}]
    assert current_uptime(endpoints) == 88.0
    assert current_uptime(None) is None


def test_count_working() -> None:
    endpoints = [provider(0, 99.0), provider(-2, 10.0), provider(0, None)]
    assert count_working(endpoints) == 2


def test_format_uptime() -> None:
    assert format_uptime(99.456) == "99.5%"
    assert format_uptime(None) == "нет данных"


def test_is_free_by_suffix_and_price() -> None:
    assert is_free({"id": "z-ai/glm-5.2:free"})
    zero = {"id": "a/b", "pricing": {"prompt": "0", "completion": "0"}}
    paid = {"id": "a/c", "pricing": {"prompt": "0.001", "completion": "0"}}
    assert is_free(zero)
    assert not is_free(paid)


CATALOG = [
    {"id": "openai/gpt-4o-mini", "name": "OpenAI: GPT-4o-mini",
     "pricing": {"prompt": "0.00000015", "completion": "0.0000006"}},
    {"id": "z-ai/glm-5.2:free", "name": "Z.ai: GLM 5.2 (free)",
     "pricing": {"prompt": "0", "completion": "0"}},
]


def test_search_models_case_insensitive() -> None:
    found = search_models(CATALOG, "GPT")
    assert [model["id"] for model in found] == ["openai/gpt-4o-mini"]


def test_search_models_free_only() -> None:
    assert search_models(CATALOG, "", free_only=True) == [CATALOG[1]]


def test_find_in_catalog() -> None:
    assert find_in_catalog(CATALOG, "z-ai/glm-5.2:free") == CATALOG[1]
    assert find_in_catalog(CATALOG, "unknown/model") is None
