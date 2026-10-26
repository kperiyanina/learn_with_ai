import json
import logging
import math
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from services.ai import _request_plan, _strip_json_fences

logger = logging.getLogger(__name__)

MATERIAL_TYPES = ("Курс", "Статья", "Видео", "Книга", "Документация", "Тренажёр")
RUSSIAN_SOURCE_DOMAINS = {
    "stepik.org",
    "openedu.ru",
    "skillbox.ru",
    "netology.ru",
    "practicum.yandex.ru",
    "htmlacademy.ru",
    "habr.com",
    "tproger.ru",
    "python.ru",
}


def build_learning_material_prompt(
    goal: str,
    level: str,
    topic: str,
    hours_per_week: int,
    tasks: tuple[str, ...] = (),
    preferred_format: str = "Смешанный формат",
) -> str:
    task_list = "\n".join(f"- {task}" for task in tasks) or "- Задачи блока не указаны"
    return f"""
Создай учебный материал на русском языке для одного блока обучения.
Цель курса: {goal}
Уровень ученика: {level}
Тема блока: {topic}
Доступная нагрузка на неделю: {hours_per_week} часов.
В блоке {len(tasks) or "несколько"} учебных задач:
{task_list}
Предпочтительный формат занятий: {preferred_format}

Материал должен объяснять тему самостоятельно, без обязательных внешних ссылок.
Материал должен соответствовать задачам блока и формату занятий. Распредели
содержание так, чтобы его можно было пройти в пределах {hours_per_week} часов
недели вместе с практикой. Для формата «Теория» сделай акцент на объяснениях
и примерах; для «Практика» — на упражнениях; для «Проектная работа» — на
пошаговом результате; для «Смешанный формат» — сбалансируй эти элементы.
Верни только JSON-объект такого формата:
{{
  "theory": "Понятное структурированное объяснение темы с примерами.",
  "task_guides": [
    {{
      "task": "Точная формулировка задачи из списка",
      "instruction": "Пошаговая инструкция, как выполнить задачу",
      "expected_result": "Что должно получиться после выполнения"
    }}
  ],
  "quiz": [
    {{
      "question": "Вопрос по теории",
      "options": ["Вариант 1", "Вариант 2", "Вариант 3"],
      "correct": 0,
      "explanation": "Почему этот ответ правильный"
    }}
  ],
  "resources": [
    {{"title": "Дополнительный материал", "url": "https://..."}}
  ]
}}

Требования:
1. Теория должна быть конкретной, практичной и рассчитанной на самостоятельное изучение.
2. Начни с ключевых понятий темы и объясни, как они связаны с практикой.
3. Выпиши основные термины и покажи один небольшой пример, который можно повторить.
4. После примера предложи наблюдение: как изменится результат при изменении входных данных.
5. Для каждой задачи из списка создай ровно одну task_guides с инструкцией и
   ожидаемым результатом. Не заменяй практику одним чек-листом.
6. Добавь от 3 до 5 вопросов теста, по 3-4 варианта ответа в каждом.
7. Поле correct — индекс правильного варианта, начиная с 0.
8. resources — необязательный массив: добавляй только проверенные ссылки, если они
   действительно нужны для углубления. Пустой массив допустим.
9. Не возвращай текст вне JSON и не делай ссылки обязательной частью объяснения.
"""


def _parse_json_response(content: str):
    cleaned = _strip_json_fences(content or "")
    if not cleaned:
        raise ValueError("Пустой ответ модели")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        escaped = re.sub(r"(?<!\\)\\(?=[\"\\/bfnrtu])", "", cleaned)
        try:
            return json.loads(escaped)
        except json.JSONDecodeError:
            repaired = cleaned
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
            repaired = re.sub(r"(\"(?:[^\"\\]|\\.)*?\")\s*:\s*\"([^\"\\]*(?:\\.[^\"\\]*)*)?\"", lambda m: m.group(0), repaired)
            repaired = repaired.replace("\n", " ")
            repaired = re.sub(r"(?<!\\)\"\s*\n\s*\"", '\\"', repaired)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Невалидный JSON от модели: {exc.msg} (строка {exc.lineno}, столбец {exc.colno})") from exc


