import pytest
from investigate.engine.validator import validate_grounding, HallucinationError
from investigate.engine.enrichment import FactsPayload, EnrichedHolding

def test_validate_grounding_success():
    facts = FactsPayload(
        total_value=100.5, 
        holdings_data={
            "A": EnrichedHolding(
                sector="Tech", 
                market_cap=50.0, 
                pe_ratio=15.2, 
                current_price=10.0, 
                allocation_percentage=100.0, 
                fifty_two_week_high=20.0, 
                fifty_two_week_low=5.0
            )
        }
    )
    review = '{"summary": "Total is 100.5 and PE is 15.2"}'
    validate_grounding(review, facts)  # Should not raise

def test_validate_grounding_hallucination():
    facts = FactsPayload(total_value=100.0, holdings_data={})
    review = '{"summary": "Total is 100.0 but I invented 42.5"}'
    with pytest.raises(HallucinationError):
        validate_grounding(review, facts)
