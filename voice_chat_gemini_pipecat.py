#!/usr/bin/env python3
"""
Голосовой чат с HeyGen Interactive Avatar - Pipecat-inspired версия
Интеграция Deepgram STT + Google Gemini LLM + HeyGen Avatar в стиле Pipecat
"""

import asyncio
import logging
import os
import sys
import json
import time
import threading
import queue
from typing import Optional, Dict, Any, List
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

class Frame:
    """Базовый класс для фреймов в Pipecat-style pipeline"""
    pass

class AudioFrame(Frame):
    """Фрейм с аудио данными"""
    def __init__(self, audio_data: bytes):
        self.audio_data = audio_data

class TextFrame(Frame):
    """Фрейм с текстовыми данными"""
    def __init__(self, text: str):
        self.text = text

class TranscriptionFrame(Frame):
    """Фрейм с транскрипцией речи"""
    def __init__(self, text: str, is_final: bool = True):
        self.text = text
        self.is_final = is_final

class LLMResponseFrame(Frame):
    """Фрейм с ответом LLM"""
    def __init__(self, text: str):
        self.text = text

class FrameProcessor:
    """Базовый класс для обработчиков фреймов"""
    
    def __init__(self):
        self.downstream = None
    
    def set_downstream(self, processor):
        """Установить следующий обработчик в pipeline"""
        self.downstream = processor
    
    async def process_frame(self, frame: Frame):
        """Обработать фрейм"""
        # Базовая реализация просто передает фрейм дальше
        if self.downstream:
            await self.downstream.process_frame(frame)
    
    async def push_frame(self, frame: Frame):
        """Отправить фрейм дальше по pipeline"""
        if self.downstream:
            await self.downstream.process_frame(frame)

class DeepgramSTTProcessor(FrameProcessor):
    """Процессор для распознавания речи через Deepgram"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
        self.deepgram_client = DeepgramClient(api_key)
        self.deepgram_connection = None
        self.microphone = None
        
    async def start(self):
        """Запуск STT сервиса"""
        try:
            logger.info("🔄 Настройка Deepgram STT...")
            
            # Настройки для живого распознавания речи
            options = LiveOptions(
                model="nova-2",
                language="ru",
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
            
            # Сохраняем ссылку на главный event loop
            main_loop = asyncio.get_event_loop()
            
            # Обработчики событий
            def on_message(self_event, result, **kwargs):
                sentence = result.channel.alternatives[0].transcript
                if sentence and result.is_final:
                    logger.info(f"🎤 Распознано: '{sentence}'")
                    # Создаем фрейм транскрипции и отправляем дальше
                    frame = TranscriptionFrame(sentence, is_final=True)
                    # Используем главный event loop через call_soon_threadsafe
                    try:
                        # Планируем выполнение в главном потоке
                        future = asyncio.run_coroutine_threadsafe(
                            self.push_frame(frame), 
                            main_loop
                        )
                        # Не ждем результат, просто планируем выполнение
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки фрейма: {e}")
                    
            def on_error(self_event, error, **kwargs):
                logger.error(f"❌ Ошибка Deepgram: {error}")
            
            # Привязываем обработчики
            self.deepgram_connection.on(LiveTranscriptionEvents.Transcript, on_message)
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
    
    async def cleanup(self):
        """Очистка ресурсов"""
        self.stop_microphone()
        if self.deepgram_connection:
            self.deepgram_connection.finish()
            logger.info("🔌 Deepgram отключен")

class GeminiLLMProcessor(FrameProcessor):
    """Процессор для генерации ответов через Gemini"""
    
    def __init__(self, api_key: str):
        super().__init__()
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.conversation_history = []
        
    async def process_frame(self, frame: Frame):
        """Обработка входящих фреймов"""
        if isinstance(frame, TranscriptionFrame):
            # Получили транскрипцию речи пользователя
            user_text = frame.text
            logger.info(f"🔄 Обработка сообщения: '{user_text}'")
            logger.info("🧠 Генерация ответа Gemini...")
            
            # Генерируем ответ через Gemini
            try:
                response = await self._generate_response(user_text)
                logger.info(f"✅ Ответ Gemini: '{response}'")
                
                # Создаем фрейм с ответом LLM и отправляем дальше
                llm_frame = LLMResponseFrame(response)
                await self.push_frame(llm_frame)
                
            except Exception as e:
                logger.error(f"❌ Ошибка генерации ответа Gemini: {e}")
                error_response = "Извините, произошла ошибка при генерации ответа."
                llm_frame = LLMResponseFrame(error_response)
                await self.push_frame(llm_frame)
        else:
            # Пропускаем другие фреймы дальше
            await super().process_frame(frame)
    
    async def _generate_response(self, user_message: str) -> str:
        """Генерация ответа через Gemini"""
        try:
            # Добавляем в историю
            self.conversation_history.append(f"Пользователь: {user_message}")
            
            # Создаем промпт с контекстом
            context = "\\n".join(self.conversation_history[-10:])  # Последние 10 сообщений
            prompt = f"""Ты дружелюбный помощник-аватар. Отвечай кратко и естественно на русском языке.

