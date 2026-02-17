import unittest
from board_analyzer import BoardCompositionAnalyzer, BoardMember
from decimal import Decimal


class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.analyzer = BoardCompositionAnalyzer()

    def test_fetch_apple_board_data(self):
        members, committees = self.analyzer.fetch_board_data("AAPL")

        self.assertGreater(len(members), 0, "Apple should have board members")

        if len(members) > 0:
            first_member = members[0]
            self.assertIsInstance(first_member, BoardMember)
            self.assertIsInstance(first_member.name, str)
            self.assertIsInstance(first_member.title, str)
            self.assertIsInstance(first_member.is_independent, bool)
            self.assertIsInstance(first_member.tenure_years, int)
            self.assertIsInstance(first_member.committees, list)

            print(f"\n[PASS] Found {len(members)} board members for AAPL")
            print(f"Example: {first_member.name} - {first_member.title}")

        self.assertGreater(len(committees), 0, "Apple should have committees")
        print(f"[PASS] Found {len(committees)} committees: {committees}")

    def test_fetch_microsoft_board_data(self):
        """Test fetching real board data for Microsoft (MSFT)."""
        members, committees = self.analyzer.fetch_board_data("MSFT")

        self.assertGreater(len(members), 0, "Microsoft should have board members")
        self.assertGreater(len(committees), 0, "Microsoft should have committees")

        print(f"\n[PASS] Found {len(members)} board members for MSFT")
        print(f"[PASS] Found {len(committees)} committees")


class TestAPIQuickCheck(unittest.TestCase):
    def test_api_connectivity(self):
        analyzer = BoardCompositionAnalyzer()

        print("\n" + "="*60)
        print("TESTING API CONNECTIVITY")
        print("="*60)

        members, committees = analyzer.fetch_board_data("AAPL")

        if len(members) > 0:
            print("[PASS] API connection successful!")
            print(f"[PASS] Retrieved {len(members)} board members")
            print(f"[PASS] Retrieved {len(committees)} committees")
            self.assertTrue(True)

        else:
            print("[FAIL] API call succeeded but returned no data")
            print("This could mean:")
            print("- Invalid API key")
            print("- Rate limit exceeded")
            print("- API endpoint changed")
            self.fail("API returned no data for AAPL")