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
