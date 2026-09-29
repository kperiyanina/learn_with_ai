from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ai import generate_ai_plan
from api_auth import create_access_token, get_user_id_from_token
from database import (
    authenticate_user,
    get_all_plans,
    get_plan_progress,
    get_plan_tasks,
    get_profile,
    init_database,
    register_user,
    save_plan,
    update_profile,
    update_task_status,
)
from models import PlanRequest


init_database()
app = FastAPI(
    title="LearnWithAI API",
    version="1.0.0",
    description="REST API для планов обучения LearnWithAI.",
)
security = HTTPBearer(auto_error=False)


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


def current_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security),
    ],
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется токен доступа.",
        )
    try:
        return get_user_id_from_token(credentials.credentials)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error


UserId = Annotated[int, Depends(current_user_id)]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(credentials: Credentials) -> TokenResponse:
    try:
        user = register_user(credentials.email, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: Credentials) -> TokenResponse:
    try:
        user = authenticate_user(credentials.email, credentials.password)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/users/me", response_model=ProfileResponse)
def get_current_profile(user_id: UserId) -> ProfileResponse:
    try:
        profile = get_profile(user_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
    )


@app.patch("/users/me", response_model=ProfileResponse)
def edit_current_profile(
    update: ProfileUpdate,
    user_id: UserId,
) -> ProfileResponse:
    try:
        update_profile(user_id, update.display_name)
        profile = get_profile(user_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ProfileResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
    )


@app.get("/plans", response_model=list[PlanResponse])
def list_plans(user_id: UserId) -> list[PlanResponse]:
    return [PlanResponse(**plan.__dict__) for plan in get_all_plans(user_id)]


@app.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, user_id: UserId) -> PlanResponse:
    plan = next(
        (plan for plan in get_all_plans(user_id) if plan.id == plan_id),
        None,
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="План не найден.")
    return PlanResponse(**plan.__dict__)


@app.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(plan_input: PlanCreate, user_id: UserId) -> PlanResponse:
    try:
        request = PlanRequest(**plan_input.model_dump())
        plan = generate_ai_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
        )
        plan_id = save_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
            plan,
            user_id=user_id,
        )
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return PlanResponse(
        id=plan_id,
        goal=request.goal,
        level=request.level,
        weeks=request.weeks,
        hours_per_week=request.hours_per_week,
    )


@app.get("/plans/{plan_id}/tasks", response_model=list[TaskResponse])
def list_tasks(plan_id: int, user_id: UserId) -> list[TaskResponse]:
    tasks = get_plan_tasks(plan_id, user_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="План или задачи не найдены.")
    return [TaskResponse(**task.__dict__) for task in tasks]


@app.get("/plans/{plan_id}/progress", response_model=ProgressResponse)
def plan_progress(plan_id: int, user_id: UserId) -> ProgressResponse:
    tasks = get_plan_tasks(plan_id, user_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="План или задачи не найдены.")
    return ProgressResponse(progress=get_plan_progress(plan_id, user_id))


@app.patch("/tasks/{task_id}", response_model=TaskResponse)
def edit_task(
    task_id: int,
    update: TaskUpdate,
    user_id: UserId,
) -> TaskResponse:
    matching_tasks = [
        task
        for plan in get_all_plans(user_id)
        for task in get_plan_tasks(plan.id, user_id)
        if task.id == task_id
    ]
    if not matching_tasks:
        raise HTTPException(status_code=404, detail="Задача не найдена.")

    update_task_status(task_id, update.completed, user_id)
    updated_task = next(
        task
        for plan in get_all_plans(user_id)
        for task in get_plan_tasks(plan.id, user_id)
        if task.id == task_id
    )
    return TaskResponse(**updated_task.__dict__)
