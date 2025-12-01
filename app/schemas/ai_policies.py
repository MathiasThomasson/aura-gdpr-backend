from enum import Enum
from pydantic import BaseModel, field_validator


class PolicyType(str, Enum):
    privacy_policy = "privacy_policy"
    cookie_policy = "cookie_policy"
    data_processing_agreement = "data_processing_agreement"
    data_retention_policy = "data_retention_policy"
    information_security_policy = "information_security_policy"
    internal_guideline = "internal_guideline"


class PolicyGenerateRequest(BaseModel):
    policy_type: PolicyType
    context_description: str | None = None
    language: str = "en"

    @field_validator("language")
    @classmethod
    def enforce_en(cls, v: str) -> str:
        if v and v.lower() != "en":
            raise ValueError("Only English is supported for now")
        return "en"


class PolicyGenerateResponse(BaseModel):
    title: str
    summary: str
    content: str
