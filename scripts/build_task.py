#!/usr/bin/env python3
"""
build_task.py — Task Folder Builder for Nano Banana Pro

Принимает папку с исходниками (фотки + принты + опциональный фон + бриф)
и собирает готовый пакет под Nano Banana Pro в Gemini: 5 промптов, чистые
референсы с нормализованными именами, README и known-issues.

Подробнее про конвенцию входной папки — docs/INPUT_FOLDER_CONVENTION.md.

Базовое использование:

    python scripts/build_task.py \
        --type tshirt \
        --slug givenchy-v3 \
        --input inputs/2026-05-04_givenchy/

Дополнительно поддерживается старый вход через --photos / --print /
--references — он остаётся как fallback для уже существующих папок,
но рекомендованный способ — собрать одну входную папку.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = REPO_ROOT / "prompts" / "templates"
BALCONY_TEMPLATE_DIR = REPO_ROOT / "stores" / "tshirts" / "backgrounds" / "balcony_template"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
TEXT_EXTS = {".md", ".txt"}

# Сценарии: какие промпты делаем для каждого типа товара.
SCENARIOS: dict[str, list[dict[str, str]]] = {
    "tshirt": [
        {"id": "01_PROMPT_FRONT", "title": "Футболка спереди на сцене"},
        {"id": "02_PROMPT_BACK", "title": "Футболка сзади на сцене"},
        {"id": "03_PROMPT_TAG", "title": "Бирка крупным планом"},
        {"id": "04_PROMPT_MODEL_FRONT", "title": "Человек спереди (на основе результата шага 1)"},
        {"id": "05_PROMPT_MODEL_BACK", "title": "Человек сзади (на основе результата шага 2)"},
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

TEMPLATE_FILES = {
    "tshirt": "tshirt_hanger.md",
    "lingerie": "lingerie_studio.md",
    "clothing": "clothing_catalog.md",
}


# ---------- helpers ----------

def slugify(text: str) -> str:
    text = text.lower().strip()
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


def list_files(folder: Path | None) -> list[Path]:
    if folder is None or not folder.exists():
        return []
    if folder.is_file():
        return [folder]
    return sorted([p for p in folder.iterdir() if p.is_file()])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------- input classification ----------

@dataclass
class Classified:
    brief_text: str = ""
    brief_file: Path | None = None
    print_front: Path | None = None
    print_back: Path | None = None
    print_tag: Path | None = None
    garment_front: Path | None = None
    garment_back: Path | None = None
    garment_tag: Path | None = None
    model_front: Path | None = None  # фото человека/модели во весь рост спереди (чспереди)
    model_back: Path | None = None   # фото человека/модели во весь рост сзади (чсзади)
    model_head_front: Path | None = None  # лицо/голова спереди — identity-lock для шага 04
    model_head_back: Path | None = None   # затылок/волосы сзади — identity-lock для шага 05
    design_sketch: Path | None = None  # коллаж/эскиз front+back в B&W — design intent reference, НЕ принт-ассет
    backgrounds: list[Path] = field(default_factory=list)
    models: list[Path] = field(default_factory=list)  # общие модель-референсы без явного ракурса
    extras: list[Path] = field(default_factory=list)


def _tokens(stem: str) -> set[str]:
    """Разбивает имя файла на слова. Учитывает кириллицу и латиницу.

    Пример: 'model_back' → {'model', 'back'}, 'фото-модель.front' → {'фото', 'модель', 'front'}.
    """
    return {t for t in re.split(r"[^a-zа-я0-9]+", stem) if t}


def _has_token(stem: str, *tokens: str) -> bool:
    """Проверяет, есть ли в имени файла хотя бы один из перечисленных токенов.

    Совпадение засчитывается, если файл-токен:
      - в точности равен искомому, либо
      - начинается с искомого (для русских корней типа 'модел' → 'модель/модели').
    """
    file_tokens = _tokens(stem)
    for t in tokens:
        t = t.lower()
        for ft in file_tokens:
            if ft == t or ft.startswith(t):
                return True
    return False


def _matches(name: str, *patterns: str) -> bool:
    return any(re.search(p, name) for p in patterns)


def classify_inputs(folder: Path) -> Classified:
    """Разбирает входную папку по категориям на основе имён файлов.

    Конвенция описана в docs/INPUT_FOLDER_CONVENTION.md.
    """
    out = Classified()
    if not folder.exists():
        return out

    for path in list_files(folder):
        ext = path.suffix.lower()
        stem = path.stem.lower()
        tokens = _tokens(stem)

        # текстовое задание
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

        # 1) ГОЛОВА / ЛИЦО модели — identity-lock для шагов 04/05.
        # Проверяем РАНЬШЕ всех остальных правил, чтобы "голова_спереди" не уходило
        # в garment_front из-за токена "спереди".
        if _has_token(stem, "голов", "head", "face", "лицо"):
            has_front = ("front" in tokens or _has_token(stem, "спереди")
                         or stem.startswith("face"))
            has_back = "back" in tokens or _has_token(stem, "сзади")
            if has_front and not has_back:
                if out.model_head_front is None:
                    out.model_head_front = path
                    continue
            if has_back and not has_front:
                if out.model_head_back is None:
                    out.model_head_back = path
                    continue
            # направление не явное — кладём в model_head_front (дефолт)
            if out.model_head_front is None:
                out.model_head_front = path
                continue
            if out.model_head_back is None:
                out.model_head_back = path
                continue
            out.extras.append(path)
            continue

        # 2) ТЕЛО ЧЕЛОВЕКА с явным ракурсом (чспереди / чсзади / model_front и т.п.).
        # Берём раньше garment-back/front, чтобы эти файлы не уходили в garment.
        is_human_explicit = (
            stem.startswith("чспереди") or stem.startswith("чсзади")
            or _has_token(stem, "чел")
        )
        is_model_word = _has_token(stem, "model", "модел", "pose", "поза")
        if is_human_explicit or is_model_word:
            has_front = (stem.startswith("чспереди") or "front" in tokens
                         or _has_token(stem, "спереди"))
            has_back = (stem.startswith("чсзади") or "back" in tokens
                        or _has_token(stem, "сзади"))
            if has_front and not has_back:
                if out.model_front is None:
                    out.model_front = path
                    continue
            if has_back and not has_front:
                if out.model_back is None:
                    out.model_back = path
                    continue
            out.models.append(path)
            continue

        # 3) DESIGN SKETCH — чёрно-белый коллаж front+back от дизайнера.
        # Это design-intent reference, НЕ принт. Берём ДО garment-front/back,
        # чтобы "коллаж_спереди" не утекало в garment_front.
        if _has_token(stem, "коллаж", "эскиз", "зарисовк", "sketch", "mockup",
                      "design"):
            if out.design_sketch is None:
                out.design_sketch = path
            else:
                out.extras.append(path)
            continue

        # фоны (раньше garment-back, чтобы "background_back" не уходило в garment_back)
        if _has_token(stem, "background", "bg", "scene", "фон", "балкон"):
            out.backgrounds.append(path)
            continue

        # принты по словам "print*"/"принт*"
        is_print_word = _has_token(stem, "print", "принт")
        if is_print_word:
            if "front" in tokens or _has_token(stem, "спереди"):
                if out.print_front is None:
                    out.print_front = path
                    continue
            if "back" in tokens or _has_token(stem, "сзади"):
                if out.print_back is None:
                    out.print_back = path
                    continue
            if "tag" in tokens or _has_token(stem, "бирк", "label"):
                if out.print_tag is None:
                    out.print_tag = path
                    continue
            if "1" in tokens and out.print_front is None:
                out.print_front = path
                continue
            if "2" in tokens and out.print_back is None:
                out.print_back = path
                continue
            if "3" in tokens and out.print_tag is None:
                out.print_tag = path
                continue

        # принты по чистым цифрам (1.png, 2.jpg, 3.png)
        if tokens == {"1"} and out.print_front is None:
            out.print_front = path
            continue
        if tokens == {"2"} and out.print_back is None:
            out.print_back = path
            continue
        if tokens == {"3"} and out.print_tag is None:
            out.print_tag = path
            continue

        # реальные фото товара
        if "front" in tokens or _has_token(stem, "спереди"):
            if out.garment_front is None:
                out.garment_front = path
                continue
        if "back" in tokens or _has_token(stem, "сзади"):
            if out.garment_back is None:
                out.garment_back = path
                continue
        if ("tag" in tokens or "label" in tokens
                or _has_token(stem, "бирк")):
            if out.garment_tag is None:
                out.garment_tag = path
                continue

        out.extras.append(path)

    return out


# ---------- pack copy ----------

def safe_copy(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def pack_refs(c: Classified, refs_dir: Path, ttype: str) -> dict[str, list[Path]]:
    """Копирует исходники в refs/ с нормализованными именами.

    Возвращает словарь категория → список итоговых путей в refs/.
    """
    refs_dir.mkdir(parents=True, exist_ok=True)
    placed: dict[str, list[Path]] = {
        "print_front": [],
        "print_back": [],
        "print_tag": [],
        "garment_front": [],
        "garment_back": [],
        "garment_tag": [],
        "model_front": [],
        "model_back": [],
        "model_head_front": [],
        "model_head_back": [],
        "design_sketch": [],
        "scene": [],
        "model": [],
    }

    def put(src: Path | None, name: str, key: str) -> None:
        if src is None:
            return
        target = refs_dir / f"{name}{src.suffix.lower()}"
        safe_copy(src, target)
        placed[key].append(target)

    put(c.print_front, "print_1_front", "print_front")
    put(c.print_back, "print_2_back", "print_back")
    put(c.print_tag, "print_3_tag", "print_tag")
    put(c.garment_front, "garment_front", "garment_front")
    put(c.garment_back, "garment_back", "garment_back")
    put(c.garment_tag, "garment_tag", "garment_tag")
    put(c.model_front, "model_front", "model_front")
    put(c.model_back, "model_back", "model_back")
    put(c.model_head_front, "model_head_front", "model_head_front")
    put(c.model_head_back, "model_head_back", "model_head_back")
    put(c.design_sketch, "design_sketch", "design_sketch")

    # сцена: либо переданные backgrounds, либо балкон-дефолт для футболок
    scenes = c.backgrounds[:]
    if not scenes and ttype == "tshirt" and BALCONY_TEMPLATE_DIR.exists():
        scenes = list_files(BALCONY_TEMPLATE_DIR)
    for i, src in enumerate(scenes, 1):
        if src.suffix.lower() not in IMAGE_EXTS:
            continue
        target = refs_dir / f"scene_{i:02d}{src.suffix.lower()}"
        safe_copy(src, target)
        placed["scene"].append(target)

    for i, src in enumerate(c.models, 1):
        if src.suffix.lower() not in IMAGE_EXTS:
            continue
        target = refs_dir / f"model_{i:02d}{src.suffix.lower()}"
        safe_copy(src, target)
        placed["model"].append(target)

    return placed


# ---------- prompts ----------

TSHIRT_PROMPTS: dict[str, str] = {
    "01_PROMPT_FRONT": """\
