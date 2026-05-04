# Magazine — ИИ фото-продакшен для маркетплейсов

Система подготовки заданий и промптов для генерации товарных фотографий через **Nano Banana Pro** (Gemini 3 Pro Image) в браузере.

> **Что это не:** не код-генератор картинок и не API-обёртка. Это конвейер, который из исходников (фото товара, принт, бриф) собирает готовую папку, которую ты вручную грузишь в Gemini и получаешь финальные картинки.

---

## Как это работает

```
[твои исходники]                    [build_task.py]                [READY_FOR_GEMINI/]
  • фото товара         ───────►       собирает         ───────►    промпты EN+RU
  • PNG принта                                                       + отобранные референсы
  • референсы фона/модели                                            + balcony scene lock refs
  • краткое ТЗ                                                       + KNOWN_ISSUES.txt
                                                                              │
                                                                              ▼
                                                                    [ты в Gemini]
                                                                    копируешь промпт,
                                                                    кидаешь референсы,
                                                                    итерируешь до результата
                                                                              │
                                                                              ▼
                                                                       outputs/*.png
```

---

## Структура репозитория

```
magazine/
├── stores/                       # 3 направления магазина
│   ├── tshirts/
│   │   ├── raw_photos/           # реальные фото футболок (фон-эталон + принты)
│   │   ├── prints/               # PNG принтов
│   │   ├── backgrounds/          # референсы фонов
│   │   ├── models/               # досье моделей
│   │   ├── tasks/                # активные и архивные задания
│   │   └── output/               # финальные карточки
│   ├── lingerie/                 # та же структура
│   └── clothing/                 # та же + avito_screenshots, style_references
├── scripts/
│   └── build_task.py             # сборщик задания → READY_FOR_GEMINI/
├── prompts/
│   ├── templates/                # шаблоны промптов (EN+RU) под Nano Banana Pro
│   │   ├── tshirt_hanger.md
│   │   ├── lingerie_studio.md
│   │   └── clothing_catalog.md
│   ├── brand_style.md            # единый визуальный стандарт
│   └── Арт директор.md            # мастер-промпт структурирования
├── docs/
│   ├── generation_guide.md       # обзор инструментов и подхода
│   └── workflows/
│       ├── nano_banana_pro_workflow.md   # полный цикл "идея → 5 картинок"
│       ├── tshirt_print_mockup.md        # фикс принта в Photopea (5 минут)
│       ├── lingerie_blending.md          # multi-image композиция
│       └── clothing_avito_rework.md      # переделка скринов Авито
├── data/
│   └── models/                   # досье моделей (общие)
└── BRIEF.txt                     # глобальное ТЗ
```

---

## Три направления

| Магазин | Что делаем | Сценарии в build_task.py |
|---------|-----------|--------------------------|
| **tshirts** | Карточки футболок: вешалка front/back, бирка, на модели front/back | 5 ракурсов |
| **lingerie** | Бельё на модели: full front/back, деталь, lifestyle | 4 ракурса |
| **clothing** | Переделка скринов Авито в студию + каталог + lifestyle | 3 ракурса |

---

## Быстрый старт

### 1. Установка
```bash
git clone https://github.com/barsik12312/magazine.git
cd magazine
# скрипт работает на чистом Python 3.10+, без зависимостей
```

### 2. Подготовь задание

Собираешь папку с исходниками (см. [docs/INPUT_FOLDER_CONVENTION.md](docs/INPUT_FOLDER_CONVENTION.md)) и натравливаешь на неё `build_task.py`:

```bash
python scripts/build_task.py \
  --type tshirt \
  --slug givenchy-v3 \
  --input inputs/2026-05-04_givenchy/
```

Где входная папка может выглядеть так:
```
inputs/2026-05-04_givenchy/
├── задание.md
├── 1.png        ← основной грудной принт (обязательный)
├── 2.jpg        ← back-принт (обязательный)
├── 3.png        ← маленький принт-«бирка» под горловиной (опционально)
├── спереди.jpg  ← реальное фото футболки спереди
├── сзади.jpg    ← реальное фото футболки сзади
├── бирка.jpg    ← опц. макро бирки
└── модель.jpg   ← опц. референс позы
```

