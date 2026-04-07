import io
import os
import threading
import uuid
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from subtitle_to_vid import (
    burn_subtitles_into_video,
    extract_audio_from_video,
    transcribe_audio_to_srt,
)


BASE_DIR = Path(__file__).resolve().parent
LOCAL_STORAGE_DIR = BASE_DIR / "local_storage"
UPLOADS_DIR = LOCAL_STORAGE_DIR / "uploads"
VIDEOS_DIR = LOCAL_STORAGE_DIR / "videos"
SUBTITLES_DIR = LOCAL_STORAGE_DIR / "subtitles"
TEMP_DIR = LOCAL_STORAGE_DIR / "temp"

for path in (UPLOADS_DIR, VIDEOS_DIR, SUBTITLES_DIR, TEMP_DIR):
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
    output_video_path: Path,
    output_srt_path: Path,
    model_size: str,
    fontsize: int,
    fontcolor: str,
    bgcolor: str,
    bg_opacity: int,
    output_mode: str,
    caption_mode: str,
) -> None:
    log_stream = io.StringIO()
    temp_audio_path = TEMP_DIR / f"{job_id}_audio.mp3"
    try:
        update_job(
            job_id,
            status="running",
            stage="Extracting audio",
            progress=5,
            started_at=datetime.utcnow().isoformat(),
        )

        with redirect_stdout(log_stream), redirect_stderr(log_stream):
            extract_audio_from_video(str(input_path), str(temp_audio_path))
            update_job(job_id, stage="Transcribing audio", progress=35)
            transcribe_audio_to_srt(
                str(temp_audio_path),
                model_size=model_size,
                output_srt_path=str(output_srt_path),
                caption_mode=caption_mode,
            )

            if output_mode in {"burned_video", "both"}:
                update_job(job_id, stage="Burning subtitles into video", progress=70)
                burn_subtitles_into_video(
                    input_video_path=str(input_path),
                    srt_file_path=str(output_srt_path),
                    output_video_path=str(output_video_path),
                    fontsize=fontsize,
                    fontcolor=fontcolor,
                    bgcolor=bgcolor,
                    bg_opacity=bg_opacity,
                )
            else:
                update_job(job_id, stage="Preparing subtitle file", progress=85)

        update_job(
            job_id,
            status="completed",
            stage="Done",
            progress=100,
            log=log_stream.getvalue(),
            completed_at=datetime.utcnow().isoformat(),
            output_video_filename=output_video_path.name if output_video_path.exists() else None,
            output_srt_filename=output_srt_path.name if output_srt_path.exists() else None,
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
    finally:
        if input_path.exists():
            try:
                input_path.unlink()
            except OSError:
                pass
        if temp_audio_path.exists():
            try:
                temp_audio_path.unlink()
            except OSError:
                pass


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
    output_mode = request.form.get("output_mode", "burned_video")
    caption_mode = request.form.get("caption_mode", "translate_to_english")

    safe_name = secure_filename(file.filename)
    job_id = uuid.uuid4().hex[:12]
    source_name = f"{job_id}_{safe_name}"
    output_video_name = f"{Path(safe_name).stem}_captioned_{job_id}.mp4"
    output_srt_name = f"{Path(safe_name).stem}_{job_id}.srt"

    input_path = UPLOADS_DIR / source_name
    output_video_path = VIDEOS_DIR / output_video_name
    output_srt_path = SUBTITLES_DIR / output_srt_name
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
            "output_video_path": str(output_video_path),
            "output_srt_path": str(output_srt_path),
            "output_video_filename": None,
            "output_srt_filename": None,
            "output_mode": output_mode,
            "caption_mode": caption_mode,
            "error": None,
            "log": "",
        }

    worker = threading.Thread(
        target=run_pipeline_job,
        args=(
            job_id,
            input_path,
            output_video_path,
            output_srt_path,
            model_size,
            fontsize,
            fontcolor,
            bgcolor,
            bg_opacity,
            output_mode,
            caption_mode,
        ),
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

    return jsonify(dict(job))


@app.get("/api/download/<filename>")
def download_output(filename: str):
    safe_name = secure_filename(filename)
    candidate_paths = [VIDEOS_DIR / safe_name, SUBTITLES_DIR / safe_name]
    for path in candidate_paths:
        if path.exists() and path.is_file():
            return send_from_directory(path.parent, safe_name, as_attachment=True)
    return jsonify({"error": "File not found."}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
