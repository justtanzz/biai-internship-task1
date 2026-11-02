import pytest
from datetime import datetime, timezone, timedelta
from app.ai import has_bangla_script, normalize_phone
from app.models import Enquiry
from fastapi.testclient import TestClient
from app.main import app

def test_bangla_detection():
    assert has_bangla_script("ফেলোশিপ প্রোগ্রামে ভর্তি হতে চাই।") is True
    assert has_bangla_script("Offline class kothay hobe?") is False
    assert has_bangla_script("Hello BIAI team") is False

def test_normalize_phone():
    # Fixes dropped leading zero from spreadsheets
    assert normalize_phone("1711000001") == "01711000001"
    # Strips 880 country code
    assert normalize_phone("8801711000001") == "01711000001"
    # Converts Bangla digits to ASCII
    assert normalize_phone("০১৭১১০০০০০১") == "01711000001"
    # Handles empty/null
    assert normalize_phone(None) is None
    assert normalize_phone("") is None

def test_overdue_flag_logic():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=48)
    
    # 1. Overdue: Created 3 days ago, never contacted
    e1 = Enquiry(category="lead", status="New", received_at=now - timedelta(days=3))
    
    # 2. Not Overdue: Created 1 day ago
    e2 = Enquiry(category="lead", status="New", received_at=now - timedelta(days=1))
    
    # 3. Overdue: Contacted 3 days ago
    e3 = Enquiry(category="lead", status="Contacted", received_at=now - timedelta(days=4), last_contacted_at=now - timedelta(days=3))
    
    def is_overdue(e: Enquiry):
        return e.category == "lead" and e.status in ["New", "Contacted", "Interested"] and (e.last_contacted_at is None or e.last_contacted_at < cutoff) and e.received_at < cutoff

    assert is_overdue(e1) is True
    assert is_overdue(e2) is False
    assert is_overdue(e3) is True


client = TestClient(app)

def test_get_enquiries_endpoint():
    response = client.get("/enquiries")
    assert response.status_code == 200
    # Verifies the endpoint successfully returns a list of database records
    assert isinstance(response.json(), list)