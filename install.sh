#!/bin/bash

echo "🚀 Установка HeyGen Interactive Avatar Console Chat"
echo "=================================================="

# Проверка Python версии
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version (требуется $required_version+)"
else
    echo "❌ Требуется Python $required_version или выше. Текущая версия: $python_version"
    exit 1
fi

# Создание виртуального окружения
echo "📦 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
echo "⬇️  Установка зависимостей..."
pip install --upgrade pip
pip install -r requirements.txt

# Проверка установки
echo "🔍 Проверка установки..."
python -c "import aiohttp, cv2, numpy; print('✅ Основные зависимости установлены')"

# Настройка конфигурации
if [ ! -f ".env" ]; then
    echo "⚙️  Создание конфигурационного файла..."
    cp .env.example .env
    echo "📝 Отредактируйте файл .env и добавьте ваш API ключ HeyGen"
fi

# Создание папки outputs
mkdir -p outputs

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Активируйте виртуальное окружение: source venv/bin/activate"
echo "2. Отредактируйте .env файл и добавьте ваш HeyGen API ключ"
echo "3. Запустите приложение: python main.py"
echo ""
echo "📚 Для получения HeyGen API ключа:"
echo "   Перейдите на https://app.heygen.com/settings/api"
echo ""
