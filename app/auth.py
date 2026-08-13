"""Minimal webhook auth for the exercise.

Real payment webhooks verify a provider signature; here we use a shared token
in the ``X-Webhook-Token`` header. Use ``require_webhook_token`` as a FastAPI
dependency to gate the webhook. (In a real system the token/secret would come
from config, not a constant.)
"""

from fastapi import Header, HTTPException

WEBHOOK_TOKEN = "dev-webhook-secret"


def require_webhook_token(x_webhook_token: str = Header(default="")) -> str:
    if x_webhook_token != WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing webhook token")
    return x_webhook_token
