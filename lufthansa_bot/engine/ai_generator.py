import os
import json
import random
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

MANDATORY_FACTS = [
    "42525052",
    "SRUV-390257",
    "1,200",
    "600",
    "Payment Hub",
    "10 days",
    "YouTube",
    "Danilo Lopes de Deus"
]

VARIATION_TEMPLATES = [
    # Style 1: Formal Legal & Regulatory Notice
    """Dear Lufthansa Customer Relations Team,

I am writing regarding case FB ID 42525052 and the acknowledged compensation of EUR 1,200.00 (EUR 600.00 per passenger for two passengers).

Despite exhaustive efforts to settle this directly, the agreed payment remains outstanding. The facts of the case are indisputable:
1. Lufthansa formally recognized liability and approved EUR 1,200.00 total compensation.
2. Full banking details were submitted initially and re-submitted via the Lufthansa Payment Hub.
3. Lufthansa gave an explicit written commitment that funds would be received within 10 days.
4. That 10-day period expired without transfer.
5. Banking details were subsequently provided through the official SRUV conciliation procedure (Case Reference: SRUV-390257), under which Lufthansa once again acknowledged the claim in full.

It is unacceptable that an acknowledged claim remains unpaid despite compliance with every verification procedure. I hereby demand immediate confirmation of the transfer execution and the corresponding bank transaction reference.

Please be advised that I produce travel and airline review content on YouTube. Should this matter remain unresolved, I will publish a fully documented, factual account detailing the entire chronology—including Lufthansa's formal recognition of the EUR 1,200.00 debt, the broken 10-day payment commitment, and all subsequent correspondence.

I trust Lufthansa will resolve this matter immediately without further escalation.

Sincerely,
Danilo Lopes de Deus
FB ID: 42525052
SRUV Reference: SRUV-390257""",

    # Style 2: Chronological Executive Escalation
    """To: Lufthansa Customer Relations
Subject: URGENT: Unpaid Acknowledged Compensation - FB ID 42525052 (SRUV-390257)

I am submitting this renewed request regarding unresolved case FB ID 42525052 concerning EUR 1,200.00 in statutory compensation (EUR 600 per passenger, 2 passengers).

The chronology of events is clear and documented:
- Lufthansa formally confirmed entitlement to EUR 1,200.00.
- Bank details were submitted as requested, and subsequently re-entered through Lufthansa's Payment Hub.
- Lufthansa explicitly committed to processing the payout within 10 days.
- That deadline passed without disbursement.
- The matter was escalated through conciliation (SRUV-390257), where Lufthansa officially reaffirmed full acknowledgment.
- Despite this second formal admission, payment has still not been executed.

I request an immediate update containing the precise date of transfer and the SWIFT/SEPA reference number.

Please note that I manage a YouTube channel focused on air travel experiences. Continued non-payment will compel me to publish a detailed video outlining the documentation, the admitted EUR 1,200 compensation, the unfulfilled 10-day payment promise, and the persistent delays.

I look forward to your prompt confirmation of payment.

Kind regards,
Danilo Lopes de Deus
FB ID: 42525052
SRUV Reference: SRUV-390257""",

    # Style 3: Direct Customer Relations Demand
    """Dear Lufthansa Customer Service,

This communication is a follow-up on Feedback FB ID 42525052 regarding the outstanding payment of EUR 1,200.00 (EUR 600 per passenger across two passengers).

Every requirement set by Lufthansa has been met:
- Compensation was formally agreed and approved by Lufthansa at EUR 1,200.00.
- Banking information was supplied and re-confirmed via your Payment Hub.
- Lufthansa stated the transfer would arrive within 10 days, yet the deadline elapsed with zero funds received.
- The claim was submitted through the SRUV conciliation mechanism under reference SRUV-390257, leading to another full acknowledgment by Lufthansa.

Nevertheless, the compensation remains unpaid. I request immediate closure of this case along with the definitive payment confirmation and transaction reference.

As the creator of a YouTube travel channel, I intend to share an objective, evidence-based review of this case—including all written admissions of the EUR 1,200 compensation and the overdue 10-day timeline—if payment is not disbursed promptly.

Please provide immediate confirmation that the transfer has been initiated.

Best regards,
Danilo Lopes de Deus
FB ID: 42525052
SRUV Reference: SRUV-390257""",

    # Style 4: Formal Conciliation Follow-up
    """Dear Customer Relations Directorate,

I write once more concerning Case FB ID 42525052 and the overdue EUR 1,200.00 compensation recognized by Lufthansa for two passengers (EUR 600 each).

All necessary documentation and procedures have been completed:
- Lufthansa acknowledged the claim and the EUR 1,200 total amount.
- Payment details were submitted both directly and via the Lufthansa Payment Hub.
- An explicit commitment of payment within 10 days was provided by Lufthansa and subsequently breached.
- The conciliation body SRUV handled case SRUV-390257, resulting in complete formal recognition by Lufthansa.
- The funds have still not been transferred.

I urge Lufthansa to issue the payment immediately and supply the bank transfer tracking reference.

I must also inform you that I operate a YouTube channel covering international travel. If resolution is not achieved immediately, I will publish a comprehensive, factual presentation of this dispute, presenting all official records, the agreed EUR 1,200 figure, and the unfulfilled 10 days timeline.

I anticipate your immediate action and confirmation of payment.

Respectfully,
Danilo Lopes de Deus
FB ID: 42525052
SRUV Reference: SRUV-390257"""
]


