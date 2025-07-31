# 📁 Структура проекта - Подробное описание файлов

## 🎯 Главные исполняемые файлы

### `voice_chat_gemini.py` ⭐ **[ОСНОВНОЙ ФАЙЛ]**
**Статус**: ✅ Актуальная версия  
**Описание**: Полная система голосового чата с аватаром  
**Компоненты**:
- 🎤 Реальный микрофон (PyAudio)
- 🔊 Deepgram STT (распознавание речи)
- 🧠 Google Gemini LLM (генерация ответов)
- 👤 HeyGen Interactive Avatar
- 📹 Непрерывная запись всей сессии (LiveKit + FFmpeg)

**Запуск**: `python voice_chat_gemini.py`

### `voice_chat_demo.py` 
**Статус**: ✅ Демо версия  
**Описание**: Демонстрационная версия с 4 тестовыми сценариями  
**Особенности**:
- Предустановленные тестовые сообщения
- Отдельные видео для каждого ответа
- Полная интеграция всех компонентов

**Запуск**: `python voice_chat_demo.py`

### `simple_voice_chat.py`
**Статус**: ⚠️ Устарела  
**Описание**: Простая версия с OpenAI (проблемы с квотой)  
**Проблема**: OpenAI API quota exceeded

### `main.py`
**Статус**: 🔄 В разработке  
**Описание**: Запуск через консольный интерфейс  
**Планы**: Будущий UI интерфейс

---

## 🏗️ Основные модули

### `heygen/` - HeyGen API интеграция

#### `heygen/session_manager.py`
**Функция**: Управление сессиями HeyGen аватаров  
**Ключевые методы**:
- `create_session()` - Создание новой сессии
- `start_session()` - Запуск сессии  
- `send_task()` - Отправка текста аватару
- `close_session()` - Закрытие сессии
- `get_available_avatars()` - Список аватаров

**Endpoints**:
- `POST /v1/streaming/create_session`
- `POST /v1/streaming/start_session`
- `POST /v1/streaming/send_task`
- `POST /v1/streaming/close_session`

#### `heygen/config.py`
**Функция**: Конфигурация и настройки по умолчанию  
**Константы**:
```python
DEFAULT_AVATAR_ID = "default"
DEFAULT_QUALITY = "medium"
DEFAULT_VOICE_RATE = 1.0
HEYGEN_BASE_URL = "https://api.heygen.com/v1"
```

### `pipecat_integration/` - Обработка потоков и запись

#### `pipecat_integration/livekit_client.py` ⭐ **[КЛЮЧЕВОЙ МОДУЛЬ]**
**Функция**: LiveKit клиент для записи видео и аудио  
**Возможности**:
- WebRTC подключение к HeyGen
- Непрерывная запись видео (VP8, 1280x720)
- Захват аудио (WAV, 48kHz)  
- FFmpeg объединение видео + аудио
- Сохранение в MP4 формат

**Ключевые методы**:
- `connect()` - Подключение к LiveKit room
- `start_recording()` - Начало записи
- `stop_recording()` - Остановка и сохранение
- `_merge_video_audio_with_ffmpeg()` - Объединение треков

#### `pipecat_integration/heygen_processor.py`
**Функция**: Обработчик потоков HeyGen  
**Роль**: Интеграция с Pipecat framework

#### `pipecat_integration/stream_recorder.py`
**Функция**: Запись потоков данных  
**Роль**: Вспомогательный модуль для записи

#### `pipecat_integration/webrtc_client.py`
**Функция**: WebRTC клиент  
**Роль**: Альтернативный WebRTC интерфейс

### `console/` - Пользовательский интерфейс

#### `console/chat_interface.py`
**Функция**: Консольный интерфейс для взаимодействия  
**Статус**: 🔄 В разработке для main.py

### `utils/` - Утилиты

#### `utils/video_audio_merge.py`
**Функция**: Объединение видео и аудио файлов  
**Технологии**: FFmpeg integration

---

## 📋 Конфигурационные файлы

### `.env.example`
**Функция**: Пример конфигурации API ключей  
**Содержимое**:
```bash
HEYGEN_API_KEY=your_heygen_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
DEFAULT_AVATAR_ID=default
DEFAULT_QUALITY=medium
OUTPUT_DIR=outputs
```

### `.env`
**Функция**: Реальные API ключи (в .gitignore)  
**Статус**: 🔒 Приватный файл

### `requirements.txt`
**Функция**: Python зависимости  
**Ключевые библиотеки**:
- `pipecat-ai` - Framework обработки потоков
- `livekit` - WebRTC и запись
- `deepgram-sdk` - Speech-to-Text
- `google-generativeai` - Gemini LLM
- `pyaudio` - Микрофон
- `ffmpeg-python` - Видео обработка