def generate_learning_material(
    goal: str,
    level: str,
    topic: str,
    hours_per_week: int = 5,
    tasks: tuple[str, ...] = (),
    preferred_format: str = "Смешанный формат",
) -> dict:
    try:
        content = _request_plan(
            build_learning_material_prompt(
                goal,
                level,
                topic,
                hours_per_week,
                tasks,
                preferred_format,
            )
        )
        raw_material = _parse_json_response(content)
        material = _validate_learning_material(raw_material, topic, goal, tasks)
        if material is not None:
            return material
        logger.warning("ИИ вернул неполный учебный материал для темы %s", topic)
    except (json.JSONDecodeError, TypeError, ValueError, RuntimeError) as error:
        logger.warning("Не удалось получить учебный материал: %s", error)
    except Exception as error:
        logger.warning("Ошибка генерации учебного материала: %s", error)

    return _fallback_learning_material(topic, tasks)


def _validate_learning_material(
    raw_material,
    topic: str = "",
    goal: str = "",
    tasks: tuple[str, ...] = (),
) -> dict | None:
    if not isinstance(raw_material, dict):
        return None
    theory = str(raw_material.get("theory", "")).strip()
    raw_task_guides = raw_material.get("task_guides", [])
    raw_quiz = raw_material.get("quiz")
    if (
        not theory
        or not isinstance(raw_task_guides, list)
        or len(raw_task_guides) != len(tasks)
        or not isinstance(raw_quiz, list)
        or not 3 <= len(raw_quiz) <= 5
    ):
        return None

    task_guides = []
    for expected_task, item in zip(tasks, raw_task_guides):
        if not isinstance(item, dict):
            return None
        task = str(item.get("task", "")).strip()
        instruction = str(item.get("instruction", "")).strip()
        expected_result = str(item.get("expected_result", "")).strip()
        if task != expected_task.strip() or not instruction or not expected_result:
            return None
        task_guides.append(
            {
                "task": task,
                "instruction": instruction,
                "expected_result": expected_result,
            }
        )

    quiz = []
    for item in raw_quiz:
        if not isinstance(item, dict):
            return None
        question = str(item.get("question", "")).strip()
        options = item.get("options")
        explanation = str(item.get("explanation", "")).strip()
        correct = item.get("correct")
        if (
            not question
            or not isinstance(options, list)
            or not 2 <= len(options) <= 5
            or not all(str(option).strip() for option in options)
            or not isinstance(correct, int)
            or isinstance(correct, bool)
            or not 0 <= correct < len(options)
        ):
            return None
        quiz.append(
            {
                "question": question,
                "options": [str(option).strip() for option in options],
                "correct": correct,
                "explanation": explanation,
            }
        )

    resources = []
    for item in raw_material.get("resources", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().removeprefix("www.")
        allowed_domain = any(
            domain == allowed or domain.endswith("." + allowed)
            for allowed in RUSSIAN_SOURCE_DOMAINS
        )
        available, _ = check_material_url(url) if allowed_domain else (False, "")
        relevant, _ = (
            check_material_relevance(url, topic, goal)
            if available
            else (False, "")
        )
        if title and parsed_url.scheme in {"http", "https"} and parsed_url.netloc and relevant:
            resources.append({"title": title[:200], "url": url})

    return {
        "theory": theory,
        "task_guides": task_guides,
        "quiz": quiz,
        "resources": resources[:5],
    }


def _fallback_learning_material(topic: str, tasks: tuple[str, ...] = ()) -> dict:
    return {
        "theory": (
            f"Тема блока — «{topic}». Начните с ключевых понятий и их связи с "
            "практикой. Выпишите основные термины, разберите один небольшой "
            "пример и затем попробуйте повторить его самостоятельно. После "
            "этого измените входные данные и проверьте, как меняется результат."
        ),
        "task_guides": [
            {
                "task": task,
                "instruction": (
                    f"Разберите задачу «{task}», выпишите необходимые шаги, "
                    "выполните их на небольшом примере и проверьте результат."
                ),
                "expected_result": (
                    "Есть выполненный пример, проверенный результат и краткий вывод "
                    "о том, что было изучено."
                ),
            }
            for task in tasks
        ],
        "quiz": [
            {
                "question": f"Что является первым шагом при изучении темы «{topic}»?",
                "options": [
                    "Разобраться с ключевыми понятиями",
                    "Сразу перейти к сложному проекту",
                    "Пропустить объяснение и запомнить ответ",
                ],
                "correct": 0,
                "explanation": "Базовые понятия помогают понимать дальнейшие примеры и практику.",
            },
            {
                "question": "Как лучше закрепить новый материал?",
                "options": [
                    "Выполнить практическое задание и изменить пример",
                    "Только перечитать теорию",
                    "Не проверять результат",
                ],
                "correct": 0,
                "explanation": "Практика и самостоятельное изменение примера проверяют понимание.",
            },
            {
                "question": "Что сделать после выполнения задания?",
                "options": [
                    "Проверить результат и сформулировать вывод",
                    "Удалить решение без проверки",
                    "Перейти к другой теме, не разбирая ошибки",
                ],
                "correct": 0,
                "explanation": "Проверка и вывод помогают заметить ошибки и закрепить навык.",
            },
        ],
        "resources": [],
    }


def build_material_prompt(
    goal: str,
    level: str,
    topic: str,
    hours_per_week: int,
) -> str:
    return f"""
Сформируй до 5 материалов для русскоязычного учебного курса.
Цель: {goal}
Уровень: {level}
Тема: {topic}
Доступная нагрузка на неделю: {hours_per_week} часов

Верни только JSON-массив из 3-5 объектов формата:
[{{"title": "Название материала", "url": "https://...", "material_type": "Статья", "tags": "тег1, тег2"}}]
Не возвращай конспект, теоретический блок, план урока, объяснение темы или
текст без конкретной ссылки на внешний материал. Каждый объект обязан содержать
одну реальную ссылку на отдельную страницу материала.
Название, тип и теги должны быть на русском языке. Используй только
русскоязычные источники с доменами stepik.org, openedu.ru, skillbox.ru,
netology.ru, practicum.yandex.ru, htmlacademy.ru, habr.com, tproger.ru,
python.ru. Ссылка должна вести непосредственно на материал по указанной теме.
Не выдумывай URL. Если не уверен, не включай материал.
Подбери объём, который реально пройти за {hours_per_week} часов в неделю.
"""


def recommend_materials(
    goal: str,
    level: str,
    topic: str,
    hours_per_week: int = 5,
) -> list[dict[str, str]]:
    for attempt in range(2):
        try:
            content = _request_plan(
                build_material_prompt(goal, level, topic, hours_per_week)
                + (
                    "\nЭто повторная попытка. Верни только ссылки, в существовании "
                    "которых уверен, и строго по теме блока."
                    if attempt
                    else ""
                )
            )
            raw_items = json.loads(_strip_json_fences(content))
        except (json.JSONDecodeError, TypeError, ValueError, RuntimeError) as error:
            logger.warning("Не удалось получить рекомендации материалов: %s", error)
            continue

        recommendations = _validate_recommendations(
            raw_items, topic, goal, verify_content=True
        )
        if recommendations:
            return recommendations
        # Some educational sites block automated HTML reads while remaining
        # usable for the learner. Keep structurally valid links in that case;
        # explicit content mismatches are still rejected by the strict pass.
        recommendations = _validate_recommendations(
            raw_items, topic, goal, verify_content=False
        )
        if recommendations:
            logger.warning(
                "Материалы прошли проверку ссылки, но содержимое не удалось "
                "автоматически подтвердить для темы %s",
                topic,
            )
            return recommendations
    return []


def _validate_recommendations(
    raw_items,
    topic: str = "",
    goal: str = "",
    verify_content: bool = True,
) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        return []
    recommendations = []
    seen_urls = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        material_type = str(item.get("material_type", "")).strip()
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower().removeprefix("www.")
        russian_text = f"{title} {material_type} {item.get('tags', '')}"
        if (
            not title
            or parsed_url.scheme not in {"http", "https"}
            or material_type not in MATERIAL_TYPES
            or url in seen_urls
            or not any("а" <= char.lower() <= "я" for char in russian_text)
            or not any(
                domain == allowed or domain.endswith("." + allowed)
                for allowed in RUSSIAN_SOURCE_DOMAINS
            )
        ):
            continue
        available, _ = check_material_url(url)
        if not available:
            continue
        relevant, reason = check_material_relevance(url, topic, goal)
        if not relevant and reason.startswith("Тема блока"):
            logger.info("Материал отклонён как нерелевантный: %s (%s)", url, reason)
            continue
        if verify_content and not relevant:
            continue
        seen_urls.add(url)
        recommendations.append(
            {
                "title": title[:200],
                "url": url,
                "material_type": material_type,
                "tags": str(item.get("tags", "")).strip()[:500],
            }
        )
    return recommendations[:5]


class _MaterialPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = []
        self.description = []
        self.text = []
        self._in_title = False
        self._in_description = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._in_title = tag.lower() == "title"
        self._in_description = (
            tag.lower() == "meta"
            and (
                attrs_dict.get("name", "").lower() == "description"
                or attrs_dict.get("property", "").lower() == "og:description"
            )
        )
        if self._in_description and attrs_dict.get("content"):
            self.description.append(attrs_dict["content"])

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False
        if tag.lower() == "meta":
            self._in_description = False

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        elif self._in_description:
            self.description.append(data)
        else:
            self.text.append(data)


def _topic_tokens(value: str) -> set[str]:
    stop_words = {
        "основы", "основа", "изучение", "изучить", "курс", "урок", "тема",
        "для", "по", "как", "при", "это", "and", "the", "with",
    }
    return {
        token.lower()
        for token in re.findall(r"[a-zа-яё][a-zа-яё0-9-]{2,}", value.lower())
        if token.lower() not in stop_words
    }


def _token_matches(token: str, candidate: str) -> bool:
    if token == candidate:
        return True
    if len(token) >= 5 and len(candidate) >= 5:
        return token.startswith(candidate[:5]) or candidate.startswith(token[:5])
    return False


def check_material_relevance(
    url: str,
    topic: str,
    goal: str = "",
    timeout: float = 5.0,
) -> tuple[bool, str]:
    """Confirm that the page itself mentions the requested learning topic."""
    expected = _topic_tokens(topic) or _topic_tokens(goal)
    if not expected:
        return False, "Тема блока не содержит проверяемых ключевых слов."

    try:
        request = Request(
            url,
            headers={
                "User-Agent": "LearnWithAI/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and "html" not in content_type:
                return False, "Ссылка ведёт не на HTML-страницу материала."
            html = response.read(300_000).decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, ValueError, UnicodeError) as error:
        return False, f"Не удалось прочитать содержимое страницы: {error}"

    parser = _MaterialPageParser()
    parser.feed(html)

    page_title = " ".join(parser.title)
    metadata = " ".join(parser.description)
    page_text = " ".join(parser.text)
    strong_text = f"{page_title} {metadata}".lower()
    all_text = f"{strong_text} {page_text}".lower()
    strong_matches = sum(
        any(_token_matches(token, candidate) for candidate in _topic_tokens(strong_text))
        for token in expected
    )
    all_matches = sum(
        any(_token_matches(token, candidate) for candidate in _topic_tokens(all_text))
        for token in expected
    )
    required = max(1, math.ceil(len(expected) * 0.4))
    if all_matches < required or strong_matches == 0:
        return False, "Заголовок или содержимое страницы не подтверждает тему блока."
    return True, "Тема блока подтверждена содержимым страницы."


def check_material_url(url: str, timeout: float = 5.0) -> tuple[bool, str]:
    request = Request(url, method="HEAD", headers={"User-Agent": "LearnWithAI/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return True, f"Ссылка доступна (HTTP {response.status})."
    except HTTPError as error:
        if error.code not in {404, 410}:
            try:
                with urlopen(
                    Request(
                        url,
                        headers={
                            "Range": "bytes=0-0",
                            "User-Agent": "LearnWithAI/1.0",
                        },
                    ),
                    timeout=timeout,
                ) as response:
                    return True, f"Ссылка доступна (HTTP {response.status})."
            except (HTTPError, URLError, TimeoutError):
                pass
        return False, f"Сайт вернул HTTP {error.code}."
    except (URLError, TimeoutError, ValueError):
        return False, "Не удалось проверить доступность ссылки."
