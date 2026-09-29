import asyncio
import mimetypes
import secrets
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, WebSocket
from pydantic import BaseModel, Field

from . import db
from .analysis_engine import analyze
from .config import MAX_ANALYSIS_SAMPLES, MAX_UPLOAD_BYTES, UPLOAD_DIR
from .signal_io import read_signal

router = APIRouter(prefix="/api")


class AnalysisRequest(BaseModel):
    signal_id: str
    sample_rate: float | None = Field(default=None, gt=0)
    center_frequency: float | None = None
    iq_format: str | None = None


class DemodulationRequest(BaseModel):
    modulation: str = Field(..., description="Measured or operator-selected modulation, for example BPSK, QPSK, 8PSK, 16QAM, or FSK")
    symbol_rate: float | None = Field(default=None, gt=0)
    sps: float | None = Field(default=None, gt=0)


def _error(code: str, message: str, status_code: int = 400) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"success": False, "error": {"code": code, "message": message}})


def _signal_path(record: dict[str, Any]) -> Path:
    path = (UPLOAD_DIR / record["stored_name"]).resolve()
    if path.parent != UPLOAD_DIR.resolve() or not path.exists():
        raise _error("SIGNAL_NOT_FOUND", "Stored signal file is unavailable.", 404)
    return path


def _latest(signal_id: str) -> dict[str, Any]:
    result = db.latest_result_for_signal(signal_id)
    if not result:
        raise _error("ANALYSIS_NOT_FOUND", "No completed analysis exists for this signal.", 404)
    return result


def _run_analysis(analysis_id: str, request: AnalysisRequest) -> None:
    record = db.get_signal(request.signal_id)
    try:
        if not record:
            raise ValueError("Signal does not exist")
        db.update_job(analysis_id, status="PROCESSING", stage="PARSING", progress=10, message="Reading signal samples")
        metadata = {"sample_rate": request.sample_rate or record.get("sample_rate"), "center_frequency": request.center_frequency if request.center_frequency is not None else record.get("center_frequency"), "iq_format": request.iq_format or record.get("iq_format")}
        if record["file_type"] == "IQ" and (not metadata["sample_rate"] or not metadata["iq_format"]):
            raise ValueError("IQ sample rate and sample format are required")
        samples, parsed = read_signal(_signal_path(record), record["file_type"], metadata, MAX_ANALYSIS_SAMPLES)
        rate = float(parsed.get("sample_rate") or metadata["sample_rate"])
        db.update_job(analysis_id, stage="FFT_ANALYSIS", progress=40, message="Calculating FFT and PSD")
        result = analyze(samples, rate, parsed.get("center_frequency") or metadata.get("center_frequency"))
        result["analysis_id"] = analysis_id
        result["signal_id"] = request.signal_id
        result["filename"] = record["filename"]
        result["file_type"] = record["file_type"]
        result["channels"] = parsed.get("channels")
        db.update_job(analysis_id, stage="FEATURE_EXTRACTION", progress=75, message="Extracting measured features")
        db.save_result(analysis_id, request.signal_id, result)
        db.save_report(analysis_id, {"analysis_id": analysis_id, "signal": {"filename": record["filename"], "file_type": record["file_type"], "sample_rate": rate, "duration": result["duration"], "center_frequency": result["center_frequency"]}, "parameters": result})
        db.update_job(analysis_id, status="COMPLETED", stage="COMPLETED", progress=100, message="Analysis completed")
    except Exception as exc:
        db.update_job(analysis_id, status="FAILED", stage="FAILED", progress=100, error=str(exc), message="Analysis failed")


@router.get("/health", tags=["health"])
def health() -> dict[str, Any]:
    return {"success": True, "data": {"status": "healthy", "service": "SIGMA RF Intelligence API"}}


