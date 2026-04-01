from pydantic import BaseModel, Field
from typing import Literal, Annotated

class Flags(BaseModel):
    clause_type: str = Field(
        ...,
        description = "Identify the type of the risky clause"
    )
    issue: str = Field(
        ...,
        description = "Identify the issue with the clause"
    )
    severity: Literal["High", "Medium", "Low"] = Field(
        ...,
        description = "Classify the severity of the clause"
    )
    suggestion: str | None = Field(
        ...,
        description = "Give suggestions to reduce the risks of the clause"
    )

class AuditResults(BaseModel):
    items: list[Flags] = Field(description="A list of identified legal risks")