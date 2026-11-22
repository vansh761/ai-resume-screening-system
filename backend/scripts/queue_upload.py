"""
Uploads one small resume and prints its status immediately.
Used by the worker-down durability check: the upload must be accepted
('pending') even while no worker is running.

Run:  docker compose exec -T backend python scripts/queue_upload.py
"""

import io
import uuid

import httpx
from docx import Document

BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=30)

r = c.post(f"{BASE}/auth/signup", json={
    "email": f"q-{uuid.uuid4().hex[:8]}@example.com", "password": "supersecret123",
    "full_name": "Queue Test", "role": "candidate",
})
r.raise_for_status()
headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

doc = Document()
doc.add_paragraph("Python developer with 3 years of experience.")
buffer = io.BytesIO()
doc.save(buffer)

r = c.post(f"{BASE}/resumes/upload", headers=headers,
           files={"file": ("q.docx", buffer.getvalue(), "application/octet-stream")})
r.raise_for_status()
print("uploaded ->", r.json()["processing_status"])
