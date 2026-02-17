import asyncio
import json
import logging
import httpx
from datetime import datetime, date
from typing import List, Dict

from app.config import settings
from app.services.s3_storage import aws_service
from app.services.snowflake import db
from app.pipelines.glassdoor.glassdoor_queries import MERGE_GLASSDOOR_REVIEWS
from app.models.glassdoor_model import GlassdoorReview, CultureSignal

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

# --- Collector Class ---

class GlassdoorCollector:
    def __init__(self):
        self.api_key = settings.WEXTRACTOR_API_KEY.get_secret_value() if settings.WEXTRACTOR_API_KEY else None
        if not self.api_key or self.api_key == "dummy_key":
            logger.warning("WEXTRACTOR_API_KEY is not set or is dummy. Collector will fail.")

    async def fetch_reviews(self, ticker: str, limit: int = 10, offset: int = 0) -> List[Dict]:
        """
        Fetch raw reviews from Wextractor API.
        """
        if ticker not in COMPANY_IDS:
            logger.error(f"No Glassdoor ID found for ticker {ticker}")
            return []

        glassdoor_id = COMPANY_IDS[ticker]
        params = {
            "id": glassdoor_id,
            "auth_token": self.api_key,
            "offset": offset,
            "limit": limit, # Note: API doc says it returns 10 per request, limit might not be adjustable per call but we can use offset loop
            "language": "en"
        }

        # Wextractor returns 10 at a time. If limit > 10, we need to loop.
        # For this implementation, we will fetch one batch or loop if needed.
        # But per user request "5 companies only for now", let's keep it simple.
        
        all_reviews = []
        current_offset = offset
        
        async with httpx.AsyncClient() as client:
            try:
                # We interpret 'limit' as 'pages' or 'batches' roughly, or just max items?
                # The API doc says "The Glassdoor API returns 10 reviews per request."
                # So if limit is 50, we need 5 calls.
                
                fetched_count = 0
                while fetched_count < limit:
                    params["offset"] = current_offset
                    logger.info(f"Fetching Glassdoor reviews for {ticker} (ID: {glassdoor_id}), offset={current_offset}")
                    
                    response = await client.get(WEXTRACTOR_URL, params=params, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    reviews = data.get("reviews", [])
                    if not reviews:
                        break
                        
                    all_reviews.extend(reviews)
                    fetched_count += len(reviews)
                    current_offset += len(reviews)
                    
                    # Rate limit sleep (10 req/sec is high, but good to be safe)
                    await asyncio.sleep(0.5)
                    
                    # If we got fewer than 10, we are at the end
                    if len(reviews) < 10:
                        break
                        
            except httpx.HTTPError as e:
                logger.error(f"Error fetching from Wextractor: {e}")
                return []
                
        return all_reviews[:limit]

    async def save_raw_to_s3(self, ticker: str, reviews: List[Dict]) -> str:
        """
        Save raw JSON to S3 and return the key.
        """
        if not reviews:
            return ""
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H%M%S")
        s3_key = f"raw/glassdoor/{ticker}/{date_str}_{timestamp}.json"
        
        success = aws_service.upload_bytes(
            data=json.dumps(reviews).encode('utf-8'),
            s3_key=s3_key,
            content_type="application/json"
        )
        
        if success:
            logger.info(f"Saved {len(reviews)} raw reviews to S3: {s3_key}")
            return s3_key
        else:
            logger.error(f"Failed to save raw reviews to S3: {s3_key}")
            return ""

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

    async def save_reviews_to_snowflake(self, reviews: List[GlassdoorReview]):
        """
        Bulk insert parsed reviews into Snowflake.
        """
        if not reviews:
            return

        # Prepare list of tuples for SQL insert
        # Table: glassdoor_reviews
        values = []
        for r in reviews:
            values.append((
                r.id,
                r.company_id,
                r.ticker,
                r.review_date,
                r.rating,
                r.title,
                r.pros[:4000] if r.pros else None,
                r.cons[:4000] if r.cons else None,
                r.advice_to_management[:4000] if r.advice_to_management else None,
                r.is_current_employee,
                r.job_title,
                r.location,
                r.culture_rating,
                r.diversity_rating,
                r.work_life_rating,
                r.senior_management_rating,
                r.comp_benefits_rating,
                r.career_opp_rating,
                r.recommend_to_friend,
                r.ceo_rating,
                r.business_outlook,
                json.dumps(r.raw_json)
            ))
        
        # Note: Snowflakes MERGE doesn't support executemany easily with simple binding in all connectors.
        # But our db service has _execute_many for INSERT. MERGE is tricky in bulk with bindings.
        # For simplicity/robustness in this prototype, let's just loop locally or use a temporary table approach.
        # Given the volume (10-50 reviews), simple loop or small batches is fine.
        # However, to be efficient, let's use the provided 'execute' in a loop for now, 
        # or better, use standard INSERT IGNORE logic if we didn't care about updates.
        # But we do want updates.
        
        # Let's try to use the `db.execute` for each row for now to be safe with MERGE syntax.
        for val in values:
            await db.execute(MERGE_GLASSDOOR_REVIEWS, val)
            
        logger.info(f"Upserted {len(reviews)} reviews to Snowflake.")

    def analyze_reviews(self, reviews: List[GlassdoorReview]) -> CultureSignal:
        """
        Mock analysis logic to produce a culture signal.
        Real implementation would use NLP specific keywords as defined in task.
        """
        if not reviews:
            return None
            
        # Placeholder logic
        innov_count = 0
        data_count = 0
        ai_count = 0
        change_count = 0
        
        for r in reviews:
            text = (r.pros or "") + " " + (r.cons or "")
            text = text.lower()
            
            if "innovation" in text or "startup" in text: innov_count += 1
            if "data" in text or "metrics" in text: data_count += 1
            if "ai" in text or "intelligence" in text: ai_count += 1
            if "change" in text or "fast" in text: change_count += 1
            
        total = len(reviews)
        
        return CultureSignal(
            company_id=reviews[0].company_id,
            ticker=reviews[0].ticker,
            batch_date=date.today(),
            innovation_score=round((innov_count / total) * 10, 2),
            data_driven_score=round((data_count / total) * 10, 2),
            ai_awareness_score=round((ai_count / total) * 10, 2),
            change_readiness_score=round((change_count / total) * 10, 2),
            overall_sentiment=0.0, # TODO: Avg rating
            review_count=total,
            confidence_score=0.8
        )

    async def run_pipeline(self, ticker: str, limit: int = 20):
        # 1. Fetch
        raw_reviews = await self.fetch_reviews(ticker, limit)
        if not raw_reviews:
            logger.info(f"No reviews found for {ticker}")
            return
            
        # 2. S3
        await self.save_raw_to_s3(ticker, raw_reviews)
        
        # 3. Parse
        parsed_reviews = [
            self.parse_review(r, ticker, COMPANY_IDS[ticker]) 
            for r in raw_reviews
        ]
        
        # 4. Snowflake
        await self.save_reviews_to_snowflake(parsed_reviews)
        
        # 5. Analyze
        signal = self.analyze_reviews(parsed_reviews)
        logger.info(f"Culture Signal for {ticker}: {signal}")
        
        # TODO: Persist CultureSignal to Snowflake 'culture_scores'
