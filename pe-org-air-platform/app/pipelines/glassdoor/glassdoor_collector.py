import asyncio
import json
import logging
import httpx
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional

from app.config import settings
from app.models.glassdoor_models import GlassdoorReview, CultureSignal

logger = logging.getLogger(__name__)

# --- Constants ---

COMPANY_IDS = {
    "NVDA": "7633",
    "JPM": "5224839",
    "WMT": "715",
    "GE": "277",
    "DG": "1342"
}

WEXTRACTOR_URL = "https://wextractor.com/api/v1/reviews/glassdoor"



# --- New Constants ---

INNOVATION_POSITIVE = [
    "innovative", "cutting-edge", "forward-thinking",
    "encourages new ideas", "experimental", "creative freedom",
    "startup mentality", "move fast", "disruptive"
]

INNOVATION_NEGATIVE = [
    "bureaucratic", "slow to change", "resistant",
    "outdated", "stuck in old ways", "red tape",
    "politics", "siloed", "hierarchical"
]

DATA_DRIVEN_KEYWORDS = [
    "data-driven", "metrics", "evidence-based",
    "analytical", "kpis", "dashboards", "data culture",
    "measurement", "quantitative"
]

AI_AWARENESS_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning",
    "automation", "data science", "ml", "algorithms",
    "predictive", "neural network"
]

CHANGE_POSITIVE = [
    "agile", "adaptive", "fast-paced", "embraces change",
    "continuous improvement", "growth mindset"
]

CHANGE_NEGATIVE = [
    "rigid", "traditional", "slow", "risk-averse",
    "change resistant", "old school"
]

# --- Collector Class ---



