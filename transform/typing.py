"""Column data-type editing."""
import pandas as pd
import streamlit as st


def render_type_editor(df):
    """Render the 'Modify Column Data Types' expander; return the (mutated) df."""
    st.markdown("---")
    with st.expander("Modify Column Data Types"):
        st.write(
            "Review and adjust data types for columns if needed. "
            "Changes here will affect filtering and visualizations."
        )

        for col in df.columns:
            current_type = str(df[col].dtype)
            options = ["No Change", "Text", "Integer", "Float", "Datetime"]

            default_index = 0
            if pd.api.types.is_integer_dtype(df[col]):
                default_index = options.index("Integer")
            elif pd.api.types.is_float_dtype(df[col]):
                default_index = options.index("Float")
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                default_index = options.index("Datetime")
            elif pd.api.types.is_object_dtype(df[col]):
                inferred_dtype = pd.api.types.infer_dtype(df[col])
                if inferred_dtype == "integer":
                    default_index = options.index("Integer")
                elif inferred_dtype == "floating":
                    default_index = options.index("Float")
                elif inferred_dtype == "datetime64":
                    default_index = options.index("Datetime")
                else:
                    default_index = options.index("Text")

            selected_type = st.selectbox(
                f"Column '{col}' (Current: {current_type})",
                options=options,
                index=default_index,
                key=f"type_select_{col}",
            )

            if selected_type != "No Change":
                try:
                    if selected_type == "Text":
                        df[col] = df[col].astype(str)
                    elif selected_type == "Integer":
                        df[col] = pd.to_numeric(df[col], errors="coerce").astype(pd.Int64Dtype())
                    elif selected_type == "Float":
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    elif selected_type == "Datetime":
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                    st.success(f"Column '{col}' converted to {selected_type}. New type: {df[col].dtype}")
                except Exception as type_e:
                    st.error(
                        f"Could not convert column '{col}' to {selected_type}: {type_e}. "
                        "Data might contain incompatible values. Consider cleaning data first."
                    )
    st.markdown("---")
    return df
