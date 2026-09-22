import hashlib
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


# ---------------- SHARED TEAM STATE ----------------
# st.session_state is private to each browser tab/person. We use st.cache_resource
# instead so the roster, updates, and reply cache are shared by everyone using this
# app on the same deployment -- one person uploads the roster, everyone sees it.
@st.cache_resource
def get_shared_store():
    return {"roster_text": "", "updates": [], "reply_cache": {}}


shared = get_shared_store()

# Chat history stays per-person (session_state), so each staff member sees their
# own conversation, not everyone else's queries mixed together.
if "messages" not in st.session_state:
    st.session_state.messages = []


def cache_key(roster_text, updates, query):
    normalized = query.strip().lower()
    raw = roster_text + "||" + "||".join(updates) + "||" + normalized
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------- SIDEBAR: roster + live updates ----------------
with st.sidebar:
    st.subheader("1. Weekly duty roster")
    st.caption("Shared with everyone using this app -- upload once, the whole team sees it.")
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
                        model="gemini-3.5-flash-lite",
                        contents=[prompt, image],
                    )
                    break
                except genai_errors.ClientError as e:
                    if "RESOURCE_EXHAUSTED" in str(e):
                        last_error = "quota"
                        break  # daily quota hit, retrying won't help
                    raise
                except genai_errors.ServerError as e:
                    last_error = e
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))  # wait 3s, then 6s before retrying
            if response is not None:
                shared["roster_text"] = response.text
                shared["reply_cache"].clear()  # roster changed, old cached answers may be stale
                st.success("Roster extracted and shared with the team.")
            elif last_error == "quota":
                st.error(
                    "The free daily limit for the roster-reading service has been reached. "
                    "It resets at midnight (Pacific time, so roughly mid-morning UAE time). "
                    "Please try again after it resets, or reduce how many times you re-extract "
                    "the same roster while testing."
                )
            else:
                st.error(
                    "The roster-reading service is temporarily busy (high demand on their end, "
                    "not a problem with your setup). Please wait a minute and click 'Extract roster' again."
                )

    if shared["roster_text"]:
        with st.expander("View / edit shared roster"):
            edited = st.text_area(
                "Roster data",
                value=shared["roster_text"],
                height=200,
                label_visibility="collapsed",
            )
            if edited != shared["roster_text"]:
                shared["roster_text"] = edited
                shared["reply_cache"].clear()

    st.divider()
    st.subheader("2. Duty change updates")
    st.caption("Shared with everyone. Paste one-off messages from the staff group, e.g. \"Dr Sajith not available today evening\"")

    with st.form("update_form", clear_on_submit=True):
        new_update = st.text_input("New update message", label_visibility="collapsed",
                                    placeholder="e.g. Dr. Joseph Thursday 8.30-4.30")
        submitted = st.form_submit_button("Add update")
        if submitted and new_update.strip():
            shared["updates"].append(new_update.strip())
            shared["reply_cache"].clear()

    if shared["updates"]:
        st.write("Active updates:")
        for i, u in enumerate(shared["updates"]):
            col1, col2 = st.columns([5, 1])
            col1.write(f"- {u}")
            if col2.button("✕", key=f"del_{i}"):
                shared["updates"].pop(i)
                shared["reply_cache"].clear()
                st.rerun()
        if st.button("Clear all updates"):
            shared["updates"] = []
            shared["reply_cache"].clear()
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

    if not shared["roster_text"]:
        reply = "Please upload and extract the weekly roster first (left sidebar) before I can answer."
    else:
        key = cache_key(shared["roster_text"], shared["updates"], patient_query)
        cached = shared["reply_cache"].get(key)

        if cached:
            reply = cached
        else:
            updates_text = "\n".join(f"- {u}" for u in shared["updates"]) or "None"
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
                                        "You are a clinic receptionist assistant chatting with clinic staff. "
                                        "You are helpful, professional, and conversational, like a "
                                        "knowledgeable real assistant, not a terse machine. You have two "
                                        "sources of truth: the WEEKLY ROSTER (the doctor's normal recurring "
                                        "schedule) and TODAY'S UPDATES (one-off changes reported by staff, "
                                        "such as a doctor being unavailable or a shifted timing). Updates "
                                        "always override the weekly roster when they conflict, since they "
                                        "reflect the latest real situation.\n\n"
                                        "Staff messages may contain typos, shorthand, or casual phrasing "
                                        "(e.g. 'pgsio' means physiotherapy, a misspelled doctor name still "
                                        "refers to that doctor, 'tomow' means tomorrow). Read past these "
                                        "naturally and understand the intent.\n\n"
                                        "Structure every answer in two parts:\n"
                                        "1. A short, natural 'checking' line or two showing what you looked "
                                        "up, e.g. 'Checking Dr. Aravind for today and tomorrow...' followed "
                                        "by what you found in the roster and updates (use the doctor's real, "
                                        "exact timings here).\n"
                                        "2. A line starting with 'Suggested reply to patient:' followed by "
                                        "the actual message in quotes, warm and professional, ready to "
                                        "paste directly into WhatsApp, with no apostrophes anywhere (write "
                                        "'do not' instead of 'don't').\n\n"
                                        "Booking buffer: in the suggested reply only (never in the checking "
                                        "line), shift the END time of each availability window 30 minutes "
                                        "earlier than the roster's real end time, so patients do not arrive "
                                        "right at closing (e.g. a roster end time of 9.00 pm becomes 8.30 "
                                        "pm in the patient-facing reply, and 1.00 pm becomes 12.30 pm). "
                                        "Start times are never changed.\n\n"
                                        "When a reply involves booking or choosing a slot, do not ask the "
                                        "patient which slot they prefer. Instead ask for their name and "
                                        "mobile number so staff can confirm the appointment.\n\n"
                                        "If a doctor is not listed as working on the day asked about, and "
                                        "no update mentions them, say in your checking line that it is "
                                        "their weekly off, and reflect that naturally in the suggested "
                                        "reply. Never invent a timing, day, or detail that is not actually "
                                        "in the roster or updates. If something is genuinely unclear, "
                                        "conflicting, or missing, do not guess and do not write a suggested "
                                        "reply yet -- instead, explain what you found and directly ask the "
                                        "staff member to confirm or provide the correct detail, offering to "
                                        "use it once given. If staff instead ask you to rephrase or polish "
                                        "a message that has nothing to do with the roster (e.g. an "
                                        "insurance note), skip the checking step and just give the "
                                        "'Suggested reply to patient:' directly, interpreting any typos or "
                                        "shorthand sensibly. Use the conversation so far for context on "
                                        "follow-up questions or corrections staff provide."
                                    ),
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        f"WEEKLY ROSTER:\n{shared['roster_text']}\n\n"
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
                else:
                    shared["reply_cache"][key] = reply  # save for instant reuse next time

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)