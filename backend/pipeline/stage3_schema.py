import os
import json
import logging
from dotenv import load_dotenv
from validation.schemas import (
    IntentSchema, SystemDesignSchema,
    DatabaseSchema, APISchema, UISchema,
    AuthSchema, BusinessLogicSchema
)
from pipeline.llm_client import call_model
from validation.repair import repair_layer

load_dotenv()
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DATABASE PROMPT
# ─────────────────────────────────────────────

DB_PROMPT = """
You are the Database Schema Generator of an app compiler.
Given the app intent and system design, generate a complete database schema.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Every table must have an id field (uuid, primary_key: true).
- Use snake_case for all table and field names.
- Foreign keys must reference valid tables using format "table_name.id".
- Field types must be one of: string, integer, boolean, float, date, datetime, text, uuid, json.

Output this exact JSON structure:
{
  "tables": [
    {
      "name": "string",
      "fields": [
        {
          "name": "string",
          "type": "string",
          "required": true,
          "unique": false,
          "primary_key": false,
          "foreign_key": null,
          "default": null
        }
      ],
      "relations": [
        {
          "type": "one_to_many",
          "target_table": "string"
        }
      ]
    }
  ]
}
"""

# ─────────────────────────────────────────────
# API PROMPT
# ─────────────────────────────────────────────

API_PROMPT = """
You are the API Schema Generator of an app compiler.
Given the app intent, system design, and database table names, generate a complete REST API schema.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- All paths must start with /api/v1/.
- Use RESTful conventions (GET /resources, POST /resources, PUT /resources/:id, DELETE /resources/:id).
- Field types must be one of: string, integer, boolean, float, date, datetime, text, uuid, json.
- Every endpoint must specify roles_allowed.

Output this exact JSON structure:
{
  "base_path": "/api/v1",
  "endpoints": [
    {
      "path": "string",
      "method": "GET",
      "description": "string",
      "request_body": [
        { "name": "string", "type": "string", "required": true }
      ],
      "response_fields": [
        { "name": "string", "type": "string", "required": true }
      ],
      "auth_required": true,
      "roles_allowed": ["string"]
    }
  ]
}
"""

# ─────────────────────────────────────────────
# UI PROMPT
# ─────────────────────────────────────────────

UI_PROMPT = """
You are the UI Schema Generator of an app compiler.
Given the app intent, system design, and API endpoint paths, generate a complete UI schema.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Every page must have a path starting with /.
- Component types must be one of: table, form, chart, card, list, modal, navbar, sidebar, button, input.
- data_source must reference an existing API endpoint path.
- visible_to_roles must reference roles defined in the app.
- fields must be plain strings only — just the field name, nothing else.
- nav_items must be plain strings only — just the label name, nothing else.

Output this exact JSON structure:
{
  "pages": [
    {
      "name": "string",
      "path": "string",
      "title": "string",
      "auth_required": true,
      "roles_allowed": ["string"],
      "components": [
        {
          "id": "string",
          "type": "table",
          "label": "string",
          "data_source": "string",
          "fields": ["string"],
          "actions": ["string"],
          "visible_to_roles": ["string"]
        }
      ]
    }
  ],
  "theme": "light",
  "nav_items": ["string"]
}
"""

# ─────────────────────────────────────────────
# AUTH PROMPT
# ─────────────────────────────────────────────

AUTH_PROMPT = """
You are the Auth Schema Generator of an app compiler.
Given the app intent and roles, generate a complete authentication and authorization schema.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Every role from the intent must have a RoleDefinition.
- Actions must be from: read, write, update, delete, manage.
- Resources should match entity names from the system design.

Output this exact JSON structure:
{
  "roles": [
    {
      "role": "string",
      "permissions": [
        {
          "resource": "string",
          "actions": ["read", "write"]
        }
      ],
      "can_access_premium": false
    }
  ],
  "jwt_enabled": true,
  "session_timeout_minutes": 60,
  "oauth_providers": []
}
"""

# ─────────────────────────────────────────────
# BUSINESS LOGIC PROMPT
# ─────────────────────────────────────────────

BIZ_PROMPT = """
You are the Business Logic Generator of an app compiler.
Given the full app context, generate business rules and logic.

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no code fences.
- Triggers should be event names like: on_payment_success, on_user_register, on_role_change.
- Only include payment_gateway if the app has payments.
- premium_features should list features restricted to premium users.

Output this exact JSON structure:
{
  "rules": [
    {
      "name": "string",
      "description": "string",
      "trigger": "string",
      "actions": ["string"],
      "applies_to_roles": ["string"]
    }
  ],
  "payment_gateway": null,
  "premium_features": ["string"]
}
"""

# ─────────────────────────────────────────────
# CONTEXT BUILDERS (trimmed for speed)
# ─────────────────────────────────────────────

def intent_summary(intent: IntentSchema) -> str:
    """Trimmed intent — only what downstream stages need."""
    return json.dumps({
        "app_name": intent.app_name,
        "app_type": intent.app_type,
        "description": intent.description,
        "user_roles": intent.user_roles,
        "has_payments": intent.has_payments,
        "has_analytics": intent.has_analytics,
        "core_features": [f.name for f in intent.core_features]
    }, indent=2)


