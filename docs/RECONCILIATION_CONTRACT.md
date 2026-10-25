# Synthetic settlement comparison

`POST /api/reconcile` accepts JSON with a `csv` string. The CSV header must be exactly `payment_id,amount_minor,currency`. Each row uses a payment ID, a positive integer amount in paise and `INR`. The file is bounded to 100 rows and 30,000 characters. The endpoint reads the current demo session's payments and returns a comparison; it does not modify payment states or persist a settlement import.

The result reports a row count, match count and findings. A successful payment with a matching amount is a match. These findings are possible:

| Kind | Meaning |
|---|---|
| `missing_settlement` | A successful internal payment is absent from the supplied file. |
| `unknown_payment` | A file row has no matching payment in this session. |
| `duplicate_settlement` | A payment ID appears a second time in the supplied file. |
| `amount_mismatch` | The file amount differs from the successful internal payment. |
| `status_mismatch` | The file includes a payment that is not internally succeeded. |

Malformed headers, missing columns, unsupported currency, zero or fractional amounts and oversized files are rejected. A file with only the header reports every successful payment in the session as missing. Results depend on the current synthetic database snapshot; they are not financial settlement statements.

## Explain-back exercise

An internal payment is succeeded for 50,000 paise. The CSV lists the same ID twice: first for 40,000 paise, then for 50,000 paise. Which findings appear, and why is the second row not counted as a match? Explain which rule you might change for a different product requirement.
