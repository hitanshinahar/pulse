import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import openai

class LLMDiagnosis(BaseModel):
    failure_category: str = Field(..., description="The categorized reason for failure (e.g. insufficient_funds, authentication_failed).")
    diagnostic_confidence: float = Field(..., description="Confidence score between 0.0 and 1.0.")
    evidence: List[str] = Field(..., description="List of evidence points extracted strictly from the provided context.")
    uncertainty: bool = Field(..., description="Set to true if evidence is insufficient to make a firm diagnosis.")

def get_openai_client():
    # Use standard env variables (OPENAI_API_KEY)
    # Can also be overridden to point to a local proxy or other provider that supports OpenAI schema
    api_key = os.environ.get("OPENAI_API_KEY", "dummy-key-for-tests")
    base_url = os.environ.get("OPENAI_BASE_URL") # e.g. for vLLM or LiteLLM
    return openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

async def diagnose_failure(context_dict: Dict[str, Any]) -> LLMDiagnosis:
    """Uses an LLM to generate a structured diagnosis of the failure."""
    
    prompt = f"""
    Analyze the following financial recovery context and diagnose the most likely cause of failure.
    Do NOT invent facts. Only use the provided context.
    
    Context:
    {json.dumps(context_dict, indent=2)}
    """
    
    client = get_openai_client()
    model = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")
    
    try:
        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial recovery diagnostic AI. Your output must be purely diagnostic and strictly follow the requested structure."},
                {"role": "user", "content": prompt}
            ],
            response_format=LLMDiagnosis,
        )
        diagnosis = response.choices[0].message.parsed
        return diagnosis
    except Exception as e:
        # Fallback to an explicit uncertainty state if API fails or parsing fails
        return LLMDiagnosis(
            failure_category="unknown",
            diagnostic_confidence=0.0,
            evidence=[f"LLM investigation failed: {str(e)}"],
            uncertainty=True
        )
