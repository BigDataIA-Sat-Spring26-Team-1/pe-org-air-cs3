import unittest
from decimal import Decimal
from unittest.mock import patch, Mock, MagicMock
from board_analyzer import BoardCompositionAnalyzer, BoardMember, GovernanceSignal


class TestBoardCompositionAnalyzer(unittest.TestCase):
    """Comprehensive tests for BoardCompositionAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = BoardCompositionAnalyzer()

    def test_base_score_only(self):
        """Test that base score is 20 when no indicators are met."""
        signal = self.analyzer.analyze_board(
            company_id="test-123",
            ticker="TEST",
            members=[
                BoardMember(
                    name="John Doe",
                    title="Director",
                    bio="General business experience",
                    is_independent=False,
                    tenure_years=5,
                    committees=[]
                )
            ],
            committees=[],
            strategy_text=""
        )

        self.assertEqual(signal.governance_score, Decimal("20"))
        self.assertEqual(signal.company_id, "test-123")
        self.assertEqual(signal.ticker, "TEST")


    def test_tech_committee_scoring(self):
        """Test +15 points for technology committee."""
        test_cases = [
            ("Technology Committee", True),
            ("Digital Committee", True),
            ("Innovation Committee", True),
            ("IT Committee", True),
            ("Technology and Cybersecurity Committee", True),
            ("TECHNOLOGY COMMITTEE", True),
            ("Audit Committee", False),
            ("Compensation Committee", False),
        ]

        for committee_name, should_score in test_cases:
            with self.subTest(committee=committee_name):
                signal = self.analyzer.analyze_board(
                    company_id="test-123",
                    ticker="TEST",
                    members=[],
                    committees=[committee_name],
                    strategy_text=""
                )

                expected_score = Decimal("35") if should_score else Decimal("20")
                self.assertEqual(
                    signal.governance_score,
                    expected_score,
                    f"Committee '{committee_name}' should {'add' if should_score else 'not add'} points"
                )
                self.assertEqual(signal.has_tech_committee, should_score)