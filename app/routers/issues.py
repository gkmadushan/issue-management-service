from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Request
from dependencies import common_params, get_db, get_secret_random
from schemas import CreateIssue, PatchIssue, CreateIssueAction
from sqlalchemy.orm import Session
from typing import Optional
from models import Issue, IssueAction, IssueStatus, ActionType
from dependencies import get_token_header
import uuid
from datetime import datetime
from exceptions import username_already_exists
from sqlalchemy import over
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid
from sqlalchemy.dialects import postgresql

page_size = os.getenv('PAGE_SIZE')


router = APIRouter(
    prefix="/v1/issues",
    tags=["IssueManagementAPIs"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

@router.post("")
def create(details: CreateIssue, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #generate token
    id = details.id or uuid.uuid4().hex

    issue_status = db.query(IssueStatus).get(details.issue_status.strip())
        
    issue = Issue(
        id=id,
        title=details.title,
        resource=details.resource,
        issue_status=issue_status,
        description=details.description,
        score=details.score,
        issue_id=details.issue_id,
        remediation_script=details.remediation_script,
        result_object=details.result_object,
        detected_at=datetime.now(),
        last_updated_at=datetime.now()
    )    

    #commiting data to db
    try:
        db.add(issue)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to create new inventory item")
    return {
        "success": True
    }


@router.get("")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, title: Optional[str] = None, resource: Optional[str] = None, issue_status: Optional[str] = None, issue_id: Optional[str] = None, script_available: Optional[str] = None, false_positive: Optional[str] = None, detected_at_from: Optional[str] = None, detected_at_to: Optional[str] = None, resolved_at_from: Optional[str] = None, resolved_at_to: Optional[str] = None):
    filters = []

    if(title):
        filters.append(Issue.title.ilike(title+'%'))

    if(resource):
        filters.append(Issue.resource_id == resource)

    if(issue_status):
        filters.append(Issue.issue_status_id == issue_status)

    if(issue_id):
        filters.append(Issue.issue_id == issue_id)

    if(script_available == True):
        filters.append(Issue.remediation_script != None)
    
    if(script_available == False):
        filters.append(Issue.remediation_script == None)

    if(detected_at_from):
        filters.append(Issue.detected_at >= detected_at_from)

    if(detected_at_to):
        filters.append(Issue.detected_at <= detected_at_to)

    if(resolved_at_from):
        filters.append(Issue.resolved_at >= resolved_at_from)
    
    if(resolved_at_to):
        filters.append(Issue.resolved_at <= resolved_at_to)

    if(false_positive == True):
        filters.append(Issue.false_positive == True)
    
    if(false_positive == False):
        filters.append(Issue.false_positive == False)


    query = db.query(
        over(func.row_number(), order_by=Issue.detected_at).label('index'),
        Issue.id,
        Issue.title,
        Issue.score,
        Issue.issue_id,
        Issue.detected_at,
        Issue.resolved_at,
        Issue.false_positive
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(Issue.detected_at.asc()), page_number = int(page), page_size = int(limit))

    response = {
        "data": query.all(),
        "meta":{
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response





@router.get("/action-types")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None):
    filters = []    


    query = db.query(
        over(func.row_number(), order_by=ActionType.name).label('index'),
        ActionType.id,
        ActionType.code,
        ActionType.name
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(ActionType.name.asc()), page_number = int(page), page_size = int(limit))

    response = {
        "data": query.all(),
        "meta":{
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response

@router.get("/issue-status")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None):
    filters = []    


    query = db.query(
        over(func.row_number(), order_by=IssueStatus.name).label('index'),
        IssueStatus.id,
        IssueStatus.code,
        IssueStatus.name
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(IssueStatus.name.asc()), page_number = int(page), page_size = int(limit))

    response = {
        "data": query.all(),
        "meta":{
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response


@router.get("/issue-actions")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, issue_id : Optional[str] = None, issue_status : Optional[str] = None, action_type : Optional[str] = None ):
    filters = []   

    if(issue_id):
        filters.append(IssueAction.issue_id == issue_id)
    
    if(issue_status):
        filters.append(IssueAction.issue_status_id == issue_status)

    if(action_type):
        filters.append(IssueAction.action_type_id == action_type)

    query = db.query(
        over(func.row_number(), order_by=IssueAction.created_at).label('index'),
        IssueAction.id,
        IssueAction.notes,
        IssueAction.issue_status,
        IssueAction.action_type,
        IssueAction.created_at
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(IssueAction.created_at.asc()), page_number = int(page), page_size = int(limit))

    response = {
        "data": query.all(),
        "meta":{
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response

@router.post("/issue-actions")
def create(details: CreateIssueAction, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #generate token
    id = details.id or uuid.uuid4().hex

    issue = db.query(Issue).get(details.issue.strip())
    issue_status = issue.issue_status
    action_type = db.query(ActionType).get(details.action_type.strip())    
        
    issue_action = Issue(
        id=id,
        issue_status=issue_status,
        action_type=action_type,
        issue=issue,
        notes=details.notes,
        created_at=datetime.now(),
    )    

    if action_type.mode == 'CHECKOUT':
        issue.locked = True
    else:
        issue.locked = False


    #commiting data to db
    try:
        db.add(issue_action)
        db.add(issue)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to create new inventory item")
    return {
        "success": True
    }


@router.get("/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    issue = db.query(Issue).get(id.strip())
    if item == None:
        raise HTTPException(status_code=404, detail="Issue not found")
    response = {
        "data": issue
    }
    return response

@router.patch("/{id}")
def patch(id:str, details: PatchIssue, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #Set user entity
    issue = db.query(Issue).get(id)

    issue.title=details.title
    issue.description=details.description
    issue.score=details.score
    issue.remediation_script=details.remediation_script
    issue.false_positive=details.false_positive

    #commiting data to db
    try:
        db.add(issue)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Failed to patch")
    return {
        "success": True
    }