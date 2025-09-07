from __future__ import annotations

from enum import Enum
from typing import List, Dict

from pydantic import BaseModel, Field


class CategoryEnum(Enum):
    REENTRANCY = "Reentrancy"
    ACCESS_CONTROL = "Access Control"
    INTEGER_OVERFLOW_UNDERFLOW = "Integer Overflow/Underflow"
    DENIAL_OF_SERVICE = "Denial of Service"
    UNCHECKED_CALL = "Unchecked Call"
    FRONT_RUNNING = "Front-Running"
    CONFIG_DEPENDENT = "Config Dependent"
    BUSINESS_LOGIC = "Business Logic"
    PRECISION_LOSS = "Precision Loss"
    CENTRALIZATION_RISK = "Centralization Risk"
    OTHER = "Other"


class Severity(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"
    BEST_PRACTICES = "Best Practices"


class Vulnerability(BaseModel):
    Issue: str = Field(..., description="A short description of the vulnerability or issue")
    Category: CategoryEnum = Field(
        default=CategoryEnum.OTHER, description="Category classifying the vulnerability or issue."
    )
    Severity: Severity
    Contracts: List[str] = Field(..., description="List of affected contract names")
    Description: str = Field(
        ...,
        description="A detailed description of the vulnerability. The description must not include any recommendations for fixes.",
    )


class WorkingResult(Vulnerability):
    Index: int


class Finding(BaseModel):
    is_match: bool = Field(..., description="Whether the finding matches the verified issue")
    is_partial_match: bool = Field(
        ..., description="Whether the finding partially matches the verified issue"
    )
    explanation: str = Field(..., description="Explanation for the match or partial match")
    severity_from_junior_auditor: str = Field(..., description="Severity from the junior auditor")
    severity_from_truth: str = Field(..., description="Severity from the truth")
    index_of_finding_from_junior_auditor: int = Field(
        ..., description="Index of the finding from the junior auditor"
    )


class EvaluatedFinding(Finding):
    is_fp: bool | None
    finding_description_from_junior_auditor: str


SeverityCounts = Dict[str, int]
