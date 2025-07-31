import asyncio
import logging
import json
import cv2
import numpy as np
import time
from typing import Optional, Callable
from datetime import datetime
import os

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, MediaStreamTrack
from aiortc.contrib.media import MediaRecorder
import aiohttp
import websockets

logger = logging.getLogger(__name__)

class HeyGenWebRTCClient:
    """
    WebRTC клиент для подключения к HeyGen Interactive Avatar
    """
    
    def __init__(self, session_manager):
        self.session_manager = session_manager
        self.pc: Optional[RTCPeerConnection] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.recorder: Optional[MediaRecorder] = None
        self.is_connected = False
        self.is_recording = False
        self.output_dir = "output"
        self.logger = logging.getLogger(__name__)
        
        # Callbacks для обработки данных
        self.on_video_frame: Optional[Callable] = None
        self.on_audio_frame: Optional[Callable] = None
        
    async def connect(self, realtime_endpoint: str, access_token: str) -> bool:
        """Подключиться к WebRTC endpoint"""
        try:
            self.logger.info(f"Подключение к WebRTC endpoint: {realtime_endpoint}")
            
            # Создать RTCPeerConnection
            self.pc = RTCPeerConnection()
            
            # Добавить обработчики событий
            self.pc.on("connectionstatechange", self._on_connection_state_change)
            self.pc.on("track", self._on_track)
            
            # Подключиться к WebSocket
            headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
            self.websocket = await websockets.connect(
                realtime_endpoint,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Создать и отправить offer
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            # Отправить offer через WebSocket с дополнительными полями
            offer_message = {
                "type": "offer",
                "sdp": self.pc.localDescription.sdp,
                "session_id": realtime_endpoint.split("/")[-1] if "/" in realtime_endpoint else None
            }
            
            await self.websocket.send(json.dumps(offer_message))
            self.logger.info("SDP offer отправлен")
            
            # Ждать ответ от сервера
            try:
                response = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=30.0
                )
                
                data = json.loads(response)
                self.logger.info(f"Получен ответ от сервера: {data}")
                
                if data.get("type") == "answer":
                    answer = RTCSessionDescription(
                        sdp=data["sdp"], 
                        type="answer"
                    )
                    await self.pc.setRemoteDescription(answer)
                    self.logger.info("Remote description установлен")
                    
                    self.is_connected = True
                    return True
                else:
                    self.logger.error(f"Неожиданный тип ответа: {data.get('type')}")
                    return False
                    
            except asyncio.TimeoutError:
                self.logger.error("Таймаут ожидания ответа от сервера")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка подключения WebRTC: {e}")
            return False
    
    async def _on_track(self, track: MediaStreamTrack):
        """Обработчик получения медиа трека"""
        logger.info(f"Получен трек: {track.kind}")
        
        if track.kind == "video":
            asyncio.create_task(self._process_video_track(track))
        elif track.kind == "audio":
            asyncio.create_task(self._process_audio_track(track))
    
    async def _process_video_track(self, track: VideoStreamTrack):
        """Обработка видео трека"""
        logger.info("Начата обработка видео трека")
        
        try:
            while True:
                frame = await track.recv()
                
                # Конвертируем frame в numpy array для OpenCV
                img = frame.to_ndarray(format="bgr24")
                
                # Вызываем callback если установлен
                if self.on_video_frame:
                    await self.on_video_frame(img)
                
                # Если идет запись, сохраняем кадр
                if self.is_recording and self.recorder:
                    await self.recorder.video_track.send(frame)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки видео: {e}")
    
    async def _process_audio_track(self, track):
        """Обработка аудио трека"""
        logger.info("Начата обработка аудио трека")
        
        try:
            while True:
                frame = await track.recv()
                
                # Вызываем callback если установлен
                if self.on_audio_frame:
                    await self.on_audio_frame(frame)
                
                # Если идет запись, сохраняем аудио
                if self.is_recording and self.recorder:
                    await self.recorder.audio_track.send(frame)
                    
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}")
    
    async def _on_connection_state_change(self):
        """Обработчик изменения состояния соединения"""
        try:
            if self.pc is None:
                return
                
            state = self.pc.connectionState
            logger.info(f"Состояние WebRTC соединения: {state}")
            
            if state == "failed" or state == "closed":
                self.is_connected = False
                await self.stop_recording()
        except Exception as e:
            logger.error(f"Ошибка в обработчике состояния: {e}")
    
    async def send_message(self, message: str, task_id: str = None) -> bool:
        """Отправить сообщение через WebRTC соединение"""
        try:
            if not self.is_connected or not self.websocket:
                self.logger.error("WebRTC не подключен")
                return False
                
            message_data = {
                "type": "message",
                "text": message,
                "task_id": task_id or f"task_{int(time.time())}"
            }
            
            await self.websocket.send(json.dumps(message_data))
            self.logger.info(f"Сообщение отправлено: {message}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return False

    async def start_recording(self, task_id: str) -> Optional[str]:
        """Начать запись видео/аудио"""
        if not self.is_connected:
            logger.error("WebRTC не подключен")
            return None
            
        if self.is_recording:
            logger.warning("Запись уже идет")
            return None
        
        try:
            # Создаем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"avatar_recording_{timestamp}_{task_id[:8]}.mp4"
            output_path = os.path.join(self.output_dir, filename)
            
            # Создаем директорию если не существует
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Создаем MediaRecorder
            self.recorder = MediaRecorder(output_path)
            
            self.is_recording = True
            logger.info(f"Начата запись в файл: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка начала записи: {e}")
            return None
    
    async def stop_recording(self) -> bool:
        """Остановить запись"""
        if not self.is_recording or not self.recorder:
            return True
            
        try:
            await self.recorder.stop()
            self.recorder = None
            self.is_recording = False
            logger.info("Запись остановлена")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return False
    
    async def disconnect(self):
        """Отключиться от WebRTC"""
        self.logger.info("Отключение от WebRTC...")
        
        # Останавливаем запись
        await self.stop_recording()
        
        # Закрываем WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        # Закрываем RTCPeerConnection
        if self.pc:
            await self.pc.close()
            self.pc = None
        
        self.is_connected = False
        self.logger.info("WebRTC отключен")
    
    def set_video_callback(self, callback: Callable):
        """Установить callback для обработки видео кадров"""
        self.on_video_frame = callback
    
    def set_audio_callback(self, callback: Callable):
        """Установить callback для обработки аудио кадров"""
        self.on_audio_frame = callback
