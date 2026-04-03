"""
Marketplace Intelligence & Data Observability Platform — Demo
Run: streamlit run app.py
"""
import warnings
warnings.filterwarnings("ignore", message=".*NumPy 1.x.*")
warnings.filterwarnings("ignore", message=".*_ARRAY_API.*")
warnings.filterwarnings("ignore", category=FutureWarning)

import streamlit as st

st.set_page_config(
    page_title="Marketplace Intelligence Platform",
    page_icon="🏪",
    layout="wide",
)

st.title("Marketplace Intelligence & Data Observability Platform")
st.markdown("""
**6 Data Sources** | **4 Use Cases** | **Groq Llama 3 70B** | **~100 Products**

Data: Open Food Facts + USDA FoodData + openFDA Recalls + Open Prices + Amazon ESCI + Instacart Baskets
""")

tab1, tab2, tab3, tab4 = st.tabs([
    "UC1: Catalog Enrichment",
    "UC2: Quality & Observability",
    "UC3: Hybrid Search",
    "UC4: Recommendations",
])

from pages import uc1_enrichment, uc2_quality, uc3_search, uc4_recommendations

with tab1:
    uc1_enrichment.render()

with tab2:
    uc2_quality.render()

with tab3:
    uc3_search.render()

with tab4:
    uc4_recommendations.render()
