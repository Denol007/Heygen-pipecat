#!/usr/bin/env python3
"""
Демо голосового чата с HeyGen Interactive Avatar
Показывает архитектуру интеграции STT + LLM + Avatar
"""

import asyncio
import logging
import os
import sys
import time
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Локальные импорты
from heygen.session_manager import HeyGenSessionManager
from pipecat_integration.livekit_client import HeyGenLiveKitClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceChatDemo:
    """Демо голосового чата с аватаром"""
    
    def __init__(self):
        # Получаем API ключи
        self.heygen_api_key = os.getenv("HEYGEN_API_KEY")
        if not self.heygen_api_key or self.heygen_api_key == "your_heygen_api_key_here":
            raise ValueError("❌ Установите настоящий HEYGEN_API_KEY в .env файле")
            
        # Инициализация клиентов
        self.session_manager = HeyGenSessionManager(self.heygen_api_key)
        self.livekit_client = None
        self.current_session = None
        
    async def create_session(self) -> bool:
        """Создать сессию с аватаром"""
        try:
            logger.info("🔄 Создание сессии с аватаром...")
            
            # Создать новую сессию
            success = await self.session_manager.create_session()
            if not success:
                logger.error("❌ Не удалось создать сессию")
                return False
                
            # Проверяем что у нас есть необходимые данные сессии
            if not self.session_manager.session_id:
                logger.error("❌ Не получен session_id")
                return False
                
            # Сохраняем данные сессии в удобном формате
            self.current_session = {
                "session_id": self.session_manager.session_id,
                "url": self.session_manager.websocket_url,
                "access_token": self.session_manager.access_token
            }
            
            logger.info(f"✅ Сессия создана: {self.session_manager.session_id}")
            
            # Запустить сессию
            start_success = await self.session_manager.start_session()
            if start_success:
                logger.info("✅ Сессия активирована")
                return True
            else:
                logger.error("❌ Не удалось активировать сессию")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания сессии: {e}")
            return False
            
    async def setup_livekit_connection(self) -> bool:
        """Настроить подключение к LiveKit для записи видео"""
        try:
            if not self.current_session:
                logger.error("❌ Нет активной сессии для подключения к LiveKit")
                return False
                
            self.livekit_client = HeyGenLiveKitClient()
            
            success = await self.livekit_client.connect(
                url=self.current_session["url"],
                access_token=self.current_session["access_token"],
                session_id=self.current_session["session_id"]
            )
            
            if success:
                logger.info("✅ Подключен к LiveKit")
                return True
            else:
                logger.error("❌ Не удалось подключиться к LiveKit")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к LiveKit: {e}")
            return False
            
    async def simulate_voice_interaction(self):
        """Симулируем голосовое взаимодействие"""
        logger.info("🎭 Симуляция голосового взаимодействия...")
        
        # Имитируем различные сценарии
        test_scenarios = [
            "Привет, как дела?",
            "Расскажи анекдот",
            "Какая сегодня погода?",
            "Спасибо, до свидания!"
        ]
        
        for i, user_input in enumerate(test_scenarios, 1):
            logger.info(f"🎤 [{i}/4] Пользователь говорит: '{user_input}'")
            
            # 1. Имитируем STT (Speech-to-Text)
            logger.info("🔄 STT: Распознавание речи...")
            await asyncio.sleep(0.5)  # Имитация времени распознавания
            transcribed_text = user_input  # В реальности здесь будет Deepgram
            logger.info(f"✅ STT результат: '{transcribed_text}'")
            
            # 2. Имитируем LLM обработку
            logger.info("🔄 LLM: Генерация ответа...")
            await asyncio.sleep(1.0)  # Имитация времени генерации
            
            # Простые ответы для демо
            responses = {
                "Привет, как дела?": "Привет! У меня всё отлично, спасибо за вопрос!",
                "Расскажи анекдот": "Почему программисты не любят природу? Потому что там слишком много багов!",
                "Какая сегодня погода?": "Сегодня прекрасная погода для программирования!",
                "Спасибо, до свидания!": "Пожалуйста! До встречи!"
            }
            
            llm_response = responses.get(user_input, "Интересный вопрос! Давайте обсудим это подробнее.")
            logger.info(f"✅ LLM ответ: '{llm_response}'")
            
            # 3. Отправляем аватару и записываем видео
            if self.current_session and self.livekit_client:
                logger.info("🔄 Отправка аватару и запись видео...")
                
                # Начинаем запись
                task_id = f"demo_task_{i}_{int(time.time())}"
                await self.livekit_client.start_recording(task_id)
                
                # Отправляем текст аватару
                await self.session_manager.send_task(
                    text=llm_response,
                    task_type="repeat"
                )
                
                # Ждем генерации ответа
                logger.info("⏳ Ожидание ответа аватара...")
                await asyncio.sleep(4.0)  # Время на генерацию + проговаривание
                
                # Останавливаем запись
                video_file = await self.livekit_client.stop_recording()
                if video_file:
                    logger.info(f"📹 Видео ответ сохранен: {video_file}")
                else:
                    logger.warning("⚠️ Видео не сохранено")
                    
            logger.info("✅ Взаимодействие завершено")
            
            # Пауза между сценариями
            if i < len(test_scenarios):
                logger.info("⏸️ Пауза между сценариями...")
                await asyncio.sleep(2.0)
                
    async def run_demo(self):
        """Запустить демо"""
        try:
            logger.info("🚀 Запуск демонстрации голосового чата...")
            logger.info("=" * 60)
            
            # Создаем сессию с аватаром
            if not await self.create_session():
                return False
                
            # Подключаемся к LiveKit для записи видео
            if not await self.setup_livekit_connection():
                return False
                
            logger.info("🎉 Система готова к демонстрации!")
            logger.info("📋 Архитектура: Пользователь → STT → LLM → Аватар → Видео")
            logger.info("=" * 60)
            
            # Запускаем симуляцию
            await self.simulate_voice_interaction()
            
            logger.info("=" * 60)
            logger.info("🎊 Демонстрация завершена успешно!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в демо: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 Очистка ресурсов...")
        
        try:
            # Отключаемся от LiveKit
            if self.livekit_client:
                await self.livekit_client.disconnect()
                
            # Закрываем сессию с аватаром
            if self.current_session:
                await self.session_manager.close_session()
                
            logger.info("✅ Очистка завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке: {e}")


async def main():
    """Главная функция"""
    try:
        print("🤖 HeyGen Voice Chat - ДЕМОНСТРАЦИЯ")
        print("=" * 50)
        print("📋 Компоненты:")
        print("   🎤 STT: Deepgram (имитация)")
        print("   🧠 LLM: OpenAI GPT (имитация)")  
        print("   👤 Avatar: HeyGen Interactive")
        print("   📹 Video: LiveKit запись")
        print("=" * 50)
        
        # Проверяем API ключ HeyGen
        heygen_key = os.getenv("HEYGEN_API_KEY")
        if not heygen_key or heygen_key == "your_heygen_api_key_here":
            print("❌ Необходимо установить настоящий HEYGEN_API_KEY в .env файле")
            print("💡 Откройте .env и замените 'your_heygen_api_key_here' на ваш ключ")
            return
            
        # Создаем и запускаем демо
        demo = VoiceChatDemo()
        await demo.run_demo()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
