"""Тесты класса Provider и оценки доступности модели."""

from models import Provider
from models.provider import (
    STATUS_AVAILABLE,
    STATUS_DOWN,
    STATUS_NOT_FOUND,
    STATUS_UNSTABLE,
    best_uptime,
    count_working,
    current_uptime,
    get_model_status,
)


def provider(status: int, uptime_5m: float | None) -> Provider:
    return Provider("Test", status, uptime_5m=uptime_5m)


def test_provider_from_api() -> None:
    item = Provider.from_api({
        "provider_name": "DeepInfra", "status": 0,
        "uptime_last_5m": 99.5, "uptime_last_1d": 98.0,
    })
    assert item.name == "DeepInfra"
    assert item.is_working
    assert item.uptime_5m == 99.5
    assert item.uptime_30m is None


def test_provider_str() -> None:
    text = str(Provider("DeepInfra", -2, 35.0, None, 80.0))
    assert "DeepInfra" in text
    assert "сбой" in text
    assert "35.0%" in text


def test_status_not_found_when_no_providers() -> None:
    assert get_model_status(None) == STATUS_NOT_FOUND
    assert get_model_status([]) == STATUS_NOT_FOUND


def test_status_available() -> None:
    assert get_model_status([provider(0, 99.5)]) == STATUS_AVAILABLE


def test_status_unstable_when_uptime_low() -> None:
    assert get_model_status([provider(0, 60.0)]) == STATUS_UNSTABLE


def test_status_down_when_all_providers_failed() -> None:
    providers = [provider(-2, 35.0), provider(-1, None)]
    assert get_model_status(providers) == STATUS_DOWN


def test_status_uses_best_working_provider() -> None:
    providers = [provider(-2, 100.0), provider(0, 50.0), provider(0, 95.0)]
    assert get_model_status(providers) == STATUS_AVAILABLE


def test_status_available_without_uptime_data() -> None:
    assert get_model_status([provider(0, None)]) == STATUS_AVAILABLE


def test_best_uptime_ignores_failed_providers() -> None:
    providers = [provider(-2, 100.0), provider(0, 80.0)]
    assert best_uptime(providers, "uptime_5m") == 80.0


def test_current_uptime_falls_back_to_30m() -> None:
    providers = [Provider("Test", 0, uptime_5m=None, uptime_30m=88.0)]
    assert current_uptime(providers) == 88.0
    assert current_uptime(None) is None


def test_count_working() -> None:
    providers = [provider(0, 99.0), provider(-2, 10.0), provider(0, None)]
    assert count_working(providers) == 2
