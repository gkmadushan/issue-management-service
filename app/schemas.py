from datetime import time
from pydantic import BaseModel, Field
from typing import List, Optional

class CreateIssue(BaseModel):
    id: Optional[str]
    resource: str
    issue_status: str
    title: Optional[str]
    description: Optional[str]
    score: float
    issue_id: str
    remediation_script: str
    result_object: str


class PatchIssue(BaseModel):
    title: str
    description: str
    score: float
    remediation_script: str
    false_positive: bool

class CreateIssueAction(BaseModel):
    issue: str
    action_type: str
    notes: str
    