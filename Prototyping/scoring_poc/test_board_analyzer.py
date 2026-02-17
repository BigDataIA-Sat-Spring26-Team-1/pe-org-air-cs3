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