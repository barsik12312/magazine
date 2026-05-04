#!/usr/bin/env python3
"""
build_task.py — Task Folder Builder for Nano Banana Pro

Собирает готовую папку задания, которую можно открыть и сразу работать
с Nano Banana Pro в Gemini: промпты + отобранные референсы + инструкции.

USAGE
-----
    python scripts/build_task.py \
        --type tshirt \
        --slug givenchy-v3 \
        --brief "Карточка футболки с принтом X. Фон — шкаф." \
        --photos path/to/photos \
        --print path/to/print.png \
        --references path/to/refs

    python scripts/build_task.py --type lingerie --slug summer-set ...
    python scripts/build_task.py --type clothing --slug avito-rework-jacket ...

OUTPUT
------
    stores/<type>s/tasks/YYYY-MM-DD_HH-MM_<slug>/
    ├── 00_BRIEF.md
    ├── READY_FOR_GEMINI/
    │   ├── README.txt
    │   ├── STEP_BY_STEP.txt
    │   ├── KNOWN_ISSUES.txt
    │   ├── 0X_PROMPT_*.txt   (по числу ракурсов)
    │   └── 0X_*.jpg          (отобранные референсы, пронумерованные)
    └── outputs/  (пустая, сюда сохраняешь готовые картинки)

Опция --copy-to-desktop дополнительно копирует папку в ~/Desktop/Tasks/
(для тех кто привык работать с рабочего стола).
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "templates"
BALCONY_TEMPLATE_DIR = REPO_ROOT / "stores" / "tshirts" / "backgrounds" / "balcony_template"

# Сценарии: какие ракурсы делаем для каждого типа товара.
# Имена файлов промптов и описаний.
SCENARIOS: dict[str, list[dict[str, str]]] = {
    "tshirt": [
        {"id": "01_FRONT_HANGER", "title": "Футболка спереди на вешалке"},
        {"id": "02_BACK_HANGER", "title": "Футболка сзади на вешалке"},
        {"id": "03_TAG", "title": "Бирка крупным планом"},
        {"id": "04_MODEL_FRONT", "title": "На модели, спереди"},
        {"id": "05_MODEL_BACK", "title": "На модели, сзади"},
    ],
    "lingerie": [
        {"id": "01_FULL_FRONT", "title": "Полный рост, анфас"},
        {"id": "02_FULL_BACK", "title": "Полный рост, сзади"},
        {"id": "03_DETAIL", "title": "Деталь — кружево / застёжка / бант"},
        {"id": "04_LIFESTYLE", "title": "Lifestyle — атмосферный кадр"},
    ],
    "clothing": [
        {"id": "01_AVITO_REWORK", "title": "Переделка скрина Авито в студию"},
        {"id": "02_CATALOG", "title": "Каталожное фото на модели"},
        {"id": "03_LIFESTYLE", "title": "Lifestyle / бренд-лента"},
    ],
}

# Какие шаблоны промптов использовать (из prompts/templates/*.md).
TEMPLATE_FILES = {
    "tshirt": "tshirt_hanger.md",
    "lingerie": "lingerie_studio.md",
    "clothing": "clothing_catalog.md",
}


def slugify(text: str) -> str:
    """Простой ASCII slug для имени папки."""
    text = text.lower().strip()
    # транслитерация русских букв
    cyr = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    lat = ("a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch "
           "' y ' e yu ya").split()
    table = dict(zip(cyr, lat))
    text = "".join(table.get(c, c) for c in text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "task"


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M")


def discover_image_files(folder: Path | None) -> list[Path]:
    if folder is None or not folder.exists():
        return []
    if folder.is_file():
        return [folder]
    exts = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    return sorted([p for p in folder.iterdir() if p.suffix.lower() in exts])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_brief(task_dir: Path, ttype: str, slug: str, brief: str,
               scenarios: list[dict[str, str]]) -> None:
    lines = [
        f"# Задание: {slug} ({ttype})",
        "",
        f"> Создано {now_stamp()} скриптом `scripts/build_task.py`.",
        "",
        "## ТЗ",
        "",
        brief.strip() if brief else "_(не заполнено — отредактируй вручную)_",
        "",
        "## Что делаем",
        "",
        "| № | Что | Описание |",
        "|---|-----|----------|",
    ]
    for s in scenarios:
        lines.append(f"| {s['id'].split('_')[0]} | {s['id']} | {s['title']} |")
    lines += [
        "",
        "## Что делать",
        "1. Открой `READY_FOR_GEMINI/`",
        "2. Используй отдельный `0X_PROMPT_*.txt` на каждую картинку",
        "3. Для tshirt-задач balcony references — обязательный scene lock",
        "4. Готовые картинки сохраняй в `outputs/`",
        "",
    ]
    write_text(task_dir / "00_BRIEF.md", "\n".join(lines))


def make_readme(target: Path, ttype: str, scenarios: list[dict[str, str]]) -> None:
    lines = [
        "═" * 71,
        "  ЭТА ПАПКА — ГОТОВЫЙ ПАКЕТ ДЛЯ NANO BANANA PRO",
        "═" * 71,
        "",
        f"  Тип задания: {ttype}",
        f"  Ракурсов: {len(scenarios)}",
        "",
        "  ЧТО ДЕЛАТЬ:",
        "  1) На каждую картинку используй отдельный 0X_PROMPT_*.txt",
        "  2) Прикладывай именно те референсы, которые перечислены в промпте",
        "  3) Для tshirt hanger shots balcony refs обязательны",
        "  4) Если что-то идёт не так — открой KNOWN_ISSUES.txt",
        "  5) Готовые картинки сохраняй в ../outputs/",
        "",
        "  СОДЕРЖИМОЕ:",
    ]
    for s in scenarios:
        lines.append(f"    {s['id']}_PROMPT.txt  ← {s['title']}")
    lines += [
        "    + изображения для загрузки в Gemini (пронумерованы)",
        "",
        "═" * 71,
    ]
    write_text(target / "README.txt", "\n".join(lines))


def make_step_by_step(target: Path, scenarios: list[dict[str, str]]) -> None:
    lines = [
        "═" * 71,
        "  ИНСТРУКЦИЯ ДЛЯ NANO BANANA PRO (Gemini)",
        "═" * 71,
        "",
        "  ОБЩИЙ ПРИНЦИП",
        "  1. На каждую картинку есть отдельный полноценный промпт",
        "  2. Если используешь Gemini — лучше держать серию в одном чате",
        "  3. Но промпты можно использовать и в других моделях",
        "  4. Для tshirt hanger shots balcony references обязательны",
        "",
    ]
    for i, s in enumerate(scenarios, 1):
        lines += [
            f"  ШАГ {i} — {s['id']} ({s['title']})",
            "  ─" * 35,
            f"  1. Открой файл: {s['id']}_PROMPT.txt",
            "  2. Скопируй весь текст (Ctrl+A → Ctrl+C)",
            "  3. Вставь в чат Gemini (Ctrl+V), но пока НЕ отправляй",
            "  4. Прикрепи изображения, на которые ссылается промпт",
            "     (см. список 'REFERENCE IMAGES' в начале промпта)",
            "  5. Отправь сообщение",
            "  6. Если результат не идеал — итерируй (см. KNOWN_ISSUES.txt)",
            f"  7. Сохрани финал → ../outputs/{s['id'].lower()}.png",
            "",
        ]
    lines += [
        "═" * 71,
        "  ВАЖНО:",
        "  • Все ракурсы делаем В ОДНОМ ЧАТЕ — Pro помнит контекст",
        "  • Если 3-4 итерации не помогают — переходи в Photopea",
        "    (см. docs/workflows/tshirt_print_mockup.md)",
        "═" * 71,
    ]
    write_text(target / "STEP_BY_STEP.txt", "\n".join(lines))


KNOWN_ISSUES_TEMPLATE = """\
═══════════════════════════════════════════════════════════════════════
  ИЗВЕСТНЫЕ ПРОБЛЕМЫ NANO BANANA PRO И КАК ИХ ОБОЙТИ
