from sqlalchemy import Column, DateTime, ForeignKey, Numeric, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import null

Base = declarative_base()
metadata = Base.metadata


class ActionType(Base):
    __tablename__ = 'action_type'

    id = Column(UUID, primary_key=True)
    code = Column(String(250), nullable=False, unique=True)
    name = Column(String(250), nullable=False)
    mode = Column(String(10), nullable=False)


class IssueStatus(Base):
    __tablename__ = 'issue_status'

    id = Column(UUID, primary_key=True)
    code = Column(String(250), nullable=False, unique=True)
    name = Column(String(250), nullable=False)


class Issue(Base):
    __tablename__ = 'issue'

    id = Column(UUID, primary_key=True)
    resource_id = Column(UUID, nullable=False)
    issue_status_id = Column(ForeignKey('issue_status.id'), nullable=False)
    title = Column(String(250))
    description = Column(String(2000))
    score = Column(String(250))
    issue_id = Column(String(6000))
    remediation_script = Column(String(6000))
    detected_at = Column(DateTime)
    resolved_at = Column(DateTime)
    last_updated_at = Column(DateTime)
    false_positive = Column(SmallInteger, nullable=False, server_default=text("0"))
    locked = Column(SmallInteger, nullable=False, server_default=text("0"))
    reference = Column(UUID, nullable=True)

    issue_status = relationship('IssueStatus')


class IssueAction(Base):
    __tablename__ = 'issue_action'

    id = Column(UUID, primary_key=True)
    notes = Column(String(6000))
    issue_id = Column(ForeignKey('issue.id'), nullable=False)
    issue_status_id = Column(ForeignKey('issue_status.id'), nullable=False)
    action_type_id = Column(ForeignKey('action_type.id'), nullable=False)
    created_at = Column(DateTime, nullable=True)

    action_type = relationship('ActionType')
    issue = relationship('Issue')
    issue_status = relationship('IssueStatus')