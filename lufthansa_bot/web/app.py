import os
import json
import mimetypes
import shutil
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from lufthansa_bot.storage.db import DatabaseManager, EVIDENCE_DIR, ATTACHMENTS_DIR
from lufthansa_bot.engine.ai_generator import TextGenerator
from lufthansa_bot.engine.form_filler import LufthansaFeedbackAutomation, CONFIG_PATH
from lufthansa_bot.scheduler import DailyScheduler

scheduler = DailyScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = None
    if os.environ.get("ENABLE_SCHEDULER", "1") != "0":
        scheduler_task = asyncio.create_task(scheduler.start())
    try:
        yield
    finally:
        if scheduler_task:
            scheduler.stop()
            scheduler_task.cancel()


app = FastAPI(title="Lufthansa Feedback Bot Portal", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "index.html")
db = DatabaseManager()
ai_generator = TextGenerator()

# Runtime lock to prevent double execution
is_automation_running = False


@app.get("/", response_class=HTMLResponse)
async def read_root():
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Lufthansa Bot Portal</h1><p>Template not found.</p>"


@app.get("/api/stats")
async def get_stats():
    stats = db.get_summary_stats()
    stats["is_running"] = is_automation_running
    return stats


@app.get("/api/submissions")
async def get_submissions(limit: int = Query(50, ge=1, le=200)):
    return db.get_recent_submissions(limit=limit)


@app.get("/api/submissions/{sub_id}")
async def get_submission(sub_id: int):
    record = db.get_submission_by_id(sub_id)
    if not record:
        raise HTTPException(status_code=404, detail="Submission record not found")
    return record


@app.get("/api/attachment")
async def get_attachment_status():
    files = []
    if os.path.exists(ATTACHMENTS_DIR):
        files = [
            {
                "name": f,
                "size_kb": round(os.path.getsize(os.path.join(ATTACHMENTS_DIR, f)) / 1024, 1),
                "modified": os.path.getmtime(os.path.join(ATTACHMENTS_DIR, f))
            }
            for f in os.listdir(ATTACHMENTS_DIR)
            if os.path.isfile(os.path.join(ATTACHMENTS_DIR, f))
            and not f.startswith(".")
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".pdf"))
        ]
        files.sort(key=lambda x: x["modified"], reverse=True)

    active_file = files[0] if files else None
    return {
        "active_file": active_file["name"] if active_file else None,
        "active_file_info": active_file,
        "all_files": files,
        "total_attachments": len(files),
        "folder": ATTACHMENTS_DIR
    }


@app.post("/api/upload-attachment")
async def upload_attachment(file: UploadFile = File(...)):
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    clean_filename = os.path.basename(file.filename or "attachment.jpg")
    dest_path = os.path.join(ATTACHMENTS_DIR, clean_filename)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "filename": clean_filename,
        "size_kb": round(os.path.getsize(dest_path) / 1024, 1)
    }


@app.delete("/api/attachment")
async def delete_attachment(filename: Optional[str] = Query(None)):
    if not os.path.exists(ATTACHMENTS_DIR):
        return {"success": True}

    if filename:
        target = os.path.join(ATTACHMENTS_DIR, os.path.basename(filename))
        if os.path.exists(target):
            os.remove(target)
    else:
        for f in os.listdir(ATTACHMENTS_DIR):
            p = os.path.join(ATTACHMENTS_DIR, f)
            if os.path.isfile(p):
                os.remove(p)

    return {"success": True}


@app.get("/api/passenger-data")
async def get_passenger_data():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@app.post("/api/passenger-data")
async def save_passenger_data(data: Dict[str, Any] = Body(...)):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return {"success": True, "data": data}


@app.post("/api/settings")
async def update_settings(payload: Dict[str, str] = Body(...)):
    for k, v in payload.items():
        db.update_setting(k, str(v))
    return {"success": True}


@app.post("/api/test-telegram")
async def test_telegram():
    from lufthansa_bot.engine.telegram_notifier import TelegramNotifier
    notifier = TelegramNotifier()
    if not notifier.is_configured():
        return {
            "success": False,
            "configured": False,
            "message": "Telegram não configurado. Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID."
        }
    ok = notifier.notify({
        "status": "TEST_SUCCESS",
        "protocol_number": "TEST-TELEGRAM",
        "duration": 2.0,
        "generated_text": "Teste de conexão do portal para o Caso Lufthansa FB ID 42525052.",
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M")
    })
    return {"success": ok, "configured": True, "message": "Mensagem entregue no Telegram!" if ok else "Falha ao enviar."}


@app.get("/api/screenshot")
async def get_screenshot(path: str = Query(...)):
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path) or not abs_path.startswith(os.path.abspath(EVIDENCE_DIR)):
        raise HTTPException(status_code=404, detail="Evidence screenshot file not found")

    media_type, _ = mimetypes.guess_type(abs_path)
    return FileResponse(abs_path, media_type=media_type or "image/png")


@app.get("/api/generate-preview")
async def generate_preview(style_idx: Optional[int] = Query(None)):
    text = ai_generator.generate(style_idx=style_idx)
    valid = ai_generator.validate_facts(text)
    return {"text": text, "valid_facts": valid}


@app.post("/api/run")
async def run_automation():
    global is_automation_running
    if is_automation_running:
        raise HTTPException(status_code=409, detail="Uma execução já está em andamento no navegador.")

    is_automation_running = True
    try:
        automation = LufthansaFeedbackAutomation(headless=False)
        result = await automation.run(mode="MANUAL_PORTAL")
        return result
    finally:
        is_automation_running = False


if __name__ == "__main__":
    import uvicorn
    print("Iniciando portal Lufthansa Bot em http://localhost:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
