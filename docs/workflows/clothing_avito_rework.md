# Воркфлоу: Переделка скриншотов Авито в студийные фото

Часто товар уже продаётся на Авито/Юле/Wildberries у поставщиков, и у тебя есть только их скриншоты. Этот воркфлоу превращает их в чистые студийные фото за 2-5 минут.

---

## Сценарий 1: Скрин с одеждой на манекене / на вешалке

**Сложность:** очень простая. Nano Banana Pro решает в 1 промпт.

### Шаги

1. Загрузи скриншот в Gemini в чат с Nano Banana Pro
2. Используй промпт из `prompts/templates/clothing_catalog.md` → "Сценарий 1: Переделка скриншота Авито в студийное фото"
3. Заполни плейсхолдеры:
   - `[BACKGROUND]` — например, "clean warm beige seamless studio backdrop"
   - `[MODEL DESCRIPTION]` — "no model, garment on white hanger" (если хочешь убрать манекен)
4. Отправь
5. Получишь чистое студийное фото без watermark Авито, без UI элементов

### Типичные правки на 2-й итерации
- Цвет немного сдвинулся → "Restore the EXACT original color from image 1 — do not shift hue or saturation"
- Watermark не до конца убран → "Remove ALL Avito branding, remove the price overlay, remove the 'Закрыть' button"
- Форма товара изменилась → "Preserve the EXACT cut, length, sleeve style from the original image"

---

## Сценарий 2: Скрин с одеждой на чужом теле / странной модели

**Сложность:** средняя. Нужно сменить модель, сохранив посадку.

### Шаги

1. Загрузи в Gemini:
   - Скриншот с Авито (image 1)
   - Опционально: фото вашей модели или референс желаемого типажа (image 2)
2. Промпт:
```
Take the garment from image 1 (a marketplace screenshot) and re-render it
on [a different model / your preferred model].

PRESERVE FROM IMAGE 1 (CRITICAL):
- Exact garment: same color, fabric, cut, length, decorative elements
- Same fit and proportions
- Color must be EXACTLY accurate

CHANGES:
- Replace the model with: [DESCRIPTION OR "use the model from image 2"]
- Pose: [DESCRIPTION — relaxed standing, looking off camera, etc.]
- Background: [clean studio beige / urban street / etc.]
- Remove all Avito UI overlays, watermarks, prices

CAMERA, LIGHTING, QUALITY: [as in standard catalog template]
```
3. Итерируй

---

## Сценарий 3: Скрин с тёмным/плохим фоном — нужен lookbook-стиль

**Сложность:** средняя-высокая. Полное преображение под бренд-стиль.

### Шаги

1. Используй промпт из "Сценарий 3: Lifestyle / бренд-лента" в `prompts/templates/clothing_catalog.md`
2. Загрузи:
   - Скриншот товара
   - 1-2 референса твоего бренд-стиля (атмосфера, цвет, локация)
3. Скажи Pro: "Rebuild the garment from image 1 in the style/atmosphere of images 2-3"
4. Итерируй

---

## Что обычно ломается

| Проблема | Решение |
|----------|---------|
| Цвет товара сдвинулся | "Color must EXACTLY match the original image 1, no hue shift" |
| Watermark Авито остался | "Remove ALL Avito branding, all UI overlays, all text" |
| Крой изменился (короче/длиннее) | "Preserve the EXACT cut and length from image 1" |
| Появились детали которых не было | "Do NOT add elements not present in image 1 — no extra buttons, no decorations" |
| Модель странная | Замени модель отдельной итерацией |

---

## Скриншоты Авито — типичные проблемы

Скриншоты обычно содержат:
- Watermark "Avito" в углу
- UI: кнопки "Позвонить", "Написать", "Закрыть"
- Текст вроде "5 из 8" (счётчик фото)
- Иногда иконки приложения
- Полосы статус-бара iPhone/Android

**Все эти элементы Pro убирает легко** — просто явно перечисли в промпте: "Remove all of: watermarks, UI buttons, photo counter, status bar elements, brand text overlays."

---

## Финал

После Gemini:
- Если цвет немного не тот — Photopea → Image → Adjustments → Color Balance / Hue-Saturation
- Если нужно стандартное соотношение для маркетплейса — Crop в Photopea (1:1 для Wildberries, 4:5 для Ozon, 3:4 для Lamoda)
- Сохрани как PNG/JPG в высоком качестве

**Время на 1 фото:** 2-5 минут вместе с итерациями.
