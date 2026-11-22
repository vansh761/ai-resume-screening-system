"""
Manual end-to-end check for Milestone 10 (needs the API and worker running).

Uploads a good resume and a corrupt one over HTTP, then polls until each
leaves the 'pending' state, printing how long every step took.

Run:  docker compose exec -T backend python scripts/e2e_async_upload.py [max_wait_seconds]
"""

import io
import sys
import time
import uuid

import httpx
from docx import Document

MAX_WAIT = float(sys.argv[1]) if len(sys.argv) > 1 else 90
BASE = "http://localhost:8000/api/v1"
client = httpx.Client(timeout=30)


def docx_bytes(text: str) -> bytes:
    doc = Document()
    doc.add_paragraph(text)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
r = client.post(f"{BASE}/auth/signup", json={
    "email": email, "password": "supersecret123",
    "full_name": "E2E Candidate", "role": "candidate",
})
r.raise_for_status()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload_and_watch(label: str, filename: str, content: bytes):
    t0 = time.time()
    r = client.post(f"{BASE}/resumes/upload", headers=headers,
                    files={"file": (filename, content, "application/octet-stream")})
    r.raise_for_status()
    body = r.json()
    print(f"[{label}] upload returned in {time.time() - t0:.2f}s -> status={body['processing_status']}")
    while time.time() - t0 < MAX_WAIT:
        cur = client.get(f"{BASE}/resumes/{body['id']}", headers=headers).json()
        if cur["processing_status"] != "pending":
            print(f"[{label}] became '{cur['processing_status']}' after {time.time() - t0:.2f}s")
            return cur
        time.sleep(0.5)
    print(f"[{label}] still pending after {MAX_WAIT:.0f}s")
    return None


good = upload_and_watch(
    "good resume", "good.docx",
    docx_bytes("Backend engineer with 5 years of experience building APIs with Python, "
               "FastAPI and PostgreSQL. Bachelor's degree in Computer Science."),
)
if good:
    print("   skills:", good["extracted_skills"], "| years:", good["years_experience"],
          "| education:", good["education_level"])

upload_and_watch("corrupt file", "bad.docx", b"this is not a real docx")
