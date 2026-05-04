# Шаблон промпта: Одежда — каталог + lifestyle + переделка скринов Авито (Nano Banana Pro)

> Оптимизировано под **Gemini 3 Pro Image (Nano Banana Pro)**.

---

## Сценарий 1: Переделка скриншота Авито в студийное фото

**Это самая лёгкая задача для Nano Banana Pro — решается одним промптом.**

### Промпт

```
Take the product in image [N] (a screenshot from a marketplace listing) and reimagine it as a professional studio fashion photo.

PRODUCT TO PRESERVE (CRITICAL):
- Same garment: same color, fabric, cut, length, decorative elements
- Same proportions and silhouette
- Color must be EXACTLY accurate (do not shift hue or saturation)
- All details: collar style, sleeve length, hem, buttons, zippers, prints — preserve exactly

CHANGES (apply):
- Remove ALL watermarks (Avito watermark, prices, text overlays, "Фото товара" labels)
- Replace background with: [BACKGROUND — clean studio beige / soft grey / minimalist room]
- Add professional studio lighting: soft key from upper-left, gentle fill from right, slight rim light
- Replace any visible mannequin or random model with [MODEL DESCRIPTION] OR keep on a hanger
- Frame the garment to fit aspect ratio [4:5 vertical] with comfortable margin

CAMERA:
- 50mm equivalent, f/4
- Eye-level
- Aspect ratio: 4:5

QUALITY:
- Photorealistic high-end e-commerce shot
- Realistic fabric texture: visible weave, natural drape, soft wrinkles where appropriate
- Sharp focus on garment, slight depth of field on background
- True-to-life color reproduction (white balance: daylight 5500K)

NEGATIVE:
- Do NOT change garment color
- Do NOT alter cut or proportions
- Do NOT add elements not present in the original (extra buttons, decorations, etc.)
- No watermarks, no Avito branding, no text
- No AI artifacts (warped seams, melted edges)
- No plastic-looking fabric
```

### Переменные

| Переменная | Пример |
|-----------|--------|
| `[N]` | номер референс-скрина |
| `[BACKGROUND]` | "clean warm beige seamless studio backdrop" / "soft warm grey wall, light wooden floor" |
| `[MODEL DESCRIPTION]` | "natural slim woman, long brown hair, neutral expression" / "no model, garment on white hanger" |

---

## Сценарий 2: Каталожное фото на модели (CATALOG)

```
Generate a professional e-commerce catalog photo of [MODEL DESCRIPTION] wearing [GARMENT FROM IMAGE [N]].

MODEL:
- [GENDER, AGE, BODY TYPE]
- [HAIR DESCRIPTION]
- [SKIN TONE]
- Standing straight, facing camera, neutral confident expression
- Hands relaxed at sides

GARMENT (preserve from image [N]):
- Same color, fabric, cut, decorations
- Realistic drape on body, natural wrinkles where fabric meets body

BACKGROUND:
- Clean [BEIGE / SOFT GREY / WHITE] seamless studio backdrop
- No props, no other objects

LIGHTING:
- Even soft studio lighting from front
- Subtle shadow under feet for grounding
- White balance: 5500K daylight

CAMERA:
- 50mm equivalent, f/5.6
- Full body framed with comfortable space above head and below feet
- Aspect ratio: 3:4

QUALITY:
- Photorealistic
- Natural skin texture, realistic hair, realistic fabric
- No AI artifacts

NEGATIVE:
- Do not change garment design
- No watermarks
- No oversaturation
```

---

## Сценарий 3: Lifestyle / бренд-лента (как референс с шёлковым платьем)

```
Cinematic editorial lifestyle photo of [MODEL DESCRIPTION] wearing [GARMENT FROM IMAGE [N]].

SCENE:
- Location: [LOCATION — sunlit Mediterranean apartment / candlelit luxury bathroom / golden hour rooftop / etc.]
- Action: [ACTION — holding a champagne glass, leaning against an arched doorway, looking thoughtfully out a window, etc.]
- Time of day: [GOLDEN HOUR / EVENING / SOFT MORNING]
- Mood: [INTIMATE / EDITORIAL / DREAMY / CONFIDENT]

PROPS (subtle, supporting the mood):
- [PROPS LIST — single white candle, small ceramic vase, glass of champagne]
- Props should be slightly out of focus, never compete with the model

LIGHTING:
- [GOLDEN HOUR ambient / candle warm glow / soft window daylight]
- One main soft directional source, ambient fill
- Catchlight in eyes
- Slight haze/atmosphere for cinematic feel

COLOR PALETTE:
- [WARM CREAM AND GOLD / SOFT BEIGE AND TERRACOTTA / etc.]
- Cohesive with the garment color

GARMENT:
- Match image [N] exactly — same fabric, color, cut, drape
- Realistic flow and movement
- Show the texture (silk sheen, linen weave, etc.)

CAMERA:
- 35mm equivalent, f/1.8
- Slight tilt or natural composition (rule of thirds, not centered)
- Aspect ratio: 4:5 vertical

QUALITY:
- Editorial fashion photography quality
- Cinematic color grading
- Shallow depth of field, dreamy bokeh
- Realistic skin, hair, fabric
- No "instagram filter" look — should feel like a real magazine spread

NEGATIVE:
- No oversaturation, no HDR
- No 6 fingers, warped features
- No text, watermarks, logos
- No oversharpening
```

---

## Iterative workflow для lifestyle

Pro отлично держит "стиль" в чате. Делай так:

1. **Первый кадр** — описывай всё максимально детально
2. **Второй кадр** — "Same model, same garment, same atmosphere, but now [different action/location]"
3. **Третий кадр** — "Same series, now [different angle / detail shot]"

Это даст серию из 5-10 фото в одном стиле для ленты бренда.
