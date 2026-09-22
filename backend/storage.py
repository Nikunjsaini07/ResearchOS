"""Private PDF storage, with local files for development."""
import os
from pathlib import Path
from urllib.parse import quote

import httpx
from backend.db import DATA


def remote_enabled():
    return bool(os.getenv("SUPABASE_URL"))


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


def save_pdf(paper_id, raw):
    if remote_enabled():
        bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "papers")
        path = f"{bucket}/{paper_id}.pdf"
        remote_request("POST", quote(path, safe="/"), content=raw,
                       headers={"Content-Type": "application/pdf", "x-upsert": "true"})
        return "supabase://" + path
    path = DATA / f"{paper_id}.pdf"
    path.write_bytes(raw)
    return str(path)


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
