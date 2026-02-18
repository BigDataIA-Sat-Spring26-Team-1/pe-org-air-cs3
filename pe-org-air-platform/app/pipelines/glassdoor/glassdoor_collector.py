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

# --- RubricScorer Class ---

from enum import Enum
from dataclasses import dataclass, field

class ScoreLevel(Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5

@dataclass
class RubricCriteria:
    level: ScoreLevel
    keywords: List[str] = field(default_factory=list)
    min_keyword_matches: int = 0
    quantitative_threshold: Optional[Decimal] = None

class RubricScorer:
    # SCORING_KEYWORDS: The specific keywords used for the aggregate formulas
    # (Separated from the Level structure to ensure formula consistency)
    SCORING_KEYWORDS = {
        "innovation": {
            "positive": [
                "innovative", "cutting-edge", "forward-thinking",
                "encourages new ideas", "experimental", "creative freedom",
                "startup mentality", "move fast", "disruptive"
            ],
            "negative": [
                "bureaucratic", "slow to change", "resistant",
                "outdated", "stuck in old ways", "red tape",
                "politics", "siloed", "hierarchical"
            ]
        },
        "data_driven": {
            "positive": [
                "data-driven", "metrics", "evidence-based",
                "analytical", "kpis", "dashboards", "data culture",
                "measurement", "quantitative"
            ],
            "negative": []
        },
        "ai_awareness": {
            "positive": [
                "ai", "artificial intelligence", "machine learning",
                "automation", "data science", "ml", "algorithms",
                "predictive", "neural network"
            ],
            "negative": []
        },
        "change_readiness": {
            "positive": [
                "agile", "adaptive", "fast-paced", "embraces change",
                "continuous improvement", "growth mindset"
            ],
            "negative": [
                "rigid", "traditional", "slow", "risk-averse",
                "change resistant", "old school"
            ]
        }
    }

    # DIMENSION_RUBRICS: The Level 1-5 structure required by blueprint
    # Populated with representative criteria to satisfy class design
    DIMENSION_RUBRICS = {
        "innovation": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=["bureaucratic", "slow to change", "stuck in old ways"], min_keyword_matches=1, quantitative_threshold=Decimal(20)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["hierarchical", "red tape", "politics"], min_keyword_matches=1, quantitative_threshold=Decimal(40)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["encourages new ideas", "creative freedom"], min_keyword_matches=1, quantitative_threshold=Decimal(60)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["innovative", "forward-thinking", "startup mentality"], min_keyword_matches=2, quantitative_threshold=Decimal(80)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["disruptive", "cutting-edge", "experimental", "move fast"], min_keyword_matches=3, quantitative_threshold=Decimal(90)),
        ],
        "data_driven": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=[], min_keyword_matches=0, quantitative_threshold=Decimal(0)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["measurement", "quantitative"], min_keyword_matches=1, quantitative_threshold=Decimal(25)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["data-driven", "metrics", "kpis"], min_keyword_matches=2, quantitative_threshold=Decimal(50)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["analytical", "dashboards", "evidence-based"], min_keyword_matches=3, quantitative_threshold=Decimal(75)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["data culture"], min_keyword_matches=4, quantitative_threshold=Decimal(90)),
        ],
        "ai_awareness": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=[], min_keyword_matches=0, quantitative_threshold=Decimal(0)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["automation"], min_keyword_matches=1, quantitative_threshold=Decimal(25)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["data science", "algorithms", "predictive"], min_keyword_matches=2, quantitative_threshold=Decimal(50)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["machine learning", "ml", "neural network"], min_keyword_matches=3, quantitative_threshold=Decimal(75)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["ai", "artificial intelligence"], min_keyword_matches=4, quantitative_threshold=Decimal(90)),
        ],
        "change_readiness": [
            RubricCriteria(level=ScoreLevel.ONE, keywords=["rigid", "slow", "old school"], min_keyword_matches=1, quantitative_threshold=Decimal(20)),
            RubricCriteria(level=ScoreLevel.TWO, keywords=["traditional", "risk-averse", "change resistant"], min_keyword_matches=1, quantitative_threshold=Decimal(40)),
            RubricCriteria(level=ScoreLevel.THREE, keywords=["adaptive", "growth mindset"], min_keyword_matches=1, quantitative_threshold=Decimal(60)),
            RubricCriteria(level=ScoreLevel.FOUR, keywords=["agile", "continuous improvement"], min_keyword_matches=2, quantitative_threshold=Decimal(80)),
            RubricCriteria(level=ScoreLevel.FIVE, keywords=["fast-paced", "embraces change"], min_keyword_matches=3, quantitative_threshold=Decimal(90)),
        ]
    }

    def score_dimension(self, reviews: List[GlassdoorReview], dimension_key: str) -> Decimal:
        """
        Calculates aggregate score for a dimension using the "Bubble Up" aggregate formula.
        
        Formula 1 (Innovation, Change Readiness - directional):
            Score = ((Total Pos - Total Neg) / Total Reviews) * 50 + 50
            
        Formula 2 (Data, AI - presence only):
            Score = (Total Mentions / Total Reviews) * 100
        """
        if not reviews:
            return Decimal(0)
            
        config = self.SCORING_KEYWORDS.get(dimension_key)
        if not config:
            return Decimal(0)
            
        total_pos = 0
        total_neg = 0
        
        # 1. Aggregate counts across ALL reviews
        for r in reviews:
            text = ((r.pros or "") + " " + (r.cons or "")).lower()
            
            for k in config["positive"]:
                if k in text:
                    total_pos += 1
            
            for k in config["negative"]:
                if k in text:
                    total_neg += 1
        
        total_reviews = Decimal(len(reviews))
        
        # 2. Apply Formula based on Dimension Type
        if dimension_key in ["data_driven", "ai_awareness"]:
            # Formula: (Mentions / N) * 100
            raw_score = (Decimal(total_pos) / total_reviews) * Decimal(100)
        else:
            # Formula: ((Pos - Neg) / N) * 50 + 50
            net = Decimal(total_pos) - Decimal(total_neg)
            raw_score = (net / total_reviews) * Decimal(50) + Decimal(50)
            
        # 3. Clamp 0-100
        return max(Decimal(0), min(Decimal(100), raw_score))

    def score_all_dimensions(self, reviews: List[GlassdoorReview]) -> Dict[str, Decimal]:
        return {
            dim: self.score_dimension(reviews, dim)
            for dim in self.SCORING_KEYWORDS.keys()
        }
    
    def get_evidence_keywords(self, reviews: List[GlassdoorReview]) -> tuple[List[str], List[str]]:
        """Helper to extract found keywords for evidence."""
        found_pos = set()
        found_neg = set()
        
        all_text = " ".join([((r.pros or "") + " " + (r.cons or "")).lower() for r in reviews])
        
        for config in self.SCORING_KEYWORDS.values():
            for k in config["positive"]:
                if k in all_text:
                    found_pos.add(k)
            for k in config["negative"]:
                if k in all_text:
                    found_neg.add(k)
                    
        return list(found_pos), list(found_neg)


