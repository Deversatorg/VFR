# VFR (Virtual Fitting Room) - AI Context & Architecture

## 1. Project Overview
Мы разрабатываем B2B/B2C SaaS платформу для виртуальной примерки одежды (AI Fashion Tech стартап).
Система генерирует 3D-аватары пользователей на основе их параметров (рост, вес) и позволяет примирять 3D-одежду, сгенерированную из 2D-фотографий брендов.

## 2. Tech Stack
Проект разделен на изолированные микросервисы:
- **Frontend:** React, React Three Fiber (R3F), Three.js, `@react-three/drei`.
- **Main Backend:** .NET Aspire, C#, PostgreSQL (Авторизация, бизнес-логика, управление каталогом).
- **AI Engine:** Python, FastAPI, Celery, Redis. Библиотеки: `smplx`, `trimesh`, `pygltflib`, `rembg`, `scipy`.
- **Storage:** S3 Object Storage (MinIO локально / AWS S3 в проде).

## 3. Core Architecture Rules (CRITICAL!)
Агенты ИИ обязаны строго соблюдать эти правила при написании кода:

1. **Client-Side Assembly ONLY:** Сервер НИКОГДА не склеивает тело и одежду в один файл. Сервер отдает две независимые ссылки (URL) на `.glb` файлы. Вся сборка (Bone Skinning, перенос весов) происходит строго в браузере клиента силами React Three Fiber.
2. **Stateless AI Engine:** Python-сервер ничего не знает про базу данных PostgreSQL. Он получает команду по сети, генерирует 3D-модель, сохраняет её в S3 и возвращает ссылку (URL) обратно в .NET.
3. **Draco Compression:** Все `.glb` файлы (тела и одежда) должны сжиматься алгоритмом Google Draco перед сохранением на диск, чтобы весить < 500 KB.
4. **Smart Templates (Одежда):** Мы не требуем 3D-модели от брендов. Мы берем заготовленные белые "зариганные" (Rigged) шаблоны `.glb`, программно (через `pygltflib` в Python) заменяем в них текстуру на вырезанную из 2D-фото (через `rembg`), сохраняя при этом все кости и веса.

## 4. Current Pipelines (Как это работает)

### Pipeline A: Avatar Generation (`vfr_ai_engine/avatar/pipeline.py`)
- **Вход:** Рост (см), Вес (кг), Тип телосложения.
- **Логика:** Конвертация параметров в Индекс Массы Тела (BMI) -> маппинг в 10 параметров `betas` для SMPL-X.
- **Движок:** Модель `SMPLX_NEUTRAL.npz`. Генерация вершин, применение костей (Rigging), поворот по оси X на 180 градусов (чтобы стоял ровно).
- **Выход:** Файл `user_{uuid}_body.glb` загружается в S3.

### Pipeline B: Garment Generation (`vfr_ai_engine/garments/pipeline.py`)
- **Вход:** 2D-фото одежды, категория (например, "t-shirt").
- **Логика:** Удаление фона -> создание UV-текстуры -> инъекция текстуры в нужный Smart Template.
- **Выход:** Зариганный файл `brand_shirt_123.glb` загружается в S3.

## 5. Current State & Focus
- Фронтенд успешно рендерит модели.
- **Текущая задача:** Логика генерации SMPL-X (BMI to Betas) живет в `vfr_ai_engine/avatar/pipeline.py`; measurement math вынесена в `vfr_ai_engine/measurements/`.
- **Запрещено:** Использовать старые модели "Xbot" или пытаться найти в интернете случайные не-зариганные `.fbx` файлы.
