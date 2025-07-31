#!/usr/bin/env python3
"""
Быстрый тест производительности голосовых систем
Измеряет время запуска и базовые метрики
"""

import time
import subprocess
import asyncio
import sys

async def test_startup_time(script_name):
    """Тест времени запуска системы"""
    print(f"⏱️  Тестирование времени запуска: {script_name}")
    
    start_time = time.time()
    
    # Запускаем процесс
    process = await asyncio.create_subprocess_exec(
        'python', script_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    startup_time = None
    try:
        # Ждем сигнал готовности
        while True:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=20.0)
            if not line:
                break
                
            line_str = line.decode().strip()
            
            # Ищем сигнал готовности системы
            if any(phrase in line_str for phrase in [
                "Система готова", 
                "готова к голосовому чату",
                "Говорите в микрофон"
            ]):
                startup_time = time.time() - start_time
                print(f"   ✅ {script_name}: {startup_time:.2f} секунд")
                break
                
    except asyncio.TimeoutError:
        print(f"   ❌ {script_name}: таймаут (>20 сек)")
        startup_time = 20.0
        
    finally:
        # Завершаем процесс
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except:
            try:
                process.kill()
            except:
                pass
    
    return startup_time

async def main():
    """Главная функция быстрого теста"""
    print("🚀 Быстрый тест производительности голосовых систем")
    print("=" * 60)
    
    systems = [
        "voice_chat_gemini.py",
        "voice_chat_gemini_pipecat.py"
    ]
    
    results = {}
    
    for system in systems:
        try:
            startup_time = await test_startup_time(system)
            results[system] = startup_time
        except Exception as e:
            print(f"   ❌ Ошибка тестирования {system}: {e}")
            results[system] = None
        
        # Пауза между тестами
        await asyncio.sleep(2)
    
    # Выводим сравнение
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
    print("=" * 60)
    
    classic_time = results.get("voice_chat_gemini.py")
    pipecat_time = results.get("voice_chat_gemini_pipecat.py")
    
    if classic_time and pipecat_time:
        diff = abs(classic_time - pipecat_time)
        faster_system = "Классическая" if classic_time < pipecat_time else "Pipecat-Style"
        
        print(f"⚡ Время запуска:")
        print(f"   voice_chat_gemini.py (Классическая): {classic_time:.2f}с")
        print(f"   voice_chat_gemini_pipecat.py (Pipecat): {pipecat_time:.2f}с")
        print(f"   🏆 {faster_system} система быстрее на {diff:.2f}с")
        
        # Процентное соотношение
        if classic_time > 0:
            overhead_pct = ((pipecat_time - classic_time) / classic_time) * 100
            if overhead_pct > 0:
                print(f"   📊 Pipecat-Style медленнее на {overhead_pct:.1f}%")
            else:
                print(f"   📊 Pipecat-Style быстрее на {abs(overhead_pct):.1f}%")
    
    print(f"\n💡 Для подробного сравнения см. PERFORMANCE_COMPARISON.md")
    print(f"🔍 Для мониторинга в реальном времени: python performance_monitor.py")

if __name__ == "__main__":
    asyncio.run(main())
