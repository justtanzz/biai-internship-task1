# BIAI CRM Prototype

An AI-driven Customer Relationship Management (CRM) prototype developed for the BIAI AI Internship Assessment (Round 2, Task 1). This application ingests raw customer inquiries, leverages LLMs for structured data extraction, and provides a dynamic Kanban interface with state-aware AI reply generation.

## 🚀 Core Features

* **Intelligent Data Extraction:** Parses unstructured WhatsApp/Facebook messages to extract structured data (Name, Phone, Company, Interest, Category, Language, and Urgency) with strict JSON schema adherence.
* **Dynamic Kanban Dashboard:** Real-time visual pipeline (New, Contacted, Interested, Paid, Lost) tied directly to a SQLite backend.
* **Context-Aware AI Replies:** Generates 2-3 sentence WhatsApp-style responses tailored to the user's language (English or Banglish) and current pipeline status without hallucinating unprovided facts.
* **SLA Monitoring (Optional Task 1):** Dedicated endpoint and UI modal to flag active leads untouched for >48 hours for immediate intervention.
* **Automated Executive Reporting (Optional Task 2):** Aggregates real-time pipeline metrics and passes them to the LLM to generate a natural-language status report.
* **Asynchronous UX:** Background AI generations are tracked in the DOM via JavaScript, maintaining persistent loading states even during UI modal transitions.

## 🛠️ Architecture & Tech Stack

* **Backend:** Python 3.14, FastAPI, Pydantic (Strict Data Validation)
* **Database:** SQLModel, SQLite (`crm.db`)
* **Frontend:** Vanilla HTML, CSS, JavaScript (Zero-dependency)
* **AI Inference:** Groq API (OpenAI SDK compatible) utilizing `qwen/qwen3.8-27b` for lightning-fast inference and superior Bangla/Banglish processing.

## 📂 Project Structure

```text
├── app/
│   ├── main.py       # FastAPI application and route definitions
│   ├── ai.py         # LLM pipeline, structured extraction, and prompt engineering
│   ├── models.py     # SQLModel database schemas
│   └── importer.py   # Script to seed the database with sample CSV data
├── data/
│   ├── biai_facts.md        # Grounding facts for the AI reply generator
│   └── sample-enquiries.csv # Demo data for the importer
├── static/
│   └── index.html    # Frontend Kanban UI
├── requirements.txt  # Python dependencies
└── .env              # Environment variables (Ignored in Git)
```

## ⚙️ Local Setup & Installation

**1. Clone the repository**
```bash
git clone https://github.com/justtanzz/biai-internship-task1.git
cd biai-internship-task1
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
Create a `.env` file in the root directory and add your Groq credentials:
```ini
LLM_BASE_URL="https://api.groq.com/openai/v1"
LLM_API_KEY="gsk_your_groq_api_key_here"
LLM_MODEL="qwen/qwen3.8-27b"
```

**5. Seed the Database (Optional but recommended)**
Run the importer script to populate the CRM with demo data.
```bash
python -m app.importer
```

**6. Run the Application**
```bash
uvicorn app.main:app --reload
```
The CRM will be accessible locally at `http://127.0.0.1:8000`.

## 🌐 Deployment Note
When deploying to cloud platforms (e.g., Render), ensure the build command installs the requirements (`pip install -r requirements.txt`) and the environment variables (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) are securely configured in the provider's dashboard.

---
**Author:** Tanzeem Haque