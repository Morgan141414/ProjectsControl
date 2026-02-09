import hashlib
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageError(ValueError):
    pass


def _safe_suffix(filename: str | None) -> str:
    if not filename:
        return ".bin"
    suffix = Path(filename).suffix
    if not suffix or len(suffix) > 10:
        return ".bin"
    return suffix


def save_upload(
    file: UploadFile,
    org_id: str,
    session_id: str,
    recording_id: str,
) -> tuple[str, int, str]:
    if settings.STORAGE_DRIVER != "local":
        raise StorageError("Only local storage is configured")

    base_dir = Path(settings.STORAGE_PATH).resolve()
    target_dir = base_dir / org_id / session_id
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = _safe_suffix(file.filename)
    target_path = target_dir / f"{recording_id}{suffix}"

    hasher = hashlib.sha256()
    total_bytes = 0
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    with target_path.open("wb") as handle:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                target_path.unlink(missing_ok=True)
                raise StorageError("Upload exceeds size limit")
            handle.write(chunk)
            hasher.update(chunk)

    return str(target_path), total_bytes, hasher.hexdigest()
