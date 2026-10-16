from fastapi import APIRouter, HTTPException

from backend_api.dependencies import UserId
from backend_api.schemas import (
    PlanCreate,
    MaterialResponse,
    MaterialUpdate,
    MaterialRecommendationRequest,
    MaterialAvailabilityResponse,
    MaterialAvailabilityRequest,
    PlanResponse,
    ProgressResponse,
    TaskResponse,
    TaskUpdate,
)
from core.models import LearningDiagnostic, PlanRequest
from services.ai import generate_ai_plan
from storage.database import (
    get_all_plans,
    get_plan_progress,
    get_plan_tasks,
    get_plan_materials,
    update_material_status,
    save_plan,
    update_task_status,
)
from services.materials import check_material_url, recommend_materials


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
        request = PlanRequest(
            goal=plan_input.goal,
            level=plan_input.level,
            weeks=plan_input.weeks,
            hours_per_week=plan_input.hours_per_week,
        )
        diagnostic = LearningDiagnostic(
            interests=plan_input.interests,
            preferred_format=plan_input.preferred_format,
            available_days=tuple(plan_input.available_days),
        )
        plan = generate_ai_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
            diagnostic,
        )
        plan_id = save_plan(
            request.goal,
            request.level,
            request.weeks,
            request.hours_per_week,
            plan,
            user_id=user_id,
            diagnostic=diagnostic,
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


@router.get(
    "/plans/{plan_id}/materials",
    response_model=list[MaterialResponse],
)
def list_materials(plan_id: int, user_id: UserId) -> list[MaterialResponse]:
    plans = get_all_plans(user_id)
    if not any(plan.id == plan_id for plan in plans):
        raise HTTPException(status_code=404, detail="План не найден.")
    materials = get_plan_materials(plan_id, user_id)
    return [MaterialResponse(**material.__dict__) for material in materials]


@router.patch("/materials/{material_id}", response_model=MaterialResponse)
def edit_material(
    material_id: int,
    update: MaterialUpdate,
    user_id: UserId,
) -> MaterialResponse:
    try:
        update_material_status(
            material_id,
            completed=update.completed,
            is_favorite=update.is_favorite,
            user_id=user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    material = next(
        (
            item
            for plan in get_all_plans(user_id)
            for item in get_plan_materials(plan.id, user_id)
            if item.id == material_id
        ),
        None,
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Материал не найден.")
    return MaterialResponse(**material.__dict__)


@router.post(
    "/plans/{plan_id}/material-recommendations",
    response_model=list[dict[str, str]],
)
def material_recommendations(
    plan_id: int,
    request: MaterialRecommendationRequest,
    user_id: UserId,
) -> list[dict[str, str]]:
    plan = next(
        (item for item in get_all_plans(user_id) if item.id == plan_id),
        None,
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="План не найден.")
    return recommend_materials(
        plan.goal,
        plan.level,
        request.topic,
        plan.hours_per_week,
    )


@router.post(
    "/materials/check-availability",
    response_model=MaterialAvailabilityResponse,
)
def material_availability(
    material_input: MaterialAvailabilityRequest,
    user_id: UserId,
) -> MaterialAvailabilityResponse:
    del user_id
    available, message = check_material_url(material_input.url)
    return MaterialAvailabilityResponse(available=available, message=message)


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
