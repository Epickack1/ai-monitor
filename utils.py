"""Вспомогательные функции безопасного ввода."""


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
