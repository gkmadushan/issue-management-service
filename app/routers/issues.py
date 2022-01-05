from matplotlib import colors
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
from datetime import datetime, timedelta
from exceptions import username_already_exists
from sqlalchemy import over, text
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid
from sqlalchemy.dialects import postgresql
import matplotlib.pyplot as plt
import io
import base64


page_size = os.getenv('PAGE_SIZE')


router = APIRouter(
    prefix="/v1/issues",
    tags=["IssueManagementAPIs"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/graphs")
def new_issues(commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    output = []
    days = "('"+datetime.now().strftime('%Y-%m-%d')+"')"
    for i in range(6):
        days += ",('"+(datetime.now() - timedelta(days=i+1)).strftime('%Y-%m-%d')+"')"

    # Issue summary graph
    result = db.execute(text(f"""
        SELECT SUM(CASE WHEN i.false_positive = 0 THEN 1 ELSE 0 END) as count, DATE(p.date)
        FROM (SELECT * FROM (VALUES {days}) AS t (date)) p
        LEFT JOIN issue i
        ON DATE(i.detected_at) = DATE(p.date)
        group by DATE(p.date)   
        """))
    rows = []
    db.close()
    for row in result:
        rows.append(row)

    if rows:
        y, x = zip(*rows)
        fig, ax = plt.subplots(figsize=(6, 4))
        f1 = io.BytesIO()

        plt.plot(x, y, linewidth=2.0, color='b')
        plt.xticks(rotation=10, fontsize="small")
        plt.xlabel('')
        plt.ylabel('Number of issues ')
        plt.title('Issue Summary')

        fig.savefig(f1, format="svg")

        output.append(base64.b64encode(f1.getvalue()))

        # Open issues by severity
        fig, ax = plt.subplots(figsize=(6, 4))

        f2 = io.BytesIO()

        result = db.execute(text(f"""
            select count(*), (CASE WHEN score='High' THEN 'High' WHEN score='Critical' THEN 'High' WHEN score='Medium' THEN 'Medium' ELSE 'Low' END) as score  from issue where resolved_at is null group by (CASE WHEN score='High' THEN 'High' WHEN score='Critical' THEN 'High' WHEN score='Medium' THEN 'Medium' ELSE 'Low' END)
            """))
        rows = []
        for row in result:
            rows.append(row)
        y, x = zip(*rows)
        bar = plt.bar(x, y, hatch=["\/\/\/", "//", ""], edgecolor='black',
                      color=['red', 'orange', 'lightblue'])
        plt.ylabel('Number of issues ')
        plt.xlabel('')
        plt.title('Open Issues by Severity')

        plt.yticks(fontsize=8)
        plt.xticks(fontsize=8)

        fig.savefig(f2, format="svg")

        output.append(base64.b64encode(f2.getvalue()))

        return output
    else:
        return False


@router.post("")
def create(details: CreateIssue, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    # generate token
    id = details.id or uuid.uuid4().hex

    issue_status = db.query(IssueStatus).filter(IssueStatus.code == 'OPEN').one()

    issue = Issue(
        id=id,
        title=details.title,
        resource_id=details.resource,
        issue_status=issue_status,
        description=details.description,
        score=details.score,
        issue_id=details.issue_id,
        remediation_script=details.remediation_script,
        detected_at=datetime.now(),
        last_updated_at=datetime.now(),
        reference=details.reference,
        unique='-'
    )

    # commiting data to db
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

    if(script_available == '1'):
        filters.append(Issue.remediation_script != None)

    if(script_available == '0'):
        filters.append(Issue.remediation_script == None)

    if(detected_at_from):
        filters.append(Issue.detected_at >= detected_at_from)

    if(detected_at_to):
        filters.append(Issue.detected_at <= detected_at_to)

    if(resolved_at_from):
        filters.append(Issue.resolved_at >= resolved_at_from)

    if(resolved_at_to):
        filters.append(Issue.resolved_at <= resolved_at_to)

    if(false_positive == '1'):
        filters.append(Issue.false_positive == 1)

    if(false_positive == '0'):
        filters.append(Issue.false_positive == 0)

    query = db.query(
        over(func.row_number(), order_by=Issue.detected_at).label('index'),
        Issue.id,
        Issue.title,
        Issue.score,
        Issue.issue_id,
        Issue.detected_at,
        Issue.resolved_at,
        Issue.false_positive,
        IssueStatus.name.label('issue_status')
    )

    query, pagination = apply_pagination(query.where(
        and_(*filters)).join(Issue.issue_status).order_by(Issue.detected_at.asc()), page_number=int(page), page_size=int(limit))

    response = {
        "data": query.all(),
        "meta": {
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

    query, pagination = apply_pagination(query.where(
        and_(*filters)).order_by(ActionType.order.asc()), page_number=int(page), page_size=int(limit))

    response = {
        "data": query.all(),
        "meta": {
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response


@router.get("/action-types/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    action_type = db.query(ActionType).get(id.strip())
    if action_type == None:
        raise HTTPException(status_code=404, detail="Action type not found")
    response = {
        "data": action_type
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

    query, pagination = apply_pagination(query.where(
        and_(*filters)).order_by(IssueStatus.name.asc()), page_number=int(page), page_size=int(limit))

    response = {
        "data": query.all(),
        "meta": {
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response


@router.get("/issue-actions")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, issue_id: Optional[str] = None, issue_status: Optional[str] = None, action_type: Optional[str] = None):
    filters = []

    if(issue_id):
        filters.append(IssueAction.issue_id == issue_id)

    if(issue_status):
        filters.append(IssueAction.issue_status_id == issue_status)

    if(action_type):
        filters.append(IssueAction.action_type_id == action_type)

    query = db.query(
        IssueAction.id,
        IssueAction.notes,
        IssueAction.issue_status,
        IssueAction.action_type,
        IssueAction.created_at,
        ActionType.name
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).join(IssueAction.action_type).join(
        IssueAction.issue_status).order_by(IssueAction.created_at.desc()), page_number=int(page), page_size=int(limit))

    response = {
        "data": query.all(),
        "meta": {
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response


@router.post("/issue-actions")
def create(details: CreateIssueAction, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    # generate token
    id = details.id or uuid.uuid4().hex

    issue = db.query(Issue).get(details.issue.strip())
    issue_status = issue.issue_status
    action_type = db.query(ActionType).get(details.action_type.strip())

    issue_action = IssueAction(
        id=id,
        issue_status=issue_status,
        action_type=action_type,
        issue=issue,
        notes=details.notes,
        created_at=datetime.now(),
    )

    if action_type.mode == 'CHECKOUT':
        issue.locked = int(True)
    if action_type.mode == 'CHECKIN':
        issue.locked = int(False)

    if action_type.code == 'FIXED':
        issue.unique_id = uuid.uuid4().hex

    # commiting data to db
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
    if issue == None:
        raise HTTPException(status_code=404, detail="Issue not found")
    response = {
        "data": issue
    }
    return response


@router.patch("/{id}")
def patch(id: str, details: PatchIssue, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    # Set user entity
    issue = db.query(Issue).get(id)

    if details.title != None:
        issue.title = details.title
    if details.description != None:
        issue.description = details.description
    if details.score != None:
        issue.score = details.score
    if details.remediation_script != None:
        issue.remediation_script = details.remediation_script
    if details.false_positive != None:
        issue.false_positive = int(details.false_positive)
    if details.locked != None:
        issue.locked = int(details.locked)

    # commiting data to db
    try:
        db.add(issue)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Failed to patch")
    return {
        "success": True
    }


@router.patch("/notify-overdue")
def notify(db: Session = Depends(get_db)):
    issue = db.query(Issue).get(id)


# @router.delete("/{reference}")
# def get_by_id(reference: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
#     issue = db.query(Issue).get(id.strip())
#     if issue == None:
#         raise HTTPException(status_code=404, detail="Issue not found")
#     response = {
#         "data": issue
#     }
#     return response
