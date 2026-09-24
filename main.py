"""AIMonitor — мониторинг доступности моделей ИИ в OpenRouter."""

from config import load_api_key
from monitor import (
    STATUS_AVAILABLE,
    STATUS_DOWN,
    STATUS_UNSTABLE,
    best_uptime,
    count_working,
    find_in_catalog,
    format_uptime,
    get_model_status,
    is_free,
    is_provider_working,
    search_models,
)
from openrouter import fetch_catalog, fetch_endpoints, send_test_prompt
from storage import add_model, load_watchlist, remove_model, save_watchlist
from utils import input_int, input_str, input_yes_no

SEARCH_LIMIT = 15


def print_model_summary(model: dict, endpoints: list[dict] | None) -> str:
    """Вывести краткий статус модели и вернуть его."""
    status = get_model_status(endpoints)
    print(f"  {model['name']} ({model['id']})")
    print(f"    Статус: {status}")
    if endpoints:
        working = count_working(endpoints)
        print(f"    Провайдеры: работают {working} из {len(endpoints)}")
        uptime_5m = format_uptime(best_uptime(endpoints, "uptime_last_5m"))
        uptime_30m = format_uptime(best_uptime(endpoints, "uptime_last_30m"))
        uptime_1d = format_uptime(best_uptime(endpoints, "uptime_last_1d"))
        print(
            f"    Аптайм: 5 мин {uptime_5m} · 30 мин {uptime_30m}"
            f" · сутки {uptime_1d}"
        )
    print()
    return status


def print_providers(endpoints: list[dict]) -> None:
    """Вывести подробную таблицу провайдеров модели."""
    print("    Провайдер                 Состояние   5 мин     сутки")
    for endpoint in endpoints:
        state = "работает" if is_provider_working(endpoint) else "сбой"
        name = endpoint.get("provider_name", "?")[:24]
        uptime_5m = format_uptime(endpoint.get("uptime_last_5m"))
        uptime_1d = format_uptime(endpoint.get("uptime_last_1d"))
        print(f"    {name:<25} {state:<11} {uptime_5m:<9} {uptime_1d}")
    print()


def check_all(models: list[dict]) -> None:
    """Проверить все отслеживаемые модели и вывести сводку."""
    print("\n=== Проверка всех моделей ===\n")
    if not models:
        print("  Список отслеживаемых моделей пуст.\n")
        return

    available = unstable = down = 0
    for model in models:
        status = print_model_summary(model, fetch_endpoints(model["id"]))
        if status == STATUS_AVAILABLE:
            available += 1
        elif status == STATUS_UNSTABLE:
            unstable += 1
        elif status == STATUS_DOWN:
            down += 1

    print(
        f"Итого: доступно {available} из {len(models)},"
        f" нестабильно {unstable}, недоступно {down}."
    )


def choose_model(models: list[dict]) -> dict | None:
    """Показать нумерованный список и вернуть выбранную модель."""
    if not models:
        print("  Список отслеживаемых моделей пуст.")
        return None

    print("\nОтслеживаемые модели:")
    for index, model in enumerate(models, 1):
        print(f"  {index}. {model['name']} ({model['id']})")

    choice = input_int("\nВведите номер модели: ")
    if 1 <= choice <= len(models):
        return models[choice - 1]
    print("  Неверный номер.")
    return None


def check_one(models: list[dict]) -> None:
    """Подробно проверить одну модель: статус и все её провайдеры."""
    model = choose_model(models)
    if model is None:
        return
    print()
    endpoints = fetch_endpoints(model["id"])
    print_model_summary(model, endpoints)
    if endpoints:
        print_providers(endpoints)


def list_models(models: list[dict]) -> None:
    """Вывести список отслеживаемых моделей без проверки."""
    print("\n=== Отслеживаемые модели ===\n")
    if not models:
        print("  Список пуст.\n")
        return
    for model in models:
        label = " [бесплатная]" if model["id"].endswith(":free") else ""
        print(f"  {model['name']}{label}")
        print(f"    id: {model['id']}")
    print()


def ensure_catalog(catalog: list[dict]) -> bool:
    """Загрузить каталог OpenRouter при первом обращении."""
    if catalog:
        return True
    print("  Загрузка каталога моделей OpenRouter...")
    catalog.extend(fetch_catalog())
    if not catalog:
        print("  Не удалось загрузить каталог: проверьте подключение.")
        return False
    return True


def search_catalog(catalog: list[dict]) -> None:
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
        label = " [бесплатная]" if is_free(model) else ""
        print(f"  {model['id']}{label}")
        print(f"    {model.get('name', '')}")
    if len(found) > SEARCH_LIMIT:
        print(f"  ...и ещё {len(found) - SEARCH_LIMIT}. Уточните запрос.")


def add_to_watchlist(models: list[dict], catalog: list[dict]) -> None:
    """Добавить модель в отслеживание по её id из каталога."""
    if not ensure_catalog(catalog):
        return
    model_id = input_str("Введите id модели (например, openai/gpt-4o-mini): ")
    model = find_in_catalog(catalog, model_id)
    if model is None:
        print("  Такой модели нет в каталоге OpenRouter.")
        print("  Найдите точный id через поиск (пункт 4).")
        return
    if not add_model(models, model_id, model.get("name", model_id)):
        print("  Модель уже отслеживается.")
        return
    if save_watchlist(models):
        print(f"  Модель '{model.get('name', model_id)}' добавлена.")
    else:
        print("  Не удалось сохранить список моделей.")


def remove_from_watchlist(models: list[dict]) -> None:
    """Удалить модель из отслеживания."""
    model = choose_model(models)
    if model is None:
        return
    remove_model(models, model["id"])
    if save_watchlist(models):
        print(f"  Модель '{model['name']}' удалена из отслеживания.")
    else:
        print("  Не удалось сохранить список моделей.")


def live_test(models: list[dict]) -> None:
    """Отправить модели короткий запрос и замерить время ответа."""
    api_key = load_api_key()
    if api_key is None:
        print("\n  API-ключ не задан. Впишите его в файл .env:")
        print("  OPENROUTER_API_KEY=sk-or-v1-...")
        return
    model = choose_model(models)
    if model is None:
        return
    print(f"\n  Отправка запроса модели {model['id']}...")
    success, text, elapsed = send_test_prompt(model["id"], api_key)
    if success:
        print(f"  Модель ответила за {elapsed} мс: {text}")
    else:
        print(f"  Ошибка через {elapsed} мс: {text}")


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
    print("0. Выход\n")


def main() -> None:
    """Точка запуска приложения."""
    models = load_watchlist()
    catalog: list[dict] = []

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "1":
            check_all(models)
        elif choice == "2":
            check_one(models)
        elif choice == "3":
            list_models(models)
        elif choice == "4":
            search_catalog(catalog)
        elif choice == "5":
            add_to_watchlist(models, catalog)
        elif choice == "6":
            remove_from_watchlist(models)
        elif choice == "7":
            live_test(models)
        elif choice == "0":
            print("\nДо свидания!")
            break
        else:
            print("\n  Неверный выбор. Попробуйте снова.")


if __name__ == "__main__":
    main()
