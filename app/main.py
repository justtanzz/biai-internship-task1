from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models import Enquiry, get_session, init_db
from app.ai import extract, suggest_reply
from datetime import datetime, timezone, timedelta

app = FastAPI(title="BIAI CRM")

# Mount the static folder to serve our UI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
def startup():
    init_db()

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
    demo_now = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
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