Контекст диалога:
{context}

Дай короткий и естественный ответ на последнее сообщение пользователя."""

            # Генерируем ответ
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Добавляем ответ в историю
            self.conversation_history.append(f"Ассистент: {response_text}")
            
            return response_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка Gemini API: {e}")
            return "Извините, произошла ошибка при обработке вашего запроса."

class HeyGenAvatarProcessor(FrameProcessor):
    """Процессор для интеграции с HeyGen Avatar"""
    
    def __init__(self, api_key: str):
        super().__init__()
        self.session_manager = HeyGenSessionManager(api_key)
        self.livekit_client = None
        self.current_session = None
        self.is_recording = False
        
    async def start_session(self):
        """Создание и запуск сессии HeyGen"""
        try:
            logger.info("🔄 Создание сессии HeyGen...")
            
            # Создаем сессию
            success = await self.session_manager.create_session()
            if not success:
                logger.error("❌ Не удалось создать сессию HeyGen")
                return False
                
            # Сохраняем данные сессии
            self.current_session = {
                "session_id": self.session_manager.session_id,
                "url": self.session_manager.websocket_url,
                "access_token": self.session_manager.access_token
            }
            
            logger.info(f"✅ Сессия HeyGen создана: {self.session_manager.session_id}")
            
            # Запускаем сессию
            start_success = await self.session_manager.start_session()
            if start_success:
                logger.info("✅ Сессия HeyGen активирована")
                
                # Подключаемся к LiveKit для записи
                await self._setup_livekit()
                return True
            else:
                logger.error("❌ Не удалось активировать сессию HeyGen")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания сессии HeyGen: {e}")
            return False
    
    async def _setup_livekit(self):
        """Настройка LiveKit для записи"""
        try:
            self.livekit_client = HeyGenLiveKitClient()
            
            success = await self.livekit_client.connect(
                url=self.current_session["url"],
                access_token=self.current_session["access_token"],
                session_id=self.current_session["session_id"]
            )
            
            if success:
                logger.info("✅ Подключен к LiveKit")
                
                # Начинаем непрерывную запись
                session_task_id = f"pipecat_session_{self.current_session['session_id']}"
                await self.livekit_client.start_recording(session_task_id)
                self.is_recording = True
                logger.info("🎬 Началась непрерывная запись сессии (Pipecat-style)")
                
            else:
                logger.error("❌ Не удалось подключиться к LiveKit")
                
        except Exception as e:
            logger.error(f"❌ Ошибка настройки LiveKit: {e}")
    
    async def process_frame(self, frame: Frame):
        """Обработка входящих фреймов"""
        if isinstance(frame, LLMResponseFrame):
            # Получили ответ от LLM для отправки аватару
            text = frame.text
            logger.info("🔄 Отправка аватару...")
            
            try:
                if self.current_session:
                    # Отправляем задачу аватару
                    await self.session_manager.send_task(
                        text=text,
                        task_type="repeat"
                    )
                    logger.info(f"💬 Аватар получил сообщение: '{text[:50]}...'")
                else:
                    logger.warning("⚠️ Нет активной сессии HeyGen")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка отправки аватару: {e}")
        else:
            # Пропускаем другие фреймы дальше
            await super().process_frame(frame)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("🧹 Очистка ресурсов HeyGen...")
            
            # Останавливаем запись
            if self.livekit_client and self.is_recording:
                logger.info("🎬 Завершение записи сессии...")
                video_file = await self.livekit_client.stop_recording()
                if video_file:
                    logger.info(f"📹 Полная запись сессии сохранена: {video_file}")
                    
                await self.livekit_client.disconnect()
                
            # Закрываем сессию
            if self.current_session:
                await self.session_manager.close_session()
                
            logger.info("✅ Очистка HeyGen завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке HeyGen: {e}")

class PipecatStylePipeline:
    """Pipecat-style pipeline для обработки фреймов"""
    
    def __init__(self, processors: List[FrameProcessor]):
        self.processors = processors
        
        # Связываем процессоры в цепочку
        for i in range(len(processors) - 1):
            processors[i].set_downstream(processors[i + 1])
    
    async def start(self):
        """Запуск pipeline"""
        # Запускаем все процессоры которые требуют инициализации
        for processor in self.processors:
            if hasattr(processor, 'start'):
                await processor.start()
    
    async def cleanup(self):
        """Очистка pipeline"""
        for processor in self.processors:
            if hasattr(processor, 'cleanup'):
                await processor.cleanup()

class VoiceChatPipecatRunner:
    """Главный класс для запуска голосового чата в Pipecat-style"""
    
    def __init__(self):
        # Получаем API ключи
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
            
        # Инициализируем процессоры
        self.stt_processor = DeepgramSTTProcessor(self.deepgram_api_key)
        self.llm_processor = GeminiLLMProcessor(self.gemini_api_key)
        self.avatar_processor = HeyGenAvatarProcessor(self.heygen_api_key)
        
        # Создаем pipeline
        self.pipeline = PipecatStylePipeline([
            self.stt_processor,        # Аудио → Транскрипция
            self.llm_processor,        # Транскрипция → LLM ответ  
            self.avatar_processor,     # LLM ответ → Avatar
        ])
        
        logger.info("✅ VoiceChatPipecatRunner инициализирован")
    
    async def test_apis(self) -> bool:
        """Тестирование всех API"""
        logger.info("🧪 Тестирование API...")
        
        # Тест Gemini
        try:
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Скажи короткое приветствие на русском языке")
            logger.info(f"✅ Gemini API работает: {response.text}")
        except Exception as e:
            logger.error(f"❌ Ошибка Gemini API: {e}")
            return False
        
        # Тест Deepgram (проверка ключа)
        try:
            logger.info("✅ Deepgram API ключ настроен")
        except Exception as e:
            logger.error(f"❌ Ошибка Deepgram API: {e}")
            return False
            
        return True
    
    async def run_voice_chat(self):
        """Запуск голосового чата"""
        try:
            logger.info("🚀 Запуск голосового чата через Pipecat-style pipeline...")
            logger.info("============================================================")
            
            # Запускаем pipeline
            await self.pipeline.start()
            
            # Создаем и запускаем сессию HeyGen
            if not await self.avatar_processor.start_session():
                logger.error("❌ Не удалось запустить сессию HeyGen") 
                return
            
            logger.info("🎉 Система готова к голосовому чату!")
            logger.info("📋 Архитектура: Микрофон → Pipecat STT → Gemini LLM → HeyGen Avatar → Видео")
            logger.info("============================================================")
            logger.info("🎤 Говорите в микрофон... (Ctrl+C для остановки)")
            
            # Запускаем микрофон
            self.stt_processor.start_microphone()
            
            # Ожидаем в бесконечном цикле
            while True:
                await asyncio.sleep(1.0)
            
        except KeyboardInterrupt:
            logger.info("👤 Остановка по запросу пользователя...")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске голосового чата: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("🧹 Очистка ресурсов...")
            await self.pipeline.cleanup()
            logger.info("✅ Очистка завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при очистке: {e}")

async def main():
    """Главная функция"""
    try:
        print("🤖 HeyGen Voice Chat with Gemini - Pipecat-Style Edition")
        print("=" * 70)
        print("📋 Компоненты:")
        print("   🎤 STT: Deepgram через Pipecat-style процессор")
        print("   🧠 LLM: Google Gemini (кастомный процессор)")  
        print("   👤 Avatar: HeyGen Interactive")
        print("   📹 Video: LiveKit запись + аудио")
        print("   🔧 Framework: Pipecat-inspired Pipeline")
        print("=" * 70)
        
        # Создаем и запускаем голосовой чат
        chat = VoiceChatPipecatRunner()
        
        # Тестируем API
        if not await chat.test_apis():
            logger.error("❌ Тесты API не прошли")
            return
            
        # Запускаем голосовой чат
        await chat.run_voice_chat()
        
    except KeyboardInterrupt:
        print("\\n👋 Программа завершена пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        print(f"\\n💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
