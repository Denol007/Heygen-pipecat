import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # HeyGen API Configuration
    HEYGEN_API_KEY = os.getenv('HEYGEN_API_KEY')
    HEYGEN_BASE_URL = os.getenv('HEYGEN_BASE_URL', 'https://api.heygen.com/v1')
    
    # Default Avatar Settings
    DEFAULT_AVATAR_ID = os.getenv('DEFAULT_AVATAR_ID', 'default')
    DEFAULT_QUALITY = os.getenv('DEFAULT_QUALITY', 'medium')
    DEFAULT_VOICE_RATE = float(os.getenv('DEFAULT_VOICE_RATE', '1.0'))
    
    # Output Settings
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'outputs')
    VIDEO_FORMAT = os.getenv('VIDEO_FORMAT', 'mp4')
    
    # Session Settings
    IDLE_TIMEOUT = int(os.getenv('IDLE_TIMEOUT', '120'))
    KEEP_ALIVE_INTERVAL = int(os.getenv('KEEP_ALIVE_INTERVAL', '60'))
    
    @classmethod
    def validate(cls):
        """Проверка обязательных настроек"""
        if not cls.HEYGEN_API_KEY:
            raise ValueError("HEYGEN_API_KEY не установлен в .env файле")
        
        # Создаем папку для выходных файлов если не существует
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        
        return True
