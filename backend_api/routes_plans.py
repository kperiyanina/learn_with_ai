from fastapi import APIRouter, HTTPException

from backend_api.dependencies import UserId
from backend_api.schemas import (
    PlanCreate,
    PlanResponse,
    ProgressResponse,
    TaskResponse,
    TaskUpdate,
)
from core.models import PlanRequest
from services.ai import generate_ai_plan
from storage.database import (
    get_all_plans,
    get_plan_progress,
    get_plan_tasks,
    save_plan,
    update_task_status,
)


router = APIRouter()


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(user_id: UserId) -> list[PlanResponse]:
    return [PlanResponse(**plan.__dict__) for plan in get_all_plans(user_id)]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, user_id: UserId) -> PlanResponse:
    plan = next(
        (plan for plan in get_all_plans(user_id) if plan.id == plan_id),
        None,
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="План не найден.")
    return PlanResponse(**plan.__dict__)


@router.post("/plans", response_model=PlanResponse, status_code=201)
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


@router.get("/plans/{plan_id}/tasks", response_model=list[TaskResponse])
def list_tasks(plan_id: int, user_id: UserId) -> list[TaskResponse]:
    tasks = get_plan_tasks(plan_id, user_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="План или задачи не найдены.")
    return [TaskResponse(**task.__dict__) for task in tasks]


@router.get("/plans/{plan_id}/progress", response_model=ProgressResponse)
def plan_progress(plan_id: int, user_id: UserId) -> ProgressResponse:
    tasks = get_plan_tasks(plan_id, user_id)
    if not tasks:
        raise HTTPException(status_code=404, detail="План или задачи не найдены.")
    return ProgressResponse(progress=get_plan_progress(plan_id, user_id))


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
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
