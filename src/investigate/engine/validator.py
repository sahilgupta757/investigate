import re
import math
from investigate.engine.enrichment import FactsPayload

class HallucinationError(Exception):
    pass

def extract_valid_numbers(obj) -> set:
    numbers = set()
    if isinstance(obj, dict):
        for v in obj.values():
            numbers.update(extract_valid_numbers(v))
    elif isinstance(obj, list):
        for item in obj:
            numbers.update(extract_valid_numbers(item))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.add(float(obj))
    return numbers

def validate_grounding(review_json: str, facts: FactsPayload) -> None:
    extracted_strings = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', review_json)
    valid_numbers = extract_valid_numbers(facts.model_dump())
    
    for s in extracted_strings:
        try:
            val = float(s)
        except ValueError:
            continue
            
        matched = False
        for valid in valid_numbers:
            if math.isclose(val, valid, rel_tol=1e-2):
                matched = True
                break
        
        if not matched:
            raise HallucinationError(f"Hallucination caught: The number {val} is not present in the facts payload.")
