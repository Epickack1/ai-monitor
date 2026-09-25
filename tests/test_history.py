"""Тесты истории проверок, статистики и сортировки моделей."""

from history import (
    add_record,
    collect_stats,
    is_valid_record,
    iter_records,
    last_record,
    make_record,
    model_stats,
    sort_models,
)
from monitor import STATUS_AVAILABLE, STATUS_DOWN, STATUS_UNSTABLE
from storage import load_history, save_history

HISTORY = [
    make_record("a/fast", STATUS_AVAILABLE, 99.0, "2026-09-26 10:00"),
    make_record("b/slow", STATUS_UNSTABLE, 70.0, "2026-09-26 10:00"),
    make_record("a/fast", STATUS_AVAILABLE, 97.0, "2026-09-26 11:00"),
    make_record("b/slow", STATUS_DOWN, None, "2026-09-26 11:00"),
]

MODELS = [
    {"id": "b/slow", "name": "Slow model"},
    {"id": "c/new", "name": "New model"},
    {"id": "a/fast", "name": "Fast model"},
]


def test_make_record_sets_time() -> None:
    record = make_record("a/b", STATUS_AVAILABLE, 99.5)
    assert record["model_id"] == "a/b"
    assert record["checked_at"]
    assert is_valid_record(record)


def test_is_valid_record_rejects_broken_data() -> None:
    assert not is_valid_record("не словарь")
    assert not is_valid_record({"model_id": "a/b"})
    broken = make_record("a/b", STATUS_AVAILABLE, 99.5)
    broken["uptime"] = "99%"
    assert not is_valid_record(broken)


def test_add_record_trims_old_records() -> None:
    history = []
    for hour in range(5):
        add_record(history, make_record("a/b", STATUS_AVAILABLE, 99.0,
                                        f"2026-09-26 0{hour}:00"), limit=3)
    assert len(history) == 3
    assert history[0]["checked_at"] == "2026-09-26 02:00"


def test_iter_records_is_generator() -> None:
    records = iter_records(HISTORY, "a/fast")
    assert next(records)["uptime"] == 99.0
    assert next(records)["uptime"] == 97.0


def test_last_record() -> None:
    assert last_record(HISTORY, "b/slow")["status"] == STATUS_DOWN
    assert last_record(HISTORY, "c/new") is None


def test_model_stats() -> None:
    stats = model_stats(HISTORY, "b/slow")
    assert stats["checks"] == 2
    assert stats["available"] == 0
    assert stats["avg_uptime"] == 70.0
    assert model_stats(HISTORY, "c/new") is None


def test_collect_stats_most_stable_first() -> None:
    stats = collect_stats(HISTORY)
    assert [item["model_id"] for item in stats] == ["a/fast", "b/slow"]
    assert stats[0]["percent"] == 100.0


def test_collect_stats_empty_history() -> None:
    assert collect_stats([]) == []


def test_sort_models_by_name() -> None:
    names = [model["name"] for model in sort_models(MODELS, HISTORY)]
    assert names == ["Fast model", "New model", "Slow model"]


def test_sort_models_by_uptime_puts_unknown_last() -> None:
    history = HISTORY[:2]
    ids = [model["id"]
           for model in sort_models(MODELS, history, by_uptime=True)]
    assert ids == ["a/fast", "b/slow", "c/new"]


def test_history_save_and_load_skips_invalid(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    assert save_history(HISTORY + [{"model_id": 1}], path)
    assert load_history(path) == HISTORY
