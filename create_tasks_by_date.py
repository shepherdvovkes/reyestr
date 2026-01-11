"""
Скрипт для создания задач по датам
Разбивает год на периоды и создает задачи для каждого периода
"""
import requests
import json
import sys
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def date_to_string(date: datetime) -> str:
    """Конвертирует datetime в формат DD.MM.YYYY"""
    return date.strftime("%d.%m.%Y")


def split_year_into_periods(year: int, period_type: str = "month") -> List[tuple]:
    """
    Разбивает год на периоды
    
    Args:
        year: Год (например, 2024)
        period_type: Тип периода - "month", "week", "day", "quarter"
    
    Returns:
        Список кортежей (start_date, end_date) в формате datetime
    """
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31, 23, 59, 59)
    periods = []
    
    if period_type == "month":
        for month in range(1, 13):
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year, 12, 31, 23, 59, 59)
            else:
                # Первый день следующего месяца минус 1 секунда
                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            periods.append((month_start, month_end))
    
    elif period_type == "quarter":
        for quarter in range(1, 5):
            quarter_start = datetime(year, (quarter - 1) * 3 + 1, 1)
            if quarter == 4:
                quarter_end = datetime(year, 12, 31, 23, 59, 59)
            else:
                quarter_end = datetime(year, quarter * 3 + 1, 1) - timedelta(seconds=1)
            periods.append((quarter_start, quarter_end))
    
    elif period_type == "week":
        current = start_date
        while current <= end_date:
            period_start = current
            # Конец недели (воскресенье)
            days_until_sunday = (6 - current.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            period_end = current + timedelta(days=days_until_sunday - 1)
            period_end = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59)
            if period_end > end_date:
                period_end = end_date
            periods.append((period_start, period_end))
            current = period_end + timedelta(seconds=1)
    
    elif period_type == "day":
        current = start_date
        while current <= end_date:
            period_start = current
            period_end = datetime(current.year, current.month, current.day, 23, 59, 59)
            periods.append((period_start, period_end))
            current = period_end + timedelta(seconds=1)
    
    else:
        raise ValueError(f"Unknown period type: {period_type}")
    
    return periods


def create_task(
    api_url: str,
    search_params: Dict[str, Any],
    start_page: int,
    max_documents: int,
    api_key: Optional[str] = None
) -> Optional[str]:
    """Создает задачу через API"""
    url = f"{api_url.rstrip('/')}/api/v1/tasks/create"
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    data = {
        "search_params": search_params,
        "start_page": start_page,
        "max_documents": max_documents
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        return result.get('task_id')
    except requests.exceptions.RequestException as e:
        print(f"✗ Ошибка создания задачи: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"  Детали: {error_detail}")
            except:
                print(f"  Ответ: {e.response.text}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Создание задач по датам для загрузки документов за год",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Создать задачи по месяцам за 2024 год
  python create_tasks_by_date.py --api-url http://localhost:8000 \\
      --year 2024 --period month

  # Создать задачи по неделям за 2024 год
  python create_tasks_by_date.py --api-url http://localhost:8000 \\
      --year 2024 --period week

  # Создать задачи по кварталам за 2024 год
  python create_tasks_by_date.py --api-url http://localhost:8000 \\
      --year 2024 --period quarter

  # Создать задачи по дням за 2024 год (будет много задач!)
  python create_tasks_by_date.py --api-url http://localhost:8000 \\
      --year 2024 --period day

  # Создать задачи с кастомными параметрами
  python create_tasks_by_date.py --api-url http://localhost:8000 \\
      --year 2024 --period month \\
      --court-region 14 --instance-type 2 \\
      --max-documents 500
        """
    )
    
    parser.add_argument(
        "--api-url",
        required=True,
        help="URL сервера (например, http://localhost:8000 или https://gate-server.com)"
    )
    parser.add_argument(
        "--api-key",
        help="API ключ для аутентификации"
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Год для загрузки (например, 2024)"
    )
    parser.add_argument(
        "--period",
        choices=["month", "week", "quarter", "day"],
        default="month",
        help="Тип периода для разбиения года (по умолчанию: month)"
    )
    parser.add_argument(
        "--court-region",
        default="11",
        help="ID региона суда (по умолчанию: 11 - Київська область)"
    )
    parser.add_argument(
        "--instance-type",
        default="1",
        help="Тип инстанции: 1=Перша інстанція, 2=Апеляційна, 3=Касаційна (по умолчанию: 1)"
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        help="Начальная страница для каждой задачи (по умолчанию: 1)"
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=100,
        help="Максимальное количество документов на задачу (по умолчанию: 100)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать какие задачи будут созданы, но не создавать их"
    )
    
    args = parser.parse_args()
    
    # Разбиваем год на периоды
    print(f"Разбиваем {args.year} год на периоды ({args.period})...")
    periods = split_year_into_periods(args.year, args.period)
    print(f"Создано {len(periods)} периодов\n")
    
    if args.dry_run:
        print("=== DRY RUN - задачи не будут созданы ===\n")
    
    # Создаем задачи для каждого периода
    success_count = 0
    failed_count = 0
    
    for i, (period_start, period_end) in enumerate(periods, 1):
        reg_date_begin = date_to_string(period_start)
        reg_date_end = date_to_string(period_end)
        
        search_params = {
            "CourtRegion": args.court_region,
            "INSType": args.instance_type,
            "ChairmenName": "",
            "SearchExpression": "",
            "RegDateBegin": reg_date_begin,
            "RegDateEnd": reg_date_end,
            "DateFrom": "",
            "DateTo": ""
        }
        
        print(f"[{i}/{len(periods)}] Период: {reg_date_begin} - {reg_date_end}")
        print(f"  Параметры: CourtRegion={args.court_region}, INSType={args.instance_type}")
        
        if args.dry_run:
            print(f"  ✓ Задача будет создана (start_page={args.start_page}, max_documents={args.max_documents})")
        else:
            task_id = create_task(
                api_url=args.api_url,
                search_params=search_params,
                start_page=args.start_page,
                max_documents=args.max_documents,
                api_key=args.api_key
            )
            
            if task_id:
                print(f"  ✓ Задача создана: {task_id}")
                success_count += 1
            else:
                print(f"  ✗ Ошибка создания задачи")
                failed_count += 1
        
        print()
    
    # Итоговая статистика
    print("=" * 60)
    if args.dry_run:
        print(f"DRY RUN: будет создано {len(periods)} задач")
    else:
        print(f"Создано задач: {success_count}/{len(periods)}")
        if failed_count > 0:
            print(f"Ошибок: {failed_count}")
    print("=" * 60)
    
    sys.exit(0 if (args.dry_run or success_count == len(periods)) else 1)


if __name__ == "__main__":
    main()
