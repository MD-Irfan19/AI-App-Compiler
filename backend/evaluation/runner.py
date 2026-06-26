import os
import sys
import json
import time
import logging
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from pipeline.stage1_intent import run_stage1
from pipeline.stage2_design import run_stage2
from pipeline.stage3_schema import run_stage3
from pipeline.stage4_refine import run_stage4
from validation.repair import check_cross_layer_consistency

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────

PROMPTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_prompts.json")
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")

# ─────────────────────────────────────────────
# RUN SINGLE PROMPT
# ─────────────────────────────────────────────

def run_single(prompt_obj: dict) -> dict:
    prompt = prompt_obj["prompt"]
    prompt_id = prompt_obj["id"]
    category = prompt_obj["category"]

    logger.info(f"Running prompt {prompt_id} [{category}]: {prompt[:60]}...")

    start = time.time()
    retries = 0
    stages_completed = 0
    error = None
    result = None

    try:
        # Stage 1
        intent = run_stage1(prompt)
        stages_completed = 1

        # Stage 2
        design = run_stage2(intent)
        stages_completed = 2

        # Stage 3
        db, api, ui, auth, biz = run_stage3(intent, design)
        stages_completed = 3

        # Stage 4
        final = run_stage4(intent, design, db, api, ui, auth, biz)
        stages_completed = 4

        # Consistency check
        consistency = check_cross_layer_consistency(final.model_dump())

        duration = int((time.time() - start) * 1000)

        result = {
            "id": prompt_id,
            "category": category,
            "prompt": prompt[:100],
            "success": True,
            "stages_completed": stages_completed,
            "retries": retries,
            "duration_ms": duration,
            "consistency_valid": consistency.is_valid,
            "consistency_errors": len(consistency.errors),
            "consistency_warnings": len(consistency.warnings),
            "output_summary": {
                "app_name": final.intent.app_name,
                "app_type": final.intent.app_type,
                "db_tables": len(final.database.tables),
                "api_endpoints": len(final.api.endpoints),
                "ui_pages": len(final.ui.pages),
                "auth_roles": len(final.auth.roles),
                "assumptions": final.intent.assumptions
            },
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        duration = int((time.time() - start) * 1000)
        error = str(e)[:200]
        logger.error(f"Prompt {prompt_id} failed at stage {stages_completed + 1}: {error}")

        result = {
            "id": prompt_id,
            "category": category,
            "prompt": prompt[:100],
            "success": False,
            "stages_completed": stages_completed,
            "retries": retries,
            "duration_ms": duration,
            "consistency_valid": False,
            "consistency_errors": 0,
            "consistency_warnings": 0,
            "output_summary": None,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }

    return result

# ─────────────────────────────────────────────
# COMPUTE SUMMARY METRICS
# ─────────────────────────────────────────────

def compute_metrics(results: list) -> dict:
    total = len(results)
    if total == 0:
        return {}

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    by_category = {}
    for r in results:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = {"total": 0, "success": 0}
        by_category[cat]["total"] += 1
        if r["success"]:
            by_category[cat]["success"] += 1

    category_rates = {
        cat: f"{(v['success']/v['total']*100):.1f}%"
        for cat, v in by_category.items()
    }

    avg_duration = (
        sum(r["duration_ms"] for r in successful) / len(successful)
        if successful else 0
    )

    consistency_passed = sum(
        1 for r in successful if r.get("consistency_valid")
    )

    failure_types = {}
    for r in failed:
        err = r.get("error", "unknown")
        key = "rate_limit" if "429" in err or "quota" in err.lower() else \
              "validation" if "validation" in err.lower() else \
              "json_parse" if "json" in err.lower() else "other"
        failure_types[key] = failure_types.get(key, 0) + 1

    return {
        "total_prompts": total,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": f"{(len(successful)/total*100):.1f}%",
        "avg_duration_ms": int(avg_duration),
        "consistency_pass_rate": f"{(consistency_passed/len(successful)*100):.1f}%" if successful else "0%",
        "success_by_category": category_rates,
        "failure_types": failure_types,
        "fastest_ms": min((r["duration_ms"] for r in successful), default=0),
        "slowest_ms": max((r["duration_ms"] for r in successful), default=0)
    }

# ─────────────────────────────────────────────
# MASTER RUNNER
# ─────────────────────────────────────────────

def run_evaluation(
    start_id: int = 1,
    end_id: int = 20,
    delay_between: int = 5
):
    """
    Runs evaluation on prompts from start_id to end_id.
    delay_between: seconds to wait between prompts (avoid rate limits)
    """
    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        all_prompts = json.load(f)

    prompts = [p for p in all_prompts if start_id <= p["id"] <= end_id]

    logger.info(f"Starting evaluation: {len(prompts)} prompts (IDs {start_id}–{end_id})")

    # Load existing results if any
    existing = []
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.load(f if not content else __import__('io').StringIO(content))
                    existing = data.get("results", [])
        except Exception:
            existing = []

    completed_ids = {r["id"] for r in existing}
    results = list(existing)

    for i, prompt_obj in enumerate(prompts):
        if prompt_obj["id"] in completed_ids:
            logger.info(f"Skipping prompt {prompt_obj['id']} — already completed")
            continue

        result = run_single(prompt_obj)
        results.append(result)

        # Save after every prompt (resume-safe)
        metrics = compute_metrics(results)
        output = {
            "run_timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "results": results
        }
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)

        logger.info(f"Progress: {i+1}/{len(prompts)} | Success rate so far: {metrics.get('success_rate', 'N/A')}")

        # Delay between prompts to avoid rate limits
        if i < len(prompts) - 1:
            logger.info(f"Waiting {delay_between}s before next prompt...")
            time.sleep(delay_between)

    # Final metrics
    final_metrics = compute_metrics(results)
    logger.info("\n" + "="*50)
    logger.info("EVALUATION COMPLETE")
    logger.info(f"Total: {final_metrics['total_prompts']}")
    logger.info(f"Success Rate: {final_metrics['success_rate']}")
    logger.info(f"Avg Duration: {final_metrics['avg_duration_ms']}ms")
    logger.info(f"Consistency Pass Rate: {final_metrics['consistency_pass_rate']}")
    logger.info(f"By Category: {final_metrics['success_by_category']}")
    logger.info("="*50)

    return final_metrics

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=20)
    parser.add_argument("--delay", type=int, default=5)
    args = parser.parse_args()

    run_evaluation(
        start_id=args.start,
        end_id=args.end,
        delay_between=args.delay
    )