This is a single-pass photorealistic IMAGE EDIT.

BASE IMAGE (do not re-synthesize the scene): garment_front.*
Treat garment_front.* as the canvas. Keep the entire image intact except for TWO printed regions:
  (A) the MAIN CHEST PRINT — the larger graphic on the OUTER FRONT of the shirt, centered on the chest.
  (B) the small NECK-LABEL PRINT on the INSIDE of the back of the neckline — what the user calls "бирка". It is a small printed brand label on the INNER (wrong-side) surface of the back of the neckband. Even though it is on the inside, it IS visible in this front-on hanger photo because the open V/round of the collar reveals the inside of the back-of-neck strip just above the front collar. Look at garment_front.* — the existing red/colored small print visible inside the collar opening, just above the front hem of the ribbed neckband, IS the "бирка".

Everything else — the t-shirt silhouette, the fabric folds, the hanger, the wall, the window, the balcony, the lighting, the colors, the perspective, the framing, the depth of field — must be preserved 1:1 from garment_front.*. Do not regenerate the scene from scratch. Do not invent new objects. Do not stylize. Do not crop differently.

REFERENCE IMAGES (attach in this order):
- garment_front.*  ← BASE / canvas (the front-on hanger photo of the existing t-shirt)
- print_1_front.*  ← new MAIN chest print (finished graphic asset, larger size, centered on the chest)
- print_3_tag.*    ← new neck-label print to apply on the inner back-of-neckline (finished graphic asset, small)
- garment_tag.*    ← optional close-up reference of the existing inner neck-label area
- scene_*.*        ← detail-memory references of the real balcony scene; use only as visual memory so background details are not invented if any tiny gap appears around the modified regions
- design_sketch.*  ← OPTIONAL black-and-white front+back collage / sketch from the designer. This is a DESIGN-INTENT REFERENCE ONLY. It is NOT a print asset and NOT a canvas. Do NOT extract pixels from it. Do NOT apply it to the shirt. Do NOT trace it. The actual finished print artwork lives in print_1_front.* / print_2_back.* / print_3_tag.* — those are the only sources of printed graphics. The sketch only shows the rough vision of how the finished t-shirt should "feel" overall (silhouette, balance of front and back graphics). The "бирка" / neck-label print is NEVER drawn on the sketch — its absence on the sketch must NOT be interpreted as "no neck-label"; the neck-label rule still comes from print_3_tag.* and garment_front.*.

