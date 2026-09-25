"""AIMonitor — мониторинг доступности моделей ИИ в OpenRouter."""

from config import load_api_key
from models import AIModel, CheckResult, Provider
from models.ai_model import add_model, find_model, remove_model, search_models
from models.check import (
    add_result,
    collect_stats,
    iter_results,
    last_result,
    sort_models,
)
from models.provider import (
    STATUS_AVAILABLE,
    STATUS_DOWN,
    STATUS_UNSTABLE,
    best_uptime,
    count_working,
)
from openrouter import fetch_catalog, fetch_providers, send_test_prompt
from storage import load_history, load_watchlist, save_history, save_watchlist
from utils import (
    format_uptime,
    input_int,
    input_int_range,
    input_str,
    input_yes_no,
)

SEARCH_LIMIT = 15
HISTORY_LIMIT = 10


def check_model(model: AIModel) -> CheckResult:
    """Запросить провайдеров модели и оценить её доступность."""
    return CheckResult.from_providers(model, fetch_providers(model.id))


def print_check(result: CheckResult) -> None:
    """Вывести краткий результат проверки модели."""
    print(f"  {result.model.name} ({result.model.id})")
    print(f"    Статус: {result.status}")
    providers = result.providers
    if providers:
        working = count_working(providers)
        print(f"    Провайдеры: работают {working} из {len(providers)}")
        uptime_5m = format_uptime(best_uptime(providers, "uptime_5m"))
        uptime_30m = format_uptime(best_uptime(providers, "uptime_30m"))
        uptime_1d = format_uptime(best_uptime(providers, "uptime_1d"))
        print(
            f"    Аптайм: 5 мин {uptime_5m} · 30 мин {uptime_30m}"
            f" · сутки {uptime_1d}"
        )
    print()


def print_providers(providers: list[Provider]) -> None:
    """Вывести подробную таблицу провайдеров модели."""
    print("    Провайдер                 Состояние   5 мин     сутки")
    for provider in providers:
        print(f"    {provider}")
    print()


def save_history_or_warn(history: list[CheckResult]) -> None:
    """Сохранить историю и сообщить, если это не удалось."""
    if not save_history(history):
        print("  Не удалось сохранить историю проверок.")


def check_all(models: list[AIModel], history: list[CheckResult]) -> None:
    """Проверить все отслеживаемые модели и вывести сводку."""
    print("\n=== Проверка всех моделей ===\n")
    if not models:
        print("  Список отслеживаемых моделей пуст.\n")
        return

    available = unstable = down = 0
    for model in models:
        result = check_model(model)
        print_check(result)
        add_result(history, result)
        if result.status == STATUS_AVAILABLE:
            available += 1
        elif result.status == STATUS_UNSTABLE:
            unstable += 1
        elif result.status == STATUS_DOWN:
            down += 1

    print(
        f"Итого: доступно {available} из {len(models)},"
        f" нестабильно {unstable}, недоступно {down}."
    )
    save_history_or_warn(history)


def choose_model(models: list[AIModel]) -> AIModel | None:
    """Показать нумерованный список и вернуть выбранную модель."""
    if not models:
        print("  Список отслеживаемых моделей пуст.")
        return None

    print("\nОтслеживаемые модели:")
    for index, model in enumerate(models, 1):
        print(f"  {index}. {model.name} ({model.id})")

    choice = input_int("\nВведите номер модели: ")
    if 1 <= choice <= len(models):
        return models[choice - 1]
    print("  Неверный номер.")
    return None


def check_one(models: list[AIModel], history: list[CheckResult]) -> None:
    """Подробно проверить одну модель: статус и все её провайдеры."""
    model = choose_model(models)
    if model is None:
        return
    print()
    result = check_model(model)
    print_check(result)
    if result.providers:
        print_providers(result.providers)
    add_result(history, result)
    save_history_or_warn(history)


def list_models(models: list[AIModel], history: list[CheckResult]) -> None:
    """Вывести список отслеживаемых моделей в выбранном порядке."""
    print("\n=== Отслеживаемые модели ===\n")
    if not models:
        print("  Список пуст.\n")
        return

    print("Порядок: 1 — как добавлены, 2 — по названию,"
          " 3 — по аптайму последней проверки")
    order = input_int_range("Выберите порядок: ", 1, 3)
    if order == 2:
        models = sort_models(models, history)
    elif order == 3:
        models = sort_models(models, history, by_uptime=True)

    print()
    for model in models:
        print(f"  {model}")
        result = last_result(history, model.id)
        last_check = "ещё не проверялась" if result is None else result
        print(f"    Последняя проверка: {last_check}")
    print()


def ensure_catalog(catalog: list[AIModel]) -> bool:
    """Загрузить каталог OpenRouter при первом обращении."""
    if catalog:
        return True
    print("  Загрузка каталога моделей OpenRouter...")
    catalog.extend(fetch_catalog())
    if not catalog:
        print("  Не удалось загрузить каталог: проверьте подключение.")
        return False
    return True


