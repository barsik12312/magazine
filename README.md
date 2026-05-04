# Magazine — ИИ фото-продакшен для маркетплейсов

Система подготовки заданий и промптов для генерации товарных фотографий через **Nano Banana Pro** (Gemini 3 Pro Image) в браузере.

> **Что это не:** не код-генератор картинок и не API-обёртка. Это конвейер, который из исходников (фото товара, принт, бриф) собирает готовую папку, которую ты вручную грузишь в Gemini и получаешь финальные картинки.

---

## Как это работает

```
[твои исходники]                    [build_task.py]                [READY_FOR_GEMINI/]
  • фото товара         ───────►       собирает         ───────►    промпты EN+RU
  • PNG принта                                                       + отобранные референсы
  • референсы фона/модели                                            + STEP_BY_STEP.txt
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
└── Задание.txt                   # глобальное ТЗ
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
```bash
python scripts/build_task.py \
  --type tshirt \
  --slug givenchy-v3 \
  --brief "Белая oversized футболка с принтом N° FUCKS GIVENCHY" \
  --photos путь/к/фоткам \
  --print путь/к/print.png
```

Это создаст:
```
stores/tshirts/tasks/2026-05-04_18-30_givenchy-v3/
├── 00_BRIEF.md              # твоё ТЗ
├── READY_FOR_GEMINI/        # ↓ это и грузишь в Gemini
│   ├── README.txt
│   ├── STEP_BY_STEP.txt
│   ├── KNOWN_ISSUES.txt
│   ├── 01_FRONT_HANGER_PROMPT.txt
│   ├── 02_BACK_HANGER_PROMPT.txt
│   ├── 03_TAG_PROMPT.txt
│   ├── 04_MODEL_FRONT_PROMPT.txt
│   ├── 05_MODEL_BACK_PROMPT.txt
│   └── 0X_*.jpg             # отобранные референсы
└── outputs/                 # сюда сохраняй финальные картинки
```

### 3. Сгенерируй в Gemini
1. Открой `https://gemini.google.com` (нужна подписка AI Plus или Pro)
2. Выбери модель **Nano Banana Pro** (Gemini 3 Pro Image)
3. Открой `READY_FOR_GEMINI/STEP_BY_STEP.txt` — там пошагово
4. Для каждого ракурса: копируешь промпт → прикрепляешь референсы → итерируешь
5. Сохраняй финал в `outputs/`

### 4. Если что-то сломалось
Открой `KNOWN_ISSUES.txt` в задании или соответствующий воркфлоу в `docs/workflows/`. Самое частое — текст принта/бирки финишится в Photopea за 5 минут.

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
- [prompts/templates/](prompts/templates/) — шаблоны промптов по категориям

---

## Принципы

1. **Всё на английском в промптах** — Nano Banana Pro понимает русский, но на EN работает чище (особенно с текстом принтов).
2. **Один чат на задание** — Pro помнит контекст, делай все ракурсы последовательно в одном чате.
3. **Длинные подробные промпты** — 1500-3000 символов норма. Расписывай товар, фон, камеру, качество, негативы.
4. **Iterative refinement** — не жди идеала с 1-й генерации. Получил → пишешь правки.
5. **Photopea для финиша текста** — сложные шрифты на принтах/бирках доводи в Photopea (5 мин), не сражайся с моделью часами.
