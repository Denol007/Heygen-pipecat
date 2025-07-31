import asyncio
import logging
import json
import cv2
import numpy as np
import time
import websockets
from typing import Optional, Callable
from datetime import datetime
import os
from urllib.parse import urlencode
import tempfile
import wave
import subprocess

from livekit import rtc
from livekit.rtc import Room, RoomOptions, VideoFrame, AudioFrame, TrackKind, VideoBufferType
import aiohttp

try:
    from scipy.io import wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class HeyGenLiveKitClient:
    """Клиент для подключения к HeyGen через LiveKit"""
    
    def __init__(self):
        self.room: Optional[Room] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_recording = False
        self.current_task_id: Optional[str] = None
        self.output_directory = "outputs"
        
        # Создать директорию для выходных файлов
        os.makedirs(self.output_directory, exist_ok=True)
        
        # Хранилище кадров для записи
        self.video_frames = []
        self.audio_frames = []
        self.recording_start_time = None
    
    async def connect_websocket_events(self, session_id: str, session_token: str, server_url: str) -> bool:
        """Подключиться к WebSocket для мониторинга событий аватара"""
        try:
            # Создать WebSocket URL для мониторинга событий
            params = {
                'session_id': session_id,
                'session_token': session_token,
                'silence_response': 'false'
            }
            
            # Извлечь hostname из server_url
            from urllib.parse import urlparse
            parsed_url = urlparse(server_url)
            hostname = parsed_url.hostname
            
            ws_url = f"wss://{hostname}/v1/ws/streaming.chat?{urlencode(params)}"
            logger.info(f"Подключение к WebSocket: {ws_url}")
            
            self.websocket = await websockets.connect(ws_url)
            
            # Запустить обработчик событий WebSocket в фоне
            asyncio.create_task(self._handle_websocket_events())
            
            logger.info("WebSocket для событий подключен")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения WebSocket: {e}")
            return False
    
    async def _handle_websocket_events(self):
        """Обработчик событий WebSocket"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"WebSocket событие: {data}")
                    
                    # Обработать различные типы событий
                    event_type = data.get('type')
                    if event_type == 'avatar_start_talking':
                        logger.info("Аватар начал говорить")
                    elif event_type == 'avatar_stop_talking':
                        logger.info("Аватар закончил говорить")
                    elif event_type == 'task_finished':
                        logger.info(f"Задача завершена: {data}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Не удалось парсить WebSocket сообщение: {message}")
                    
        except Exception as e:
            logger.error(f"Ошибка в обработчике WebSocket: {e}")
        
    async def connect(self, url: str, access_token: str, session_id: str = None, server_url: str = None) -> bool:
        """Подключиться к LiveKit room"""
        try:
            logger.info(f"Подключение к LiveKit room: {url}")
            
            # Создать room без опций (используем значения по умолчанию)
            self.room = Room()
            
            # Добавить обработчики событий
            @self.room.on("track_subscribed")
            def on_track_subscribed(track, publication, participant):
                logger.info(f"Track subscribed: {track.kind} from {participant.identity}")
                if track.kind == TrackKind.KIND_VIDEO:
                    asyncio.create_task(self._handle_video_track(track))
                elif track.kind == TrackKind.KIND_AUDIO:
                    asyncio.create_task(self._handle_audio_track(track))
            
            @self.room.on("disconnected")
            def on_disconnected(reason):
                logger.info(f"Отключен от room: {reason}")
                self.is_connected = False
            
            @self.room.on("participant_connected")
            def on_participant_connected(participant):
                logger.info(f"Участник подключился: {participant.identity}")
            
            # Подключиться к room
            await self.room.connect(url, access_token)
            self.is_connected = True
            logger.info("Успешно подключен к LiveKit room")
            
            # Подключить WebSocket для событий если указаны параметры
            if session_id and server_url:
                await self.connect_websocket_events(session_id, access_token, server_url)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к LiveKit: {e}")
            return False
            
            # Создать room с опциями
            options = RoomOptions(
                auto_subscribe=True,
                dynacast=True,
                adaptive_stream=True
            )
            
            self.room = Room(options=options)
            
            # Добавить обработчики событий
            def on_track_subscribed(track, publication, participant):
                logger.info(f"Track subscribed: {track.kind}")
                if track.kind == TrackKind.KIND_VIDEO:
                    # Подписываемся на видео кадры
                    track.on("frame_received", self._on_video_frame)
                elif track.kind == TrackKind.KIND_AUDIO:
                    # Подписываемся на аудио кадры
                    track.on("frame_received", self._on_audio_frame)
            
            def on_disconnected(reason):
                logger.info(f"Отключен от room: {reason}")
                self.is_connected = False
            
            def on_participant_connected(participant):
                logger.info(f"Участник подключился: {participant.identity}")
            
            # Регистрируем обработчики
            self.room.on("track_subscribed", on_track_subscribed)
            self.room.on("disconnected", on_disconnected)
            self.room.on("participant_connected", on_participant_connected)
            
            # Подключиться к room
            await self.room.connect(url, access_token)
            self.is_connected = True
            logger.info("Успешно подключен к LiveKit room")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка подключения к LiveKit: {e}")
            return False
    
    async def _handle_video_track(self, track):
        """Обработчик видео трека"""
        try:
            logger.info(f"Обработка видео трека: {track}")
            
            # Создать VideoStream для получения кадров
            video_stream = rtc.VideoStream(track)
            
            # Запустить обработку кадров в фоне
            asyncio.create_task(self._process_video_stream(video_stream))
                    
        except Exception as e:
            logger.error(f"Ошибка обработки видео трека: {e}")
    
    async def _handle_audio_track(self, track):
        """Обработчик аудио трека"""
        try:
            logger.info(f"Обработка аудио трека: {track}")
            
            # Создать AudioStream для получения кадров
            audio_stream = rtc.AudioStream(track)
            
            # Запустить обработку кадров в фоне
            asyncio.create_task(self._process_audio_stream(audio_stream))
                    
        except Exception as e:
            logger.error(f"Ошибка обработки аудио трека: {e}")
    
    async def _process_video_stream(self, video_stream):
        """Обработка видео потока"""
        try:
            async for frame_event in video_stream:
                if self.is_recording:
                    await self._process_video_frame(frame_event.frame)
        except Exception as e:
            logger.error(f"Ошибка обработки видео потока: {e}")
    
    async def _process_audio_stream(self, audio_stream):
        """Обработка аудио потока"""
        try:
            async for frame_event in audio_stream:
                if self.is_recording:
                    await self._process_audio_frame(frame_event.frame)
        except Exception as e:
            logger.error(f"Ошибка обработки аудио потока: {e}")
    
    async def _process_video_frame(self, frame: VideoFrame):
        """Обработать видео кадр"""
        try:
            if self.is_recording:
                # Конвертировать VideoFrame в RGB24 формат
                rgb_frame = frame.convert(VideoBufferType.RGB24)
                
                # Получить данные кадра
                width = rgb_frame.width
                height = rgb_frame.height
                
                # Получить данные как bytes и конвертировать в numpy array
                frame_data = rgb_frame.data
                
                # Создать numpy array из bytes данных
                frame_array = np.frombuffer(frame_data, dtype=np.uint8)
                frame_array = frame_array.reshape((height, width, 3))
                
                # Конвертировать RGB в BGR для OpenCV
                img_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
                
                # Добавить временную метку
                timestamp = time.time()
                self.video_frames.append({
                    'frame': img_bgr,
                    'timestamp': timestamp
                })
                
                logger.debug(f"Захвачен видео кадр: {width}x{height}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки видео кадра: {e}")
    
    async def _process_audio_frame(self, frame: AudioFrame):
        """Обработать аудио кадр"""
        try:
            if self.is_recording:
                # Сохранить аудио данные
                timestamp = time.time()
                self.audio_frames.append({
                    'data': frame.data,
                    'sample_rate': frame.sample_rate,
                    'channels': frame.num_channels,
                    'timestamp': timestamp
                })
                
                logger.debug(f"Захвачен аудио кадр: {frame.sample_rate}Hz, {frame.num_channels} каналов")
                
        except Exception as e:
            logger.error(f"Ошибка обработки аудио кадра: {e}")
    
    async def start_recording(self, task_id: str) -> Optional[str]:
        """Начать запись видео/аудио"""
        if not self.is_connected:
            logger.error("LiveKit не подключен")
            return None
            
        if self.is_recording:
            logger.warning("Запись уже идет")
            return None
        
        try:
            self.current_task_id = task_id
            self.is_recording = True
            self.recording_start_time = time.time()
            self.video_frames = []
            self.audio_frames = []
            
            logger.info(f"Начата запись для задачи: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Ошибка начала записи: {e}")
            return None
    
    def _check_ffmpeg_available(self) -> bool:
        """Проверить доступность FFmpeg в системе"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False

    async def _merge_video_audio_with_ffmpeg(self, video_path: str, audio_path: str, output_path: str) -> bool:
        """Объединить видео и аудио с помощью системного FFmpeg"""
        try:
            # Проверить наличие файлов
            if not os.path.exists(video_path):
                logger.error(f"Видео файл не найден: {video_path}")
                return False
                
            if not os.path.exists(audio_path):
                logger.error(f"Аудио файл не найден: {audio_path}")
                return False
            
            # Команда FFmpeg для объединения видео и аудио
            cmd = [
                'ffmpeg',
                '-i', video_path,  # Входное видео
                '-i', audio_path,  # Входное аудио
                '-c:v', 'copy',    # Копировать видео без перекодирования
                '-c:a', 'aac',     # Кодировать аудио в AAC
                '-shortest',       # Остановиться когда закончится самый короткий поток
                '-y',              # Перезаписать выходной файл если существует
                output_path
            ]
            
            logger.info(f"Объединение видео и аудио с помощью FFmpeg...")
            
            # Выполнить команду
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Таймаут 30 секунд
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Видео с аудио создано: {output_path}")
                return True
            else:
                logger.error(f"❌ Ошибка FFmpeg: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Таймаут выполнения FFmpeg")
            return False
        except FileNotFoundError:
            logger.error("❌ FFmpeg не найден в системе")
            logger.info("💡 Установите FFmpeg: brew install ffmpeg")
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка объединения: {e}")
            return False
        """Сохранить аудио кадры в WAV файл"""
        try:
            if not self.audio_frames:
                logger.warning("Нет аудио кадров для сохранения")
                return False
            
            # Определить параметры аудио из первого кадра
            if self.audio_frames:
                first_frame = self.audio_frames[0]
                sample_rate = first_frame['sample_rate']
                channels = first_frame['channels']
            else:
                return False
            
            # Объединить все аудио данные
            audio_data = []
            for frame_info in self.audio_frames:
                # Конвертировать bytes в numpy array
                frame_data = np.frombuffer(frame_info['data'], dtype=np.int16)
                audio_data.append(frame_data)
            
            if audio_data:
                # Объединить все аудио кадры
                combined_audio = np.concatenate(audio_data)
                
                # Сохранить как WAV файл
                if SCIPY_AVAILABLE:
                    from scipy.io import wavfile
                    wavfile.write(audio_path, sample_rate, combined_audio)
                else:
                    # Альтернативный способ через wave модуль
                    with wave.open(audio_path, 'wb') as wav_file:
                        wav_file.setnchannels(channels)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(combined_audio.tobytes())
                
                logger.info(f"Аудио сохранено: {audio_path} ({len(self.audio_frames)} кадров)")
                return True
            else:
                logger.warning("Нет аудио данных для сохранения")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка сохранения аудио: {e}")
            return False

    async def _save_audio_to_wav(self, audio_path: str) -> bool:
        """Сохранить аудио кадры в WAV файл"""
        try:
            if not self.audio_frames:
                logger.warning("Нет аудио кадров для сохранения")
                return False
            
            # Определить параметры аудио из первого кадра
            if self.audio_frames:
                first_frame = self.audio_frames[0]
                sample_rate = first_frame['sample_rate']
                channels = first_frame['channels']
            else:
                return False
            
            # Объединить все аудио данные
            audio_data = []
            for frame_info in self.audio_frames:
                # Конвертировать bytes в numpy array
                frame_data = np.frombuffer(frame_info['data'], dtype=np.int16)
                audio_data.append(frame_data)
            
            if audio_data:
                # Объединить все аудио кадры
                combined_audio = np.concatenate(audio_data)
                
                # Сохранить как WAV файл
                if SCIPY_AVAILABLE:
                    from scipy.io import wavfile
                    wavfile.write(audio_path, sample_rate, combined_audio)
                else:
                    # Альтернативный способ через wave модуль
                    with wave.open(audio_path, 'wb') as wav_file:
                        wav_file.setnchannels(channels)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(sample_rate)
                        wav_file.writeframes(combined_audio.tobytes())
                
                logger.info(f"Аудио сохранено: {audio_path} ({len(self.audio_frames)} кадров)")
                return True
            else:
                logger.warning("Нет аудио данных для сохранения")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка сохранения аудио: {e}")
            return False

    async def stop_recording(self) -> Optional[str]:
        """Остановить запись и сохранить файлы с аудио"""
        if not self.is_recording:
            logger.warning("Запись не активна")
            return None
        
        try:
            self.is_recording = False
            
            if not self.video_frames:
                logger.warning("Нет видео кадров для сохранения")
                return None
            
            # Создать уникальные имена файлов
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_suffix = f"_{self.current_task_id}" if self.current_task_id else ""
            base_filename = f"avatar_response_{timestamp}{task_suffix}"
            
            video_only_path = os.path.join(self.output_directory, f"{base_filename}_video_only.mp4")
            audio_path = os.path.join(self.output_directory, f"{base_filename}.wav")
            final_video_path = os.path.join(self.output_directory, f"{base_filename}.mp4")
            
            # Сохранить видео без аудио
            if self.video_frames:
                first_frame = self.video_frames[0]['frame']
                height, width = first_frame.shape[:2]
                fps = 30  # Предполагаемый FPS
                
                # Создать VideoWriter для видео без звука
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(video_only_path, fourcc, fps, (width, height))
                
                # Записать все кадры
                for frame_data in self.video_frames:
                    video_writer.write(frame_data['frame'])
                
                video_writer.release()
                logger.info(f"Видео (без звука) сохранено: {video_only_path}")
            
            # Сохранить аудио
            audio_saved = await self._save_audio_to_wav(audio_path)
            
            # Объединить видео и аудио, если доступен FFmpeg
            if audio_saved and self._check_ffmpeg_available():
                try:
                    logger.info("Объединение видео и аудио...")
                    
                    # Объединить с помощью FFmpeg
                    merge_success = await self._merge_video_audio_with_ffmpeg(
                        video_only_path, audio_path, final_video_path
                    )
                    
                    if merge_success:
                        # Удалить временные файлы
                        if os.path.exists(video_only_path):
                            os.remove(video_only_path)
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                        
                        logger.info(f"Видео с аудио сохранено: {final_video_path}")
                        logger.info(f"Записано видео кадров: {len(self.video_frames)}")
                        logger.info(f"Записано аудио кадров: {len(self.audio_frames)}")
                        
                        return final_video_path
                    else:
                        logger.error("Не удалось объединить видео и аудио")
                        return video_only_path
                        
                except Exception as e:
                    logger.error(f"Ошибка объединения видео и аудио: {e}")
                    # Если объединение не удалось, вернуть видео без звука
                    return video_only_path
            else:
                # Если нет аудио или FFmpeg недоступен, вернуть видео без звука
                if not audio_saved:
                    logger.warning("Аудио не сохранено, возвращаем видео без звука")
                if not self._check_ffmpeg_available():
                    logger.warning("FFmpeg недоступен, возвращаем видео без звука")
                    
                return video_only_path
                
        except Exception as e:
            logger.error(f"Ошибка сохранения записи: {e}")
            return None
        finally:
            self.current_task_id = None
            self.video_frames = []
            self.audio_frames = []
    
    async def send_message(self, message: str, task_id: str = None) -> bool:
        """Отправить сообщение через LiveKit room (если поддерживается)"""
        try:
            if not self.is_connected or not self.room:
                logger.error("LiveKit не подключен")
                return False
            
            # LiveKit может поддерживать отправку данных через data channel
            # Но для HeyGen нужно использовать HTTP API для отправки задач
            logger.info("Отправка сообщений происходит через HTTP API, не через LiveKit")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def disconnect(self):
        """Отключиться от LiveKit room"""
        try:
            if self.is_recording:
                await self.stop_recording()
            
            # Закрыть WebSocket соединение
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                logger.info("WebSocket закрыт")
            
            # Отключиться от LiveKit room
            if self.room:
                await self.room.disconnect()
                logger.info("Отключен от LiveKit room")
            
            self.is_connected = False
            self.room = None
            
        except Exception as e:
            logger.error(f"Ошибка отключения от LiveKit: {e}")
    
    def get_recording_stats(self) -> dict:
        """Получить статистику записи"""
        return {
            "is_recording": self.is_recording,
            "current_task_id": self.current_task_id,
            "video_frames_count": len(self.video_frames),
            "audio_frames_count": len(self.audio_frames),
            "recording_duration": time.time() - self.recording_start_time if self.recording_start_time else 0
        }
