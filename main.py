#!/usr/bin/env python3
"""
HeyGen Interactive Avatar Console Chat

Консольное приложение для лайв-разговора с HeyGen Interactive Avatar.
Использует Pipecat для обработки потоков и HeyGen API для управления аватаром.

Автор: Avatar Chat Team
Дата: 2025-07-31
"""

import asyncio
import sys
import logging
from console.chat_interface import main

def setup_logging():
    """Настройка системы логирования"""
    logging.basicConfig(
        level=logging.DEBUG,  # Изменено на DEBUG для более подробных логов
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('avatar_chat.log', encoding='utf-8')
        ]
    )

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        sys.exit(1)

def print_startup_info():
    """Вывод информации о запуске"""
    print("🚀 Запуск HeyGen Interactive Avatar Console Chat...")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("📝 Логи сохраняются в: avatar_chat.log")
    print()

if __name__ == "__main__":
    # Проверки перед запуском
    check_python_version()
    setup_logging()
    print_startup_info()
    
    try:
        # Запуск основного приложения
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка при запуске: {e}")
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
