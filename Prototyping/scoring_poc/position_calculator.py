from decimal import Decimal
from typing import Dict


class PositionFactorCalculator:
    """
    Calculate position factor for H^R.
    
    Formula: PF = 0.6 * VR_component + 0.4 * MCap_component
    
    Where:
    - VR_component = (vr_score - sector_avg_vr) / 50, clamped to [-1, 1]
    - MCap_component = (market_cap_percentile - 0.5) * 2
    
    Bounded to [-1, 1]
    """

    # Sector average V^R scores (from framework calibration data)
    SECTOR_AVG_VR: Dict[str, float] = {
        "technology": 65.0,
        "financial_services": 55.0,
        "healthcare": 52.0,
        "business_services": 50.0,
        "retail": 48.0,
        "manufacturing": 45.0,
    }