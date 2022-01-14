from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from utils.database import Base
from dependencies import get_db, get_token_header
import datetime


def override_get_token_header():
    return True


app.dependency_overrides[get_token_header] = override_get_token_header

client = TestClient(app)


def test_get_issues_200():
    response = client.get("/v1/issues")
    assert response.status_code == 200


def test_get_single_issue_404():
    response = client.get("/v1/issues/3f07cf23-cd0f-42b5-99c4-efa9022adccf")
    assert response.status_code == 404


def test_get_graphs_200():
    response = client.get("/v1/issues/graphs")
    assert response.status_code == 200


def test_get_issues_200():
    response = client.get("/v1/issues")
    assert response.status_code == 200


def test_get_action_types_200():
    response = client.get("/v1/issues/action-types")
    assert response.status_code == 200


def test_create_issue_422():
    response = client.post("/v1/issues", json={
        "id": "4f07cf23-cd0f-42b5-99c4-efa9022adccf",
        "title": "Test title",
        "description": "Test desc",
        "score": "Medium",
        "issue_id": "XXXXXX",
        "remediation_script": "",
        "issue_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "reference": "4f07cf23-cd0f-42b5-99c4-efa9022adccf"
    })
    assert response.status_code == 422
