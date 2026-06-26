import os
import time
import json
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from pipeline.stage1_intent import run_stage1
from pipeline.stage2_design import run_stage2
from pipeline.stage3_schema import (
    run_stage3, generate_database, generate_api,
    generate_ui, generate_auth, generate_business_logic
)
from pipeline.stage4_refine import run_stage4
from fastapi.responses import StreamingResponse
from runtime.generator import generate_app, zip_generated_app
from validation.repair import check_cross_layer_consistency

load_dotenv()

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(
    title="App Compiler API",
    description="Converts natural language prompts into structured app configurations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-app-compiler-eta.vercel.app",
        "http://localhost:3000",                 
        "http://localhost:3001",                 
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────

class CompileRequest(BaseModel):
    prompt: str
    generate_app_files: bool = False

class StageResult(BaseModel):
    stage: str
    status: str
    duration_ms: int
    output_summary: dict

class CompileResponse(BaseModel):
    success: bool
    prompt: str
    app_config: dict
    stages: list[StageResult]
    validation: dict
    generated_app_path: str | None = None
    total_duration_ms: int
    timestamp: str

# ─────────────────────────────────────────────
# EVALUATION LOG HELPER
# ─────────────────────────────────────────────

RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "evaluation", "results.json"
)

def log_result(prompt: str, success: bool, stages: list, duration_ms: int, error: str = None):
    try:
        os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)

        results = []
        if os.path.exists(RESULTS_PATH):
            try:
                with open(RESULTS_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        results = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                logger.warning("results.json was corrupt — resetting")
                results = []

        results.append({
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": prompt[:100],
            "success": success,
            "total_duration_ms": duration_ms,
            "stages_completed": len(stages),
            "error": error
        })

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    except Exception as e:
        logger.warning(f"Failed to log result: {e}")

# ─────────────────────────────────────────────
# CORE COMPILE ENDPOINT
# ─────────────────────────────────────────────

@app.post("/compile", response_model=CompileResponse)
async def compile_prompt(request: CompileRequest):
    """
    Main pipeline endpoint.
    Takes a natural language prompt and returns a complete app configuration.
    """
    if not request.prompt or len(request.prompt.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Prompt is too short. Please describe your app in more detail."
        )

    total_start = time.time()
    stages = []

    try:
        # ── Stage 1: Intent Extraction
        s1_start = time.time()
        intent = run_stage1(request.prompt)
        s1_duration = int((time.time() - s1_start) * 1000)
        stages.append(StageResult(
            stage="intent_extraction",
            status="success",
            duration_ms=s1_duration,
            output_summary={
                "app_name": intent.app_name,
                "app_type": intent.app_type,
                "features_count": len(intent.core_features),
                "roles": intent.user_roles,
                "assumptions": intent.assumptions
            }
        ))
        logger.info(f"Stage 1 done in {s1_duration}ms")

        # ── Stage 2: System Design
        s2_start = time.time()
        design = run_stage2(intent)
        s2_duration = int((time.time() - s2_start) * 1000)
        stages.append(StageResult(
            stage="system_design",
            status="success",
            duration_ms=s2_duration,
            output_summary={
                "entities_count": len(design.entities),
                "flows_count": len(design.flows),
                "external_services": design.external_services
            }
        ))
        logger.info(f"Stage 2 done in {s2_duration}ms")

        # ── Stage 3: Schema Generation
        s3_start = time.time()
        db, api, ui, auth, biz = run_stage3(intent, design)
        s3_duration = int((time.time() - s3_start) * 1000)
        stages.append(StageResult(
            stage="schema_generation",
            status="success",
            duration_ms=s3_duration,
            output_summary={
                "db_tables": len(db.tables),
                "api_endpoints": len(api.endpoints),
                "ui_pages": len(ui.pages),
                "auth_roles": len(auth.roles),
                "business_rules": len(biz.rules)
            }
        ))
        logger.info(f"Stage 3 done in {s3_duration}ms")

        # ── Stage 4: Refinement
        s4_start = time.time()
        final_config = run_stage4(intent, design, db, api, ui, auth, biz)
        s4_duration = int((time.time() - s4_start) * 1000)

        consistency = check_cross_layer_consistency(final_config.model_dump())
        stages.append(StageResult(
            stage="refinement",
            status="success",
            duration_ms=s4_duration,
            output_summary={
                "consistency_valid": consistency.is_valid,
                "errors": len(consistency.errors),
                "warnings": len(consistency.warnings)
            }
        ))
        logger.info(f"Stage 4 done in {s4_duration}ms")

        # ── Runtime Generation (optional)
        generated_path = None
        if request.generate_app_files:
            safe_name = final_config.intent.app_name.replace(" ", "_").lower()
            output_dir = os.path.join("generated_apps", safe_name)
            _folder_path, zip_path = generate_app(final_config, output_dir=output_dir)
            generated_path = f"/download/{os.path.basename(zip_path)}"
            logger.info(f"App zipped and ready for download at: {generated_path}")

        total_duration = int((time.time() - total_start) * 1000)

        # ── Log result
        log_result(request.prompt, True, stages, total_duration)

        return CompileResponse(
            success=True,
            prompt=request.prompt,
            app_config=final_config.model_dump(),
            stages=[s.model_dump() for s in stages],
            validation={
                "is_valid": consistency.is_valid,
                "errors": [e.model_dump() for e in consistency.errors],
                "warnings": [w.model_dump() for w in consistency.warnings]
            },
            generated_app_path=generated_path,
            total_duration_ms=total_duration,
            timestamp=datetime.utcnow().isoformat()
        )

    except Exception as e:
        total_duration = int((time.time() - total_start) * 1000)
        log_result(request.prompt, False, stages, total_duration, error=str(e))
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "stages_completed": len(stages),
                "failed_at": stages[-1].stage if stages else "intent_extraction"
            }
        )

