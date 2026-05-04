# Шаблон промпта: Бельё на модели (Nano Banana Pro)

> Оптимизировано под **Gemini 3 Pro Image (Nano Banana Pro)** в режиме **multi-image composition**: грузишь фото модели + фото товара + фото фона/референса → получаешь финал.

---

## Подход

Сила Nano Banana Pro в этом кейсе — он умеет:
- Сохранять примерное лицо/телосложение модели по референсу (не 1-в-1, но "очень похоже")
- Точно переносить фактуру и цвет товара
- Сохранять освещение и атмосферу референса

Что от тебя нужно:
1. **Фото модели** (1-2 шт): анфас + профиль, желательно при близком к нужному освещении
2. **Фото товара** (1 шт): чистое фото белья на манекене, плоско, или на однотонном фоне
3. **Фото фона/референс** (1 шт): пример атмосферы, которую хочешь
4. Описание в промпте: какие ракурсы, какое настроение, что важно сохранить

---

## Базовый промпт (FULL_FRONT — полный рост, анфас)

```
Generate a photorealistic fashion photo of a woman wearing the lingerie set from image [N].

MODEL (preserve identity from images [N]):
- Use the model's face structure, skin tone, hair color/length/style from the reference photos
- Approximate likeness is fine — does NOT need to be 1:1 face copy, but should look like "the same person"
- Body type from reference: [BODY TYPE — natural, athletic, curvy, etc.]
- [HAIR STATE: loose / styled / tied back]

LINGERIE (match image [N] EXACTLY):
- Same fabric, color, embroidery, lace pattern, straps, decorative elements
- Same fit and proportions
- Realistic fabric texture: visible weave, slight transparency where applicable, soft fall

POSE:
- Standing relaxed, slight contrapposto, weight on one leg
- Arms naturally at sides, one hand can rest on hip
- Head straight or slight ¾ turn
- Confident relaxed expression, lips slightly parted, soft direct gaze toward camera

BACKGROUND (match image [N] mood):
- [STUDIO / BEDROOM / LOFT — описание]
- [FLOOR/WALL — материалы и цвета]
- Mood: [WARM / COLD / NEUTRAL]

LIGHTING:
- Soft key light from upper-left at 45°
- Soft fill light from right
- Subtle rim light for depth
- Warm color temperature ~3800K
- Natural skin tone reproduction, no orange or grey cast

CAMERA:
- 85mm equivalent
- f/2.8, shallow depth of field
- Eye-level, slightly below shoulder height
- Aspect ratio: 4:5 vertical

QUALITY:
- Photorealistic, like a high-end fashion editorial shot
- Realistic skin texture: visible pores, subtle imperfections, natural shine
- Realistic hair strands, individual hair detail
- No "AI gloss", no plastic skin, no melted features
- Natural body proportions

NEGATIVE:
- No 6 fingers, extra limbs, warped facial features
- No stylization (no airbrush, no Instagram filter, no oversaturation)
- No text, no watermarks, no logos other than what's on the lingerie
- No accessories not specified (jewelry, etc.)
- No oversharpening
```

---

## Базовый промпт (FULL_BACK — полный рост, сзади)

Тот же шаблон, заменить:
- "Standing relaxed, facing camera" → "Standing relaxed, model facing away from camera, head turned slightly to show profile"
- "soft direct gaze toward camera" → "looking over shoulder slightly, soft expression"

---

## Базовый промпт (DETAIL — крупный план деталей)

```
Macro close-up detail shot of [SPECIFIC DETAIL: lace pattern, bow, embroidery, clasp, strap junction, etc.] of the lingerie from image [N].

Show:
- The fabric texture in extreme detail (visible weave, embroidery threads, lace transparency)
- Realistic stitching and edge finishing
- Subtle skin underneath (where applicable)
- Soft natural light catching the fabric texture

CAMERA:
- 100mm macro equivalent, f/4
- Aspect ratio: 1:1 square
- Razor-sharp focus on the detail, slight bokeh on edges

QUALITY:
- Editorial-grade close-up
- Real fabric realism: every thread visible
- Natural specular highlights
- No oversharpening, no overprocessing
```

---

## Переменные

| Переменная | Пример |
|-----------|--------|
| `[N]` | номер референса в чате |
| `[BODY TYPE]` | "natural slim", "athletic toned", "curvy hourglass" |
| `[HAIR STATE]` | "long brown hair flowing loose over shoulders" |
| `[STUDIO/BEDROOM/LOFT]` | "minimalist studio", "soft-lit bedroom with linen sheets", "industrial loft with brick wall" |
| `[FLOOR/WALL]` | "warm beige plaster wall, light wooden floor" |
| `[WARM/COLD/NEUTRAL]` | warm |
| `[SPECIFIC DETAIL]` | "the chantilly lace trim along the bra cup edge" |

---

## Iterative workflow (рекомендую)

**Шаг 1 — генерация базы:**
> "Generate the FULL_FRONT shot using prompts above. Don't worry about perfecting yet, just get the composition and overall vibe."

**Шаг 2 — фикс конкретных проблем:**
> "Keep this exact image but: (a) make the lace pattern match image [N] more precisely, (b) make hair slightly less styled, (c) warmer lighting on skin"

**Шаг 3 — финал:**
> "Now generate FULL_BACK and DETAIL shots in the exact same style, lighting, and atmosphere as this finalized image."

Pro умеет помнить стиль предыдущих картинок в чате — используй это.
