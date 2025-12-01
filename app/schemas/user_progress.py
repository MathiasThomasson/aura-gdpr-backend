from pydantic import BaseModel


class UserProgressOut(BaseModel):
    created_first_dsr: bool = False
    created_first_policy: bool = False
    created_first_dpia: bool = False
    created_first_ropa: bool = False
    created_first_tom: bool = False
    ran_ai_audit: bool = False

    model_config = {"from_attributes": True}


class UserProgressUpdate(BaseModel):
    created_first_dsr: bool | None = None
    created_first_policy: bool | None = None
    created_first_dpia: bool | None = None
    created_first_ropa: bool | None = None
    created_first_tom: bool | None = None
    ran_ai_audit: bool | None = None
