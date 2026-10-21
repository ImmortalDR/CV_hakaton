"""Addressed employer tasks. Separate from professional grade and contact grants."""
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select, func

from .models import TaskPlan, TaskAssignment, Profile, ContactGrant, Company, now
from .schemas import Input
from .outputs import Output


def fail(code, detail):
    raise HTTPException(code, detail)


class PlanInput(Input):
    candidate_id: UUID
    request_id: UUID
    title: str = Field(min_length=3, max_length=160)
    prompt: str = Field(min_length=20, max_length=4000)
    rubric: str = Field(min_length=10, max_length=2000)
    interval_days: int = Field(ge=1, le=365, strict=True)
    response_days: int = Field(ge=1, le=365, strict=True)

    @model_validator(mode="after")
    def deadline(self):
        if self.response_days > self.interval_days:
            raise ValueError("Срок ответа не должен превышать период выдачи")
        return self


class PlanDecision(Input):
    status: Literal["active", "paused", "closed"]


class TaskAnswer(Input):
    answer: str = Field(min_length=1, max_length=6000)


class TaskReview(Input):
    score: int = Field(ge=0, le=100, strict=True)
    feedback: str = Field(min_length=10, max_length=2000)


class AssignmentView(Output):
    id: str
    sequence: int
    version: int
    title: str
    prompt: str
    rubric: str
    status: str
    created_at: datetime
    due_at: datetime
    answer: str | None
    submitted_at: datetime | None
    score: int | None
    feedback: str | None
    reviewed_at: datetime | None


class PlanView(Output):
    id: str
    candidate_id: str
    candidate_name: str
    company_name: str
    title: str
    prompt: str
    rubric: str
    interval_days: int
    response_days: int
    version: int
    status: str
    next_issue_at: datetime | None
    consent_at: datetime | None
    access_available: bool
    assignments: list[AssignmentView]


class TaskInbox(Output):
    plans: list[PlanView]
    pending: int
    last_reviewed_at: datetime | None


def permitted(db, plan, profile):
    return bool(profile and profile.processing and profile.published and
                db.get(ContactGrant, (plan.candidate_id, plan.company_id)))


def suspend(db, candidate_id):
    """Caller holds Profile lock; consent never silently returns on republication."""
    for plan in db.scalars(select(TaskPlan).where(TaskPlan.candidate_id == candidate_id).with_for_update()):
        if plan.status != "closed":
            plan.status = "paused"
        for a in db.scalars(select(TaskAssignment).where(TaskAssignment.plan_id == plan.id, TaskAssignment.status.in_(["issued", "viewed"]))):
            a.status = "cancelled"


def tick_plan(db, plan, profile, at):
    """Profile then Plan are locked by every writer; sequence stays unique."""
    if not permitted(db, plan, profile):
        if plan.status != "closed":
            plan.status = "paused"
        for a in db.scalars(select(TaskAssignment).where(TaskAssignment.plan_id == plan.id, TaskAssignment.status.in_(["issued", "viewed"]))):
            a.status = "cancelled"
        return
    assignments = list(db.scalars(select(TaskAssignment).where(TaskAssignment.plan_id == plan.id)))
    for a in assignments:
        if a.status in ("issued", "viewed") and a.due_at <= at:
            a.status = "expired"
    if plan.status != "active" or not plan.next_issue_at or plan.next_issue_at > at:
        return
    if any(a.status in ("issued", "viewed", "submitted") for a in assignments):
        return  # Do not pile up unanswered tasks or unreviewed work.
    db.add(TaskAssignment(plan_id=plan.id, sequence=max((a.sequence for a in assignments), default=0)+1,
                          version=plan.version, title=plan.title, prompt=plan.prompt, rubric=plan.rubric,
                          created_at=at, due_at=at+timedelta(days=plan.response_days)))
    plan.next_issue_at = at + timedelta(days=plan.interval_days)


