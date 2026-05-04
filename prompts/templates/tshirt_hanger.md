# Шаблон промпта: Футболка на вешалке (Nano Banana Pro)

> Этот шаблон оптимизирован под **Gemini 3 Pro Image (Nano Banana Pro)**. Pro понимает длинные детальные промпты, явные негативные инструкции и multi-image композицию.

---

## Подход

Nano Banana Pro лучше всего работает, когда ты:
1. Грузишь **2-4 референс-фото** (фон/шкаф, реальная футболка с похожей посадкой, отдельно PNG принта если есть)
2. Пишешь промпт **на английском**, длинный и конкретный (1500-3000 символов — норма)
3. **Прямо называешь известные проблемы** ("don't add extra letters", "preserve exact spelling")
4. Просишь **iteratively** — сначала базу без принта, потом добавляешь принт отдельной итерацией ("now add the print exactly as in image 3")

---

## Базовый промпт (FRONT — вешалка, спереди)

```
Generate a photorealistic e-commerce product photo of a [COLOR] oversized cotton crew-neck t-shirt hanging on a black plastic clothes hanger, hooked on a white window handle.

PRINT (CRITICAL — match exactly):
The t-shirt has a print on the chest area. The print is shown in image [N] (the PNG with transparent background). Reproduce it EXACTLY as shown:
- Same letters, same spelling, same order
- Same font weight and proportions
- Same colors
- Apply natural fabric distortion (wrinkles deform the print slightly)
- Print should look screen-printed into the fabric (matte ink, no gloss, no halo)

BACKGROUND (match image [N]):
- Dark emerald velvet curtain on the back wall
- Black plastic clothes hanger on a white window handle
- Green potted plant (fiddle leaf fig style) on the right
- Dark metal shelf-ladder visible on the right edge
- Natural soft daylight coming from a window on the left
- Slight shadow from t-shirt on the curtain

CAMERA:
- iPhone 15 Pro main camera equivalent, 26mm focal length
- Eye-level shot
- Light depth of field, t-shirt in sharp focus, background slightly soft
- Aspect ratio: 4:5 vertical (portrait, marketplace-friendly)

QUALITY:
- Photorealistic, indistinguishable from a real iPhone photo
- Realistic cotton fabric texture: natural wrinkles, slight creases at shoulders, soft drape
- Realistic shadows and ambient occlusion under the hanger
- No oversaturation, no HDR look, no plastic-y skin or fabric

NEGATIVE (do NOT include):
- Do not add extra letters, symbols, or marks not present in the print reference
- Do not change the spelling of any text
- Do not add brand logos other than the one in the print reference
- Do not add visible stitching seams unless they exist in the reference
- No AI artifacts: no warped letters, no melted edges, no extra fingers/limbs (no model in this shot)
- No text outside the t-shirt area
- No watermarks, no signatures
```

---

## Базовый промпт (BACK — вешалка, сзади)

Тот же шаблон, заменить:
- "front of t-shirt with print on chest" → "back of t-shirt, plain back unless print reference shows back design"
- "view from front" → "view from back"

---

## Базовый промпт (TAG — бирка крупным планом)

```
Macro close-up photo of the inner neckline tag of the [COLOR] cotton t-shirt from previous images.

The tag should:
- Be a small white woven fabric label sewn into the back of the neckline
- Show brand name "[BRAND TEXT]" in clean sans-serif font
- Show size "[SIZE]" below brand name
- Show care symbols (machine wash, tumble dry low, no bleach) in a row at the bottom
- Be slightly creased, photographed at an angle, with shallow depth of field

CAMERA:
- 100mm macro equivalent, f/4
- Aspect ratio: 1:1 square

QUALITY:
- Razor-sharp text on tag, perfectly legible
- Realistic woven fabric texture on both tag and t-shirt
- Soft natural daylight, very slight shadow

NEGATIVE:
- Do not invent extra text
- Do not add fake care symbols not in the standard set
- Do not blur the brand name
- Brand name spelling must match EXACTLY: "[BRAND TEXT]"
```

---

## Базовый промпт (MODEL_FRONT — на модели, вид спереди)

```
Generate a photorealistic photo of a young man (~25 years old, athletic build, [HAIR DESCRIPTION], [SKIN TONE], [FACE DESCRIPTION FROM DOSSIER]) wearing the same [COLOR] oversized t-shirt with the [PRINT DESCRIPTION] print on the chest, exactly as shown in the previous t-shirt images.

PRINT CONSISTENCY (CRITICAL):
- The print on the t-shirt must be IDENTICAL to image [N]
- Same letters, same colors, same proportions
- Account for the natural distortion when fabric is on a body (slight stretch on chest, slight wrinkles)
- Print scale: should occupy the chest area, ~20-25cm wide

POSE:
- Standing relaxed, slight contrapposto
- Hands at sides or one in pocket
- Looking slightly off-camera (¾ angle), neutral confident expression
- Framed from mid-thigh up

CLOTHING (other than t-shirt):
- Light blue baggy jeans, slightly cropped at the ankle
- Plain white sneakers (visible if framed)

BACKGROUND:
- Plain white seamless studio background OR same room as t-shirt-on-hanger shots (decide based on "[VARIANT]")
- Soft natural daylight from upper-left

CAMERA:
- 50mm equivalent, f/2.8
- Eye-level
- Aspect ratio: 4:5 vertical

QUALITY:
- Photorealistic, like an iPhone 15 Pro shot
- Natural skin texture with visible pores and slight asymmetry
- Realistic cotton drape and wrinkles where fabric meets body
- Subtle catchlight in eyes
- Realistic hair strands, no melted strands

NEGATIVE:
- Do not change the print
- Do not stylize the model (no airbrushing, no plastic skin)
- No 6 fingers, no extra limbs, no warped facial features
- Do not add jewelry, watches, or accessories unless specified
- No watermark, no Instagram filters
```

---

## Базовый промпт (MODEL_BACK — на модели, вид сзади)

Тот же шаблон что MODEL_FRONT, заменить:
- "front view" → "back view, model facing away from camera, head turned slightly to show profile"
- Print: если есть на спине — описать; если нет — "back of shirt is plain"

---

## Переменные для подстановки

| Переменная | Пример |
|-----------|--------|
| `[COLOR]` | white / black / cream / heather grey |
| `[PRINT DESCRIPTION]` | "N° FUCKS GIVENCHY с CC-логотипом" |
| `[BRAND TEXT]` | название бренда на бирке |
| `[SIZE]` | M / L / XL |
| `[HAIR DESCRIPTION]` | "short brown hair, slight wave" |
| `[SKIN TONE]` | "light olive skin tone" |
| `[FACE DESCRIPTION FROM DOSSIER]` | из досье модели в `data/models/` |
| `[VARIANT]` | "studio" / "wardrobe" |
| `[N]` | номер референс-картинки в чате |

---

## Альтернативный фон "Балкон"

Заменить в Background-блоке:
```
- Light wooden floor with parquet
- Floor-to-ceiling glass balcony door on the left, soft city view outside
- Small ladder shelf with a few dried flowers and one small green plant
- Warmer, brighter natural light coming from balcony
- Slight indoor-outdoor color contrast
```
