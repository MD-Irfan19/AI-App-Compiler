import os
import json
import logging
from dotenv import load_dotenv
from pipeline.llm_client import call_model
from validation.schemas import IntentSchema, SystemDesignSchema
from validation.repair import repair_layer

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

DESIGN_SYSTEM_PROMPT = """
You are Stage 2 of an app compiler pipeline.
You receive structured intent and convert it into a system architecture design.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Define all entities the app needs (users, contacts, payments, etc.)
- Define all major app flows (login flow, payment flow, etc.)
- List external services only if genuinely needed (Stripe for payments, etc.)
- Every entity must have a name, description, list of fields, and relations.

Output this exact JSON structure:
{
  "entities": [
    {
      "name": "string",
      "description": "string",
      "fields": ["string"],
      "relations": ["string"]
    }
  ],
  "flows": [
    {
      "name": "string",
      "steps": ["string"],
      "roles_involved": ["string"]
    }
  ],
  "external_services": ["string"],
  "architecture_notes": ["string"]
}
"""

# ─────────────────────────────────────────────
# STAGE 2 RUNNER
# ─────────────────────────────────────────────

def run_stage2(intent: IntentSchema) -> SystemDesignSchema:
    """
    Takes IntentSchema from Stage 1.
    Returns validated SystemDesignSchema.
    """
    logger.info("Stage 2: Generating system design...")

    intent_json = json.dumps(intent.model_dump(), indent=2)
    full_prompt = f"{DESIGN_SYSTEM_PROMPT}\n\nIntent Input:\n{intent_json}"

    raw_output = call_model(full_prompt)

    logger.debug(f"Stage 2 raw output: {raw_output}")

    # Repair + validate
    repaired_data, validation = repair_layer("system_design", raw_output)

    if not validation.is_valid:
        logger.error(f"Stage 2 repair failed: {validation.errors}")
        raise ValueError(f"Stage 2 failed after repair: {validation.errors}")

    design = SystemDesignSchema(**repaired_data)
    logger.info(f"Stage 2 complete: {len(design.entities)} entities, {len(design.flows)} flows")
    return design


# ─────────────────────────────────────────────
# LOCAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from pipeline.stage1_intent import run_stage1
    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    intent = run_stage1(test_prompt)
    result = run_stage2(intent)
    print(json.dumps(result.model_dump(), indent=2))