OBJECTIVE — DO ALL IN ONE PASS:
1. Erase the existing MAIN CHEST PRINT on the OUTER FRONT of the t-shirt in garment_front.* completely. Reconstruct clean cotton fabric in that area, preserving folds, light, and shadow as in the rest of the shirt.
2. Erase the existing NECK-LABEL PRINT on the INNER (wrong-side) surface of the back of the neckline — the small printed graphic visible inside the collar opening. Reconstruct clean cotton fabric of the inner neckband there.
3. Apply print_1_front.* onto the chest as the main print. Size and placement: same scale and position as the original main chest print in garment_front.* (large, centered, around mid-chest height). Treat as a matte screen-print transfer. Preserve every glyph, line, decoration, strike-through, and proportion of print_1_front.* — do not re-typeset, do not redesign, do not respell.
4. Apply print_3_tag.* onto the INNER (wrong-side) surface of the back of the neckline, in the same small size and same position as the original neck-label print in garment_front.* (i.e. visible inside the collar opening, sitting on the inner neckband / inside back-of-neck panel just above the front hem of the ribbed collar). It is a small printed graphic, visibly smaller than the main chest print. Preserve every glyph and proportion of print_3_tag.* exactly. If print_3_tag.* is not provided, leave that area as clean inner-cotton with no invented brand text.
5. Both prints must coexist on the same front view: the small neck-label print visible inside the collar opening AND the main chest print centered on the chest. Both look like real screen-print on cotton.

PRINT BEHAVIOUR:
- Treat print_1_front.* and print_3_tag.* as TWO completely independent finished graphic design assets.
- print_1_front.* lives ONLY on the OUTER chest area, inside its own bounding box. It does NOT touch the collar, the neckband, the inside of the neckline, or any other region. Glyphs from print_3_tag.* must NEVER appear inside the chest print region.
- print_3_tag.* lives ONLY on the INNER (wrong-side) surface of the back of the neckline, visible through the collar opening. Its size is small — it must be visibly smaller than the main chest print and contained inside the collar opening area, not overlapping the chest at all.
- Do NOT merge, fuse, overlay, or substitute glyphs from print_3_tag.* into print_1_front.* (e.g. do NOT replace the letter "C" of FUCKS with the CHANEL CC logo, etc.). The two prints are different physical objects on different parts of the garment and must not visually mix.
- Do not re-render either as text from scratch.

FABRIC INTEGRATION (CRITICAL — do not skip; this is what separates a real screen-print from a Photoshop sticker):
- The print must look APPLIED INTO the cotton, not laid on top. Visible cotton weave / microtexture must show THROUGH the dark areas of the print, the way real screen-print ink absorbs slightly into cotton fibers (minor desaturation in fiber valleys, tiny variation in opacity along the fabric grain).
- Edges of the print must follow the EXACT same micro-creases and folds of the cotton as the surrounding shirt area. If the fabric has a wrinkle or fold under the print, the print bends along that wrinkle (slight curvature, slight tonal shift, tiny break in coverage where the fold is sharpest). It is NOT flat. It is NOT rectangular. It is NOT shifted as a block on top of the shirt.
- Lighting on the print must match the lighting on the shirt around it pixel-for-pixel: the same highlight side, the same shadow side, the same falloff. If part of the chest is in shade in garment_front.*, the print over that part is also slightly darker. If part is in highlight, the print there has slightly brighter ink response.
- Colour rendering: matte screen-print on cotton — no glossy sticker sheen, no halo, no bevel, no embossed plastic effect, no decal sheen, no white outline, no rectangular box around the artwork. The ink reads as cotton-printed, not as vinyl heat-transfer or photoshop overlay.
- Reference for the EXACT material look you should reproduce: imagine the close-up macro of a printed neck-label on cotton (the kind step 03 produces) — visible weave under the ink, slight ink-bleed into fibers, no separated layer. Apply that same material quality to the main chest print at chest-print scale.
- Do NOT add any drop shadow, no glow, no outer rim, no extra contrast around the artwork.

LOCKED ELEMENTS FROM garment_front.* (DO NOT CHANGE):
- t-shirt silhouette and fit
- collar shape, ribbed neckband, sleeve and hem stitching
- exact fabric color and tone (outer AND inner)
- drape, wrinkles, folds, shadows
- hanger position, hanger type, hanger color
- background scene (balcony, window, balcony floor, radiator, ladder, plant, curtain, desk edge, windowsill objects, reflections)
- camera angle, framing, crop, aspect ratio
- lighting direction, exposure, white balance, ambient light

SCENE / BALCONY DETAIL MEMORY:
scene_*.* references exist only so the model has clean memory of how the balcony looks. Do NOT swap garment_front.*'s scene for scene_*.*. The base scene comes from garment_front.* and must remain identical. Use scene_*.* only as fallback memory when reconstructing tiny background pixels that may need to be inferred where the old print previously covered the shirt — and even then, only if the affected pixels are part of the background (e.g. shirt-edge regions). Otherwise scene_*.* is reference, not source.

NEGATIVE / DO NOT INCLUDE:
- do not regenerate the background from scratch
- do not crop differently
- do not change the t-shirt color
- do not change print artwork meaning, glyphs, or layout
- do not invent new logos or extra text anywhere
- do NOT place the neck-label print on the OUTER FRONT of the shirt (it lives on the INNER surface of the back of the neckline, visible only through the collar opening)
- do NOT place a second print on the upper chest below the collar — there is no "small chest print under the collar"; the small print is the inner neck-label visible through the open collar
- do not add a model, mannequin, hands, or arms
- no AI artifacts, melted letters, warped fabric edges, random decor additions
- no watermarks, signatures, UI overlays

OUTPUT:
One single photorealistic image in the same aspect ratio and framing as garment_front.*. The main chest print AND the small inner neck-label print (visible through the collar opening) are both replaced; everything else is preserved 1:1.
""",
    "02_PROMPT_BACK": """\
This is a single-pass photorealistic IMAGE EDIT.

BASE IMAGE (do not re-synthesize the scene): garment_back.*
Treat garment_back.* as the canvas. Keep everything intact except for ONE region: the main back print on the OUTER back of the t-shirt. Important: the user's neck-label "бирка" is a print on the INNER (wrong-side) surface of the back of the neckline — i.e. on the inside. From this OUTER back-on hanger view it is NOT visible (the outer back of the neckband is just plain cotton). Do not try to add, invent, or migrate any neck-label artwork to the outer back of the shirt.

REFERENCE IMAGES (attach in this order):
- garment_back.*   ← BASE / canvas
- print_2_back.*   ← new back print (finished graphic asset)
- garment_tag.*    ← optional reference for fabric / collar close-up
- scene_*.*        ← detail-memory references of the balcony scene (memory only, not a scene donor)
- design_sketch.*  ← OPTIONAL black-and-white front+back collage / sketch from the designer. DESIGN-INTENT REFERENCE ONLY. Do NOT extract pixels from it. Do NOT apply it to the shirt. The real back print is print_2_back.* — that is the only source of printed graphics. The sketch only shows rough overall vision. The neck-label "бирка" is never drawn on the sketch and is also not visible on the OUTER back of the shirt anyway.

