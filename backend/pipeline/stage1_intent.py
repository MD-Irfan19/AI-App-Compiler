import os
import json
import logging
from dotenv import load_dotenv
from validation.schemas import IntentSchema
from validation.repair import repair_layer
from pipeline.llm_client import call_model

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

INTENT_SYSTEM_PROMPT = """
You are Stage 1 of an app compiler pipeline.
Your ONLY job is to extract structured intent from a user's natural language app description.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- If the input is vague, make reasonable assumptions and document them in the "assumptions" field.
- If something is genuinely unclear, add it to "clarifications_needed".
- Never hallucinate features not implied by the prompt.
- Always include at least one role in user_roles.

Output this exact JSON structure:
{
  "app_name": "string",
  "app_type": "string",
  "description": "string",
  "core_features": [
    {
      "name": "string",
      "description": "string",
      "requires_auth": true,
      "roles_allowed": ["string"]
    }
  ],
  "user_roles": ["string"],
  "has_payments": false,
  "has_analytics": false,
  "has_notifications": false,
  "assumptions": ["string"],
  "clarifications_needed": ["string"]
}
"""

# ─────────────────────────────────────────────
# STAGE 1 RUNNER
# ─────────────────────────────────────────────

def run_stage1(user_prompt: str) -> IntentSchema:
    """
    Takes raw user prompt.
    Returns validated IntentSchema.
    """
    logger.info("Stage 1: Extracting intent...")

    full_prompt = f"{INTENT_SYSTEM_PROMPT}\n\nUser Input:\n{user_prompt}"

    raw_output = call_model(full_prompt)

    logger.debug(f"Stage 1 raw output: {raw_output}")

    # Repair + validate
    repaired_data, validation = repair_layer("intent", raw_output)

    if not validation.is_valid:
        logger.error(f"Stage 1 repair failed: {validation.errors}")
        raise ValueError(f"Stage 1 failed after repair: {validation.errors}")

    # Parse into Pydantic model
    intent = IntentSchema(**repaired_data)
    logger.info(f"Stage 1 complete: {intent.app_name} ({intent.app_type})")
    return intent


# ─────────────────────────────────────────────
# LOCAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    result = run_stage1(test_prompt)
    print(json.dumps(result.model_dump(), indent=2))