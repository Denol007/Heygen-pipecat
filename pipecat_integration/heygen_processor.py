import asyncio
import logging
import os
import time
from typing import Optional, Any
from datetime import datetime
import cv2
import numpy as np
from pipecat_integration.stream_recorder import HeyGenStreamManager
from pipecat_integration.livekit_client import HeyGenLiveKitClient

logger = logging.getLogger(__name__)

class HeyGenFrameProcessor:
    """
    Pipecat Frame Processor для интеграции с HeyGen Interactive Avatar
    
    Этот класс будет интегрирован с Pipecat для обработки аудио/видео потоков
    и управления записью ответов аватара.
    """
    
    def __init__(self, session_manager):
        # Инициализация компонентов
        self.session_manager = session_manager
        self.livekit_client = HeyGenLiveKitClient()
        self.stream_manager = HeyGenStreamManager(session_manager)
        self.is_processing = False
        self.current_task_id: Optional[str] = None
        self.current_recording_path: Optional[str] = None
    
    async def initialize(self) -> bool:
        """Инициализировать процессор"""
        logger.info("Инициализация HeyGen Frame Processor...")
        
        # Инициализируем поток
        success = await self.stream_manager.initialize_stream()
        if not success:
            logger.error("Не удалось инициализировать поток")
            return False
        
        logger.info("HeyGen Frame Processor готов")
        return True
    
    async def process_text_task(self, text: str, task_type: str = "repeat") -> Optional[str]:
        """
        Обработать текстовую задачу для аватара и записать видео через WebRTC
        
        Args:
            text: Текст для произнесения аватаром
            task_type: Тип задачи ("repeat" или "chat")
            
        Returns:
            Путь к записанному видео файлу или None при ошибке
        """
        if self.is_processing:
            logger.warning("Уже обрабатывается задача")
            return None
        
        self.is_processing = True
        
        try:
            logger.info(f"Начало обработки задачи: {text[:50]}...")
            
            # Подключаемся к LiveKit если еще не подключены
            if not self.livekit_client.is_connected:
                logger.info("Подключение к LiveKit...")
                
                # Подключаемся к LiveKit room используя данные сессии
                url = self.session_manager.websocket_url
                access_token = self.session_manager.access_token
                session_id = self.session_manager.session_id
                server_url = self.session_manager.base_url
                
                if not url or not access_token:
                    logger.error("Отсутствуют данные для подключения к LiveKit")
                    return None
                
                if not await self.livekit_client.connect(url, access_token, session_id, server_url):
                    logger.error("Не удалось подключиться к LiveKit")
                    return None
            
            # Начинаем запись перед отправкой задачи
            task_id = f"task_{int(time.time())}"
            recording_path = await self.livekit_client.start_recording(task_id)
            if not recording_path:
                logger.error("Не удалось начать запись")
                return None
            
            # Отправляем задачу аватару через HTTP API
            result = await self.session_manager.send_task(text, task_type=task_type)
            if not result:
                logger.error("Не удалось отправить задачу")
                await self.livekit_client.stop_recording()
                return None
            
            task_data = result.get('data', {})
            self.current_task_id = task_data.get('task_id', task_id)
            duration_ms = task_data.get('duration_ms', 5000)  # По умолчанию 5 секунд
            
            logger.info(f"Задача отправлена, task_id: {self.current_task_id}, ожидание {duration_ms}ms...")
            
            # Ждем завершения задачи (аватар генерирует ответ)
            wait_time = (duration_ms / 1000) + 2.0  # +2 секунды для буфера
            logger.info(f"Запись в течение {wait_time:.1f} секунд...")
            await asyncio.sleep(wait_time)
            
            # Останавливаем запись и получаем путь к файлу
            video_path = await self.livekit_client.stop_recording()
            
            if video_path and os.path.exists(video_path):
                file_size = os.path.getsize(video_path)
                if file_size > 1024:  # Больше 1KB
                    logger.info(f"✅ Видео сохранено: {video_path} (размер: {file_size} байт)")
                    return video_path
                else:
                    logger.warning(f"Видео файл слишком мал: {file_size} байт")
                    return None
            else:
                logger.error("Не удалось сохранить видео")
                return None
            
        except Exception as e:
            logger.error(f"Ошибка обработки задачи: {e}")
            # Останавливаем запись в случае ошибки
            if self.livekit_client.is_recording:
                await self.livekit_client.stop_recording()
            return None
        finally:
            self.is_processing = False
            self.current_task_id = None
    
    async def interrupt_current_task(self) -> bool:
        """Прервать текущую задачу"""
        if not self.is_processing:
            logger.info("Нет активной задачи для прерывания")
            return True
        
        logger.info("Прерывание текущей задачи...")
        
        # Прерываем задачу в HeyGen
        success = await self.session_manager.interrupt_task()
        
        # Останавливаем запись LiveKit
        await self.livekit_client.stop_recording()
        
        # Останавливаем запись stream manager
        await self.stream_manager.stop_task_recording()
        
        # Сбрасываем состояние
        self.is_processing = False
        self.current_task_id = None
        self.current_recording_path = None
        
        logger.info("Задача прервана")
        return success
    
    async def process_audio_frame(self, audio_frame: Any):
        """
        Обработать аудио кадр (для будущей интеграции с Pipecat)
        
        Args:
            audio_frame: Аудио кадр от Pipecat
        """
        # В будущем здесь будет реальная обработка аудио кадров
        # Например, STT (Speech-to-Text) для преобразования речи в текст
        # и отправка результата аватару
        pass
    
    async def process_video_frame(self, video_frame: Any):
        """
        Обработать видео кадр (для будущей интеграции с Pipecat)
        
        Args:
            video_frame: Видео кадр от Pipecat
        """
        # В будущем здесь будет реальная обработка видео кадров
        # Например, сохранение кадров в запись
        pass
    
    def get_status(self) -> str:
        """Получить читаемый статус процессора"""
        if self.is_processing:
            return f"Обрабатывается задача {self.current_task_id}"
        else:
            return "Готов к обработке"

    async def get_processing_status(self) -> dict:
        """Получить полный статус обработки"""
        return {
            "is_processing": self.is_processing,
            "current_task_id": self.current_task_id,
            "session_active": self.session_manager.is_active,
            "session_id": self.session_manager.session_id
        }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        logger.info("Очистка HeyGen Frame Processor...")
        
        # Прерываем текущую задачу если есть
        if self.is_processing:
            await self.interrupt_current_task()
        
        # Отключаем LiveKit
        await self.livekit_client.disconnect()
        
        # Очищаем stream manager
        await self.stream_manager.cleanup()
        
        logger.info("HeyGen Frame Processor очищен")

