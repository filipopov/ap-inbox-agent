"""Web chat (Streamlit). Entry point on Streamlit Community Cloud; run locally with `streamlit run streamlit_app.py`.

On first start it downloads the read-only app database (app.db, ~160 MB) from a private Hugging Face dataset,
because it is too large for the git repository. Locally, an existing app/app.db is used as is.
"""
import os
from pathlib import Path

import streamlit as st

# API keys: Streamlit secrets (cloud) or environment variables (local)
try:
    secrets = dict(st.secrets)
except Exception:  # no secrets.toml (local run): fall back to environment variables
    secrets = {}
for key in ("GEMINI_API_KEY", "GROQ_API_KEY", "HF_TOKEN", "DATA_REPO"):
    if key not in os.environ and key in secrets:
        os.environ[key] = secrets[key]


@st.cache_resource(show_spinner="Loading the inbox database (first start only, ~30 s)...")
def ensure_db():
    local = Path(__file__).parent / "app/app.db"
    if local.exists():
        return str(local)
    from huggingface_hub import hf_hub_download
    return hf_hub_download(repo_id=os.environ.get("DATA_REPO", "fpo14/ap-inbox-data"), filename="app.db",
                           repo_type="dataset", token=os.environ.get("HF_TOKEN"))


os.environ["APP_DB"] = ensure_db()
from agent.agent import answer  # noqa: E402  (needs APP_DB and API keys set first)

EXAMPLES = [
    "Which vendors chase us for payment, and how far did each go?",
    "Which chased invoices are not in the inbox?",
    "How many invoices did we receive, and what is their total?",
    "Which files could not be read?",
    "How accurate are you?",
]

st.set_page_config(page_title="AP Inbox Agent", page_icon="🧾")
st.title("🧾 AP Inbox Agent")
st.caption("Ask about one month of an accounts-payable inbox (5,705 emails, 8,554 attachments, 24 Aug – 30 Sep 2026). "
           "Answers cite email/file IDs and flag anything unreadable, missing or uncertain.")

if "history" not in st.session_state:
    st.session_state.history = []  # [{"role", "content", "trace"}]

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("trace"):
            with st.expander("How I got this"):
                st.code("\n".join(m["trace"]), language=None)

question = st.chat_input("Ask a question about the inbox")
if not st.session_state.history and not question:
    st.write("Try one of these:")
    for ex in EXAMPLES:
        if st.button(ex):
            question = ex

if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Querying the inbox..."):
            past = [{"role": m["role"], "content": m["content"]} for m in st.session_state.history]
            text, trace = answer(question, past)
        st.markdown(text)
        if trace:
            with st.expander("How I got this"):
                st.code("\n".join(trace), language=None)
    st.session_state.history += [{"role": "user", "content": question},
                                 {"role": "assistant", "content": text, "trace": trace}]
