"""Тесты хранения списка моделей и чтения API-ключа."""

from config import load_api_key, parse_env_line
from openrouter import describe_http_error
from storage import (
    add_model,
    is_watched,
    load_watchlist,
    remove_model,
    save_watchlist,
)


def test_save_and_load_roundtrip(tmp_path) -> None:
    path = str(tmp_path / "watchlist.json")
    models = [{"id": "z-ai/glm-5.2:free", "name": "Z.ai: GLM 5.2 (free)"}]
    assert save_watchlist(models, path)
    assert load_watchlist(path) == models


def test_load_missing_file_returns_empty(tmp_path) -> None:
    assert load_watchlist(str(tmp_path / "nope.json")) == []


def test_load_broken_json_returns_empty(tmp_path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{ это не json", encoding="utf-8")
    assert load_watchlist(str(path)) == []


def test_load_skips_invalid_models(tmp_path) -> None:
    path = str(tmp_path / "watchlist.json")
    good = {"id": "a/b", "name": "Model B"}
    save_watchlist([good, {"id": "a/c"}, "мусор"], path)
    assert load_watchlist(path) == [good]


def test_load_not_a_list_returns_empty(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text('{"id": "a/b"}', encoding="utf-8")
    assert load_watchlist(str(path)) == []


def test_add_model_rejects_duplicates() -> None:
    models = []
    assert add_model(models, "a/b", "Model B")
    assert not add_model(models, "a/b", "Model B")
    assert is_watched(models, "a/b")


def test_remove_model() -> None:
    models = [{"id": "a/b", "name": "Model B"}]
    assert remove_model(models, "a/b")
    assert not remove_model(models, "a/b")
    assert models == []


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
