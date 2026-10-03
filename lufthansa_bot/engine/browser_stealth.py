import os
import sys
import random
import asyncio
from datetime import datetime
from typing import Optional, Tuple
from patchright.async_api import async_playwright, Page, BrowserContext, Locator


def get_chrome_executable() -> Optional[str]:
    """Finds Chrome/Chromium executable on Windows or Linux."""
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
    else:
        candidates = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


CHROME_PATH = get_chrome_executable()

if sys.platform == "win32":
    USER_DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "LufthansaBot_ChromeProfile"
    )
else:
    USER_DATA_DIR = os.path.join(
        os.environ.get("HOME", "/tmp"),
        ".lufthansa_bot_profile"
    )

EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "evidence")


class StealthBrowserManager:
    """Manages stealth browser lifecycle with native Chrome and anti-fingerprint protection."""

    def __init__(self, headless: Optional[bool] = None, proxy: Optional[dict] = None):
        # Auto-detect headless if running in container / Linux without DISPLAY
        if headless is None:
            if os.environ.get("HEADLESS", "").lower() in ["1", "true", "yes"]:
                self.headless = True
            elif sys.platform != "win32" and not os.environ.get("DISPLAY"):
                self.headless = True
            else:
                self.headless = False
        else:
            self.headless = headless

        self.proxy = proxy or ({"server": os.environ["PROXY_SERVER"]} if os.environ.get("PROXY_SERVER") else None)
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        os.makedirs(EVIDENCE_DIR, exist_ok=True)

    async def start(self) -> Page:
        """Launches persistent Chrome context with anti-Akamai stealth arguments."""
        self.playwright = await async_playwright().start()
        
        args = [
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--no-first-run",
            "--disable-infobars",
            "--window-size=1280,900",
        ]

        if sys.platform == "win32":
            args.extend([
                "--enable-gpu",
                "--use-gl=angle",
                "--use-angle=d3d11",
            ])
            if not self.headless:
                args.append("--start-maximized")
        else:
            args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ])

        exec_path = get_chrome_executable()

        launch_kwargs = {
            "user_data_dir": USER_DATA_DIR,
            "executable_path": exec_path,
            "headless": self.headless,
            "args": args,
            "viewport": None if (not self.headless and sys.platform == "win32") else {"width": 1280, "height": 900},
            "ignore_default_args": ["--enable-automation"],
            "locale": "en-GB",
            "timezone_id": "America/Sao_Paulo",
        }
        if self.proxy:
            launch_kwargs["proxy"] = self.proxy

        context = await self.playwright.chromium.launch_persistent_context(**launch_kwargs)
        self.context = context

        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()
        return page

    async def close(self):
        """Closes browser context and Playwright instance cleanly."""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()


# Human-like kinematic helpers

async def human_delay(min_sec: float = 0.3, max_sec: float = 1.0):
    """Waits for a randomized duration."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def human_type(locator: Locator, text: str, field_name: str = "field"):
    """Types text with natural human keystroke intervals and occasional hesitations."""
    await locator.scroll_into_view_if_needed()
    await locator.hover()
    await human_delay(0.15, 0.35)
    await locator.click()
    await human_delay(0.1, 0.25)
    
    # Clear existing content if any
    await locator.fill("")
    await human_delay(0.1, 0.2)

    for i, char in enumerate(text):
        await locator.type(char, delay=random.uniform(30, 85))
        if random.random() < 0.03 and i > 0 and i < len(text) - 1:
            await human_delay(0.2, 0.5)


async def human_click(locator: Locator):
    """Moves smoothly over the element and performs a human click."""
    await locator.scroll_into_view_if_needed()
    await locator.hover()
    await human_delay(0.2, 0.5)
    await locator.click()
    await human_delay(0.3, 0.7)


async def wait_for_sensor_settle(page: Page, duration: float = 2.0):
    """Waits for Akamai telemetry sensor background requests to complete and stabilize."""
    await asyncio.sleep(duration + random.uniform(0.5, 1.2))


async def take_evidence_screenshot(page: Page, prefix: str = "submission") -> str:
    """Captures a screenshot of the current page state and saves to evidence folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.png"
    filepath = os.path.join(EVIDENCE_DIR, filename)
    await page.screenshot(path=filepath, full_page=True)
    return filepath