class PipecatHeyGenBridge:
    """
    Мост между Pipecat и HeyGen для полной интеграции
    
    Этот класс будет использоваться для создания полноценного
    Pipecat pipeline с поддержкой HeyGen Interactive Avatar
    """
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.frame_processor = HeyGenFrameProcessor(session_manager)
        self.pipeline = None  # Будет содержать Pipecat pipeline
    
    async def create_pipeline(self):
        """Создать Pipecat pipeline с HeyGen интеграцией"""
        # В будущем здесь будет создание полного Pipecat pipeline
        # с интеграцией аудио/видео обработки и HeyGen API
        
        logger.info("Создание Pipecat pipeline...")
        
        # Инициализируем frame processor
        success = await self.frame_processor.initialize()
        if not success:
            logger.error("Не удалось инициализировать frame processor")
            return False
        
        # Здесь будет создание реального Pipecat pipeline
        # Например:
        # self.pipeline = Pipeline([
        #     AudioInputProcessor(),
        #     STTProcessor(),
        #     self.frame_processor,
        #     AudioOutputProcessor(),
        #     VideoOutputProcessor()
        # ])
        
        logger.info("Pipecat pipeline создан")
        return True
    
    async def start_pipeline(self):
        """Запустить pipeline"""
        if not self.pipeline:
            logger.error("Pipeline не создан")
            return False
        
        # Запуск реального Pipecat pipeline
        # await self.pipeline.start()
        
        logger.info("Pipecat pipeline запущен")
        return True
    
    async def stop_pipeline(self):
        """Остановить pipeline"""
        if self.pipeline:
            # await self.pipeline.stop()
            self.pipeline = None
        
        await self.frame_processor.cleanup()
        logger.info("Pipecat pipeline остановлен")
