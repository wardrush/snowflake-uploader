from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


@dataclass
class StoredFile:
    original_filename: str
    stored_name: str
    storage_path: str
    storage_backend: str
    size_bytes: int
    checksum_sha256: str
    content_type: str | None
    file_ext: str


class StorageService:
    def save_upload(self, file_storage: FileStorage, destination_hint: str) -> StoredFile:
        raise NotImplementedError


class LocalStorageService(StorageService):
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_storage: FileStorage, destination_hint: str) -> StoredFile:
        original_filename = file_storage.filename or "upload"
        safe_original = secure_filename(original_filename)
        ext = Path(safe_original).suffix.lower()
        stored_name = f"{Path(safe_original).stem}-{uuid.uuid4().hex}{ext}"

        dated_dir = self.root / destination_hint / datetime.utcnow().strftime("%Y/%m/%d")
        dated_dir.mkdir(parents=True, exist_ok=True)
        destination = dated_dir / stored_name

        digest = hashlib.sha256()
        size = 0
        with destination.open("wb") as handle:
            file_storage.stream.seek(0)
            while True:
                chunk = file_storage.stream.read(8192)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)

        file_storage.stream.seek(0)
        relative_path = destination.relative_to(self.root)
        return StoredFile(
            original_filename=original_filename,
            stored_name=stored_name,
            storage_path=str(relative_path).replace(os.sep, "/"),
            storage_backend="local",
            size_bytes=size,
            checksum_sha256=digest.hexdigest(),
            content_type=file_storage.content_type,
            file_ext=ext,
        )

    def delete(self, storage_path: str) -> None:
        target = (self.root / storage_path).resolve()
        if self.root.resolve() not in target.parents:
            return
        if target.exists():
            target.unlink()
