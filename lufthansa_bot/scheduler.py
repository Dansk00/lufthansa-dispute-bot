import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from lufthansa_bot.storage.db import DatabaseManager
from lufthansa_bot.engine.form_filler import LufthansaFeedbackAutomation


class DailyScheduler:
    """Manages daily recurring execution at configured target time."""

    def __init__(self, target_time: str = "09:00"):
        self.target_time = target_time
        self.db = DatabaseManager()
        self.automation = LufthansaFeedbackAutomation(headless=False)
        self.running = False

    def get_configured_time(self) -> str:
        stats = self.db.get_summary_stats()
        return stats.get("settings", {}).get("scheduled_time", self.target_time)

    async def start(self):
        self.running = True
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lufthansa Bot Daily Scheduler iniciado.")
        
        while self.running:
            target_str = self.get_configured_time()
            now = datetime.now()
            target_hour, target_minute = map(int, target_str.split(":"))
            next_run = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            
            if next_run <= now:
                next_run += timedelta(days=1)

            seconds_until_next = (next_run - now).total_seconds()
            print(f"[{now.strftime('%H:%M:%S')}] Próxima execução agendada para: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (em {int(seconds_until_next/60)} minutos)")

            # Sleep in intervals of 30 seconds to allow clean interruption
            while seconds_until_next > 0 and self.running:
                sleep_chunk = min(30, seconds_until_next)
                await asyncio.sleep(sleep_chunk)
                seconds_until_next -= sleep_chunk

            if not self.running:
                break

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando execução diária automática...")
            try:
                result = await self.automation.run(mode="DAILY_AUTO")
                print(f"Execução diária finalizada: Status={result['status']}, Protocolo={result.get('protocol_number')}")
            except Exception as e:
                print(f"Erro na execução diária: {e}")

            # Sleep at least 60 seconds so it does not trigger again in the same minute
            await asyncio.sleep(65)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    scheduler = DailyScheduler()
    asyncio.run(scheduler.start())
