#!/usr/bin/env python3
"""
Голосовой чат с HeyGen Interactive Avatar через Pipecat
Использует Deepgram STT, OpenAI ChatGPT, ElevenLabs TTS
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frame_processor import FrameDirection
from pipecat.frames.frames import (
    Frame, AudioRawFrame, TranscriptionFrame, 
    LLMMessagesFrame, TextFrame, TTSAudioRawFrame,
    EndFrame, StartFrame
)
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.transports.network.websocket import WebsocketTransport
from pipecat.vad.vad_analyzer import VADAnalyzer

# Локальные импорты
from heygen.session_manager import HeyGenSessionManager
from pipecat_integration.livekit_client import HeyGenLiveKitClient
from utils.logger import setup_logger
from utils.config import Config

# Настройка логирования
logger = setup_logger(__name__)

class VoiceChatOrchestrator:
    """Оркестратор голосового чата с аватаром"""
    
    def __init__(self):
        self.config = Config()
        self.session_manager = HeyGenSessionManager(self.config.heygen_api_key)
        self.livekit_client = None
        self.current_session = None
        
        # Сервисы для Pipecat
        self.deepgram_stt = None
        self.openai_llm = None
        self.elevenlabs_tts = None
        self.vad_analyzer = None
        
        # Pipeline компоненты
        self.pipeline = None
        self.pipeline_task = None
        self.pipeline_runner = None
        
    async def initialize_services(self):
        """Инициализация всех сервисов"""
        logger.info("Инициализация сервисов...")
        
        # Speech-to-Text (Deepgram)
        if self.config.deepgram_api_key:
            self.deepgram_stt = DeepgramSTTService(
                api_key=self.config.deepgram_api_key,
                model="nova-2",
                language="ru"  # Русский язык
            )
            logger.info("✅ Deepgram STT инициализован")
        else:
            logger.error("❌ Deepgram API ключ не найден")
            return False
            
        # LLM (OpenAI ChatGPT)
        if self.config.openai_api_key:
            self.openai_llm = OpenAILLMService(
                api_key=self.config.openai_api_key,
                model="gpt-4o-mini",
                system_prompt="Ты дружелюбный AI-помощник. Отвечай кратко и по делу на русском языке."
            )
            logger.info("✅ OpenAI LLM инициализован")
        else:
            logger.error("❌ OpenAI API ключ не найден")
            return False
            
        # Text-to-Speech (ElevenLabs - опционально)
        if self.config.elevenlabs_api_key:
            self.elevenlabs_tts = ElevenLabsTTSService(
                api_key=self.config.elevenlabs_api_key,
                voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice
                model="eleven_multilingual_v2"
            )
            logger.info("✅ ElevenLabs TTS инициализован")
        else:
            logger.warning("⚠️ ElevenLabs API ключ не найден - будем использовать только аватар")
            
        # Voice Activity Detection
        self.vad_analyzer = SileroVADAnalyzer()
        logger.info("✅ VAD анализатор инициализован")
        
        return True
        
    async def create_session(self) -> bool:
        """Создать сессию с аватаром"""
        try:
            logger.info("Создание сессии с аватаром...")
            
            # Закрыть предыдущую сессию если есть
            if self.current_session:
                await self.session_manager.close_session(self.current_session["session_id"])
                
            # Создать новую сессию
            session_data = await self.session_manager.create_session()
            if not session_data:
                logger.error("Не удалось создать сессию")
                return False
                
            self.current_session = session_data
            logger.info(f"✅ Сессия создана: {session_data['session_id']}")
            
            # Запустить сессию
            success = await self.session_manager.start_session(session_data["session_id"])
            if success:
                logger.info("✅ Сессия активирована")
                return True
            else:
                logger.error("Не удалось активировать сессию")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка создания сессии: {e}")
            return False
            
    async def setup_livekit_connection(self) -> bool:
        """Настроить подключение к LiveKit"""
        try:
            if not self.current_session:
                logger.error("Нет активной сессии для подключения к LiveKit")
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
                logger.error("Не удалось подключиться к LiveKit")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка подключения к LiveKit: {e}")
            return False
            
    async def create_pipeline(self):
        """Создать Pipecat pipeline для обработки голоса"""
        try:
            logger.info("Создание Pipecat pipeline...")
            
            # Создаем процессоры
            processors = []
            
            # 1. VAD для определения речи
            if self.vad_analyzer:
                processors.append(self.vad_analyzer)
                
            # 2. Speech-to-Text
            if self.deepgram_stt:
                processors.append(self.deepgram_stt)
                
            # 3. LLM для генерации ответов
            if self.openai_llm:
                processors.append(self.openai_llm)
                
            # 4. TTS если есть ElevenLabs
            if self.elevenlabs_tts:
                processors.append(self.elevenlabs_tts)
                
            # Создаем pipeline
            self.pipeline = Pipeline(processors)
            
            # Настраиваем обработчики кадров
            self.pipeline.add_event_handler("on_transcription", self._on_transcription)
            self.pipeline.add_event_handler("on_llm_response", self._on_llm_response)
            self.pipeline.add_event_handler("on_tts_audio", self._on_tts_audio)
            
            logger.info("✅ Pipeline создан")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания pipeline: {e}")
            return False
            
    async def _on_transcription(self, frame: TranscriptionFrame):
        """Обработка результата распознавания речи"""
        transcription = frame.text.strip()
        if transcription:
            logger.info(f"🎤 Распознано: {transcription}")
            
            # Отправляем текст аватару через HeyGen API
            if self.current_session:
                await self.session_manager.send_task(
                    self.current_session["session_id"],
                    transcription
                )
                
    async def _on_llm_response(self, frame: TextFrame):
        """Обработка ответа от LLM"""
        response_text = frame.text.strip()
        if response_text:
            logger.info(f"🤖 LLM ответ: {response_text}")
            
            # Отправляем ответ аватару
            if self.current_session:
                await self.session_manager.send_task(
                    self.current_session["session_id"],
                    response_text
                )
                
    async def _on_tts_audio(self, frame: TTSAudioRawFrame):
        """Обработка аудио от TTS"""
        logger.debug("🔊 Получен TTS аудио кадр")
        # Здесь можно добавить логику воспроизведения аудио
        
    async def start_voice_chat(self):
        """Запустить голосовой чат"""
        try:
            logger.info("🚀 Запуск голосового чата...")
            
            # Инициализация всех компонентов
            if not await self.initialize_services():
                logger.error("Не удалось инициализировать сервисы")
                return False
                
            if not await self.create_session():
                logger.error("Не удалось создать сессию")
                return False
                
            if not await self.setup_livekit_connection():
                logger.error("Не удалось подключиться к LiveKit")
                return False
                
            if not await self.create_pipeline():
                logger.error("Не удалось создать pipeline")
                return False
                
            # Создаем задачу pipeline
            self.pipeline_task = PipelineTask(self.pipeline)
            
            # Запускаем runner
            self.pipeline_runner = PipelineRunner()
            
            logger.info("🎉 Голосовой чат готов к работе!")
            logger.info("🎤 Говорите в микрофон, аватар будет отвечать...")
            
            # Запускаем основной цикл
            await self.pipeline_runner.run(self.pipeline_task)
            
        except KeyboardInterrupt:
            logger.info("Остановка по Ctrl+C")
        except Exception as e:
            logger.error(f"Ошибка в голосовом чате: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("🧹 Очистка ресурсов...")
        
        try:
            # Останавливаем pipeline
            if self.pipeline_runner:
                await self.pipeline_runner.cleanup()
                
            # Отключаемся от LiveKit
            if self.livekit_client:
                await self.livekit_client.disconnect()
                
            # Закрываем сессию
            if self.current_session:
                await self.session_manager.close_session(self.current_session["session_id"])
                
            logger.info("✅ Очистка завершена")
            
        except Exception as e:
            logger.error(f"Ошибка при очистке: {e}")


async def main():
    """Главная функция"""
    try:
        # Проверяем наличие необходимых переменных окружения
        required_vars = ["HEYGEN_API_KEY", "DEEPGRAM_API_KEY", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют переменные окружения: {', '.join(missing_vars)}")
            logger.info("💡 Скопируйте .env.example в .env и заполните API ключи")
            return
            
        # Создаем и запускаем голосовой чат
        orchestrator = VoiceChatOrchestrator()
        await orchestrator.start_voice_chat()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
