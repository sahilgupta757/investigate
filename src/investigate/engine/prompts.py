from pydantic import BaseModel, Field
import openai
import json
from investigate.engine.enrichment import FactsPayload
from investigate.engine.validator import validate_grounding

class PortfolioReview(BaseModel):
    summary: str = Field(description="High level summary of the portfolio health")
    strengths: list[str] = Field(description="List of portfolio strengths")
    concentration_risks: list[str] = Field(description="Any concentration risks identified")
    valuation_anomalies: list[str] = Field(description="Any valuation anomalies like extremely high or negative P/E")

SYSTEM_INSTRUCTION = """
You are a senior equity analyst evaluating a portfolio. 
You will receive a JSON payload containing the portfolio's facts (holdings, sectors, P/E ratios, market caps).
Analyze this data and return a JSON object matching the requested schema.

CRITICAL RULES:
1. Handle `null` values gracefully. Not all stocks will have full data.
2. DO NOT output any numeric values with formatting suffixes (like "B", "M", "K"). Output the raw numbers exactly as they appear in the payload (e.g. 1500000000 instead of 1.5B) so our numeric validator can verify them.
3. You are strictly forbidden from doing arithmetic. Use only the exact numbers provided in the payload.
"""

def generate_fast_pass(facts: FactsPayload, api_key: str) -> PortfolioReview:
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    # Empty portfolio handling
    if facts.total_value <= 0 or not facts.holdings_data:
        return PortfolioReview(
            summary="Portfolio is empty.",
            strengths=[],
            concentration_risks=[],
            valuation_anomalies=[]
        )
        
    facts_json = facts.model_dump_json()

    response = client.chat.completions.create(
        model="google/gemini-2.5-flash",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": f"Analyze this portfolio: {facts_json}"}
        ]
    )

    content = response.choices[0].message.content
    if content is None:
        content = "{}"

    # Hard gate validation
    validate_grounding(content, facts)

    return PortfolioReview.model_validate_json(content)
