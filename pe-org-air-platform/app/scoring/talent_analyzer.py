from decimal import Decimal
from typing import Dict, List, Optional, Set
import math


class TalentConcentrationCalculator:
    """
    Calculate talent concentration (key-person risk).
    
    Talent Concentration (TC) measures how much AI capability depends on a few individuals:
    - TC = 0.0: Capability distributed across many people (low risk)
    - TC = 1.0: All capability in one person (maximum risk)
    
    Formula from Lab 5:
    TC = 0.4 × leadership_ratio + 
         0.3 × team_size_factor + 
         0.2 × skill_concentration + 
         0.1 × individual_mentions
    
    TalentRiskAdj = 1 - 0.15 × max(0, TC - 0.25)
    """
    
    SENIORITY_KEYWORDS = {
        "senior": ["principal", "staff", "director", "vp", "head", "chief"],
        "mid": ["senior", "lead", "manager"],
        "entry": ["junior", "associate", "entry", "intern"]
    }
    
    AI_ROLE_KEYWORDS = [
        "machine learning", "ml engineer", "data scientist", "ai engineer",
        "artificial intelligence", "deep learning", "nlp", "computer vision",
        "data science"
    ]

    def calculate_tc(
        self,
        job_postings: List[Dict],
        glassdoor_individual_mentions: int = 0,
        glassdoor_review_count: int = 1
    ) -> Decimal:
        """
        Calculate talent concentration ratio.
        
        Args:
            job_postings: List of job posting dicts with 'title', 'description'
            glassdoor_individual_mentions: Count of reviews mentioning specific people
            glassdoor_review_count: Total Glassdoor reviews
        
        Returns:
            Talent concentration in [0, 1]
        """
        if not job_postings:
            return Decimal("0.5")  # Neutral if no data
        
        # Analyze job postings
        job_analysis = self._analyze_job_postings(job_postings)
        
        # Component 1: Leadership ratio (40% weight)
        leadership_ratio = self._calculate_leadership_ratio(job_analysis)
        
        # Component 2: Team size factor (30% weight)
        team_size_factor = self._calculate_team_size_factor(job_analysis)
        
        # Component 3: Skill concentration (20% weight)
        skill_concentration = self._calculate_skill_concentration(job_analysis)
        
        # Component 4: Individual mentions (10% weight)
        individual_factor = self._calculate_individual_mention_factor(
            glassdoor_individual_mentions,
            glassdoor_review_count
        )
        
        # Weighted combination
        tc = (
            Decimal("0.4") * leadership_ratio +
            Decimal("0.3") * team_size_factor +
            Decimal("0.2") * skill_concentration +
            Decimal("0.1") * individual_factor
        )
        
        # Bound to [0, 1]
        tc = max(Decimal("0"), min(Decimal("1"), tc))
        
        return round(tc, 4)

    def calculate_talent_risk_adjustment(self, tc: Decimal) -> Decimal:
        """
        Calculate TalentRiskAdj factor for H^R formula.
        
        TalentRiskAdj = 1 - 0.15 × max(0, TC - 0.25)
        
        Returns:
            Adjustment factor (typically 0.85-1.0)
        """
        penalty = max(Decimal("0"), tc - Decimal("0.25"))
        adjustment = Decimal("1") - (Decimal("0.15") * penalty)
        return round(adjustment, 4)

    def _analyze_job_postings(self, job_postings: List[Dict]) -> Dict:
        """Categorize job postings by level and extract skills."""
        analysis = {
            "total_ai_jobs": 0,
            "senior_ai_jobs": 0,
            "mid_ai_jobs": 0,
            "entry_ai_jobs": 0,
            "unique_skills": set()
        }
        
        for job in job_postings:
            title = str(job.get("title", "")).lower()
            desc = str(job.get("description", "")).lower()
            
            # Check if AI-related
            if not any(kw in title or kw in desc for kw in self.AI_ROLE_KEYWORDS):
                continue
            
            analysis["total_ai_jobs"] += 1
            
            # Categorize by seniority (check in order: senior > mid > entry)
            if any(kw in title for kw in self.SENIORITY_KEYWORDS["senior"]):
                analysis["senior_ai_jobs"] += 1
            elif any(kw in title for kw in self.SENIORITY_KEYWORDS["mid"]):
                analysis["mid_ai_jobs"] += 1
            elif any(kw in title for kw in self.SENIORITY_KEYWORDS["entry"]):
                analysis["entry_ai_jobs"] += 1
            else:
                analysis["mid_ai_jobs"] += 1  # Default to mid
            
            # Extract skills (simplified: look for common tech keywords)
            skills = self._extract_skills(desc)
            analysis["unique_skills"].update(skills)
        
        return analysis

    def _extract_skills(self, description: str) -> Set[str]:
        """Extract technical skills from job description."""
        skill_keywords = [
            "python", "java", "scala", "r", "sql",
            "tensorflow", "pytorch", "keras", "scikit-learn",
            "spark", "hadoop", "kafka", "airflow",
            "aws", "azure", "gcp", "docker", "kubernetes"
        ]
        
        found_skills = set()
        desc_lower = description.lower()
        
        for skill in skill_keywords:
            if skill in desc_lower:
                found_skills.add(skill)
        
        return found_skills

    def _calculate_leadership_ratio(self, job_analysis: Dict) -> Decimal:
        """
        Calculate leadership ratio.
        
        leadership_ratio = senior_jobs / total_jobs
        
        High ratio = capability concentrated in leaders = high TC
        """
        total = job_analysis["total_ai_jobs"]
        if total == 0:
            return Decimal("0.5")  # Default if no data
        
        senior = job_analysis["senior_ai_jobs"]
        ratio = Decimal(senior) / Decimal(total)
        
        return ratio

    def _calculate_team_size_factor(self, job_analysis: Dict) -> Decimal:
        """
        Calculate team size factor.
        
        team_size_factor = min(1.0, 1.0 / (total_ai_jobs ** 0.5 + 0.1))
        
        Smaller teams = higher TC (more concentrated)
        """
        total = job_analysis["total_ai_jobs"]
        
        if total == 0:
            return Decimal("1.0")  # Maximum concentration if no team
        
        # Formula from PDF
        denominator = math.sqrt(total) + 0.1
        factor = min(1.0, 1.0 / denominator)
        
        return Decimal(str(round(factor, 4)))

    def _calculate_skill_concentration(self, job_analysis: Dict) -> Decimal:
        """
        Calculate skill concentration.
        
        skill_concentration = 1 - (unique_skills / 15) capped at [0,1]
        
        Fewer unique skills = higher concentration = higher TC
        """
        unique_skills = len(job_analysis["unique_skills"])
        
        # Normalize by 15 (reference number from PDF)
        concentration = 1.0 - (unique_skills / 15.0)
        concentration = max(0.0, min(1.0, concentration))
        
        return Decimal(str(round(concentration, 4)))

    def _calculate_individual_mention_factor(
        self,
        individual_mentions: int,
        total_reviews: int
    ) -> Decimal:
        """
        Calculate individual mention factor from Glassdoor.
        
        individual_factor = glassdoor_individual_mentions / glassdoor_review_count
        
        More mentions of specific people = higher TC
        
        TODO: Implement once Glassdoor collection is complete.
        This requires NLP to detect mentions of specific individuals in reviews.
        """
        if total_reviews == 0:
            return Decimal("0.5")  # Neutral if no reviews
        
        # Placeholder: return neutral until Glassdoor NLP is implemented
        return Decimal("0.5")
        
        # Future implementation:
        # ratio = individual_mentions / total_reviews
        # return Decimal(str(min(1.0, ratio)))
