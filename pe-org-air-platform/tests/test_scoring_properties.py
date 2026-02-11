"""
Property-based tests for scoring engine.

These tests verify invariant properties that should hold for ALL valid inputs,
using Hypothesis to generate 500 random test cases per property.
"""
import pytest
from hypothesis import given, strategies as st, settings
from decimal import Decimal
from typing import Dict

from app.scoring import (
    VRCalculator,
    HRCalculator,
    SynergyCalculator,
    ConfidenceCalculator,
    EvidenceMapper,
    PositionFactorCalculator,
    TalentConcentrationCalculator
)
from app.models.scoring import Dimension, SignalSource, EvidenceScore


# Hypothesis strategies for generating test data
@st.composite
def dimension_scores(draw):
    """Generate valid dimension scores (0-100)."""
    return {
        "data_infrastructure": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "ai_governance": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "technology_stack": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "talent": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "leadership": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "use_case_portfolio": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
        "culture": Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
    }


@st.composite
def evidence_scores_list(draw, min_size=0, max_size=10):
    """Generate a list of EvidenceScore objects."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    sources = draw(st.lists(
        st.sampled_from(list(SignalSource)),
        min_size=size,
        max_size=size,
        unique=True
    ))
    
    return [
        EvidenceScore(
            source=source,
            raw_score=Decimal(str(draw(st.floats(min_value=0, max_value=100)))),
            confidence=Decimal(str(draw(st.floats(min_value=0, max_value=1)))),
            evidence_count=draw(st.integers(min_value=1, max_value=100)),
            metadata={}
        )
        for source in sources
    ]


# =============================================================================
# V^R CALCULATOR PROPERTY TESTS
# =============================================================================

class TestVRCalculatorProperties:
    """Property-based tests for VRCalculator."""
    
    @settings(max_examples=500)
    @given(dimension_scores())
    def test_vr_always_bounded(self, scores: Dict[str, Decimal]):
        """Property: 0 ≤ V^R ≤ 100 for all valid inputs."""
        calculator = VRCalculator()
        vr = calculator.calculate_vr(scores)
        
        assert Decimal("0") <= vr <= Decimal("100"), \
            f"V^R {vr} is outside bounds [0, 100]"
    
    @settings(max_examples=500)
    @given(dimension_scores())
    def test_higher_scores_increase_vr(self, scores: Dict[str, Decimal]):
        """Property: Increasing all dimension scores increases V^R (monotonicity)."""
        calculator = VRCalculator()
        
        vr_original = calculator.calculate_vr(scores)
        
        # Increase all scores by 10
        increased_scores = {
            dim: min(Decimal("100"), score + Decimal("10"))
            for dim, score in scores.items()
        }
        vr_increased = calculator.calculate_vr(increased_scores)
        
        assert vr_increased >= vr_original, \
            f"V^R decreased when scores increased: {vr_original} -> {vr_increased}"
    
    @settings(max_examples=500)
    @given(st.floats(min_value=50, max_value=50))
    def test_uniform_dimensions_no_cv_penalty(self, uniform_score: float):
        """Property: Uniform scores across all dimensions should have no CV penalty."""
        calculator = VRCalculator()
        
        # All dimensions have the same score
        scores = {
            dim: Decimal(str(uniform_score))
            for dim in [
                "data_infrastructure", "ai_governance", "technology_stack",
                "talent", "leadership", "use_case_portfolio", "culture"
            ]
        }
        
        vr = calculator.calculate_vr(scores)
        
        # With uniform scores, V^R should equal the uniform score
        # (weighted average of identical values = that value)
        assert abs(float(vr) - uniform_score) < 0.1, \
            f"V^R {vr} != uniform score {uniform_score} (CV penalty applied incorrectly)"
    
    @settings(max_examples=500)
    @given(dimension_scores())
    def test_deterministic(self, scores: Dict[str, Decimal]):
        """Property: Same inputs produce identical outputs (determinism)."""
        calculator = VRCalculator()
        
        vr1 = calculator.calculate_vr(scores)
        vr2 = calculator.calculate_vr(scores)
        
        assert vr1 == vr2, \
            f"Non-deterministic behavior: {vr1} != {vr2}"


# =============================================================================
# EVIDENCE MAPPER PROPERTY TESTS
# =============================================================================

class TestEvidenceMapperProperties:
    """Property-based tests for EvidenceMapper."""
    
    @settings(max_examples=500)
    @given(evidence_scores_list(min_size=0, max_size=10))
    def test_all_dimensions_returned(self, evidence_scores):
        """Property: Mapper always returns exactly 7 dimensions."""
        mapper = EvidenceMapper()
        result = mapper.map_evidence_to_dimensions(evidence_scores)
        
        assert len(result) == 7, \
            f"Expected 7 dimensions, got {len(result)}"
        
        expected_dims = set(Dimension)
        actual_dims = set(result.keys())
        
        assert expected_dims == actual_dims, \
            f"Missing dimensions: {expected_dims - actual_dims}"
    
    @settings(max_examples=500)
    @given(st.sampled_from(list(Dimension)))
    def test_missing_evidence_defaults_to_50(self, excluded_dimension: Dimension):
        """Property: Dimensions with no evidence default to score = 50."""
        mapper = EvidenceMapper()
        
        # Create evidence for all dimensions EXCEPT one
        evidence_scores = []
        for source, mapping in mapper.mappings.items():
            # Skip sources that contribute to the excluded dimension
            if mapping.primary_dimension == excluded_dimension:
                continue
            if excluded_dimension in mapping.secondary_mappings:
                continue
            
            evidence_scores.append(
                EvidenceScore(
                    source=source,
                    raw_score=Decimal("75.0"),
                    confidence=Decimal("0.9"),
                    evidence_count=10,
                    metadata={}
                )
            )
        
        result = mapper.map_evidence_to_dimensions(evidence_scores)
        
        # The excluded dimension should have score = 50 (default)
        if excluded_dimension in result:
            score = result[excluded_dimension].score
            # Allow some tolerance due to potential indirect contributions
            if result[excluded_dimension].total_weight == Decimal("0.0"):
                assert score == Decimal("50.0"), \
                    f"Dimension {excluded_dimension} with no evidence should default to 50, got {score}"
    
    @settings(max_examples=500)
    @given(
        st.lists(
            st.sampled_from(list(SignalSource)),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_more_evidence_higher_confidence(self, sources):
        """Property: More evidence sources should not decrease confidence."""
        mapper = EvidenceMapper()
        
        # Create evidence with subset of sources
        evidence_subset = [
            EvidenceScore(
                source=sources[0],
                raw_score=Decimal("70.0"),
                confidence=Decimal("0.8"),
                evidence_count=10,
                metadata={}
            )
        ]
        
        # Create evidence with all sources
        evidence_full = [
            EvidenceScore(
                source=source,
                raw_score=Decimal("70.0"),
                confidence=Decimal("0.8"),
                evidence_count=10,
                metadata={}
            )
            for source in sources
        ]
        
        result_subset = mapper.map_evidence_to_dimensions(evidence_subset)
        result_full = mapper.map_evidence_to_dimensions(evidence_full)
        
        # For each dimension, confidence should not decrease with more evidence
        for dim in Dimension:
            conf_subset = result_subset[dim].confidence
            conf_full = result_full[dim].confidence
            
            assert conf_full >= conf_subset, \
                f"Confidence decreased for {dim}: {conf_subset} -> {conf_full}"


# =============================================================================
# H^R CALCULATOR PROPERTY TESTS
# =============================================================================

class TestHRCalculatorProperties:
    """Property-based tests for HRCalculator."""
    
    @settings(max_examples=500)
    @given(
        st.floats(min_value=0, max_value=100),
        st.floats(min_value=-1, max_value=1)
    )
    def test_hr_always_bounded(self, hr_base: float, position_factor: float):
        """Property: 0 ≤ H^R ≤ 100 for all valid inputs."""
        calculator = HRCalculator()
        hr = calculator.calculate_hr(
            Decimal(str(hr_base)),
            Decimal(str(position_factor))
        )
        
        assert Decimal("0") <= hr <= Decimal("100"), \
            f"H^R {hr} is outside bounds [0, 100]"
    
    @settings(max_examples=500)
    @given(st.floats(min_value=50, max_value=90))
    def test_positive_position_increases_hr(self, hr_base: float):
        """Property: Positive position factor increases H^R."""
        calculator = HRCalculator()
        
        hr_neutral = calculator.calculate_hr(Decimal(str(hr_base)), Decimal("0.0"))
        hr_positive = calculator.calculate_hr(Decimal(str(hr_base)), Decimal("0.5"))
        
        assert hr_positive > hr_neutral, \
            f"Positive position factor should increase H^R: {hr_neutral} -> {hr_positive}"


# =============================================================================
# SYNERGY CALCULATOR PROPERTY TESTS
# =============================================================================

class TestSynergyCalculatorProperties:
    """Property-based tests for SynergyCalculator."""
    
    @settings(max_examples=500)
    @given(
        st.floats(min_value=0, max_value=100),
        st.floats(min_value=0, max_value=100)
    )
    def test_synergy_always_bounded(self, vr: float, hr: float):
        """Property: 0 ≤ Synergy ≤ 100 for all valid inputs."""
        calculator = SynergyCalculator()
        synergy = calculator.calculate_synergy(
            Decimal(str(vr)),
            Decimal(str(hr))
        )
        
        assert Decimal("0") <= synergy <= Decimal("100"), \
            f"Synergy {synergy} is outside bounds [0, 100]"
    
    @settings(max_examples=500)
    @given(
        st.floats(min_value=50, max_value=100),
        st.floats(min_value=50, max_value=100)
    )
    def test_higher_vr_hr_increases_synergy(self, vr: float, hr: float):
        """Property: Higher V^R and H^R increase Synergy (monotonicity)."""
        calculator = SynergyCalculator()
        
        synergy_base = calculator.calculate_synergy(
            Decimal(str(vr)),
            Decimal(str(hr))
        )
        
        synergy_increased = calculator.calculate_synergy(
            Decimal(str(min(100, vr + 10))),
            Decimal(str(min(100, hr + 10)))
        )
        
        assert synergy_increased >= synergy_base, \
            f"Synergy decreased when V^R and H^R increased: {synergy_base} -> {synergy_increased}"


# =============================================================================
# TALENT CONCENTRATION PROPERTY TESTS
# =============================================================================

class TestTalentConcentrationProperties:
    """Property-based tests for TalentConcentrationCalculator."""
    
    @settings(max_examples=500)
    @given(st.lists(st.dictionaries(
        keys=st.sampled_from(["title", "description"]),
        values=st.text(min_size=10, max_size=100)
    ), min_size=0, max_size=50))
    def test_tc_always_bounded(self, job_postings):
        """Property: 0 ≤ TC ≤ 1 for all valid inputs."""
        calculator = TalentConcentrationCalculator()
        tc = calculator.calculate_tc(job_postings)
        
        assert Decimal("0") <= tc <= Decimal("1"), \
            f"TC {tc} is outside bounds [0, 1]"
    
    @settings(max_examples=500)
    @given(st.floats(min_value=0, max_value=1))
    def test_talent_risk_adj_bounded(self, tc: float):
        """Property: 0.85 ≤ TalentRiskAdj ≤ 1.0 for all valid TC."""
        calculator = TalentConcentrationCalculator()
        adj = calculator.calculate_talent_risk_adjustment(Decimal(str(tc)))
        
        # TalentRiskAdj = 1 - 0.15 × max(0, TC - 0.25)
        # Min: 1 - 0.15 × (1 - 0.25) = 0.8875
        # Max: 1.0 (when TC ≤ 0.25)
        assert Decimal("0.85") <= adj <= Decimal("1.0"), \
            f"TalentRiskAdj {adj} is outside expected bounds [0.85, 1.0]"


# =============================================================================
# POSITION FACTOR PROPERTY TESTS
# =============================================================================

class TestPositionFactorProperties:
    """Property-based tests for PositionFactorCalculator."""
    
    @settings(max_examples=500)
    @given(
        st.floats(min_value=0, max_value=100),
        st.sampled_from(["technology", "financial_services", "healthcare", "retail"]),
        st.floats(min_value=0, max_value=1)
    )
    def test_position_factor_bounded(self, vr_score: float, sector: str, percentile: float):
        """Property: -1 ≤ PositionFactor ≤ 1 for all valid inputs."""
        calculator = PositionFactorCalculator()
        pf = calculator.calculate_position_factor(vr_score, sector, percentile)
        
        assert Decimal("-1") <= pf <= Decimal("1"), \
            f"PositionFactor {pf} is outside bounds [-1, 1]"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
