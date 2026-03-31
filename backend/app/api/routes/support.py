"""Support ticket system routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_superadmin
from app.core.time import utc_now_naive
from app.models.support import FAQArticle, SupportTicket, TicketMessage
from app.models.user import User
from app.schemas.support import (
    FAQCreate, FAQOut, TicketCreate, TicketMessageCreate,
    TicketMessageOut, TicketOut, TicketRating, TicketUpdate,
)

router = APIRouter(prefix="/support", tags=["support"])


# ── Tickets ──────────────────────────────────────────────────────

@router.post("/tickets", response_model=TicketOut)
def create_ticket(
    body: TicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = SupportTicket(
        org_id=body.org_id,
        user_id=user.id,
        category=body.category,
        priority=body.priority,
        subject=body.subject,
        description=body.description,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets")
def list_my_tickets(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(SupportTicket).filter(SupportTicket.user_id == user.id)
    if status:
        q = q.filter(SupportTicket.status == status)
    total = q.count()
    tickets = q.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [TicketOut.model_validate(t) for t in tickets], "total": total}


@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if ticket.user_id != user.id and not user.is_superadmin:
        raise HTTPException(403, "Access denied")
    return ticket


@router.post("/tickets/{ticket_id}/messages", response_model=TicketMessageOut)
def add_message(
    ticket_id: str,
    body: TicketMessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if ticket.user_id != user.id and not user.is_superadmin:
        raise HTTPException(403, "Access denied")

    msg = TicketMessage(
        ticket_id=ticket_id,
        sender_id=user.id,
        message=body.message,
        is_internal=body.is_internal and user.is_superadmin,
    )
    db.add(msg)

    if ticket.user_id == user.id:
        ticket.status = "waiting_for_support"
    else:
        ticket.status = "waiting_for_user"
    ticket.updated_at = utc_now_naive()
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/tickets/{ticket_id}/messages")
def list_messages(
    ticket_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if ticket.user_id != user.id and not user.is_superadmin:
        raise HTTPException(403, "Access denied")

    msgs = (
        db.query(TicketMessage)
        .filter(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at.asc())
        .all()
    )
    if not user.is_superadmin:
        msgs = [m for m in msgs if not m.is_internal]
    return [TicketMessageOut.model_validate(m) for m in msgs]


@router.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: str,
    body: TicketUpdate,
    user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    if body.status:
        ticket.status = body.status
        if body.status == "resolved":
            ticket.resolved_at = utc_now_naive()
        elif body.status == "closed":
            ticket.closed_at = utc_now_naive()
    if body.priority:
        ticket.priority = body.priority
    if body.resolution:
        ticket.resolution = body.resolution
    ticket.updated_at = utc_now_naive()
    db.commit()
    return {"status": ticket.status}


@router.post("/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: str,
    agent_id: str,
    user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    ticket.assigned_to = agent_id
    ticket.status = "in_progress"
    ticket.updated_at = utc_now_naive()
    db.commit()
    return {"status": "assigned"}


@router.post("/tickets/{ticket_id}/rate")
def rate_ticket(
    ticket_id: str,
    body: TicketRating,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket or ticket.user_id != user.id:
        raise HTTPException(404, "Ticket not found")
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(400, "Rating must be 1-5")
    ticket.satisfaction_rating = body.rating
    db.commit()
    return {"status": "rated"}


# ── FAQ ──────────────────────────────────────────────────────────

@router.get("/faq")
def list_faq(
    category: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(FAQArticle).filter(FAQArticle.is_published == True)
    if category:
        query = query.filter(FAQArticle.category == category)
    if q:
        query = query.filter(
            (FAQArticle.title.ilike(f"%{q}%")) | (FAQArticle.content.ilike(f"%{q}%"))
        )
    articles = query.order_by(FAQArticle.helpful_count.desc()).all()
    return [FAQOut.model_validate(a) for a in articles]


@router.get("/faq/{faq_id}", response_model=FAQOut)
def get_faq(faq_id: str, db: Session = Depends(get_db)):
    article = db.get(FAQArticle, faq_id)
    if not article or not article.is_published:
        raise HTTPException(404, "Article not found")
    article.views_count += 1
    db.commit()
    return article


@router.post("/faq/{faq_id}/helpful")
def mark_faq_helpful(faq_id: str, db: Session = Depends(get_db)):
    article = db.get(FAQArticle, faq_id)
    if not article:
        raise HTTPException(404, "Article not found")
    article.helpful_count += 1
    db.commit()
    return {"helpful_count": article.helpful_count}


# ── Admin support endpoints ──────────────────────────────────────

@router.get("/admin/tickets")
def list_all_tickets(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    priority: str | None = None,
    user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    q = db.query(SupportTicket)
    if status:
        q = q.filter(SupportTicket.status == status)
    if priority:
        q = q.filter(SupportTicket.priority == priority)
    total = q.count()
    tickets = q.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [TicketOut.model_validate(t) for t in tickets], "total": total}


@router.get("/admin/stats")
def support_stats(
    user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    open_count = db.query(SupportTicket).filter(SupportTicket.status == "open").count()
    in_progress = db.query(SupportTicket).filter(SupportTicket.status == "in_progress").count()
    resolved = db.query(SupportTicket).filter(SupportTicket.status == "resolved").count()
    total = db.query(SupportTicket).count()

    from sqlalchemy import func
    avg_rating = db.query(func.avg(SupportTicket.satisfaction_rating)).filter(
        SupportTicket.satisfaction_rating.isnot(None)
    ).scalar()

    return {
        "total_tickets": total,
        "open": open_count,
        "in_progress": in_progress,
        "resolved": resolved,
        "avg_satisfaction": round(float(avg_rating), 2) if avg_rating else None,
    }


@router.post("/admin/faq", response_model=FAQOut)
def create_faq(
    body: FAQCreate,
    user: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    article = FAQArticle(
        category=body.category,
        title=body.title,
        content=body.content,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article
