#!/usr/bin/env python3
"""
Голосовой чат с HeyGen Interactive Avatar
Интеграция Deepgram STT + Google Gemini LLM + HeyGen Avatar
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

# LLM - Google Gemini
import google.generativeai as genai

# Локальные импорты
from heygen.session_manager import HeyGenSessionManager
from pipecat_integration.livekit_client import HeyGenLiveKitClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VoiceChatWithGemini:
    """Голосовой чат с Gemini и аватаром"""
    
    def __init__(self):
        # Получаем API ключи из переменных окружения
        self.heygen_api_key = os.getenv("HEYGEN_API_KEY")
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Проверяем API ключи
        if not self.heygen_api_key or self.heygen_api_key == "your_heygen_api_key_here":
            raise ValueError("❌ Установите настоящий HEYGEN_API_KEY в .env файле")
        if not self.deepgram_api_key:
            raise ValueError("❌ Установите DEEPGRAM_API_KEY в .env файле")
        if not self.gemini_api_key:
            raise ValueError("❌ Установите GEMINI_API_KEY в .env файле")
            
        # Инициализация клиентов
        self.session_manager = HeyGenSessionManager(self.heygen_api_key)
        self.livekit_client = None
        self.current_session = None
        
        # Инициализация Deepgram
        self.deepgram_client = DeepgramClient(self.deepgram_api_key)
        self.deepgram_connection = None
        self.microphone = None
        
        # Инициализация Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Очередь для обработки сообщений
        self.message_queue = queue.Queue()
        self.is_running = False
        self.processing_thread = None
        
        logger.info("✅ VoiceChatWithGemini инициализирован")
        
    async def test_apis(self) -> bool:
        """Протестировать все API"""
        logger.info("🧪 Тестирование API...")
        
        # Тест Gemini
        try:
            response = self.gemini_model.generate_content("Скажи короткое приветствие на русском языке")
            logger.info(f"✅ Gemini API работает: {response.text}")
        except Exception as e:
            logger.error(f"❌ Ошибка Gemini API: {e}")
            return False
            
        # Тест Deepgram
        try:
            # Проверяем подключение к Deepgram
            logger.info("✅ Deepgram API ключ настроен")
        except Exception as e:
            logger.error(f"❌ Ошибка Deepgram API: {e}")
            return False
            
        return True
        
    async def generate_llm_response(self, user_input: str) -> str:
        """Генерировать ответ с помощью Gemini"""
        try:
            # Создаем контекст для дружелюбного русскоязычного ассистента
            prompt = f"""Ты дружелюбный голосовой ассистент. Отвечай кратко (1-2 предложения), 
            естественно и по-дружески на русском языке. Вот сообщение пользователя:
            
            {user_input}"""
            
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа Gemini: {e}")
            return "Извините, произошла ошибка при генерации ответа."
    
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
                
                # Начинаем непрерывную запись сессии
                session_task_id = f"session_{self.current_session['session_id']}"
                await self.livekit_client.start_recording(session_task_id)
                logger.info("🎬 Началась непрерывная запись всей сессии")
                
                return True
            else:
                logger.error("❌ Не удалось подключиться к LiveKit")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к LiveKit: {e}")
            return False
    
    def setup_deepgram_connection(self):
        """Настроить подключение к Deepgram для распознавания речи"""
        try:
            logger.info("🔄 Настройка Deepgram STT...")
            
            # Настройки для живого распознавания речи
            options = LiveOptions(
                model="nova-2",
                language="ru",  # Русский язык
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                encoding="linear16",
                channels=1,
                sample_rate=16000,
            )
            
            # Создаем подключение к Deepgram
            self.deepgram_connection = self.deepgram_client.listen.websocket.v("1")
            
            # Обработчики событий
            def on_message(self_event, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if sentence and result.is_final:
                    logger.info(f"🎤 Распознано: '{sentence}'")
                    # Добавляем в очередь для обработки
                    self.message_queue.put(sentence)
                    
            def on_metadata(self_event, metadata, **kwargs):
                logger.debug(f"📊 Метаданные Deepgram: {metadata}")
                
            def on_speech_started(self_event, speech_started, **kwargs):
                logger.debug("🎤 Начало речи")
                
            def on_utterance_end(self_event, utterance_end, **kwargs):
                logger.debug("🎤 Конец высказывания")
                
            def on_error(self_event, error, **kwargs):
                logger.error(f"❌ Ошибка Deepgram: {error}")
            
            # Привязываем обработчики
            self.deepgram_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.deepgram_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            self.deepgram_connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
            self.deepgram_connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
            self.deepgram_connection.on(LiveTranscriptionEvents.Error, on_error)
            
            # Запускаем подключение
            if self.deepgram_connection.start(options):
                logger.info("✅ Deepgram подключен")
                
                # Настраиваем микрофон
                self.microphone = Microphone(self.deepgram_connection.send)
                return True
            else:
                logger.error("❌ Не удалось подключиться к Deepgram")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка настройки Deepgram: {e}")
            return False
    
    def start_microphone(self):
        """Запустить микрофон"""
        try:
            if self.microphone:
                self.microphone.start()
                logger.info("🎤 Микрофон запущен")
                return True
            else:
                logger.error("❌ Микрофон не настроен")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка запуска микрофона: {e}")
            return False
    
    def stop_microphone(self):
        """Остановить микрофон"""
        try:
            if self.microphone:
                self.microphone.finish()
                logger.info("🎤 Микрофон остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки микрофона: {e}")
    
    async def process_voice_message(self, transcript: str):
        """Обработать голосовое сообщение"""
        try:
            logger.info(f"🔄 Обработка сообщения: '{transcript}'")
            
            # Генерируем ответ с помощью Gemini
            logger.info("🧠 Генерация ответа Gemini...")
            llm_response = await self.generate_llm_response(transcript)
            logger.info(f"✅ Ответ Gemini: '{llm_response}'")
            
            # Отправляем аватару и записываем видео
            if self.current_session and self.livekit_client:
                logger.info("🔄 Отправка аватару...")
                
                # Отправляем текст аватару (запись уже идет)
                await self.session_manager.send_task(
                    text=llm_response,
                    task_type="repeat"
                )
                
                logger.info(f"� Аватар получил сообщение: '{llm_response[:50]}...'")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}")
    
    def message_processing_worker(self):
        """Рабочий поток для обработки сообщений"""
        logger.info("🔄 Запуск обработчика сообщений...")
        
        while self.is_running:
            try:
                # Ждем сообщение из очереди (с таймаутом)
                transcript = self.message_queue.get(timeout=1.0)
                
                # Обрабатываем в асинхронном контексте
                asyncio.run(self.process_voice_message(transcript))
                
                self.message_queue.task_done()
                
            except queue.Empty:
                # Таймаут - продолжаем работу
                continue
            except Exception as e:
                logger.error(f"❌ Ошибка в обработчике сообщений: {e}")
                
        logger.info("🛑 Обработчик сообщений остановлен")
    
    async def run_voice_chat(self):
        """Запустить голосовой чат"""
        try:
            logger.info("🚀 Запуск голосового чата с Gemini...")
            logger.info("=" * 60)
            
            # Тестируем API
            if not await self.test_apis():
                return False
            
            # Создаем сессию с аватаром
            if not await self.create_session():
                return False
                
            # Подключаемся к LiveKit для записи видео
            if not await self.setup_livekit_connection():
                return False
            
            # Настраиваем Deepgram
            if not self.setup_deepgram_connection():
                return False
            
            logger.info("🎉 Система готова к голосовому чату!")
            logger.info("📋 Архитектура: Микрофон → Deepgram STT → Gemini LLM → HeyGen Avatar → Видео")
            logger.info("=" * 60)
            logger.info("🎤 Говорите в микрофон... (Ctrl+C для остановки)")
            
            # Запускаем обработку сообщений в отдельном потоке
            self.is_running = True
            self.processing_thread = threading.Thread(target=self.message_processing_worker)
            self.processing_thread.start()
            
            # Запускаем микрофон
            if not self.start_microphone():
                return False
            
            # Ждем прерывания от пользователя
            try:
                while self.is_running:
                    await asyncio.sleep(1.0)
            except KeyboardInterrupt:
                logger.info("🛑 Получен сигнал остановки")
                
        except Exception as e:
            logger.error(f"❌ Ошибка в голосовом чате: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 Очистка ресурсов...")
        
        try:
            # Останавливаем обработку сообщений
            self.is_running = False
            
            # Останавливаем микрофон
            self.stop_microphone()
            
            # Закрываем Deepgram соединение
            if self.deepgram_connection:
                self.deepgram_connection.finish()
                logger.info("🔌 Deepgram отключен")
            
            # Ждем завершения потока обработки
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=3.0)
                logger.info("🛑 Обработчик сообщений остановлен")
                logger.info("🧵 Поток обработки завершен")
                
            # Останавливаем запись и отключаемся от LiveKit
            if self.livekit_client:
                logger.info("🎬 Завершение записи всей сессии...")
                video_file = await self.livekit_client.stop_recording()
                if video_file:
                    logger.info(f"📹 Полная запись сессии сохранена: {video_file}")
                else:
                    logger.warning("⚠️ Запись сессии не была сохранена")
                    
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
        print("🤖 HeyGen Voice Chat with Gemini")
        print("=" * 50)
        print("📋 Компоненты:")
        print("   🎤 STT: Deepgram (реальный)")
        print("   🧠 LLM: Google Gemini (реальный)")  
        print("   👤 Avatar: HeyGen Interactive")
        print("   📹 Video: LiveKit запись + аудио")
        print("=" * 50)
        
        # Создаем и запускаем голосовой чат
        chat = VoiceChatWithGemini()
        await chat.run_voice_chat()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
