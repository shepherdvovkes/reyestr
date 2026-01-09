"""
Расчет времени загрузки 130 миллионов документов
"""

# Параметры
total_documents = 130_000_000
threads = 100

# Время на один документ (секунды)
# Оптимистичный сценарий: 18 сек
# Реалистичный сценарий: 20 сек  
# Пессимистичный сценарий: 25 сек

time_per_doc_optimistic = 18
time_per_doc_realistic = 20
time_per_doc_pessimistic = 25

# При 100 потоках, теоретически можем обрабатывать 100 документов одновременно
# Но с учетом rate limiting и задержек, реальная скорость ниже

# Оптимистичный сценарий: 100 документов за 18 сек = 5.56 документов/сек
docs_per_sec_optimistic = threads / time_per_doc_optimistic

# Реалистичный сценарий: 100 документов за 20 сек = 5.0 документов/сек
docs_per_sec_realistic = threads / time_per_doc_realistic

# Пессимистичный сценарий: 100 документов за 25 сек = 4.0 документов/сек
docs_per_sec_pessimistic = threads / time_per_doc_pessimistic

# С учетом ограничений сервера, CAPTCHA, ошибок сети - снижаем эффективность на 30-50%
efficiency_optimistic = 0.7  # 70% эффективность
efficiency_realistic = 0.6   # 60% эффективность
efficiency_pessimistic = 0.5 # 50% эффективность

# Финальная скорость
final_speed_optimistic = docs_per_sec_optimistic * efficiency_optimistic
final_speed_realistic = docs_per_sec_realistic * efficiency_realistic
final_speed_pessimistic = docs_per_sec_pessimistic * efficiency_pessimistic

# Время в секундах
time_sec_optimistic = total_documents / final_speed_optimistic
time_sec_realistic = total_documents / final_speed_realistic
time_sec_pessimistic = total_documents / final_speed_pessimistic

# Конвертация в дни
days_optimistic = time_sec_optimistic / (24 * 3600)
days_realistic = time_sec_realistic / (24 * 3600)
days_pessimistic = time_sec_pessimistic / (24 * 3600)

# Конвертация в месяцы (30 дней)
months_optimistic = days_optimistic / 30
months_realistic = days_realistic / 30
months_pessimistic = days_pessimistic / 30

# Конвертация в годы
years_optimistic = days_optimistic / 365
years_realistic = days_realistic / 365
years_pessimistic = days_pessimistic / 365

print("=" * 70)
print("РАСЧЕТ ВРЕМЕНИ ЗАГРУЗКИ 130 МИЛЛИОНОВ ДОКУМЕНТОВ")
print("=" * 70)
print(f"\nОбщее количество документов: {total_documents:,}")
print(f"Количество потоков: {threads}")
print(f"\nВремя на один документ: {time_per_doc_optimistic}-{time_per_doc_pessimistic} секунд")
print(f"\nТеоретическая скорость (без учета ограничений):")
print(f"  Оптимистично: {docs_per_sec_optimistic:.2f} документов/сек = {docs_per_sec_optimistic * 3600:,.0f} документов/час")
print(f"  Реалистично: {docs_per_sec_realistic:.2f} документов/сек = {docs_per_sec_realistic * 3600:,.0f} документов/час")
print(f"  Пессимистично: {docs_per_sec_pessimistic:.2f} документов/сек = {docs_per_sec_pessimistic * 3600:,.0f} документов/час")

print(f"\nРеальная скорость (с учетом ограничений сервера, CAPTCHA, ошибок):")
print(f"  Оптимистично: {final_speed_optimistic:.2f} документов/сек = {final_speed_optimistic * 3600:,.0f} документов/час")
print(f"  Реалистично: {final_speed_realistic:.2f} документов/сек = {final_speed_realistic * 3600:,.0f} документов/час")
print(f"  Пессимистично: {final_speed_pessimistic:.2f} документов/сек = {final_speed_pessimistic * 3600:,.0f} документов/час")

print(f"\n" + "=" * 70)
print("ОЦЕНКА ВРЕМЕНИ ЗАГРУЗКИ:")
print("=" * 70)
print(f"\n📊 ОПТИМИСТИЧНЫЙ СЦЕНАРИЙ (70% эффективность):")
print(f"   Время: {days_optimistic:,.0f} дней ({months_optimistic:.1f} месяцев, {years_optimistic:.2f} лет)")
print(f"   Скорость: {final_speed_optimistic:.2f} документов/сек")

print(f"\n📊 РЕАЛИСТИЧНЫЙ СЦЕНАРИЙ (60% эффективность):")
print(f"   Время: {days_realistic:,.0f} дней ({months_realistic:.1f} месяцев, {years_realistic:.2f} лет)")
print(f"   Скорость: {final_speed_realistic:.2f} документов/сек")

print(f"\n📊 ПЕССИМИСТИЧНЫЙ СЦЕНАРИЙ (50% эффективность):")
print(f"   Время: {days_pessimistic:,.0f} дней ({months_pessimistic:.1f} месяцев, {years_pessimistic:.2f} лет)")
print(f"   Скорость: {final_speed_pessimistic:.2f} документов/сек")

print(f"\n" + "=" * 70)
print("РЕКОМЕНДАЦИИ:")
print("=" * 70)
print(f"1. Оптимизация кода:")
print(f"   - Уменьшить delay_between_requests с 2.0 до 1.0-1.5 сек")
print(f"   - Уменьшить задержки asyncio.sleep() в download_print_version")
print(f"   - Использовать пул браузеров вместо создания нового для каждого документа")
print(f"\n2. Увеличение потоков:")
print(f"   - Увеличить до 200-500 потоков (если сервер выдержит)")
print(f"   - Использовать распределенную систему (несколько серверов)")
print(f"\n3. Оптимизация процесса:")
print(f"   - Пропускать загрузку HTML-версии, если print-версия успешна")
print(f"   - Использовать кэширование для повторных запросов")
print(f"   - Обрабатывать ошибки и CAPTCHA автоматически")
print("=" * 70)
