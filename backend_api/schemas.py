from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileResponse(BaseModel):
    user_id: int
    display_name: str


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1)


class PlanCreate(BaseModel):
    goal: str
    level: str
    weeks: int
    hours_per_week: int
    interests: str = ""
    preferred_format: str = "Смешанный формат"
    available_days: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    id: int
    goal: str
    level: str
    weeks: int
    hours_per_week: int


class TaskResponse(BaseModel):
    id: int
    week: int
    topic: str
    task: str
    completed: bool


class TaskUpdate(BaseModel):
    completed: bool


class ProgressResponse(BaseModel):
    progress: float


class MaterialCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    url: str
    material_type: str
    tags: str = ""
    task_id: int | None = None
    week: int | None = None


class MaterialResponse(BaseModel):
    id: int
    plan_id: int
    task_id: int | None
    week: int | None
    title: str
    url: str
    material_type: str
    tags: str
    is_favorite: bool
    completed: bool


class MaterialUpdate(BaseModel):
    completed: bool | None = None
    is_favorite: bool | None = None


class MaterialRecommendationRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)


class MaterialAvailabilityResponse(BaseModel):
    available: bool
    message: str


class MaterialAvailabilityRequest(BaseModel):
    url: str
