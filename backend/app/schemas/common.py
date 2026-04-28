"""Use: Defines small shared API schemas used across routers.
Where to use: Import these for simple message and error responses.
Role: Schema layer. It keeps common response shapes explicit and reusable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class RateLimitErrorResponse(BaseModel):
    code: str = "rate_limit_exceeded"
    message: str
    limit: int = Field(gt=0)
    window_seconds: int = Field(gt=0)
    retry_after_seconds: int = Field(ge=0)


class PaginatedResponse(BaseModel):
    """Standard paginated list response matching frontend expectations."""
    items: list = Field(default_factory=list, description="List of items for this page")
    total: int = Field(default=0, ge=0, description="Total count across all pages")
    page: int = Field(default=1, ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    total_pages: int = Field(default=0, ge=0, description="Total number of pages")
