from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class SummaryRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=50000)
    summary_length: Optional[str] = Field(default="medium", pattern="^(short|medium|long)$")


    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')

        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v).strip()

        # Basic validation for meaningful content
        words = v.split()
        if len(words) < 10:
            raise ValueError('Text must contain at least 10 words')

        return v

    @validator('summary_length')
    def validate_summary_length(cls, v):
        if v not in ['short', 'medium', 'long']:
            raise ValueError('Summary length must be short, medium, or long')
        return v


class SummaryResponse(BaseModel):
    summary: str
    original_length: int
    summary_length: int
    compression_ratio: float
    processing_time: float

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None