@router.post("/signals/upload", tags=["signals"])
async def upload_signal(file: UploadFile = File(...), sample_rate: float | None = Form(default=None), iq_format: str | None = Form(default=None)) -> dict[str, Any]:
    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in {".iq", ".wav"}:
        raise _error("UNSUPPORTED_FORMAT", "Only .iq and .wav files are supported.")
    if file.content_type and file.content_type not in {"application/octet-stream", "audio/wav", "audio/x-wav", "audio/wave"}:
        raise _error("INVALID_MIME", "The uploaded MIME type is not supported.")
    signal_id = f"SIG-{secrets.token_hex(5).upper()}"
    stored_name = f"{signal_id}{suffix}"
    target = UPLOAD_DIR / stored_name
    total = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    target.unlink(missing_ok=True)
                    raise _error("FILE_TOO_LARGE", f"Maximum upload size is {MAX_UPLOAD_BYTES} bytes.")
                output.write(chunk)
        parsed = {}
        if suffix == ".wav":
            _, parsed = read_signal(target, "WAV", None, MAX_ANALYSIS_SAMPLES)
        resolved_rate = parsed.get("sample_rate") or sample_rate
        resolved_format = parsed.get("iq_format") or iq_format
        values = {"id": signal_id, "filename": filename, "stored_name": stored_name, "file_type": suffix[1:].upper(), "size_bytes": total, "mime_type": file.content_type or mimetypes.guess_type(filename)[0], "sample_rate": resolved_rate, "center_frequency": None, "iq_format": resolved_format, "channels": parsed.get("channels"), "duration": (total / 8 / resolved_rate) if suffix == ".iq" and resolved_rate else parsed.get("duration"), "num_samples": parsed.get("num_samples") or ((total // 8) if suffix == ".iq" else None), "requires_metadata": suffix == ".iq" and (not resolved_rate or not resolved_format), "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        db.insert_signal(values)
        return {"success": True, "data": {"signal_id": signal_id, "filename": filename, "file_type": values["file_type"], "status": "UPLOADED", "requires_metadata": bool(values["requires_metadata"]), "metadata": values}}
    except HTTPException:
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise _error("INVALID_SIGNAL", str(exc))


@router.get("/signals", tags=["signals"])
def signals() -> dict[str, Any]:
    return {"success": True, "data": db.list_signals()}


@router.get("/signals/{signal_id}", tags=["signals"])
def signal(signal_id: str) -> dict[str, Any]:
    record = db.get_signal(signal_id)
    if not record:
        raise _error("SIGNAL_NOT_FOUND", "Signal was not found.", 404)
    return {"success": True, "data": record}


@router.delete("/signals/{signal_id}", tags=["signals"])
def delete(signal_id: str) -> dict[str, Any]:
    record = db.get_signal(signal_id)
    if not record:
        raise _error("SIGNAL_NOT_FOUND", "Signal was not found.", 404)
    _signal_path(record).unlink(missing_ok=True)
    db.delete_signal(signal_id)
    return {"success": True, "data": {"signal_id": signal_id, "status": "DELETED"}}


@router.post("/analysis", tags=["analysis"])
def create_analysis(request: AnalysisRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    record = db.get_signal(request.signal_id)
    if not record:
        raise _error("SIGNAL_NOT_FOUND", "Signal was not found.", 404)
    rate = request.sample_rate or record.get("sample_rate")
    fmt = request.iq_format or record.get("iq_format")
    if record["file_type"] == "IQ" and (not rate or not fmt):
        raise _error("MISSING_METADATA", "IQ analysis requires sample_rate and iq_format.")
    analysis_id = f"AN-{secrets.token_hex(5).upper()}"
    db.insert_job(analysis_id, request.signal_id)
    background_tasks.add_task(_run_analysis, analysis_id, request)
    return {"success": True, "data": {"analysis_id": analysis_id, "signal_id": request.signal_id, "status": "QUEUED"}}


@router.get("/analysis/{analysis_id}", tags=["analysis"])
def analysis(analysis_id: str) -> dict[str, Any]:
    job = db.get_job(analysis_id)
    if not job:
        raise _error("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)
    result = db.get_result(analysis_id)
    return {"success": True, "data": {"job": job, "result": result}}


@router.get("/analysis/{analysis_id}/results", tags=["analysis"])
def results(analysis_id: str) -> dict[str, Any]:
    result = db.get_result(analysis_id)
    if not result:
        raise _error("RESULT_NOT_READY", "Analysis results are not ready.", 404)
    return {"success": True, "data": result}


@router.post("/analysis/{analysis_id}/demodulate", tags=["analysis"])
def demodulate_analysis(analysis_id: str, request: DemodulationRequest) -> dict[str, Any]:
    job = db.get_job(analysis_id)
    if not job:
        raise _error("ANALYSIS_NOT_FOUND", "Analysis was not found.", 404)
    record = db.get_signal(job["signal_id"])
    result = db.get_result(analysis_id)
    if not record or not result:
        raise _error("RESULT_NOT_READY", "Analysis results are not ready.", 409)
    if request.modulation.upper() not in {"BPSK", "QPSK", "8PSK", "16QAM", "2FSK", "BFSK", "FSK"}:
        return {"success": True, "data": {"status": "NOT_SUPPORTED", "modulation": request.modulation, "reason": "No reliable prototype demodulator is registered for this modulation."}}
    try:
        from recovery.demodulators import demodulate
        samples, parsed = read_signal(_signal_path(record), record["file_type"], {"sample_rate": result["sampling_rate"], "iq_format": record.get("iq_format")}, MAX_ANALYSIS_SAMPLES)
        decoded = demodulate(samples, modulation=request.modulation, sample_rate=float(parsed.get("sample_rate") or result["sampling_rate"]), symbol_rate=request.symbol_rate, sps=request.sps)
        diagnostics = decoded.get("diagnostics", {})
        locked = bool(diagnostics.get("locked"))
        return {"success": True, "data": {"status": "COMPLETED" if locked else "NOT_SUPPORTED", "modulation": request.modulation, "samples_processed": len(samples), "bitstream_available": bool(decoded.get("bits")) if locked else False, "bits": decoded.get("bits", [])[:10000], "diagnostics": diagnostics}}
    except Exception as exc:
        raise _error("DEMODULATION_FAILED", str(exc))


@router.get("/signals/{signal_id}/spectrum", tags=["visualization"])
def spectrum(signal_id: str) -> dict[str, Any]:
    return {"success": True, "data": _latest(signal_id)["spectrum"]}


@router.get("/signals/{signal_id}/spectrogram", tags=["visualization"])
def spectrogram(signal_id: str) -> dict[str, Any]:
    return {"success": True, "data": _latest(signal_id)["spectrogram"]}


@router.get("/signals/{signal_id}/constellation", tags=["visualization"])
def constellation(signal_id: str) -> dict[str, Any]:
    return {"success": True, "data": _latest(signal_id)["constellation"]}


@router.get("/reports/{analysis_id}", tags=["reports"])
def report(analysis_id: str) -> dict[str, Any]:
    value = db.get_report(analysis_id)
    if not value:
        raise _error("REPORT_NOT_FOUND", "Report is not available.", 404)
    return {"success": True, "data": value}


@router.get("/history", tags=["history"])
def history() -> dict[str, Any]:
    return {"success": True, "data": [{"job": db.get_job(row["id"]), "result": db.get_result(row["id"])} for row in _jobs()]}


def _jobs() -> list[dict[str, Any]]:
    import sqlite3
    from .config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute("SELECT id FROM analysis_jobs ORDER BY updated_at DESC")]
    finally:
        conn.close()


@router.websocket("/ws/analysis/{analysis_id}")
async def analysis_socket(websocket: WebSocket, analysis_id: str) -> None:
    await websocket.accept()
    try:
        while True:
            job = db.get_job(analysis_id)
            if not job:
                await websocket.send_json({"error": "Analysis was not found"})
                return
            await websocket.send_json({"analysis_id": analysis_id, "stage": job["stage"], "progress": job["progress"], "message": job["message"], "status": job["status"]})
            if job["status"] in {"COMPLETED", "FAILED"}:
                return
            await asyncio.sleep(0.5)
    finally:
        await websocket.close()