═══════════════════════════════════════════════════════════════════════

ПРОБЛЕМА 1: FRONT PRINT ломается как текст
─────────────────────────────────────────────────────────────────────
  Решение A — попроси перерендерить с прямым указанием:
    "Treat image [N] as a finished graphic asset, not as text to be
    re-rendered. Copy its visual appearance exactly onto the shirt.
    Do not respell, redesign, or simplify any part of it."

  Решение B — финиш в Photopea (5 минут, бесплатно):
    1. https://www.photopea.com
    2. Открой результат + PNG-принт
    3. Перенеси принт как слой → Blend Mode "Multiply"
    4. Свободная трансформация (Ctrl+T) подгони размер
    5. Filter → Distort → Displacement Map (футболку как displace-карту)
    6. Сохрани как PNG

ПРОБЛЕМА 2: Балкон / сцена отличается от референса
─────────────────────────────────────────────────────────────────────
  "Keep the exact same balcony scene from the references. This is a
  locked real environment, not a loosely inspired setup. Do not change
  any detail, object, placement, geometry, or crop logic."

ПРОБЛЕМА 3: Цвет товара плавает между ракурсами
─────────────────────────────────────────────────────────────────────
  "All shots in this series must use the same exact [color] for the
  [garment]. Re-render with consistent color — color temperature 5500K."

  Финал: Photopea → Image → Adjustments → Color Balance.

