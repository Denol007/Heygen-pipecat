import asyncio
import logging
import sys
import os
from typing import Optional
from datetime import datetime
from heygen.session_manager import HeyGenSessionManager
from heygen.config import Config
from pipecat_integration.heygen_processor import HeyGenFrameProcessor

logger = logging.getLogger(__name__)

class ConsoleAvatarChat:
    """Консольный интерфейс для общения с аватаром"""
    
    def __init__(self):
        self.session_manager = HeyGenSessionManager()
        self.frame_processor = HeyGenFrameProcessor(self.session_manager)
        self.current_session_id = None
        self.keep_alive_task = None
        self.is_running = False
        self.session_active = False
    
    def print_welcome(self):
        """Показать приветствие"""
        print("\n" + "="*60)
        print("🤖 HeyGen Interactive Avatar Console Chat")
        print("="*60)
        print("  /help     - показать помощь")
        print("  /avatars  - показать список аватаров")
        print("  /quit     - выйти")
        print("\n💡 Для начала работы будет создана новая сессия...")
    
    def print_help(self):
        """Показать справку"""
        print("\n📋 Справка по командам:")
        print("  /help     - показать эту справку")
        print("  /start    - создать новую сессию с аватаром")
        print("  /cleanup  - закрыть все активные сессии")
        print("  /status   - проверить статус API и текущей сессии")
        print("  /stop     - закрыть текущую сессию")
        print("  /quit     - выйти")
        print("\n💬 Для отправки сообщения аватару просто введите текст")
    
    async def cleanup_sessions(self):
        """Закрыть все активные сессии"""
        print("\n🧹 Закрытие всех активных сессий...")
        
        try:
            # Получаем список активных сессий
            active_sessions = await self.session_manager.list_active_sessions()
            
            if not active_sessions:
                print("✅ Нет активных сессий")
                return
            
            print(f"🔍 Найдено активных сессий: {len(active_sessions)}")
            
            # Закрываем все сессии
            success = await self.session_manager.close_all_active_sessions()
            
            if success:
                print("✅ Все сессии успешно закрыты")
            else:
                print("⚠️ Не все сессии удалось закрыть")
                
        except Exception as e:
            logger.error(f"Ошибка при закрытии сессий: {e}")
            print(f"❌ Ошибка при закрытии сессий: {e}")

    async def start_session(self):
        """Создать и активировать сессию для работы"""
        if self.session_active:
            print("⚠️ Сессия уже активна. Используйте /stop для закрытия текущей сессии.")
            return False
            
        print("\n� Создание рабочей сессии...")
        
        try:
            # Сначала очищаем любые зависшие сессии
            await self.session_manager.close_all_active_sessions()
            
            # Создаем новую сессию
            if await self.session_manager.create_session():
                print(f"✅ Сессия создана: {self.session_manager.session_id}")
                
                # Запускаем сессию
                print("🔄 Активация сессии...")
                if await self.session_manager.start_session():
                    self.session_active = True
                    self.current_session_id = self.session_manager.session_id
                    print("✅ Сессия активирована!")
                    print(f"⏱️  Лимит времени: {self.session_manager.session_duration_limit}s")
                    print("\n🎉 Теперь можете отправлять сообщения аватару!")
                    return True
                else:
                    print("❌ Не удалось активировать сессию")
                    await self.session_manager.close_session()
                    self.session_active = False
                    return False
            else:
                print("❌ Не удалось создать сессию")
                self.session_active = False
                return False
                
        except Exception as e:
            logger.error(f"Ошибка создания сессии: {e}")
            print(f"❌ Ошибка: {e}")
            return False

    async def stop_session(self):
        """Закрыть текущую рабочую сессию"""
        if not self.session_active:
            print("ℹ️ Нет активной сессии")
            return
            
        print("\n🔒 Закрытие текущей сессии...")
        
        try:
            if self.session_manager.is_active:
                success = await self.session_manager.close_session()
                if success:
                    print("✅ Сессия закрыта")
                else:
                    print("⚠️ Проблемы при закрытии сессии")
            
            self.session_active = False
            self.current_session_id = None
            
        except Exception as e:
            logger.error(f"Ошибка закрытия сессии: {e}")
            print(f"❌ Ошибка: {e}")

    async def send_message_to_avatar(self, message: str):
        """Отправить сообщение аватару и скачать видео ответ"""
        # Проверяем реальное состояние сессии в менеджере
        if not hasattr(self.session_manager, 'session_id') or not self.session_manager.session_id:
            print("❌ Нет активной сессии. Используйте /start для создания сессии.")
            self.session_active = False
            return
            
        print(f"\n🗣️  Отправка: \"{message}\"")
        print("⏳ Аватар обрабатывает сообщение...")
        
        try:
            # Используем frame processor для обработки задачи и скачивания видео
            video_path = await self.frame_processor.process_text_task(message)
            
            if video_path:
                print(f"✅ Видео ответ скачан: {video_path}")
                
                # Показываем информацию о файле
                import os
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    size_mb = file_size / (1024 * 1024)
                    print(f"📹 Размер файла: {size_mb:.2f} MB")
                    print(f"📁 Расположение: {video_path}")
            else:
                print("❌ Не удалось получить видео ответ")
                
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            print(f"❌ Ошибка: {e}")

    async def check_session_status(self):
        """Проверить статус текущей сессии"""
        print("\n📊 Статус сессии:")
        print("-" * 30)
        
        # Синхронизируем состояние с реальным
        real_active = hasattr(self.session_manager, 'session_id') and self.session_manager.session_id
        
        if real_active:
            self.session_active = True
            self.current_session_id = self.session_manager.session_id
            print(f"🟢 Активная сессия: {self.current_session_id}")
            # Убираем проблемный метод get_remaining_time пока он не реализован
            # remaining = self.session_manager.get_remaining_time()
            # if remaining:
            #     print(f"⏰ Осталось времени: {remaining}s")
            print("💬 Готов принимать сообщения")
        else:
            self.session_active = False
            print("🔴 Нет активной сессии")
            print("💡 Используйте /start для создания сессии")

    async def check_api_status(self):
        """Проверить статус API и активные сессии"""
        print("\n📊 Проверка статуса API...")
        
        try:
            active_sessions = await self.session_manager.list_active_sessions()
            
            if not active_sessions:
                print("✅ Нет активных сессий - API доступен")
            else:
                print(f"ℹ️ Найдено активных сессий: {len(active_sessions)}")
                for session in active_sessions:
                    session_id = session.get('session_id', 'Unknown')
                    status = session.get('status', 'Unknown')
                    print(f"  - {session_id}: {status}")
                    
        except Exception as e:
            logger.error(f"Ошибка проверки API: {e}")
            print(f"❌ Ошибка: {e}")

    async def process_command(self, command: str) -> bool:
        """Обработать команду. Возвращает False для выхода"""
        if command == '/help':
            self.print_help()
        elif command == '/start':
            await self.start_session()
        elif command == '/stop':
            await self.stop_session()
        elif command == '/cleanup':
            await self.cleanup_sessions()
        elif command == '/status':
            await self.check_session_status()
            await self.check_api_status()
        elif command == '/quit':
            print("\n👋 Завершение работы...")
            return False
        else:
            print(f"❓ Неизвестная команда: {command}")
            print("   Введите /help для справки")
        
        return True

    async def chat_loop(self):
        """Основной цикл чата"""
        try:
            while True:
                # Показываем подсказку в зависимости от статуса сессии
                if self.session_active:
                    prompt = "\n💬 Сообщение аватару (или команду): "
                else:
                    prompt = "\n💬 Введите команду: "
                    
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                # Обрабатываем команды
                if user_input.startswith('/'):
                    should_continue = await self.process_command(user_input)
                    if not should_continue:
                        break
                else:
                    # Отправляем сообщение аватару если сессия активна
                    if self.session_active:
                        await self.send_message_to_avatar(user_input)
                    else:
                        print("❌ Нет активной сессии. Используйте /start для создания.")
                    
        except KeyboardInterrupt:
            print("\n\n⚠️  Получен сигнал прерывания (Ctrl+C)")
        except Exception as e:
            logger.error(f"Ошибка в цикле чата: {e}")
            print(f"\n❌ Критическая ошибка: {e}")

    async def cleanup(self):
        """Очистка ресурсов"""
        print("\n🧹 Завершение работы...")
        
        self.is_running = False
        
        # Закрываем активную сессию если есть
        if self.session_active:
            await self.stop_session()
        
        print("✅ Очистка завершена")

    async def run(self):
        """Запустить чат"""
        try:
            self.print_welcome()
            
            print("\n🎉 Готов к работе!")
            print("    Введите /help для списка команд")
            print("    Используйте /start для создания сессии с аватаром")
            print("    Используйте /cleanup если возникнут проблемы с лимитами")
            
            # Запускаем цикл чата
            await self.chat_loop()
            
        finally:
            # Всегда выполняем очистку
            await self.cleanup()

async def main():
    """Главная функция"""
    chat = ConsoleAvatarChat()
    await chat.run()

if __name__ == "__main__":
    asyncio.run(main())
