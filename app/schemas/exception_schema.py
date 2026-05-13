"""RFC 7807 Problem Details model."""
#This defines the shape of error responses (RFC 7807 standard).
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str
    request_id: str