OBJECTIVE — DO ALL IN ONE PASS:
1. Erase the existing back artwork on the OUTER back of the t-shirt in garment_back.* completely. Reconstruct clean cotton fabric there with the same folds, light, and shadow as the rest of the shirt.
2. Apply print_2_back.* onto the upper back / centered placement area, faithfully, as a matte screen-print transfer. Same scale and position as the original back print in garment_back.*. Preserve every detail of the artwork.
3. Do not show any neck-label print on the outer back of the neckline. The "бирка" is on the INNER surface of the back of the neckline and is invisible from this outer back view. The outer back of the neckband should be plain cotton (or the same neckline detail as in garment_back.* — no invented logos, no extra graphics).

PRINT BEHAVIOUR:
- print_2_back.* is a finished graphic design asset, not text to be re-rendered.
- Preserve composition, glyph shapes, internal structure, line counts, and lower elements exactly.

FABRIC INTEGRATION (CRITICAL — do not skip; this is what separates a real screen-print from a Photoshop sticker):
- The print must look APPLIED INTO the cotton, not laid on top. Visible cotton weave / microtexture must show THROUGH the dark areas of the print, the way real screen-print ink absorbs slightly into cotton fibers (minor desaturation in fiber valleys, tiny variation in opacity along the fabric grain).
- Edges of the print must follow the EXACT same micro-creases and folds of the cotton as the surrounding shirt area. If the fabric has a wrinkle or fold under the print, the print bends along that wrinkle (slight curvature, slight tonal shift, tiny break in coverage where the fold is sharpest). It is NOT flat. It is NOT rectangular. It is NOT shifted as a block on top of the shirt.
- Lighting on the print must match the lighting on the shirt around it pixel-for-pixel: the same highlight side, the same shadow side, the same falloff. If part of the back is in shade in garment_back.*, the print over that part is also slightly darker. If part is in highlight, the print there has slightly brighter ink response.
- Colour rendering: matte screen-print on cotton — no glossy sticker sheen, no halo, no bevel, no embossed plastic effect, no decal sheen, no white outline, no rectangular box around the artwork. The ink reads as cotton-printed, not as vinyl heat-transfer or photoshop overlay.
- Reference for the EXACT material look you should reproduce: imagine the close-up macro of a printed neck-label on cotton (the kind step 03 produces) — visible weave under the ink, slight ink-bleed into fibers, no separated layer. Apply that same material quality to the back print at back-print scale.
- Do NOT add any drop shadow, no glow, no outer rim, no extra contrast around the artwork.

LOCKED ELEMENTS FROM garment_back.* (DO NOT CHANGE):
- t-shirt silhouette and fit
- collar shape, ribbed neckband, sleeves, hem
- exact fabric color
- drape, wrinkles, folds, shadows
- hanger position, type, color
- background scene (balcony, window, floor, radiator, ladder, plant, curtain, desk edge, windowsill, reflections)
- camera angle, framing, crop, aspect ratio
- lighting and white balance

SCENE / BALCONY DETAIL MEMORY:
scene_*.* references are visual memory only. Do not swap the base scene for scene_*.*. The scene comes from garment_back.* and must remain identical.

NEGATIVE / DO NOT INCLUDE:
- do not regenerate the background
- do not crop differently
- do not change the t-shirt color or shape
- do not change print artwork meaning or glyphs
- do NOT add any neck-label print on the OUTER back of the neckband — the "бирка" lives on the INNER surface and is not visible from outside on the back
- do NOT migrate the inner neck-label print to the outside of the shirt
- no model, mannequin, hands
- no AI artifacts, melted letters, warped fabric, random decor additions
- no watermarks, no UI overlays

OUTPUT:
One photorealistic image in the same aspect ratio and framing as garment_back.*. Back print replaced; everything else preserved 1:1; no neck-label print visible on the outer back.
""",
    "03_PROMPT_TAG": """\
This is a photorealistic close-up shot of the small NECK-LABEL PRINT ("бирка") on the INNER (wrong-side) surface of the back of the t-shirt's neckline.

This is the printed brand label that lives on the INSIDE of the back of the neckband. From a normal front-on hanger view it peeks through the open collar (visible inside the collar opening, just above the front hem of the ribbed neckband). From a normal outer-back view it is hidden behind the cotton. This step's job is a clean macro of that inner label, with the new artwork applied.

This prompt is ONLY needed if print_3_tag.* is part of the task. If it is not provided, skip this step entirely.

BASE IMAGE: garment_tag.* if available; otherwise garment_front.* (the existing label is visible inside the collar opening of the front hanger view) or garment_back.* (a flipped/peeled view of the inner back-of-neck if available).

REFERENCE IMAGES (attach in this order):
- garment_tag.*    ← BASE / canvas if a dedicated label close-up exists
- garment_front.*  ← fallback BASE if garment_tag.* is missing — the inner label visible through the collar opening will be the reference area
- print_3_tag.*    ← new neck-label print (finished graphic asset)
- result_front.*   ← optional: if step 01 is already done, use it as additional fidelity reinforcement

OBJECTIVE — DO ALL IN ONE PASS:
1. Erase the existing neck-label print on the INNER surface of the back of the neckline completely. Reconstruct clean inner cotton fabric there with the same folds, light, and shadow as the surrounding inner-neckband area.
2. Apply print_3_tag.* in the same small size and same position as the original inner neck-label, sitting on the inner back-of-neck panel. Preserve every glyph, line, and decoration from print_3_tag.* exactly.
3. Frame the camera as a tight close-up around the back-of-neck inner label area so the new print fills most of the frame and is clearly readable. The shot must read clearly as an INNER neck-label, not an outer chest print: surrounding the print you should see the inner side of the ribbed neckband and a hint of the inside cotton of the back panel.
4. Keep the surrounding ribbed collar, cotton fabric, lighting, perspective, and color natural and consistent with the rest of the shirt.

PRINT BEHAVIOUR:
- Treat print_3_tag.* as a finished graphic design asset.
- Matte screen-print look on cotton — no glossy sticker, no halo, no bevel, no embossed plastic effect, no decal sheen.
- Allow only natural cotton fabric distortion (slight curving with folds).
- The print must look like ink bonded to the inside of the cotton, not a sticker on top.

LOCKED ELEMENTS (DO NOT CHANGE):
- ribbed collar texture, cotton jersey texture
- t-shirt color and fabric tone (outer AND inner)
- lighting direction and exposure
- white balance and color temperature
- depth of field and focus point

NEGATIVE / DO NOT INCLUDE:
- do NOT render this as a sewn-in woven fabric label — it is a PRINT on the INSIDE of the cotton, not a separate stitched-on tag
- do NOT place this print on the outer chest — that is the main chest print, not the бирка
- do NOT place this print on the OUTER back of the neckband — it lives on the INNER surface
- no unrelated extra text blocks
- no invented brand names beyond what is in print_3_tag.*
- no glossy editorial light
- no stains, no heavy wear, no fake distress
- no AI artifacts, no warped letters, no melted edges
- no watermarks, no UI overlays

OUTPUT:
One photorealistic close-up of the inner neck-label print, with print_3_tag.* faithfully applied to the inside surface of the back of the neckline, and the surrounding fabric, collar, and lighting preserved.
""",
    "04_PROMPT_MODEL_FRONT": """\
