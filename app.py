"""
Medical AI Hallucination Detection — Streamlit UI
Run: streamlit run app.py
"""
import sys
import os
import json
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent
SRC_PATH  = REPO_ROOT / "src"
DATA_PATH = REPO_ROOT / "data"
OUT_PATH  = REPO_ROOT / "outputs"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

OUT_PATH.mkdir(exist_ok=True)

# ── Streamlit imports ────────────────────────────────────────────────────────
import streamlit as st

st.set_page_config(
    page_title="Medical Hallucination Detector",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Lazy-load heavy dependencies (cached for session) ───────────────────────
@st.cache_resource(show_spinner="Loading models (first run may take 60-90 s)...")
def load_verifier():
    from medical_verifier import MedicalVerifier
    return MedicalVerifier()

@st.cache_resource(show_spinner="Loading disease buckets...")
def load_buckets(config):
    from disease_buckets import DiseaseKBBuckets
    centroids_path = DATA_PATH / "disease_centroids.npz"
    kb_csv  = DATA_PATH / "expanded_knowledge_base_preprocessed.csv"
    kb_emb  = DATA_PATH / "kb_embeddings_preprocessed.npy"
    buckets = DiseaseKBBuckets(config=config)
    if centroids_path.exists():
        buckets.load(str(centroids_path))
    elif kb_csv.exists() and kb_emb.exists():
        buckets.build(str(kb_csv), str(kb_emb))
        buckets.save(str(centroids_path))
    else:
        return None
    return buckets

# ── Risk colour helpers ──────────────────────────────────────────────────────
RISK_COLOUR  = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red", "CRITICAL": "darkred"}
CONF_COLOUR  = {"HIGH": "green", "MEDIUM": "orange", "LOW": "red"}
CONF_EMOJI   = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❌"}

def risk_badge(level: str) -> str:
    col = RISK_COLOUR.get(level, "grey")
    return f"<span style='background:{col};color:white;padding:2px 10px;border-radius:4px;font-weight:bold'>{level}</span>"

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏥 Med-HAL Detector")
    st.caption("Medical AI Hallucination Detection System")

    st.divider()
    st.subheader("Mode")
    mode = st.radio("Verification mode", ["Standard", "Disease-specialised"], index=0)

    disease_choice = None
    if mode == "Disease-specialised":
        disease_choice = st.selectbox(
            "Select disease",
            ["type_1_diabetes", "metastatic_cancer"],
            format_func=lambda x: x.replace("_", " ").title(),
        )

    st.divider()
    st.subheader("Config (read-only)")
    try:
        from medical_config import get_global_config
        cfg = get_global_config()
        thresh = cfg.get_confidence_thresholds()
        st.metric("CONFIDENCE_HIGH",   thresh["high"])
        st.metric("CONFIDENCE_MEDIUM", thresh["medium"])
        risk_th = cfg.get_risk_thresholds()
        st.metric("HIGH_RISK_LOW_CONF_RATIO", risk_th["high_risk_low_conf"])
    except Exception as e:
        st.error(f"Config load failed: {e}")

    st.divider()
    st.caption("GPU info")
    try:
        import torch
        if torch.cuda.is_available():
            st.success(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            st.info("CPU only")
    except ImportError:
        st.warning("torch not found")

# ── Main layout ───────────────────────────────────────────────────────────────
st.title("Medical AI Hallucination Detection")
st.caption("Extracts claims from medical text, scores them against a PubMed knowledge base, and flags implausibilities.")

tab_single, tab_batch, tab_history = st.tabs(["Single Summary", "Batch Verification", "Result History"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Single summary
# ═══════════════════════════════════════════════════════════════════════════════
with tab_single:
    col_input, col_result = st.columns([1, 1], gap="large")

    with col_input:
        st.subheader("Input")
        default_text = (
            "The patient was diagnosed with Type 1 diabetes mellitus and started on insulin "
            "glargine 10 units at bedtime. HbA1c was 9.2%. Metformin 500 mg twice daily was "
            "added. The patient should stop insulin immediately and use herbal remedies for a "
            "complete diabetes cure."
        )
        summary_text = st.text_area(
            "Medical summary",
            value=default_text,
            height=280,
            placeholder="Paste a medical summary here...",
        )
        summary_id = st.text_input("Summary ID (optional)", value="summary_001")
        verify_btn = st.button("Verify", type="primary", use_container_width=True)

    with col_result:
        st.subheader("Result")
        result_placeholder = st.empty()

    if verify_btn and summary_text.strip():
        with st.spinner("Running verification pipeline..."):
            try:
                verifier = load_verifier()

                if mode == "Disease-specialised" and disease_choice:
                    from medical_config import get_global_config
                    cfg = get_global_config()
                    buckets = load_buckets(cfg)
                    if buckets is None:
                        st.error("Disease KB buckets unavailable — knowledge base files missing.")
                    else:
                        result = verifier.verify_for_disease(
                            summary_text.strip(),
                            disease=disease_choice,
                            buckets=buckets,
                            summary_id=summary_id or None,
                        )
                else:
                    result = verifier.verify_single_summary(
                        summary_text.strip(),
                        summary_id=summary_id or None,
                    )

                # ── Display result ──────────────────────────────────────────
                with col_result:
                    ra    = result.get("risk_assessment", {})
                    risk  = ra.get("overall_risk", "N/A")
                    total = result.get("total_claims", 0)
                    warns = result.get("safety_warnings", [])

                    st.markdown(f"**Overall Risk:** {risk_badge(risk)}", unsafe_allow_html=True)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total claims", total)
                    m2.metric("Safety warnings", len(warns))
                    m3.metric("Low-conf claims", ra.get("low_confidence_claims", "—"))

                    # Claims table
                    claims = result.get("claims", [])
                    if claims:
                        st.subheader("Claims")
                        for c in claims:
                            label  = c.get("confidence_label", "LOW")
                            score  = c.get("confidence_score", 0)
                            text   = c.get("claim_text", "")
                            neg    = " 🔴 NEGATED"    if c.get("is_negated")   else ""
                            unc    = " 🟡 UNCERTAIN"  if c.get("is_uncertain") else ""
                            emoji  = CONF_EMOJI.get(label, "❓")
                            with st.expander(f"{emoji} [{label} {score:.3f}]{neg}{unc} — {text[:70]}..."):
                                st.write(text)
                                facts = c.get("supporting_facts", [])
                                if facts:
                                    st.caption("Supporting evidence:")
                                    for f in facts[:3]:
                                        st.markdown(f"- {f.get('title','')[:120]}")

                    # Safety warnings
                    if warns:
                        st.subheader("Safety Warnings")
                        for w in warns:
                            sev = w.get("severity", "INFO")
                            msg = w.get("message", "")
                            if sev in ("CRITICAL", "HIGH"):
                                st.error(f"[{sev}] {msg}")
                            elif sev == "MEDIUM":
                                st.warning(f"[{sev}] {msg}")
                            else:
                                st.info(f"[{sev}] {msg}")

                    # Download
                    st.divider()
                    st.download_button(
                        "Download JSON",
                        data=json.dumps(result, indent=2, default=str),
                        file_name=f"{summary_id or 'result'}.json",
                        mime="application/json",
                    )

                    # Persist to history
                    hist_path = OUT_PATH / "verification_history.jsonl"
                    with open(hist_path, "a") as f:
                        f.write(json.dumps(result, default=str) + "\n")

            except Exception as e:
                st.error(f"Verification failed: {e}")
                st.exception(e)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Batch verification
# ═══════════════════════════════════════════════════════════════════════════════
with tab_batch:
    st.subheader("Batch Verification")
    st.caption("Enter one summary per line or upload a JSON file with a list of strings.")

    batch_mode = st.radio("Input method", ["Text (one per line)", "Upload JSON"])

    batch_texts = []
    if batch_mode == "Text (one per line)":
        raw = st.text_area(
            "Summaries (one per line)",
            height=200,
            placeholder="Summary 1...\nSummary 2...\n",
        )
        if raw.strip():
            batch_texts = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    else:
        uploaded = st.file_uploader("Upload JSON (list of strings)", type=["json"])
        if uploaded:
            try:
                data = json.load(uploaded)
                if isinstance(data, list):
                    batch_texts = [str(x) for x in data]
                    st.success(f"Loaded {len(batch_texts)} summaries.")
                else:
                    st.error("JSON must be a list of strings.")
            except Exception as e:
                st.error(f"JSON parse error: {e}")

    run_batch = st.button("Run Batch", type="primary", disabled=len(batch_texts) == 0)

    if run_batch and batch_texts:
        with st.spinner(f"Verifying {len(batch_texts)} summaries..."):
            try:
                verifier = load_verifier()
                batch_results = verifier.verify_multiple_summaries(
                    batch_texts,
                    summary_ids=[f"batch_{i:03d}" for i in range(len(batch_texts))],
                )

                # Summary table
                import pandas as pd
                rows = []
                for r in batch_results:
                    ra = r.get("risk_assessment", {})
                    rows.append({
                        "ID": r.get("summary_id", ""),
                        "Risk": ra.get("overall_risk", "N/A"),
                        "Claims": r.get("total_claims", 0),
                        "Warnings": len(r.get("safety_warnings", [])),
                        "Low-conf": ra.get("low_confidence_claims", 0),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                # Charts
                import plotly.express as px
                risk_counts = df["Risk"].value_counts().reset_index()
                risk_counts.columns = ["Risk", "Count"]
                colour_seq = {"LOW": "#28a745", "MEDIUM": "#ffc107", "HIGH": "#fd7e14", "CRITICAL": "#dc3545"}
                fig = px.bar(
                    risk_counts, x="Risk", y="Count",
                    color="Risk",
                    color_discrete_map=colour_seq,
                    title="Risk Level Distribution",
                )
                st.plotly_chart(fig, use_container_width=True)

                # Download
                st.download_button(
                    "Download batch JSON",
                    data=json.dumps(batch_results, indent=2, default=str),
                    file_name="batch_results.json",
                    mime="application/json",
                )
                st.download_button(
                    "Download batch CSV",
                    data=df.to_csv(index=False),
                    file_name="batch_results.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"Batch verification failed: {e}")
                st.exception(e)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Result history
# ═══════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("Verification History")
    hist_path = OUT_PATH / "verification_history.jsonl"
    if hist_path.exists():
        records = []
        with open(hist_path) as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        if records:
            import pandas as pd
            rows = []
            for r in records:
                ra = r.get("risk_assessment", {})
                rows.append({
                    "ID": r.get("summary_id", ""),
                    "Timestamp": r.get("analysis_timestamp", ""),
                    "Risk": ra.get("overall_risk", "N/A"),
                    "Claims": r.get("total_claims", 0),
                    "Warnings": len(r.get("safety_warnings", [])),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            if st.button("Clear history"):
                hist_path.unlink()
                st.rerun()
        else:
            st.info("No history yet.")
    else:
        st.info("No history yet — run a verification to populate this tab.")
