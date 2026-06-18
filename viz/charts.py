"""Visualization studio."""
import plotly.express as px
import streamlit as st


def render_visualization(df):
    """Render the chart builder for ``df``."""
    st.markdown("---")
    st.subheader("Visualization Studio")

    all_columns = df.columns.tolist()
    if not all_columns:
        st.info("Upload data to see visualization options.")
        return

    col_x, col_y = st.columns(2)
    with col_x:
        x_axis = st.selectbox("Select X-Axis", options=all_columns, index=0)
    with col_y:
        y_axis = st.selectbox(
            "Select Y-Axis",
            options=all_columns,
            index=1 if len(all_columns) > 1 else 0,
        )

    chart_type = st.selectbox("Select Chart Type", options=["Line", "Bar", "Scatter"], index=0)

    if not (x_axis and y_axis):
        st.info("Please select both X and Y axes to generate a chart.")
        return

    try:
        if chart_type == "Line":
            fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Line Chart)")
        elif chart_type == "Bar":
            fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Bar Chart)")
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis} (Scatter Plot)")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as chart_e:
        st.error(
            f"Error creating chart: {chart_e}. "
            "Please check your axis selections and data types."
        )
