from decimal import Decimal
from typing import Dict


class VRCalculator:
    """Calculates Vertical Readiness (V^R) from dimension scores."""
    
    # Weights from Lab 5 specification
    DIMENSION_WEIGHTS = {
        "data_infrastructure": Decimal("0.15"),
        "ai_governance": Decimal("0.10"),
        "technology_stack": Decimal("0.20"),
        "talent": Decimal("0.20"),
        "leadership": Decimal("0.10"),
        "use_case_portfolio": Decimal("0.15"),
        "culture": Decimal("0.10"),
    }

    def calculate_vr(self, dimension_scores: Dict[str, Decimal]) -> Decimal:
        """
        Calculate V^R as weighted average of dimension scores.
        
        V^R = Σ(dimension_score × weight)
        
        Args:
            dimension_scores: Dict mapping dimension names to scores (0-100)
            
        Returns:
            V^R score (0-100)
        """
        vr = Decimal("0")
        
        for dim, weight in self.DIMENSION_WEIGHTS.items():
            score = dimension_scores.get(dim, Decimal("50.0"))
            vr += score * weight
        
        return round(vr, 2)


class HRCalculator:
    """Calculates Horizontal Readiness (H^R) from market position."""
    
    def __init__(self, alpha: Decimal = Decimal("0.15")):
        """
        Args:
            alpha: Scaling factor for position influence (default 0.15 from PDF)
        """
        self.alpha = alpha

    def calculate_hr(
        self, 
        hr_base: Decimal, 
        position_factor: Decimal
    ) -> Decimal:
        """
        Calculate H^R incorporating market position.
        
        H^R = H^R_base × (1 + α × PositionFactor)
        
        Args:
            hr_base: Base horizontal readiness (typically 70.0)
            position_factor: Market position factor (0.0 to 1.0)
            
        Returns:
            H^R score (0-100)
        """
        hr = hr_base * (Decimal("1") + self.alpha * position_factor)
        return round(hr, 2)


class SynergyCalculator:
    """Calculates final Synergy Score from V^R and H^R."""

    def calculate_synergy(
        self,
        vr_score: Decimal,
        hr_score: Decimal,
        alignment_factor: Decimal = Decimal("1.0"),
        timing_factor: Decimal = Decimal("1.0")
    ) -> Decimal:
        """
        Calculate Synergy Score.
        
        Synergy = (V^R × H^R / 100) × Alignment × Timing
        
        Args:
            vr_score: Vertical Readiness (0-100)
            hr_score: Horizontal Readiness (0-100)
            alignment_factor: Strategic alignment (0.0-1.0, default 1.0)
            timing_factor: Market timing (0.0-1.0, default 1.0)
            
        Returns:
            Synergy score (0-100)
        """
        base_synergy = (vr_score * hr_score) / Decimal("100")
        synergy = base_synergy * alignment_factor * timing_factor
        
        return round(synergy, 2)


class ConfidenceCalculator:
    """Calculates overall confidence from dimension confidences."""

    def calculate_overall_confidence(
        self, 
        dimension_confidences: list
    ) -> Decimal:
        """
        Calculate overall confidence as average of dimension confidences.
        
        Args:
            dimension_confidences: List of confidence values (0.0-1.0)
            
        Returns:
            Overall confidence (0.0-1.0)
        """
        if not dimension_confidences:
            return Decimal("0.0")
        
        total = sum(dimension_confidences)
        avg = total / len(dimension_confidences)
        
        return round(avg, 2)
