# Шаблон промпта: Футболки — hanger / tag / model

> Этот шаблон теперь заточен не под свободное "вдохновись референсом", а под **locked-scene reconstruction** + **graphic-transfer fidelity**. То есть: если у тебя есть реальные фото сцены и отдельный PNG принта, модель должна максимально сохранить и сцену, и графику без самодеятельности.

---

## Главные принципы

1. **Сцена не пересобирается заново**. Если приложены реальные balcony references — это не inspiration, это exact environment lock.
2. **Принт не набирается заново как текст**. Если приложен PNG / graphic reference — это готовый графический элемент, который нужно перенести на ткань визуально.
3. **Ни одна деталь сцены не должна меняться**, если пользователь не просил.
4. **Каждая картинка = отдельный полноценный промпт**, пригодный не только для Gemini, но и для другой модели.
5. **Одно изделие = одна серия**. Все 5 кадров должны ощущаться как один и тот же реальный товар.

---

## Базовый промпт (FRONT_HANGER)

```text
Generate one photorealistic e-commerce product photo of a [COLOR] oversized cotton crew-neck t-shirt hanging on a black plastic hanger in the EXACT real balcony/window scene shown in the attached references.

REFERENCE IMAGES:
- Image 1 = the front print graphic / artwork that must appear on the chest
- Image 2 = the front print placement / layout mockup
- Image 3 = real reference of a similar t-shirt hanging in the target balcony scene
- Image 4 = close-up fabric / collar / drape reference for the real t-shirt
- Images 5+ = balcony template references showing the exact environment that must remain unchanged

OBJECTIVE:
Create a final product photo that looks like a real smartphone photo of the t-shirt hanging in that exact balcony scene. The goal is not to invent a new setup. The goal is to reconstruct the real scene and swap the garment graphic while preserving the environment.

CHEST PRINT / GRAPHIC TRANSFER (CRITICAL):
The artwork in image 1 is a PRE-MADE GRAPHIC DESIGN ASSET, not text that should be re-typeset or re-rendered from scratch.
Treat image 1 as finished graphic artwork.
Transfer that exact artwork onto the chest area of the t-shirt.
Preserve every visible graphic detail from image 1:
- same glyph shapes
- same letterforms
- same line weights
- same spacing
- same strike-throughs / decorations
- same logo integration
- same proportions
- same black/white relationship
Do NOT reinterpret the artwork.
Do NOT respell it.
Do NOT replace letters with similar ones.
Do NOT redesign the composition.
Only allow the kind of subtle distortion caused by real cotton fabric folds and the drape of the hanging shirt.
The print should look like matte screen print ink bonded to the cotton surface: no glossy sticker look, no halo, no bevel, no embossed effect.

PRINT PLACEMENT (CRITICAL):
Follow image 2 for size and placement.
The chest print must sit in the exact same relative position as in the placement mockup.
Keep scale believable for a real oversized t-shirt.
Do not move it too high, too low, too small, or too large.

GARMENT:
- [COLOR] oversized t-shirt
- heavyweight cotton jersey
- matte fabric surface
- structured but soft drape
- crew neck with ribbed collar
- natural shoulder drop
- realistic sleeve and hem stitching only if visible in the garment reference
- no luxury CGI fabric, no glossy synthetic look

LOCKED BALCONY SCENE (ABSOLUTE PRIORITY):
Reconstruct the exact real balcony/window environment from the attached balcony references.
This is a locked scene, not a stylistic prompt.
Preserve all visible environmental details.
Do not replace, remove, restyle, or simplify objects.
Keep the same:
- window frame geometry
- frame color
- handle side and handle position
- open/closed state of the window as shown in the chosen framing reference
- balcony outside with green floor / turf visible where present
- radiator placement
- ladder placement
- plant placement
- curtain presence and color
- desk edge on the right where visible
- windowsill objects where visible
- overall perspective and crop logic
If a specific balcony reference includes some reflections, keep them natural and subtle rather than deleting the whole reality of the space.
No object substitution. No decor changes. No cleanup. No redesign.

COMPOSITION:
- the shirt is the hero object
- hanger attached to the same real window handle / hook logic seen in the references
- framing should feel like a real handheld or carefully shot phone photo from the same room
- aspect ratio: 4:5 vertical
- t-shirt centered enough for marketplace use, but still believable as a real photo in the actual room

LIGHTING:
Use the exact real daylight logic from the balcony references.
Soft natural daylight from the window side.
Do not turn the shot into studio light.
Do not make it cinematic or overly contrasty.
Keep the same realistic ambient conditions as the real balcony references.

CAMERA / LOOK:
- photorealistic smartphone-style product image
- natural lens perspective
- sharp garment and print
- mild depth separation only if naturally believable
- no HDR look
- no over-sharpening
- no beauty retouching

NEGATIVE / DO NOT CHANGE:
- do not change the scene layout
- do not replace the plant, ladder, radiator, curtain, desk, or balcony floor
- do not change the handle location or geometry
- do not generate a different room
- do not re-render the artwork as new text
- do not alter spelling or glyph shapes in the print graphic
- do not add extra logos
- do not add extra text outside the print
- do not add a person, mannequin, or hands
- no AI artifacts
- no melted edges
- no warped letters
- no fake luxury showroom styling
- no random decor additions
- no watermarks or UI overlays

OUTPUT:
One final 4:5 photorealistic marketplace-ready image that looks like a real photo taken in the exact attached balcony scene, with the provided artwork transferred faithfully onto the t-shirt.
```

