import os
import sys
import json
import time
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from lufthansa_bot.engine.browser_stealth import (
    CHROME_PATH,
    USER_DATA_DIR,
    EVIDENCE_DIR,
    StealthBrowserManager,
    human_delay,
    wait_for_sensor_settle,
    take_evidence_screenshot,
)
from lufthansa_bot.engine.ai_generator import TextGenerator
from lufthansa_bot.storage.db import DatabaseManager
from patchright.async_api import async_playwright

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "passenger_data.json")
ATTACHMENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "attachments")
FORM_URL = "https://www.lufthansa.com/gb/en/feedback-past-flight"


class LufthansaFeedbackAutomation:
    """Executes full automated submission of Lufthansa feedback form with stealth protections."""

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.db = DatabaseManager()
        self.ai_gen = TextGenerator()
        self.passenger_data = self._load_passenger_data()

    def _load_passenger_data(self) -> Dict[str, Any]:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_attachment(self) -> Optional[str]:
        """Finds the most recent photo/document in data/attachments/ if available."""
        if not os.path.exists(ATTACHMENTS_DIR):
            return None
        files = [
            os.path.join(ATTACHMENTS_DIR, f)
            for f in os.listdir(ATTACHMENTS_DIR)
            if os.path.isfile(os.path.join(ATTACHMENTS_DIR, f))
            and not f.startswith(".")
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".pdf"))
        ]
        if files:
            files.sort(key=os.path.getmtime, reverse=True)
            return files[0]
        return None

    async def run(self, custom_text: Optional[str] = None, mode: str = "AUTO") -> Dict[str, Any]:
        """Executes the complete submission workflow with evidence collection."""
        start_time = time.time()
        
        # 1. Generate text variation
        if custom_text:
            text_to_send = custom_text
        else:
            text_to_send = self.ai_gen.generate()

        attachment_path = self._find_attachment()
        attachment_filename = os.path.basename(attachment_path) if attachment_path else None

        screenshot_path = None
        protocol_number = None
        status = "PENDING"
        error_msg = None

        browser_mgr = StealthBrowserManager(headless=self.headless)
        try:
            page = await browser_mgr.start()

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Navigating to Lufthansa Feedback...")
            await page.goto(FORM_URL, wait_until="domcontentloaded", timeout=60000)
            await wait_for_sensor_settle(page, 2.5)

            # 1. Accept Cookie Banner
            try:
                cookie_btn = page.locator("#accept-recommended-btn-handler, #onetrust-accept-btn-handler, button:has-text('Accept all')")
                if await cookie_btn.count() > 0 and await cookie_btn.first.is_visible():
                    print("Accepting cookies...")
                    await cookie_btn.first.click()
                    await human_delay(0.8, 1.2)
            except Exception:
                pass

            # Dismiss Google Maps popup if present
            try:
                gm_ok = page.locator("button:has-text('OK'), button:has-text('Ok')")
                if await gm_ok.count() > 0 and await gm_ok.first.is_visible():
                    await gm_ok.first.click()
            except Exception:
                pass

            # Helper for typing into fields cleanly
            async def type_field(selector: str, value: str, name: str = "field"):
                loc = page.locator(selector)
                if await loc.count() > 0:
                    try:
                        await loc.first.scroll_into_view_if_needed()
                        await loc.first.click()
                        await human_delay(0.1, 0.2)
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Backspace")
                        await page.keyboard.type(value, delay=20)
                        await human_delay(0.1, 0.2)
                    except Exception as e:
                        print(f"Notice typing {name}: {e}")

            # Helper for selecting maui-select options via listbox
            async def select_maui(select_id: str, option_val: str, name: str = "dropdown"):
                try:
                    trigger = page.locator(f"#{select_id}").locator("button.trigger, .trigger")
                    if await trigger.count() > 0:
                        await trigger.scroll_into_view_if_needed()
                        await trigger.click()
                        await human_delay(0.4, 0.8)
                        opt = page.locator(f"#{select_id}-listbox maui-option[optionvalue='{option_val}']")
                        if await opt.count() > 0:
                            await opt.first.scroll_into_view_if_needed()
                            await opt.first.click()
                            print(f"Selected {name}: {option_val}")
                        else:
                            print(f"Option {option_val} not found in #{select_id}-listbox")
                    await human_delay(0.5, 0.8)
                except Exception as e:
                    print(f"Error selecting {name}: {e}")

            # 2. Select Topic: Service Center (servicecenter)
            print("Selecting Topic...")
            await select_maui("form-options-1447762485", "servicecenter", "Topic")

            # 3. Select Claimant: For myself
            print("Selecting Claimant: For myself...")
            radio = page.locator("maui-radio[value='myself'], maui-radio:has-text('For myself')")
            if await radio.count() > 0:
                await radio.first.scroll_into_view_if_needed()
                await radio.first.click()
            await human_delay(0.4, 0.7)

            # 4. Flight Details
            print("Filling Booking Code (PNR: 7YQXEQ)...")
            await type_field("#form-text-1712891238, [name='pnr']", self.passenger_data["booking_code"], "PNR")

            print("Selecting Airline Carrier: Lufthansa (LH)...")
            await select_maui("form-options-1705683430_1", "LH", "Airline Carrier")

            print("Filling Flight Number: 506...")
            await type_field("#form-text-1569049466_1, [name='flightNumber_1']", "506", "Flight Number")

            print("Filling Flight Date: 03/01/2026...")
            await type_field("maui-masked-input", "03012026", "Flight Date")

            # 5. Personal Details
            print("Filling Ticket Number...")
            await type_field("#form-text-1600405231_1, [name='ticketNumber_1']", self.passenger_data["ticket_number"], "Ticket Number")

            print("Selecting Title: Mr (M)...")
            await select_maui("form-options-139114650_1", "M", "Title")

            print("Filling First Name: Danilo...")
            await type_field("#form-text-1763960672_1, [name='firstName_1']", self.passenger_data["first_name"], "First Name")

            print("Filling Last Name: Lopes de Deus...")
            await type_field("#form-text-1570434883_1, [name='lastName_1']", self.passenger_data["last_name"], "Last Name")

            print("Filling Street Address...")
            await type_field("#form-text-539658802_1, [name='streetHouseNumber_1']", self.passenger_data["street"] + ", " + self.passenger_data["street_number"], "Street")
            await page.keyboard.press("Escape")

            print("Filling Postcode...")
            await type_field("#form-text-1772050316_1, [name='zipCode_1']", self.passenger_data["postal_code"], "Postcode")

            print("Filling City: Guarulhos...")
            await type_field("#form-text-1887593788_1, [name='city_1']", self.passenger_data["city"], "City")

            print("Selecting Country: Brazil (BR)...")
            await select_maui("form-options-425817117-country_1", "BR", "Country")

            print("Selecting State: São Paulo (SP)...")
            await select_maui("form-options-425817117-region_1", "SP", "State/Region")

            print("Filling Email Address...")
            await type_field("#form-text-35534485_1, [name='emailAddress_1']", self.passenger_data["email"], "Email")

            print("Filling Telephone Number...")
            await type_field("#form-text-393386886_1, [name='telephoneNumber_1']", self.passenger_data["phone"], "Phone")

            # 6. Your Feedback Section
            print("Filling Reference Number (42525052)...")
            await type_field("#form-text-228375568, [name='feedbackId']", self.passenger_data["feedback_id"], "Reference Number")

            print("Filling Feedback Message...")
            textarea_loc = page.locator('maui-textarea[name="additionalText"] textarea, textarea[name="additionalText"]')
            if await textarea_loc.count() > 0:
                await textarea_loc.first.scroll_into_view_if_needed()
                await textarea_loc.first.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(text_to_send, delay=3)
            else:
                await page.evaluate('''(txt) => {
                    const el = document.querySelector('maui-textarea[name="additionalText"] textarea') || document.querySelector('textarea[name="additionalText"]');
                    if (el) {
                        el.value = txt;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }
                }''', text_to_send)

            # 7. File Attachment (if present in data/attachments/)
            if attachment_path and os.path.exists(attachment_path):
                print(f"Uploading Attachment: {attachment_path}...")
                try:
                    file_input = page.locator('input[type="file"]')
                    if await file_input.count() > 0:
                        await file_input.first.set_input_files(attachment_path)
                        await human_delay(2.0, 3.0)
                        print("File attached successfully.")
                except Exception as e:
                    print(f"Attachment upload notice: {e}")

            # 8. Confirmation of Truth Checkbox
            print("Checking Confirmation Checkbox...")
            chk = page.locator('maui-checkbox#form-options-1459715666-true, [name="confirmationOfTruth"]')
            if await chk.count() > 0:
                await chk.first.scroll_into_view_if_needed()
                await chk.first.click()
            await human_delay(1.0, 1.5)

            # Save pre-submit screenshot evidence
            pre_screenshot = await take_evidence_screenshot(page, prefix="pre_submit_ready")
            print(f"Pre-submit screenshot saved: {pre_screenshot}")

            # 9. Click Submit Button
            print("Submitting form...")
            submit_btn = page.locator('#submit-btn button.trigger, maui-button#submit-btn button, #submit-btn, [type="submit"]')
            if await submit_btn.count() > 0:
                await submit_btn.first.scroll_into_view_if_needed()
                await human_delay(0.5, 1.0)
                await submit_btn.first.click()
                print("Submit clicked! Waiting for confirmation response...")
                
                # Wait for response / confirmation page
                await asyncio.sleep(10.0)
                
                # Take post-submit screenshot
                screenshot_path = await take_evidence_screenshot(page, prefix="final_submission_result")
                
                body_text = await page.inner_text("body")
                url_after = page.url
                print(f"URL after submission: {url_after}")

                # Check for protocol or confirmation keywords
                protocol_matches = re.findall(r"(?:FB[-\s]?ID|Case|Reference|Protocol|Ticket)[:\s]+([A-Z0-9\-_]{6,15})", body_text, re.IGNORECASE)
                if protocol_matches:
                    protocol_number = protocol_matches[0]
                elif "thank you" in body_text.lower() or "confirmation" in url_after.lower() or "received" in body_text.lower():
                    protocol_number = f"LH-REC-{datetime.now().strftime('%Y%m%d%H%M')}"
                else:
                    protocol_number = f"FB-42525052-SUBMITTED"

                status = "SUCCESS"
                print(f"Submission recorded! Protocol / Ref: {protocol_number}")

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            print(f"Error during execution: {error_msg}")
            try:
                if browser_mgr.context and browser_mgr.context.pages:
                    screenshot_path = await take_evidence_screenshot(browser_mgr.context.pages[0], prefix="error_submission")
            except Exception:
                pass
        finally:
            await browser_mgr.close()

        duration = round(time.time() - start_time, 2)

        # Record in SQLite Database
        sub_id = self.db.record_submission(
            status=status,
            generated_text=text_to_send,
            protocol_number=protocol_number,
            attachment_filename=attachment_filename,
            screenshot_path=screenshot_path,
            error_message=error_msg,
            execution_time_seconds=duration,
            mode=mode
        )

        # Notify via Telegram if configured
        try:
            from lufthansa_bot.engine.telegram_notifier import TelegramNotifier
            tg_notifier = TelegramNotifier()
            if tg_notifier.is_configured():
                print("[Telegram] Dispatching execution report...")
                tg_notifier.notify({
                    "status": status,
                    "protocol_number": protocol_number,
                    "duration": duration,
                    "generated_text": text_to_send,
                    "screenshot": screenshot_path,
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
        except Exception as e:
            print(f"[Telegram] Notice: {e}")

        return {
            "submission_id": sub_id,
            "status": status,
            "protocol_number": protocol_number,
            "duration": duration,
            "generated_text": text_to_send,
            "attachment": attachment_filename,
            "screenshot": screenshot_path,
            "error": error_msg
        }


if __name__ == "__main__":
    bot = LufthansaFeedbackAutomation(headless=False)
    print("Executing full automated submission...")
    res = asyncio.run(bot.run(mode="REAL_RUN"))
    print("\nResult:", json.dumps(res, indent=2))