# ─────────────────────────────────────────────
# CORE COMPILE ENDPOINT (STREAMING)
# ─────────────────────────────────────────────

@app.post("/compile/stream")
async def compile_stream(request: CompileRequest):
    """
    Streaming pipeline endpoint.
    Yields Server-Sent Events (SSE) representing stage progress and final output.
    """
    if not request.prompt or len(request.prompt.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Prompt is too short. Please describe your app in more detail."
        )

    async def event_generator():
        total_start = time.time()
        stages = []
        try:
            # ── Stage 1: Intent Extraction
            yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'intent_extraction', 'label': 'Extracting Intent'})}\n\n"
            s1_start = time.time()
            intent = await asyncio.to_thread(run_stage1, request.prompt)
            s1_duration = int((time.time() - s1_start) * 1000)
            s1_summary = {
                "app_name": intent.app_name,
                "app_type": intent.app_type,
                "features_count": len(intent.core_features),
                "roles": intent.user_roles,
                "assumptions": intent.assumptions
            }
            stages.append(StageResult(
                stage="intent_extraction",
                status="success",
                duration_ms=s1_duration,
                output_summary=s1_summary
            ))
            yield f"data: {json.dumps({'type': 'stage_done', 'stage': 'intent_extraction', 'duration_ms': s1_duration, 'output_summary': s1_summary})}\n\n"

            # ── Stage 2: System Design
            yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'system_design', 'label': 'Designing Architecture'})}\n\n"
            s2_start = time.time()
            design = await asyncio.to_thread(run_stage2, intent)
            s2_duration = int((time.time() - s2_start) * 1000)
            s2_summary = {
                "entities_count": len(design.entities),
                "flows_count": len(design.flows),
                "external_services": design.external_services
            }
            stages.append(StageResult(
                stage="system_design",
                status="success",
                duration_ms=s2_duration,
                output_summary=s2_summary
            ))
            yield f"data: {json.dumps({'type': 'stage_done', 'stage': 'system_design', 'duration_ms': s2_duration, 'output_summary': s2_summary})}\n\n"

            # ── Stage 3: Schema Generation
            yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'schema_generation', 'label': 'Generating Schemas'})}\n\n"
            s3_start = time.time()

            # Sub-generators directly called to emit finer-grained events
            sub_start = time.time()
            db = await asyncio.to_thread(generate_database, intent, design)
            yield f"data: {json.dumps({'type': 'substep_done', 'stage': 'schema_generation', 'substep': 'database', 'duration_ms': int((time.time() - sub_start) * 1000)})}\n\n"

            sub_start = time.time()
            api = await asyncio.to_thread(generate_api, intent, design, db)
            yield f"data: {json.dumps({'type': 'substep_done', 'stage': 'schema_generation', 'substep': 'api', 'duration_ms': int((time.time() - sub_start) * 1000)})}\n\n"

            sub_start = time.time()
            ui = await asyncio.to_thread(generate_ui, intent, design, api)
            yield f"data: {json.dumps({'type': 'substep_done', 'stage': 'schema_generation', 'substep': 'ui', 'duration_ms': int((time.time() - sub_start) * 1000)})}\n\n"

            sub_start = time.time()
            auth = await asyncio.to_thread(generate_auth, intent, design)
            yield f"data: {json.dumps({'type': 'substep_done', 'stage': 'schema_generation', 'substep': 'auth', 'duration_ms': int((time.time() - sub_start) * 1000)})}\n\n"

            sub_start = time.time()
            biz = await asyncio.to_thread(generate_business_logic, intent, design, db)
            yield f"data: {json.dumps({'type': 'substep_done', 'stage': 'schema_generation', 'substep': 'business_logic', 'duration_ms': int((time.time() - sub_start) * 1000)})}\n\n"

            s3_duration = int((time.time() - s3_start) * 1000)
            s3_summary = {
                "db_tables": len(db.tables),
                "api_endpoints": len(api.endpoints),
                "ui_pages": len(ui.pages),
                "auth_roles": len(auth.roles),
                "business_rules": len(biz.rules)
            }
            stages.append(StageResult(
                stage="schema_generation",
                status="success",
                duration_ms=s3_duration,
                output_summary=s3_summary
            ))
            yield f"data: {json.dumps({'type': 'stage_done', 'stage': 'schema_generation', 'duration_ms': s3_duration, 'output_summary': s3_summary})}\n\n"

            # ── Stage 4: Refinement
            yield f"data: {json.dumps({'type': 'stage_start', 'stage': 'refinement', 'label': 'Refining & Validating'})}\n\n"
            s4_start = time.time()
            final_config = await asyncio.to_thread(run_stage4, intent, design, db, api, ui, auth, biz)
            s4_duration = int((time.time() - s4_start) * 1000)

            consistency = check_cross_layer_consistency(final_config.model_dump())
            s4_summary = {
                "consistency_valid": consistency.is_valid,
                "errors": len(consistency.errors),
                "warnings": len(consistency.warnings)
            }
            stages.append(StageResult(
                stage="refinement",
                status="success",
                duration_ms=s4_duration,
                output_summary=s4_summary
            ))
            yield f"data: {json.dumps({'type': 'stage_done', 'stage': 'refinement', 'duration_ms': s4_duration, 'output_summary': s4_summary})}\n\n"

            # ── Runtime Generation (optional)
            generated_path = None
            if request.generate_app_files:
                safe_name = final_config.intent.app_name.replace(" ", "_").lower()
                output_dir = os.path.join("generated_apps", safe_name)
                _folder_path, zip_path = await asyncio.to_thread(generate_app, final_config, output_dir=output_dir)
                generated_path = f"/download/{os.path.basename(zip_path)}"
                logger.info(f"App zipped and ready for download at: {generated_path}")

            total_duration = int((time.time() - total_start) * 1000)

            # ── Log result
            log_result(request.prompt, True, stages, total_duration)

            complete_response = {
                "success": True,
                "prompt": request.prompt,
                "app_config": final_config.model_dump(),
                "stages": [s.model_dump() for s in stages],
                "validation": {
                    "is_valid": consistency.is_valid,
                    "errors": [e.model_dump() for e in consistency.errors],
                    "warnings": [w.model_dump() for w in consistency.warnings]
                },
                "generated_app_path": generated_path,
                "total_duration_ms": total_duration,
                "timestamp": datetime.utcnow().isoformat()
            }
            yield f"data: {json.dumps({'type': 'complete', 'data': complete_response})}\n\n"

        except Exception as e:
            total_duration = int((time.time() - total_start) * 1000)
            log_result(request.prompt, False, stages, total_duration, error=str(e))
            logger.error(f"Pipeline streaming failed: {e}")
            stage_name = stages[-1].stage if stages else "intent_extraction"
            yield f"data: {json.dumps({'type': 'error', 'stage': stage_name, 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ─────────────────────────────────────────────
