import pytest
from investigate.engine.prompts import generate_fast_pass, PortfolioReview
from investigate.engine.enrichment import FactsPayload, EnrichedHolding

def test_generate_fast_pass(mocker):
    facts = FactsPayload(
        total_value=100.0, 
        holdings_data={"AAPL": EnrichedHolding()}
    )
    
    mock_client = mocker.patch("openai.OpenAI")
    mock_choice = mocker.MagicMock()
    mock_choice.message.content = '{"summary": "Good", "strengths": [], "concentration_risks": [], "valuation_anomalies": []}'
    mock_client.return_value.chat.completions.create.return_value.choices = [mock_choice]
    
    mocker.patch("investigate.engine.prompts.validate_grounding")
    
    review = generate_fast_pass(facts, "dummy_key")
    assert review.summary == "Good"