This is a photorealistic catalog photo of a model wearing the t-shirt produced in step 01.

REFERENCE IMAGES (attach in this order):
- result_front.*       ← the FINAL output of step 01 (REQUIRED — this is the primary GARMENT source of truth)
- model_head_front.*   ← face / head identity-lock for the model (REQUIRED if provided in the task; this is the EXACT face the model must have)
- model_front.*        ← full-body front-view pose / styling reference for the model (optional)
- print_1_front.*      ← chest print (finished graphic asset, fidelity reinforcement)
- model_*.*            ← generic model reference if no model_front.* / model_head_front.* (optional fallback)

OBJECTIVE:
Create a clean on-model front view that feels like the exact same physical t-shirt from result_front.*, now worn by a young male model. The chest print is the hero. The inner neck-label print ("бирка") is on the INSIDE of the back of the neckline — when the shirt is worn by a person, the model's neck blocks the collar opening so the inner label is NOT visible from a front-on shot. Do not try to surface it on the outer chest.

MODEL IDENTITY (HIGH PRIORITY):
- If model_head_front.* is provided: the model's FACE / HEAD must match model_head_front.* exactly — same facial structure, same skin tone, same eye colour, same eyebrow shape, same nose, same mouth, same hair style/colour/length, same hairline. Do NOT generate a different face. The viewer must recognize this as the same person across shots.
- If model_front.* is provided: follow its full-body pose family, body proportions, build, styling, framing, and crop logic. Body identity must match.
- If neither is provided, fall back to: young man, early 20s, slim athletic build, dark hair, natural proportions, neutral expression, no celebrity look, no heavy glamour. Face should not dominate the frame; chest area is hero.

GARMENT CONTINUITY (ABSOLUTE PRIORITY):
result_front.* is the source of truth for the garment.
Preserve from result_front.*: same color tone, same oversized fit, same collar shape, same ribbed neckband, same fabric weight, same drape quality, same chest print size and placement, same under-collar tag print (if present in result_front.*), same overall garment identity.
This must feel like the exact same t-shirt — not a reimagined version, not a different cut, not a different print.

CHEST PRINT / GRAPHIC FIDELITY:
The chest print must match result_front.* and print_1_front.* exactly.
Do not re-render any letters or shapes. Allow only natural body curvature and fabric tension distortion.

FABRIC INTEGRATION (CRITICAL — print must look INTO the cotton, not on top):
- The chest print must look APPLIED INTO the cotton, not laid as a sticker. Visible cotton weave / microtexture must show THROUGH the dark areas of the print, like real screen-print ink absorbing slightly into cotton fibers.
- The print must follow the body curvature: across the chest the print bends slightly with the pectoral curve, with the rib cage, with any fold from the model's pose. It is NOT flat. It is NOT rectangular. It does NOT shift as a block when the body moves.
- Lighting on the print matches the lighting on the shirt around it: same highlight side, same shadow side, same falloff. If part of the chest is in shade, the print over that part is also slightly darker. Same for highlights.
- Matte screen-print on cotton — no glossy sticker sheen, no halo, no bevel, no embossed plastic effect, no decal sheen, no white outline, no rectangular box around the artwork. The ink reads as cotton-printed, not as vinyl heat-transfer or photoshop overlay.

INNER NECK-LABEL PRINT (бирка):
The "бирка" lives on the INSIDE surface of the back of the neckline of the shirt in result_front.*. When worn by a model in a normal front-on pose, the model's neck and the front of the collar fully cover the collar opening, so the inner label is NOT visible from the camera. Do NOT add the бирка to the upper chest. Do NOT add it on top of the collar. Do NOT place a second small print near the neckline on the outer front. Just leave the upper chest / collar area clean and natural — print_3_tag.* should NOT appear in this shot.

STYLING:
- light blue relaxed jeans (or jeans matching model_*.* if provided)
- simple clean footwear if visible
- minimal styling, no random accessories

BACKGROUND:
- clean neutral catalog-style backdrop by default
- if scene_*.* or any custom background is provided in the task, treat it as locked and reproduce it faithfully

LIGHTING:
- soft clean commercial light
- realistic skin and fabric rendering
- no glossy fashion-magazine lighting

CAMERA / LOOK:
- 4:5 vertical
- realistic catalog framing
- chest area and front print clearly readable
- natural proportions
- realistic cotton texture

NEGATIVE / DO NOT INCLUDE:
- do not change the front print artwork
- do not change print placement
- do not change the garment shape from result_front.*
- do NOT surface the inner neck-label (бирка) onto the outer chest, collar, or shoulders — it lives inside the back of the neckline and is hidden by the model's neck in this view
- no jewelry, watches, hats, or sunglasses
- no anatomy errors, no extra fingers, no melted hair
- no UI overlays, no watermarks

OUTPUT:
One photorealistic 4:5 front-view on-model catalog image. The garment matches result_front.* exactly; only the model and pose are added; no neck-label print visible on the outer front.
""",
    "05_PROMPT_MODEL_BACK": """\
This is a photorealistic catalog photo of the same model wearing the t-shirt produced in step 02, viewed from the back.

REFERENCE IMAGES (attach in this order):
- result_back.*       ← the FINAL output of step 02 (REQUIRED — primary GARMENT source of truth)
- model_head_back.*   ← head / hair identity-lock from behind (REQUIRED if provided; this is the EXACT back of the head the model must have)
- model_back.*        ← full-body back-view pose / styling reference (optional)
- model_head_front.*  ← fidelity reinforcement so the same person identity is preserved across front/back shots (optional)
- print_2_back.*      ← back print (finished graphic asset, fidelity reinforcement)
- model_*.*           ← generic model reference if no model_back.* (optional fallback)

OBJECTIVE:
Back-view on-model companion image for the same t-shirt series. Must preserve the same garment identity, same fit family, and same back artwork as result_back.*.

MODEL IDENTITY (HIGH PRIORITY):
- If model_head_back.* is provided: the back of the head must match model_head_back.* exactly — same hair length, same hair colour, same hair texture, same hairline shape, same nape area, same neck thickness. Do NOT generate a different person's hair / head from behind.
- If model_back.* is provided: follow its full-body back-view pose, build, styling, framing, and crop logic.
- If model_head_front.* is provided as well: use it as a cross-reference so the back-of-head matches the SAME person as in step 04 — hair colour and length, skin tone of the neck, body build must be consistent.
- If neither head nor body reference is provided, fall back to: same young man as step 04 — slim athletic build, dark hair, natural proportions. Back view only, face not shown.

GARMENT CONTINUITY (ABSOLUTE PRIORITY):
result_back.* is the source of truth for the garment.
Preserve: same color tone, same oversized cut, same collar and shoulder proportions, same fabric behavior, same drape quality, same overall shape, same back print size and placement.

BACK PRINT / GRAPHIC FIDELITY:
The back print must match result_back.* and print_2_back.* exactly. Do not redesign, simplify, move, or add extra text. Allow only natural body / fabric-following distortion.

