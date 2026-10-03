import os
import sys
import json
import uuid
import mimetypes
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TelegramNotifier:
    """Sends real-time execution reports with screenshots directly to Telegram."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        if bot_token is not None:
            self.bot_token = bot_token
        else:
            self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")

        if chat_id is not None:
            self.chat_id = chat_id
        else:
            self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")

        if self.bot_token is None or self.chat_id is None:
            try:
                from lufthansa_bot.storage.db import DatabaseManager
                db = DatabaseManager()
                stats = db.get_summary_stats()
                settings = stats.get("settings", {})
                if self.bot_token is None:
                    self.bot_token = settings.get("telegram_bot_token")
                if self.chat_id is None:
                    self.chat_id = settings.get("telegram_chat_id")
            except Exception:
                pass
        self.api_base = "https://api.telegram.org/bot"

    def is_configured(self) -> bool:
        """Returns True if both bot_token and chat_id are present."""
        return bool(self.bot_token and self.chat_id)

    def format_caption(self, submission_data: Dict[str, Any]) -> str:
        """Formats an executive summary report for Telegram."""
        status = submission_data.get("status", "UNKNOWN")
        status_icon = "✅" if status == "SUCCESS" else ("⚠️" if "CAPTCHA" in status else "❌")
        
        protocol = submission_data.get("protocol_number") or "Nenhum"
        duration = submission_data.get("duration", 0)
        timestamp = submission_data.get("timestamp") or datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # Format text preview snippet (max 120 chars to guarantee caption safety)
        text_preview = submission_data.get("generated_text", "")
        if len(text_preview) > 120:
            text_preview = text_preview[:120] + "..."

        error_msg = submission_data.get("error_message") or submission_data.get("error")
        error_line = f"\n⚠️ <b>Erro/Motivo:</b> <code>{error_msg[:250]}</code>\n" if error_msg else ""

        caption = (
            f"✈️ <b>RELATÓRIO DE DISPARO — LUFTHANSA</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Caso:</b> FB ID 42525052 | SRUV-390257\n"
            f"💰 <b>Compensação:</b> EUR 1.200,00 (2 Pax)\n"
            f"🎫 <b>Voo:</b> LH 506 (03/01/2026) | PNR: 7YQXEQ\n\n"
            f"📊 <b>STATUS:</b> {status_icon} <b>{status}</b>\n"
            f"📝 <b>Protocolo:</b> <code>{protocol}</code>\n"
            f"⏱️ <b>Duração:</b> {duration}s\n"
            f"📅 <b>Data/Hora:</b> {timestamp}\n"
            f"{error_line}\n"
            f"✉️ <b>PRÉVIA DA MENSAGEM:</b>\n"
            f"<i>{text_preview}</i>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 <i>Comprovante visual da tela anexado acima.</i>"
        )
        return caption

    def send_photo(self, photo_path: str, caption: str) -> bool:
        """Sends photo with caption using multipart/form-data."""
        if not self.is_configured():
            print("[Telegram] Notifier not configured (TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing).")
            return False

        if not os.path.exists(photo_path):
            print(f"[Telegram] Photo file not found at {photo_path}. Falling back to text message.")
            return self.send_message(caption)

        url = f"{self.api_base}{self.bot_token}/sendPhoto"
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
        filename = os.path.basename(photo_path)
        mime_type = mimetypes.guess_type(photo_path)[0] or "image/png"

        try:
            with open(photo_path, "rb") as f:
                photo_bytes = f.read()

            # Build multipart body
            body = bytearray()

            # chat_id field
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'.encode("utf-8"))
            body.extend(f"{self.chat_id}\r\n".encode("utf-8"))

            # parse_mode field
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\n'.encode("utf-8"))
            body.extend(b"HTML\r\n")

            # caption field (max 1024 chars for photo captions)
            truncated_caption = caption[:1024]
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n'.encode("utf-8"))
            body.extend(truncated_caption.encode("utf-8"))
            body.extend(b"\r\n")

            # photo file field
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode("utf-8")
            )
            body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
            body.extend(photo_bytes)
            body.extend(b"\r\n")

            # final boundary
            body.extend(f"--{boundary}--\r\n".encode("utf-8"))

            req = urllib.request.Request(
                url,
                data=bytes(body),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "LufthansaDisputeBot/1.0"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=25) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                if res_data.get("ok"):
                    print("[Telegram] Report with photo delivered successfully!")
                    return True
                else:
                    print(f"[Telegram] Delivery error: {res_data}")
                    return False

        except Exception as e:
            print(f"[Telegram] Failed to send photo: {e}")
            # Try sending message text only as fallback
            return self.send_message(caption)

    def send_message(self, text: str) -> bool:
        """Sends text message fallback."""
        if not self.is_configured():
            return False

        url = f"{self.api_base}{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return bool(res.get("ok"))
        except Exception as e:
            print(f"[Telegram] Failed to send message fallback: {e}")
            return False

    def notify(self, submission_result: Dict[str, Any]) -> bool:
        """Main entrypoint to send report."""
        if not self.is_configured():
            return False

        caption = self.format_caption(submission_result)
        screenshot = submission_result.get("screenshot")

        if screenshot and os.path.exists(screenshot):
            return self.send_photo(screenshot, caption)
        else:
            return self.send_message(caption)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    notifier = TelegramNotifier()
    print("Telegram Configured:", notifier.is_configured())
    sample_sub = {
        "status": "SUCCESS",
        "protocol_number": "LH-REC-TEST2026",
        "duration": 45.2,
        "generated_text": "Dear Lufthansa Customer Relations, I am writing regarding case FB ID 42525052 and the acknowledged compensation of EUR 1,200.00...",
        "screenshot": None
    }
    caption = notifier.format_caption(sample_sub)
    print("\nFormatted caption preview:\n" + "-"*50)
    print(caption)
