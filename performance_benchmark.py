#!/usr/bin/env python3
"""
Тестирование производительности голосовых чат систем
Сравнение voice_chat_gemini.py vs voice_chat_gemini_pipecat.py
"""

import asyncio
import time
import psutil
import os
import sys
import json
import threading
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Метрики производительности"""
    system_name: str
    startup_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    response_times: List[float]
    avg_response_time: float
    peak_memory_mb: float
    total_api_calls: int
    errors_count: int
    test_duration: float

class PerformanceMonitor:
    """Монитор производительности"""
    
    def __init__(self, process_name: str):
        self.process_name = process_name
        self.start_time = time.time()
        self.monitoring = False
        self.memory_samples = []
        self.cpu_samples = []
        self.process = None
        
    def start_monitoring(self):
        """Запуск мониторинга"""
        self.monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Dict:
        """Остановка мониторинга и получение результатов"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2.0)
            
        return {
            'duration': time.time() - self.start_time,
            'avg_memory_mb': sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0,
            'peak_memory_mb': max(self.memory_samples) if self.memory_samples else 0,
            'avg_cpu_percent': sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0,
            'memory_samples': len(self.memory_samples),
            'cpu_samples': len(self.cpu_samples)
        }
    
    def _monitor_loop(self):
        """Цикл мониторинга"""
        while self.monitoring:
            try:
                # Найти процесс по имени
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if self.process_name in cmdline and 'python' in cmdline:
                            # Измеряем память
                            memory_info = proc.memory_info()
                            memory_mb = memory_info.rss / 1024 / 1024
                            self.memory_samples.append(memory_mb)
                            
                            # Измеряем CPU
                            cpu_percent = proc.cpu_percent()
                            self.cpu_samples.append(cpu_percent)
                            
                            self.process = proc
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
            except Exception as e:
                logger.error(f"Ошибка мониторинга: {e}")
                
            time.sleep(0.5)  # Замер каждые 500мс

class SystemTester:
    """Тестер системы"""
    
    def __init__(self, system_name: str, script_path: str):
        self.system_name = system_name
        self.script_path = script_path
        self.monitor = PerformanceMonitor(script_path)
        
    async def run_startup_test(self) -> float:
        """Тест времени запуска"""
        logger.info(f"🚀 Тестирование запуска {self.system_name}...")
        
        start_time = time.time()
        
        # Запускаем процесс
        process = await asyncio.create_subprocess_exec(
            'python', self.script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd='/Users/denol/Desktop/speekhead/lasttry'
        )
        
        # Ждем пока система инициализируется (ищем "Система готова")
        startup_time = None
        try:
            while True:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
                if not line:
                    break
                    
                line_str = line.decode().strip()
                logger.debug(f"{self.system_name}: {line_str}")
                
                # Ищем сигнал готовности
                if "Система готова" in line_str or "готова к голосовому чату" in line_str:
                    startup_time = time.time() - start_time
                    logger.info(f"✅ {self.system_name} запущен за {startup_time:.2f} сек")
                    break
                    
                # Ищем ошибки
                if "❌" in line_str or "ERROR" in line_str:
                    logger.error(f"❌ Ошибка в {self.system_name}: {line_str}")
                    
        except asyncio.TimeoutError:
            logger.error(f"❌ Таймаут запуска {self.system_name}")
            startup_time = 30.0  # максимальное время
            
        finally:
            # Завершаем процесс
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except:
                process.kill()
                
        return startup_time or 30.0
    
    async def run_memory_test(self, duration: int = 30) -> Dict:
        """Тест потребления памяти"""
        logger.info(f"💾 Тестирование памяти {self.system_name} ({duration}сек)...")
        
        # Запускаем мониторинг
        self.monitor.start_monitoring()
        
        # Запускаем процесс
        process = await asyncio.create_subprocess_exec(
            'python', self.script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            cwd='/Users/denol/Desktop/speekhead/lasttry'
        )
        
        # Ждем указанное время
        try:
            await asyncio.sleep(duration)
        finally:
            # Завершаем процесс
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except:
                process.kill()
                
        # Получаем результаты мониторинга
        results = self.monitor.stop_monitoring()
        
        logger.info(f"📊 {self.system_name} - Память: {results['avg_memory_mb']:.1f}MB (пик: {results['peak_memory_mb']:.1f}MB)")
        logger.info(f"📊 {self.system_name} - CPU: {results['avg_cpu_percent']:.1f}%")
        
        return results