---

## 🧪 Тестовые и вспомогательные файлы

### `test_components.py`
**Функция**: Тестирование компонентов системы  
**Тесты**:
- HeyGen API подключение
- Deepgram STT
- Gemini LLM
- LiveKit соединение

### `run.py`
**Функция**: Альтернативный файл запуска  
**Статус**: 🔄 Экспериментальный

### `voice_chat.py`
**Функция**: Базовая версия голосового чата  
**Статус**: 📚 Архивная версия

---

## 📁 Директории

### `outputs/`
**Функция**: Выходные файлы (видео записи)  
**Содержимое**:
```
📁 outputs/
├── 📄 README.md
├── 🎬 avatar_response_20250731_183905_session_xxx.mp4  # Полная сессия
├── 🎬 avatar_response_20250731_183355_voice_task_xxx.mp4  # Отдельные ответы
└── 📊 *.wav  # Промежуточные аудио файлы
```

**Форматы**:
- **Полная сессия**: `session_[session_id].mp4` (новая система)
- **Отдельные ответы**: `voice_task_[timestamp].mp4` (старая система)

### `venv/`
**Функция**: Python виртуальное окружение  
**Статус**: 🚫 В .gitignore

### `__pycache__/`
**Функция**: Python compiled files  
**Статус**: 🚫 В .gitignore

---

## 📚 Документация

### `README.md` ⭐ **[ГЛАВНАЯ ДОКУМЕНТАЦИЯ]**
**Содержимое**:
- Обзор проекта и архитектуры
- Инструкции по установке
- Описание API endpoints
- Руководство по использованию
- Решение проблем

### `QUICK_START.md`
**Содержимое**: Быстрый запуск за 5 минут

### `API_ENDPOINTS.md`
**Содержимое**: Полный справочник по всем API

### `ARCHITECTURE.md`  
**Содержимое**: Подробное описание архитектуры системы

### `PROJECT_STRUCTURE.md` (этот файл)
**Содержимое**: Описание каждого файла в проекте

### `VOICE_CHAT_README.md`
**Статус**: 📚 Архивная документация

---

## 🛠️ Служебные файлы

### `.gitignore`
**Функция**: Исключения для Git  
**Исключает**:
```
.env
venv/
__pycache__/
*.log
outputs/*.mp4
outputs/*.wav
```

### `install.sh`
**Функция**: Скрипт автоматической установки  
**Действия**:
- Создание venv
- Установка зависимостей
- Проверка FFmpeg

### `demo.sh`
**Функция**: Скрипт запуска демо  

### `avatar_chat.log`
**Функция**: Лог файл приложения  
**Содержимое**: Подробные логи работы системы

---

## 📊 Статистика проекта

### 📈 Размер кодовой базы
- **Основной код**: ~1,500 строк Python
- **Документация**: ~2,000 строк Markdown  
- **Конфигурация**: ~100 строк

### 🧩 Архитектурные компоненты
- **6 основных модулей**
- **4 API интеграции** (HeyGen, Deepgram, Gemini, LiveKit)
- **3 уровня обработки** (Audio → Text → Avatar)
- **2 режима записи** (Непрерывная + Индивидуальная)

### 📦 Зависимости
- **15+ Python библиотек**
- **4 системные зависимости** (FFmpeg, PortAudio, etc.)
- **3 внешних API сервиса**

---

## 🎯 Точки входа в систему

### Для пользователей:
1. **`python voice_chat_gemini.py`** - Полная система с микрофоном
2. **`python voice_chat_demo.py`** - Демо с тестовыми сценариями

### Для разработчиков:
1. **`python test_components.py`** - Тестирование компонентов
2. **`python main.py`** - Консольный интерфейс (в разработке)

### Для изучения:
1. **`README.md`** - Начните здесь
2. **`QUICK_START.md`** - Быстрый старт
3. **`ARCHITECTURE.md`** - Глубокое понимание
4. **`API_ENDPOINTS.md`** - Справочник по API

---

**🎉 Проект готов к использованию и расширению!**
- `.env` - Файл с настройками и API ключами
- `.env.example` - Пример конфигурационного файла
- `requirements.txt` - Список зависимостей Python

### 📚 Документация
- `README.md` - Подробная документация проекта
- `PROJECT_STRUCTURE.md` - Этот файл со структурой проекта

### 🛠️ Скрипты установки и демо
- `install.sh` - Автоматическая установка проекта
- `demo.sh` - Демонстрация функций проекта

### 📄 Служебные файлы
- `.gitignore` - Исключения для Git
- `avatar_chat.log` - Файл логов (создается при запуске)

