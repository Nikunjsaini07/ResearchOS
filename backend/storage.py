"""Read and remove legacy PDFs. New PDFs are processed in memory only."""
import os
from pathlib import Path
from urllib.parse import quote

import httpx


def remote_request(method, object_path, **kwargs):
    base = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base.startswith("https://") or not key:
        raise ValueError("Configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY on the server.")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", **kwargs.pop("headers", {})}
    try:
        with httpx.Client(timeout=60) as client:
            response = client.request(method, base + "/storage/v1/object/" + object_path, headers=headers, **kwargs)
            response.raise_for_status()
            return response
    except httpx.HTTPError:
        raise ValueError("PDF storage is unavailable. Check the private bucket and server storage settings.") from None


def read_pdf(reference):
    if reference.startswith("supabase://"):
        return remote_request("GET", "authenticated/" + quote(reference[11:], safe="/")).content
    return Path(reference).read_bytes()


def delete_pdf(reference):
    if reference.startswith("supabase://"):
        bucket, name = reference[11:].split("/", 1)
        remote_request("DELETE", quote(bucket, safe=""), json={"prefixes": [name]})
    else:
        Path(reference).unlink(missing_ok=True)
