"""Webhook auth: provider-style HMAC signature verification.

Real payment webhooks aren't gated by a shared bearer token — the sender
signs the request with a secret only it and the platform know (HMAC over the
raw request body) and the platform recomputes that HMAC and compares it in
constant time. This mirrors Paystack's ``x-paystack-signature`` convention
(HMAC-SHA512 over the raw JSON body, hex-encoded) since "paystack" is this
exercise's default channel.

Verification runs against the *raw* body bytes, not the parsed-and-reserialized
Pydantic model — re-encoding JSON can reorder keys or change whitespace,
which would change the bytes and break a legitimate signature.
"""

import hashlib
import hmac

from fastapi import Header, HTTPException, Request

# NOTE: in a real system this is per-provider config pulled from a secret
# store, never a constant — and each rail (gateway, GSI, core-banking feed)
# would have its own secret and its own signature convention.
WEBHOOK_SIGNING_SECRET = "dev-webhook-secret"


async def require_webhook_signature(
    request: Request, x_webhook_signature: str = Header(default="")
) -> bytes:
    raw_body = await request.body()
    expected = hmac.new(WEBHOOK_SIGNING_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
    if not x_webhook_signature or not hmac.compare_digest(expected, x_webhook_signature):
        raise HTTPException(status_code=401, detail="invalid or missing webhook signature")
    return raw_body
