#!/usr/bin/env python3
"""
Финальный скрипт запуска с предварительными проверками
HeyGen Interactive Avatar Console Chat
"""

import sys
import os
import asyncio
import logging

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    return True

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        'aiohttp',
        'asyncio',
        'logging',
        'datetime',
        'os',
        'sys'
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Отсутствуют пакеты: {', '.join(missing)}")
        print("📦 Запустите: pip install -r requirements.txt")
        return False
    
    print("✅ Основные зависимости установлены")
    return True

def check_config():
    """Проверка конфигурации"""
    print("⚙️ Проверка конфигурации...")
    
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден")
        print("📝 Скопируйте .env.example в .env и настройте API ключ")
        return False
    
    # Проверяем наличие API ключа
    with open('.env', 'r') as f:
        content = f.read()
        if 'your_heygen_api_key_here' in content:
            print("❌ API ключ HeyGen не настроен в .env файле")
            print("🔑 Замените 'your_heygen_api_key_here' на ваш реальный API ключ")
            return False
    
    print("✅ Конфигурация найдена")
    return True

def check_output_directory():
    """Проверка папки для выходных файлов"""
    output_dir = 'outputs'
    
    if not os.path.exists(output_dir):
        print(f"📁 Создание папки {output_dir}...")
        os.makedirs(output_dir, exist_ok=True)
    
    if not os.access(output_dir, os.W_OK):
        print(f"❌ Нет прав записи в папку {output_dir}")
        return False
    
    print(f"✅ Папка {output_dir} готова")
    return True

def run_quick_test():
    """Быстрый тест основных компонентов"""
    print("🧪 Быстрый тест компонентов...")
    
    try:
        # Тестируем импорты основных модулей
        from heygen.config import Config
        from heygen.session_manager import HeyGenSessionManager
        
        # Проверяем конфигурацию
        Config.validate()
        
        print("✅ Основные компоненты работают")
        return True
    except Exception as e:
        print(f"❌ Ошибка в компонентах: {e}")
        return False

async def main():
    """Главная функция с проверками"""
    print("🚀 HeyGen Interactive Avatar Console Chat")
    print("=" * 50)
    print("Запуск предварительных проверок...")
    print()
    
    # Запуск всех проверок
    checks = [
        ("Python версия", check_python_version),
        ("Зависимости", check_dependencies),
        ("Конфигурация", check_config),
        ("Папка outputs", check_output_directory),
        ("Компоненты", run_quick_test)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"🔄 {check_name}...")
        result = check_func()
        
        if not result:
            all_passed = False
            print(f"❌ {check_name} - ПРОВАЛЕН")
            break
        else:
            print(f"✅ {check_name} - ОК")
    
    print()
    
    if not all_passed:
        print("❌ Предварительные проверки провалились!")
        print("🔧 Исправьте ошибки выше и запустите снова")
        return False
    
    print("🎉 Все проверки прошли успешно!")
    print("🚀 Запуск основного приложения...")
    print()
    
    # Запуск основного приложения
    try:
        from console.chat_interface import main as chat_main
        await chat_main()
        return True
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
        return True
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        print(f"\n💥 Критическая ошибка: {e}")
        return False

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('avatar_chat.log', encoding='utf-8')
        ]
    )
    
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Фатальная ошибка: {e}")
        sys.exit(1)
