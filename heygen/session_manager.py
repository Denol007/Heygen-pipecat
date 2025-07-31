import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any, List
from .config import Config

logger = logging.getLogger(__name__)

class HeyGenSessionManager:
    """Менеджер для управления HeyGen streaming сессиями"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.HEYGEN_API_KEY
        self.base_url = Config.HEYGEN_BASE_URL
        self.session_id: Optional[str] = None
        self.websocket_url: Optional[str] = None
        self.access_token: Optional[str] = None
        self.session_duration_limit: Optional[int] = None
        self.realtime_endpoint: Optional[str] = None
        self.is_active = False
        
        if not self.api_key:
            raise ValueError("API ключ HeyGen не найден")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Заголовки для HTTP запросов"""
        return {
            'accept': 'application/json',
            'content-type': 'application/json',
            'x-api-key': self.api_key
        }
    
    async def get_available_avatars(self) -> List[Dict[str, Any]]:
        """Получить список доступных аватаров"""
        url = f"{self.base_url}/streaming/avatar.list"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('data', [])
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка получения аватаров: {response.status} - {error_text}")
                    return []
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """Получить список активных сессий"""
        url = f"{self.base_url}/streaming.list"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                try:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Ответ от API: {data}")
                        
                        # Проверяем тип данных
                        if isinstance(data, dict):
                            sessions_data = data.get('data', {})
                            if isinstance(sessions_data, dict) and 'sessions' in sessions_data:
                                # Формат: {'data': {'sessions': [...]}}
                                return sessions_data['sessions']
                            elif isinstance(sessions_data, list):
                                # Формат: {'data': [...]}
                                return sessions_data
                            else:
                                return data.get('data', [])
                        elif isinstance(data, list):
                            return data
                        else:
                            logger.warning(f"Неожиданный тип данных от API: {type(data)}")
                            return []
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения активных сессий: {response.status} - {error_text}")
                        return []
                except Exception as e:
                    logger.error(f"Ошибка парсинга ответа от API: {e}")
                    error_text = await response.text()
                    logger.error(f"Содержимое ответа: {error_text}")
                    return []
    
    async def close_all_active_sessions(self):
        """Закрыть все активные сессии (для обеспечения единственной сессии)"""
        try:
            active_sessions = await self.list_active_sessions()
            logger.info(f"Найдено активных сессий: {len(active_sessions)}")
            
            for session in active_sessions:
                if isinstance(session, dict):
                    session_id = session.get('session_id')
                    if session_id:
                        await self._close_session_by_id(session_id)
                        logger.info(f"Закрыта активная сессия: {session_id}")
                    else:
                        logger.warning(f"Сессия без ID: {session}")
                else:
                    logger.warning(f"Неожиданный тип сессии: {type(session)} - {session}")
        except Exception as e:
            logger.error(f"Ошибка при закрытии активных сессий: {e}")
            # Продолжаем выполнение, так как это не критическая ошибка
    
    async def _close_session_by_id(self, session_id: str):
        """Закрыть сессию по ID"""
        url = f"{self.base_url}/streaming.stop"
        data = {"session_id": session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status != 200:
                    logger.error(f"Ошибка закрытия сессии {session_id}: {response.status}")
    
    async def create_session(
        self, 
        avatar_id: str = None, 
        quality: str = None,
        voice_settings: Dict[str, Any] = None
    ) -> bool:
        """Создать новую streaming сессию"""
        url = f"{self.base_url}/streaming.new"
        
        # Подготовка данных запроса
        request_data = {
            "quality": quality or Config.DEFAULT_QUALITY,
            "avatar_id": avatar_id or Config.DEFAULT_AVATAR_ID,
            "version": "v2",
            "video_encoding": "VP8",
            "disable_idle_timeout": False,
            "activity_idle_timeout": Config.IDLE_TIMEOUT
        }
        
        # Добавляем настройки голоса если указаны
        if voice_settings:
            request_data["voice"] = voice_settings
        else:
            request_data["voice"] = {"rate": Config.DEFAULT_VOICE_RATE}
        
        logger.info(f"Создание сессии с параметрами: {request_data}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=request_data) as response:
                try:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Ответ создания сессии: {data}")
                        
                        if isinstance(data, dict):
                            session_data = data.get('data', {})
                        else:
                            logger.error(f"Неожиданный формат ответа: {type(data)}")
                            return False
                        
                        self.session_id = session_data.get('session_id')
                        self.websocket_url = session_data.get('url')
                        self.access_token = session_data.get('access_token')
                        self.session_duration_limit = session_data.get('session_duration_limit')
                        self.realtime_endpoint = session_data.get('realtime_endpoint')
                        
                        if self.session_id:
                            logger.info(f"Сессия создана: {self.session_id}")
                            return True
                        else:
                            logger.error("Не получен session_id от API")
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка создания сессии: {response.status} - {error_text}")
                        return False
                except Exception as e:
                    logger.error(f"Ошибка при создании сессии: {e}")
                    error_text = await response.text()
                    logger.error(f"Содержимое ответа: {error_text}")
                    return False
    
    async def start_session(self) -> bool:
        """Запустить созданную сессию"""
        if not self.session_id:
            logger.error("Сессия не создана")
            return False
        
        url = f"{self.base_url}/streaming.start"
        data = {"session_id": self.session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    self.is_active = True
                    logger.info(f"Сессия запущена: {self.session_id}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка запуска сессии: {response.status} - {error_text}")
                    return False
    
    async def send_task(
        self, 
        text: str, 
        task_type: str = "repeat",
        task_mode: str = "sync"
    ) -> Optional[Dict[str, Any]]:
        """Отправить задачу аватару"""
        if not self.session_id:
            logger.error("Сессия не активна")
            return None
        
        url = f"{self.base_url}/streaming.task"
        data = {
            "session_id": self.session_id,
            "text": text,
            "task_type": task_type,
            "task_mode": task_mode
        }
        
        logger.info(f"Отправка задачи: {text[:50]}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Задача отправлена, ответ API: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка отправки задачи: {response.status} - {error_text}")
                    return None

    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить результат выполнения задачи"""
        if not self.session_id:
            logger.error("Сессия не активна")
            return None
        
        # Пробуем разные возможные endpoints
        possible_urls = [
            f"{self.base_url}/streaming.task.result/{task_id}",
            f"{self.base_url}/streaming/task/{task_id}",
            f"{self.base_url}/streaming/task/{task_id}/result",
            f"{self.base_url}/streaming.task/{task_id}/status",
            f"{self.base_url}/task/{task_id}",
        ]
        
        for url in possible_urls:
            logger.debug(f"Пробуем endpoint: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"Результат задачи {task_id} с {url}: {result}")
                        return result
                    else:
                        logger.debug(f"Endpoint {url} недоступен: {response.status}")
        
        logger.error(f"Не найден рабочий endpoint для получения результата задачи {task_id}")
        return None

    async def download_task_video(self, task_id: str, output_path: str) -> bool:
        """Скачать видео результат задачи"""
        # Сначала получаем информацию о задаче
        task_result = await self.get_task_result(task_id)
        if not task_result:
            logger.error(f"Не удалось получить информацию о задаче {task_id}")
            return False
        
        # Извлекаем URL видео из результата
        data = task_result.get('data', {})
        video_url = data.get('video_url') or data.get('url') or data.get('result_url')
        
        if not video_url:
            logger.error(f"Видео URL не найден в результате задачи {task_id}")
            logger.debug(f"Доступные поля: {list(data.keys())}")
            return False
        
        logger.info(f"Скачивание видео с {video_url} в {output_path}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    if response.status == 200:
                        with open(output_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        logger.info(f"Видео сохранено: {output_path}")
                        return True
                    else:
                        logger.error(f"Ошибка скачивания видео: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Ошибка при скачивании видео: {e}")
            return False
    
    async def interrupt_task(self) -> bool:
        """Прервать текущую задачу аватара"""
        if not self.session_id:
            logger.error("Сессия не активна")
            return False
        
        url = f"{self.base_url}/streaming.interrupt"
        data = {"session_id": self.session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    logger.info("Задача прервана")
                    return True
                else:
                    logger.error(f"Ошибка прерывания задачи: {response.status}")
                    return False
    
    async def keep_alive(self) -> bool:
        """Поддержать сессию активной"""
        if not self.session_id:
            return False
        
        url = f"{self.base_url}/streaming.keep_alive"
        data = {"session_id": self.session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    logger.debug("Keep-alive отправлен")
                    return True
                else:
                    logger.error(f"Ошибка keep-alive: {response.status}")
                    return False
    
    async def close_session(self) -> bool:
        """Закрыть текущую сессию"""
        if not self.session_id:
            return True
        
        url = f"{self.base_url}/streaming.stop"
        data = {"session_id": self.session_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 200:
                    logger.info(f"Сессия закрыта: {self.session_id}")
                    self._reset_session()
                    return True
                else:
                    logger.error(f"Ошибка закрытия сессии: {response.status}")
                    return False
    
    def _reset_session(self):
        """Сбросить данные сессии"""
        self.session_id = None
        self.websocket_url = None
        self.access_token = None
        self.session_duration_limit = None
        self.is_active = False
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.is_active:
            await self.close_session()
