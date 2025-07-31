# 🚀 Быстрый запуск HeyGen Avatar Chat

## ⚡ За 5 минут к работающему чату

### 1. Скачивание и установка (2 мин)

```bash
# Клонируем репозиторий
git clone <repository-url>
cd heygen-interactive-avatar-chat

# Создаем виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. API ключи (2 мин)

```bash
# Копируем пример конфигурации
cp .env.example .env

# Редактируем файл .env
nano .env  # или любой текстовый редактор
```

**Минимально необходимые ключи:**
```bash
HEYGEN_API_KEY=your_heygen_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key_here  
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Системные зависимости (1 мин)

**macOS:**
```bash
brew install ffmpeg portaudio
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg portaudio19-dev
```

**Windows:**
- Скачайте FFmpeg с https://ffmpeg.org/download.html
- Добавьте в PATH

### 4. Запуск! 🎉

```bash
python voice_chat_gemini.py
```

**Увидите:**
```
🤖 HeyGen Voice Chat with Gemini
==================================================
📋 Компоненты:
   🎤 STT: Deepgram (реальный)
   🧠 LLM: Google Gemini (реальный)
   👤 Avatar: HeyGen Interactive
   📹 Video: LiveKit запись + аудио
==================================================
🎤 Говорите в микрофон... (Ctrl+C для остановки)
```

---

## 📋 Получение API ключей

### HeyGen API Key
1. Зайдите на https://app.heygen.com/
2. Создайте аккаунт или войдите
3. Перейдите в Settings → API Keys
4. Создайте новый ключ

### Deepgram API Key  
1. Зайдите на https://console.deepgram.com/
2. Зарегистрируйтесь
3. Получите $200 бесплатных кредитов
4. Скопируйте API ключ из Dashboard

### Google Gemini API Key
1. Зайдите на https://makersuite.google.com/app/apikey
2. Войдите через Google аккаунт
3. Нажмите "Create API Key"
4. Скопируйте ключ

---

## 🐛 Решение проблем

### ❌ "ModuleNotFoundError: No module named 'pyaudio'"
```bash
# macOS
brew install portaudio
pip install pyaudio

# Ubuntu  
sudo apt install portaudio19-dev
pip install pyaudio

# Windows
pip install pipwin
pipwin install pyaudio
```

### ❌ "ffmpeg not found"
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows - скачайте с https://ffmpeg.org/
```

### ❌ "Microphone access denied"
- **macOS**: System Preferences → Security & Privacy → Microphone → разрешите доступ для Terminal
- **Windows**: Settings → Privacy → Microphone → разрешите доступ

### ❌ "API key invalid"
- Проверьте правильность копирования ключей в .env
- Убедитесь что нет лишних пробелов
- Проверьте квоты на соответствующих платформах

---

## 📹 Результат

После успешного запуска вы получите:
- **Распознавание речи** с микрофона в реальном времени
- **Ответы AI** на русском языке через Gemini
- **Видео файлы** с аватаром в папке `outputs/`
- **Непрерывную запись** всей сессии в одном MP4

**Пример файла результата:**
```
outputs/avatar_response_20250731_183905_session_5bf4e1f2-6e24-11f0-8b5a-1e5f151a7552.mp4
```

---

**🎉 Готово! Теперь вы можете общаться с AI аватаром голосом!**
