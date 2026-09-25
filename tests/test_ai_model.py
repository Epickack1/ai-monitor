"""Тесты класса AIModel и функций работы со списком моделей."""

from models import AIModel
from models.ai_model import (
    add_model,
    find_model,
    parse_price,
    remove_model,
    search_models,
)

CATALOG = [
    AIModel.from_api({
        "id": "openai/gpt-4o-mini", "name": "OpenAI: GPT-4o-mini",
        "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
    }),
    AIModel.from_api({
        "id": "z-ai/glm-5.2:free", "name": "Z.ai: GLM 5.2 (free)",
        "pricing": {"prompt": "0", "completion": "0"},
    }),
]


def test_model_creation() -> None:
    model = AIModel("openai/gpt-4o-mini", "OpenAI: GPT-4o-mini")
    assert model.id == "openai/gpt-4o-mini"
    assert model.name == "OpenAI: GPT-4o-mini"
    assert model.price is None


def test_model_str() -> None:
    model = AIModel("z-ai/glm-5.2:free", "GLM 5.2")
    assert str(model) == "GLM 5.2 [бесплатная] (z-ai/glm-5.2:free)"


def test_is_free_by_suffix_and_price() -> None:
    assert AIModel("z-ai/glm-5.2:free", "GLM").is_free
    assert AIModel("a/b", "Zero", price=0.0).is_free
    assert not AIModel("a/c", "Paid", price=0.001).is_free
    assert not AIModel("a/d", "Unknown").is_free


def test_from_api_reads_price() -> None:
    assert CATALOG[0].price > 0
    assert CATALOG[1].price == 0


def test_parse_price_handles_bad_data() -> None:
    assert parse_price(None) is None
    assert parse_price({"prompt": "0"}) is None
    assert parse_price({"prompt": "abc", "completion": "0"}) is None


def test_from_data_and_to_data_roundtrip() -> None:
    data = {"id": "a/b", "name": "Model B"}
    assert AIModel.from_data(data).to_data() == data


def test_validate_id() -> None:
    assert AIModel.validate_id("openai/gpt-4o-mini")
    assert not AIModel.validate_id("gpt-4o-mini")
    assert not AIModel.validate_id("openai/")
    assert not AIModel.validate_id("open ai/gpt")


def test_matches_case_insensitive() -> None:
    assert CATALOG[0].matches("GPT")
    assert not CATALOG[0].matches("claude")


def test_search_models() -> None:
    found = search_models(CATALOG, "GPT")
    assert [model.id for model in found] == ["openai/gpt-4o-mini"]


def test_search_models_free_only() -> None:
    assert search_models(CATALOG, "", free_only=True) == [CATALOG[1]]


def test_find_model() -> None:
    assert find_model(CATALOG, "z-ai/glm-5.2:free") is CATALOG[1]
    assert find_model(CATALOG, "unknown/model") is None


def test_add_model_rejects_duplicates() -> None:
    models = []
    assert add_model(models, AIModel("a/b", "Model B"))
    assert not add_model(models, AIModel("a/b", "Model B"))
    assert len(models) == 1


def test_remove_model() -> None:
    models = [AIModel("a/b", "Model B")]
    assert remove_model(models, "a/b")
    assert not remove_model(models, "a/b")
    assert models == []
