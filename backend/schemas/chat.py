"""
Chat API request/response schemas.

This module defines the Pydantic models for chat-related API endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""

    dataset_id: Optional[int] = Field(
        None,
        description="ID of the dataset to analyze. If None, uses current active dataset."
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User's message/question"
    )
    conversation_id: Optional[int] = Field(
        None,
        description="ID of existing conversation to continue. If None, creates new conversation."
    )


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""

    conversation_id: int = Field(
        ...,
        description="ID of the conversation"
    )
    message_id: int = Field(
        ...,
        description="ID of the assistant's message"
    )
    content: str = Field(
        ...,
        description="Assistant's response text"
    )
    cache_hit: bool = Field(
        False,
        description="Whether the response was retrieved from cache"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the response was generated"
    )
    usage: Optional[dict] = Field(
        None,
        description="Token usage information (input_tokens, output_tokens)"
    )
