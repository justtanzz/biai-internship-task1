import csv, re, sys
from datetime import datetime, timezone
from sqlmodel import Session, select, delete
from app.models import Enquiry, engine, init_db
from app.ai import extract, normalize_phone

def run(path="data/sample-enquiries.csv", use_ai=True):
    init_db()
    with open(path, encoding="utf-8-sig") as f, Session(engine) as s:
        s.exec(delete(Enquiry))  # Clear existing rows so re-runs are idempotent
        s.commit()
        print(f"{'ID':>2} | {'LANG':8} | {'CATEGORY':10} | {'INTEREST':10} | {'URG'} | {'DUP'} | {'NAME & COMPANY'}")
        print("-" * 80)
        for row in csv.DictReader(f):
            sender = row["sender name"]
            m = re.match(r"^(.*?)\s*\((.*)\)$", sender)
            fallback_name, fallback_comp = (m.group(1), m.group(2)) if m else (sender, None)
            phone = normalize_phone(row["phone"])
            
            # Phone call notes (rows 5 & 16) are already initial contact logs
            initial_status = "Contacted" if "Phone call" in row["channel"] else "New"
            
            e = Enquiry(
                name=fallback_name, company=fallback_comp, phone=phone,
                channel=row["channel"], message=row["message"], status=initial_status,
                received_at=datetime.strptime(row["received at"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            )
            if use_ai:
                x = extract(e.message, sender, row["phone"], e.channel)
                e.name = x.name or fallback_name
                e.company = x.company or fallback_comp
                e.interest, e.category, e.language = x.interest, x.category, x.language
                e.urgent, e.summary = x.urgent, x.summary
                
            if phone:
                first = s.exec(select(Enquiry).where(Enquiry.phone == phone)).first()
                if first:
                    e.duplicate_of = first.id
                    e.status = "Duplicate"
            s.add(e)
            s.commit()
            s.refresh(e)
            comp_str = f" ({e.company})" if e.company else ""
            dup_str = f"#{e.duplicate_of}" if e.duplicate_of else " - "
            urg_str = "YES" if e.urgent else " - "
            print(f"{e.id:>2} | {e.language:8} | {e.category:10} | {e.interest:10} | {urg_str} | {dup_str:>3} | {e.name}{comp_str}")

if __name__ == "__main__":
    run(use_ai="--no-ai" not in sys.argv)