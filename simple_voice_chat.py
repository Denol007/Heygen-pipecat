#!/usr/bin/env python3
"""
Простой голосовой чат с HeyGen Interactive Avatar
Интеграция Deepgram STT + OpenAI LLM + HeyGen Avatar
"""

import asyncio
import logging
import os
import sys
import json
import time
import threading
import queue
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Speech-to-Text
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
)

# LLM
import openai

# Локальные импорты
from heygen.session_manager import HeyGenSessionManager
from pipecat_integration.livekit_client import HeyGenLiveKitClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleVoiceChat:
    """Простой голосовой чат с аватаром"""
    
    def __init__(self):
        # Получаем API ключи из переменных окружения
        self.heygen_api_key = os.getenv("HEYGEN_API_KEY")
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.heygen_api_key:
            raise ValueError("HEYGEN_API_KEY не найден в переменных окружения")
        if not self.deepgram_api_key:
            raise ValueError("DEEPGRAM_API_KEY не найден в переменных окружения")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
            
        # Инициализация клиентов
        self.session_manager = HeyGenSessionManager(self.heygen_api_key)
        self.livekit_client = None
        self.current_session = None
        
        # Deepgram клиент
        self.deepgram = DeepgramClient(self.deepgram_api_key)
        self.dg_connection = None
        self.microphone = None
        
        # OpenAI клиент
        self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Состояние
        self.is_listening = False
        self.is_recording = False
        self.conversation_history = [
            {"role": "system", "content": "Ты дружелюбный AI-помощник. Отвечай кратко и по делу на русском языке, максимум 2-3 предложения."}
        ]
        
        # Очередь для сообщений
        self.message_queue = queue.Queue()
        
    async def create_session(self) -> bool:
        """Создать сессию с аватаром"""
        try:
            logger.info("🔄 Создание сессии с аватаром...")
            
            # Закрыть предыдущую сессию если есть
            if self.current_session:
                await self.session_manager.close_session(self.current_session["session_id"])
                
            # Создать новую сессию
            session_data = await self.session_manager.create_session()
            if not session_data:
                logger.error("❌ Не удалось создать сессию")
                return False
                
            self.current_session = session_data
            logger.info(f"✅ Сессия создана: {session_data['session_id']}")
            
            # Запустить сессию
            success = await self.session_manager.start_session(session_data["session_id"])
            if success:
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
            
    def setup_deepgram_stt(self):
        """Настроить Deepgram Speech-to-Text"""
        try:
            logger.info("🔄 Настройка Deepgram STT...")
            
            # Создаем подключение
            self.dg_connection = self.deepgram.listen.live.v("1")
            
            # Настраиваем обработчики событий
            def on_open(self, open, **kwargs):
                logger.info("✅ Deepgram соединение открыто")
                
            def on_message(self, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if sentence.strip():
                    logger.info(f"🎤 Распознано: {sentence}")
                    # Добавляем в очередь для обработки
                    self.message_queue.put(sentence)
                    
            def on_metadata(self, metadata, **kwargs):
                logger.debug(f"📊 Metadata: {metadata}")
                
            def on_speech_started(self, speech_started, **kwargs):
                logger.debug("🎤 Начало речи")
                
            def on_utterance_end(self, utterance_end, **kwargs):
                logger.debug("🎤 Конец высказывания")
                
            def on_close(self, close, **kwargs):
                logger.info("🔐 Deepgram соединение закрыто")
                
            def on_error(self, error, **kwargs):
                logger.error(f"❌ Deepgram ошибка: {error}")
                
            # Регистрируем обработчики
            self.dg_connection.on(LiveTranscriptionEvents.Open, on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            self.dg_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            self.dg_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            
            # Настройки транскрипции
            options = LiveOptions(
                model="nova-2",
                language="ru",
                smart_format=True,
                interim_results=False,
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=300
            )
            
            # Запускаем соединение
            if self.dg_connection.start(options):
                logger.info("✅ Deepgram STT готов")
                return True
            else:
                logger.error("❌ Не удалось запустить Deepgram STT")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка настройки Deepgram STT: {e}")
            return False
            
    def setup_microphone(self):
        """Настроить микрофон"""
        try:
            logger.info("🔄 Настройка микрофона...")
            
            self.microphone = Microphone(self.dg_connection.send)
            logger.info("✅ Микрофон готов")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки микрофона: {e}")
            return False
            
    async def generate_llm_response(self, user_message: str) -> str:
        """Генерировать ответ через OpenAI"""
        try:
            # Добавляем сообщение пользователя в историю
            self.conversation_history.append({"role": "user", "content": user_message})
            
            # Ограничиваем историю последними 10 сообщениями
            if len(self.conversation_history) > 11:  # system + 10 messages
                self.conversation_history = [self.conversation_history[0]] + self.conversation_history[-10:]
            
            # Генерируем ответ
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.conversation_history,
                max_tokens=150,
                temperature=0.7
            )
            
            assistant_message = response.choices[0].message.content.strip()
            
            # Добавляем ответ в историю
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            logger.info(f"🤖 LLM ответ: {assistant_message}")
            return assistant_message
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации LLM ответа: {e}")
            return "Извините, произошла ошибка при генерации ответа."
            
    async def process_messages(self):
        """Обработка сообщений из очереди"""
        logger.info("🔄 Запуск обработчика сообщений...")
        
        while self.is_listening:
            try:
                # Проверяем очередь сообщений
                if not self.message_queue.empty():
                    user_message = self.message_queue.get_nowait()
                    
                    if user_message.strip():
                        logger.info(f"💬 Обработка: {user_message}")
                        
                        # Генерируем ответ через LLM
                        llm_response = await self.generate_llm_response(user_message)
                        
                        # Отправляем ответ аватару
                        if self.current_session and llm_response:
                            # Начинаем запись видео ответа
                            if self.livekit_client:
                                task_id = f"voice_task_{int(time.time())}"
                                self.livekit_client.start_recording(task_id)
                                
                            # Отправляем сообщение аватару
                            await self.session_manager.send_task(
                                self.current_session["session_id"],
                                llm_response
                            )
                            
                            # Ждем некоторое время для генерации ответа
                            await asyncio.sleep(3.0)
                            
                            # Останавливаем запись
                            if self.livekit_client:
                                video_file = await self.livekit_client.stop_recording()
                                if video_file:
                                    logger.info(f"📹 Видео ответ сохранен: {video_file}")
                                    
                await asyncio.sleep(0.1)  # Небольшая задержка
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"❌ Ошибка обработки сообщения: {e}")
                await asyncio.sleep(1.0)
                
    async def start_voice_chat(self):
        """Запустить голосовой чат"""
        try:
            logger.info("🚀 Запуск голосового чата с аватаром...")
            
            # Создаем сессию с аватаром
            if not await self.create_session():
                return False
                
            # Подключаемся к LiveKit для записи видео
            if not await self.setup_livekit_connection():
                return False
                
            # Настраиваем Deepgram STT
            if not self.setup_deepgram_stt():
                return False
                
            # Настраиваем микрофон
            if not self.setup_microphone():
                return False
                
            logger.info("🎉 Все компоненты готовы!")
            logger.info("🎤 Говорите в микрофон, я вас слушаю...")
            logger.info("📝 Нажмите Ctrl+C для завершения")
            
            # Запускаем прослушивание
            self.is_listening = True
            
            # Запускаем микрофон
            self.microphone.start()
            
            # Запускаем обработчик сообщений в отдельной задаче
            message_task = asyncio.create_task(self.process_messages())
            
            # Ждем завершения
            try:
                while self.is_listening:
                    await asyncio.sleep(1.0)
            except KeyboardInterrupt:
                logger.info("🛑 Остановка по Ctrl+C")
                
            # Завершаем обработчик сообщений
            self.is_listening = False
            await message_task
            
        except Exception as e:
            logger.error(f"❌ Ошибка в голосовом чате: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 Очистка ресурсов...")
        
        try:
            self.is_listening = False
            
            # Останавливаем микрофон
            if self.microphone:
                self.microphone.finish()
                
            # Закрываем Deepgram соединение
            if self.dg_connection:
                self.dg_connection.finish()
                
            # Отключаемся от LiveKit
            if self.livekit_client:
                await self.livekit_client.disconnect()
                
            # Закрываем сессию с аватаром
            if self.current_session:
                await self.session_manager.close_session(self.current_session["session_id"])
                
            logger.info("✅ Очистка завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке: {e}")


async def main():
    """Главная функция"""
    try:
        print("🤖 HeyGen Voice Chat")
        print("=" * 50)
        
        # Проверяем наличие необходимых переменных окружения
        required_vars = ["HEYGEN_API_KEY", "DEEPGRAM_API_KEY", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
            logger.info("💡 Скопируйте .env.example в .env и заполните API ключи")
            return
            
        # Создаем и запускаем голосовой чат
        voice_chat = SimpleVoiceChat()
        await voice_chat.start_voice_chat()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
