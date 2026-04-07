import io
import os
import threading
import uuid
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from subtitle_to_vid import add_english_subtitles_to_video


BASE_DIR = Path(__file__).resolve().parent
LOCAL_STORAGE_DIR = BASE_DIR / "local_storage"
UPLOADS_DIR = LOCAL_STORAGE_DIR / "uploads"
OUTPUTS_DIR = LOCAL_STORAGE_DIR / "outputs"
TEMP_DIR = LOCAL_STORAGE_DIR / "temp"

for path in (UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR):
    path.mkdir(parents=True, exist_ok=True)


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

app = Flask(__name__)
jobs = {}
jobs_lock = threading.Lock()


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def update_job(job_id: str, **updates) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)


def run_pipeline_job(
    job_id: str,
    input_path: Path,
    output_path: Path,
    model_size: str,
    fontsize: int,
    fontcolor: str,
    bgcolor: str,
    bg_opacity: int,
) -> None:
    log_stream = io.StringIO()
    try:
        update_job(
            job_id,
            status="running",
            stage="Processing video",
            progress=10,
            started_at=datetime.utcnow().isoformat(),
        )

        with redirect_stdout(log_stream), redirect_stderr(log_stream):
            add_english_subtitles_to_video(
                input_video_path=str(input_path),
                output_video_path=str(output_path),
                model_size=model_size,
                fontsize=fontsize,
                fontcolor=fontcolor,
                bgcolor=bgcolor,
                bg_opacity=bg_opacity,
                keep_temp_files=False,
            )

        update_job(
            job_id,
            status="completed",
            stage="Done",
            progress=100,
            log=log_stream.getvalue(),
            completed_at=datetime.utcnow().isoformat(),
            output_filename=output_path.name,
        )
    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            stage="Failed",
            progress=100,
            error=str(exc),
            log=log_stream.getvalue(),
            completed_at=datetime.utcnow().isoformat(),
        )


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/jobs")
def create_job():
    file = request.files.get("video")
    if not file or not file.filename:
        return jsonify({"error": "Please choose a video file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file type."}), 400

    model_size = request.form.get("model_size", "base")
    fontsize = int(request.form.get("fontsize", 24))
    fontcolor = request.form.get("fontcolor", "white")
    bgcolor = request.form.get("bgcolor", "black")
    bg_opacity = int(request.form.get("bg_opacity", 180))

    safe_name = secure_filename(file.filename)
    job_id = uuid.uuid4().hex[:12]
    source_name = f"{job_id}_{safe_name}"
    output_name = f"{Path(safe_name).stem}_captioned_{job_id}.mp4"

    input_path = UPLOADS_DIR / source_name
    output_path = OUTPUTS_DIR / output_name
    file.save(input_path)

    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "stage": "Queued",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "input_filename": safe_name,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "output_filename": None,
            "error": None,
            "log": "",
        }

    worker = threading.Thread(
        target=run_pipeline_job,
        args=(job_id, input_path, output_path, model_size, fontsize, fontcolor, bgcolor, bg_opacity),
        daemon=True,
    )
    worker.start()

    return jsonify({"job_id": job_id})


@app.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404

    response = dict(job)
    if response["status"] == "running":
        # Minimal time-based progress for better UI feedback.
        current_progress = response.get("progress", 10)
        response["progress"] = min(95, max(10, current_progress + 1))
        update_job(job_id, progress=response["progress"])

    return jsonify(response)


@app.get("/api/download/<filename>")
def download_output(filename: str):
    safe_name = secure_filename(filename)
    return send_from_directory(OUTPUTS_DIR, safe_name, as_attachment=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
