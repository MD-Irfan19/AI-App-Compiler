import os
import json
import logging
from json_repair import repair_json
from dotenv import load_dotenv
from validation.schemas import (
    AppConfig, IntentSchema, SystemDesignSchema,
    DatabaseSchema, APISchema, UISchema,
    AuthSchema, BusinessLogicSchema
)
from pipeline.llm_client import call_model
from validation.repair import check_cross_layer_consistency

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# REFINEMENT PROMPT
# ─────────────────────────────────────────────

REFINE_PROMPT = """
You are Stage 4 of an app compiler pipeline — the Refinement Layer.
You receive a complete app configuration and must fix any inconsistencies.

Your job:
- Ensure all roles used in UI and API exist in the auth schema
- Ensure all API data_sources in UI map to real API endpoint paths
- Ensure DB tables are referenced correctly in API request/response fields
- Remove hallucinated fields that don't belong
- Fill in any missing critical fields

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Return the COMPLETE corrected app config — all layers included.
- Do not remove any layers. Fix them.
- Keep the exact same JSON structure as the input.
"""

# ─────────────────────────────────────────────
# SAFE JSON PARSER FOR FULL CONFIG
# ─────────────────────────────────────────────

def parse_full_config(raw: str) -> dict:
    """
    Safely parse a full AppConfig JSON string.
    Tries direct parse first, then json_repair.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Stage 4: Direct JSON parse failed — attempting repair")
        try:
            return json.loads(repair_json(cleaned))
        except Exception as e:
            logger.error(f"Stage 4: JSON repair also failed: {e}")
            return {}

# ─────────────────────────────────────────────
# STAGE 4 RUNNER
# ─────────────────────────────────────────────

def run_stage4(
    intent: IntentSchema,
    design: SystemDesignSchema,
    db: DatabaseSchema,
    api: APISchema,
    ui: UISchema,
    auth: AuthSchema,
    biz: BusinessLogicSchema
) -> AppConfig:
    logger.info("Stage 4: Refining and assembling final config...")

    REQUIRED_LAYERS = ["intent", "system_design", "database", "api", "ui", "auth", "business_logic"]

    # Assemble raw config
    raw_config = {
        "intent": intent.model_dump(),
        "system_design": design.model_dump(),
        "database": db.model_dump(),
        "api": api.model_dump(),
        "ui": ui.model_dump(),
        "auth": auth.model_dump(),
        "business_logic": biz.model_dump(),
        "generation_metadata": {
            "pipeline_version": "1.0.0",
            "model_used": "meta/llama-3.3-70b-instruct",
        }
    }

    # Run cross-layer consistency check
    consistency = check_cross_layer_consistency(raw_config)
    logger.info(f"Pre-refinement consistency: valid={consistency.is_valid}, issues={len(consistency.errors + consistency.warnings)}")

    # If inconsistencies found — send to Nvidia NIM for repair
    if not consistency.is_valid:
        logger.info("Inconsistencies found — sending to Nvidia NIM for refinement...")

        issues = [e.model_dump() for e in consistency.errors + consistency.warnings]
        full_prompt = f"""{REFINE_PROMPT}

Current Config:
{json.dumps(raw_config, indent=2)}

Detected Issues:
{json.dumps(issues, indent=2)}

Return the corrected full config JSON:"""

        raw_output = call_model(full_prompt)

        # Parse the full refined config
        refined_data = parse_full_config(raw_output)


        if refined_data and "intent" in refined_data:
            # Merge — use refined layer if present, fall back to original if missing
            for layer in REQUIRED_LAYERS:
                if layer not in refined_data or not refined_data[layer]:
                    logger.warning(f"Stage 4: Refined config missing '{layer}' — keeping original")
                    refined_data[layer] = raw_config[layer]
            raw_config = refined_data
            logger.info("Stage 4: Refinement applied successfully")
        else:
            logger.warning("Stage 4: Refinement returned invalid output — using pre-refinement config")

    # Always re-inject generation_metadata (LLM may have dropped it)
    raw_config["generation_metadata"] = {
        "pipeline_version": "1.0.0",
        "model_used": "meta/llama-3.3-70b-instruct",
    }

    # Final consistency check
    final_consistency = check_cross_layer_consistency(raw_config)
    raw_config["generation_metadata"]["consistency_check"] = {
        "is_valid": final_consistency.is_valid,
        "errors": len(final_consistency.errors),
        "warnings": len(final_consistency.warnings)
    }

    for layer in REQUIRED_LAYERS:
        if layer not in raw_config or raw_config[layer] is None:
            raise ValueError(f"Critical layer '{layer}' is missing from final config")

    # Build final AppConfig
    app_config = AppConfig(**raw_config)
    logger.info("Stage 4 complete: Final AppConfig assembled")
    return app_config


# ─────────────────────────────────────────────
# LOCAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from pipeline.stage1_intent import run_stage1
    from pipeline.stage2_design import run_stage2
    from pipeline.stage3_schema import run_stage3

    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    intent = run_stage1(test_prompt)
    design = run_stage2(intent)
    db, api, ui, auth, biz = run_stage3(intent, design)
    final = run_stage4(intent, design, db, api, ui, auth, biz)
    print(json.dumps(final.model_dump(), indent=2))