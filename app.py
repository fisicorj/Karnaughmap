import math
import streamlit as st
import pandas as pd
from sympy import symbols
from sympy.logic.boolalg import SOPform

st.set_page_config(page_title="Universal Karnaugh Map Solver", layout="wide")


# =========================
# Helpers
# =========================
def gray_code(n_bits: int) -> list[str]:
    if n_bits == 0:
        return [""]
    if n_bits == 1:
        return ["0", "1"]
    prev = gray_code(n_bits - 1)
    return ["0" + x for x in prev] + ["1" + x for x in reversed(prev)]


def valid_map_shape(n_vars: int) -> tuple[int, int, int, int]:
    """
    Split variables between rows and columns.
    Returns:
        row_bits, col_bits, n_rows, n_cols
    """
    row_bits = n_vars // 2
    col_bits = n_vars - row_bits
    n_rows = 2 ** row_bits
    n_cols = 2 ** col_bits
    return row_bits, col_bits, n_rows, n_cols


def binary_str_to_index(bits: str) -> int:
    return int(bits, 2) if bits else 0


def minterm_index(row_gray: str, col_gray: str) -> int:
    bits = row_gray + col_gray
    return binary_str_to_index(bits)


def format_sympy_expr(expr) -> str:
    if expr is True:
        return "1"
    if expr is False:
        return "0"

    s = str(expr)
    s = s.replace("&", " · ")
    s = s.replace("|", " + ")
    s = s.replace("~", "¬")
    return s


def build_kmap_dataframe(n_rows: int, n_cols: int) -> pd.DataFrame:
    data = [["0" for _ in range(n_cols)] for _ in range(n_rows)]
    return pd.DataFrame(data)


def parse_cell_value(value: str) -> str:
    if value is None:
        return "0"
    text = str(value).strip().upper()
    if text in {"0", "1", "X"}:
        return text
    return "0"


def solve_kmap(n_vars: int, grid_df: pd.DataFrame, var_names: list[str]):
    row_bits, col_bits, n_rows, n_cols = valid_map_shape(n_vars)
    row_labels = gray_code(row_bits)
    col_labels = gray_code(col_bits)

    minterms = []
    dontcares = []
    cell_map = []

    for r in range(n_rows):
        for c in range(n_cols):
            value = parse_cell_value(grid_df.iat[r, c])
            idx = minterm_index(row_labels[r], col_labels[c])

            cell_map.append(
                {
                    "row_gray": row_labels[r],
                    "col_gray": col_labels[c],
                    "value": value,
                    "minterm": idx,
                }
            )

            if value == "1":
                minterms.append(idx)
            elif value == "X":
                dontcares.append(idx)

    vars_sym = symbols(var_names)
    expr = SOPform(vars_sym, minterms, dontcares)

    return {
        "minterms": sorted(minterms),
        "dontcares": sorted(dontcares),
        "expr": expr,
        "cell_map": cell_map,
        "row_labels": row_labels,
        "col_labels": col_labels,
    }


# =========================
# UI
# =========================
st.title("Universal Karnaugh Map Solver")
st.markdown(
    """
Fill in the Karnaugh map with:

- `0` for false
- `1` for true
- `X` for don't care

The app supports valid Karnaugh map sizes up to **16x16**.
"""
)

with st.sidebar:
    st.header("Configuration")

    n_vars = st.selectbox(
        "Number of variables",
        options=list(range(2, 9)),
        index=2,
        help="2 to 8 variables supported. 8 variables corresponds to a 16x16 map.",
    )

    default_names = [chr(ord("A") + i) for i in range(n_vars)]
    custom_names = st.text_input(
        "Variable names (comma-separated)",
        value=",".join(default_names),
        help="Example: A,B,C,D",
    )

    raw_names = [x.strip() for x in custom_names.split(",") if x.strip()]
    if len(raw_names) != n_vars:
        st.warning("The number of variable names does not match the selected number of variables. Default names will be used.")
        var_names = default_names
    else:
        var_names = raw_names

    st.markdown("---")
    show_mapping = st.checkbox("Show minterm mapping table", value=True)
    show_expr_raw = st.checkbox("Show raw SymPy expression", value=False)

