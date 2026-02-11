from decimal import Decimal
from typing import Dict, List, Optional


class TalentConcentrationCalculator:
    """
    Quantifies people risk based on:
    1. Seniority distribution in AI roles (top-heavy = risky)
    2. Glassdoor sentiment (negative reviews = retention risk)
    """
    
    SENIORITY_KEYWORDS = {
        "senior": ["senior", "principal", "staff", "lead", "director", "vp", "chief", "head of"],
        "mid": ["engineer", "scientist", "analyst", "developer", "specialist"],
        "junior": ["junior", "associate", "entry", "intern", "graduate"]
    }
    
    AI_ROLE_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist", "ai engineer",
        "artificial intelligence", "deep learning", "nlp", "computer vision"
    ]

    def calculate_people_risk(
        self, 
        job_postings: List[Dict],
        glassdoor_reviews: Optional[List[Dict]] = None
    ) -> Decimal:
        """
        Calculate people risk score (0.0 to 1.0).
        
        High score = high risk (top-heavy seniority, negative sentiment)
        Low score = low risk (healthy pyramid, positive sentiment)
        
        Returns:
            Decimal between 0.0 (low risk) and 1.0 (high risk)
        """
        if not job_postings:
            return Decimal("0.5")  # Neutral if no data
        
        # Component 1: Seniority Distribution Risk (70% weight)
        seniority_risk = self._calculate_seniority_risk(job_postings)
        
        # Component 2: Glassdoor Sentiment Risk (30% weight)
        sentiment_risk = self._calculate_sentiment_risk(glassdoor_reviews) if glassdoor_reviews else Decimal("0.5")
        
        # Weighted combination
        total_risk = (seniority_risk * Decimal("0.7")) + (sentiment_risk * Decimal("0.3"))
        
        return min(Decimal("1.0"), total_risk)

    def _calculate_seniority_risk(self, job_postings: List[Dict]) -> Decimal:
        """
        Analyze seniority distribution in AI-related job postings.
        
        Logic:
        - Filter for AI-related roles only
        - Classify each role by seniority level
        - Calculate risk based on pyramid shape:
          * Healthy: Many junior, fewer senior (low risk)
          * Top-heavy: Mostly senior roles (high risk - brain drain vulnerability)
        """
        ai_jobs = []
        for job in job_postings:
            title = str(job.get("title", "")).lower()
            desc = str(job.get("description", "")).lower()
            
            # Check if this is an AI-related role
            if any(kw in title or kw in desc for kw in self.AI_ROLE_KEYWORDS):
                ai_jobs.append(job)
        
        if not ai_jobs:
            return Decimal("0.5")  # Neutral if no AI roles found
        
        # Classify each AI job by seniority
        senior_count = 0
        mid_count = 0
        junior_count = 0
        
        for job in ai_jobs:
            title = str(job.get("title", "")).lower()
            
            # Check seniority level (order matters: check senior first)
            if any(kw in title for kw in self.SENIORITY_KEYWORDS["senior"]):
                senior_count += 1
            elif any(kw in title for kw in self.SENIORITY_KEYWORDS["junior"]):
                junior_count += 1
            else:
                # Default to mid-level if no clear seniority indicator
                mid_count += 1
        
        total = senior_count + mid_count + junior_count
        
        # Calculate risk based on senior ratio
        # High senior ratio = high risk (top-heavy, vulnerable to departures)
        senior_ratio = Decimal(senior_count) / Decimal(total)
        
        # Risk scoring:
        # 0-20% senior = 0.2 risk (healthy pyramid)
        # 20-40% senior = 0.4 risk (balanced)
        # 40-60% senior = 0.6 risk (slightly top-heavy)
        # 60%+ senior = 0.8-1.0 risk (very top-heavy, high vulnerability)
        
        if senior_ratio >= Decimal("0.6"):
            risk = Decimal("0.8") + (senior_ratio - Decimal("0.6")) * Decimal("0.5")
        elif senior_ratio >= Decimal("0.4"):
            risk = Decimal("0.6") + (senior_ratio - Decimal("0.4")) * Decimal("1.0")
        elif senior_ratio >= Decimal("0.2"):
            risk = Decimal("0.4") + (senior_ratio - Decimal("0.2")) * Decimal("1.0")
        else:
            risk = Decimal("0.2") + senior_ratio
        
        return min(Decimal("1.0"), risk)

    def _calculate_sentiment_risk(self, glassdoor_reviews: List[Dict]) -> Decimal:
        """
        Analyze Glassdoor review sentiment to assess retention risk.
        
        Logic:
        - Negative reviews = higher retention risk = higher people risk
        - Positive reviews = lower retention risk = lower people risk
        
        TODO: Implement once Glassdoor collection is complete
        Expected review structure:
        {
            "rating": 3.5,           # 1-5 scale
            "text": "...",
            "pros": "...",
            "cons": "...",
            "sentiment": "negative"  # or "positive", "neutral"
        }
        
        Implementation plan:
        1. Filter for AI/tech-related reviews (check if review mentions AI, ML, data, etc.)
        2. Calculate average rating for AI-related reviews
        3. Analyze sentiment of cons/negative reviews
        4. Map to risk score:
           - Avg rating 4.0+ = 0.2 risk (low retention risk)
           - Avg rating 3.0-4.0 = 0.5 risk (moderate)
           - Avg rating <3.0 = 0.8 risk (high retention risk)
        """
        if not glassdoor_reviews:
            return Decimal("0.5")  # Neutral if no reviews
        
        # Placeholder: Return neutral risk until Glassdoor collection is implemented
        # Once implemented, this will analyze review ratings and sentiment
        return Decimal("0.5")
        
        # Future implementation (uncomment when Glassdoor data is available):
        # total_rating = Decimal("0")
        # ai_review_count = 0
        # 
        # for review in glassdoor_reviews:
        #     text = str(review.get("text", "")).lower()
        #     
        #     # Check if review mentions AI/tech topics
        #     if any(kw in text for kw in self.AI_ROLE_KEYWORDS):
        #         rating = Decimal(str(review.get("rating", 3.0)))
        #         total_rating += rating
        #         ai_review_count += 1
        # 
        # if ai_review_count == 0:
        #     return Decimal("0.5")
        # 
        # avg_rating = total_rating / Decimal(ai_review_count)
        # 
        # # Map rating to risk (inverse relationship)
        # if avg_rating >= Decimal("4.0"):
        #     return Decimal("0.2")
        # elif avg_rating >= Decimal("3.0"):
        #     return Decimal("0.5")
        # else:
        #     return Decimal("0.8")