def design_summary(design: SystemDesignSchema) -> str:
    """Trimmed design — entity names + flow names only."""
    return json.dumps({
        "entities": [e.name for e in design.entities],
        "flows": [f.name for f in design.flows],
        "external_services": design.external_services
    }, indent=2)


def db_summary(db: DatabaseSchema) -> str:
    """Trimmed DB — table names + field names only."""
    return json.dumps({
        "tables": [
            {
                "name": t.name,
                "fields": [f.name for f in t.fields]
            }
            for t in db.tables
        ]
    }, indent=2)


def api_summary(api: APISchema) -> str:
    """Trimmed API — paths + methods only."""
    return json.dumps({
        "base_path": api.base_path,
        "endpoints": [
            {
                "path": e.path,
                "method": e.method.value if hasattr(e.method, "value") else e.method,
                "roles_allowed": e.roles_allowed
            }
            for e in api.endpoints
        ]
    }, indent=2)

# ─────────────────────────────────────────────
# INDIVIDUAL GENERATORS
# ─────────────────────────────────────────────

def generate_database(intent: IntentSchema, design: SystemDesignSchema) -> DatabaseSchema:
    logger.info("Stage 3a: Generating database schema...")
    context = (
        f"Intent:\n{intent_summary(intent)}\n\n"
        f"System Design:\n{design_summary(design)}"
    )
    raw_output = call_model(f"{DB_PROMPT}\n\nContext:\n{context}")
    data, validation = repair_layer("database", raw_output)
    if not validation.is_valid:
        raise ValueError(f"Database schema generation failed: {validation.errors}")
    return DatabaseSchema(**data)


def generate_api(intent: IntentSchema, design: SystemDesignSchema, db: DatabaseSchema) -> APISchema:
    logger.info("Stage 3b: Generating API schema...")
    context = (
        f"Intent:\n{intent_summary(intent)}\n\n"
        f"System Design:\n{design_summary(design)}\n\n"
        f"Database Tables:\n{db_summary(db)}"
    )
    raw_output = call_model(f"{API_PROMPT}\n\nContext:\n{context}")
    data, validation = repair_layer("api", raw_output)
    if not validation.is_valid:
        raise ValueError(f"API schema generation failed: {validation.errors}")
    return APISchema(**data)


def generate_ui(intent: IntentSchema, design: SystemDesignSchema, api: APISchema) -> UISchema:
    logger.info("Stage 3c: Generating UI schema...")
    context = (
        f"Intent:\n{intent_summary(intent)}\n\n"
        f"System Design:\n{design_summary(design)}\n\n"
        f"API Endpoints:\n{api_summary(api)}"
    )
    raw_output = call_model(f"{UI_PROMPT}\n\nContext:\n{context}")
    data, validation = repair_layer("ui", raw_output)
    if not validation.is_valid:
        raise ValueError(f"UI schema generation failed: {validation.errors}")
    return UISchema(**data)


def generate_auth(intent: IntentSchema, design: SystemDesignSchema) -> AuthSchema:
    logger.info("Stage 3d: Generating auth schema...")
    context = (
        f"Intent:\n{intent_summary(intent)}\n\n"
        f"System Design:\n{design_summary(design)}"
    )
    raw_output = call_model(f"{AUTH_PROMPT}\n\nContext:\n{context}")
    data, validation = repair_layer("auth", raw_output)
    if not validation.is_valid:
        raise ValueError(f"Auth schema generation failed: {validation.errors}")
    return AuthSchema(**data)


def generate_business_logic(intent: IntentSchema, design: SystemDesignSchema, db: DatabaseSchema) -> BusinessLogicSchema:
    logger.info("Stage 3e: Generating business logic...")
    context = (
        f"Intent:\n{intent_summary(intent)}\n\n"
        f"System Design:\n{design_summary(design)}\n\n"
        f"Database Tables:\n{db_summary(db)}"
    )
    raw_output = call_model(f"{BIZ_PROMPT}\n\nContext:\n{context}")
    data, validation = repair_layer("business_logic", raw_output)
    if not validation.is_valid:
        raise ValueError(f"Business logic generation failed: {validation.errors}")
    return BusinessLogicSchema(**data)


# ─────────────────────────────────────────────
# STAGE 3 MASTER RUNNER
# ─────────────────────────────────────────────

def run_stage3(intent: IntentSchema, design: SystemDesignSchema):
    db = generate_database(intent, design)
    api = generate_api(intent, design, db)
    ui = generate_ui(intent, design, api)
    auth = generate_auth(intent, design)
    biz = generate_business_logic(intent, design, db)
    logger.info("Stage 3 complete: all schemas generated")
    return db, api, ui, auth, biz


# ─────────────────────────────────────────────
# LOCAL TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from pipeline.stage1_intent import run_stage1
    from pipeline.stage2_design import run_stage2
    test_prompt = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    intent = run_stage1(test_prompt)
    design = run_stage2(intent)
    db, api, ui, auth, biz = run_stage3(intent, design)
    print("DB Tables:", [t.name for t in db.tables])
    print("API Endpoints:", [e.path for e in api.endpoints])
    print("UI Pages:", [p.name for p in ui.pages])
    print("Auth Roles:", [r.role for r in auth.roles])
    print("Biz Rules:", [r.name for r in biz.rules])