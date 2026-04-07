from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.logging_config import configure_logging
configure_logging("INFO")

import streamlit as st

st.set_page_config(
    page_title="Food Catalog DQ Pipeline",
    page_icon="🥫",
    layout="wide",
)

# Sidebar — token usage (shown after pipeline run)
with st.sidebar:
    st.title("Food Catalog DQ")
    st.markdown("---")
    if "token_log" in st.session_state:
        tl = st.session_state["token_log"]
        uc = tl.get("unit_cost", {})
        st.subheader("LLM Usage — This Run")
        st.metric("API Calls", f"{tl['calls']:,}")
        st.metric("Input Tokens", f"{tl['input_tokens']:,}")
        st.metric("Cache-Hit Tokens", f"{tl['cache_tokens']:,}")
        st.metric("Output Tokens", f"{tl['output_tokens']:,}")
        st.markdown("**Cost breakdown**")
        st.caption(f"Input: ${tl.get('input_cost_usd', 0):.4f}  "
                   f"(${uc.get('input_per_1m_usd', 0.14)}/1M)")
        st.caption(f"Cached: ${tl.get('cached_cost_usd', 0):.4f}  "
                   f"(${uc.get('cached_input_per_1m_usd', 0.014)}/1M)")
        st.caption(f"Output: ${tl.get('output_cost_usd', 0):.4f}  "
                   f"(${uc.get('output_per_1m_usd', 0.28)}/1M)")
        st.metric("Total Cost (USD)", f"${tl.get('total_cost_usd', 0):.4f}")
    else:
        st.info("Run the pipeline on the EDA page to see LLM usage.")

    st.markdown("---")
    if st.button("🗑️ Clear DSPy Cache", help="Delete ~/.dspy_cache and enriched output so the next run starts fresh"):
        dspy_cache = Path.home() / ".dspy_cache"
        if dspy_cache.exists():
            shutil.rmtree(dspy_cache)
            dspy_cache.mkdir()
        enriched = Path(__file__).parent.parent / "data" / "products_enriched.csv"
        if enriched.exists():
            enriched.unlink()
        for key in ("pre_df", "post_df", "token_log"):
            st.session_state.pop(key, None)
        st.success("Cache cleared. Re-run the pipeline from the EDA page.")

# Multipage navigation
eda_page = st.Page("page_eda.py", title="EDA Overview", icon="📊")
rows_page = st.Page("page_rows.py", title="Transformation Explorer", icon="🔍")

pg = st.navigation([eda_page, rows_page])
pg.run()
