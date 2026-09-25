"""Вспомогательные функции: безопасный ввод, форматирование, замер времени."""

import functools
import time
from collections.abc import Callable
from typing import Any


def input_int(prompt: str) -> int:
    """Запросить целое число. При некорректном вводе запрос повторяется."""
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Введите число.")


def input_int_range(prompt: str, low: int, high: int) -> int:
    """Запросить целое число от low до high включительно."""
    while True:
        value = input_int(prompt)
        if low <= value <= high:
            return value
        print(f"  Введите число от {low} до {high}.")


def input_str(prompt: str) -> str:
    """Запросить непустую строку. Пустой ввод не принимается."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  Значение не может быть пустым.")


def input_yes_no(prompt: str) -> bool:
    """Запросить ответ да/нет. Пустой ввод считается ответом «нет»."""
    answer = input(prompt + " (д/н): ").strip().lower()
    return answer in ("д", "да", "y", "yes")


def format_uptime(value: float | None) -> str:
    """Отформатировать аптайм в процентах, например 99.5%."""
    if value is None:
        return "нет данных"
    return f"{value:.1f}%"


def timed(func: Callable[..., Any]) -> Callable[..., tuple[Any, int]]:
    """Декоратор: вернуть результат функции и время её работы в миллисекундах.

    Время замеряется и тогда, когда функция вернула сообщение об ошибке.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> tuple[Any, int]:
        started = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = int((time.perf_counter() - started) * 1000)
        return result, elapsed
    return wrapper