class BenchmarkRunner:
    """Основной класс для запуска бенчмарков"""
    
    def __init__(self):
        self.systems = {
            'Классическая система': 'voice_chat_gemini.py',
            'Pipecat-Style система': 'voice_chat_gemini_pipecat.py'
        }
        self.results = {}
        
    async def run_all_benchmarks(self):
        """Запуск всех тестов"""
        logger.info("🔥 Запуск полного тестирования производительности...")
        logger.info("=" * 70)
        
        for system_name, script_path in self.systems.items():
            logger.info(f"\n🧪 Тестирование: {system_name}")
            logger.info("-" * 50)
            
            tester = SystemTester(system_name, script_path)
            
            # Тест запуска
            startup_time = await tester.run_startup_test()
            
            # Тест памяти (30 секунд)
            memory_results = await tester.run_memory_test(30)
            
            # Сохраняем результаты
            self.results[system_name] = {
                'startup_time': startup_time,
                'memory_results': memory_results
            }
            
            # Пауза между тестами
            await asyncio.sleep(5)
            
        # Выводим сравнение
        self.print_comparison()
        
        # Сохраняем в файл
        self.save_results()
    
    def print_comparison(self):
        """Вывод сравнения результатов"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 СРАВНЕНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
        logger.info("=" * 70)
        
        # Таблица результатов
        print("\n📋 Сводная таблица:")
        print("+" + "-" * 68 + "+")
        print(f"| {'Метрика':<25} | {'Классическая':<18} | {'Pipecat-Style':<18} |")
        print("+" + "-" * 68 + "+")
        
        if len(self.results) >= 2:
            classic = list(self.results.values())[0]
            pipecat = list(self.results.values())[1]
            
            print(f"| {'Время запуска':<25} | {classic['startup_time']:<17.2f}s | {pipecat['startup_time']:<17.2f}s |")
            print(f"| {'Средняя память':<25} | {classic['memory_results']['avg_memory_mb']:<17.1f}MB | {pipecat['memory_results']['avg_memory_mb']:<17.1f}MB |")
            print(f"| {'Пиковая память':<25} | {classic['memory_results']['peak_memory_mb']:<17.1f}MB | {pipecat['memory_results']['peak_memory_mb']:<17.1f}MB |")
            print(f"| {'Средний CPU':<25} | {classic['memory_results']['avg_cpu_percent']:<17.1f}% | {pipecat['memory_results']['avg_cpu_percent']:<17.1f}% |")
            
            print("+" + "-" * 68 + "+")
            
            # Выводы
            print("\n🏆 ВЫВОДЫ:")
            
            # Сравнение запуска
            if classic['startup_time'] < pipecat['startup_time']:
                diff = pipecat['startup_time'] - classic['startup_time']
                print(f"⚡ Классическая система запускается на {diff:.2f}с быстрее")
            else:
                diff = classic['startup_time'] - pipecat['startup_time']
                print(f"⚡ Pipecat-Style система запускается на {diff:.2f}с быстрее")
                
            # Сравнение памяти
            classic_mem = classic['memory_results']['avg_memory_mb']
            pipecat_mem = pipecat['memory_results']['avg_memory_mb']
            
            if classic_mem < pipecat_mem:
                diff = pipecat_mem - classic_mem
                pct = (diff / classic_mem) * 100
                print(f"💾 Классическая система использует на {diff:.1f}MB ({pct:.1f}%) меньше памяти")
            else:
                diff = classic_mem - pipecat_mem
                pct = (diff / pipecat_mem) * 100
                print(f"💾 Pipecat-Style система использует на {diff:.1f}MB ({pct:.1f}%) меньше памяти")
                
            # Сравнение CPU
            classic_cpu = classic['memory_results']['avg_cpu_percent']
            pipecat_cpu = pipecat['memory_results']['avg_cpu_percent']
            
            if classic_cpu < pipecat_cpu:
                diff = pipecat_cpu - classic_cpu
                print(f"🔥 Классическая система использует на {diff:.1f}% меньше CPU")
            else:
                diff = classic_cpu - pipecat_cpu
                print(f"🔥 Pipecat-Style система использует на {diff:.1f}% меньше CPU")
    
    def save_results(self):
        """Сохранение результатов в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_results_{timestamp}.json"
        
        # Добавляем метаданные
        results_with_meta = {
            'timestamp': timestamp,
            'test_date': datetime.now().isoformat(),
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cpu_count': psutil.cpu_count(),
                'total_memory_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024
            },
            'results': self.results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_with_meta, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n💾 Результаты сохранены в: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения результатов: {e}")

async def main():
    """Главная функция"""
    print("🔥 Бенчмарк производительности голосовых чат систем")
    print("=" * 60)
    print("🎯 Сравнение: voice_chat_gemini.py vs voice_chat_gemini_pipecat.py")
    print("📊 Метрики: время запуска, память, CPU")
    print("⏱️  Длительность: ~2-3 минуты")
    print("=" * 60)
    
    # Проверяем наличие файлов
    required_files = ['voice_chat_gemini.py', 'voice_chat_gemini_pipecat.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Файл {file} не найден!")
            return
    
    print("✅ Все необходимые файлы найдены")
    
    # Запускаем тесты
    runner = BenchmarkRunner()
    await runner.run_all_benchmarks()
    
    print("\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    asyncio.run(main())