## 📂 Модули проекта

### heygen/ - Интеграция с HeyGen API
```
heygen/
├── __init__.py              # Инициализация модуля
├── config.py                # Конфигурация и настройки
└── session_manager.py       # Управление HeyGen сессиями
```

**config.py**
- Загрузка настроек из .env файла
- Валидация обязательных параметров
- Конфигурация по умолчанию

**session_manager.py**
- Создание и управление streaming сессиями
- API методы: new, start, stop, task, interrupt, keep_alive
- Автоматическое закрытие существующих сессий
- Обработка ошибок API

### console/ - Консольный интерфейс
```
console/
├── __init__.py              # Инициализация модуля
└── chat_interface.py        # Основной интерфейс чата
```

**chat_interface.py**
- Консольное меню и команды
- Обработка пользовательского ввода
- Управление сессией и состоянием
- Интеграция с frame processor
- Keep-alive механизм

### pipecat_integration/ - Интеграция с Pipecat
```
pipecat_integration/
├── __init__.py              # Инициализация модуля
├── heygen_processor.py      # Pipecat Frame Processor
└── stream_recorder.py       # Запись видео потоков
```

**heygen_processor.py**
- Pipecat Frame Processor для HeyGen
- Обработка текстовых задач с записью видео
- Управление состоянием обработки
- Интеграция audio/video frames (для будущего)
- Мост между Pipecat и HeyGen

**stream_recorder.py**
- Запись WebSocket/WebRTC потоков
- Управление видео файлами
- WebSocket handler для LiveKit
- Эмуляция записи (для тестирования)

### outputs/ - Выходные файлы
```
outputs/
├── README.md                # Описание папки
└── [video files]            # Сохраненные видео ответы аватара
```

## 🔄 Workflow приложения

### 1. Инициализация
```
main.py → console/chat_interface.py → heygen/config.py
```

### 2. Создание сессии
```
console/chat_interface.py → heygen/session_manager.py → HeyGen API
```

### 3. Обработка сообщений
```
User Input → console/chat_interface.py → 
pipecat_integration/heygen_processor.py → 
heygen/session_manager.py → HeyGen API →
pipecat_integration/stream_recorder.py → Video File
```

### 4. Команды
```
/help, /avatars, /status, /outputs, /interrupt, /quit →
console/chat_interface.py → Various handlers
```

## 🔧 Ключевые классы и методы

### HeyGenSessionManager
```python
- create_session()           # Создание новой сессии
- start_session()            # Запуск сессии
- send_task()                # Отправка задач аватару
- interrupt_task()           # Прерывание речи
- keep_alive()               # Поддержание сессии
- close_session()            # Закрытие сессии
- close_all_active_sessions() # Закрытие всех сессий
```

### HeyGenFrameProcessor
```python
- initialize()               # Инициализация процессора
- process_text_task()        # Обработка текста с записью
- interrupt_current_task()   # Прерывание текущей задачи
- get_processing_status()    # Статус обработки
```

### StreamRecorder
```python
- start_recording()          # Начало записи
- add_frame()                # Добавление кадра
- stop_recording()           # Остановка записи
- generate_filename()        # Генерация имени файла
```

### ConsoleAvatarChat
```python
- initialize_session()       # Инициализация сессии
- send_message_to_avatar()   # Отправка сообщения
- process_command()          # Обработка команд
- chat_loop()                # Основной цикл чата
```

## 🚀 Как запустить

### Быстрый старт
```bash
./install.sh                # Автоматическая установка
# Настройте .env файл с API ключом
python main.py               # Запуск
```

### Ручная установка
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Настройте .env файл
python main.py
```

### Тестирование
```bash
python test_components.py   # Тест всех компонентов
./demo.sh                   # Демонстрация проекта
```

## 📊 Размер проекта

- **Всего файлов**: ~15
- **Строк кода**: ~1500+
- **Модулей Python**: 8
- **Зависимостей**: 8

## 🎯 Готовые функции

- ✅ Создание и управление HeyGen сессиями
- ✅ Консольный интерфейс с командами
- ✅ Запись видео ответов (эмуляция)
- ✅ Единственная активная сессия
- ✅ Прерывание речи аватара
- ✅ Keep-alive механизм
- ✅ Обработка ошибок
- ✅ Логирование
- ✅ Конфигурация через .env

## 🔮 Для будущего развития

- [ ] Реальная WebRTC запись через LiveKit
- [ ] STT интеграция для голосового ввода
- [ ] Полная Pipecat pipeline интеграция
- [ ] GUI интерфейс
- [ ] Поддержка множественных аватаров
- [ ] Chat mode с AI диалогами

---

**Проект готов к использованию! 🚀**
