from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator


class RawProduct(BaseModel):
    code: Optional[str] = None
    product_name: Optional[str] = None
    brands: Optional[str] = None
    quantity: Optional[str] = None
    categories_en: Optional[str] = None
    allergens_en: Optional[str] = None
    labels_en: Optional[str] = None
    ingredients_text_en: Optional[str] = None
    nutriscore_grade: Optional[str] = None


class EnrichedProduct(BaseModel):
    code: str
    product_name: Optional[str] = None
    brands: Optional[str] = None
    quantity_normalized: Optional[str] = None
    categories_clean: Optional[str] = None
    allergens_extracted: list[str] = []
    dietary_flags: list[str] = []
    ingredients_text_en: Optional[str] = None
    nutriscore_grade: Optional[str] = None
    dq_score_pre: float = 0.0
    dq_score_post: float = 0.0
    transformations_applied: list[str] = []
    enriched_by_llm: bool = False
    # dedup columns (added by find_duplicates)
    duplicate_group_id: Optional[int] = None
    canonical: Optional[bool] = None
    duplicate_score: Optional[float] = None


class DSPyOutput(BaseModel):
    categories_clean: str = ""
    allergens_extracted: str = ""   # comma-separated
    dietary_flags: str = ""          # comma-separated
    quantity_normalized: str = ""
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
