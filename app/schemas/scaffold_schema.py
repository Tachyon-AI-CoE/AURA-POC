"""ScaffoldResponse schema."""
#This defines the shape of success response when POST /scaffold works.
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ScaffoldResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: Literal["success"]
    scaffold_type: str
    repo_url: str
    config_path: str
    template_used: str
    created_at: str
    message: str
