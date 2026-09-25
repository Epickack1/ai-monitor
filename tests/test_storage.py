"""Тесты хранения данных в JSON, чтения API-ключа и вспомогательных функций."""

import json

from config import load_api_key, parse_env_line
from models import AIModel, CheckResult
from models.provider import STATUS_AVAILABLE, STATUS_DOWN
from openrouter import describe_http_error
from storage import load_history, load_watchlist, save_history, save_watchlist
from utils import format_uptime, timed


def test_save_and_load_watchlist_creates_objects(tmp_path) -> None:
    path = str(tmp_path / "watchlist.json")
    models = [AIModel("z-ai/glm-5.2:free", "Z.ai: GLM 5.2 (free)")]
    assert save_watchlist(models, path)
    loaded = load_watchlist(path)
    assert isinstance(loaded[0], AIModel)
    assert loaded[0].id == "z-ai/glm-5.2:free"
    assert loaded[0].name == "Z.ai: GLM 5.2 (free)"


def test_load_missing_file_returns_empty(tmp_path) -> None:
    assert load_watchlist(str(tmp_path / "nope.json")) == []


def test_load_broken_json_returns_empty(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ это не json", encoding="utf-8")
    assert load_watchlist(str(path)) == []


def test_load_skips_invalid_models(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    data = [{"id": "a/b", "name": "Model B"}, {"id": "a/c"}, "мусор"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert [model.id for model in load_watchlist(str(path))] == ["a/b"]


def test_load_not_a_list_returns_empty(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text('{"id": "a/b"}', encoding="utf-8")
    assert load_watchlist(str(path)) == []


def test_history_links_results_to_models(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    model = AIModel("a/b", "Model B")
    history = [
        CheckResult(model, STATUS_AVAILABLE, 99.0, "2026-09-26 10:00"),
        CheckResult(model, STATUS_DOWN, None, "2026-09-26 11:00"),
    ]
    assert save_history(history, path)

    loaded = load_history([model], path)
    assert len(loaded) == 2
    assert loaded[0].model is model
    assert loaded[1].to_data() == history[1].to_data()


def test_history_keeps_removed_models(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    removed = AIModel("old/model", "Old")
    save_history([
        CheckResult(removed, STATUS_AVAILABLE, 99.0, "2026-09-26 10:00"),
        CheckResult(removed, STATUS_AVAILABLE, 98.0, "2026-09-26 11:00"),
    ], path)

    loaded = load_history([], path)
    assert loaded[0].model.id == "old/model"
    assert loaded[0].model is loaded[1].model


def test_history_skips_invalid_records(tmp_path) -> None:
    path = tmp_path / "history.json"
    good = CheckResult(AIModel("a/b", "B"), STATUS_AVAILABLE, 99.0, "t")
    data = [good.to_data(), {"model_id": 1}, {**good.to_data(), "uptime": "x"}]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert len(load_history([], str(path))) == 1


def test_parse_env_line() -> None:
    assert parse_env_line("OPENROUTER_API_KEY=sk-123") == (
        "OPENROUTER_API_KEY", "sk-123")
    assert parse_env_line('KEY="value"') == ("KEY", "value")
    assert parse_env_line("# комментарий") is None
    assert parse_env_line("") is None


def test_load_api_key_from_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-test\n", encoding="utf-8")
    assert load_api_key(str(env_file)) == "sk-test"


def test_load_api_key_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert load_api_key(str(tmp_path / ".env")) is None


def test_describe_http_error() -> None:
    assert describe_http_error(401) == "неверный или отсутствующий API-ключ"
    assert describe_http_error(599) == "ошибка на стороне OpenRouter"
    assert describe_http_error(418) == "неизвестная ошибка"


def test_format_uptime() -> None:
    assert format_uptime(99.456) == "99.5%"
    assert format_uptime(None) == "нет данных"


def test_timed_decorator() -> None:
    @timed
    def add(first: int, second: int) -> int:
        """Сложить два числа."""
        return first + second

    result, elapsed = add(2, second=3)
    assert result == 5
    assert elapsed >= 0
    assert add.__name__ == "add"
    assert add.__doc__ == "Сложить два числа."
