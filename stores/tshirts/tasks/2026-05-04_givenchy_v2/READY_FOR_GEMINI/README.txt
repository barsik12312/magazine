READY_FOR_GEMINI — GIVENCHY V2 / balcony locked scene

Главное изменение после повторного анализа:
- шкаф забываем
- официальный фон для футболки = реальная balcony-сцена из твоих фото
- в папку добавлены отдельные balcony template references
- промпты переписаны так, чтобы модель НЕ меняла детали сцены и НЕ перерисовывала принт как новый текст

ЧТО ВАЖНО:
1. 01_PROMPT_FRONT_HANGER.txt — главный кадр, от него зависит вся серия
2. 02_PROMPT_BACK_HANGER.txt — тот же товар, та же сцена
3. 03_PROMPT_TAG.txt — бирка
4. 04_PROMPT_MODEL_FRONT.txt — модель спереди
5. 05_PROMPT_MODEL_BACK.txt — модель сзади

КЛЮЧЕВЫЕ РЕФЕРЕНСЫ:
- 01_print_FRONT_design.jpg = источник истины для front print
- 03_layout_BACK_mockup.jpg = источник истины для back graphic
- 04/05/06 = реальные фото футболки
- 09-13 = чистые balcony references, которые надо прикладывать как scene lock

ПРИНЦИП РАБОТЫ:
- каждая картинка = отдельный полноценный промпт
- промпты можно использовать не только в Gemini, но и в другой модели
- если делаешь hanger shots, обязательно прикладывай balcony refs
- если модель пытается менять детали — итерируй с фразой:
  "keep the exact same balcony scene, do not change any detail"
