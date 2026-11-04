from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select, SQLModel
from contextlib import asynccontextmanager
from app.models import Enquiry, get_session, init_db
from app.ai import extract, suggest_reply, generate_summary 
from datetime import datetime, timezone, timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)
# Mount the static folder to serve our UI
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

class ExtractIn(BaseModel):
    message: str
    sender_name: str = ""
    phone: str = ""
    channel: str = ""

@app.post("/extract")
def api_extract(body: ExtractIn):
    return extract(body.message, body.sender_name, body.phone, body.channel)

@app.get("/enquiries")
def list_enquiries(s: Session = Depends(get_session)):
    return s.exec(select(Enquiry).order_by(Enquiry.received_at.desc())).all()

@app.post("/enquiries")
def create_enquiry(e: Enquiry, s: Session = Depends(get_session)):
    # Check for existing phone number before saving
    if e.phone:
        first = s.exec(select(Enquiry).where(Enquiry.phone == e.phone)).first()
        if first:
            e.duplicate_of = first.id
            e.status = "Duplicate"
            
    s.add(e)
    s.commit()
    s.refresh(e)
    return e

class StatusUpdate(BaseModel):
    status: str

@app.patch("/enquiries/{eid}/status")
def update_status(eid: int, body: StatusUpdate, s: Session = Depends(get_session)):
    e = s.get(Enquiry, eid)
    if not e:
        raise HTTPException(status_code=404)
    e.status = body.status
    e.last_contacted_at = datetime.now(timezone.utc)
    s.add(e)
    s.commit()
    return {"status": "updated"}

@app.post("/enquiries/{eid}/reply")
def reply(eid: int, s: Session = Depends(get_session)):
    e = s.get(Enquiry, eid)
    if not e:
        raise HTTPException(status_code=404)
    e.suggested_reply = suggest_reply(e.message, e.language, e.name, e.interest, e.category)
    s.add(e)
    s.commit()
    return {"reply": e.suggested_reply}

@app.get("/reports/overdue")
def get_overdue(s: Session = Depends(get_session)):
    # Configurable "now" for the demo data (Oct 26-27, 2026)
    demo_now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    cutoff = demo_now - timedelta(hours=48)
    
    overdue = s.exec(
        select(Enquiry).where(
            (Enquiry.category == "lead") & 
            (Enquiry.status.in_(["New", "Contacted", "Interested"])) &
            (
                (Enquiry.last_contacted_at == None) | 
                (Enquiry.last_contacted_at < cutoff)
            ) &
            (Enquiry.received_at < cutoff)
        )
    ).all()
    return overdue

@app.get("/reports/summary")
def get_weekly_summary(s: Session = Depends(get_session)):
    enquiries = s.exec(select(Enquiry)).all()
    total = len(enquiries)
    new = sum(1 for e in enquiries if e.status == "New" and e.category == "lead")
    support = sum(1 for e in enquiries if e.category == "support")
    urgent = sum(1 for e in enquiries if e.urgent)
    paid = sum(1 for e in enquiries if e.status == "Paid")
    
    stats = f"Total Enquiries: {total}. New Leads: {new}. Support Tickets: {support}. Urgent Items: {urgent}. Paid: {paid}."
    summary_text = generate_summary(stats)
    return {"summary": summary_text}