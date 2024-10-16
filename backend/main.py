import asyncio
from datetime import date, timedelta
from services.mystat_client import (
    create_client,
    ClientConfig,
    LoginData,
    ScheduleEntry
)

async def print_schedule(schedule: list[ScheduleEntry]):
    print("\nРасписание занятий:")
    print("-" * 80)
    print(f"{'Дата':<12} {'Время':<12} {'Предмет':<20} {'Преподаватель':<20} {'Аудитория':<10}")
    print("-" * 80)
    
    for entry in schedule:
        print(
            f"{entry.date:<12} "
            f"{entry.started_at[:-3]}-{entry.finished_at[:-3]:<6} "
            f"{entry.subject_name[:18]:<20} "
            f"{entry.teacher_name[:18]:<20} "
            f"{entry.room_name:<10}"
        )

async def main():
    # Создаем конфигурацию для клиента
    config = ClientConfig(
        login_data=LoginData(
            username="login",
            password="pass"
        )
    )
    
    try:
        # Инициализируем клиент
        client = await create_client(config)
        
        # Получаем расписание на сегодня
        today = date.today()
        today_schedule = await client.get_schedule_by_date(today)
        print("\nРасписание на сегодня:")
        await print_schedule(today_schedule)
        
        # Получаем расписание на завтра
        tomorrow = today + timedelta(days=1)
        tomorrow_schedule = await client.get_schedule_by_date(tomorrow)
        print("\nРасписание на завтра:")
        await print_schedule(tomorrow_schedule)
        
        # Получаем расписание на весь месяц
        print("\nПолучаем расписание на весь месяц...")
        month_schedule = await client.get_month_schedule(today)
        print(f"Всего занятий в текущем месяце: {len(month_schedule)}")
        
        # Показываем первые 5 занятий месяца
        print("\nПервые 5 занятий месяца:")
        await print_schedule(month_schedule[:5])
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    # Запускаем асинхронную функцию
    asyncio.run(main())