from decimal import Decimal
import re
from typing import List, Tuple
from app.models.board import BoardMember, GovernanceSignal
from bs4 import BeautifulSoup


class BoardCompositionAnalyzer:
    """
    Analyze board composition for AI governance indicators.
    
    Scoring:
    - Tech committee exists: +15 points
    - AI expertise on board: +20 points
    - Data officer role: +15 points
    - Independent ratio > 0.5: +10 points
    - Risk committee tech oversight: +10 points
    - AI in strategic priorities: +10 points
    - Base: 20 points
    - Max: 100 points
    """

    BASE_SCORE = Decimal("20")
    MAX_SCORE = Decimal("100")

    # Scoring Weights
    SCORE_TECH_COMMITTEE = Decimal("15")
    SCORE_AI_EXPERTISE = Decimal("20")
    SCORE_DATA_OFFICER = Decimal("15")
    SCORE_INDEPENDENT_RATIO = Decimal("10")
    SCORE_RISK_OVERSIGHT = Decimal("10")
    SCORE_STRATEGIC_PRIORITY = Decimal("10")

    AI_EXPERTISE_KEYWORDS = [
        "artificial intelligence",
        "machine learning",
        "chief data officer",
        "cdo",
        "caio",
        "chief ai",
        "chief technology",
        "cto",
        "chief digital",
        "data science",
        "analytics",
        "digital transformation",
    ]

    TECH_COMMITTEE_NAMES = [
        "technology committee",
        "digital committee",
        "innovation committee",
        "it committee",
        "technology and cybersecurity"
    ]

    DATA_OFFICER_TITLES = [
        "chief data officer", "cdo",
        "chief ai officer", "caio",
        "chief analytics officer", "cao",
        "chief digital officer"
    ]

    AI_STRATEGY_KEYWORDS = [
        "artificial intelligence", "machine learning", "ai strategy",
        "ai initiative", "ai transformation", "generative ai", "ai model"
    ]

    RISK_TECH_KEYWORDS = [
        "technology",
        "cyber",
        "digital",
        "it"
    ]

    def __init__(self):
        self.confidence = None

    def analyze_board(
        self,
        company_id: str,
        ticker: str,
        members: List[BoardMember],
        committees: List[str],
        strategy_text: str = "",
    ) -> GovernanceSignal:
        """
        Analyze board for AI governance strength.
        
        Args:
            company_id: Company UUID
            ticker: Stock ticker
            members: List of board members and executives
            committees: List of committee names
            strategy_text: Text from annual report strategy section
        
        Returns:
            GovernanceSignal with governance score
        """
        score = self.BASE_SCORE

        # Check for tech committee
        relevant_committees = []
        has_tech = False
        for c in committees:
            if any(tc in c.lower() for tc in self.TECH_COMMITTEE_NAMES):
                has_tech = True
                relevant_committees.append(c)

        if has_tech:
            score += self.SCORE_TECH_COMMITTEE

        # Check for AI expertise on board
        ai_experts = []
        for member in members:
            bio_lower = member.bio.lower()
            title_lower = member.title.lower()

            if any(kw in bio_lower or kw in title_lower for kw in self.AI_EXPERTISE_KEYWORDS):
                ai_experts.append(member.name)

        has_ai_expertise = len(ai_experts) > 0
        if has_ai_expertise:
            score += self.SCORE_AI_EXPERTISE

        # Check for data officer role
        has_data_officer = False
        for member in members:
            title_lower = member.title.lower()
            bio_lower = member.bio.lower()

            if any(
                title in title_lower or title in bio_lower
                for title in self.DATA_OFFICER_TITLES
            ):
                has_data_officer = True
                break

        if has_data_officer:
            score += self.SCORE_DATA_OFFICER

        # Check independent ratio
        independent_count = sum(1 for member in members if member.is_independent)
        total_directors = len(members)

        independent_ratio = Decimal("0")
        if total_directors > 0:
            independent_ratio = Decimal(independent_count) / Decimal(total_directors)
            if independent_ratio > Decimal("0.5"):
                score += self.SCORE_INDEPENDENT_RATIO

        # Check risk committee oversight
        has_risk_tech_oversight = False
        for c in committees:
            c_lower = c.lower()
            if "risk" in c_lower and any(
                tech in c_lower
                for tech in self.RISK_TECH_KEYWORDS
            ):
                has_risk_tech_oversight = True
                if c not in relevant_committees:
                    relevant_committees.append(c)

        if has_risk_tech_oversight:
            score += self.SCORE_RISK_OVERSIGHT

        # Check AI in strategy
        has_ai_in_strategy = False
        if strategy_text:
            strategy_lower = strategy_text.lower()
            has_ai_in_strategy = any(kw in strategy_lower for kw in self.AI_STRATEGY_KEYWORDS)

            if has_ai_in_strategy:
                score += self.SCORE_STRATEGIC_PRIORITY

        # Cap at 100
        score = min(score, self.MAX_SCORE)

        # Calculate confidence based on data completeness
        data_points = 0
        total_possible = 6

        if committees:
            data_points += 1
        if members:
            data_points += 1
        if any(member.bio for member in members):
            data_points += 1
        if strategy_text:
            data_points += 1
        if total_directors > 0:
            data_points += 1
        if any(member.committees for member in members):
            data_points += 1
        
        confidence = min(
            Decimal("0.5") + Decimal(data_points) / Decimal(total_possible * 2),
            Decimal("0.95")
        )
        
        self.confidence = confidence
        
        return GovernanceSignal(
            company_id=company_id,
            ticker=ticker,
            has_tech_committee=has_tech,
            has_ai_expertise=has_ai_expertise,
            has_data_officer=has_data_officer,
            has_risk_tech_oversight=has_risk_tech_oversight,
            has_ai_in_strategy=has_ai_in_strategy,
            tech_expertise_count=len(ai_experts),
            independent_ratio=independent_ratio,
            governance_score=score,
            confidence=confidence,
            ai_experts=ai_experts,
            relevant_committees=relevant_committees
        )

