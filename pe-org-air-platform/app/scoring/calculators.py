from decimal import Decimal
from typing import Dict, List, Optional
import structlog
from .utils import weighted_mean, clamp, to_decimal, coefficient_of_variation, weighted_std_dev
from app.services.sector_config import sector_config

logger = structlog.get_logger(__name__)


class VRCalculator:
    """Calculates Vertical Readiness (V^R) from dimension scores with CV penalty."""

    def calculate_vr(self, dimension_scores: Dict[str, Decimal], sector: str = "default") -> Decimal:
        """
        Calculate V^R as weighted average of dimension scores, adjusted by CV penalty.
        
        V^R_base = Σ(dimension_score × weight)
        CV_penalty = 1 - 0.25 × CV(scores)
        V^R_final = V^R_base × CV_penalty
        """
        weights = sector_config.get_weights(sector)
        
        values = []
        w_list = []
        
        for dim, weight in weights.items():
            score = dimension_scores.get(dim, Decimal("50.0"))
            values.append(score)
            w_list.append(weight)
        
        # 1. Calculate Base VR (Weighted Mean)
        vr_base = weighted_mean(values, w_list)
        
        # 2. Calculate CV Penalty
        # Note: We use unweighted CV for consistency across dimensions
        mean_score = sum(values) / len(values) if values else Decimal("0")
        if mean_score > 0:
            std_dev = (sum((s - mean_score)**2 for s in values) / len(values)).sqrt()
            cv = std_dev / mean_score
        else:
            cv = Decimal("1.0")
            
        cv_penalty = Decimal("1.0") - (Decimal("0.25") * cv)
        vr_final = vr_base * cv_penalty
        vr_final = clamp(vr_final, Decimal("0"), Decimal("100"))
        
        # Audit Trail
        logger.info(
            "vr_calculated",
            vr_base=float(vr_base),
            cv=float(cv),
            cv_penalty=float(cv_penalty),
            vr_final=float(vr_final),
            sector=sector,
            dimension_breakdown={k: float(v) for k, v in dimension_scores.items()}
        )
        
        return to_decimal(float(vr_final), places=2)


class HRCalculator:
    """Calculates Horizontal Readiness (H^R) from market position."""
    
    def __init__(self, alpha: Decimal = Decimal("0.15")):
        self.alpha = alpha

    def calculate_hr(
        self, 
        hr_base: Decimal, 
        position_factor: Decimal
    ) -> Decimal:
        """
        Calculate H^R incorporating market position.
        H^R = H^R_base × (1 + α × PositionFactor)
        """
        hr = hr_base * (Decimal("1") + self.alpha * position_factor)
        hr = clamp(hr, Decimal("0"), Decimal("100"))
        
        logger.info(
            "hr_calculated",
            hr_base=float(hr_base),
            position_factor=float(position_factor),
            alpha=float(self.alpha),
            hr_final=float(hr)
        )
        
        return to_decimal(float(hr), places=2)


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
        """
        base_synergy = (vr_score * hr_score) / Decimal("100")
        synergy = base_synergy * alignment_factor * timing_factor
        synergy = clamp(synergy, Decimal("0"), Decimal("100"))
        
        logger.info(
            "synergy_calculated",
            vr_score=float(vr_score),
            hr_score=float(hr_score),
            alignment=float(alignment_factor),
            timing=float(timing_factor),
            synergy_final=float(synergy)
        )
        
        return to_decimal(float(synergy), places=2)


class ConfidenceCalculator:
    """Calculates overall confidence using SEM (Standard Error of Mean)."""

    def calculate_overall_confidence(
        self, 
        dimension_confidences: List[Decimal]
    ) -> Decimal:
        """
        Calculate overall confidence. 
        In V2, we incorporate SEM to penalize high variance in confidence.
        """
        if not dimension_confidences:
            return Decimal("0.0")
        
        n = len(dimension_confidences)
        mean_conf = sum(dimension_confidences) / n
        
        if n > 1:
            variance = sum((c - mean_conf)**2 for c in dimension_confidences) / (n - 1)
            sem = variance.sqrt() / Decimal(str(n)).sqrt()
            # Penalty for low consensus
            confidence = mean_conf * (Decimal("1.0") - sem)
        else:
            confidence = mean_conf
            
        confidence = clamp(confidence, Decimal("0"), Decimal("1"))
        
        return to_decimal(float(confidence), places=2)


class OrgAIRCalculator:
    """Final aggregator for the PE Org-AI-R System (Lab 6)."""

    def __init__(self):
        self.vr_calc = VRCalculator()
        self.hr_calc = HRCalculator()
        self.synergy_calc = SynergyCalculator()
        self.conf_calc = ConfidenceCalculator()

    def calculate_org_air(
        self,
        dimension_scores: Dict[str, Decimal],
        dimension_confidences: List[Decimal],
        position_factor: Decimal,
        hr_base: Decimal = Decimal("70.0"),
        sector: str = "default",
        alignment: Decimal = Decimal("1.0"),
        timing: Decimal = Decimal("1.0"),
        company_id: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Orchestrate the full calculation flow with complete audit trail.
        """
        # Bind context for all logs in this flow
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            company_id=company_id,
            assessment_id=assessment_id,
            sector=sector
        )
        
        # 1. Vertical Readiness
        vr_score = self.vr_calc.calculate_vr(dimension_scores, sector=sector)
        
        # 2. Horizontal Readiness
        hr_score = self.hr_calc.calculate_hr(hr_base, position_factor)
        
        # 3. Synergy Score
        synergy_score = self.synergy_calc.calculate_synergy(
            vr_score, hr_score, alignment_factor=alignment, timing_factor=timing
        )
        
        # 4. Confidence (CI)
        confidence = self.conf_calc.calculate_overall_confidence(dimension_confidences)
        
        import uuid
        audit_id = str(uuid.uuid4())
        
        result = {
            "org_air_score": float(synergy_score),
            "v_r": float(vr_score),
            "h_r": float(hr_score),
            "confidence": float(confidence),
            "audit_log_id": audit_id
        }
        
        logger.info(
            "org_air_calculation_complete",
            company_score=result["org_air_score"],
            components={
                "V_R": result["v_r"],
                "H_R": result["h_r"]
            },
            confidence=result["confidence"],
            evidence_n=len(dimension_confidences),
            audit_id=audit_id
        )
        
        return result