FABRIC INTEGRATION (CRITICAL — print must look INTO the cotton, not on top):
- The back print must look APPLIED INTO the cotton, not laid as a sticker. Visible cotton weave / microtexture must show THROUGH the dark areas of the print, like real screen-print ink absorbing slightly into cotton fibers.
- The print must follow the body curvature: across the back the print bends slightly with the shoulder blades, spine curve, any fold from the model's pose. It is NOT flat. It is NOT rectangular. It does NOT shift as a block.
- Lighting on the print matches the lighting on the shirt around it: same highlight side, same shadow side, same falloff. If part of the back is in shade, the print over that part is also slightly darker. Same for highlights.
- Matte screen-print on cotton — no glossy sticker sheen, no halo, no bevel, no embossed plastic effect, no decal sheen, no white outline, no rectangular box around the artwork. The ink reads as cotton-printed, not as vinyl heat-transfer or photoshop overlay.

INNER NECK-LABEL PRINT (бирка):
The "бирка" lives on the INNER (wrong-side) surface of the back of the neckline of the shirt and is therefore invisible from any outer back view. On a model viewed from behind, the model's hair / neck / hairline additionally covers the back of the neckband. Do NOT invent any logo or text on the OUTER back of the neckband. The outer back-of-neck area should be plain cotton, like in result_back.*.

STYLING:
- same jeans logic as the front on-model shot
- minimal catalog styling, no random accessories

BACKGROUND:
- clean neutral catalog-style backdrop by default
- if scene_*.* or any custom background is provided, treat it as locked

LIGHTING:
- soft clean commercial light
- realistic fabric rendering
- no glossy editorial exaggeration

CAMERA / LOOK:
- 4:5 vertical
- back print clearly readable
- natural catalog framing
- realistic cotton texture and fold behavior

NEGATIVE / DO NOT INCLUDE:
- do not change the back print
- do NOT add any neck-label print on the OUTER back of the neckband — the бирка is on the INSIDE and is not visible from outside on the back
- do not change the garment silhouette from result_back.*
- no props or other people
- do not show the face
- no anatomy errors, no extra fingers, no melted edges
- no UI overlays, no watermarks

OUTPUT:
One photorealistic 4:5 back-view on-model catalog image. The garment matches result_back.* exactly; only the model and pose are added; no neck-label print visible on the outer back.
""",
}


def make_tshirt_prompts(target: Path, has_tag: bool = True) -> int:
    """Записывает промпты в target. Если has_tag=False, пропускает 03_PROMPT_TAG.
    Возвращает число записанных файлов.
    """
    written = 0
    for sid, body in TSHIRT_PROMPTS.items():
        if not has_tag and sid == "03_PROMPT_TAG":
            continue
        write_text(target / f"{sid}.txt", body)
        written += 1
    return written


# generic fallback for non-tshirt types — берём всё из шаблона
def make_generic_prompts(target: Path, ttype: str,
                         scenarios: list[dict[str, str]]) -> None:
    template_file = PROMPTS_DIR / TEMPLATE_FILES[ttype]
    template_text = ""
    if template_file.exists():
        template_text = template_file.read_text(encoding="utf-8")
    for s in scenarios:
        body = template_text or f"[Не найден шаблон {template_file}]"
        write_text(target / f"{s['id']}.txt", body)


# ---------- meta files ----------

def make_brief(task_dir: Path, ttype: str, slug: str, brief: str,
               scenarios: list[dict[str, str]],
               classified: Classified, has_custom_scene: bool) -> None:
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
        "| № | ID | Описание |",
        "|---|-----|----------|",
    ]
    for s in scenarios:
        num = s['id'].split('_')[0] if s['id'][:2].isdigit() else "—"
        lines.append(f"| {num} | {s['id']} | {s['title']} |")
    lines += [
        "",
        "## Исходники, которые скрипт нашёл",
        "",
        f"- print_1 (front): {classified.print_front.name if classified.print_front else '—'}",
        f"- print_2 (back): {classified.print_back.name if classified.print_back else '—'}",
        f"- print_3 (tag): {classified.print_tag.name if classified.print_tag else '—'}",
        f"- garment_front: {classified.garment_front.name if classified.garment_front else '—'}",
        f"- garment_back: {classified.garment_back.name if classified.garment_back else '—'}",
        f"- garment_tag: {classified.garment_tag.name if classified.garment_tag else '—'}",
        f"- model_front: {classified.model_front.name if classified.model_front else '—'}",
        f"- model_back: {classified.model_back.name if classified.model_back else '—'}",
        f"- model_head_front: {classified.model_head_front.name if classified.model_head_front else '—'}",
        f"- model_head_back: {classified.model_head_back.name if classified.model_head_back else '—'}",
        f"- design_sketch: {classified.design_sketch.name if classified.design_sketch else '—'} (B&W коллаж front+back, design-intent only, НЕ принт)",
        f"- backgrounds: {len(classified.backgrounds)} файла"
        + ("" if has_custom_scene else " (нет → используется balcony template)"),
        f"- models: {len(classified.models)} файла",
        f"- extras: {len(classified.extras)} файла (не используется в промптах)",
        "",
        "## Что делать",
        "1. Открой `READY_FOR_GEMINI/`.",
        "2. Используй отдельный `0X_PROMPT_*.txt` на каждую картинку.",
        ("3. Для футболок порядок: 01 (спереди) → 02 (сзади)"
         + (" → 03 (бирка)" if classified.print_tag else "")
         + " → 04 (человек спереди) → 05 (человек сзади)."),
        "4. Перед шагом 04/05 сохрани результаты шагов 01/02 как `result_front.*` и `result_back.*` и приложи их в чат.",
        "5. Готовые финалы сохраняй в `outputs/` (имена не важны).",
        "",
    ]
    write_text(task_dir / "00_BRIEF.md", "\n".join(lines))


def make_readme(target: Path, ttype: str,
                scenarios: list[dict[str, str]]) -> None:
    lines = [
        "═" * 71,
        "  ЭТА ПАПКА — ГОТОВЫЙ ПАКЕТ ДЛЯ NANO BANANA PRO",
        "═" * 71,
        "",
        f"  Тип задания: {ttype}",
        f"  Промптов: {len(scenarios)}",
        "",
        "  ЧТО ДЕЛАТЬ:",
        "  1) На каждую картинку используй отдельный 0X_PROMPT_*.txt",
        "  2) Прикладывай файлы из refs/ в порядке, указанном в промпте",
        "  3) Для футболок: 04/05 строятся ПОСЛЕ 01/02, на их результате",
        "  4) Если что-то идёт не так — KNOWN_ISSUES.txt",
        "  5) Финалы сохраняй в ../outputs/ (имена не важны)",
        "",
        "  СОДЕРЖИМОЕ:",
    ]
    for s in scenarios:
        lines.append(f"    {s['id']}.txt  ← {s['title']}")
    lines += [
        "    refs/  — нормализованные исходники для прикрепления",
        "",
        "═" * 71,
    ]
    write_text(target / "README.txt", "\n".join(lines))


KNOWN_ISSUES_TEMPLATE = """\
═══════════════════════════════════════════════════════════════════════
  ИЗВЕСТНЫЕ ПРОБЛЕМЫ NANO BANANA PRO И КАК ИХ ОБОЙТИ (edit-mode)
