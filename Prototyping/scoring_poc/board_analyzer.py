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