class GlassdoorCollector:
    def __init__(self):
        self.api_key = settings.WEXTRACTOR_API_KEY.get_secret_value() if settings.WEXTRACTOR_API_KEY else None
        if not self.api_key or self.api_key == "dummy_key":
            logger.warning("WEXTRACTOR_API_KEY is not set or is dummy. Collector will fail.")

    async def fetch_reviews(self, ticker: str, glassdoor_id: str = None, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Fetch raw reviews from Wextractor API.
        If glassdoor_id is provided, uses it. Otherwise looks up in COMPANY_IDS.
        """
        if not glassdoor_id:
            glassdoor_id = COMPANY_IDS.get(ticker)
        
        if not glassdoor_id:
            logger.error(f"No Glassdoor ID found for ticker {ticker} and none provided.")
            return []

        params = {
            "id": glassdoor_id,
            "auth_token": self.api_key,
            "offset": offset,
            "limit": limit, # Note: API might ignore limit > 10
            "language": "en"
        }
        
        all_reviews = []
        current_offset = offset
        
        async with httpx.AsyncClient() as client:
            try:
                fetched_count = 0
                while fetched_count < limit:
                    params["offset"] = current_offset
                    logger.info(f"Fetching Glassdoor reviews for {ticker} (ID: {glassdoor_id}), offset={current_offset}")
                    
                    response = await client.get(WEXTRACTOR_URL, params=params, timeout=30.0)
                    logger.debug(f"Wextractor response status: {response.status_code}")
                    response.raise_for_status()
                    data = response.json()
                    
                    reviews = data.get("reviews", [])
                    if not reviews:
                        break
                        
                    all_reviews.extend(reviews)
                    fetched_count += len(reviews)
                    current_offset += len(reviews)
                    
                    # Rate limit sleep
                    await asyncio.sleep(0.5)
                    
                    if len(reviews) < 10:
                        break
                        
            except httpx.HTTPError as e:
                logger.error(f"Error fetching from Wextractor: {e}")
                return []
                
        return all_reviews[:limit]




    def parse_review(self, raw: Dict, ticker: str, company_id: str) -> GlassdoorReview:
        """
        Parse a single raw review dictionary into a GlassdoorReview object.
        """
        # Date parsing
        # Example: "2022-10-04T13:32:07.730"
        try:
            rdate = datetime.fromisoformat(raw.get("datetime"))
        except:
            rdate = datetime.now()

        # Helper for ratings (some might be strings like "4.4" or empty)
        def parse_float(val):
            try:
                return float(val)
            except:
                return 0.0

        return GlassdoorReview(
            id=raw.get("id"),
            company_id=company_id,
            ticker=ticker,
            review_date=rdate,
            rating=parse_float(raw.get("rating")),
            title=raw.get("title"),
            pros=raw.get("pros"),
            cons=raw.get("cons"),
            advice_to_management=raw.get("advice"),
            is_current_employee=raw.get("is_current_job", False),
            job_title=raw.get("reviewer"),
            location=raw.get("location"),
            culture_rating=parse_float(raw.get("culture_and_values_rating")),
            diversity_rating=parse_float(raw.get("diversity_and_inclusion_rating")),
            work_life_rating=parse_float(raw.get("work_life_balance_rating")),
            senior_management_rating=parse_float(raw.get("senior_management_rating")),
            comp_benefits_rating=parse_float(raw.get("compensation_and_benefits_rating")),
            career_opp_rating=parse_float(raw.get("career_opportunities_rating")),
            recommend_to_friend=raw.get("rating_recommend_to_friend"),
            ceo_rating=raw.get("rating_ceo"),
            business_outlook=raw.get("rating_business_outlook"),
            raw_json=raw
        )





    def analyze_reviews(self, reviews: List[GlassdoorReview]) -> Optional[CultureSignal]:
        """
        Analyze reviews for culture indicators using weighted keyword scoring.
        Algorithm:
        1. Combine pros and cons text for each review
        2. Count keyword matches for each category
        3. Weight by recency (last 2 years = full weight, older = 0.5)
        4. Weight current employees higher (1.2x multiplier)
        5. Calculate component scores
        6. Calculate overall weighted average
        """
        if not reviews:
            return None

        # Initialize weighted sums
        innov_score_sum = Decimal(0)
        data_score_sum = Decimal(0)
        ai_score_sum = Decimal(0)
        change_score_sum = Decimal(0)
        
        total_weight = Decimal(0)

        # Evidence Aggregation
        all_positive_keywords = set()
        all_negative_keywords = set()

        # Metrics
        total_rating_sum = Decimal(0)
        current_employee_count = 0

        for r in reviews:
            # Metrics
            total_rating_sum += Decimal(r.rating)
            if r.is_current_employee:
                current_employee_count += 1

            # 1. Combine text
            text = (r.pros or "") + " " + (r.cons or "")
            text = text.lower()
            
            # 2. Match Keywords (simple containment)
            # Innovation
            innov_pos = 0
            for k in INNOVATION_POSITIVE:
                if k in text:
                    innov_pos += 1
                    all_positive_keywords.add(k)
            
            innov_neg = 0
            for k in INNOVATION_NEGATIVE:
                if k in text:
                    innov_neg += 1
                    all_negative_keywords.add(k)
            
            innov_net = innov_pos - innov_neg

            # Data
            data_mentions = 0
            for k in DATA_DRIVEN_KEYWORDS:
                if k in text:
                    data_mentions += 1
                    all_positive_keywords.add(k)

            # AI
            ai_mentions = 0
            for k in AI_AWARENESS_KEYWORDS:
                if k in text:
                    ai_mentions += 1
                    all_positive_keywords.add(k)

            # Change
            change_pos = 0
            for k in CHANGE_POSITIVE:
                if k in text:
                    change_pos += 1
                    all_positive_keywords.add(k)
            
            change_neg = 0
            for k in CHANGE_NEGATIVE:
                if k in text:
                    change_neg += 1
                    all_negative_keywords.add(k)
            
            change_net = change_pos - change_neg

            # 3. Recency Weight
            days_old = (date.today() - r.review_date.date()).days
            recency_weight = Decimal("1.0") if days_old < 730 else Decimal("0.5")
            
            # 4. Employee Status Weight
            employee_weight = Decimal("1.2") if r.is_current_employee else Decimal("1.0")
            
            weight = recency_weight * employee_weight
            total_weight += weight

            # Accumulate weighted contributions
            innov_score_sum += Decimal(innov_net) * weight
            data_score_sum += Decimal(data_mentions) * weight
            ai_score_sum += Decimal(ai_mentions) * weight
            change_score_sum += Decimal(change_net) * weight
            
        # 5. Calculate Component Scores (normalized 0-100)
        
        if total_weight == 0:
            return None

        # Normalized to 0-100 range roughly
        innov_final = (innov_score_sum / total_weight) * Decimal(50) + Decimal(50)
        change_final = (change_score_sum / total_weight) * Decimal(50) + Decimal(50)
        data_final = (data_score_sum / total_weight) * Decimal(100)
        ai_final = (ai_score_sum / total_weight) * Decimal(100)
        
        # Clamp scores 0-100
        def clamp(x): return max(Decimal(0), min(Decimal(100), x))
        
        innov_final = clamp(innov_final)
        change_final = clamp(change_final)
        data_final = clamp(data_final)
        ai_final = clamp(ai_final)

        logger.debug(f"Culture Component Scores for {reviews[0].ticker}: "
                     f"Innov={innov_final}, Change={change_final}, "
                     f"Data={data_final}, AI={ai_final}")
        
        # 6. Overall Weighted Average (CORRECTED WEIGHTS)
        overall = (
            Decimal("0.30") * innov_final +   # Requirement: 30%
            Decimal("0.25") * data_final +
            Decimal("0.25") * ai_final +
            Decimal("0.20") * change_final    # Requirement: 20%
        )
        
        # Additional Metrics
        avg_rating = total_rating_sum / Decimal(len(reviews))
        current_employee_ratio = Decimal(current_employee_count) / Decimal(len(reviews))

        return CultureSignal(
            company_id=reviews[0].company_id,
            ticker=reviews[0].ticker,
            batch_date=date.today(),
            innovation_score=round(innov_final, 2),
            data_driven_score=round(data_final, 2),
            ai_awareness_score=round(ai_final, 2),
            change_readiness_score=round(change_final, 2),
            overall_sentiment=round(overall, 2),
            review_count=len(reviews),
            avg_rating=round(avg_rating, 2),
            current_employee_ratio=round(current_employee_ratio, 2),
            positive_keywords_found=list(all_positive_keywords),
            negative_keywords_found=list(all_negative_keywords),
            confidence_score=Decimal("0.8")
        )
