from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    IN_REVIEW = "IN_REVIEW"

class IngredientDataStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INCOMPLETE = "INCOMPLETE"

class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    SEASONAL = "SEASONAL"

# --- User Schemas ---
class UserRegister(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(...)
    terms_accepted: bool = Field(default=False)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("terms_accepted")
    @classmethod
    def terms_must_be_accepted(cls, v: bool):
        if not v:
            raise ValueError("You must accept the terms of service and food safety disclaimer")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class UserProfileUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)

class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("New passwords do not match")
        return v

class UserRoleUpdate(BaseModel):
    role: UserRole

class UserStatusUpdate(BaseModel):
    is_active: bool

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetSubmit(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    confirm_password: str

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

# --- Restaurant Schemas ---
class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(default="")
    address: str = Field(default="")
    city: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(default="")
    email: str = Field(default="")
    cuisine_type: str = Field(default="Various")
    status: str = Field(default="ACTIVE")

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    cuisine_type: Optional[str] = None
    status: Optional[str] = None

class RestaurantResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    address: str = ""
    city: str
    phone: str = ""
    email: str = ""
    cuisine_type: str = "Various"
    status: str = "ACTIVE"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    dish_count: int = 0

# --- Allergen Schemas ---
class AllergenCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field(default="")
    allergen_category: str = Field(default="Major")

class AllergenUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allergen_category: Optional[str] = None

class AllergenResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    allergen_category: str = "Major"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    ingredient_count: int = 0
    dish_count: int = 0

# --- Ingredient Schemas ---
class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(default="")
    category: str = Field(default="General")
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    source_reference: str = Field(default="")
    allergen_ids: List[str] = Field(default_factory=list)

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    source_reference: Optional[str] = None
    allergen_ids: Optional[List[str]] = None

class IngredientResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "General"
    verification_status: str = "UNVERIFIED"
    source_reference: str = ""
    last_verified_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    allergens: List[Dict[str, Any]] = Field(default_factory=list)
    dish_count: int = 0

# --- Dish Schemas ---
class DishCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: str = Field(default="")
    category: str = Field(default="Main Course")
    price: float = Field(default=0.0, ge=0.0)
    vegetarian: bool = Field(default=False)
    vegan: bool = Field(default=False)
    preparation_notes: str = Field(default="")
    availability_status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    ingredient_data_status: IngredientDataStatus = IngredientDataStatus.PARTIAL
    restaurant_ids: List[str] = Field(default_factory=list)
    ingredient_ids: List[str] = Field(default_factory=list)
    may_contain_allergen_ids: List[str] = Field(default_factory=list)

class DishUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    vegetarian: Optional[bool] = None
    vegan: Optional[bool] = None
    preparation_notes: Optional[str] = None
    availability_status: Optional[AvailabilityStatus] = None
    ingredient_data_status: Optional[IngredientDataStatus] = None
    restaurant_ids: Optional[List[str]] = None
    ingredient_ids: Optional[List[str]] = None
    may_contain_allergen_ids: Optional[List[str]] = None

class DishResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "Main Course"
    price: float = 0.0
    vegetarian: bool = False
    vegan: bool = False
    preparation_notes: str = ""
    availability_status: str = "AVAILABLE"
    ingredient_data_status: str = "PARTIAL"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    restaurants: List[Dict[str, Any]] = Field(default_factory=list)
    ingredients: List[Dict[str, Any]] = Field(default_factory=list)
    allergens: List[Dict[str, Any]] = Field(default_factory=list)
    may_contain_allergens: List[Dict[str, Any]] = Field(default_factory=list)

# --- Allergy Checker Schemas ---
class MatchMode(str, Enum):
    ANY = "ANY"
    ALL = "ALL"

class AllergyCheckRequest(BaseModel):
    allergen_ids: List[str] = Field(..., min_length=1)
    match_mode: MatchMode = MatchMode.ANY
    restaurant_id: Optional[str] = None
    city: Optional[str] = None
    category: Optional[str] = None

class MatchedIngredientInfo(BaseModel):
    ingredient_id: str
    ingredient_name: str
    allergen_id: str
    allergen_name: str
    verification_status: str
    source_reference: str = ""

class DishAllergyResult(BaseModel):
    dish_id: str
    dish_name: str
    dish_category: str
    price: float
    vegetarian: bool
    vegan: bool
    ingredient_data_status: str
    restaurant_id: str
    restaurant_name: str
    city: str
    has_allergen_match: bool
    matched_allergens: List[str]
    matched_ingredients: List[MatchedIngredientInfo]
    may_contain_allergens: List[str]
    missing_ingredient_info: bool
    safety_summary: str

# --- Graph Schemas ---
class GraphNode(BaseModel):
    id: str
    label: str  # Restaurant, Dish, Ingredient, Allergen
    name: str
    category: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str  # OFFERS, CONTAINS, CONTAINS_ALLERGEN, MAY_CONTAIN
    data: Dict[str, Any] = Field(default_factory=dict)

class GraphDataResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

# --- Activity Log Schema ---
class ActivityLogResponse(BaseModel):
    id: str
    actor_id: str
    actor_name: str
    action: str
    entity_type: str
    entity_id: str
    description: str
    timestamp: str
