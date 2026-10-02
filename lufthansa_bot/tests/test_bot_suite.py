import os
import sys
import unittest
import json
import tempfile
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(PROJECT_ROOT))

from lufthansa_bot.storage.db import DatabaseManager, init_db
from lufthansa_bot.engine.ai_generator import TextGenerator, MANDATORY_FACTS
from lufthansa_bot.web.app import app
from fastapi.testclient import TestClient


class TestLufthansaBot(unittest.TestCase):

    def setUp(self):
        self.config_path = os.path.join(PROJECT_ROOT, "config", "passenger_data.json")

    def test_passenger_data_config(self):
        """Verifies that all required flight and passenger parameters exist and match user specs."""
        self.assertTrue(os.path.exists(self.config_path))
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["booking_code"], "7YQXEQ")
        self.assertEqual(data["flight_number"], "LH 506")
        self.assertEqual(data["flight_date"], "03/01/2026")
        self.assertEqual(data["ticket_number"], "2202238571223")
        self.assertEqual(data["first_name"], "Danilo")
        self.assertEqual(data["last_name"], "Lopes de Deus")
        self.assertEqual(data["email"], "dan-sk@hotmail.com")
        self.assertEqual(data["document_id"], "42525052")
        self.assertEqual(data["feedback_id"], "42525052")
        self.assertEqual(data["sruv_reference"], "SRUV-390257")
        self.assertEqual(data["compensation_total"], "EUR 1,200.00")

    def test_ai_generator_facts(self):
        """Verifies that the AI text generator preserves all mandatory facts in every variation."""
        generator = TextGenerator()
        for idx in range(4):
            variation = generator.generate(style_idx=idx)
            self.assertIsNotNone(variation)
            for fact in MANDATORY_FACTS:
                self.assertIn(
                    fact.lower(),
                    variation.lower(),
                    f"Fact '{fact}' missing in variation style {idx}"
                )
            self.assertTrue(generator.validate_facts(variation))

    def test_database_manager(self):
        """Tests SQLite persistence, evidence storage, and stats aggregation."""
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
            temp_db = tf.name

        try:
            db = DatabaseManager(db_path=temp_db)
            stats = db.get_summary_stats()
            self.assertEqual(stats["total_runs"], 0)

            # Insert a success record
            sub_id = db.record_submission(
                status="SUCCESS",
                generated_text="Test email variation content",
                protocol_number="FB-42525052-TEST",
                attachment_filename="receipt.jpg",
                screenshot_path="evidence/test.png",
                execution_time_seconds=12.5,
                mode="TEST"
            )
            self.assertGreater(sub_id, 0)

            # Check updated stats
            stats = db.get_summary_stats()
            self.assertEqual(stats["total_runs"], 1)
            self.assertEqual(stats["success_count"], 1)
            self.assertEqual(stats["last_success_protocol"], "FB-42525052-TEST")

            # Check single retrieval
            rec = db.get_submission_by_id(sub_id)
            self.assertIsNotNone(rec)
            assert rec is not None
            self.assertEqual(rec["protocol_number"], "FB-42525052-TEST")
            self.assertEqual(rec["status"], "SUCCESS")
        finally:
            if os.path.exists(temp_db):
                try:
                    os.remove(temp_db)
                except Exception:
                    pass

    def test_web_portal_endpoints(self):
        """Tests FastAPI endpoints of the web dashboard."""
        client = TestClient(app)
        
        # GET /
        resp_root = client.get("/")
        self.assertEqual(resp_root.status_code, 200)
        self.assertIn("Lufthansa Dispute Ops", resp_root.text)

        # GET /api/stats
        resp_stats = client.get("/api/stats")
        self.assertEqual(resp_stats.status_code, 200)
        stats_json = resp_stats.json()
        self.assertIn("total_runs", stats_json)

        # GET /api/attachment
        resp_att = client.get("/api/attachment")
        self.assertEqual(resp_att.status_code, 200)
        att_json = resp_att.json()
        self.assertIn("folder", att_json)

        # POST /api/upload-attachment and DELETE /api/attachment
        test_file_content = b"fake-receipt-content"
        resp_up = client.post(
            "/api/upload-attachment",
            files={"file": ("test_receipt.jpg", test_file_content, "image/jpeg")}
        )
        self.assertEqual(resp_up.status_code, 200)
        self.assertTrue(resp_up.json()["success"])

        # Check attachment active
        resp_att_after = client.get("/api/attachment")
        self.assertEqual(resp_att_after.json()["active_file"], "test_receipt.jpg")

        # Delete attachment
        resp_del = client.delete("/api/attachment?filename=test_receipt.jpg")
        self.assertEqual(resp_del.status_code, 200)

        # GET /api/passenger-data
        resp_pax = client.get("/api/passenger-data")
        self.assertEqual(resp_pax.status_code, 200)
        self.assertEqual(resp_pax.json().get("booking_code"), "7YQXEQ")

        # POST /api/settings
        resp_set = client.post("/api/settings", json={"scheduled_time": "09:30"})
        self.assertEqual(resp_set.status_code, 200)
        self.assertTrue(resp_set.json()["success"])

        # GET /api/generate-preview
        resp_gen = client.get("/api/generate-preview")
        self.assertEqual(resp_gen.status_code, 200)
        gen_json = resp_gen.json()
        self.assertTrue(gen_json["valid_facts"])
        self.assertIn("FB ID 42525052", gen_json["text"])


if __name__ == "__main__":
    unittest.main()
