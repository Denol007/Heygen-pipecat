#!/usr/bin/env python3
"""
Простой скрипт для ручного измерения производительности
Запустите этот скрипт в отдельном терминале во время работы голосовых систем
"""

import psutil
import time
import sys
from datetime import datetime

def find_voice_chat_processes():
    """Найти запущенные процессы голосового чата"""
    processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'voice_chat_gemini' in cmdline and 'python' in cmdline:
                # Определяем тип системы
                if 'pipecat' in cmdline:
                    system_type = "Pipecat-Style"
                else:
                    system_type = "Классическая"
                
                processes.append({
                    'pid': proc.info['pid'],
                    'type': system_type,
                    'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                    'cpu_percent': proc.cpu_percent(),
                    'process': proc
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return processes

def monitor_performance(duration_seconds=60):
    """Мониторинг производительности в реальном времени"""
    print(f"🔍 Мониторинг производительности ({duration_seconds} секунд)")
    print("=" * 80)
    print(f"{'Время':<8} | {'Система':<15} | {'PID':<8} | {'Память':<10} | {'CPU':<8}")
    print("-" * 80)
    
    start_time = time.time()
    measurements = []
    
    try:
        while time.time() - start_time < duration_seconds:
            timestamp = datetime.now().strftime("%H:%M:%S")
            processes = find_voice_chat_processes()
            
            if not processes:
                print(f"{timestamp} | Нет запущенных процессов голосового чата")
            else:
                for proc_info in processes:
                    memory_mb = proc_info['memory_mb']
                    cpu_percent = proc_info['cpu_percent']
                    
                    print(f"{timestamp} | {proc_info['type']:<15} | {proc_info['pid']:<8} | {memory_mb:<9.1f}MB | {cpu_percent:<7.1f}%")
                    
                    # Сохраняем измерения
                    measurements.append({
                        'timestamp': timestamp,
                        'type': proc_info['type'],
                        'memory_mb': memory_mb,
                        'cpu_percent': cpu_percent
                    })
            
            time.sleep(2)  # Измерения каждые 2 секунды
            
    except KeyboardInterrupt:
        print("\n⏹️  Мониторинг остановлен пользователем")
    
    # Анализируем результаты
    analyze_measurements(measurements)

def analyze_measurements(measurements):
    """Анализ собранных измерений"""
    if not measurements:
        print("❌ Нет данных для анализа")
        return
    
    print("\n" + "=" * 80)
    print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 80)
    
    # Группируем по типам систем
    by_type = {}
    for m in measurements:
        system_type = m['type']
        if system_type not in by_type:
            by_type[system_type] = []
        by_type[system_type].append(m)
    
    # Статистика по каждой системе
    for system_type, data in by_type.items():
        if not data:
            continue
            
        memory_values = [m['memory_mb'] for m in data]
        cpu_values = [m['cpu_percent'] for m in data]
        
        avg_memory = sum(memory_values) / len(memory_values)
        max_memory = max(memory_values)
        min_memory = min(memory_values)
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        max_cpu = max(cpu_values)
        min_cpu = min(cpu_values)
        
        print(f"\n🔧 {system_type}:")
        print(f"   💾 Память: {avg_memory:.1f}MB (мин: {min_memory:.1f}, макс: {max_memory:.1f})")
        print(f"   🔥 CPU: {avg_cpu:.1f}% (мин: {min_cpu:.1f}, макс: {max_cpu:.1f})")
        print(f"   📊 Измерений: {len(data)}")
    
    # Сравнение если есть обе системы
    if len(by_type) >= 2:
        print(f"\n🏆 СРАВНЕНИЕ:")
        systems = list(by_type.keys())
        
        for i, sys1 in enumerate(systems):
            for sys2 in systems[i+1:]:
                data1 = by_type[sys1]
                data2 = by_type[sys2]
                
                avg_mem1 = sum(m['memory_mb'] for m in data1) / len(data1)
                avg_mem2 = sum(m['memory_mb'] for m in data2) / len(data2)
                
                avg_cpu1 = sum(m['cpu_percent'] for m in data1) / len(data1)
                avg_cpu2 = sum(m['cpu_percent'] for m in data2) / len(data2)
                
                mem_diff = abs(avg_mem1 - avg_mem2)
                cpu_diff = abs(avg_cpu1 - avg_cpu2)
                
                if avg_mem1 < avg_mem2:
                    print(f"   💾 {sys1} использует на {mem_diff:.1f}MB меньше памяти")
                else:
                    print(f"   💾 {sys2} использует на {mem_diff:.1f}MB меньше памяти")
                
                if avg_cpu1 < avg_cpu2:
                    print(f"   🔥 {sys1} использует на {cpu_diff:.1f}% меньше CPU")
                else:
                    print(f"   🔥 {sys2} использует на {cpu_diff:.1f}% меньше CPU")

def main():
    """Главная функция"""
    print("📊 Монитор производительности голосовых чат систем")
    print("=" * 60)
    print("🎯 Запустите одну или обе системы в других терминалах:")
    print("   python voice_chat_gemini.py")
    print("   python voice_chat_gemini_pipecat.py")
    print("=" * 60)
    
    # Проверяем текущие процессы
    processes = find_voice_chat_processes()
    if processes:
        print("✅ Найдены запущенные процессы:")
        for proc_info in processes:
            print(f"   {proc_info['type']} (PID: {proc_info['pid']})")
    else:
        print("⚠️  Голосовые чат системы не запущены")
        print("💡 Запустите системы и затем перезапустите этот монитор")
        return
    
    # Спрашиваем длительность мониторинга
    try:
        duration = input("\n⏱️  Длительность мониторинга в секундах (по умолчанию 60): ")
        if duration.strip():
            duration = int(duration)
        else:
            duration = 60
    except ValueError:
        duration = 60
    
    # Запускаем мониторинг
    monitor_performance(duration)
    
    print("\n🎉 Мониторинг завершен!")
    print("💾 Результаты анализа показаны выше")

if __name__ == "__main__":
    main()
