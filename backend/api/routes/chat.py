"""
Chat API routes.

Handles chat message endpoints with conversation history persistence and caching.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
import pandas as pd

from backend.api.deps import get_db
from backend.schemas.chat import ChatMessageRequest, ChatMessageResponse
from backend.db.models import Dataset, Conversation, Message
from backend.services.chat_service import run_langgraph_chat, create_data_context


router = APIRouter()


def get_anthropic_api_key(
    x_anthropic_api_key: Optional[str] = Header(None, alias="X-Anthropic-API-Key")
) -> str:
    """
    Extract Anthropic API key from request header.

    Args:
        x_anthropic_api_key: API key from X-Anthropic-API-Key header

    Returns:
        API key string

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_anthropic_api_key:
        raise HTTPException(
            status_code=401,
            detail="Anthropic API key is required. Provide it in X-Anthropic-API-Key header."
        )

    # Basic validation (Anthropic keys start with "sk-ant-")
    if not x_anthropic_api_key.startswith("sk-"):
        raise HTTPException(
            status_code=401,
            detail="Invalid Anthropic API key format. Keys should start with 'sk-'."
        )

    if len(x_anthropic_api_key) < 20:
        raise HTTPException(
            status_code=401,
            detail="Invalid Anthropic API key. Key is too short."
        )

    return x_anthropic_api_key


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_anthropic_api_key)
):
    """
    Send a chat message and get AI response.

    This endpoint:
    1. Checks cache for repeated questions
    2. Loads dataset from database if dataset_id provided
    3. Loads or creates conversation
    4. Invokes LangGraph chatbot with tools
    5. Persists user and assistant messages
    6. Returns response with cache_hit indicator

    Args:
        request: Chat message request
        db: Database session
        api_key: Anthropic API key from header

    Returns:
        ChatMessageResponse with assistant's reply

    Raises:
        HTTPException: If dataset not found, API key invalid, or LLM error
    """
    try:
        # Load dataset if dataset_id provided
        df = None
        dataset_name = "general"
        dataset_id = request.dataset_id

        if dataset_id:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

            if not dataset:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset with ID {dataset_id} not found."
                )

            # Load dataset file
            try:
                df = pd.read_csv(dataset.file_path, encoding='utf-8')
                dataset_name = dataset.name
            except FileNotFoundError:
                raise HTTPException(
                    status_code=404,
                    detail=f"Dataset file not found: {dataset.file_path}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load dataset: {str(e)}"
                )

        # Create data context
        if df is not None:
            data_context = create_data_context(df, dataset_name)
        else:
            data_context = "데이터셋이 로드되지 않았습니다. 일반 질문에 답변할 수 있습니다."

        # Load or create conversation
        conversation = None
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id
            ).first()

            if not conversation:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation with ID {request.conversation_id} not found."
                )
        else:
            # Create new conversation
            conversation = Conversation(
                dataset_id=dataset_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(conversation)
            db.flush()  # Get conversation.id without committing

        # Load conversation history
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.asc()).all()

        # Convert to chat format
        chat_messages = []
        for msg in messages:
            chat_messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        chat_messages.append({
            "role": "user",
            "content": request.message
        })

        # Save user message to database
        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=request.message,
            tool_calls=None,
            created_at=datetime.utcnow()
        )
        db.add(user_message)

        # Invoke chatbot
        response_text, usage_info, cache_hit = run_langgraph_chat(
            api_key=api_key,
            model="claude-sonnet-4-20250514",
            messages=chat_messages,
            data_context=data_context,
            df=df,
            dataset_name=dataset_name,
            dataset_id=dataset_id
        )

        # Save assistant message to database
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=response_text,
            tool_calls=None,
            created_at=datetime.utcnow()
        )
        db.add(assistant_message)

        # Update conversation updated_at
        conversation.updated_at = datetime.utcnow()

        # Commit all changes
        db.commit()
        db.refresh(assistant_message)

        # Return response
        return ChatMessageResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            content=response_text,
            cache_hit=cache_hit,
            timestamp=assistant_message.created_at,
            usage=usage_info if not cache_hit else None
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Chat service error: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all messages in a conversation.

    Args:
        conversation_id: ID of the conversation
        db: Database session

    Returns:
        List of messages with role, content, and timestamp

    Raises:
        HTTPException: If conversation not found
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=f"Conversation with ID {conversation_id} not found."
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()

    return {
        "conversation_id": conversation_id,
        "dataset_id": conversation.dataset_id,
        "title": conversation.title,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
    }


@router.get("/conversations")
async def list_conversations(
    dataset_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List conversations, optionally filtered by dataset.

    Args:
        dataset_id: Optional dataset ID to filter by
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        db: Database session

    Returns:
        List of conversations with metadata
    """
    query = db.query(Conversation)

    if dataset_id:
        query = query.filter(Conversation.dataset_id == dataset_id)

    conversations = query.order_by(
        Conversation.updated_at.desc()
    ).limit(limit).offset(offset).all()

    return {
        "conversations": [
            {
                "id": conv.id,
                "dataset_id": conv.dataset_id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
            }
            for conv in conversations
        ],
        "limit": limit,
        "offset": offset
    }
