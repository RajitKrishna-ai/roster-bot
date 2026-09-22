# 🏥 Clinic Roster Assistant

### AI-Powered Doctor Availability & Patient Response Automation

Clinic Roster Assistant is an AI-powered application designed to automate doctor availability queries in healthcare clinics.

The system converts weekly duty roster images into structured information using multimodal AI, incorporates real-time duty updates from clinic staff, and generates accurate, professional, patient-ready WhatsApp responses.

Instead of manually checking spreadsheets, roster images, and staff WhatsApp groups, clinic reception teams can get instant answers through a simple conversational interface.

---

## 🚀 Problem Statement

Clinic reception teams frequently receive questions such as:

* Is Dr. Venugopal available on Friday?
* What time is Dr. Aravind available today?
* Which GP doctors are available today?
* Is the dental doctor available tomorrow?
* Did any doctor change their duty timing?

Traditionally, answering these questions requires checking:

1. Weekly roster images
2. Doctor schedules
3. Staff WhatsApp groups
4. Last-minute duty changes

This process is manual, repetitive, and prone to human error.

Clinic Roster Assistant solves this problem using Generative AI and rule-based source prioritization.

---

# 💡 Solution Architecture

The application uses a two-stage AI pipeline:

```text
                 ┌─────────────────────┐
                 │ Weekly Roster Image │
                 └──────────┬──────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │ Gemini Multimodal │
                  │ AI Vision Model   │
                  └──────────┬────────┘
                             │
                             ▼
                  Structured Roster Data
                             │
                             │
       ┌─────────────────────┴────────────────────┐
       │                                          │
       ▼                                          ▼
Weekly Doctor Schedule                     Live Duty Updates
                                           (Staff Messages)
       │                                          │
       └─────────────────────┬────────────────────┘
                             ▼
                    Source Priority Logic
                 Updates Override Weekly Roster
                             │
                             ▼
                    ┌──────────────────┐
                    │ Groq LLM Engine  │
                    │ GPT OSS 120B     │
                    └────────┬─────────┘
                             │
                             ▼
                  Patient-Ready WhatsApp Reply
```

---

# ✨ Key Features

## 🖼️ AI-Powered Roster Extraction

Upload a weekly doctor duty roster as an image.

The application uses Google's Gemini multimodal AI model to:

* Read roster images
* Extract doctor names
* Identify departments
* Understand working days
* Extract duty timings
* Identify weekly offs
* Flag unclear information instead of guessing

The extracted roster is displayed in an editable format, allowing staff to manually correct any information when required.

---

## 🔄 Real-Time Duty Updates

Clinic staff can add temporary updates such as:

```text
Dr Sajith not available today evening
```

or:

```text
Dr Joseph Thursday 8.30 - 4.30
```

These updates are dynamically added to the active context.

### Source Priority Logic

The system follows a clear decision hierarchy:

```text
TODAY'S DUTY UPDATES
        ↓
Overrides
        ↓
WEEKLY ROSTER
```

This ensures that last-minute schedule changes always take priority over the normal weekly roster.

---

## 💬 Conversational Patient Query System

Reception staff can ask natural language questions such as:

```text
Dr Venu timing on Friday
```

```text
All GP doctors timing today
```

```text
Today Dr Aravind timing
```

```text
Is dental doctor available tomorrow?
```

The AI understands the context and generates a short, professional response ready to send directly through WhatsApp.

---

## 🧠 Context-Aware Conversations

The system maintains recent conversation history to handle follow-up questions.

Example:

```text
User: Is Dr Aravind available today?

Assistant: Dr Aravind is available from 9:00 AM to 12:30 PM.

User: What about tomorrow?

Assistant: [Uses previous conversation context to understand the doctor reference]
```

The system includes recent conversation messages in the LLM context to support natural follow-up interactions.

---

# 🧠 AI Design Principles

The application is designed with several reliability principles.

### 1. Source of Truth Hierarchy

```text
Live Updates > Weekly Roster
```

Temporary updates represent the latest operational information and therefore override the recurring schedule.

---

### 2. No Guessing Policy

If roster information is unclear, the extraction model is instructed to return:

```text
unclear
```

instead of hallucinating information.

---

### 3. Weekly Off Detection

If a doctor is listed in the weekly roster but not scheduled on a requested day, the assistant identifies it as:

```text
Weekly Off
```

rather than incorrectly saying that information is unavailable.

---

### 4. Conversation Context

