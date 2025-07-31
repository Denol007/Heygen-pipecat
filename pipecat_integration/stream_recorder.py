import asyncio
import logging
import os
from datetime import datetime
from typing import Optional
import cv2
import numpy as np
from heygen.config import Config

logger = logging.getLogger(__name__)

class StreamRecorder:
    """Класс для записи видео и аудио потоков"""
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.current_recording: Optional[cv2.VideoWriter] = None
        self.recording_filename: Optional[str] = None
        self.is_recording = False
        
        # Создаем папку для выходных файлов
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_filename(self, prefix: str = "avatar_response") -> str:
        """Генерировать имя файла с timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.{Config.VIDEO_FORMAT}"
        return os.path.join(self.output_dir, filename)
    
    def start_recording(self, width: int = 720, height: int = 480, fps: int = 30) -> str:
        """Начать запись видео"""
        if self.is_recording:
            self.stop_recording()
        
        self.recording_filename = self.generate_filename()
        
        # Настройка кодека
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Создание VideoWriter
        self.current_recording = cv2.VideoWriter(
            self.recording_filename,
            fourcc,
            fps,
            (width, height)
        )
        
        if self.current_recording.isOpened():
            self.is_recording = True
            logger.info(f"Начата запись: {self.recording_filename}")
            return self.recording_filename
        else:
            logger.error("Не удалось начать запись")
            return None
    
    def add_frame(self, frame: np.ndarray):
        """Добавить кадр в запись"""
        if self.is_recording and self.current_recording:
            self.current_recording.write(frame)
    
    def stop_recording(self) -> Optional[str]:
        """Остановить запись и вернуть путь к файлу"""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        filename = self.recording_filename
        
        if self.current_recording:
            self.current_recording.release()
            self.current_recording = None
        
        logger.info(f"Запись остановлена: {filename}")
        return filename
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self.is_recording:
            self.stop_recording()

class WebSocketStreamHandler:
    """Обработчик WebSocket потока от HeyGen"""
    
    def __init__(self, websocket_url: str, access_token: str):
        self.websocket_url = websocket_url
        self.access_token = access_token
        self.recorder = StreamRecorder()
        self.is_connected = False
        self.websocket = None
    
    async def connect(self) -> bool:
        """Подключиться к WebSocket"""
        try:
            # В будущем здесь будет реальное подключение к LiveKit WebSocket
            # import websockets
            # self.websocket = await websockets.connect(
            #     self.websocket_url,
            #     extra_headers={"Authorization": f"Bearer {self.access_token}"}
            # )
            
            # Пока что эмулируем подключение
            self.is_connected = True
            logger.info("WebSocket подключен (эмуляция)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения WebSocket: {e}")
            return False
    
    async def start_recording_session(self) -> str:
        """Начать сессию записи"""
        if not self.is_connected:
            logger.error("WebSocket не подключен")
            return None
        
        # Начинаем запись
        filename = self.recorder.start_recording()
        
        if filename:
            logger.info(f"Сессия записи начата: {filename}")
            
            # В реальной реализации здесь будет обработка WebRTC потока
            # Пока что эмулируем запись
            await self._simulate_recording()
            
        return filename
    
    async def _simulate_recording(self):
        """Эмуляция записи (для тестирования)"""
        # Создаем простой тестовый видео файл
        duration_seconds = 3
        fps = 30
        width, height = 720, 480
        
        for i in range(duration_seconds * fps):
            # Создаем простой кадр с текстом
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Добавляем текст на кадр
            text = f"Avatar Response Frame {i+1}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(frame, text, (50, height//2), font, 1, (255, 255, 255), 2)
            
            # Добавляем кадр в запись
            self.recorder.add_frame(frame)
            
            # Небольшая задержка для эмуляции реального времени
            await asyncio.sleep(1/fps)
    
    async def stop_recording_session(self) -> Optional[str]:
        """Остановить сессию записи"""
        filename = self.recorder.stop_recording()
        
        if filename:
            file_size = os.path.getsize(filename) if os.path.exists(filename) else 0
            logger.info(f"Запись сохранена: {filename} ({file_size} bytes)")
        
        return filename
    
    async def disconnect(self):
        """Отключиться от WebSocket"""
        self.is_connected = False
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        # Останавливаем запись если активна
        self.recorder.cleanup()
        
        logger.info("WebSocket отключен")

class HeyGenStreamManager:
    """Менеджер для управления потоками HeyGen"""
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.stream_handler: Optional[WebSocketStreamHandler] = None
        self.current_recording: Optional[str] = None
    
    async def initialize_stream(self) -> bool:
        """Инициализировать поток"""
        if not self.session_manager.websocket_url or not self.session_manager.access_token:
            logger.error("WebSocket URL или access token не найдены")
            return False
        
        self.stream_handler = WebSocketStreamHandler(
            self.session_manager.websocket_url,
            self.session_manager.access_token
        )
        
        return await self.stream_handler.connect()
    
    async def start_task_recording(self) -> Optional[str]:
        """Начать запись для задачи"""
        if not self.stream_handler:
            logger.error("Поток не инициализирован")
            return None
        
        self.current_recording = await self.stream_handler.start_recording_session()
        return self.current_recording
    
    async def stop_task_recording(self) -> Optional[str]:
        """Остановить запись задачи"""
        if not self.stream_handler:
            return None
        
        filename = await self.stream_handler.stop_recording_session()
        self.current_recording = None
        return filename
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.stream_handler:
            await self.stream_handler.disconnect()
            self.stream_handler = None
