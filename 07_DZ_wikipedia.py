from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re


def init_browser():
    """Инициализация браузера"""
    options = webdriver.FirefoxOptions()
    # options.add_argument('--headless')  # Раскомментируй, если не хочешь видеть браузер
    return webdriver.Firefox(options=options)


def search_wikipedia(browser, query):
    """Поиск запроса в Википедии"""
    browser.get("https://ru.wikipedia.org/wiki/Служебная:Поиск")

    try:
        # Ждём появления поля поиска
        wait = WebDriverWait(browser, 10)
        search_box = wait.until(
            EC.presence_of_element_located((By.ID, "searchInput"))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        # Ждём загрузки результата
        time.sleep(3)
        return True
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return False


def get_article_title(browser):
    """Получить заголовок текущей статьи"""
    try:
        title = browser.find_element(By.ID, "firstHeading")
        return title.text
    except:
        return "Без заголовка"


def get_paragraphs(browser):
    """Получить все параграфы статьи (основной контент)"""
    try:
        # Ищем основной контент статьи
        content = browser.find_element(By.ID, "mw-content-text")
        # Находим все <p> внутри контента, но не внутри таблиц и шаблонов
        paragraphs = content.find_elements(By.CSS_SELECTOR, "p:not(.mw-empty-elt)")

        # Фильтруем: убираем пустые и служебные параграфы
        clean_paragraphs = []
        for p in paragraphs:
            text = p.text.strip()
            # Пропускаем слишком короткие и служебные блоки
            if len(text) > 50 and not text.startswith("Материал из"):
                clean_paragraphs.append(text)

        return clean_paragraphs
    except:
        return []


def get_internal_links(browser, max_links=10):
    """Получить внутренние ссылки из статьи"""
    try:
        content = browser.find_element(By.ID, "mw-content-text")
        # Ищем ссылки, которые ведут на другие статьи Википедии
        links = content.find_elements(By.CSS_SELECTOR, "a[href^='/wiki/']")

        clean_links = []
        seen = set()

        for link in links:
            href = link.get_attribute("href")
            text = link.text.strip()

            # Фильтруем: только ссылки с текстом, не на спецстраницы
            if (text and
                    len(text) > 2 and
                    href and
                    ":" not in href.split("/")[-1] and  # исключаем Файл:, Категория: и т.д.
                    "#" not in href and  # исключаем якоря
                    text not in seen and
                    text.lower() not in ["править", "править код", "источник"]):

                seen.add(text)
                clean_links.append({"text": text, "href": href, "element": link})

                if len(clean_links) >= max_links:
                    break

        return clean_links
    except:
        return []


def scroll_paragraphs(paragraphs, title):
    """Режим просмотра параграфов статьи"""
    if not paragraphs:
        print("⚠️ В статье нет доступных параграфов для чтения.")
        return

    print(f"\n📖 Статья: {title}")
    print(f"📑 Всего параграфов: {len(paragraphs)}")
    print("=" * 70)

    current = 0
    page_size = 2  # Сколько параграфов показывать за раз

    while True:
        # Показываем текущую «страницу» параграфов
        start = current
        end = min(current + page_size, len(paragraphs))

        print(f"\n📄 Параграфы {start + 1}-{end} из {len(paragraphs)}:")
        print("-" * 70)

        for i in range(start, end):
            # Обрезаем очень длинные параграфы для удобства
            text = paragraphs[i]
            if len(text) > 500:
                text = text[:500] + "..."
            print(f"{i + 1}. {text}\n")

        # Меню навигации по параграфам
        print("\n🔹 Навигация:")
        print("  [N]ext — следующие параграфы")
        print("  [P]rev — предыдущие параграфы")
        print("  [T]op — в начало")
        print("  [B]ack — вернуться в главное меню")
        print("  [Q]uit — выйти из программы")

        choice = input("\nВаш выбор: ").strip().lower()

        if choice in ["n", "next", "н", "вперёд", "далее"]:
            if end < len(paragraphs):
                current = end
            else:
                print("🔚 Вы достигли конца статьи.")
                current = 0  # Зацикливаем в начало
        elif choice in ["p", "prev", "п", "назад"]:
            if current > 0:
                current = max(0, current - page_size)
            else:
                print("🔙 Вы в начале статьи.")
        elif choice in ["t", "top", "т", "начало"]:
            current = 0
        elif choice in ["b", "back", "м", "меню", "главное"]:
            return "menu"
        elif choice in ["q", "quit", "выход", "выход"]:
            return "exit"
        else:
            print("⚠️ Неверная команда, попробуйте снова.")


def choose_link(links, title):
    """Предложить пользователю выбрать ссылку для перехода"""
    if not links:
        print("⚠️ В статье не найдено внутренних ссылок.")
        return None

    print(f"\n🔗 Ссылки из статьи «{title}»:")
    print("=" * 70)

    # Показываем нумерованный список ссылок
    for i, link in enumerate(links, start=1):
        # Обрезаем длинные названия
        text = link["text"]
        if len(text) > 50:
            text = text[:47] + "..."
        print(f"{i}. {text}")

    print(f"\n🔹 Введите номер ссылки (1-{len(links)}) для перехода")
    print("🔹 Или [B]ack — вернуться в главное меню")
    print("🔹 Или [Q]uit — выйти из программы")

    while True:
        choice = input("\nВаш выбор: ").strip().lower()

        if choice in ["b", "back", "м", "меню"]:
            return "menu"
        elif choice in ["q", "quit", "выход"]:
            return "exit"
        elif choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(links):
                return links[num - 1]  # Возвращаем выбранный словарь ссылки
            else:
                print(f"⚠️ Введите число от 1 до {len(links)}")
        else:
            print("⚠️ Неверный ввод, попробуйте снова.")


def main_menu():
    """Главное меню программы"""
    print("\n" + "🌐" * 35)
    print("📚 ВИКИ-ПОИСК: Консольный навигатор по Википедии")
    print("🌐" * 35)
    print("\nДоступные команды:")
    print("  • Введите запрос для поиска статьи")
    print("  • [Q]uit — выйти из программы")
    print("  • [H]elp — справка")
    print("-" * 70)


def main():
    """Основная функция программы"""
    browser = init_browser()
    current_url = None

    try:
        while True:
            # === ГЛАВНОЕ МЕНЮ ===
            main_menu()

            query = input("\n🔍 Введите запрос (или команду): ").strip()

            if query.lower() in ["q", "quit", "выход", "выход"]:
                print("👋 Спасибо за использование! До свидания!")
                break
            elif query.lower() in ["h", "help", "справка", "помощь"]:
                print("\n📖 Справка:")
                print("  • Введите любое слово или фразу для поиска в Википедии")
                print("  • После загрузки статьи вы сможете:")
                print("    - Листать параграфы ([N]/[P]/[T])")
                print("    - Перейти по внутренней ссылке")
                print("    - Вернуться в меню ([B]) или выйти ([Q])")
                continue
            elif not query:
                print("⚠️ Введите запрос для поиска.")
                continue

            # === ПОИСК И ПЕРЕХОД НА СТАТЬЮ ===
            print(f"\n🔎 Ищу «{query}» в Википедии...")
            if not search_wikipedia(browser, query):
                print("❌ Не удалось выполнить поиск. Попробуйте снова.")
                continue

            # === РАБОТА СО СТАТЬЁЙ ===
            while True:
                title = get_article_title(browser)
                print(f"\n✅ Загружена статья: «{title}»")

                # Меню действий со статьёй
                print("\n🔹 Что хотите сделать?")
                print("  [R]ead — листать параграфы статьи")
                print("  [L]inks — перейти по внутренней ссылке")
                print("  [N]ew search — новый поиск")
                print("  [Q]uit — выйти из программы")

                action = input("\nВаш выбор: ").strip().lower()

                if action in ["q", "quit", "выход"]:
                    print("👋 До свидания!")
                    return
                elif action in ["n", "new", "поиск", "новый"]:
                    break  # Возвращаемся к главному меню для нового поиска
                elif action in ["r", "read", "ч", "читать"]:
                    # === РЕЖИМ ЧТЕНИЯ ПАРАГРАФОВ ===
                    paragraphs = get_paragraphs(browser)
                    result = scroll_paragraphs(paragraphs, title)

                    if result == "exit":
                        return
                    # Если result == "menu" — продолжаем цикл статьи
                elif action in ["l", "links", "с", "ссылки"]:
                    # === РЕЖИМ ВЫБОРА ССЫЛКИ ===
                    links = get_internal_links(browser)
                    selected = choose_link(links, title)

                    if selected == "exit":
                        return
                    elif selected == "menu":
                        continue
                    elif selected:
                        # === ПЕРЕХОД ПО ВЫБРАННОЙ ССЫЛКЕ ===
                        print(f"\n🔗 Перехожу по ссылке: «{selected['text']}»")

                        try:
                            # Прокручиваем к элементу и кликаем
                            browser.execute_script("arguments[0].scrollIntoView();", selected["element"])
                            time.sleep(1)
                            selected["element"].click()
                            time.sleep(3)  # Ждём загрузки новой страницы
                            # Продолжаем цикл — теперь работаем с новой статьёй
                        except Exception as e:
                            print(f"❌ Ошибка перехода: {e}")
                            # Пробуем перейти по href напрямую
                            browser.get(selected["href"])
                            time.sleep(3)
                else:
                    print("⚠️ Неверная команда, попробуйте снова.")

    finally:
        # Гарантированно закрываем браузер при выходе
        print("\n🔄 Завершение работы...")
        browser.quit()


# 🔹 Запуск программы
if __name__ == "__main__":
    main()