row_bits, col_bits, n_rows, n_cols = valid_map_shape(n_vars)
row_labels = gray_code(row_bits)
col_labels = gray_code(col_bits)

st.subheader("Map structure")
st.write(
    f"Variables: **{n_vars}** | "
    f"Rows: **{n_rows}** ({row_bits} bits) | "
    f"Columns: **{n_cols}** ({col_bits} bits)"
)

row_vars = var_names[:row_bits]
col_vars = var_names[row_bits:]

row_title = "".join(row_vars) if row_vars else "—"
col_title = "".join(col_vars) if col_vars else "—"

c1, c2 = st.columns(2)
with c1:
    st.write(f"**Row variables:** {row_title}")
    st.write(f"Gray order: {row_labels}")
with c2:
    st.write(f"**Column variables:** {col_title}")
    st.write(f"Gray order: {col_labels}")

st.subheader("Fill the Karnaugh map")

if "kmap_state" not in st.session_state:
    st.session_state.kmap_state = {}

state_key = f"kmap_{n_vars}"

if state_key not in st.session_state.kmap_state:
    df_init = build_kmap_dataframe(n_rows, n_cols)
    df_init.columns = col_labels
    df_init.index = row_labels
    st.session_state.kmap_state[state_key] = df_init

grid_df = st.session_state.kmap_state[state_key].copy()

edited_df = st.data_editor(
    grid_df,
    width="stretch",
    num_rows="fixed",
    key=f"editor_{n_vars}",
)

edited_df = edited_df.applymap(parse_cell_value)
st.session_state.kmap_state[state_key] = edited_df

col_a, col_b, col_c = st.columns(3)

with col_a:
    if st.button("Fill all with 0", width="stretch"):
        df_zero = build_kmap_dataframe(n_rows, n_cols)
        df_zero.columns = col_labels
        df_zero.index = row_labels
        st.session_state.kmap_state[state_key] = df_zero
        st.rerun()

with col_b:
    if st.button("Fill all with 1", width="stretch"):
        df_one = pd.DataFrame([["1"] * n_cols for _ in range(n_rows)], index=row_labels, columns=col_labels)
        st.session_state.kmap_state[state_key] = df_one
        st.rerun()

with col_c:
    if st.button("Checkerboard demo", width="stretch"):
        df_demo = pd.DataFrame(
            [[str((r + c) % 2) for c in range(n_cols)] for r in range(n_rows)],
            index=row_labels,
            columns=col_labels,
        )
        st.session_state.kmap_state[state_key] = df_demo
        st.rerun()

st.markdown("---")

if st.button("Solve Karnaugh Map", width="stretch"):
    result = solve_kmap(n_vars, edited_df, var_names)

    st.success("Map solved successfully.")

    st.subheader("Result")
    st.write(f"**Minterms:** {result['minterms']}")
    st.write(f"**Don't cares:** {result['dontcares']}")

    expr_pretty = format_sympy_expr(result["expr"])
    st.markdown(f"### Final simplified equation")
    st.code(expr_pretty, language="text")

    if show_expr_raw:
        st.markdown("### Raw SymPy expression")
        st.code(str(result["expr"]), language="python")

    if show_mapping:
        st.subheader("Cell → minterm mapping")
        map_df = pd.DataFrame(result["cell_map"])
        st.dataframe(map_df, width="stretch")

    st.subheader("Canonical interpretation")
    st.markdown(
        """
The solver interprets each `1` as a minterm and each `X` as a don't-care term,
then computes the minimized **sum-of-products (SOP)** expression.
"""
    )

    if len(result["minterms"]) == 0 and len(result["dontcares"]) == 0:
        st.info("All cells are 0, so the function is 0.")