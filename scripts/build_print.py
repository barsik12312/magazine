"""build_print.py — собрать ОДИН принт-ассет из N референсов через Nano Banana Pro.

Это отдельный workflow от scripts/build_task.py.

build_task.py — берёт готовые принты (1.jpg / 2.jpg / 3.jpg) и наносит их
на футболку. На входе уже есть готовая графика.

build_print.py — наоборот: берёт N разрозненных референсов (скриншоты с
Pinterest, ч/б эскизы, любые картинки) и говорит Banana собрать из них
ЕДИНЫЙ принт-ассет на нейтральном (чисто-белом) фоне. Готовый принт ты
потом сохраняешь как `1.jpg` / `2.jpg` / `3.jpg` и кидаешь в обычный
build_task для нанесения на футболку.

Базовое использование:
    python scripts/build_print.py \\
        --slug print-back-v1 \\
        --print-kind back \\
        --input "/path/to/folder/with/refs"

В папке должны лежать:
- N image-файлов (любые имена; pin_*, ref_*, 1.jpg, 2.jpg, 3.jpg, и т.д.)
  — это референсы для сборки. Нормализуются в refs/ как ref_01.ext, ref_02.ext, …
- Опционально: коллаж.jpg / эскиз.jpg / sketch.jpg — раскладка/задумка
- Опционально: задание.md — стиль/настроение в свободной форме

На выходе создаётся task-папка вида
    stores/prints/tasks/<timestamp>_<slug>/
        READY_FOR_GEMINI/
            01_PROMPT_COMPOSE_PRINT.txt   ← один промпт для Banana
            refs/
                ref_01.jpg
                ref_02.jpg
                …
                design_sketch.jpg          ← если был
        00_BRIEF.md                        ← аудит для тебя, не для Banana
        outputs/                           ← сюда сохраняй результат
        inputs_snapshot/                   ← копия исходной папки

После генерации сохрани результат как 1.jpg / 2.jpg / 3.jpg (в зависимости
от --print-kind) и кидай в обычный build_task.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
TEXT_EXTS = {".md", ".txt"}
PRINT_KINDS = ("front", "back", "tag")


# ---------- helpers (mirror build_task.py — оставляем независимыми) ----------

def slugify(text: str) -> str:
    text = text.lower().strip()
    cyr = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    lat = ("a b v g d e e zh z i y k l m n o p r s t u f h ts ch sh sch "
           "' y ' e yu ya").split()
    table = dict(zip(cyr, lat))
    text = "".join(table.get(c, c) for c in text)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "print"


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H-%M")


def list_files(folder: Path | None) -> list[Path]:
    if folder is None or not folder.exists():
        return []
    if folder.is_file():
        return [folder]
    return sorted([p for p in folder.iterdir() if p.is_file()])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _has_token(stem: str, *tokens: str) -> bool:
    return any(t in stem for t in tokens)


# ---------- Pinterest URL helper ----------

PINTEREST_HOSTS = ("pinterest.com", "ru.pinterest.com", "pinterest.ru",
                   "i.pinimg.com", "pin.it")


def _is_pinterest_url(url: str) -> bool:
    return any(h in url for h in PINTEREST_HOSTS)


def _extract_pinimg_url_from_html(html: str) -> str | None:
    """Из HTML страницы пина пробуем достать прямой URL на i.pinimg.com.
    Pinterest пишет его в og:image, в JSON-LD, и в data-объекте.
    """
    # og:image — самый стабильный
    m = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # JSON-LD: "contentUrl":"..."
    m = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', html)
    if m:
        return m.group(1).replace("\\u002F", "/")
    # Прямой URL в HTML
    m = re.search(r'https?://i\.pinimg\.com/[^"\'\s]+\.(?:jpg|jpeg|png|webp)',
                  html, re.IGNORECASE)
    if m:
        return m.group(0)
    return None


def _upgrade_pinimg_to_originals(url: str) -> str:
    """Pinterest CDN отдаёт картинки разных размеров через path-сегмент
    (236x, 474x, 564x, 736x, originals). По умолчанию og:image часто
    возвращает 736x или меньше. Подменяем сегмент на /originals/, чтобы
    получить максимальное разрешение.
    """
    if "i.pinimg.com" not in url:
        return url
    # Замена /236x/, /474x/, /564x/, /736x/, /1200x/ → /originals/
    return re.sub(r"i\.pinimg\.com/(?:\d+x\d*|\d+x)/",
                  "i.pinimg.com/originals/", url)


def _fetch_bytes(url: str, ua: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_image_from_url(url: str, target: Path,
                         user_agent: str | None = None) -> bool:
    """Скачивает картинку по URL в target. Если URL — pinterest, парсит
    страницу и достаёт прямой i.pinimg URL, после чего апгрейдит до
    /originals/ для максимального разрешения. Возвращает True/False.
    """
    ua = user_agent or (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    try:
        if _is_pinterest_url(url) and "i.pinimg.com" not in url:
            # шаг 1: тянем HTML страницы пина
            html = _fetch_bytes(url, ua, 15).decode("utf-8", errors="ignore")
            direct = _extract_pinimg_url_from_html(html)
            if not direct:
                print(f"  WARN: не нашёл прямой image URL на странице {url}",
                      file=sys.stderr)
                return False
            url = direct

        # Апгрейд до /originals/ перед скачиванием
        original_url = _upgrade_pinimg_to_originals(url)

        # Пробуем сначала /originals/, при 403/404 откатываемся на og-вариант.
        for attempt_url in (original_url, url) if original_url != url else (url,):
            try:
                data = _fetch_bytes(attempt_url, ua, 30)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                return True
            except urllib.error.HTTPError as e:
                if e.code in (403, 404) and attempt_url != url:
                    continue  # пробуем fallback
                raise
        return False
    except (urllib.error.URLError, urllib.error.HTTPError,
            ConnectionError, TimeoutError) as e:
        print(f"  WARN: не удалось скачать {url}: {e}", file=sys.stderr)
        return False
    except Exception as e:  # noqa: BLE001 — fallback на любую ошибку
        print(f"  WARN: ошибка при скачивании {url}: {e}", file=sys.stderr)
        return False


def download_urls_into_folder(urls_file: Path, dest: Path) -> int:
    """Читает txt-файл (по 1 URL на строку, пустые/# — комментарии) и
    качает каждый URL в dest как pin_NN.<ext>. Возвращает количество
    успешно скачанных.
    """
    lines = urls_file.read_text(encoding="utf-8").splitlines()
    urls: list[str] = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        urls.append(ln)
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    for i, url in enumerate(urls, 1):
        # Угадываем расширение по URL (pinimg обычно .jpg). По умолчанию .jpg.
        ext = ".jpg"
        for cand in (".png", ".webp", ".jpeg", ".jpg"):
            if cand in url.lower():
                ext = cand
                break
        target = dest / f"pin_{i:02d}{ext}"
        if fetch_image_from_url(url, target):
            ok += 1
    return ok


# ---------- input classification ----------

@dataclass
class ComposeClassified:
    brief_text: str = ""
    brief_file: Path | None = None
    refs: list[Path] = field(default_factory=list)
    design_sketch: Path | None = None
    extras: list[Path] = field(default_factory=list)


def classify_compose(folder: Path) -> ComposeClassified:
    """Простой классификатор для print-compose. Все image-файлы — это
    референсы для сборки. Если в имени есть коллаж/эскиз/sketch/mockup —
    это design-sketch (раскладка/задумка), он попадает в свой слот.
    """
    out = ComposeClassified()
    if not folder.exists():
        return out

    for path in list_files(folder):
        ext = path.suffix.lower()
        stem = path.stem.lower()

        # текстовое задание (стиль/настроение)
        if ext in TEXT_EXTS and _has_token(stem, "задание", "brief", "task"):
            out.brief_file = path
            try:
                out.brief_text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                out.brief_text = path.read_text(encoding="cp1251",
                                                 errors="ignore")
            continue

        if ext not in IMAGE_EXTS:
            out.extras.append(path)
            continue

        # design sketch / collage / mockup — разово
        if _has_token(stem, "коллаж", "эскиз", "зарисовк", "sketch",
                      "mockup", "design"):
            if out.design_sketch is None:
                out.design_sketch = path
                continue
            # дополнительные эскизы — в общий пул референсов

        out.refs.append(path)

    return out


def pack_compose_refs(c: ComposeClassified, refs_dir: Path) -> dict[str, list[Path]]:
    """Копирует референсы в refs/ с нормализованными именами:
    ref_01.<ext>, ref_02.<ext>, …, design_sketch.<ext>
    """
    refs_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, list[Path]] = {"ref": [], "design_sketch": []}
    for i, src in enumerate(c.refs, 1):
        if src.suffix.lower() not in IMAGE_EXTS:
            continue
        target = refs_dir / f"ref_{i:02d}{src.suffix.lower()}"
        shutil.copy2(src, target)
        out["ref"].append(target)
    if c.design_sketch is not None:
        target = refs_dir / f"design_sketch{c.design_sketch.suffix.lower()}"
        shutil.copy2(c.design_sketch, target)
        out["design_sketch"].append(target)
    return out


# ---------- prompt templates ----------

COMPOSE_PRINT_BASE = """\
This is a flat-art generation task. The OUTPUT is a single PRINT ASSET — a
piece of artwork that will later be applied as a screen-print onto a
t-shirt in a separate edit-mode pass. Therefore the output must look like
a clean print sheet, NOT like a photo of a t-shirt and NOT like a
lifestyle scene.

WHAT TO GENERATE
- A single composite illustration that reads as ONE coherent print.
- Background: pure white #FFFFFF (or near-white #F8F8F8). Flat. No
  gradient, no vignette, no paper texture, no fabric, no shadow under
  objects, no reflective surface, no environment of any kind. The
  background is the equivalent of a print-sheet — empty.
- No t-shirt, no garment, no model, no body, no hanger, no mannequin,
  no studio lights, no scene props. ONLY the artwork.
- No watermark, no Pinterest UI, no website chrome, no logos belonging
  to source platforms, no mouse cursor.

REFERENCES (attach in this order)
- ref_NN.* — visual references (multiple). For each one: ignore its
  original background completely and isolate ONLY the subject(s) /
  graphic elements. Treat references as a *bank of motifs*, not as
  layered images. The original photographic context, lighting, paper,
  studio backdrop, watermark, text overlay, etc. of each ref must be
  removed.
- design_sketch.* (optional) — a black-and-white collage / sketch by
  the designer showing the rough LAYOUT they want for the final print
  (placement, scale, balance). If present: follow it as the guide for
  WHERE each motif sits within the composition. If absent: arrange
  the motifs into a balanced, visually coherent group on your own.

COMPOSITION RULES
- Combine the isolated motifs from all ref_NN.* into ONE unified piece
  of artwork. Not a grid of separate thumbnails — one composition.
- Maintain consistent rendering style across all motifs (same line
  weight, same level of detail, same colour treatment). If references
  are stylistically inconsistent, harmonise them into a single
  coherent style — do NOT collage clashing styles together.
- Subjects should NOT overlap chaotically. Either stack them in a
  layered tableau, or place them around a central focal element, or
  arrange them in the layout dictated by design_sketch.*.
- Negative space is allowed and encouraged — do not fill the entire
  canvas edge-to-edge. The print should breathe.
- This is the FINAL artwork that will be transferred to fabric — do
  NOT include placeholder elements like "your text here", crop marks,
  bleed lines, registration marks, or designer annotations.

STYLE GUIDANCE
- Read the user's brief (if provided below) for tone / style /
  mood / colour palette / typography. The brief is the source of
  stylistic intent — follow it strictly.
- If no style is specified: render in a clean, contemporary
  screen-print style — solid colours, defined edges, slight
  imperfections allowed (as in real screen-printing), but overall
  graphic and intentional.

DO NOT
- Do NOT generate a photo of a t-shirt with this print on it.
- Do NOT add fabric texture / cotton weave to the print itself
  (that integration happens later in build_task pipeline).
- Do NOT invent a brand / wordmark not requested by the user.
- Do NOT include any source-platform watermark or UI artifact.
- Do NOT preserve the original backgrounds of the references —
  every motif must be isolated cleanly onto the white sheet.
"""

COMPOSE_PRINT_BY_KIND: dict[str, str] = {
    "front": """\

OUTPUT SPEC — FRONT CHEST PRINT
- Aspect ratio: roughly square or vertical 4:5. Will be applied to
  the upper / mid chest area of a t-shirt.
- Target render area: aim for ~2000×2400 px or similar. Hi-res,
  print-quality.
- Scale: the assembled artwork is the kind of size you would expect
  for a chest print — bold and visible from a few meters, but not
  edge-bleeding the t-shirt.
- Centre the composition on its own canvas (the artwork is centred
  on the white sheet; the future apply-step will handle placement
  on the actual chest).
""",
    "back": """\

OUTPUT SPEC — BACK PRINT
- Aspect ratio: roughly square or vertical 4:5 / 3:4. Will be
  applied to the upper / mid back panel of a t-shirt.
- Target render area: ~2000×2400 px or similar. Hi-res.
- Scale: typical back-print size — fills most of the upper back
  area, can be slightly larger than the chest print.
- Centre the composition on its own canvas. Background is pure
  white #FFFFFF — DO NOT include the t-shirt itself.
- For each reference: remove its original background completely.
  Keep ONLY the depicted objects / motifs / characters. The
  user explicitly noted this in the brief: "только предметы,
  фон удалить" — strip backgrounds aggressively.
""",
    "tag": """\

OUTPUT SPEC — INNER NECK-LABEL PRINT (бирка)
- Aspect ratio: small, horizontal banner — roughly 5:2 or 3:1.
  Will sit inside the back-of-neck on the inner surface of the
  collar; visible from the front through the open collar.
- Target render area: ~1600×640 px or similar — readable but
  compact.
- Scale: small printed brand mark / tag-style label. Single
  focused element (not a busy collage). Typography-led if the
  brief mentions a brand name; or a tiny graphic mark.
- Background: pure white #FFFFFF. The label has hard edges and
  no surrounding context.
- Do NOT render this as a photo of a label or a stitched fabric
  tag — this is a flat *printed* graphic that will later be
  silk-screened onto the inner cotton.
""",
}


def build_compose_prompt(kind: str, brief_text: str,
                          placed: dict[str, list[Path]]) -> str:
    """Собирает один промпт-файл: header (FILES TO ATTACH) + technical body."""
    if kind not in COMPOSE_PRINT_BY_KIND:
        raise ValueError(f"unknown print-kind {kind!r}; must be one of "
                         f"{', '.join(COMPOSE_PRINT_BY_KIND)}")

    # FILES TO ATTACH header (минималистичный английский, см. build_task.py)
    header_lines: list[str] = ["FILES TO ATTACH:"]
    n = 0
    for ref in placed.get("ref", []):
        n += 1
        header_lines.append(
            f"{n}) {ref.name} — visual reference (isolate motifs, drop background)"
        )
    for sketch in placed.get("design_sketch", []):
        n += 1
        header_lines.append(
            f"{n}) {sketch.name} — B&W layout sketch (placement guide; do NOT trace pixels)"
        )
    if n == 0:
        header_lines.append("  (no references found — the prompt below will run on style guidance only)")
    header_lines.append("")
    header_lines.append("---")
    header_lines.append("")
    header = "\n".join(header_lines)

    body = COMPOSE_PRINT_BASE + COMPOSE_PRINT_BY_KIND[kind]

    # User brief — добавляем в самый конец промпта как явную секцию,
    # потому что для compose mode стиль ИДЁТ от пользователя (в отличие
    # от build_task где per-frame заметки вообще не идут в Banana —
    # тут стиль это и есть содержание задачи, не frame-конфиг).
    if brief_text and brief_text.strip():
        body += "\n\nUSER BRIEF (highest priority — follow strictly):\n"
        body += brief_text.strip()
        body += "\n"

    return header + body


# ---------- meta files ----------

def make_brief(task_dir: Path, slug: str, kind: str, brief: str,
               classified: ComposeClassified) -> None:
    lines = [
        f"# Print-compose: {slug} ({kind})",
        "",
        f"> Создано {now_stamp()} скриптом `scripts/build_print.py`.",
        "",
        "## Что собираем",
        "",
        f"Один принт-ассет на нейтральном фоне (#FFFFFF). Тип: **{kind}** "
        f"({'грудной' if kind == 'front' else 'back' if kind == 'back' else 'бирка'}).",
        "",
        "## Стиль / brief",
        "",
        brief.strip() if brief else "_(не заполнено)_",
        "",
        "## Найденные исходники",
        "",
        f"- Референсы (ref_NN.*): {len(classified.refs)} файла",
        f"- Design sketch (раскладка): "
        f"{classified.design_sketch.name if classified.design_sketch else '—'}",
        f"- Brief файл: "
        f"{classified.brief_file.name if classified.brief_file else '—'}",
        f"- Extras (не использовано): {len(classified.extras)}",
        "",
        "## Что делать",
        "",
        "1. Открой `READY_FOR_GEMINI/01_PROMPT_COMPOSE_PRINT.txt`.",
        "2. Прикрепи файлы из `refs/` в порядке списка `FILES TO ATTACH:`.",
        "3. Тащи в Nano Banana Pro, генерируй.",
        f"4. Готовый принт сохраняй в `outputs/`. Затем переименуй в "
        f"`{'1' if kind == 'front' else '2' if kind == 'back' else '3'}.jpg` "
        f"и положи в input-папку для основного `build_task.py --type tshirt`.",
        "",
    ]
    write_text(task_dir / "00_BRIEF.md", "\n".join(lines))


def make_readme(target: Path, kind: str) -> None:
    lines = [
        "═" * 71,
        "  ПАКЕТ ДЛЯ NANO BANANA PRO — СБОРКА ОДНОГО ПРИНТА",
        "═" * 71,
        "",
        f"  Тип принта: {kind}",
        "  Промпт: 01_PROMPT_COMPOSE_PRINT.txt",
        "  Фон выходного принта: чисто-белый #FFFFFF (для последующего",
        "  нанесения на ткань через build_task.py)",
        "",
        "  ЧТО ДЕЛАТЬ:",
        "  1) Открой 01_PROMPT_COMPOSE_PRINT.txt",
        "  2) Прикрепи файлы из refs/ в порядке FILES TO ATTACH",
        "  3) Не дополняй промпт от себя — он самодостаточен",
        "  4) Готовый принт сохрани в ../outputs/, потом переименуй",
        f"     в {'1' if kind == 'front' else '2' if kind == 'back' else '3'}.jpg",
        "     и положи в input для build_task.py --type tshirt",
        "",
        "═" * 71,
    ]
    write_text(target / "README.txt", "\n".join(lines))


# ---------- main ----------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a Banana-ready task to compose ONE print "
                    "asset from N references on a neutral background. "
                    "Output of this script feeds into build_task.py "
                    "(its result becomes 1.jpg / 2.jpg / 3.jpg).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--slug", required=True,
                   help="Короткое имя задания (для папки), напр. "
                        "'print-back-v1'.")
    p.add_argument("--print-kind", required=True, choices=PRINT_KINDS,
                   help="Какой принт собираем: front (грудной), back "
                        "(спина), tag (бирка). Влияет на пропорции и "
                        "размер.")
    p.add_argument("--input", dest="input_folder", type=Path, required=True,
                   help="Папка с референсами (image-файлы) + опционально "
                        "коллаж.jpg / эскиз.jpg + задание.md. Если "
                        "передан --urls-file, скрипт сначала закачает "
                        "URL'ы в эту папку.")
    p.add_argument("--urls-file", type=Path, default=None,
                   help="Файл со списком URL (по 1 на строку; пустые "
                        "и # — комментарии). Поддерживает Pinterest "
                        "ссылки — автоматически парсит страницу пина "
                        "и достаёт прямой image URL. Скачанные файлы "
                        "кладутся в --input как pin_01.<ext>, ...")
    p.add_argument("--brief", default="",
                   help="Краткий стиль/настроение принта. Можно через "
                        "--brief-file или через задание.md в input.")
    p.add_argument("--brief-file", type=Path, default=None,
                   help="Путь к md/txt файлу с описанием стиля.")
    p.add_argument("--out-root", type=Path, default=None,
                   help="Куда складывать (по умолчанию: stores/prints/tasks/)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Если передан --urls-file, сначала качаем URLs в input-папку.
    if args.urls_file is not None:
        if not args.urls_file.exists():
            print(f"ERROR: --urls-file {args.urls_file} не найден",
                  file=sys.stderr)
            return 1
        args.input_folder.mkdir(parents=True, exist_ok=True)
        print(f"Скачиваю URL'ы из {args.urls_file} в {args.input_folder} ...")
        ok = download_urls_into_folder(args.urls_file, args.input_folder)
        print(f"  скачано: {ok} файла")
        if ok == 0:
            print("ERROR: ни один URL не удалось скачать. Проверь "
                  "доступ в интернет или скачай картинки вручную.",
                  file=sys.stderr)
            return 1

    # Загрузить input.
    if not args.input_folder.exists():
        print(f"ERROR: input folder {args.input_folder} не найден",
              file=sys.stderr)
        return 1

    c = classify_compose(args.input_folder)

    # Brief может прийти из --brief, --brief-file, или из задания.md в input.
    brief = c.brief_text
    if args.brief_file is not None:
        try:
            brief = args.brief_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            brief = args.brief_file.read_text(encoding="cp1251",
                                               errors="ignore")
    if args.brief:
        brief = (brief + "\n\n" + args.brief).strip() if brief else args.brief

    if not c.refs:
        print(f"ERROR: в папке {args.input_folder} не найдено ни одного "
              f"image-референса. Положи минимум 1 jpg/png.",
              file=sys.stderr)
        return 1

    # Папка задания.
    slug = slugify(args.slug)
    folder_name = f"{now_stamp()}_{slug}"
    out_root = args.out_root or (REPO_ROOT / "stores" / "prints" / "tasks")
    task_dir = out_root / folder_name
    ready = task_dir / "READY_FOR_GEMINI"
    refs = ready / "refs"
    outputs = task_dir / "outputs"
    snapshot = task_dir / "inputs_snapshot"

    if task_dir.exists():
        print(f"ERROR: task dir already exists: {task_dir}",
              file=sys.stderr)
        return 1

    task_dir.mkdir(parents=True)
    ready.mkdir()
    refs.mkdir()
    outputs.mkdir()
    (outputs / ".gitkeep").touch()

    # snapshot входной папки
    snapshot.mkdir()
    for src in list_files(args.input_folder):
        shutil.copy2(src, snapshot / src.name)

    # Положить refs в refs/.
    placed = pack_compose_refs(c, refs)

    # extras копируем отдельно
    if c.extras:
        extras_dir = ready / "extras"
        extras_dir.mkdir(exist_ok=True)
        for src in c.extras:
            shutil.copy2(src, extras_dir / src.name)

    # Промпт.
    prompt_text = build_compose_prompt(args.print_kind, brief, placed)
    write_text(ready / "01_PROMPT_COMPOSE_PRINT.txt", prompt_text)

    # Meta.
    make_brief(task_dir, slug, args.print_kind, brief, c)
    make_readme(ready, args.print_kind)

    print(f"OK. Создал: {task_dir}")
    print(f"     refs:")
    for k, v in placed.items():
        if v:
            print(f"       {k}: {len(v)}")
    if c.extras:
        print(f"     extras (не использовано): {len(c.extras)}")
    print(f"     промпт: {ready / '01_PROMPT_COMPOSE_PRINT.txt'}")
    print(f"     после генерации сохрани результат в:")
    print(f"       {outputs}/")
    target_name = ('1' if args.print_kind == 'front'
                   else '2' if args.print_kind == 'back' else '3')
    print(f"     потом переименуй в {target_name}.jpg и кидай в "
          f"input для build_task.py --type tshirt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
