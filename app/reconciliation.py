"""Read-only comparison of a synthetic settlement CSV with current payments."""

import csv
import io

from fastapi import HTTPException

HEADER = ["payment_id", "amount_minor", "currency"]


def parse_csv(value: str) -> list[dict[str, str]]:
    try:
        reader = csv.DictReader(io.StringIO(value), strict=True)
        if reader.fieldnames != HEADER:
            raise ValueError("Header must be payment_id,amount_minor,currency")
        records = list(reader)
        if len(records) > 100:
            raise ValueError("Use at most 100 settlement rows.")
        for row in records:
            if set(row) != set(HEADER) or any(cell is None for cell in row.values()):
                raise ValueError("Each row needs exactly three fields.")
            if not row["payment_id"] or len(row["payment_id"]) > 80:
                raise ValueError("Every row needs a payment ID of at most 80 characters.")
            amount = row["amount_minor"]
            if not amount.isascii() or not amount.isdecimal() or not 1 <= int(amount) <= 10_000_000:
                raise ValueError("Amounts must be positive integer INR minor units within the demo limit.")
            if row["currency"] != "INR":
                raise ValueError("This demo accepts INR settlement rows only.")
        return records
    except (ValueError, csv.Error) as error:
        raise HTTPException(422, str(error)) from error


def compare(records: list[dict[str, str]], payments: dict[str, dict]) -> dict:
    findings, seen, matched = [], set(), 0
    for row in records:
        payment_id = row["payment_id"]
        if payment_id in seen:
            findings.append({"payment_id": payment_id, "kind": "duplicate_settlement", "detail": "ID occurs more than once in the file."})
            continue
        seen.add(payment_id)
        payment = payments.get(payment_id)
        if payment is None:
            kind, detail = "unknown_payment", "No matching payment in this demo session."
        elif payment["status"] != "succeeded":
            kind, detail = "status_mismatch", f"Internal payment status is {payment['status']}."
        elif payment["amount_minor"] != int(row["amount_minor"]):
            kind, detail = "amount_mismatch", f"Expected {payment['amount_minor']} minor units; file has {row['amount_minor']}."
        else:
            matched += 1
            continue
        findings.append({"payment_id": payment_id, "kind": kind, "detail": detail})
    for payment_id, payment in payments.items():
        if payment["status"] == "succeeded" and payment_id not in seen:
            findings.append({"payment_id": payment_id, "kind": "missing_settlement", "detail": "Successful payment is absent from this file."})
    return {"rows": len(records), "matched": matched, "findings": findings, "scope": "all successful payments in this demo session"}
