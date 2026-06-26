from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────

class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    FLOAT = "float"
    DATE = "date"
    DATETIME = "datetime"
    TEXT = "text"
    UUID = "uuid"
    JSON = "json"

class ComponentType(str, Enum):
    TABLE = "table"
    FORM = "form"
    CHART = "chart"
    CARD = "card"
    LIST = "list"
    MODAL = "modal"
    NAVBAR = "navbar"
    SIDEBAR = "sidebar"
    BUTTON = "button"
    INPUT = "input"

class RelationType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"

class AuthRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"
    PREMIUM = "premium"

# ─────────────────────────────────────────────
# INTENT SCHEMA (Stage 1 Output)
# ─────────────────────────────────────────────

class Feature(BaseModel):
    name: str
    description: str
    requires_auth: bool = True
    roles_allowed: List[str] = []

class IntentSchema(BaseModel):
    app_name: str
    app_type: str  # e.g., "CRM", "E-commerce", "Dashboard"
    description: str
    core_features: List[Feature]
    user_roles: List[str]
    has_payments: bool = False
    has_analytics: bool = False
    has_notifications: bool = False
    assumptions: List[str] = []  # Documented assumptions for vague prompts
    clarifications_needed: List[str] = []  # Flags for underspecified input

# ─────────────────────────────────────────────
# SYSTEM DESIGN SCHEMA (Stage 2 Output)
# ─────────────────────────────────────────────

class Entity(BaseModel):
    name: str
    description: str
    fields: List[str]
    relations: List[str] = []

class AppFlow(BaseModel):
    name: str
    steps: List[str]
    roles_involved: List[str]

class SystemDesignSchema(BaseModel):
    entities: List[Entity]
    flows: List[AppFlow]
    external_services: List[str] = []  # e.g., Stripe, SendGrid
    architecture_notes: List[str] = []

# ─────────────────────────────────────────────
# DATABASE SCHEMA (Stage 3 Output - Part 1)
# ─────────────────────────────────────────────

class DBField(BaseModel):
    name: str
    type: FieldType
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None  # e.g., "users.id"
    default: Optional[Any] = None

class DBTable(BaseModel):
    name: str
    fields: List[DBField]
    relations: List[Dict[str, str]] = []  # [{type, target_table}]

class DatabaseSchema(BaseModel):
    tables: List[DBTable]

# ─────────────────────────────────────────────
# API SCHEMA (Stage 3 Output - Part 2)
# ─────────────────────────────────────────────

class APIField(BaseModel):
    name: str
    type: FieldType
    required: bool = True

class APIEndpoint(BaseModel):
    path: str
    method: HTTPMethod
    description: str
    request_body: List[APIField] = []
    response_fields: List[APIField] = []
    auth_required: bool = True
    roles_allowed: List[str] = []

class APISchema(BaseModel):
    base_path: str = "/api/v1"
    endpoints: List[APIEndpoint]

# ─────────────────────────────────────────────
# UI SCHEMA (Stage 3 Output - Part 3)
# ─────────────────────────────────────────────

class UIComponent(BaseModel):
    id: str
    type: ComponentType
    label: str
    data_source: Optional[str] = None
    fields: List[Union[str, Dict[str, Any]]] = []
    actions: List[Union[str, Dict[str, Any]]] = []
    visible_to_roles: List[str] = []

class UIPage(BaseModel):
    name: str
    path: str
    title: str
    auth_required: bool = True
    roles_allowed: List[str] = []
    components: List[UIComponent]

class UISchema(BaseModel):
    pages: List[UIPage]
    theme: str = "light"
    nav_items: List[Union[str, Dict[str, Any]]] = []

# ─────────────────────────────────────────────
# AUTH SCHEMA (Stage 3 Output - Part 4)
# ─────────────────────────────────────────────

class Permission(BaseModel):
    resource: str  # e.g., "contacts", "analytics"
    actions: List[str]  # e.g., ["read", "write", "delete"]

class RoleDefinition(BaseModel):
    role: str
    permissions: List[Permission]
    can_access_premium: bool = False

class AuthSchema(BaseModel):
    roles: List[RoleDefinition]
    jwt_enabled: bool = True
    session_timeout_minutes: int = 60
    oauth_providers: List[str] = []

# ─────────────────────────────────────────────
# BUSINESS LOGIC SCHEMA (Stage 3 Output - Part 5)
# ─────────────────────────────────────────────

class BusinessRule(BaseModel):
    name: str
    description: str
    trigger: str  # e.g., "on_payment_success"
    actions: List[str]
    applies_to_roles: List[str] = []

class BusinessLogicSchema(BaseModel):
    rules: List[BusinessRule]
    payment_gateway: Optional[str] = None  # e.g., "stripe"
    premium_features: List[str] = []

# ─────────────────────────────────────────────
# FINAL APP CONFIG (Stage 4 Output — Master Output)
# ─────────────────────────────────────────────

class AppConfig(BaseModel):
    intent: IntentSchema
    system_design: SystemDesignSchema
    database: DatabaseSchema
    api: APISchema
    ui: UISchema
    auth: AuthSchema
    business_logic: BusinessLogicSchema
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)

# ─────────────────────────────────────────────
# VALIDATION RESULT
# ─────────────────────────────────────────────

class ValidationError(BaseModel):
    layer: str  # e.g., "database", "api", "ui"
    field: str
    issue: str
    severity: str  # "critical" or "warning"

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = []
    warnings: List[ValidationError] = []
    repaired: bool = False