from pydantic import BaseModel, Field


class OnboardingStateOut(BaseModel):
    onboarding_completed: bool
    onboarding_step: int = Field(ge=0)

    model_config = {"from_attributes": True}


class OnboardingStateUpdate(BaseModel):
    onboarding_completed: bool | None = None
    onboarding_step: int | None = Field(default=None, ge=0)
