"""
OVERTHRONE :: components/panels/code_terminal.py
Code terminal panel: Python editor + safe execution + AP submission.
"""

import streamlit as st
import random
from datetime import datetime
from db import save_gs, push_ev, run_code_safe
from config import TASKS, CODE_FAIL_CHANCE


def render_code_terminal(gs, MT, dn):
    st.markdown("""
    <div style="background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);border-radius:4px;
        padding:0.75rem 1rem;margin-bottom:12px;font-family:'Share Tech Mono',monospace;font-size:0.68rem;color:var(--dim)">
        💻 Python execution engine — Standard library available.
        <span style="color:#FF2244"> os · sys · subprocess blocked for security.</span>
    </div>
    """, unsafe_allow_html=True)

    sov_task_names = {t["id"]: t["title"] for t in TASKS["sovereign"]}
    sel_id = st.selectbox(
        "Load task template",
        options=["custom"] + [t["id"] for t in TASKS["sovereign"]],
        format_func=lambda x: "— Custom Code —" if x == "custom" else sov_task_names[x],
        key="code_task_sel",
    )

    default_code = "# Write your Python code here\nprint('Hello, War Room!')"
    if sel_id != "custom":
        task_obj = next((t for t in TASKS["sovereign"] if t["id"] == sel_id), None)
        if task_obj:
            default_code = task_obj.get("starter", default_code)

    code_key = f"code_{sel_id}"
    if code_key not in st.session_state:
        st.session_state[code_key] = default_code

    user_code = st.text_area(
        "Code Editor",
        value=st.session_state[code_key],
        height=300,
        key=f"editor_{sel_id}",
        label_visibility="collapsed",
        placeholder="# Write Python here...",
    )
    st.session_state[code_key] = user_code

    run_col, submit_col = st.columns([1, 1], gap="small")
    with run_col:
        run_clicked = st.button("▶  RUN CODE", key="run_code", use_container_width=True)
    with submit_col:
        submit_clicked = st.button(
            "✓  SUBMIT FOR AP", key="submit_code",
            use_container_width=True, disabled=(sel_id == "custom")
        )

    output_key = f"out_{sel_id}"

    if "code_outputs" not in st.session_state:
        st.session_state.code_outputs = {}

    if run_clicked:
        stdout, stderr = run_code_safe(user_code)
        st.session_state.code_outputs[output_key] = {
            "stdout": stdout, "stderr": stderr,
            "ts": datetime.utcnow().strftime("%H:%M:%S"),
        }

    if submit_clicked and sel_id != "custom":
        stdout, stderr = run_code_safe(user_code)
        st.session_state.code_outputs[output_key] = {
            "stdout": stdout, "stderr": stderr,
            "ts": datetime.utcnow().strftime("%H:%M:%S"),
        }
        task_obj = next((t for t in TASKS["sovereign"] if t["id"] == sel_id), None)
        if task_obj and not stderr:
            if random.random() < CODE_FAIL_CHANCE:
                push_ev("TASK", f"Code submission FAILED — Team {MT}", MT)
                st.error("Submission rejected by the judges. Try again.")
            else:
                gs["ap"][MT] = int(gs["ap"].get(MT, 0)) + task_obj["pts"]
                save_gs(gs)
                push_ev("TASK", f"Team {MT} ({dn}) submitted code '{task_obj['title']}' +{task_obj['pts']} AP", MT)
                st.success(f"✓ Accepted! +{task_obj['pts']} AP awarded to Team {MT}")
            st.rerun()
        elif stderr:
            st.error("Fix errors before submitting.")

    # Output terminal
    out = st.session_state.code_outputs.get(output_key)
    if out:
        ts   = out.get("ts", "")
        sout = out.get("stdout", "")
        serr = out.get("stderr", "")
        html = f'<div class="code-term"><div style="color:#3a3a5a;font-size:0.55rem;margin-bottom:6px">RUN @ {ts}</div>'
        if sout:
            html += f'<div class="stdout">{sout}</div>'
        if serr:
            html += f'<div class="stderr">{serr}</div>'
        if not sout and not serr:
            html += '<div class="ok">✓ No output — executed with no errors</div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="code-term" style="color:#222238">// Output will appear here after execution</div>',
            unsafe_allow_html=True,
        )
