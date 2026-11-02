from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field, Session, create_engine

class Enquiry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    phone: Optional[str] = Field(default=None, index=True)
    company: Optional[str] = None
    channel: str = ""
    interest: str = "unclear"    # bootcamp | fellowship | corporate | other | unclear
    category: str = "lead"       # lead | support | spam | not_a_lead
    status: str = "New"          # New | Contacted | Interested | Paid | Lost
    language: str = "english"    # english | banglish | bangla
    urgent: bool = False
    message: str = ""
    summary: str = ""
    suggested_reply: Optional[str] = None
    duplicate_of: Optional[int] = None
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_contacted_at: Optional[datetime] = None

engine = create_engine("sqlite:///crm.db")

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s