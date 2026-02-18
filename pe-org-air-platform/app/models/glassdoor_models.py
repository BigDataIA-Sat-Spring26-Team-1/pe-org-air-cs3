from datetime import datetime, date
from typing import Optional, Dict
from pydantic import BaseModel

class GlassdoorReview(BaseModel):
    id: str
    company_id: str
    ticker: str
    review_date: datetime
    rating: float
    title: Optional[str] = None
    pros: Optional[str] = None
    cons: Optional[str] = None
    advice_to_management: Optional[str] = None
    is_current_employee: bool = False
    job_title: Optional[str] = None
    location: Optional[str] = None
    culture_rating: float = 0.0
    diversity_rating: float = 0.0
    work_life_rating: float = 0.0
    senior_management_rating: float = 0.0
    comp_benefits_rating: float = 0.0
    career_opp_rating: float = 0.0
    recommend_to_friend: Optional[str] = None
    ceo_rating: Optional[str] = None
    business_outlook: Optional[str] = None
    raw_json: Optional[Dict] = None

from decimal import Decimal

class CultureSignal(BaseModel):
    company_id: str
    ticker: str
    batch_date: date
    innovation_score: Decimal
    data_driven_score: Decimal
    ai_awareness_score: Decimal
    change_readiness_score: Decimal
    overall_sentiment: Decimal
    review_count: int
    avg_rating: Decimal
    current_employee_ratio: Decimal
    positive_keywords_found: list[str] = []
    negative_keywords_found: list[str] = []
    confidence_score: Decimal