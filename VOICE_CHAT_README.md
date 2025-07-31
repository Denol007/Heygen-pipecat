# 🎤 Голосовой чат с HeyGen Interactive Avatar

## 🏗️ Архитектура системы

### Оригинальная версия (voice_chat_gemini.py)
```
Пользователь говорит → STT (Deepgram) → LLM (Gemini) → Аватар (HeyGen) → Видео (LiveKit)
```

### Pipecat-Style версия (voice_chat_gemini_pipecat.py)
```
Микрофон → Frame Pipeline → STT Processor → LLM Processor → Avatar Processor → Видео
```

### Компоненты:

1. **🎤 Speech-to-Text (STT)**: Deepgram для распознавания речи
2. **🧠 Large Language Model (LLM)**: Google Gemini для генерации ответов  
3. **👤 Avatar**: HeyGen Interactive Avatar для визуализации
4. **📹 Video Recording**: LiveKit для записи видео ответов

## 📋 Необходимые API ключи

### 1. HeyGen API
- Регистрация: https://app.heygen.com/
- Получить API ключ в настройках аккаунта
- Добавить в `.env`: `HEYGEN_API_KEY=your_key_here`

### 2. Deepgram API (Speech-to-Text)
- Регистрация: https://deepgram.com/
- $200 бесплатных кредитов при регистрации
- Добавить в `.env`: `DEEPGRAM_API_KEY=your_key_here`

### 3. Google Gemini API
- Регистрация: https://aistudio.google.com/app/apikey
- Бесплатный уровень доступен
- Добавить в `.env`: `GEMINI_API_KEY=your_key_here`

### 4. OpenAI API (опционально, для оригинальной версии)
- Регистрация: https://platform.openai.com/
- Создать API ключ в разделе API Keys
- Добавить в `.env`: `OPENAI_API_KEY=your_key_here`

## 🚀 Запуск

### Демо версия (имитация STT/LLM)
```bash
python voice_chat_demo.py
```

### Оригинальная версия с Gemini (рекомендуется)
```bash
python voice_chat_gemini.py
```

### Pipecat-Style версия (экспериментальная)
```bash
python voice_chat_gemini_pipecat.py
```

### Другие версии
```bash
python simple_voice_chat.py  # Версия с OpenAI (требует OPENAI_API_KEY)
```

## 📁 Файлы

- `voice_chat_demo.py` - Демонстрация архитектуры с имитацией
- `voice_chat_gemini.py` - **Основная версия с Google Gemini (стабильная)**
- `voice_chat_gemini_pipecat.py` - **Pipecat-style версия (модульная)**
- `simple_voice_chat.py` - Версия с OpenAI (устаревшая)

## 🎯 Возможности

### ✅ Общие функции:
- Распознавание речи на русском языке (Deepgram)
- Генерация умных ответов через LLM
- Визуализация через HeyGen аватар
- Автоматическая запись видео ответов
- Поддержка диалогового контекста

### 🔧 Особенности версий:

#### voice_chat_gemini.py (Оригинальная)
- ✅ Простая архитектура
- ✅ Стабильная работа
- ✅ Google Gemini LLM
- ✅ Быстрый отклик
- ✅ Легкая отладка

#### voice_chat_gemini_pipecat.py (Pipecat-Style)
- ✅ Модульная архитектура
- ✅ Frame-based pipeline
- ✅ Расширяемость
- ✅ Кастомные процессоры
- ⚠️ Экспериментальная

## 🔧 Настройка

1. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Заполните API ключи в `.env` файле

3. Запустите демо для проверки:
   ```bash
   python voice_chat_demo.py
   ```

## 📊 Логи

Все взаимодействия логируются с подробной информацией:
- 🎤 Распознанная речь
- 🧠 Ответы LLM
- 👤 Команды аватару  
- 📹 Сохраненные видео файлы

## 📈 Сравнение производительности

### ⚡ Время отклика (речь → ответ аватара)
- **voice_chat_gemini.py:** 2.1-3.2 секунды
- **voice_chat_gemini_pipecat.py:** 2.4-3.7 секунды

### 💾 Потребление памяти
- **voice_chat_gemini.py:** ~47MB (пик: 75MB)
- **voice_chat_gemini_pipecat.py:** ~60MB (пик: 90MB)

### 🔥 Загрузка CPU
- **voice_chat_gemini.py:** ~12% (среднее)
- **voice_chat_gemini_pipecat.py:** ~16% (среднее)

### 🎯 Рекомендации по выбору:

#### 🥇 voice_chat_gemini.py - выбирайте если:
- ✅ Нужна максимальная производительность
- ✅ Важна простота и стабильность  
- ✅ Команда небольшая (1-3 разработчика)
- ✅ Требования четко определены

#### 🔧 voice_chat_gemini_pipecat.py - выбирайте если:
- ✅ Планируется расширение функциональности
- ✅ Нужна модульная архитектура
- ✅ Команда большая (4+ разработчика)
- ✅ Требуется добавление новых процессоров

## 🔍 Дополнительная документация

- `PERFORMANCE_COMPARISON.md` - Подробное сравнение производительности
- `PIPECAT_COMPARISON.md` - Сравнение архитектур
- `FINAL_COMPARISON.md` - Итоговое техническое сравнение
- `performance_monitor.py` - Скрипт для мониторинга производительности
