"""Phase 6A: request/response schemas for the knowledge ask endpoints.

The retrieval tier is caller-determined, never caller-supplied (§10 of
14-rag-ingestion-architecture.md): the public request carries an `index`
field only so clients that name a tier get an explicit rejection instead of
silent widening — the router still queries the literal 'public' index.
"""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

QUESTION_MAX_LENGTH = 2000


class KnowledgeQuestion(BaseModel):
    question: str = Field(max_length=QUESTION_MAX_LENGTH)

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Question cannot be empty")
        return s


class KnowledgeAskRequest(KnowledgeQuestion):
    # Literal keeps arbitrary tier names out at validation time; the router
    # additionally rejects 'cx' on the public route with 403.
    index: Literal["public", "cx"] = "public"


class KnowledgeSource(BaseModel):
    doc_path: str
    title: str
    source_decisions: list[str]


class KnowledgeAskResponse(BaseModel):
    outcome: Literal["answered", "refused"]
    answer: str
    # Null on every refusal: naming the matched golden case would confirm a
    # recognized leak probe exists (and some probe slugs name the deny-listed
    # decision).
    matched_case_slug: str | None
    sources: list[KnowledgeSource]
    retrieval_count: int
