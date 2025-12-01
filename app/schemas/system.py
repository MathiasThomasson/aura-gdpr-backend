from pydantic import BaseModel


class SystemVersion(BaseModel):
    version: str
    build: str
    timestamp: str
