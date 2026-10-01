"""Shared helpers for serving stored files."""

from fastapi import Response

from app.services.storage import LocalStorage


async def file_response(
    storage: LocalStorage,
    *,
    storage_key: str,
    filename: str | None,
    mime_type: str | None,
) -> Response:
    content = await storage.read_async(storage_key)
    return Response(
        content=content,
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename or "file"}"'},
    )
