"""Запросы к открытому API OpenRouter."""

import json
import urllib.error
import urllib.request

from models import AIModel, Provider
from utils import timed

API_URL = "https://openrouter.ai/api/v1"
USER_AGENT = "AIMonitor/1.0"
TIMEOUT = 15

HTTP_ERRORS = {
    400: "некорректный запрос",
    401: "неверный или отсутствующий API-ключ",
    402: "недостаточно средств на балансе OpenRouter",
    403: "доступ запрещён модерацией",
    404: "модель не найдена",
    408: "превышено время ожидания ответа",
    429: "слишком много запросов, попробуйте позже",
    502: "провайдер модели недоступен",
    503: "нет доступных провайдеров для модели",
}


def describe_http_error(code: int) -> str:
    """Вернуть понятное описание HTTP-ошибки OpenRouter."""
    if code in HTTP_ERRORS:
        return HTTP_ERRORS[code]
    if code >= 500:
        return "ошибка на стороне OpenRouter"
    return "неизвестная ошибка"


def get_json(path: str) -> dict | None:
    """Выполнить GET-запрос и вернуть разобранный JSON.

    Возвращает None, если ресурс не найден или сеть недоступна.
    """
    request = urllib.request.Request(
        API_URL + path, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_catalog() -> list[AIModel]:
    """Загрузить каталог всех моделей OpenRouter."""
    data = get_json("/models")
    if data is None:
        return []
    return [AIModel.from_api(item) for item in data.get("data", [])]


def fetch_providers(model_id: str) -> list[Provider] | None:
    """Загрузить провайдеров модели с их статусом и аптаймом.

    Возвращает None, если модель не найдена или сеть недоступна.
    """
    data = get_json(f"/models/{model_id}/endpoints")
    if data is None:
        return None
    endpoints = data.get("data", {}).get("endpoints", [])
    return [Provider.from_api(endpoint) for endpoint in endpoints]


@timed
def send_test_prompt(model_id: str, api_key: str) -> tuple[bool, str]:
    """Отправить модели короткий запрос.

    Возвращает пару: успешно ли и текст результата. Благодаря декоратору
    timed вызов возвращает ещё и время ответа: ((успех, текст), мс).
    """
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Ответь одним словом: ping"}],
        "max_tokens": 64,
    }
    request = urllib.request.Request(
        API_URL + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            answer = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return False, f"{exc.code}: {describe_http_error(exc.code)}"
    except (urllib.error.URLError, TimeoutError):
        return False, "нет ответа от сервера"

    if "error" in answer:
        return False, answer["error"].get("message", "ошибка модели")

    choices = answer.get("choices") or [{}]
    message = choices[0].get("message") or {}
    text = (message.get("content") or "").strip()
    if not text and message.get("reasoning"):
        text = "(ответ ушёл в рассуждения модели, лимит токенов исчерпан)"
    return True, text or "(пустой ответ)"
