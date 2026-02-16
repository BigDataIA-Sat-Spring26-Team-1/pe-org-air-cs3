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


        def test_nvidia_leader(self):
        """Test NVIDIA as industry leader - high PF expected."""
        pf = self.calc.calculate_position_factor(
            vr_score=92.0,
            sector='technology',
            market_cap_percentile=0.95,
        )
        self.assertGreater(float(pf), 0.6)
        self.assertLess(float(pf), 1.0)

    def test_average_position(self):
        """Test company with average position - PF should be near 0."""
        pf = self.calc.calculate_position_factor(
            vr_score=45.0,
            sector='manufacturing',
            market_cap_percentile=0.5,
        )
        self.assertAlmostEqual(float(pf), 0.0, places=2)

    def test_laggard_position(self):
        """Test company lagging in sector - negative PF expected."""
        pf = self.calc.calculate_position_factor(
            vr_score=35.0,
            sector='retail',
            market_cap_percentile=0.2
        )
        self.assertLess(float(pf), 0.0)
        self.assertGreater(float(pf), -1.0)

        def test_upper_bound(self):
        """Test that PF is bounded to maximum of 1.0."""
        pf = self.calc.calculate_position_factor(
            vr_score=100.0,
            sector='technology',
            market_cap_percentile=1.0,
        )
        self.assertLessEqual(float(pf), 1.0)

    def test_lower_bound(self):
        """Test that PF is bounded to minimum of -1.0."""
        pf = self.calc.calculate_position_factor(
            vr_score=0.0,
            sector='technology',
            market_cap_percentile=0.0,
        )
        self.assertGreaterEqual(float(pf), -1.0)

    def test_vr_component_clamping_high(self):
        """Test that VR component is properly clamped at 1.0."""
        pf = self.calc.calculate_position_factor(
            vr_score=150.0,
            sector='technology',
            market_cap_percentile=0.5,
        )
        self.assertAlmostEqual(float(pf), 0.6, places=2)

    def test_vr_component_clamping_low(self):
        """Test that VR component is properly clamped at -1.0."""
        pf = self.calc.calculate_position_factor(
            vr_score=-50.0,
            sector='technology',
            market_cap_percentile=0.5,
        )
        self.assertAlmostEqual(float(pf), -0.6, places=2)

        def test_different_sectors(self):
        """Test calculation works correctly for different sectors."""
        sectors_to_test = [
            'technology',
            'financial_services',
            'healthcare',
            'retail',
            'manufacturing'
        ]

        for sector in sectors_to_test:
            pf = self.calc.calculate_position_factor(
                vr_score=60.0,
                sector=sector,
                market_cap_percentile=0.6
            )
            self.assertIsInstance(pf, Decimal)
            self.assertGreaterEqual(float(pf), -1.0)
            self.assertLessEqual(float(pf), 1.0)

    def test_unknown_sector_default(self):
        """Test that unknown sectors use default average of 50.0."""
        pf = self.calc.calculate_position_factor(
            vr_score=60.0,
            sector='unknown_sector',
            market_cap_percentile=0.5
        )
        self.assertAlmostEqual(float(pf), 0.12, places=2)

    def test_return_type(self):
        """Test that return type is Decimal."""
        pf = self.calc.calculate_position_factor(
            vr_score=70.0,
            sector='technology',
            market_cap_percentile=0.7
        )
        self.assertIsInstance(pf, Decimal)

    def test_precision(self):
        """Test that results are rounded to 2 decimal places."""
        pf = self.calc.calculate_position_factor(
            vr_score=73.333,
            sector='technology',
            market_cap_percentile=0.777
        )
        pf_str = str(pf)
        if '.' in pf_str:
            decimal_places = len(pf_str.split('.')[1])
            self.assertLessEqual(decimal_places, 2)