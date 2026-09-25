"""Тесты результата проверки, истории, статистики и сортировки."""

from models import AIModel, CheckResult, ModelStats, Provider
from models.check import (
    add_result,
    collect_stats,
    iter_results,
    last_result,
    sort_models,
)
from models.provider import STATUS_AVAILABLE, STATUS_DOWN, STATUS_UNSTABLE

FAST = AIModel("a/fast", "Fast model")
SLOW = AIModel("b/slow", "Slow model")
NEW = AIModel("c/new", "New model")
MODELS = [SLOW, NEW, FAST]

HISTORY = [
    CheckResult(FAST, STATUS_AVAILABLE, 99.0, "2026-09-26 10:00"),
    CheckResult(SLOW, STATUS_UNSTABLE, 70.0, "2026-09-26 10:00"),
    CheckResult(FAST, STATUS_AVAILABLE, 97.0, "2026-09-26 11:00"),
    CheckResult(SLOW, STATUS_DOWN, None, "2026-09-26 11:00"),
]


def test_result_creation_sets_time() -> None:
    result = CheckResult(FAST, STATUS_AVAILABLE, 99.5)
    assert result.model is FAST
    assert result.checked_at
    assert result.is_available


def test_result_from_providers() -> None:
    providers = [Provider("P1", 0, uptime_5m=60.0)]
    result = CheckResult.from_providers(SLOW, providers)
    assert result.status == STATUS_UNSTABLE
    assert result.uptime == 60.0
    assert result.providers == providers
    assert not result.is_available


def test_result_to_data_stores_model_id() -> None:
    assert HISTORY[0].to_data() == {
        "model_id": "a/fast",
        "status": STATUS_AVAILABLE,
        "uptime": 99.0,
        "checked_at": "2026-09-26 10:00",
    }


def test_result_from_data_links_model() -> None:
    result = CheckResult.from_data(HISTORY[1].to_data(), SLOW)
    assert result.model is SLOW
    assert result.uptime == 70.0


def test_result_str() -> None:
    assert str(HISTORY[3]) == "2026-09-26 11:00  Недоступна   нет данных"


def test_add_result_trims_old_records() -> None:
    history = []
    for hour in range(5):
        result = CheckResult(FAST, STATUS_AVAILABLE, 99.0,
                             f"2026-09-26 0{hour}:00")
        add_result(history, result, limit=3)
    assert len(history) == 3
    assert history[0].checked_at == "2026-09-26 02:00"


def test_iter_results_is_generator() -> None:
    results = iter_results(HISTORY, "a/fast")
    assert next(results).uptime == 99.0
    assert next(results).uptime == 97.0


def test_last_result() -> None:
    assert last_result(HISTORY, "b/slow").status == STATUS_DOWN
    assert last_result(HISTORY, "c/new") is None


def test_model_stats() -> None:
    stats = ModelStats(SLOW)
    for result in iter_results(HISTORY, SLOW.id):
        stats.add(result)
    assert stats.checks == 2
    assert stats.available == 0
    assert stats.percent == 0.0
    assert stats.avg_uptime == 70.0


def test_collect_stats_most_stable_first() -> None:
    stats = collect_stats(HISTORY)
    assert [item.model for item in stats] == [FAST, SLOW]
    assert stats[0].percent == 100.0


def test_collect_stats_empty_history() -> None:
    assert collect_stats([]) == []


def test_sort_models_by_name() -> None:
    names = [model.name for model in sort_models(MODELS, HISTORY)]
    assert names == ["Fast model", "New model", "Slow model"]


def test_sort_models_by_uptime_puts_unknown_last() -> None:
    history = HISTORY[:2]
    ordered = sort_models(MODELS, history, by_uptime=True)
    assert ordered == [FAST, SLOW, NEW]
