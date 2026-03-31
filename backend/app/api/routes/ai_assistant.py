"""AI Company Assistant routes."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_org_membership, require_role
from app.core.time import utc_now_naive
from app.models.ai_assistant import AICompanyAssistant, AIConversation
from app.models.enums import OrgRole
from app.models.user import User
from app.schemas.ai_assistant import AIChatMessage, AIChatResponse, AIAssistantOut, AIAssistantSettings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-assistant"])


@router.post("/orgs/{org_id}/ai/assistant/chat", response_model=AIChatResponse)
def chat_with_assistant(
    org_id: str,
    body: AIChatMessage,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_org_membership(org_id, user, db)

    assistant = db.query(AICompanyAssistant).filter(AICompanyAssistant.org_id == org_id).first()
    if not assistant or not assistant.is_enabled:
        raise HTTPException(403, "AI Assistant is not enabled for this organization")

    if assistant.tokens_used_this_month >= assistant.monthly_tokens_limit:
        raise HTTPException(429, "Monthly AI token limit reached")

    try:
        import anthropic
        client = anthropic.Anthropic()

        context = json.loads(assistant.context_json) if assistant.context_json else {}
        system_prompt = (
            f"You are an AI assistant for the company. "
            f"Company context: {json.dumps(context)}. "
            f"User: {user.full_name}. "
            f"Answer questions about company processes, provide recommendations, and help with tasks."
        )

        response = client.messages.create(
            model=assistant.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": body.message}],
        )

        reply = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        assistant.tokens_used_this_month += tokens
        db.commit()

        return AIChatResponse(response=reply, tokens_used=tokens)
    except ImportError:
        logger.warning("anthropic package not available")
        return AIChatResponse(
            response="AI Assistant is temporarily unavailable. The anthropic package is not installed.",
            tokens_used=0,
        )
    except Exception as e:
        logger.error("AI Assistant error: %s", e)
        return AIChatResponse(
            response="AI Assistant encountered an error. Please try again later.",
            tokens_used=0,
        )


@router.get("/orgs/{org_id}/ai/assistant/conversations")
def list_conversations(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_org_membership(org_id, user, db)
    convs = (
        db.query(AIConversation)
        .filter(AIConversation.org_id == org_id, AIConversation.user_id == user.id)
        .order_by(AIConversation.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": c.id,
            "tokens_used": c.tokens_used,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in convs
    ]


@router.get("/orgs/{org_id}/ai/assistant/settings", response_model=AIAssistantOut)
def get_assistant_settings(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    assistant = db.query(AICompanyAssistant).filter(AICompanyAssistant.org_id == org_id).first()
    if not assistant:
        assistant = AICompanyAssistant(org_id=org_id)
        db.add(assistant)
        db.commit()
        db.refresh(assistant)
    return assistant


@router.patch("/orgs/{org_id}/ai/assistant/settings")
def update_assistant_settings(
    org_id: str,
    body: AIAssistantSettings,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    assistant = db.query(AICompanyAssistant).filter(AICompanyAssistant.org_id == org_id).first()
    if not assistant:
        assistant = AICompanyAssistant(org_id=org_id)
        db.add(assistant)

    if body.is_enabled is not None:
        assistant.is_enabled = body.is_enabled
    if body.model is not None:
        assistant.model = body.model
    if body.monthly_tokens_limit is not None:
        assistant.monthly_tokens_limit = body.monthly_tokens_limit
    db.commit()
    return {"status": "updated"}
