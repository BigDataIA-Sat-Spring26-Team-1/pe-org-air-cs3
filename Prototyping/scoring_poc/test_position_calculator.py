import unittest
from decimal import Decimal
from position_calculator import PositionFactorCalculator


class TestPositionFactorCalculator(unittest.TestCase):
    """Comprehensive tests for Position Factor calculations."""

    def setUp(self):
        self.calc = PositionFactorCalculator()

    def test_basic_calculation(self):
        """Test basic position factor calculation."""
        pf = self.calc.calculate_position_factor(
            vr_score=75.0,
            sector='technology',
            market_cap_percentile=0.75,
        )
        self.assertAlmostEqual(float(pf), 0.32, places=2)