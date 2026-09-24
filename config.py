"""Чтение API-ключа OpenRouter из переменной окружения или файла .env."""

import os

KEY_NAME = "OPENROUTER_API_KEY"
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


def parse_env_line(line: str) -> tuple[str, str] | None:
    """Разобрать строку вида КЛЮЧ=значение из файла .env."""
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    name, value = line.split("=", 1)
    return name.strip(), value.strip().strip('"').strip("'")


def load_api_key(env_file: str = ENV_FILE) -> str | None:
    """Вернуть API-ключ или None, если он не задан."""
    key = os.environ.get(KEY_NAME)
    if key:
        return key
    if not os.path.exists(env_file):
        return None
    with open(env_file, encoding="utf-8") as file:
        for line in file:
            pair = parse_env_line(line)
            if pair is not None and pair[0] == KEY_NAME and pair[1]:
                return pair[1]
    return None