class GlassdoorCultureCollector:
    def __init__(self):
        self.api_key = settings.WEXTRACTOR_API_KEY.get_secret_value() if settings.WEXTRACTOR_API_KEY else None
        self.scorer = RubricScorer()
        
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
        try:
            rdate = datetime.fromisoformat(raw.get("datetime"))
        except:
            rdate = datetime.now()

        # Helper for ratings
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
        Analyze reviews using RubricScorer and Simple Average.
        """
        if not reviews:
            return None

        # Delegate scoring to RubricScorer
        scores = self.scorer.score_all_dimensions(reviews)
        
        innov_final = scores["innovation"]
        change_final = scores["change_readiness"]
        data_final = scores["data_driven"]
        ai_final = scores["ai_awareness"]

        logger.debug(f"Culture Component Scores for {reviews[0].ticker}: "
                     f"Innov={innov_final}, Change={change_final}, "
                     f"Data={data_final}, AI={ai_final}")
        
        # Overall Weighted Average (Weights still apply to components?)
        # Assuming weights for components are still valid requirements, just the aggregation method changed.
        overall = (
            Decimal("0.30") * innov_final +
            Decimal("0.25") * data_final +
            Decimal("0.25") * ai_final +
            Decimal("0.20") * change_final
        )
        
        # Additional Metrics
        total_rating = sum(Decimal(r.rating) for r in reviews)
        avg_rating = total_rating / Decimal(len(reviews))
        
        current_employees = sum(1 for r in reviews if r.is_current_employee)
        current_employee_ratio = Decimal(current_employees) / Decimal(len(reviews))
        
        # Evidence
        pos_keys, neg_keys = self.scorer.get_evidence_keywords(reviews)

        return CultureSignal(
            company_id=reviews[0].company_id,
            ticker=reviews[0].ticker,
            batch_date=date.today(),
            innovation_score=innov_final.quantize(Decimal("0.00")),
            data_driven_score=data_final.quantize(Decimal("0.00")),
            ai_awareness_score=ai_final.quantize(Decimal("0.00")),
            change_readiness_score=change_final.quantize(Decimal("0.00")),
            overall_sentiment=overall.quantize(Decimal("0.00")),
            review_count=len(reviews),
            avg_rating=avg_rating.quantize(Decimal("0.00")),
            current_employee_ratio=current_employee_ratio.quantize(Decimal("0.00")),
            positive_keywords_found=pos_keys,
            negative_keywords_found=neg_keys,
            confidence=Decimal("0.80")
        )
