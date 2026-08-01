from __future__ import annotations

import hashlib


def hash_resume_answer(answer: str) -> str:
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


def resume_request_matches(receipt: object, *, idempotency_key: str, answer: str) -> bool:
    if not isinstance(receipt, dict) or receipt.get("idempotency_key") != idempotency_key:
        return False
    expected_hash = receipt.get("answer_hash")
    if isinstance(expected_hash, str):
        return expected_hash == hash_resume_answer(answer)
    stored_answer = receipt.get("answer")
    return isinstance(stored_answer, str) and stored_answer == answer


def terminal_resume_receipt(receipt: object) -> dict[str, str] | None:
    if not isinstance(receipt, dict):
        return None
    idempotency_key = receipt.get("idempotency_key")
    answer_hash = receipt.get("answer_hash")
    answer = receipt.get("answer")
    if not isinstance(idempotency_key, str):
        return None
    if not isinstance(answer_hash, str) and isinstance(answer, str):
        answer_hash = hash_resume_answer(answer)
    if not isinstance(answer_hash, str):
        return None
    return {"idempotency_key": idempotency_key, "answer_hash": answer_hash}