def search_catalog(catalog: list[AIModel]) -> None:
    """Найти модели в каталоге OpenRouter по части названия."""
    if not ensure_catalog(catalog):
        return
    query = input_str("Введите часть названия или id: ")
    free_only = input_yes_no("Только бесплатные?")
    found = search_models(catalog, query, free_only)
    if not found:
        print("\n  Ничего не найдено.")
        return

    print(f"\nНайдено моделей: {len(found)}")
    for model in found[:SEARCH_LIMIT]:
        print(f"  {model}")
    if len(found) > SEARCH_LIMIT:
        print(f"  ...и ещё {len(found) - SEARCH_LIMIT}. Уточните запрос.")


def add_to_watchlist(models: list[AIModel], catalog: list[AIModel]) -> None:
    """Добавить модель в отслеживание по её id из каталога."""
    model_id = input_str("Введите id модели (например, openai/gpt-4o-mini): ")
    if not AIModel.validate_id(model_id):
        print("  Неверный формат id: нужно «разработчик/модель».")
        return
    if not ensure_catalog(catalog):
        return
    model = find_model(catalog, model_id)
    if model is None:
        print("  Такой модели нет в каталоге OpenRouter.")
        print("  Найдите точный id через поиск (пункт 4).")
        return
    if not add_model(models, model):
        print("  Модель уже отслеживается.")
        return
    if save_watchlist(models):
        print(f"  Модель '{model.name}' добавлена.")
    else:
        print("  Не удалось сохранить список моделей.")


def remove_from_watchlist(models: list[AIModel]) -> None:
    """Удалить модель из отслеживания."""
    model = choose_model(models)
    if model is None:
        return
    remove_model(models, model.id)
    if save_watchlist(models):
        print(f"  Модель '{model.name}' удалена из отслеживания.")
    else:
        print("  Не удалось сохранить список моделей.")


def live_test(models: list[AIModel]) -> None:
    """Отправить модели короткий запрос и замерить время ответа."""
    api_key = load_api_key()
    if api_key is None:
        print("\n  API-ключ не задан. Впишите его в файл .env:")
        print("  OPENROUTER_API_KEY=sk-or-v1-...")
        return
    model = choose_model(models)
    if model is None:
        return
    print(f"\n  Отправка запроса модели {model.id}...")
    (success, text), elapsed = send_test_prompt(model.id, api_key)
    if success:
        print(f"  Модель ответила за {elapsed} мс: {text}")
    else:
        print(f"  Ошибка через {elapsed} мс: {text}")


def show_stats(history: list[CheckResult]) -> None:
    """Вывести статистику доступности моделей по истории проверок."""
    print("\n=== Статистика доступности ===\n")
    stats = collect_stats(history)
    if not stats:
        print("  История пуста. Сначала проверьте модели (пункт 1 или 2).")
        return

    print(f"Всего проверок: {len(history)}, моделей: {len(stats)}\n")
    print("  Модель                               Проверок  Доступна"
          "  Ср. аптайм")
    for item in stats:
        print(f"  {item}")

    print(f"\nСамая стабильная: {stats[0].model.id}")
    if len(stats) > 1:
        print(f"Самая проблемная: {stats[-1].model.id}")


def show_model_history(
    models: list[AIModel], history: list[CheckResult]
) -> None:
    """Вывести последние проверки выбранной модели."""
    model = choose_model(models)
    if model is None:
        return
    results = list(iter_results(history, model.id))
    if not results:
        print("\n  Модель ещё не проверялась.")
        return

    print(f"\nПоследние проверки {model.id}:")
    for result in results[-HISTORY_LIMIT:]:
        print(f"  {result}")
    print(f"  Всего проверок: {len(results)}")


def print_menu() -> None:
    """Вывести главное меню."""
    print("\n=== AIMonitor ===\n")
    print("1. Проверить все модели")
    print("2. Проверить модель подробно")
    print("3. Показать отслеживаемые модели")
    print("4. Найти модель в каталоге OpenRouter")
    print("5. Добавить модель в отслеживание")
    print("6. Удалить модель из отслеживания")
    print("7. Живой тест модели (нужен API-ключ)")
    print("8. Статистика доступности")
    print("9. История проверок модели")
    print("0. Выход\n")


def main() -> None:
    """Точка запуска приложения."""
    models = load_watchlist()
    history = load_history(models)
    catalog: list[AIModel] = []

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            check_all(models, history)
        elif choice == "2":
            check_one(models, history)
        elif choice == "3":
            list_models(models, history)
        elif choice == "4":
            search_catalog(catalog)
        elif choice == "5":
            add_to_watchlist(models, catalog)
        elif choice == "6":
            remove_from_watchlist(models)
        elif choice == "7":
            live_test(models)
        elif choice == "8":
            show_stats(history)
        elif choice == "9":
            show_model_history(models, history)
        elif choice == "0":
            print("\nДо свидания!")
            break
        else:
            print("\n  Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nРабота прервана. До свидания!")