class TextGenerator:
    """Generates daily rich variations in English while ensuring all immutable facts remain 100% intact."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

        self.api_key = (
            os.environ.get("OPENCODE_GO_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or self.config.get("api_key")
        )
        self.api_base = (
            os.environ.get("OPENCODE_GO_API_BASE")
            or os.environ.get("OPENAI_API_BASE")
            or self.config.get("api_base")
            or "https://opencode.ai/zen/go/v1"
        )
        self.model = self.config.get("model") or "deepseek-v4-flash-vision-exp"

    def validate_facts(self, text: str) -> bool:
        """Verifies that all essential facts are present in the text."""
        lower = text.lower()
        checks = [
            "42525052" in lower,
            "sruv-390257" in lower,
            ("1,200" in lower or "1200" in lower),
            "600" in lower,
            "payment hub" in lower,
            ("10 days" in lower or "10-day" in lower),
            "youtube" in lower,
            "danilo lopes de deus" in lower
        ]
        return all(checks)

    def generate_via_llm(self, seed: Optional[int] = None) -> Optional[str]:
        """Attempts to generate a fresh variation using LLM API."""
        if not self.api_key:
            return None

        styles = [
            "formal legal notice with numbered chronology",
            "assertive customer relations escalation",
            "executive-level concise summary demand",
            "detailed conciliation follow-up"
        ]
        chosen_style = random.choice(styles)

        prompt = f"""You are drafting a formal dispute follow-up message to Lufthansa Customer Relations on behalf of Danilo Lopes de Deus.
Tone/Style requested: {chosen_style}.
Language: English.

CRITICAL: You MUST include every one of the following facts accurately without omitting or modifying any numbers or names:
1. Feedback ID: FB ID 42525052
2. Compensation total: EUR 1,200.00 (EUR 600 per passenger for 2 passengers)
3. Lufthansa already formally acknowledged the compensation in full.
4. Bank details were provided directly and via Lufthansa's Payment Hub.
5. Lufthansa explicitly stated the payment would be processed within 10 days, but that deadline expired without payment.
6. Bank details were also submitted via the SRUV conciliation procedure (Case Reference: SRUV-390257), which resulted in Lufthansa acknowledging the claim in full.
7. Payment remains outstanding.
8. Request immediate confirmation of the payment date and transfer reference.
9. Inform Lufthansa that Danilo maintains a YouTube channel on travel experiences, and if unresolved, a factual documented video account detailing the chronology, the acknowledged EUR 1,200 debt, and the broken 10-day timeline will be published.
10. Sign-off strictly as:
Danilo Lopes de Deus
FB ID: 42525052
SRUV Reference: SRUV-390257

Output ONLY the final email/message text. No meta-commentary, no Markdown code blocks."""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a professional legal and customer relations correspondence assistant. Output only the requested text."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            url = f"{self.api_base.rstrip('/')}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"].strip()
                if self.validate_facts(text):
                    return text
        except Exception:
            pass

        return None

    def generate(self, style_idx: Optional[int] = None) -> str:
        """Generates a text variation, with automatic validation and template fallback."""
        # Try LLM first if configured
        llm_result = self.generate_via_llm()
        if llm_result:
            return llm_result

        # Deterministic rich template rotation
        if style_idx is not None and 0 <= style_idx < len(VARIATION_TEMPLATES):
            return VARIATION_TEMPLATES[style_idx]
        return random.choice(VARIATION_TEMPLATES)


if __name__ == "__main__":
    generator = TextGenerator()
    text = generator.generate()
    print("Generated variation:\n" + "-"*50)
    print(text)
    print("-" * 50)
    print("Facts valid:", generator.validate_facts(text))
