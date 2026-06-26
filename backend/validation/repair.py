import json
import logging
from json_repair import repair_json
from typing import Any, Dict, Tuple
from validation.schemas import ValidationResult, ValidationError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# LAYER FIELD REQUIREMENTS
# ─────────────────────────────────────────────

REQUIRED_KEYS = {
    "intent": ["app_name", "app_type", "description", "core_features", "user_roles"],
    "system_design": ["entities", "flows"],
    "database": ["tables"],
    "api": ["endpoints"],
    "ui": ["pages"],
    "auth": ["roles"],
    "business_logic": ["rules"],
}

# ─────────────────────────────────────────────
# JSON REPAIR
# ─────────────────────────────────────────────

def safe_parse_json(raw: str) -> Tuple[Dict, bool]:
    """
    Attempt to parse JSON. If it fails, use json_repair to fix it.
    Returns (parsed_dict, was_repaired)
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        return json.loads(cleaned), False
    except json.JSONDecodeError:
        logger.warning("JSON decode failed — attempting repair")
        try:
            repaired = repair_json(cleaned)
            return json.loads(repaired), True
        except Exception as e:
            logger.error(f"JSON repair also failed: {e}")
            return {}, True

# ─────────────────────────────────────────────
# MISSING KEY REPAIR
# ─────────────────────────────────────────────

DEFAULTS = {
    "core_features": [],
    "user_roles": ["admin", "user"],
    "assumptions": [],
    "clarifications_needed": [],
    "has_payments": False,
    "has_analytics": False,
    "has_notifications": False,
    "entities": [],
    "flows": [],
    "external_services": [],
    "architecture_notes": [],
    "tables": [],
    "endpoints": [],
    "base_path": "/api/v1",
    "pages": [],
    "theme": "light",
    "nav_items": [],
    "roles": [],
    "jwt_enabled": True,
    "session_timeout_minutes": 60,
    "oauth_providers": [],
    "rules": [],
    "premium_features": [],
}

def inject_missing_keys(layer_name: str, data: Dict) -> Dict:
    """Inject default values for missing required keys."""
    required = REQUIRED_KEYS.get(layer_name, [])
    for key in required:
        if key not in data:
            logger.warning(f"[{layer_name}] Missing key '{key}' — injecting default")
            data[key] = DEFAULTS.get(key, None)
    return data

# ─────────────────────────────────────────────
# VALID TYPES
# ─────────────────────────────────────────────

VALID_FIELD_TYPES = {
    "string", "integer", "boolean", "float",
    "date", "datetime", "text", "uuid", "json"
}

# ─────────────────────────────────────────────
# FIELD REPAIR
# ─────────────────────────────────────────────

def fix_api_fields(data: Dict) -> Dict:
    """
    Ensure every request_body and response_fields item has required fields.
    LLMs sometimes return {name: x} without type, or with empty/invalid type.
    """
    for endpoint in data.get("endpoints", []):
        if not isinstance(endpoint, dict):
            continue
        for field in endpoint.get("request_body", []):
            if isinstance(field, dict):
                if not field.get("type") or field["type"] not in VALID_FIELD_TYPES:
                    field["type"] = "string"
                if "required" not in field:
                    field["required"] = True
                if not field.get("name"):
                    field["name"] = "field"
        for field in endpoint.get("response_fields", []):
            if isinstance(field, dict):
                if not field.get("type") or field["type"] not in VALID_FIELD_TYPES:
                    field["type"] = "string"
                if "required" not in field:
                    field["required"] = True
                if not field.get("name"):
                    field["name"] = "field"
    return data

def fix_api_endpoints(data: Dict) -> Dict:
    """
    Ensure every endpoint has required top-level fields.
    LLMs sometimes return incomplete endpoint objects.
    """
    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    cleaned_endpoints = []

    for endpoint in data.get("endpoints", []):
        if not isinstance(endpoint, dict):
            continue

        # Skip completely empty endpoints
        if not endpoint.get("path"):
            logger.warning("Skipping endpoint with no path")
            continue

        # Fix missing method
        if not endpoint.get("method") or endpoint["method"].upper() not in valid_methods:
            path = endpoint.get("path", "")
            # Guess method from path context
            if any(x in path for x in ["/create", "/add", "/register", "/login"]):
                endpoint["method"] = "POST"
            elif any(x in path for x in ["/update", "/edit"]):
                endpoint["method"] = "PUT"
            elif any(x in path for x in ["/delete", "/remove"]):
                endpoint["method"] = "DELETE"
            else:
                endpoint["method"] = "GET"
            logger.warning(f"Injected method '{endpoint['method']}' for endpoint: {path}")

        # Fix missing description
        if not endpoint.get("description"):
            endpoint["description"] = f"{endpoint['method']} {endpoint['path']}"
            logger.warning(f"Injected description for endpoint: {endpoint['path']}")

        # Fix missing auth_required
        if "auth_required" not in endpoint:
            endpoint["auth_required"] = True

        # Fix missing roles_allowed
        if "roles_allowed" not in endpoint or not isinstance(endpoint["roles_allowed"], list):
            endpoint["roles_allowed"] = []

        # Fix missing request_body and response_fields
        if "request_body" not in endpoint:
            endpoint["request_body"] = []
        if "response_fields" not in endpoint:
            endpoint["response_fields"] = []

        cleaned_endpoints.append(endpoint)

    data["endpoints"] = cleaned_endpoints
    return data


def fix_db_fields(data: Dict) -> Dict:
    """
    Ensure every DB field has required attributes.
    """
    for table in data.get("tables", []):
        if not isinstance(table, dict):
            continue
        for field in table.get("fields", []):
            if isinstance(field, dict):
                if not field.get("type") or field["type"] not in VALID_FIELD_TYPES:
                    field["type"] = "string"
                if "required" not in field:
                    field["required"] = True
                if "unique" not in field:
                    field["unique"] = False
                if "primary_key" not in field:
                    field["primary_key"] = False
                if "foreign_key" not in field:
                    field["foreign_key"] = None
                if "default" not in field:
                    field["default"] = None
    return data

# ─────────────────────────────────────────────
# CROSS-LAYER CONSISTENCY CHECK
# ─────────────────────────────────────────────

def check_cross_layer_consistency(config: Dict) -> ValidationResult:
    """
    Check that:
    - UI data_sources map to real API endpoints
    - Auth roles used in UI/API exist in auth schema
    - API response fields reference valid DB table names
    """
    errors = []
    warnings = []

    # Build lookup sets — all crash-safe
    db_tables = {
        t.get("name")
        for t in config.get("database", {}).get("tables", [])
        if isinstance(t, dict) and t.get("name")
    }

    api_paths = {
        e.get("path")
        for e in config.get("api", {}).get("endpoints", [])
        if isinstance(e, dict) and e.get("path")
    }

    auth_roles = {
        r.get("role")
        for r in config.get("auth", {}).get("roles", [])
        if isinstance(r, dict) and r.get("role")
    }

    # ── Check 1: UI data_sources map to real API endpoints
    for page in config.get("ui", {}).get("pages", []):
        if not isinstance(page, dict):
            continue
        for component in page.get("components", []):
            if not isinstance(component, dict):
                continue
            ds = component.get("data_source")
            if ds and ds not in api_paths:
                warnings.append(ValidationError(
                    layer="ui",
                    field=f"page:{page.get('name', 'unknown')}/component:{component.get('id', 'unknown')}",
                    issue=f"data_source '{ds}' does not match any API endpoint",
                    severity="warning"
                ))

    # ── Check 2: Roles used in UI pages exist in auth schema
    for page in config.get("ui", {}).get("pages", []):
        if not isinstance(page, dict):
            continue
        for role in page.get("roles_allowed", []):
            if role and role not in auth_roles:
                errors.append(ValidationError(
                    layer="ui",
                    field=f"page:{page.get('name', 'unknown')}",
                    issue=f"role '{role}' not defined in auth schema",
                    severity="critical"
                ))

    # ── Check 3: Roles used in API endpoints exist in auth schema
    for endpoint in config.get("api", {}).get("endpoints", []):
        if not isinstance(endpoint, dict):
            continue
        for role in endpoint.get("roles_allowed", []):
            if role and role not in auth_roles:
                errors.append(ValidationError(
                    layer="api",
                    field=endpoint.get("path", "unknown"),
                    issue=f"role '{role}' not defined in auth schema",
                    severity="critical"
                ))

    # ── Check 4: API foreign keys reference valid DB tables (uses db_tables)
    for endpoint in config.get("api", {}).get("endpoints", []):
        if not isinstance(endpoint, dict):
            continue
        all_fields = endpoint.get("request_body", []) + endpoint.get("response_fields", [])
        for field in all_fields:
            if not isinstance(field, dict):
                continue
            fk = field.get("foreign_key")
            if fk:
                # foreign_key format is "table_name.id" — extract table name
                ref_table = fk.split(".")[0] if "." in fk else fk
                if ref_table and ref_table not in db_tables:
                    warnings.append(ValidationError(
                        layer="api",
                        field=f"{endpoint.get('path', 'unknown')}.{field.get('name', 'unknown')}",
                        issue=f"foreign_key references unknown table '{ref_table}'",
                        severity="warning"
                    ))

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

# ─────────────────────────────────────────────
# MASTER REPAIR FUNCTION
# ─────────────────────────────────────────────

def repair_layer(layer_name: str, raw_output: str) -> Tuple[Dict, ValidationResult]:
    parsed, was_repaired = safe_parse_json(raw_output)

    if not parsed:
        return {}, ValidationResult(
            is_valid=False,
            errors=[ValidationError(
                layer=layer_name,
                field="root",
                issue="Could not parse or repair JSON output",
                severity="critical"
            )],
            repaired=was_repaired
        )

    # Inject missing top-level keys
    repaired_data = inject_missing_keys(layer_name, parsed)

    # Layer-specific field repairs
    if layer_name == "api":
        repaired_data = fix_api_endpoints(repaired_data)
        repaired_data = fix_api_fields(repaired_data)
    elif layer_name == "database":
        repaired_data = fix_db_fields(repaired_data)

    return repaired_data, ValidationResult(
        is_valid=True,
        errors=[],
        repaired=was_repaired
    )