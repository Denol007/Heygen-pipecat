#!/bin/bash

echo "🎬 HeyGen Interactive Avatar Console Chat - Демонстрация"
echo "========================================================"
echo ""

# Проверка виртуального окружения
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Виртуальное окружение активно: $(basename $VIRTUAL_ENV)"
else
    echo "⚠️  Активация виртуального окружения..."
    source venv/bin/activate
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        echo "✅ Виртуальное окружение активировано: $(basename $VIRTUAL_ENV)"
    else
        echo "❌ Не удалось активировать виртуальное окружение"
        exit 1
    fi
fi

echo ""
echo "🔍 Проверка структуры проекта:"
echo "------------------------------"

files_to_check=(
    "main.py"
    "heygen/config.py"
    "heygen/session_manager.py"
    "console/chat_interface.py"
    "pipecat_integration/heygen_processor.py"
    "pipecat_integration/stream_recorder.py"
    ".env"
    "outputs/"
)

for file in "${files_to_check[@]}"; do
    if [[ -e "$file" ]]; then
        if [[ -d "$file" ]]; then
            echo "📁 $file - OK"
        else
            echo "📄 $file - OK"
        fi
    else
        echo "❌ $file - ОТСУТСТВУЕТ"
    fi
done

echo ""
echo "🧪 Запуск тестирования компонентов:"
echo "-----------------------------------"
python test_components.py

echo ""
echo "📋 Следующие шаги для использования:"
echo "======================================"
echo ""
echo "1. 🔑 Настройте API ключ HeyGen:"
echo "   Откройте файл .env и замените 'your_heygen_api_key_here'"
echo "   на ваш реальный API ключ от HeyGen"
echo ""
echo "2. 🚀 Запустите приложение:"
echo "   python main.py"
echo "   или"
echo "   python run.py (с дополнительными проверками)"
echo ""
echo "3. 💬 Используйте команды в чате:"
echo "   /help      - справка"
echo "   /avatars   - список аватаров"
echo "   /status    - статус сессии"
echo "   /outputs   - сохраненные видео"
echo "   /interrupt - прервать речь"
echo "   /quit      - выйти"
echo ""
echo "4. 📱 Отправка сообщений:"
echo "   Просто введите текст и нажмите Enter"
echo "   Аватар произнесет его и видео сохранится в outputs/"
echo ""
echo "📚 Полную документацию смотрите в README.md"
echo ""
