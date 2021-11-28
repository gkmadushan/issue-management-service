from datetime import time
from pydantic import BaseModel, Field
from typing import List, Optional

class CreateIssue(BaseModel):
    id: Optional[str]
    resource: str
    title: Optional[str]
    description: Optional[str]
    score: str
    issue_id: str
    remediation_script: str
    issue_date: str
    reference: str

class PatchIssue(BaseModel):
    title: Optional[str]
    description: Optional[str]
    score: Optional[float]
    remediation_script: Optional[str]
    false_positive: Optional[bool]
    locked: Optional[bool]

class CreateIssueAction(BaseModel):
    id: Optional[str]
    issue: str
    action_type: str
    notes: str
    