ПРОБЛЕМА 4: Лицо модели слишком яркое / похоже на знаменитость
─────────────────────────────────────────────────────────────────────
  "Make the model's face less prominent — frame higher, partial face,
  hair over face, or looking down. Focus on the garment, not on a
  specific identifiable face."

ПРОБЛЕМА 5: На фото-на-модели принт другой / меньше / в другом месте
─────────────────────────────────────────────────────────────────────
  "The print must be SAME SIZE and SAME POSITION as in the previous
  hanger shot. Re-render."

ПРОБЛЕМА 6: AI-артефакты (6 пальцев, искажения, melted edges)
─────────────────────────────────────────────────────────────────────
  Проще всего: перегенерировать. Pro обычно фиксит со 2-3 раза.
  Если упорно — попроси сменить позу/ракурс или добавь в промпт:
    "No AI artifacts: hands must have exactly 5 fingers each, no
    extra limbs, no melted facial features."

═══════════════════════════════════════════════════════════════════════
  ОБЩИЕ ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════

  • НЕ начинай новый чат на каждый ракурс — Pro помнит контекст
  • Делай все ракурсы в ОДНОМ чате последовательно
  • Если 3-4 итерации не помогают — переходи в Photopea
  • Для tshirts правильная логика: balcony = locked scene, print = finished graphic asset
  • Текст и логотипы — слабая зона ИИ, считай нормой ручную доработку
  • Сохраняй промежуточные версии (иногда 1-я генерация лучше 4-й)
  • 4K режим (если есть) — лучше включить для финала