---

## Базовый промпт (BACK_HANGER)

```text
Generate one photorealistic back-view product photo of the SAME [COLOR] oversized t-shirt hanging in the EXACT same locked balcony scene as the front shot.

REFERENCE IMAGES:
- Image 1 = back graphic layout / mockup / back artwork reference
- Image 2 = real back-view garment reference in the balcony scene
- Images 3+ = locked balcony scene references

OBJECTIVE:
Show the back of the same physical t-shirt while preserving the exact same environment, same hanger logic, same garment identity, and same realism level as the front image.

BACK GRAPHIC (CRITICAL):
Treat the back artwork reference as the source of truth.
Preserve its exact silhouette, placement, stripe count, spacing, lower logo placement, and overall composition.
Do not improvise. Do not simplify. Do not change orientation.
If the artwork is a mockup rather than a clean print file, still preserve its composition exactly.
Apply only natural fabric-following distortion.

LOCKED SCENE:
Same strict rule as front shot: reconstruct the exact balcony environment without changing any visible detail.

CONTINUITY:
- same t-shirt body
- same collar construction
- same fabric weight
- same color
- same hanger
- same room
- same camera family
- same daylight logic

NEGATIVE:
- do not change stripe count
- do not change shape
- do not add text on the back unless present in the reference
- do not change the balcony details
- do not introduce a different crop logic unrelated to the real references
- no mannequin, no model, no hands
- no AI artifacts

OUTPUT:
One 4:5 photorealistic back-view image from the same product series.
```

---

## Базовый промпт (TAG)

```text
Generate one photorealistic macro product photo of the inner neckline tag of the SAME t-shirt.

OBJECTIVE:
The image should feel like a real product-detail photo from the same garment series.

TAG:
- small woven fabric label sewn into the inside back neckline
- realistic woven texture
- realistic fold / curvature
- macro sharpness on the label area
- surrounding collar fabric visible

TEXT RULE:
If the exact brand text matters, render it as accurately as possible, but preserve clean typography and realism.
If a separate tag reference exists, follow it exactly.
If not, keep the tag believable and production-friendly.

CAMERA:
- 1:1 square
- macro close-up
- shallow depth of field
- sharp focus on the tag

NEGATIVE:
- no gibberish if avoidable
- no random extra lines of text
- no fake stains
- no unrealistic floating label

OUTPUT:
One photorealistic square macro detail shot.
```

---

## Базовый промпт (MODEL_FRONT)

```text
Generate one photorealistic catalog / lifestyle photo of a male model wearing the SAME t-shirt from the hanger shots.

REFERENCE IMAGES:
- model type reference
- front print artwork
- front hanger result / hanger reference
- optional balcony references if the model shot should also stay in the balcony environment

OBJECTIVE:
Show the same garment on-body while preserving the same print size, same print placement, same garment identity, and the intended styling direction.

MODEL:
Use the attached model reference for body type, age range, styling, pose family, and proportions.
Do not make the model overly glamorous or celebrity-like.

PRINT CONTINUITY:
The chest print must match the hanger shot exactly in composition, scale relationship, and placement.
Treat the print graphic as a transferred artwork, not newly generated text.

BACKGROUND:
If the user wants studio: keep it clean and minimal.
If the user wants balcony continuity: lock the same balcony scene just as strictly as for hanger shots.

NEGATIVE:
- no change to print
- no accessories unless requested
- no anatomy mistakes
- no fashion-editorial exaggeration unless requested

OUTPUT:
One photorealistic 4:5 on-model image.
```

---

## Базовый промпт (MODEL_BACK)

```text
Generate one photorealistic back-view on-model image of the SAME male model wearing the SAME t-shirt.

OBJECTIVE:
Show the back artwork clearly while preserving the same garment, same model identity/type, same styling, and same photo-series continuity.

BACK GRAPHIC:
Must match the back hanger shot exactly.
Same shape, same placement, same proportions, same visual identity.

MODEL / STYLING:
Preserve same jeans, same fit logic, same stance family, same realism level.

BACKGROUND:
Use the requested environment (studio or locked balcony) exactly.

NEGATIVE:
- no graphic redesign
- no different garment silhouette
- no anatomy artifacts
- no random props or extra people

OUTPUT:
One photorealistic 4:5 back-view on-model image.
```
