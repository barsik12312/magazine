# Задание 1 — карточка футболки "N° FUCKS GIVENCHY" (v3 логика, balcony locked scene)

## Что делаем
Карточка товара из 5 финальных изображений:

| № | Что | Ракурс | Aspect |
|---|-----|--------|--------|
| 01 | FRONT_HANGER | футболка спереди на чёрной вешалке в РЕАЛЬНОЙ balcony-сцене | 4:5 |
| 02 | BACK_HANGER | та же футболка сзади в той же balcony-сцене | 4:5 |
| 03 | TAG | бирка крупным планом | 1:1 |
| 04 | MODEL_FRONT | на модели спереди | 4:5 |
| 05 | MODEL_BACK | на модели сзади | 4:5 |

## Главный пересмотр после повторного анализа
Раньше фоном считался шкаф / curtain scene. Это неверно для текущего рабочего подхода.

**Правильная сцена для футболок — балконная зона из реальных фото.**

Это теперь официальный scene template для t-shirt задач:
- белое окно / дверной проём
- открытая створка / ручка
- зелёный балконный пол / turf снаружи
- белый радиатор
- чёрная лестница
- большое зелёное растение в горшке
- маленькие предметы на подоконнике
- край деревянного стола справа
- тёмно-зелёная штора справа

Важно: **ни одна деталь сцены не должна меняться**, если пользователь отдельно не попросил.

## Дизайн товара

### База
- цвет: белый
- тип: oversized cotton crew-neck
- ткань: плотный матовый хлопок
- ворот: ribbed crew neck

### FRONT print
Источник истины: `01_print_FRONT_design.jpg`

Это не текст, который нужно заново набирать.
Это **готовый графический asset**, который нужно перенести на футболку визуально 1-в-1.

Правила:
- не менять буквы
- не менять композицию
- не менять толщину линий
- не менять strike-through
- не менять встроенный CC-элемент
- допускается только естественное искажение по складкам ткани

### BACK print
Источник истины: `03_layout_BACK_mockup.jpg`

Нужно сохранить:
- вертикальную форму
- композицию
- пропорции
- расположение на спине
- нижний логотип-элемент
- общее ощущение того же back graphic

## Источники для сцены

### Футболка в сцене
- `04_reference_REAL_tshirt_FRONT_on_balcony.jpg`
- `05_reference_REAL_tshirt_BACK_on_balcony.jpg`
- `06_reference_REAL_tshirt_CLOSEUP.jpg`

### Чистые balcony references без футболки
- `09_reference_BALCONY_master_wide.jpg`
- `10_reference_BALCONY_angle_left.jpg`
- `11_reference_BALCONY_angle_center.jpg`
- `12_reference_BALCONY_angle_reflections.jpg`
- `13_reference_BALCONY_angle_right.jpg`

Эти изображения нужны не как вдохновение, а как **scene lock**.

## Модель
Оставляем типаж как у референсов Avito:
- молодой парень
- худощавое атлетическое телосложение
- тёмные волосы
- нейтральная подача
- без гламура

## Как теперь должна проходить работа
1. Для каждой картинки используется **полноценный отдельный промпт**
2. В модель грузятся:
   - front/back print reference
   - garment placement reference
   - real garment scene references
   - balcony template references
   - model references (для model shots)
3. В промпте явно зафиксировано:
   - print = graphic transfer, not text rendering
   - balcony = locked real scene
   - no object replacement
   - no detail change
4. Если модель всё равно меняет текст бирки или печать — добиваем Photopea

## Главные риски
1. Модель может всё ещё пытаться "перерисовать" front print как текст
2. Модель может слегка упрощать back graphic
3. Модель может менять мелкие детали balcony scene если prompt слишком мягкий
4. На tag shot текст может быть с гибберишем

Из-за этого в новых промптах усилены:
- graphic-transfer wording
- locked-scene wording
- no-detail-change wording