═══════════════════════════════════════════════════════════════════════

ПРОБЛЕМА 1: Модель пересоздаёт сцену вместо edit поверх исходника
─────────────────────────────────────────────────────────────────────
  Это самая частая беда у генеративных моделей: вместо того чтобы
  изменить только принт и бирку, модель ре-рендерит весь кадр. Тогда
  фон, ткань, свет — всё «плывёт».
  Решение: дописать в чат:
    "garment_front.* (or garment_back.*) is the BASE IMAGE. Modify
    only the chest/back print and the inner-collar tag. Preserve the
    rest of the image pixel-by-pixel from the base. Do not re-synthesize
    the scene, fabric, hanger, or lighting."

ПРОБЛЕМА 2: Старый принт остаётся видимым / не до конца стёрт
─────────────────────────────────────────────────────────────────────
    "Erase the existing chest/back print COMPLETELY before applying
    the new one. Reconstruct the clean cotton fabric in that area
    using the surrounding folds, light, and shadow. There must be NO
    ghost or remnant of the previous artwork."

ПРОБЛЕМА 3: Бирка сместилась, вылезла на внешнюю сторону или исчезла
─────────────────────────────────────────────────────────────────────
  Напоминание: "бирка" в нашей системе — это маленький печатный
  брендовый label на ВНУТРЕННЕЙ (изнаночной) стороне ЗАДНЕЙ части
  горловины. Видна только спереди (через вырез) и на макро (шаг 03).
  На внешней стороне (спереди под воротником или сзади) её НЕТ.
  Если в задании print_3_tag нет — бирки на финале быть не должно.

  Если бирка вылезла на внешнюю сторону:
    "The neck-label print (print_3_tag.*) lives ONLY on the INNER
    (wrong-side) surface of the back of the neckline. Remove any
    occurrence of it on the OUTER chest, on the OUTER neckband, on
    the shoulders, or on the back. It must only be visible inside
    the collar opening as the inner back-of-neck label."

  Если бирка сместилась внутри:
    "Keep the inner neck-label print exactly where the original red
    label sits in garment_front.* (visible inside the open collar,
    on the inner side of the back-of-neck panel just above the
    front hem of the ribbed neckband). Same size, same position,
    only the artwork is replaced."

ПРОБЛЕМА 3.5: print_3_tag влился в грудной принт (буквы мержатся)
─────────────────────────────────────────────────────────────────────
  Симптом: буквы из print_1_front (напр. "FUCKS") подменяются
  элементами из print_3_tag (напр. CC-логотип вместо "C").
  Причина: модель воспринимает все принты как один банк графики
  и смешивает их.
  Решение: дописать
    "print_1_front.* and print_3_tag.* are TWO independent prints on
    DIFFERENT regions of the shirt. print_1_front.* lives ONLY on the
    outer chest in its own bounding box. print_3_tag.* lives ONLY on
    the inner back-of-neck label. Glyphs from print_3_tag.* must NEVER
    appear inside the chest print region. Do NOT replace any letter
    of print_1_front.* with shapes from print_3_tag.* (e.g. do not
    replace 'C' with the CC monogram). Render each print exactly as
    its source asset, in its own location only."

ПРОБЛЕМА 4: Принт ломается как текст / буквы перерисованы
─────────────────────────────────────────────────────────────────────
    "Treat print_1_front.* / print_2_back.* / print_3_tag.* as
    finished graphic design assets. Do not re-typeset, redesign, or
    respell any letter. Transfer the artwork visually as if applying
    a screen-print transfer onto cotton."
  Если 3-4 итерации не помогают — Photopea-фолбэк:
    1. https://www.photopea.com
    2. Открой результат + PNG принта
    3. Перенеси принт как слой → Blend Mode "Multiply"
    4. Ctrl+T — подгони размер по груди/спине
    5. Filter → Distort → Displacement Map (футболку как displace-карту)
    6. Save as PNG

ПРОБЛЕМА 5: На фото-на-модели принт / бирка отличаются от шагов 01/02
─────────────────────────────────────────────────────────────────────
    "result_front.* / result_back.* is the source of truth for the
    garment. The chest print, back print, and the small under-collar
    tag print (if it exists in result_front.*) must match it exactly:
    same size, same position, same artwork. If result_front.* has no
    tag print, do not invent one."

ПРОБЛЕМА 6: Лицо модели слишком яркое / похоже на знаменитость
─────────────────────────────────────────────────────────────────────
    "Make the model's face less prominent — frame higher, partial
    face, hair over face, or looking down. Focus on the garment, not
    on a specific identifiable face."

ПРОБЛЕМА 7: AI-артефакты (6 пальцев, искажения, melted edges)
─────────────────────────────────────────────────────────────────────
  Перегенерируй. Если упорно — попроси сменить позу / ракурс или
  добавь в промпт:
    "No AI artifacts: hands must have exactly 5 fingers each, no
    extra limbs, no melted facial features."

═══════════════════════════════════════════════════════════════════════
  ОБЩИЕ ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════

  • НЕ начинай новый чат на каждый ракурс — Pro помнит контекст
  • Делай ракурсы последовательно в одном чате
  • Если 3-4 итерации не помогают — переходи в Photopea
  • Tshirts edit-mode: garment_front/back = canvas, prints = assets
  • Балкон-референсы (scene_*) = детали-память, НЕ замена сцены
  • Бирка = маленький печатный label на ВНУТРЕННЕЙ стороне задней
    части горловины; видна спереди через вырез и на макро; опц.
    (если нет print_3_tag — её нет ни на 01, ни в шаге 03)
    На модели (04/05) она НИКОГДА не видна — шея и волосы скрывают.
  • Текст и логотипы — слабая зона ИИ, считай нормой ручную доработку
  • Сохраняй промежуточные версии (иногда 1-я генерация лучше 4-й)
  • 4K режим (если есть) — лучше включить для финала