═══════════════════════════════════════════════════════════════════════
"""


def make_known_issues(target: Path) -> None:
    write_text(target / "KNOWN_ISSUES.txt", KNOWN_ISSUES_TEMPLATE)


def extract_template_block(template_path: Path, scenario_id: str) -> str:
    """Достаёт релевантный блок промпта из шаблона.

    Шаблоны размечены заголовками с упоминанием ракурса.
    Если ничего не нашли — возвращаем весь шаблон.
    """
    if not template_path.exists():
        return f"[Не найден шаблон {template_path}]"
    text = template_path.read_text(encoding="utf-8")
    keyword = scenario_id.split("_", 1)[1] if "_" in scenario_id else scenario_id
    keyword = keyword.lower()
    blocks: list[str] = []
    current: list[str] = []
    capture = False
    for line in text.splitlines():
        if line.startswith("## ") or line.startswith("# "):
            if capture and current:
                blocks.append("\n".join(current))
                current = []
            capture = keyword in line.lower()
        if capture:
            current.append(line)
    if capture and current:
        blocks.append("\n".join(current))
    if blocks:
        return "\n\n".join(blocks)
    return text


def make_prompts(target: Path, ttype: str,
                 scenarios: list[dict[str, str]],
                 brief: str, image_count: int) -> None:
    template_file = PROMPTS_DIR / TEMPLATE_FILES[ttype]
    intro_lines = [
        "═" * 71,
        f"  PROMPT TEMPLATE FOR NANO BANANA PRO",
        "═" * 71,
        "",
        "ВАЖНО: ниже — полноценная заготовка из общего шаблона.",
        "ОБЯЗАТЕЛЬНО заполни плейсхолдеры в [QUADRATIC BRACKETS] под свой",
        "конкретный товар. Если это tshirt-задача, считай balcony references",
        "обязательным scene lock, а print reference — finished graphic asset.",
        "",
        f"BRIEF: {brief.strip() if brief else '(заполни вручную)'}",
        "",
        f"REFERENCE IMAGES: прикреплено {image_count} файла. См. отдельные",
        "файлы 0X_*.jpg в этой папке. Промпт ссылается на них как 'image 1',",
        "'image 2' и т.д. — порядок прикрепления должен совпадать с номерами.",
        "",
        "═" * 71,
        "",
    ]
    for s in scenarios:
        body = extract_template_block(template_file, s["id"])
        full = "\n".join(intro_lines) + body
        write_text(target / f"{s['id']}_PROMPT.txt", full)


def copy_references(src_files: list[Path], dst: Path,
                    prefix_offset: int = 1) -> int:
    """Копирует исходники с номерами в имени. Возвращает число файлов."""
    n = 0
    for i, src in enumerate(src_files, start=prefix_offset):
        dst_name = f"{i:02d}_{src.stem}{src.suffix.lower()}"
        # делаем имя безопасным
        dst_name = re.sub(r"[^A-Za-z0-9_.\-]+", "_", dst_name)
        shutil.copy2(src, dst / dst_name)
        n += 1
    return n


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a ready-for-Gemini task folder for Nano Banana Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--type", required=True,
                   choices=["tshirt", "lingerie", "clothing"],
                   help="Тип товара (определяет сценарии и шаблоны)")
    p.add_argument("--slug", required=True,
                   help="Короткое имя задания (для папки), напр. 'givenchy-v3'")
    p.add_argument("--brief", default="",
                   help="Краткое ТЗ. Можно через --brief-file")
    p.add_argument("--brief-file", type=Path, default=None,
                   help="Путь к md/txt файлу с ТЗ")
    p.add_argument("--photos", type=Path, default=None,
                   help="Папка с фото товара (или один файл)")
    p.add_argument("--print", dest="print_file", type=Path, default=None,
                   help="PNG/JPG принта (для футболок)")
    p.add_argument("--references", type=Path, default=None,
                   help="Папка с дополнительными референсами (фон, модель)")
    p.add_argument("--out-root", type=Path, default=None,
                   help="Куда складывать (по умолчанию: stores/<type>s/tasks/)")
    p.add_argument("--copy-to-desktop", action="store_true",
                   help="Дополнительно скопировать в ~/Desktop/Tasks/")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    brief = args.brief
    if args.brief_file:
        if not args.brief_file.exists():
            print(f"ERROR: brief file not found: {args.brief_file}",
                  file=sys.stderr)
            return 1
        brief = args.brief_file.read_text(encoding="utf-8")

    scenarios = SCENARIOS[args.type]
    slug = slugify(args.slug)
    folder_name = f"{now_stamp()}_{slug}"

    out_root = args.out_root or (REPO_ROOT / "stores" / f"{args.type}s" / "tasks")
    task_dir = out_root / folder_name
    ready = task_dir / "READY_FOR_GEMINI"
    outputs = task_dir / "outputs"

    if task_dir.exists():
        print(f"ERROR: task dir already exists: {task_dir}", file=sys.stderr)
        return 1

    task_dir.mkdir(parents=True)
    ready.mkdir()
    outputs.mkdir()
    (outputs / ".gitkeep").touch()

    # Собираем все referenced images по порядку:
    # 1) print (если есть) — для футболок
    # 2) photos
    # 3) built-in balcony template refs for tshirts
    # 4) references
    images: list[Path] = []
    if args.print_file:
        if not args.print_file.exists():
            print(f"WARN: print file not found: {args.print_file}",
                  file=sys.stderr)
        else:
            images.append(args.print_file)
    images.extend(discover_image_files(args.photos))
    if args.type == "tshirt" and BALCONY_TEMPLATE_DIR.exists():
        images.extend(discover_image_files(BALCONY_TEMPLATE_DIR))
    images.extend(discover_image_files(args.references))

    n_copied = copy_references(images, ready, prefix_offset=1)

    make_brief(task_dir, args.type, slug, brief, scenarios)
    make_readme(ready, args.type, scenarios)
    make_step_by_step(ready, scenarios)
    make_known_issues(ready)
    make_prompts(ready, args.type, scenarios, brief, n_copied)

    print(f"OK. Создал: {task_dir}")
    print(f"     ракурсов:    {len(scenarios)}")
    print(f"     референсов:  {n_copied}")
    print(f"     открой:      {ready / 'README.txt'}")

    if args.copy_to_desktop:
        desktop = Path.home() / "Desktop" / "Tasks" / folder_name
        desktop.parent.mkdir(parents=True, exist_ok=True)
        if desktop.exists():
            shutil.rmtree(desktop)
        shutil.copytree(task_dir, desktop)
        print(f"     copied to:   {desktop}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
