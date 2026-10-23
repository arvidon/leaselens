import asyncio
import tempfile
from pathlib import Path

import streamlit as st

from leaselens import pipeline

st.set_page_config(page_title="LeaseLens", page_icon="🏠")
st.title("LeaseLens")
st.caption("Upload a lease. Get the risky clauses, a negotiation plan, and a draft email.")

# Stages: upload → questions → results
state = st.session_state
state.setdefault("review", None)
state.setdefault("result", None)
state.setdefault("log", [])


def progress(msg: str) -> None:
    state.log.append(msg)
    status.write(msg)


def reset() -> None:
    state.review = None
    state.result = None
    state.log = []


if state.review is None:
    uploaded = st.file_uploader("Lease (PDF)", type=["pdf"])
    if uploaded and st.button("Analyse lease", type="primary"):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / uploaded.name
            path.write_bytes(uploaded.getvalue())
            with st.status("Analysing lease…", expanded=True) as status:
                state.review = asyncio.run(pipeline.start_review(path, progress))
                status.update(label="Analysis ready", state="complete")
        st.rerun()

elif state.review.questions:
    st.subheader("A few questions before we finish")
    with st.form("answers"):
        answers = {}
        for i, q in enumerate(state.review.questions, start=1):
            if q.options:
                answers[i] = (q.prompt, st.radio(q.prompt, q.options, key=f"q{i}"))
            else:
                answers[i] = (q.prompt, st.text_input(q.prompt, key=f"q{i}"))
        submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        text = "\n".join(f"- {p}: {a}" for p, a in answers.values())
        with st.status("Working…", expanded=True) as status:
            state.review = asyncio.run(pipeline.finish_review(state.review, text, progress))
            state.result = asyncio.run(pipeline.plan_and_draft(state.review, progress))
            status.update(label="Done", state="complete")
        st.rerun()

elif state.result is None:
    # No questions were needed: go straight to the plan and draft.
    with st.status("Working…", expanded=True) as status:
        state.result = asyncio.run(pipeline.plan_and_draft(state.review, progress))
        status.update(label="Done", state="complete")
    st.rerun()

else:
    st.subheader("Risk analysis")
    st.markdown(state.review.analysis)
    with st.expander("Negotiation plan"):
        st.markdown(state.result["plan"])
    st.subheader("Draft email to landlord")
    st.markdown(state.result["draft"])

if state.review is not None:
    st.sidebar.button("Start over", on_click=reset)
