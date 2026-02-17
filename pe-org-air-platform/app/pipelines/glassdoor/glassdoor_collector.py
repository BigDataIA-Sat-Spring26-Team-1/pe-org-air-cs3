import asyncio
import json
import logging
import httpx
from datetime import datetime, date
from typing import List, Dict

from app.config import settings
from app.services.s3_storage import aws_service
from app.services.snowflake import db
from app.pipelines.glassdoor.glassdoor_queries import MERGE_GLASSDOOR_REVIEWS, INSERT_CULTURE_SIGNAL
from app.models.glassdoor_model import GlassdoorReview, CultureSignal

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
# ... (existing imports and methods) ...

    def analyze_reviews(self, reviews: List[GlassdoorReview]) -> CultureSignal:
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
        innov_score_sum = 0
        data_score_sum = 0
        ai_score_sum = 0
        change_score_sum = 0
        
        total_weight = 0.0

        for r in reviews:
            # 1. Combine text
            text = (r.pros or "") + " " + (r.cons or "")
            text = text.lower()
            
            # 2. Match Keywords (simple containment)
            # Innovation
            innov_pos = sum(1 for hw in INNOVATION_POSITIVE if hw in text)
            innov_neg = sum(1 for hw in INNOVATION_NEGATIVE if hw in text)
            innov_net = innov_pos - innov_neg

            # Data
            data_mentions = sum(1 for hw in DATA_DRIVEN_KEYWORDS if hw in text)

            # AI
            ai_mentions = sum(1 for hw in AI_AWARENESS_KEYWORDS if hw in text)

            # Change
            change_pos = sum(1 for hw in CHANGE_POSITIVE if hw in text)
            change_neg = sum(1 for hw in CHANGE_NEGATIVE if hw in text)
            change_net = change_pos - change_neg

            # 3. Recency Weight
            days_old = (date.today() - r.review_date.date()).days
            recency_weight = 1.0 if days_old < 730 else 0.5
            
            # 4. Employee Status Weight
            employee_weight = 1.2 if r.is_current_employee else 1.0
            
            weight = recency_weight * employee_weight
            total_weight += weight

            # Accumulate weighted contributions
            # Formula interpretation:
            # Each review contributes its (net * weight) to the sum?
            # Or calculate score per review and average?
            # The image says: innovation_score = (positive_mentions - negative_mentions) / total_reviews * 50 + 50
            # Let's interpret "total_reviews" as "total_weight" in a weighted system.
            
            innov_score_sum += innov_net * weight
            data_score_sum += data_mentions * weight
            ai_score_sum += ai_mentions * weight
            change_score_sum += change_net * weight
            
        # 5. Calculate Component Scores (normalized 0-100)
        # Base 50, +/- based on net sentiment density.
        # Scaling factor: If every review has +1 net mention, score should be ~100? or ~60? 
        # Image says: (pos - neg) / total * 50 + 50.
        # Let's start with that but using weighted sums.
        
        if total_weight == 0:
            return None

        # Normalized to 0-100 range roughly
        # Innovation: Base 50. +1 avg net mention -> 100? No, let's say +1 avg is good.
        # Let's use a multiplier. 50?
        # (innov_score_sum / total_weight) is "avg net mentions per weighted review".
        # If avg is 1 (1 more pos than neg per review), score = 1 * 50 + 50 = 100.
        # If avg is -1, score = -1 * 50 + 50 = 0.
        # Perfectly reasonable range.
        
        innov_final = (innov_score_sum / total_weight) * 50 + 50
        change_final = (change_score_sum / total_weight) * 50 + 50
        
        # Data & AI: These are just mentions, no negative keywords listed in constants (for Data/AI).
        # Image Formula: data_driven_score = data_mentions / total_reviews * 100
        # Wait, mentions are usually sparse. If 1 in 10 reviews mentions it, avg is 0.1. Score = 10?
        # Maybe scale is higher or threshold based.
        # Let's stick to the linear formula from the prompt image logic if visible, 
        # or use a reasonable scaler like 100.
        # Logic in image (blurry) seems to be `data_mentions / total_reviews * 100`.
        # So providing 1 mention per review = 100 score.
        
        data_final = (data_score_sum / total_weight) * 100
        ai_final = (ai_score_sum / total_weight) * 100
        
        # Clamp scores 0-100
        def clamp(x): return max(0.0, min(100.0, x))
        
        innov_final = clamp(innov_final)
        change_final = clamp(change_final)
        data_final = clamp(data_final)
        ai_final = clamp(ai_final)
        
        # 6. Overall Weighted Average
        # Formula: 0.20 * innov + 0.25 * data + 0.25 * ai + 0.30 * change
        overall = (
            0.20 * innov_final +
            0.25 * data_final +
            0.25 * ai_final +
            0.30 * change_final
        )
        
        return CultureSignal(
            company_id=reviews[0].company_id,
            ticker=reviews[0].ticker,
            batch_date=date.today(),
            innovation_score=round(innov_final, 2),
            data_driven_score=round(data_final, 2),
            ai_awareness_score=round(ai_final, 2),
            change_readiness_score=round(change_final, 2),
            overall_sentiment=round(overall, 2), # Using overall culture score as sentiment
            review_count=len(reviews),
            confidence_score=0.8 # Placeholder or calc based on volume
        )

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
        date_str = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"raw/glassdoor/{ticker}/{date_str}.json"
        
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

    async def save_culture_signal(self, signal: CultureSignal):
        if not signal:
            return
            
        logger.info(f"Saving culture signal for {signal.ticker} to Snowflake...")
        try:
            await db.execute(
                INSERT_CULTURE_SIGNAL,
                (
                    signal.company_id,
                    signal.ticker,
                    signal.batch_date,
                    signal.innovation_score,
                    signal.data_driven_score,
                    signal.ai_awareness_score,
                    signal.change_readiness_score,
                    signal.overall_sentiment,
                    signal.review_count,
                    signal.confidence_score
                )
            )
            logger.info("Successfully saved culture signal.")
        except Exception as e:
            logger.error(f"Failed to save culture signal: {e}")

    async def run_pipeline(self, ticker: str, glassdoor_id: str = None, limit: int = 20):
        # Resolve ID first
        if not glassdoor_id:
            glassdoor_id = COMPANY_IDS.get(ticker)
            
        if not glassdoor_id:
            logger.error(f"Cannot run pipeline for {ticker}: No Glassdoor ID found.")
            return

        # 0. Check S3 for existing data for today
        date_str = datetime.now().strftime("%Y-%m-%d")
        s3_key = f"raw/glassdoor/{ticker}/{date_str}.json"
        
        raw_reviews = None
        if aws_service.file_exists(s3_key):
            logger.info(f"Found existing raw data for {ticker} in S3: {s3_key}")
            raw_reviews = aws_service.read_json(s3_key)

        if not raw_reviews:
            # 1. Fetch
            # Pass resolved glassdoor_id
            raw_reviews = await self.fetch_reviews(ticker, glassdoor_id=glassdoor_id, limit=limit)
            if not raw_reviews:
                logger.info(f"No reviews found for {ticker}")
                return
                
            # 2. S3
            await self.save_raw_to_s3(ticker, raw_reviews)
        else:
            logger.info(f"Using {len(raw_reviews)} reviews from S3 cache.")
        
        # 3. Parse
        parsed_reviews = [
            self.parse_review(r, ticker, glassdoor_id) 
            for r in raw_reviews
        ]
        
        # 4. Snowflake
        await self.save_reviews_to_snowflake(parsed_reviews)
        
        # 5. Analyze
        signal = self.analyze_reviews(parsed_reviews)
        logger.info(f"Culture Signal for {ticker}: {signal}")
        
        # 6. Persist Culture Signal
        await self.save_culture_signal(signal)

    async def run_batch(self, companies: List[Dict[str, str]], limit: int = 20):
        """
        Run pipeline for multiple companies.
        Expects a list of dicts: [{"ticker": "NVDA", "id": "7633"}, ...]
        """
        logger.info(f"Starting batch run for {len(companies)} companies...")
        for comp in companies:
            ticker = comp.get("ticker")
            gid = comp.get("id")
            if ticker:
                await self.run_pipeline(ticker, glassdoor_id=gid, limit=limit)
