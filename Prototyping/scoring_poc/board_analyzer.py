import re
import httpx
import datetime
from decimal import Decimal
from typing import List, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass, field


@dataclass
class BoardMember:
    """A board member or executive."""
    name: str
    title: str
    bio: str
    is_independent: bool
    tenure_years: int
    committees: List[str] = field(default_factory=list)


@dataclass
class GovernanceSignal:
    """Board-derived governance signal."""
    company_id: str
    ticker: str

    # Boolean indicators
    has_tech_committee: bool
    has_ai_expertise: bool
    has_data_officer: bool
    has_risk_tech_oversight: bool
    has_ai_in_strategy: bool

    # Metrics
    tech_expertise_count: int
    independent_ratio: Decimal

    # Final score
    governance_score: Decimal
    confidence: Decimal

    # Evidence
    ai_experts: List[str] = field(default_factory=list)
    relevant_committees: List[str] = field(default_factory=list)

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