The system passes recent chat history to the language model, allowing follow-up questions to be interpreted correctly.

---

### 5. Patient-Friendly Responses

Responses are optimized to be:

* Short
* Warm
* Professional
* Clear
* Ready to paste into WhatsApp

Example:

> Good morning! Dr Aravind is available today from 9:00 AM to 12:30 PM. Please let us know if you would like to book an appointment. Warm regards.

---

# 🛠️ Technology Stack

| Technology              | Purpose                                          |
| ----------------------- | ------------------------------------------------ |
| Python                  | Core application language                        |
| Streamlit               | Web application interface                        |
| Google Gemini           | Multimodal roster image extraction               |
| Groq                    | High-speed LLM inference                         |
| GPT OSS 120B            | Conversational reasoning and response generation |
| Pillow                  | Image processing                                 |
| Streamlit Session State | Application state management                     |

---

# 📂 Project Structure

```text
roster-bot/
│
├── app.py
├── requirements.txt
├── .gitignore
├── README.md
│
└── .streamlit/
    └── secrets.toml       # Local only - NOT committed to GitHub
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/RajitKrishna-ai/roster-bot.git
cd roster-bot
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔐 API Configuration

Create the following folder:

```text
.streamlit
```

Inside it, create:

```text
secrets.toml
```

Add your API keys:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
GROQ_API_KEY = "your_groq_api_key"
```

### Important

Never commit `.streamlit/secrets.toml` to GitHub.

Make sure your `.gitignore` contains:

```gitignore
.streamlit/secrets.toml
.env
.venv/
```

---

# ▶️ Running the Application

Run:

```bash
streamlit run app.py
```

The application will open in your browser.

---

# 📋 Application Workflow

### Step 1: Upload Weekly Roster

Upload the clinic duty roster image.

```text
Roster Image
      ↓
Gemini Vision Model
      ↓
Structured Doctor Schedule
```

---

### Step 2: Review Extracted Data

The extracted roster is displayed in an editable text area.

Staff can manually correct information if needed.

---

### Step 3: Add Live Updates

Add temporary updates from the staff WhatsApp group.

Example:

```text
Dr Sajith not available today evening
```

---

### Step 4: Ask Patient Queries

Enter patient questions in natural language.

Example:

```text
Which GP doctors are available today?
```

---

### Step 5: Generate Patient Reply

The system combines:

```text
Weekly Roster
      +
Live Duty Updates
      +
Conversation Context
      ↓
AI Reasoning
      ↓
Patient-Ready Response
```

---

# 🔒 Security Considerations

API credentials are managed using Streamlit Secrets.

Sensitive files are excluded from version control:

```gitignore
.streamlit/secrets.toml
.env
.env.*
.venv/
```

API keys should never be hardcoded directly into application source code.

If an API key is accidentally exposed, it should be immediately revoked and replaced.

---

# 🎯 Potential Real-World Use Cases

This system can be adapted for:

* Clinics and hospitals
* Medical reception desks
* Dental clinics
* Diagnostic centers
* Multi-specialty healthcare facilities
* Appointment support teams
* WhatsApp-based patient support systems

---

# 🔮 Future Improvements

Potential enhancements include:

* WhatsApp Business API integration
* Automated roster synchronization
* Structured database storage
* PostgreSQL / Supabase integration
* Doctor availability calendar
* Appointment booking integration
* Multi-clinic support
* Role-based authentication
* Persistent conversation history
* RAG-based roster retrieval
* Automated expiry of temporary duty updates
* Voice-based receptionist interface
* Analytics dashboard for common patient queries

---

# 🧠 Technical Highlights

This project demonstrates practical implementation of:

* Multimodal Generative AI
* Vision-based document understanding
* LLM-powered conversational systems
* Context-aware AI assistants
* Source-of-truth prioritization
* Real-time information overrides
* Prompt engineering
* Session state management
* AI safety through no-guessing instructions
* Production-oriented secret management

---

# 👨‍💻 Author

**Rajit R Krishna**

Data Scientist | AI Engineer | Machine Learning | NLP | Generative AI

Dubai, UAE

GitHub: github.com/RajitKrishna-ai

---

# ⭐ Why This Project Matters

This project demonstrates how Generative AI can solve a real operational problem rather than simply acting as a generic chatbot.

The architecture combines multimodal AI, live operational updates, conversational reasoning, and source-priority rules to create a practical healthcare automation system.

The result is a lightweight AI receptionist assistant capable of reducing manual workload and improving response speed for clinic staff.

---

