#!/usr/bin/env python3
"""
Утилита для объединения видео и аудио файлов
Использует системный FFmpeg
"""

import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def merge_video_audio_with_ffmpeg(video_path: str, audio_path: str, output_path: str) -> bool:
    """
    Объединить видео и аудио с помощью системного FFmpeg
    """
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
        
        logger.info(f"Выполняем: {' '.join(cmd)}")
        
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

def check_ffmpeg_available() -> bool:
    """Проверить доступность FFmpeg в системе"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False
