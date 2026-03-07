"""Structured artifact schemas for generated application content."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ArtifactStyle(str, Enum):
    formal = "formal"
    concise = "concise"
    confident = "confident"


class DocumentHeader(BaseModel):
    applicant_name: str = ""
    applicant_email: str = ""
    applicant_phone: str = ""
    applicant_location: str = ""


class ParagraphBlock(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    style: ArtifactStyle = ArtifactStyle.formal

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split()).strip()


class SignatureBlock(BaseModel):
    signoff: str = Field(min_length=1, max_length=40)
    include_name: bool = False


class ArtifactMetadata(BaseModel):
    content_type: str
    company_name: str = ""
    job_title: str = ""


class CoverLetterArtifact(BaseModel):
    header: DocumentHeader = Field(default_factory=DocumentHeader)
    greeting: str = Field(min_length=1, max_length=120)
    opening: ParagraphBlock
    body: List[ParagraphBlock] = Field(min_length=1, max_length=3)
    closing: ParagraphBlock
    signature: SignatureBlock = Field(default_factory=lambda: SignatureBlock(signoff="Sincerely,"))
    metadata: ArtifactMetadata

    @model_validator(mode="after")
    def validate_lengths(self) -> "CoverLetterArtifact":
        total_words = len(self.to_plain_text().split())
        if total_words > 380:
            raise ValueError("Cover letter exceeds 380 words")
        return self

    def to_plain_text(self) -> str:
        paragraphs = [self.greeting, self.opening.text]
        paragraphs.extend(block.text for block in self.body)
        paragraphs.append(self.closing.text)
        paragraphs.append(self.signature.signoff)
        return "\n\n".join(part for part in paragraphs if part)


class EmailArtifact(BaseModel):
    header: DocumentHeader = Field(default_factory=DocumentHeader)
    subject: str = Field(min_length=1, max_length=120)
    greeting: str = Field(min_length=1, max_length=120)
    body: List[ParagraphBlock] = Field(min_length=1, max_length=4)
    call_to_action: ParagraphBlock
    signature: SignatureBlock = Field(default_factory=lambda: SignatureBlock(signoff="Best,"))
    metadata: ArtifactMetadata

    @model_validator(mode="after")
    def validate_lengths(self) -> "EmailArtifact":
        total_words = len(self.to_plain_text().split())
        if total_words > 240:
            raise ValueError("Email exceeds 240 words")
        return self

    def to_plain_text(self) -> str:
        paragraphs = [self.greeting]
        paragraphs.extend(block.text for block in self.body)
        paragraphs.append(self.call_to_action.text)
        paragraphs.append(self.signature.signoff)
        return "\n\n".join(part for part in paragraphs if part)


class LinkedInMessageArtifact(BaseModel):
    body: str = Field(min_length=1, max_length=200)

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        return " ".join(value.split()).strip()
