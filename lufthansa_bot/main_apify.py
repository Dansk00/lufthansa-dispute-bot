import os
import sys
import asyncio
from datetime import datetime
from apify import Actor

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lufthansa_bot.engine.form_filler import LufthansaFeedbackAutomation
from lufthansa_bot.engine.telegram_notifier import TelegramNotifier


async def main():
    async with Actor:
        Actor.log.info("Starting Lufthansa Dispute Bot on Apify Cloud...")

        # 1. Read optional input
        actor_input = await Actor.get_input() or {}
        mode = actor_input.get("mode", "REAL_RUN")
        Actor.log.info(f"Execution Mode: {mode}")

        # 2. Configure Apify Residential Proxy (Brazil)
        proxy_dict = None
        try:
            Actor.log.info("Requesting Apify Residential Proxy (Brazil)...")
            proxy_configuration = await Actor.create_proxy_configuration(
                groups=["RESIDENTIAL"],
                country_code="BR"
            )
            if proxy_configuration:
                proxy_url = await proxy_configuration.new_url()
                Actor.log.info("Apify Residential Proxy obtained successfully!")
                from urllib.parse import urlsplit
                u = urlsplit(proxy_url)
                proxy_dict = {
                    "server": f"{u.scheme}://{u.hostname}:{u.port}",
                    "username": u.username or "",
                    "password": u.password or ""
                }
        except Exception as e:
            Actor.log.warning(f"Failed to obtain residential proxy, using default network: {e}")

        # 3. Execute Lufthansa Automation with Residential Proxy
        automation = LufthansaFeedbackAutomation(headless=True, proxy=proxy_dict)
        
        Actor.log.info("Navigating and submitting Lufthansa feedback form...")
        result = await automation.run(mode=f"APIFY_{mode}")
        Actor.log.info(f"Execution finished: Status={result.get('status')}, Protocol={result.get('protocol_number')}")

        # 4. Save output to Apify Key-Value Store
        await Actor.set_value("OUTPUT", result)

        screenshot_path = result.get("screenshot")
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                with open(screenshot_path, "rb") as f:
                    img_data = f.read()
                await Actor.set_value("screenshot.png", img_data, content_type="image/png")
                Actor.log.info("Receipt screenshot saved to Apify Key-Value Store.")
            except Exception as e:
                Actor.log.warning(f"Error saving screenshot to Apify store: {e}")


if __name__ == "__main__":
    asyncio.run(main())
