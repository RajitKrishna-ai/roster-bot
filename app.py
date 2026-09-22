import time
import streamlit as st
from PIL import Image
from google import genai
from google.genai import errors as genai_errors
from groq import Groq

st.set_page_config(page_title="Clinic Roster Assistant", page_icon="🏥")
st.title("🏥 Clinic Roster Assistant")
st.caption("Upload the weekly roster, add any duty-change updates as they come in, then chat to get instant patient replies.")

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

if not GEMINI_API_KEY or not GROQ_API_KEY:
    st.error("API keys not found. Add GEMINI_API_KEY and GROQ_API_KEY in .streamlit/secrets.toml")
    st.stop()

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

if "roster_text" not in st.session_state:
    st.session_state.roster_text = ""
if "updates" not in st.session_state:
    st.session_state.updates = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- SIDEBAR: roster + live updates ----------------
with st.sidebar:
    st.subheader("1. Weekly duty roster")
    uploaded_file = st.file_uploader("Upload roster photo", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None and st.button("Extract roster"):
        with st.spinner("Reading the roster..."):
            image = Image.open(uploaded_file)
            prompt = (
                "Extract this duty roster image into a clean, structured text table. "
                "Columns: Doctor Name, Department, Days Available, Timing. "
                "Be explicit about which days each doctor is NOT working, if shown, or make it "
                "clear that any day not listed for a doctor should be treated as their day off. "
                "If a field is unclear, write 'unclear' rather than guessing. "
                "Output only the table, no extra commentary."
            )
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    response = gemini_client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=[prompt, image],
                    )
                    break
                except genai_errors.ServerError as e:
                    last_error = e
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))  # wait 3s, then 6s before retrying
            if response is not None:
                st.session_state.roster_text = response.text
                st.success("Roster extracted.")
            else:
                st.error(
                    "The roster-reading service is temporarily busy (high demand on their end, "
                    "not a problem with your setup). Please wait a minute and click 'Extract roster' again."
                )

    if st.session_state.roster_text:
        with st.expander("View / edit extracted roster"):
            st.session_state.roster_text = st.text_area(
                "Roster data",
                value=st.session_state.roster_text,
                height=200,
                label_visibility="collapsed",
            )

    st.divider()
    st.subheader("2. Duty change updates")
    st.caption("Paste one-off messages from the staff group, e.g. \"Dr Sajith not available today evening\"")

    with st.form("update_form", clear_on_submit=True):
        new_update = st.text_input("New update message", label_visibility="collapsed",
                                    placeholder="e.g. Dr. Joseph Thursday 8.30-4.30")
        submitted = st.form_submit_button("Add update")
        if submitted and new_update.strip():
            st.session_state.updates.append(new_update.strip())

    if st.session_state.updates:
        st.write("Active updates:")
        for i, u in enumerate(st.session_state.updates):
            col1, col2 = st.columns([5, 1])
            col1.write(f"- {u}")
            if col2.button("✕", key=f"del_{i}"):
                st.session_state.updates.pop(i)
                st.rerun()
        if st.button("Clear all updates"):
            st.session_state.updates = []
            st.rerun()

# ---------------- MAIN: chat interface ----------------
st.divider()
st.subheader("Chat")
st.caption("Paste a patient's WhatsApp question below, or ask to rephrase any message, and get a ready-to-send reply.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

patient_query = st.chat_input("Paste the patient's message here")

if patient_query:
    st.session_state.messages.append({"role": "user", "content": patient_query})
    with st.chat_message("user"):
        st.write(patient_query)

    if not st.session_state.roster_text:
        reply = "Please upload and extract the weekly roster first (left sidebar) before I can answer."
    else:
        updates_text = "\n".join(f"- {u}" for u in st.session_state.updates) or "None"
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:]
        )
        with st.spinner("Thinking..."):
            reply = None
            for attempt in range(3):
                try:
                    chat_completion = groq_client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a clinic receptionist assistant chatting with clinic staff. You are "
                            "helpful, professional, and conversational, like a knowledgeable real assistant, "
                            "not a terse machine. You have two sources of truth: the WEEKLY ROSTER (the "
                            "doctor's normal recurring schedule) and TODAY'S UPDATES (one-off changes "
                            "reported by staff, such as a doctor being unavailable or a shifted timing). "
                            "Updates always override the weekly roster when they conflict, since they "
                            "reflect the latest real situation.\n\n"
                            "Staff messages may contain typos, shorthand, or casual phrasing (e.g. 'pgsio' "
                            "means physiotherapy, a misspelled doctor name still refers to that doctor, "
                            "'tomow' means tomorrow). Read past these naturally and understand the intent.\n\n"
                            "Structure every answer in two parts:\n"
                            "1. A short, natural 'checking' line or two showing what you looked up, e.g. "
                            "'Checking Dr. Aravind for today and tomorrow...' followed by what you found in "
                            "the roster and updates (use the doctor's real, exact timings here).\n"
                            "2. A line starting with 'Suggested reply to patient:' followed by the actual "
                            "message in quotes, warm and professional, ready to paste directly into "
                            "WhatsApp, with no apostrophes anywhere (write 'do not' instead of 'don't').\n\n"
                            "Booking buffer: in the suggested reply only (never in the checking line), "
                            "shift the END time of each availability window 30 minutes earlier than the "
                            "roster's real end time, so patients do not arrive right at closing (e.g. a "
                            "roster end time of 9.00 pm becomes 8.30 pm in the patient-facing reply, and "
                            "1.00 pm becomes 12.30 pm). Start times are never changed.\n\n"
                            "When a reply involves booking or choosing a slot, do not ask the patient which "
                            "slot they prefer. Instead ask for their name and mobile number so staff can "
                            "confirm the appointment.\n\n"
                            "If a doctor is not listed as working on the day asked about, and no update "
                            "mentions them, say in your checking line that it is their weekly off, and "
                            "reflect that naturally in the suggested reply. Never invent a timing, day, or "
                            "detail that is not actually in the roster or updates. If something is genuinely "
                            "unclear, conflicting, or missing, do not guess and do not write a suggested "
                            "reply yet — instead, explain what you found and directly ask the staff member "
                            "to confirm or provide the correct detail, offering to use it once given. If "
                            "staff instead ask you to rephrase or polish a message that has nothing to do "
                            "with the roster (e.g. an insurance note), skip the checking step and just give "
                            "the 'Suggested reply to patient:' directly, interpreting any typos or shorthand "
                            "sensibly. Use the conversation so far for context on follow-up questions or "
                            "corrections staff provide."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"WEEKLY ROSTER:\n{st.session_state.roster_text}\n\n"
                            f"TODAY'S UPDATES:\n{updates_text}\n\n"
                            f"CONVERSATION SO FAR:\n{history_text}\n\n"
                            f"Now write the reply to the latest patient message above."
                        ),
                    },
                        ],
                    )
                    reply = chat_completion.choices[0].message.content
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))  # wait 3s, then 6s before retrying
            if reply is None:
                reply = (
                    "Sorry, the reply service is temporarily busy. Please try sending your "
                    "message again in a moment."
                )

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)