def run_due(factory, at=None):
    """May run concurrently. One transaction/plan, no backlog burst after downtime."""
    at = at or now()
    with factory() as db:
        ids = list(db.execute(select(TaskPlan.id, TaskPlan.candidate_id).where(TaskPlan.status == "active")).all())
    for pid, cid in ids:
        with factory.begin() as db:
            from .demo_idle import lock
            lock(db)
            profile = db.scalar(select(Profile).where(Profile.user_id == cid).with_for_update())
            plan = db.scalar(select(TaskPlan).where(TaskPlan.id == pid).with_for_update())
            if plan is not None:
                tick_plan(db, plan, profile, at)
    return len(ids)


def install_routes(app, AUTH, DB, candidate, company):
    def load_plan(pid, user, db):
        plan = db.get(TaskPlan, pid)
        if not plan:
            fail(404, "План заданий не найден")
        if user.role == "candidate":
            if plan.candidate_id != user.id:
                fail(404, "План заданий не найден")
        elif company(user, db).id != plan.company_id:
            fail(404, "План заданий не найден")
        profile = db.scalar(select(Profile).where(Profile.user_id == plan.candidate_id).with_for_update())
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == pid).with_for_update().execution_options(populate_existing=True))
        if not permitted(db, plan, profile):
            fail(403, "Нужно действующее согласие на контакты после принятия приглашения и публикация профиля")
        return plan, profile

    def view(db, plan, user, at):
        profile = db.get(Profile, plan.candidate_id)
        access = permitted(db, plan, profile)
        rows = list(db.scalars(select(TaskAssignment).where(TaskAssignment.plan_id == plan.id).order_by(TaskAssignment.sequence.desc())))
        return dict(id=plan.id, candidate_id=plan.candidate_id,
                    candidate_name=profile.name if access or user.id == plan.candidate_id else "Кандидат снял публикацию",
                    company_name=db.get(Company, plan.company_id).name,
                    **{k:getattr(plan,k) for k in ["title","prompt","rubric","interval_days","response_days","version","status","next_issue_at","consent_at"]},
                    access_available=access, assignments=[dict(
                        **{k:getattr(a,k) for k in AssignmentView.model_fields if k != "status"},
                        status="expired" if a.status in ("issued","viewed") and a.due_at <= at else a.status
                    ) for a in rows] if access or user.id == plan.candidate_id else [])

    @app.get("/api/tasks", response_model=TaskInbox, tags=["Задания работодателей"])
    def inbox(user: AUTH, db: DB):
        clause = TaskPlan.candidate_id == user.id if user.role == "candidate" else TaskPlan.company_id == company(user,db).id
        plans = [view(db,p,user,now()) for p in db.scalars(select(TaskPlan).where(clause).order_by(TaskPlan.created_at.desc()))]
        pending = sum((p["status"] == "awaiting") + sum(a["status"] in ("issued","viewed") for a in p["assignments"]) for p in plans if p["access_available"]) if user.role == "candidate" else sum(a["status"] == "submitted" for p in plans for a in p["assignments"])
        dates = [a["reviewed_at"] for p in plans for a in p["assignments"] if a["reviewed_at"]]
        return dict(plans=plans, pending=pending, last_reviewed_at=max(dates) if dates else None)

    @app.post("/api/tasks/plans", response_model=PlanView, status_code=201, tags=["Задания работодателей"])
    def create_plan(data: PlanInput, user: AUTH, db: DB):
        co = company(user,db,True)
        profile = db.scalar(select(Profile).where(Profile.user_id == str(data.candidate_id)).with_for_update())
        values = data.model_dump(mode="json")
        previous = db.scalar(select(TaskPlan).where(TaskPlan.company_id == co.id, TaskPlan.request_id == str(data.request_id)))
        if previous:
            if any(getattr(previous,k) != v for k,v in values.items()):
                fail(409,"Повторный запрос содержит другие условия")
            if not permitted(db,previous,profile):
                fail(403,"Согласие на контакты отозвано")
            return view(db,previous,user,now())
        plan = TaskPlan(company_id=co.id, **values)
        if not permitted(db,plan,profile):
            fail(403,"Предлагать задания можно после принятия приглашения и при действующей публикации")
        if db.scalar(select(TaskPlan.id).where(TaskPlan.company_id == co.id, TaskPlan.candidate_id == profile.user_id, TaskPlan.status != "closed")):
            fail(409,"Для этого кандидата уже есть план. Закройте его перед созданием нового")
        db.add(plan); db.flush()
        return view(db,plan,user,now())

    @app.patch("/api/tasks/plans/{pid}", response_model=PlanView, tags=["Задания работодателей"])
    def change_plan(pid: str, data: PlanDecision, user: AUTH, db: DB):
        plan, profile = load_plan(pid,user,db)
        if user.role == "employer" and data.status != "closed":
            fail(403,"Согласие на выдачу заданий меняет только кандидат")
        if plan.status == "closed" and data.status != "closed":
            fail(409,"План закрыт. Для новых условий нужен новый план и согласие")
        if plan.status != data.status:
            plan.status = data.status
            if data.status == "active":
                # Recover the cadence even for plans paused by older releases,
                # which cleared next_issue_at. Cancelled issues consume a period.
                last_issue = db.scalar(select(func.max(TaskAssignment.created_at)).where(TaskAssignment.plan_id == pid))
                earliest = last_issue + timedelta(days=plan.interval_days) if last_issue else now()
                plan.next_issue_at = max(plan.next_issue_at, earliest) if plan.next_issue_at else earliest
                plan.consent_at = now()
            elif data.status == "closed":
                plan.next_issue_at = None
            if data.status != "active":
                for a in db.scalars(select(TaskAssignment).where(TaskAssignment.plan_id == pid, TaskAssignment.status.in_(["issued","viewed"]))):
                    a.status = "cancelled"
        tick_plan(db,plan,profile,now());db.flush()
        return view(db,plan,user,now())

    def assignment(aid,user,db):
        a = db.get(TaskAssignment,aid)
        if not a: fail(404,"Задание не найдено")
        plan,profile = load_plan(a.plan_id,user,db)
        db.refresh(a)  # Another request may have submitted/reviewed while waiting for Profile.
        return a,plan,profile

    @app.post("/api/tasks/assignments/{aid}/answer", response_model=PlanView, tags=["Задания работодателей"])
    def answer(aid: str, data: TaskAnswer, user: AUTH, db: DB):
        if user.role != "candidate": fail(403,"Ответ отправляет кандидат")
        a,plan,profile=assignment(aid,user,db)
        if a.status in ("submitted","reviewed"):
            if a.answer != data.answer: fail(409,"Ответ уже отправлен")
            return view(db,plan,user,now())
        if plan.status != "active" or a.status not in ("issued","viewed") or a.due_at <= now():
            fail(409,"Срок ответа истёк или выдача остановлена")
        a.answer, a.submitted_at, a.status = data.answer, now(), "submitted"
        db.flush();return view(db,plan,user,now())

    @app.post("/api/tasks/assignments/{aid}/review", response_model=PlanView, tags=["Задания работодателей"])
    def review(aid: str, data: TaskReview, user: AUTH, db: DB):
        if user.role != "employer": fail(403,"Оценку выставляет работодатель")
        a,plan,profile=assignment(aid,user,db)
        if a.status == "reviewed":
            if (a.score,a.feedback) != (data.score,data.feedback): fail(409,"Оценка уже сохранена")
            return view(db,plan,user,now())
        if a.status != "submitted": fail(409,"Сначала дождитесь ответа кандидата")
        a.score,a.feedback,a.reviewed_at,a.status=data.score,data.feedback,now(),"reviewed"
        db.flush();return view(db,plan,user,now())


def last_reviewed(db, candidate_id, company_id=None):
    stmt = select(func.max(TaskAssignment.reviewed_at)).join(TaskPlan).where(TaskPlan.candidate_id == candidate_id)
    if company_id: stmt = stmt.where(TaskPlan.company_id == company_id)
    return db.scalar(stmt)
