"""UC4: Cross-Category Recommendations tab."""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR


def render():
    st.header("UC4: Cross-Category Recommendations")
    st.caption("Instacart basket analysis → Association rules → LLM affinity profiles")

    try:
        baskets = pd.read_csv(DATA_DIR / "instacart_baskets.csv")
        rules = pd.read_csv(DATA_DIR / "association_rules.csv") if (DATA_DIR / "association_rules.csv").exists() else pd.DataFrame()
        departments = pd.read_csv(DATA_DIR / "instacart_departments.csv") if (DATA_DIR / "instacart_departments.csv").exists() else pd.DataFrame()
    except FileNotFoundError as e:
        st.error(f"Data not found: {e}. Run scripts/01_fetch_data.py and scripts/06_prepare_instacart.py first.")
        return

    # Section 1: Basket Analysis Overview
    st.subheader("1. Basket Analysis Overview")

    col1, col2, col3, col4 = st.columns(4)
    n_orders = baskets["order_id"].nunique()
    n_products = baskets["product_name"].nunique()
    n_depts = baskets["department"].nunique()
    avg_items = baskets.groupby("order_id").size().mean()
    with col1:
        st.metric("Orders Sampled", f"{n_orders:,}")
    with col2:
        st.metric("Unique Products", f"{n_products:,}")
    with col3:
        st.metric("Departments", n_depts)
    with col4:
        st.metric("Avg Items/Basket", f"{avg_items:.1f}")

    # Top products
    top_products = baskets["product_name"].value_counts().head(15)
    fig = px.bar(x=top_products.values, y=top_products.index, orientation="h",
                 title="Top 15 Most Ordered Products", labels={"x": "Order Count", "y": "Product"})
    fig.update_layout(yaxis=dict(autorange="reversed"), height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Department distribution
    dept_counts = baskets.groupby("department")["order_id"].nunique().sort_values(ascending=False)
    fig = px.pie(values=dept_counts.values, names=dept_counts.index, title="Orders by Department")
    st.plotly_chart(fig, use_container_width=True)

    # Cross-category stats
    basket_depts = baskets.groupby("order_id")["department"].nunique()
    cross_cat_pct = (basket_depts >= 2).mean() * 100
    st.metric("Cross-Category Baskets (2+ departments)", f"{cross_cat_pct:.0f}%")

    st.divider()

    # Section 2: Association Rules
    st.subheader("2. Association Rules")

    if len(rules) > 0:
        st.dataframe(
            rules[["antecedent", "consequent", "support", "confidence", "lift"]].head(20),
            use_container_width=True,
        )
    else:
        st.info("No association rules found. Run scripts/06_prepare_instacart.py first.")

    st.divider()

    # Section 3: Category Explorer
    st.subheader("3. Category Explorer")

    dept_list = sorted(baskets["department"].unique().tolist())
    dept_list = [d for d in dept_list if d != "missing"]
    selected_dept = st.selectbox("Select a department:", dept_list)

    if selected_dept and len(rules) > 0:
        # Find rules where selected department is antecedent
        dept_rules = rules[rules["antecedent"].str.lower().str.contains(selected_dept.lower())]
        if len(dept_rules) > 0:
            st.markdown(f"**Shoppers who buy from *{selected_dept}* also buy:**")
            for _, rule in dept_rules.head(5).iterrows():
                st.write(f"  → **{rule['consequent']}** (confidence: {rule['confidence']}%, lift: {rule['lift']})")
        else:
            # Try as consequent
            dept_rules = rules[rules["consequent"].str.lower().str.contains(selected_dept.lower())]
            if len(dept_rules) > 0:
                st.markdown(f"**Shoppers who buy from these departments also buy *{selected_dept}*:**")
                for _, rule in dept_rules.head(5).iterrows():
                    st.write(f"  ← **{rule['antecedent']}** (confidence: {rule['confidence']}%, lift: {rule['lift']})")
            else:
                st.info(f"No strong association rules found for '{selected_dept}'.")

    # Co-occurrence network
    if len(rules) > 0:
        st.markdown("**Department Co-occurrence Network**")
        edges = rules.head(15)
        if len(edges) > 0:
            all_nodes = list(set(edges["antecedent"].tolist() + edges["consequent"].tolist()))
            # Simple node positions (circle layout)
            import math
            n = len(all_nodes)
            positions = {node: (math.cos(2*math.pi*i/n), math.sin(2*math.pi*i/n)) for i, node in enumerate(all_nodes)}

            edge_x, edge_y = [], []
            for _, row in edges.iterrows():
                x0, y0 = positions.get(row["antecedent"], (0, 0))
                x1, y1 = positions.get(row["consequent"], (0, 0))
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#888"), hoverinfo="none"))
            fig.add_trace(go.Scatter(
                x=[positions[n][0] for n in all_nodes],
                y=[positions[n][1] for n in all_nodes],
                mode="markers+text", text=all_nodes, textposition="top center",
                marker=dict(size=20, color="steelblue"),
            ))
            fig.update_layout(showlegend=False, height=500, title="Category Affinity Network")
            fig.update_xaxes(visible=False)
            fig.update_yaxes(visible=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Section 4: LLM Affinity Profile
    st.subheader("4. LLM Affinity Profile")

    if selected_dept and st.button(f"Generate profile for '{selected_dept}'"):
        from utils.llm import call_llm

        # Get co-purchase stats for context
        dept_baskets = baskets[baskets["department"] == selected_dept]["order_id"].unique()
        co_depts = baskets[baskets["order_id"].isin(dept_baskets)].groupby("department")["order_id"].nunique()
        co_depts = co_depts.sort_values(ascending=False).head(8)
        co_text = ", ".join([f"{dept} ({count/len(dept_baskets)*100:.0f}%)" for dept, count in co_depts.items() if dept != selected_dept])

        top_prods = baskets[baskets["department"] == selected_dept]["product_name"].value_counts().head(5)
        prods_text = ", ".join([f"{name} ({count})" for name, count in top_prods.items()])

        prompt = f"""You are a retail analytics expert. Generate a shopper affinity profile for the '{selected_dept}' department.

Data:
- Total baskets containing {selected_dept}: {len(dept_baskets):,}
- Top products: {prods_text}
- Most common co-purchased departments: {co_text}

Write a 3-4 sentence shopper profile describing who buys from this department, what they typically buy together, and shopping behavior patterns. Be specific with percentages."""

        with st.spinner("Generating affinity profile..."):
            profile = call_llm(prompt, max_tokens=300)

        if profile:
            st.success(profile)
        else:
            st.error("Failed to generate profile. Check Groq API key.")