Скрипт автоматически разберёт файлы по категориям, нормализует имена и соберёт пакет:

```
stores/tshirts/tasks/2026-05-04_18-30_givenchy-v3/
├── 00_BRIEF.md
├── inputs_snapshot/                  # снимок исходников
├── outputs/                          # сюда сохраняешь финал
└── READY_FOR_GEMINI/
    ├── README.txt
    ├── KNOWN_ISSUES.txt
    ├── 01_PROMPT_FRONT.txt           # edit поверх garment_front: грудь + бирка
    ├── 02_PROMPT_BACK.txt            # edit поверх garment_back
    ├── 03_PROMPT_TAG.txt             # макро бирки (создаётся только если есть `3`)
    ├── 04_PROMPT_MODEL_FRONT.txt     # человек спереди (база = твой результат шага 1)
    ├── 05_PROMPT_MODEL_BACK.txt      # человек сзади (база = твой результат шага 2)
    ├── refs/                         # нормализованные имена: print_1_front, garment_front, scene_*, ...
    └── extras/                       # неподобранные файлы
```

### 3. Сгенерируй в Gemini
1. Открой `https://gemini.google.com` (нужна подписка AI Plus или Pro)
2. Выбери модель **Nano Banana Pro** (Gemini 3 Pro Image)
3. Для каждого шага: копируешь промпт `0X_PROMPT_*.txt` → прикрепляешь файлы из `refs/` в указанном порядке → итерируешь
4. Шаги 04/05 запускай ПОСЛЕ шагов 01/02 (используют твои готовые результаты)
5. Сохраняй финал в `outputs/`

### 4. Если что-то сломалось
Открой `KNOWN_ISSUES.txt` в задании или соответствующий воркфлоу в `docs/workflows/`. Для футболок главные принципы edit-mode: garment_front/back = canvas, print = finished graphic asset, балкон = детали-память (не scene-donor). Самое частое — текст принта/бирки финишится в Photopea за 5 минут.

---

## Готовый пример: задание 1 (Givenchy)

В репо лежит **полностью готовое задание 1** под Nano Banana Pro:

📁 `stores/tshirts/tasks/2026-05-04_givenchy_v2/`

Открой и работай — в `READY_FOR_GEMINI/` всё готово к загрузке в Gemini. Это пример как должно выглядеть готовое задание после `build_task.py`.

---

## Документация

- [docs/generation_guide.md](docs/generation_guide.md) — обзор инструментов (Nano Banana Pro, альтернативы, Photopea)
- [docs/workflows/nano_banana_pro_workflow.md](docs/workflows/nano_banana_pro_workflow.md) — полный цикл работы
- [docs/workflows/tshirt_print_mockup.md](docs/workflows/tshirt_print_mockup.md) — фикс принта в Photopea
- [docs/workflows/lingerie_blending.md](docs/workflows/lingerie_blending.md) — multi-image композиция для белья
- [docs/workflows/clothing_avito_rework.md](docs/workflows/clothing_avito_rework.md) — переделка скринов Авито
- [prompts/brand_style.md](prompts/brand_style.md) — единый визуальный стандарт
- [prompts/gem_system_prompt.md](prompts/gem_system_prompt.md) — system instruction для Custom Gem в Gemini
- [prompts/templates/](prompts/templates/) — шаблоны промптов по категориям

---

## Принципы

1. **Всё на английском в промптах** — Nano Banana Pro понимает русский, но на EN работает чище.
2. **Каждая картинка = отдельный полноценный промпт** — пригодный и для Gemini, и для других моделей.
3. **Для tshirts edit-mode**: `garment_front` / `garment_back` = база (canvas). Стираем старый принт + (опц.) старую бирку и наносим новые за один прогон. Сцена сохраняется из исходника.
4. **Балкон-референсы = detail-memory**, а не scene-donor. Они не заменяют сцену из реального фото.
5. **Print = finished graphic asset** — не проси модель заново набирать логотип/текст, проси визуально перенести artwork.
6. **Бирка** — это маленький принт под горловиной СПЕРЕДИ (не внутренняя нашивка), и она опциональна. Если файла `3` нет — бирки в задании нет.
7. **Iterative refinement + Photopea** — если после 2-3 итераций текст/принт всё ещё ломается, быстрее добить вручную.
