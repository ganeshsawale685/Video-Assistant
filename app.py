from dotenv import load_dotenv

load_dotenv()

import html
import os
import re
import tempfile
import time

import streamlit as st
import streamlit.components.v1 as components

from utils.audio_processing import process_input
from core.transcriber import transcribe_all
from core.summarize import summarize_transcript, generate_title
from core.extractor import (
    extract_key_decisions,
    extract_questions,
    extract_action_items,
)
from core.rag_engine import build_rag_chain, ask_question


# ----------------------------------------------------------------------------
# Page setup (no sidebar)
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Meeting Assistant",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------------------------------------------------------
# Theme: "recording studio at night"
#   midnight blue base, cyan = the audio signal, amber = work in progress
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Sora:wght@500;600;700&display=swap');

    :root {
        --bg: #070b1a;
        --panel: rgba(255, 255, 255, .045);
        --line: rgba(148, 163, 255, .18);
        --text: #e6ecff;
        --muted: #9aa6c9;
        --signal: #38bdf8;
        --signal-deep: #0c4a6e;
        --amber: #fbbf24;
    }

    /* hide sidebar completely */
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"] { background: transparent; }

    .stApp {
        background:
            radial-gradient(1100px 560px at 12% -10%, rgba(56, 189, 248, .16), transparent 60%),
            radial-gradient(900px 520px at 100% 0%, rgba(129, 140, 248, .13), transparent 60%),
            var(--bg);
        color: var(--text);
    }
    html, body, [class*="css"], .stMarkdown, .stTextInput, .stButton {
        font-family: 'DM Sans', system-ui, sans-serif;
    }
    h1, h2, h3, h4, .doc-title {
        font-family: 'Sora', 'DM Sans', sans-serif !important;
        letter-spacing: -0.015em;
        color: var(--text);
    }
    .block-container { padding-top: 1.4rem; max-width: 1100px; }

    /* ---------- keyframes ---------- */
    @keyframes fadeUp  { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
    @keyframes fadeIn  { from { opacity: 0; } to { opacity: 1; } }
    @keyframes flipIn  { from { opacity: 0; transform: perspective(900px) rotateX(-16deg) translateY(20px); }
                         to   { opacity: 1; transform: perspective(900px) rotateX(0) translateY(0); } }
    @keyframes spin    { to { transform: rotate(360deg); } }
    @keyframes shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
    @keyframes drawTick{ from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }
    @keyframes pop     { 0% { transform: scale(.6); } 60% { transform: scale(1.15); } 100% { transform: scale(1); } }
    @keyframes bounce  { 0%, 80%, 100% { transform: translateY(0); opacity: .35; } 40% { transform: translateY(-5px); opacity: 1; } }
    @keyframes cubeSpin{ from { transform: rotateX(-25deg) rotateY(0deg); } to { transform: rotateX(-25deg) rotateY(360deg); } }
    @keyframes count   { from { --num: 0; } to { --num: var(--target); } }
    @property --num { syntax: '<integer>'; initial-value: 0; inherits: false; }

    /* ---------- hero ---------- */
    .hero-text { text-align: center; margin-top: -34px; animation: fadeUp .8s .1s ease-out backwards; }
    .hero-text h1 { font-size: 2.6rem; font-weight: 700; margin: 0 0 .5rem 0; }
    .hero-text p  { color: var(--muted); font-size: 1.05rem; max-width: 560px; margin: 0 auto 1.4rem auto; }

    /* ---------- glass cards ---------- */
    [class*="st-key-card_"], .st-key-inputcard {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        backdrop-filter: blur(10px);
        transform-style: preserve-3d;
        animation: flipIn .7s ease-out backwards;
        transition: transform .3s ease, box-shadow .3s ease, border-color .3s ease;
    }
    [class*="st-key-card_"]:hover {
        transform: perspective(900px) translateY(-5px) rotateX(2.5deg) rotateY(-2.5deg);
        border-color: rgba(56, 189, 248, .55);
        box-shadow: 0 18px 40px -18px rgba(56, 189, 248, .55);
    }
    .st-key-inputcard { animation-delay: .25s; }
    .st-key-card_1 { animation-delay: .15s; }
    .st-key-card_2 { animation-delay: .30s; }
    .st-key-card_3 { animation-delay: .45s; }
    .st-key-card_4 { animation-delay: .60s; }

    /* ---------- processing card with 3D cube ---------- */
    .pipe { margin-top: 1.2rem; padding: 1.2rem 1.4rem; border: 1px solid var(--line); border-radius: 14px;
            background: var(--panel); backdrop-filter: blur(10px); animation: fadeUp .4s ease-out backwards; }
    .pipe-head { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; font-family: 'Sora', sans-serif; font-weight: 600; }
    .cube-wrap { width: 34px; height: 34px; perspective: 220px; flex: none; }
    .cube { width: 34px; height: 34px; position: relative; transform-style: preserve-3d; animation: cubeSpin 4s linear infinite; }
    .cube i { position: absolute; inset: 0; border: 1.5px solid var(--signal); background: rgba(56, 189, 248, .1); }
    .cube i:nth-child(1) { transform: translateZ(17px); }
    .cube i:nth-child(2) { transform: rotateY(180deg) translateZ(17px); }
    .cube i:nth-child(3) { transform: rotateY(90deg) translateZ(17px); }
    .cube i:nth-child(4) { transform: rotateY(-90deg) translateZ(17px); }
    .cube i:nth-child(5) { transform: rotateX(90deg) translateZ(17px); border-color: var(--amber); }
    .cube i:nth-child(6) { transform: rotateX(-90deg) translateZ(17px); }

    .pipe-bar { height: 6px; border-radius: 4px; background: rgba(255, 255, 255, .08); overflow: hidden; margin-bottom: 1rem; }
    .pipe-bar span { display: block; height: 100%; border-radius: 4px;
        background: linear-gradient(90deg, var(--signal), #bae6fd, var(--signal)); background-size: 200% 100%;
        animation: shimmer 1.6s linear infinite; transition: width .6s ease; }
    .pipe-steps { list-style: none; margin: 0; padding: 0; display: grid; gap: .65rem; }
    .pipe-steps li { display: flex; align-items: center; gap: .75rem; color: var(--muted); }
    .pipe-steps li.active { color: var(--text); font-weight: 500; }
    .pipe-steps li.done   { color: var(--text); }
    .pipe-steps .dot { width: 22px; height: 22px; border-radius: 50%; display: grid; place-items: center;
                       border: 2px solid rgba(255, 255, 255, .14); flex: none; }
    .pipe-steps li.active .dot { border-color: rgba(251, 191, 36, .25); border-top-color: var(--amber); animation: spin .8s linear infinite; }
    .pipe-steps li.done .dot   { background: var(--signal); border-color: var(--signal); animation: pop .35s ease-out; }
    .pipe-steps .dot svg { width: 12px; height: 12px; fill: none; stroke: #04141f; stroke-width: 3.2;
                           stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 24; animation: drawTick .35s .1s ease-out backwards; }

    /* ---------- results ---------- */
    .doc-title { font-size: 1.9rem; line-height: 1.25; margin: .2rem 0 .25rem 0; font-weight: 700; animation: fadeUp .5s ease-out backwards; }
    .doc-meta  { color: var(--muted); font-size: .9rem; margin-bottom: 1rem; animation: fadeUp .5s .08s ease-out backwards; }
    .stats { display: flex; gap: 2.2rem; margin: .2rem 0 .6rem 0; animation: fadeUp .5s .16s ease-out backwards; }
    .stat b { display: block; font-family: 'Sora', sans-serif; font-size: 1.8rem; color: var(--signal);
              animation: count 1.1s ease-out forwards; counter-reset: num var(--num); }
    .stat b::after { content: counter(num); }
    .stat span { color: var(--muted); font-size: .85rem; }

    /* chat */
    [data-testid="stChatMessage"] { animation: fadeUp .35s ease-out backwards; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; }
    .typing { display: flex; gap: 5px; padding: .5rem 0; }
    .typing i { width: 8px; height: 8px; border-radius: 50%; background: var(--signal); animation: bounce 1.1s infinite; }
    .typing i:nth-child(2) { animation-delay: .15s; }
    .typing i:nth-child(3) { animation-delay: .30s; }

    /* suggestion chips (buttons inside the chips container) */
    .st-key-chips div.stButton > button {
        border-radius: 999px; background: rgba(56, 189, 248, .08); border: 1px solid rgba(56, 189, 248, .35);
        color: var(--text); font-size: .85rem; padding: .3rem .9rem; }
    .st-key-chips div.stButton > button:hover { background: rgba(56, 189, 248, .2); border-color: var(--signal); }

    /* transcript viewer */
    .tx-box { max-height: 480px; overflow-y: auto; padding: 1rem 1.2rem; border: 1px solid var(--line);
              border-radius: 12px; background: var(--panel); line-height: 1.75; color: var(--text); }
    .tx-box p { margin: 0 0 .7rem 0; }
    .tx-box mark { background: rgba(251, 191, 36, .85); color: #1b1300; border-radius: 3px; padding: 0 2px; }
    .tx-count { color: var(--muted); font-size: .88rem; margin: .2rem 0 .6rem 0; }

    /* checklist */
    .st-key-card_2 [data-testid="stCheckbox"] { padding: .15rem 0; }
    .st-key-card_2 [data-testid="stCheckbox"] label { cursor: pointer; }

    /* tabs + buttons */
    [data-baseweb="tab-panel"] { animation: fadeIn .4s ease-out backwards; }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 9px; transition: transform .15s ease, box-shadow .2s ease, background .2s ease; }
    div.stButton > button:hover, div.stDownloadButton > button:hover { transform: translateY(-2px); }
    div.stButton > button:active { transform: scale(.98); }
    div.stButton > button[kind="primary"] { background: var(--signal); color: #04141f; border: none; font-weight: 600; }
    div.stButton > button[kind="primary"]:hover { background: #7dd3fc; box-shadow: 0 10px 24px -10px rgba(56, 189, 248, .9); }
    button:focus-visible { outline: 2px solid var(--amber) !important; outline-offset: 2px; }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# 3D scene (Three.js inside an iframe): a ring of audio bars around a wireframe core.
# It follows the mouse a little. Needs internet for the Three.js CDN script.
# ----------------------------------------------------------------------------
THREE_TEMPLATE = """
<!doctype html><html><head><meta charset="utf-8">
<style>html,body{margin:0;height:100%;overflow:hidden;background:transparent}canvas{display:block}</style>
</head><body>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function () {
  if (!window.THREE) return;
  var COMPACT = __COMPACT__;
  var W = function () { return window.innerWidth; };
  var H = function () { return window.innerHeight; };

  var renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch (e) { return; }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(W(), H());
  document.body.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(COMPACT ? 40 : 42, W() / H(), 0.1, 100);
  camera.position.set(0, COMPACT ? 3.4 : 3.6, COMPACT ? 11 : 9.5);
  camera.lookAt(0, 0.4, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  var key = new THREE.PointLight(0x38bdf8, 1.6, 30); key.position.set(0, 5, 5); scene.add(key);
  var warm = new THREE.PointLight(0xfbbf24, 1.1, 30); warm.position.set(-6, 2, -4); scene.add(warm);

  var ring = new THREE.Group(); scene.add(ring);
  var N = COMPACT ? 48 : 72, R = 3.2;
  var geo = new THREE.BoxGeometry(0.16, 1, 0.16); geo.translate(0, 0.5, 0);
  var bars = [];
  for (var i = 0; i < N; i++) {
    var a = i / N * Math.PI * 2;
    var amber = i % 12 === 0;
    var mat = new THREE.MeshStandardMaterial({
      color: amber ? 0xfbbf24 : 0x38bdf8,
      emissive: amber ? 0x7a5a08 : 0x0c4a6e,
      roughness: 0.35, metalness: 0.2
    });
    var m = new THREE.Mesh(geo, mat);
    m.position.set(Math.cos(a) * R, 0, Math.sin(a) * R);
    m.rotation.y = -a;
    ring.add(m); bars.push(m);
  }

  var core = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1.1, 1),
    new THREE.MeshBasicMaterial({ color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.55 })
  );
  core.position.y = 0.9; ring.add(core);

  var base = new THREE.Mesh(
    new THREE.TorusGeometry(R + 0.35, 0.015, 8, 128),
    new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.5 })
  );
  base.rotation.x = Math.PI / 2; ring.add(base);

  var count = COMPACT ? 90 : 240, pos = new Float32Array(count * 3);
  for (var j = 0; j < count; j++) {
    var r = 4 + Math.random() * 3, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
    pos[j * 3] = r * Math.sin(ph) * Math.cos(th);
    pos[j * 3 + 1] = r * Math.cos(ph) * 0.6 + 1;
    pos[j * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
  }
  var pg = new THREE.BufferGeometry();
  pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  var pts = new THREE.Points(pg, new THREE.PointsMaterial({ color: 0x7dd3fc, size: 0.04, transparent: true, opacity: 0.7 }));
  scene.add(pts);

  var tx = 0, ty = 0, mx = 0, my = 0;
  window.addEventListener('mousemove', function (e) { tx = e.clientX / W() - 0.5; ty = e.clientY / H() - 0.5; });
  window.addEventListener('resize', function () {
    renderer.setSize(W(), H()); camera.aspect = W() / H(); camera.updateProjectionMatrix();
  });

  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var clock = new THREE.Clock();

  function frame() {
    var t = reduce ? 2 : clock.getElapsedTime();
    mx += (tx - mx) * 0.05; my += (ty - my) * 0.05;
    for (var i = 0; i < bars.length; i++) {
      var s = 0.5 + 0.5 * Math.sin(t * 1.7 + i * 0.38);
      var s2 = 0.6 + 0.4 * Math.sin(t * 0.8 + i * 0.11);
      bars[i].scale.y = 0.25 + 1.9 * s * s2;
    }
    ring.rotation.y = t * 0.22 + mx * 1.2;
    ring.rotation.x = my * 0.35;
    core.rotation.y = t * 0.5; core.rotation.x = t * 0.3;
    core.scale.setScalar(1 + 0.06 * Math.sin(t * 2));
    pts.rotation.y = -t * 0.04;
    renderer.render(scene, camera);
    if (!reduce) requestAnimationFrame(frame);
  }
  frame();
})();
</script></body></html>
"""


def scene_3d(height: int, compact: bool = False):
    src = THREE_TEMPLATE.replace("__COMPACT__", "true" if compact else "false")
    components.html(src, height=height)


# ----------------------------------------------------------------------------
# Animated pieces
# ----------------------------------------------------------------------------
STEPS = [
    "Fetching the audio",
    "Transcribing speech",
    "Writing title and summary",
    "Finding tasks, decisions and questions",
    "Preparing the chat",
]

SUGGESTIONS = [
    "Give me a 3-line recap",
    "What are the next steps and who owns them?",
    "What was decided?",
    "What is still unresolved?",
]

CHECK_SVG = '<svg viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>'
CUBE_HTML = '<div class="cube-wrap"><div class="cube"><i></i><i></i><i></i><i></i><i></i><i></i></div></div>'
TYPING_HTML = '<div class="typing"><i></i><i></i><i></i></div>'


def progress_html(active: int) -> str:
    """active = index of the step running now; steps before it are done."""
    pct = int(active / len(STEPS) * 100)
    rows = []
    for i, label in enumerate(STEPS):
        if i < active:
            rows.append(f'<li class="done"><span class="dot">{CHECK_SVG}</span>{label}</li>')
        elif i == active:
            rows.append(f'<li class="active"><span class="dot"></span>{label}…</li>')
        else:
            rows.append(f'<li><span class="dot"></span>{label}</li>')
    head = "All done" if active >= len(STEPS) else "Working on your recording"
    return (
        '<div class="pipe">'
        f'<div class="pipe-head">{CUBE_HTML}<span>{head}</span></div>'
        f'<div class="pipe-bar"><span style="width:{max(pct, 6)}%"></span></div>'
        f'<ul class="pipe-steps">{"".join(rows)}</ul>'
        "</div>"
    )


def stream_words(text: str, delay: float = 0.02):
    """Typewriter effect for st.write_stream."""
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


# ----------------------------------------------------------------------------
# Pipeline (same steps as the CLI; `holder` shows the animated progress card)
# ----------------------------------------------------------------------------
def run_pipeline_with_progress(source: str, language: str, holder) -> dict:
    def show(i: int):
        holder.markdown(progress_html(i), unsafe_allow_html=True)

    show(0)
    chunks = process_input(source)

    show(1)
    transcript = transcribe_all(chunks, language)

    show(2)
    title = generate_title(transcript)
    summary = summarize_transcript(transcript)

    show(3)
    action_items = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)

    show(4)
    rag_chain = build_rag_chain(transcript)

    show(len(STEPS))
    time.sleep(0.6)

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_items,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def to_items(value) -> list:
    """Turn a string or list from the extractors into a clean list of lines."""
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    items = []
    for line in str(value).splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if line:
            items.append(line)
    return items


def as_markdown(value) -> str:
    """Your extractors may return a string or a list; show both nicely."""
    items = to_items(value)
    if not items:
        return "_Nothing found._"
    # keep the original text if the extractor already returned a markdown string
    if isinstance(value, str):
        return value
    return "\n".join(f"- {item}" for item in items)


def checked_report_actions(result: dict) -> str:
    """Action items as a markdown checklist that reflects the ticks in the UI."""
    items = to_items(result["action_items"])
    if not items:
        return "_Nothing found._"
    lines = []
    for i, item in enumerate(items):
        mark = "x" if st.session_state.get(f"ai_{i}", False) else " "
        lines.append(f"- [{mark}] {item}")
    return "\n".join(lines)


def build_report(result: dict) -> str:
    return (
        f"# {result['title']}\n\n"
        f"## Summary\n{as_markdown(result['summary'])}\n\n"
        f"## Action items\n{checked_report_actions(result)}\n\n"
        f"## Key decisions\n{as_markdown(result['key_decisions'])}\n\n"
        f"## Open questions\n{as_markdown(result['open_questions'])}\n\n"
        f"## Transcript\n{result['transcript']}\n"
    )


def reset_session():
    for key in list(st.session_state.keys()):
        if key in ("result", "messages", "source_label", "toast", "pending_q") or key.startswith(("ai_", "tx_")):
            st.session_state.pop(key, None)


def render_checklist(items: list):
    """Tickable action items with a live progress bar."""
    if not items:
        st.markdown("_Nothing found._")
        return
    done = sum(1 for i in range(len(items)) if st.session_state.get(f"ai_{i}", False))
    st.progress(done / len(items), text=f"{done} of {len(items)} done")
    for i, item in enumerate(items):
        key = f"ai_{i}"
        label = f"~~{item}~~" if st.session_state.get(key, False) else item
        st.checkbox(label, key=key)


def highlight(text: str, query: str) -> str:
    safe = html.escape(text)
    if not query:
        return safe
    pattern = re.compile(re.escape(html.escape(query)), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe)


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def ask_and_stream(question: str):
    """Show the question, answer it with a typing indicator, and store both."""
    messages = st.session_state["messages"]
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        holder = st.empty()
        holder.markdown(TYPING_HTML, unsafe_allow_html=True)
        try:
            answer = str(ask_question(st.session_state["result"]["rag_chain"], question))
        except Exception as e:
            answer = f"Something went wrong while answering: {e}"
        holder.empty()
        st.write_stream(stream_words(answer))
    messages.append({"role": "assistant", "content": answer})


# ----------------------------------------------------------------------------
# Input screen
# ----------------------------------------------------------------------------
if "result" not in st.session_state:
    scene_3d(height=360)

    st.markdown(
        """
        <div class="hero-text">
            <h1>AI Video Assistant</h1>
            <p>Add a YouTube link or upload a recording. You'll get a summary,
            action items, decisions and open questions, and you can ask follow-up questions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        with st.container(key="inputcard"):
            tab_url, tab_file = st.tabs(["YouTube link", "Upload a file"])

            with tab_url:
                url = st.text_input(
                    "YouTube URL",
                    placeholder="https://www.youtube.com/watch?v=…",
                    label_visibility="collapsed",
                )

            with tab_file:
                uploaded = st.file_uploader(
                    "Audio or video file",
                    type=["mp3", "wav", "m4a", "mp4", "mov", "mkv", "webm"],
                    label_visibility="collapsed",
                )

            language = st.radio(
                "Spoken language",
                options=["english", "hinglish"],
                format_func=str.capitalize,
                horizontal=True,
            )

            go = st.button("Analyze recording", type="primary", use_container_width=True)

        progress_holder = st.empty()

    if go:
        tmp_path = None
        source = None
        label = None

        if uploaded is not None:
            suffix = os.path.splitext(uploaded.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            source, label = tmp_path, uploaded.name
        elif url.strip():
            source, label = url.strip(), url.strip()

        if not source:
            with mid:
                st.warning("Add a YouTube link or upload a file first.")
        else:
            try:
                result = run_pipeline_with_progress(source, language, progress_holder)
                st.session_state["result"] = result
                st.session_state["source_label"] = label
                st.session_state["messages"] = []
                st.session_state["toast"] = True
            except Exception as e:
                progress_holder.empty()
                with mid:
                    st.error(f"Couldn't process this recording: {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

            if "result" in st.session_state:
                st.rerun()


# ----------------------------------------------------------------------------
# Results screen
# ----------------------------------------------------------------------------
else:
    result = st.session_state["result"]
    messages = st.session_state["messages"]

    if st.session_state.pop("toast", False):
        st.toast("Your recording is ready", icon="✅")

    words = len(result["transcript"].split())
    read_minutes = max(1, round(words / 200))
    asked = sum(1 for m in messages if m["role"] == "user")

    head_left, head_right = st.columns([3, 2])
    with head_left:
        st.markdown(f"<div class='doc-title'>{html.escape(str(result['title']))}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='doc-meta'>{html.escape(str(st.session_state.get('source_label', '')))}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="stats">
                <div class="stat"><b style="--target:{words}"></b><span>words spoken</span></div>
                <div class="stat"><b style="--target:{read_minutes}"></b><span>minutes to read</span></div>
                <div class="stat"><b style="--target:{asked}"></b><span>questions asked</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, _ = st.columns([1.3, 1, 1])
        with b1:
            st.download_button(
                "Download report",
                data=build_report(result),
                file_name="meeting_report.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with b2:
            if st.button("Start over", use_container_width=True):
                reset_session()
                st.rerun()
    with head_right:
        scene_3d(height=210, compact=True)

    tab_overview, tab_chat, tab_transcript = st.tabs(["Overview", "Ask questions", "Transcript"])

    # ---- Overview ----
    with tab_overview:
        with st.container(key="card_1"):
            st.markdown("#### Summary")
            st.markdown(as_markdown(result["summary"]))

        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(key="card_2"):
                st.markdown("#### Action items")
                render_checklist(to_items(result["action_items"]))
        with c2:
            with st.container(key="card_3"):
                st.markdown("#### Key decisions")
                st.markdown(as_markdown(result["key_decisions"]))
        with c3:
            with st.container(key="card_4"):
                st.markdown("#### Open questions")
                open_qs = to_items(result["open_questions"])
                if not open_qs:
                    st.markdown("_Nothing found._")
                for i, q in enumerate(open_qs):
                    st.markdown(f"- {q}")
                    # click to ask the assistant about this open question
                    if st.button("Ask about this", key=f"askq_{i}"):
                        st.session_state["pending_q"] = f"Tell me more about this open question: {q}"
                        st.toast("Sent to the chat. Open the “Ask questions” tab.", icon="💬")

    # ---- Chat ----
    with tab_chat:
        top_l, top_r = st.columns([4, 1])
        with top_r:
            if messages and st.button("Clear chat", use_container_width=True):
                st.session_state["messages"] = []
                st.rerun()

        if not messages:
            st.info("Ask anything about this recording, or tap a suggestion below.")
            with st.container(key="chips"):
                chip_cols = st.columns(2)
                for i, s in enumerate(SUGGESTIONS):
                    with chip_cols[i % 2]:
                        if st.button(s, key=f"chip_{i}", use_container_width=True):
                            st.session_state["pending_q"] = s
                            st.rerun()

        for m in messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        typed = st.chat_input("Ask about this recording")
        question = typed or st.session_state.pop("pending_q", None)
        if question:
            ask_and_stream(question)

    # ---- Transcript ----
    with tab_transcript:
        s1, s2 = st.columns([3, 1])
        with s1:
            query = st.text_input(
                "Search transcript",
                key="tx_query",
                placeholder="Search the transcript, e.g. deadline",
                label_visibility="collapsed",
            ).strip()
        with s2:
            only_matches = st.toggle("Only matching lines", value=True, key="tx_only")

        sentences = split_sentences(result["transcript"])
        if query:
            hits = [s for s in sentences if query.lower() in s.lower()]
            total = sum(s.lower().count(query.lower()) for s in sentences)
            st.markdown(
                f"<div class='tx-count'>{total} match{'es' if total != 1 else ''} in {len(hits)} line{'s' if len(hits) != 1 else ''}</div>",
                unsafe_allow_html=True,
            )
            shown = hits if only_matches else sentences
        else:
            shown = sentences

        if shown:
            body = "".join(f"<p>{highlight(s, query)}</p>" for s in shown)
        else:
            body = "<p>No matches.</p>"
        st.markdown(f"<div class='tx-box'>{body}</div>", unsafe_allow_html=True)

        st.write("")
        st.download_button(
            "Download transcript (.txt)",
            data=result["transcript"],
            file_name="transcript.txt",
            mime="text/plain",
        )