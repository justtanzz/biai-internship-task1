import json, os, re
from typing import Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"), api_key=os.getenv("LLM_API_KEY"))
MODEL = os.getenv("LLM_MODEL")

class Extracted(BaseModel):
    name: str
    phone: str          # "" if unknown (avoids anyOf schema issues in LM Studio)
    company: str        # "" if unknown
    interest: Literal["bootcamp", "fellowship", "corporate", "other", "unclear"]
    category: Literal["lead", "support", "spam", "not_a_lead"]
    language: Literal["english", "banglish", "bangla"]
    urgent: bool
    summary: str

SYSTEM = """You extract CRM fields from enquiries sent to BIAI, an AI training company
offering: bootcamp, fellowship, and corporate training. Messages may be in English,
Banglish (Bangla in English letters) or Bangla script.

Rules:
- interest:
  * 'bootcamp': mentions bootcamp.
  * 'fellowship': mentions fellowship.
  * 'corporate': a company, bank, factory, or group wanting training for employees/staff (even for 15+ staff).
  * 'other': specific non-core programs like 'free masterclass'.
  * 'unclear': general questions about courses, classes, recordings, certificates, or discounts without naming a program.
- category:
  * 'lead': prospective customer asking about programs, prices, schedules, or group training.
  * 'support': someone who ALREADY paid or enrolled and has an issue (missing payment confirmation, refund/cancellation request).
  * 'spam': scams, crypto ads, unrelated promotions.
  * 'not_a_lead': job seekers / internship applicants.
- urgent: true ONLY for angry customers, threats, missing payment confirmations, or corporate leads requesting a call soon.
- name: person's name only (strip job titles and company names).
- company: company/organization name if mentioned in sender field or message (e.g., 'Gazipur textile company', 'bank in Motijheel', 'small garment factory'), else "".
- phone: digits if present, else "".
- language: 'bangla' if Bangla script is used, 'banglish' if Bangla words in English alphabet, 'english' if English.
- summary: one short English sentence (include note if sender is a minor/school student or requested a specific callback time).
Never invent information. Use "" when string is unknown."""

def has_bangla_script(text: str) -> bool:
    return bool(re.search(r"[\u0980-\u09FF]", text))

def normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = raw.translate(str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789"))
    digits = re.sub(r"\D", "", digits)
    if digits.startswith("880"):
        digits = "0" + digits[3:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    return digits or None

def _parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    # Fallback if model wraps JSON in extra text
    m = re.search(r"\{.*\}", text, flags=re.S)
    return json.loads(m.group(0) if m else text)

def extract(message: str, sender_name: str = "", phone: str = "", channel: str = "") -> Extracted:
    user = (f"Channel: {channel}\nSender name field: {sender_name}\n"
            f"Phone field: {phone}\nMessage: {message}")
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "enquiry", "strict": True, "schema": Extracted.model_json_schema()}},
        )
    except Exception:
        # Fallback if LM Studio rejects response_format
        r = client.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM + f"\nReturn ONLY valid JSON matching schema: {Extracted.model_json_schema()}"},
                {"role": "user", "content": user}
            ],
        )
    out = Extracted.model_validate(_parse_json(r.choices[0].message.content))
    if has_bangla_script(message):
        out.language = "bangla"
    out.phone = normalize_phone(out.phone or phone) or ""
    return out

def _facts() -> str:
    p = os.path.join("data", "biai_facts.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

def suggest_reply(message: str, language: str, name: str, interest: str, category: str) -> str:
    if language == "english":
        style = "English"
    else:
        style = ("Banglish (Bangla words written ONLY in English alphabet, e.g., "
                 "'Assalamualaikum, apnar message er jonno dhonnobad'). "
                 "CRITICAL: Do NOT use Bangla script (বাংলা অক্ষর) anywhere in your reply.")
    system = f"""You write short, warm WhatsApp-style replies for BIAI's team.
Language & Script Rule: Write in {style}
Tone: Helpful, polite, 2-3 sentences max.
Grounding Rules:
- Use ONLY the facts below.
- Never invent prices, dates, batch schedules, refund policies, or government approval claims; say our team will reach out to confirm the details.
- If category is 'support', apologise sincerely for the inconvenience and assure them a team member is checking this urgently today.
- If category is 'not_a_lead' (e.g. job applicant), politely direct them to email support@biai.com.bd.
Output ONLY the reply text.

FACTS:
{_facts()}"""
    user = f"Sender: {name}\nInterest: {interest}\nCategory: {category}\nMessage: {message}"
    r = client.chat.completions.create(
        model=MODEL, temperature=0.3,
        messages=[{"role": "user", "content": system + "\n\n" + user}],
        max_tokens=1500,
    )
    return r.choices[0].message.content.strip()