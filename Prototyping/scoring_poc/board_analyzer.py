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

    # AI expertise patterns
    AI_EXPERTISE_PATTERNS = [
        r'\bartificial\s+intelligence\b',
        r'\bmachine\s+learning\b',
        r'\bchief\s+data\s+officer\b',
        r'\bCDO\b',
        r'\bCAIO\b',
        r'\bchief\s+ai\b',
        r'\bchief\s+technology\b',
        r'\bCTO\b',
        r'\bchief\s+digital\b',
        r'\bdata\s+science\b',
        r'\banalytics\b',
        r'\bdigital\s+transformation\b',
    ]

    # Tech committee patterns
    TECH_COMMITTEE_PATTERNS = [
        r'\btechnology\s+committee\b',
        r'\btechnology\s+and\s+\w+\s+committee\b',
        r'\bdigital\s+(strategy\s+)?committee\b',
        r'\binnovation\s+committee\b',
        r'\bIT\s+committee\b',
        r'\btechnology\s+and\s+cybersecurity\b',
        r'\binformation\s+technology\s+committee\b',
    ]

    # Data officer patterns
    DATA_OFFICER_PATTERNS = [
        r'\bchief\s+data\s+officer\b',
        r'\bCDO\b',
        r'\bchief\s+ai\s+officer\b',
        r'\bCAIO\b',
        r'\bchief\s+analytics\s+officer\b',
        r'\bCAO\b',
        r'\bchief\s+digital\s+officer\b',
    ]

    # AI strategy patterns
    AI_STRATEGY_PATTERNS = [
        r'\bartificial\s+intelligence\b',
        r'\bmachine\s+learning\b',
        r'\bai\s+strategy\b',
        r'\bai\s+initiative',
        r'\bai\s+transformation\b',
        r'\bgenerative\s+ai\b',
        r'\bai\s+model'
    ]

    # Risk+tech patterns
    RISK_TECH_PATTERNS = [
        r'\btechnology\b',
        r'\bcyber(security)?\b',
        r'\bdigital\b',
        r'\bIT\b',
        r'\binformation\s+technology\b',
    ]

    SEC_API_KEY = "0c6b6b0df58cba77bb714d703df6468482e29b67b343728ce00048f3eac7390c"
    SEC_ENDPOINT = "https://api.sec-api.io/directors-and-board-members"

    def __init__(self):
        self.confidence = None