# DOWNLOAD ENDPOINT
# NOTE: Generated apps are stored temporarily on local disk and zipped
# for download. On platforms with ephemeral filesystems (e.g. Render
# free tier), these files do not persist across service restarts or
# redeploys. This is acceptable for demo purposes but would need
# external storage (S3, etc.) for production persistence.
# ─────────────────────────────────────────────

@app.get("/download/{filename}")
async def download_generated_app(filename: str):
    """
    Serves a previously generated app's zip file for download.
    """
    from fastapi.responses import FileResponse

    # Security: prevent path traversal — only allow simple filenames,
    # no directory separators or '..' sequences
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    zip_path = os.path.join("generated_apps", filename)

    if not os.path.exists(zip_path):
        raise HTTPException(
            status_code=404,
            detail="Generated app not found. It may have expired or the server may have restarted."
        )

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=filename,
    )

# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model": "meta/llama-3.3-70b-instruct",
        "pipeline_stages": 4,
        "timestamp": datetime.utcnow().isoformat()
    }

# ─────────────────────────────────────────────
# METRICS ENDPOINT
# ─────────────────────────────────────────────

@app.get("/metrics")
async def get_metrics():
    """Returns evaluation metrics from the results log."""
    try:
        if not os.path.exists(RESULTS_PATH):
            return {"message": "No results logged yet", "total_runs": 0}

        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"message": "No results logged yet", "total_runs": 0}
            data = json.loads(content)

        # Handle both formats — evaluation runner and live API logger
        if isinstance(data, list):
            results = data
            total = len(results)
            successful = sum(1 for r in results if r.get("success"))
            avg_duration = sum(r.get("total_duration_ms", 0) for r in results) / total if total else 0
            return {
                "total_runs": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": f"{(successful/total*100):.1f}%" if total else "0%",
                "average_duration_ms": int(avg_duration),
                "recent_runs": results[-5:]
            }
        else:
            # Evaluation runner format
            return {
                "total_runs": data.get("metrics", {}).get("total_prompts", 0),
                "metrics": data.get("metrics", {}),
                "recent_results": data.get("results", [])[-5:]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)