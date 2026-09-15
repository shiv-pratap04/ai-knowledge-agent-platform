import os
import uuid
from pathlib import Path

import requests

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
PDF_PATH = Path(__file__).parents[1] / "uploaded_docs" / "Computer Networking Notes for Tech Placements.pdf"
PASSWORD = "tenant-test-pass123"


def signup(username: str, org_name: str) -> str:
    response = requests.post(
        f"{BASE_URL}/signup",
        json={"username": username, "password": PASSWORD, "org_name": org_name},
        timeout=30,
    )
    response.raise_for_status()
    return login(username)


def login(username: str) -> str:
    response = requests.post(
        f"{BASE_URL}/login",
        json={"username": username, "password": PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main():
    suffix = uuid.uuid4().hex[:8]
    token_a = signup(f"isolation_a_{suffix}", f"Isolation A {suffix}")
    token_b = signup(f"isolation_b_{suffix}", f"Isolation B {suffix}")

    with PDF_PATH.open("rb") as pdf:
        upload = requests.post(
            f"{BASE_URL}/documents",
            headers=auth(token_a),
            files={"file": (PDF_PATH.name, pdf, "application/pdf")},
            timeout=180,
        )
    upload.raise_for_status()
    assert upload.json()["total_chunks_created"] > 0

    query = requests.post(
        f"{BASE_URL}/query",
        headers=auth(token_a),
        json={"question": "What is the OSI model?"},
        timeout=180,
    )
    query.raise_for_status()
    conversation_id = query.json()["conversation_id"]

    empty_conversation = requests.post(
        f"{BASE_URL}/conversations",
        headers=auth(token_a),
        json={"title": "Isolation test"},
        timeout=30,
    )
    empty_conversation.raise_for_status()

    other_conversation = requests.get(
        f"{BASE_URL}/conversations/{conversation_id}",
        headers=auth(token_b),
        timeout=30,
    )
    assert other_conversation.status_code == 404, other_conversation.text

    other_documents = requests.get(
        f"{BASE_URL}/documents",
        headers=auth(token_b),
        timeout=30,
    )
    other_documents.raise_for_status()
    assert other_documents.json() == [], other_documents.text

    other_conversations = requests.get(
        f"{BASE_URL}/conversations",
        headers=auth(token_b),
        timeout=30,
    )
    other_conversations.raise_for_status()
    assert other_conversations.json() == [], other_conversations.text

    print("PASS: Org B cannot access Org A's conversation (404).")
    print("PASS: Org B sees no documents from Org A.")
    print("PASS: Org B sees no conversations from Org A.")
    print("Tenant isolation test passed.")


if __name__ == "__main__":
    main()
