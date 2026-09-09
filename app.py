import streamlit as st
from PIL import Image
from google import genai
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
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[prompt, image],
            )
            st.session_state.roster_text = response.text
        st.success("Roster extracted.")

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
st.caption("Paste a patient's WhatsApp question below and get a ready-to-send reply.")

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
            chat_completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a clinic receptionist assistant chatting with clinic staff, who will "
                            "forward your reply to a patient on WhatsApp. You have two sources of truth: "
                            "the WEEKLY ROSTER (the doctor's normal recurring schedule) and TODAY'S UPDATES "
                            "(one-off changes reported by staff, such as a doctor being unavailable or a "
                            "shifted timing). Updates always override the weekly roster when they conflict, "
                            "since they reflect the latest real situation. If a doctor is not listed as "
                            "working on the day asked about in the weekly roster, and no update mentions "
                            "that doctor, say clearly that it is the doctor's weekly off that day, rather "
                            "than saying the doctor is 'not scheduled' or that information is unavailable. "
                            "Only say information is unavailable if the doctor is not in the roster at all, "
                            "or the roster is genuinely unclear about that day. Write a short, warm, "
                            "professional reply, ready to paste directly into WhatsApp. Do not use "
                            "apostrophes anywhere (write 'do not' instead of 'don't'). Use the conversation "
                            "so far for context if the patient asks a follow-up question."
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

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)