═══════════════════════════════════════════════════════════════════════
"""


def make_known_issues(target: Path) -> None:
    write_text(target / "KNOWN_ISSUES.txt", KNOWN_ISSUES_TEMPLATE)


# ---------- legacy fallback (--photos / --print / --references) ----------

def classify_legacy(args: argparse.Namespace) -> Classified:
    """Совместимость со старым CLI: photos = garment*, references = scene*."""
    c = Classified()
    if args.brief_file and args.brief_file.exists():
        c.brief_file = args.brief_file
        c.brief_text = args.brief_file.read_text(encoding="utf-8", errors="ignore")
    elif args.brief:
        c.brief_text = args.brief

    if args.print_file and args.print_file.exists():
        c.print_front = args.print_file

    photos = list_files(args.photos)
    if photos:
        c.garment_front = photos[0]
        if len(photos) > 1:
            c.garment_back = photos[1]
        if len(photos) > 2:
            c.garment_tag = photos[2]
        c.extras.extend(photos[3:])

    refs = list_files(args.references)
    if refs:
        c.backgrounds.extend(p for p in refs if p.suffix.lower() in IMAGE_EXTS)

    return c


# ---------- main ----------

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
    p.add_argument("--input", dest="input_folder", type=Path, default=None,
                   help="Папка с исходниками (см. docs/INPUT_FOLDER_CONVENTION.md)")
    p.add_argument("--brief", default="",
                   help="Краткое ТЗ. Можно через --brief-file")
    p.add_argument("--brief-file", type=Path, default=None,
                   help="Путь к md/txt файлу с ТЗ")
    p.add_argument("--photos", type=Path, default=None,
                   help="(legacy) Папка с фото товара")
    p.add_argument("--print", dest="print_file", type=Path, default=None,
                   help="(legacy) PNG/JPG принта (для футболок)")
    p.add_argument("--references", type=Path, default=None,
                   help="(legacy) Папка с фоном / референсами")
    p.add_argument("--out-root", type=Path, default=None,
                   help="Куда складывать (по умолчанию: stores/<type>s/tasks/)")
    p.add_argument("--copy-to-desktop", action="store_true",
                   help="Дополнительно скопировать в ~/Desktop/Tasks/")
    p.add_argument("--downloads", dest="downloads", action="store_true",
                   default=True,
                   help="Копировать refs в ~/Downloads с префиксом slug "
                        "и mtime=now, чтобы они всплывали наверх в диалогах "
                        "загрузки (по умолчанию ВКЛ)")
    p.add_argument("--no-downloads", dest="downloads", action="store_false",
                   help="Не копировать refs в ~/Downloads")
    p.add_argument("--downloads-dir", type=Path, default=None,
                   help="Кастомный путь до Downloads (по умолчанию ~/Downloads "
                        "или $XDG_DOWNLOAD_DIR)")
    return p.parse_args()


def resolve_downloads_dir(custom: Path | None) -> Path:
    """Возвращает путь к папке загрузок пользователя.

    Порядок: --downloads-dir > $XDG_DOWNLOAD_DIR > ~/Downloads (Linux/Mac)
    > ~/Загрузки (если есть, fallback для русской винды) > ~/Downloads (создаётся).
    """
    if custom is not None:
        return custom
    env = os.environ.get("XDG_DOWNLOAD_DIR")
    if env:
        return Path(env).expanduser()
    home = Path.home()
    cyrillic = home / "Загрузки"
    if cyrillic.exists():
        return cyrillic
    return home / "Downloads"


def copy_refs_to_downloads(refs_dir: Path, downloads_dir: Path,
                           slug: str) -> list[Path]:
    """Копирует все файлы из refs_dir в downloads_dir с префиксом slug.

    - имена становятся `<slug>__<original_name>`
    - mtime/atime ставятся на текущий момент → файлы поднимаются в верх
      "Recently created" в файлдиалогах
    - если файл с таким именем уже есть, он перезаписывается
    - возвращает список итоговых путей
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)
    placed: list[Path] = []
    now = time.time()
    for src in list_files(refs_dir):
        if src.is_dir():
            continue
        dst = downloads_dir / f"{slug}__{src.name}"
        shutil.copy2(src, dst)
        os.utime(dst, (now, now))
        placed.append(dst)
    return placed


def main() -> int:
    args = parse_args()

    # классификация
    if args.input_folder:
        if not args.input_folder.exists():
            print(f"ERROR: input folder not found: {args.input_folder}",
                  file=sys.stderr)
            return 1
        c = classify_inputs(args.input_folder)
        # позволяем перебить бриф через CLI
        if args.brief and not c.brief_text:
            c.brief_text = args.brief
        if args.brief_file and args.brief_file.exists() and not c.brief_text:
            c.brief_text = args.brief_file.read_text(encoding="utf-8",
                                                     errors="ignore")
    else:
        c = classify_legacy(args)

    scenarios = SCENARIOS[args.type]
    slug = slugify(args.slug)
    folder_name = f"{now_stamp()}_{slug}"

    out_root = args.out_root or (REPO_ROOT / "stores" / f"{args.type}s" / "tasks")
    task_dir = out_root / folder_name
    ready = task_dir / "READY_FOR_GEMINI"
    refs = ready / "refs"
    outputs = task_dir / "outputs"
    snapshot = task_dir / "inputs_snapshot"

    if task_dir.exists():
        print(f"ERROR: task dir already exists: {task_dir}", file=sys.stderr)
        return 1

    task_dir.mkdir(parents=True)
    ready.mkdir()
    refs.mkdir()
    outputs.mkdir()
    (outputs / ".gitkeep").touch()

    # snapshot входной папки
    if args.input_folder and args.input_folder.exists() and args.input_folder.is_dir():
        snapshot.mkdir()
        for src in list_files(args.input_folder):
            shutil.copy2(src, snapshot / src.name)

    has_custom_scene = bool(c.backgrounds)
    placed = pack_refs(c, refs, args.type)

    # extras копируем отдельно, чтобы пользователь видел что не подобралось
    if c.extras:
        extras_dir = ready / "extras"
        extras_dir.mkdir(exist_ok=True)
        for src in c.extras:
            shutil.copy2(src, extras_dir / src.name)

    # промпты. Для футболок шаг 03 (бирка-кадр) пропускаем,
    # если в задании нет print_3_tag.
    has_tag = c.print_tag is not None
    if args.type == "tshirt":
        make_tshirt_prompts(ready, has_tag=has_tag)
        if not has_tag:
            scenarios = [s for s in scenarios if s.get("id") != "03_PROMPT_TAG"]
    else:
        make_generic_prompts(ready, args.type, scenarios)

    make_brief(task_dir, args.type, slug, c.brief_text or args.brief,
               scenarios, c, has_custom_scene)
    make_readme(ready, args.type, scenarios)
    make_known_issues(ready)

    print(f"OK. Создал: {task_dir}")
    print(f"     промптов:    {len(scenarios)}")
    print(f"     refs:")
    for k, v in placed.items():
        if v:
            print(f"       {k}: {len(v)}")
    if c.extras:
        print(f"     extras (не использовано): {len(c.extras)}")

    if args.copy_to_desktop:
        desktop = Path.home() / "Desktop" / "Tasks" / folder_name
        desktop.parent.mkdir(parents=True, exist_ok=True)
        if desktop.exists():
            shutil.rmtree(desktop)
        shutil.copytree(task_dir, desktop)
        print(f"     copied to:   {desktop}")

    if args.downloads:
        downloads_dir = resolve_downloads_dir(args.downloads_dir)
        try:
            placed_dl = copy_refs_to_downloads(refs, downloads_dir, slug)
        except OSError as exc:
            print(f"     downloads:   skipped ({exc})")
        else:
            print(f"     downloads:   {len(placed_dl)} файлов в {downloads_dir} "
                  f"с префиксом '{slug}__'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
