from decimal import Decimal


class PositionFactorCalculator:
    """Calculates market position factor based on market capitalization."""
    
    THRESHOLDS = {
        "mega_cap": Decimal("200_000_000_000"),      # $200B+
        "large_cap": Decimal("10_000_000_000"),      # $10B-$200B
        "mid_cap": Decimal("2_000_000_000"),         # $2B-$10B
        "small_cap": Decimal("300_000_000"),         # $300M-$2B
    }

    def calculate_position_factor(self, market_cap_usd: Decimal) -> Decimal:
        """
        Calculate position factor (0.0 to 1.0) based on market cap.
        
        Mega Cap (>$200B): 0.90 + scaled bonus up to 1.0
        Large Cap ($10B-$200B): 0.70-0.90 linear
        Mid Cap ($2B-$10B): 0.50-0.70 linear
        Small Cap ($300M-$2B): 0.30-0.50 linear
        Emerging (<$300M): 0.0-0.30 linear
        """
        if market_cap_usd >= self.THRESHOLDS["mega_cap"]:
            # Mega cap: 0.90 base + up to 0.10 bonus
            bonus = min(Decimal("1.0"), market_cap_usd / Decimal("3_000_000_000_000"))
            return Decimal("0.90") + (bonus * Decimal("0.10"))
        
        elif market_cap_usd >= self.THRESHOLDS["large_cap"]:
            # Large cap: linear 0.70 to 0.90
            range_size = self.THRESHOLDS["mega_cap"] - self.THRESHOLDS["large_cap"]
            position = (market_cap_usd - self.THRESHOLDS["large_cap"]) / range_size
            return Decimal("0.70") + (position * Decimal("0.20"))
        
        elif market_cap_usd >= self.THRESHOLDS["mid_cap"]:
            # Mid cap: linear 0.50 to 0.70
            range_size = self.THRESHOLDS["large_cap"] - self.THRESHOLDS["mid_cap"]
            position = (market_cap_usd - self.THRESHOLDS["mid_cap"]) / range_size
            return Decimal("0.50") + (position * Decimal("0.20"))
        
        elif market_cap_usd >= self.THRESHOLDS["small_cap"]:
            # Small cap: linear 0.30 to 0.50
            range_size = self.THRESHOLDS["mid_cap"] - self.THRESHOLDS["small_cap"]
            position = (market_cap_usd - self.THRESHOLDS["small_cap"]) / range_size
            return Decimal("0.30") + (position * Decimal("0.20"))
        
        else:
            # Emerging: linear 0.0 to 0.30
            position = min(Decimal("1.0"), market_cap_usd / self.THRESHOLDS["small_cap"])
            return position * Decimal("0.30")
