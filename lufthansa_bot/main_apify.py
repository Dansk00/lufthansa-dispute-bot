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

        # 5. Sync with Render Web Portal if RENDER_URL is configured
        render_url = os.environ.get("RENDER_URL")
        if render_url:
            try:
                Actor.log.info(f"Syncing submission result with Render Portal: {render_url}...")
                import base64
                import json
                import urllib.request

                sync_payload = {
                    "status": result.get("status"),
                    "protocol_number": result.get("protocol_number"),
                    "duration": result.get("duration"),
                    "generated_text": result.get("generated_text"),
                    "mode": "APIFY_SCHEDULED",
                    "error": result.get("error")
                }
                if screenshot_path and os.path.exists(screenshot_path):
                    with open(screenshot_path, "rb") as f:
                        sync_payload["screenshot_base64"] = base64.b64encode(f.read()).decode("utf-8")

                req = urllib.request.Request(
                    f"{render_url.rstrip('/')}/api/sync-submission",
                    data=json.dumps(sync_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "ApifyActor/1.0"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    Actor.log.info(f"Synced with Render Portal successfully! Status={resp.status}")
            except Exception as e:
                Actor.log.warning(f"Error syncing with Render portal: {e}")


if __name__ == "__main__":
    asyncio.run(main())
