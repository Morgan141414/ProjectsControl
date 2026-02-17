"""Vacancy and job application routes."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_org_membership, require_role
from app.core.time import utc_now_naive
from app.models.enums import OrgRole
from app.models.vacancy import Vacancy, VacancyApplication
from app.models.user import User
from app.schemas.vacancy import (
    ApplicationCreate, ApplicationOut, ApplicationUpdate,
    VacancyCreate, VacancyOut, VacancyUpdate,
)

router = APIRouter(tags=["vacancies"])


@router.post("/orgs/{org_id}/vacancies", response_model=VacancyOut)
def create_vacancy(
    org_id: str,
    body: VacancyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    vacancy = Vacancy(
        org_id=org_id,
        team_id=body.team_id,
        title=body.title,
        description=body.description,
        requirements=body.requirements,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_currency=body.salary_currency,
        experience_years=body.experience_years,
        skills_required_json=json.dumps(body.skills_required) if body.skills_required else None,
        employment_type=body.employment_type,
        created_by=user.id,
    )
    db.add(vacancy)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.get("/orgs/{org_id}/vacancies")
def list_org_vacancies(
    org_id: str,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Vacancy).filter(Vacancy.org_id == org_id)
    if active_only:
        q = q.filter(Vacancy.is_active == True)
    total = q.count()
    vacancies = q.order_by(Vacancy.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [VacancyOut.model_validate(v) for v in vacancies], "total": total}


@router.get("/vacancies/search")
def search_vacancies(
    q: str | None = None,
    employment_type: str | None = None,
    salary_min: int | None = None,
    experience_max: int | None = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Vacancy).filter(Vacancy.is_active == True)
    if q:
        query = query.filter(
            (Vacancy.title.ilike(f"%{q}%")) | (Vacancy.description.ilike(f"%{q}%"))
        )
    if employment_type:
        query = query.filter(Vacancy.employment_type == employment_type)
    if salary_min:
        query = query.filter(Vacancy.salary_max >= salary_min)
    if experience_max is not None:
        query = query.filter(Vacancy.experience_years <= experience_max)

    total = query.count()
    vacancies = query.order_by(Vacancy.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [VacancyOut.model_validate(v) for v in vacancies], "total": total}


@router.get("/vacancies/{vacancy_id}", response_model=VacancyOut)
def get_vacancy(
    vacancy_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(404, "Vacancy not found")
    vacancy.views_count += 1
    db.commit()
    return vacancy


@router.patch("/vacancies/{vacancy_id}", response_model=VacancyOut)
def update_vacancy(
    vacancy_id: str,
    body: VacancyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(404, "Vacancy not found")
    membership = get_org_membership(vacancy.org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "skills_required" and value is not None:
            vacancy.skills_required_json = json.dumps(value)
        elif hasattr(vacancy, field):
            setattr(vacancy, field, value)
    db.commit()
    db.refresh(vacancy)
    return vacancy


@router.post("/vacancies/{vacancy_id}/apply", response_model=ApplicationOut)
def apply_to_vacancy(
    vacancy_id: str,
    body: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy or not vacancy.is_active:
        raise HTTPException(404, "Vacancy not found or closed")

    existing = (
        db.query(VacancyApplication)
        .filter(VacancyApplication.vacancy_id == vacancy_id, VacancyApplication.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(409, "Already applied")

    app = VacancyApplication(
        vacancy_id=vacancy_id,
        user_id=user.id,
        cover_letter=body.cover_letter,
    )
    db.add(app)
    vacancy.applications_count += 1
    db.commit()
    db.refresh(app)
    return app


@router.get("/vacancies/{vacancy_id}/applications")
def list_applications(
    vacancy_id: str,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(404, "Vacancy not found")
    membership = get_org_membership(vacancy.org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    q = db.query(VacancyApplication).filter(VacancyApplication.vacancy_id == vacancy_id)
    if status:
        q = q.filter(VacancyApplication.status == status)
    total = q.count()
    apps = q.order_by(VacancyApplication.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [ApplicationOut.model_validate(a) for a in apps], "total": total}


@router.patch("/vacancies/{vacancy_id}/applications/{app_id}")
def update_application(
    vacancy_id: str,
    app_id: str,
    body: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vacancy = db.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(404, "Vacancy not found")
    membership = get_org_membership(vacancy.org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    application = db.get(VacancyApplication, app_id)
    if not application or application.vacancy_id != vacancy_id:
        raise HTTPException(404, "Application not found")

    application.status = body.status
    application.reviewed_by = user.id
    application.updated_at = utc_now_naive()
    db.commit()
    return {"status": application.status}


@router.get("/users/me/applications")
def my_applications(
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(VacancyApplication).filter(VacancyApplication.user_id == user.id)
    total = q.count()
    apps = q.order_by(VacancyApplication.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [ApplicationOut.model_validate(a) for a in apps], "total": total}
