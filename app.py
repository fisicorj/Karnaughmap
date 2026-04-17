from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from typing import List, Tuple, Set, Dict

import pandas as pd
import streamlit as st
from sympy import symbols
from sympy.logic.boolalg import SOPform


st.set_page_config(page_title="Universal Karnaugh Map Solver", layout="wide")


# ============================================================
# Data structures
# ============================================================

@dataclass(frozen=True)
class Group:
    cells: frozenset[tuple[int, int]]
    minterms: frozenset[int]
    term_bits: tuple[int | None, ...]  # None means eliminated variable


# ============================================================
# Gray code / map helpers
# ============================================================

def gray_code(n_bits: int) -> list[str]:
    if n_bits == 0:
        return [""]
    if n_bits == 1:
        return ["0", "1"]
    prev = gray_code(n_bits - 1)
    return ["0" + x for x in prev] + ["1" + x for x in reversed(prev)]


def valid_layouts_up_to_8_vars() -> dict[str, int]:
    return {
        "2x2 (2 variables)": 2,
        "2x4 (3 variables)": 3,
        "4x4 (4 variables)": 4,
        "4x8 (5 variables)": 5,
        "8x8 (6 variables)": 6,
        "8x16 (7 variables)": 7,
        "16x16 (8 variables)": 8,
    }


def split_variables(n_vars: int) -> tuple[int, int, int, int]:
    row_bits = n_vars // 2
    col_bits = n_vars - row_bits
    n_rows = 2 ** row_bits
    n_cols = 2 ** col_bits
    return row_bits, col_bits, n_rows, n_cols


def parse_cell_value(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"0", "1", "X"}:
        return text
    return "0"


def build_empty_df(row_labels: list[str], col_labels: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [["0" for _ in range(len(col_labels))] for _ in range(len(row_labels))],
        index=row_labels,
        columns=col_labels,
    )


def binary_str_to_int(bits: str) -> int:
    return int(bits, 2) if bits else 0


def cell_bits(row_gray: str, col_gray: str) -> str:
    return row_gray + col_gray


def minterm_from_cell(row_gray: str, col_gray: str) -> int:
    return binary_str_to_int(cell_bits(row_gray, col_gray))


def format_expr_pretty(expr) -> str:
    if expr is True:
        return "1"
    if expr is False:
        return "0"

    text = str(expr)
    text = text.replace("&", " · ")
    text = text.replace("|", " + ")
    text = text.replace("~", "¬")
    return text


# ============================================================
# Boolean / grouping logic
# ============================================================

def pattern_from_bits(bits: str, n_vars: int) -> tuple[int | None, ...]:
    return tuple(int(b) for b in bits[:n_vars])


def merge_patterns(a: tuple[int | None, ...], b: tuple[int | None, ...]) -> tuple[int | None, ...] | None:
    diff_positions = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            if x is None or y is None:
                return None
            diff_positions.append(i)

    if len(diff_positions) != 1:
        return None

    idx = diff_positions[0]
    merged = list(a)
    merged[idx] = None
    return tuple(merged)


def qm_prime_implicants(minterms: list[int], dontcares: list[int], n_vars: int) -> list[tuple[tuple[int | None, ...], frozenset[int]]]:
    initial_terms = sorted(set(minterms) | set(dontcares))
    current = [(tuple(int(b) for b in f"{m:0{n_vars}b}"), frozenset([m])) for m in initial_terms]
    prime_implicants: set[tuple[tuple[int | None, ...], frozenset[int]]] = set()

    while True:
        used = set()
        next_round = set()

        for i in range(len(current)):
            for j in range(i + 1, len(current)):
                p1, c1 = current[i]
                p2, c2 = current[j]
                merged = merge_patterns(p1, p2)
                if merged is not None:
                    used.add((p1, c1))
                    used.add((p2, c2))
                    next_round.add((merged, frozenset(set(c1) | set(c2))))

        for item in current:
            if item not in used:
                prime_implicants.add(item)

        if not next_round:
            break

        # deduplicate by pattern + covered set
        current = sorted(next_round, key=lambda x: (str(x[0]), sorted(x[1])))

    # Keep only implicants that cover at least one real minterm
    filtered = []
    minterm_set = set(minterms)
    for pattern, covered in prime_implicants:
        real_covered = frozenset(m for m in covered if m in minterm_set)
        if real_covered:
            filtered.append((pattern, real_covered))

    # Remove duplicates by pattern keeping union of coverage
    merged_map: dict[tuple[int | None, ...], set[int]] = {}
    for pattern, covered in filtered:
        merged_map.setdefault(pattern, set()).update(covered)

    return [(pattern, frozenset(sorted(cov))) for pattern, cov in merged_map.items()]


def pattern_covers_minterm(pattern: tuple[int | None, ...], m: int, n_vars: int) -> bool:
    bits = f"{m:0{n_vars}b}"
    for p, b in zip(pattern, bits):
        if p is None:
            continue
        if int(b) != p:
            return False
    return True


def find_essential_and_cover(
    prime_implicants: list[tuple[tuple[int | None, ...], frozenset[int]]],
    minterms: list[int],
    n_vars: int,
) -> list[tuple[tuple[int | None, ...], frozenset[int]]]:
    minterm_set = set(minterms)

    coverage: dict[int, list[int]] = {m: [] for m in minterms}
    for idx, (pattern, covered) in enumerate(prime_implicants):
        for m in covered:
            coverage[m].append(idx)

    selected_indices: set[int] = set()

    # Essential prime implicants
    for m, idxs in coverage.items():
        if len(idxs) == 1:
            selected_indices.add(idxs[0])

    covered_so_far: set[int] = set()
    for idx in selected_indices:
        covered_so_far.update(prime_implicants[idx][1])

    remaining = sorted(minterm_set - covered_so_far)
    if not remaining:
        return [prime_implicants[i] for i in sorted(selected_indices)]

    candidate_indices = [i for i in range(len(prime_implicants)) if i not in selected_indices]

    # Brute force is fine here (<= 8 vars / teaching usage)
    best_combo = None
    best_score = None

    for r in range(1, len(candidate_indices) + 1):
        for combo in combinations(candidate_indices, r):
            union_cov = set()
            literal_count = 0

            for idx in combo:
                pattern, cov = prime_implicants[idx]
                union_cov.update(cov)
                literal_count += sum(1 for bit in pattern if bit is not None)

            if set(remaining).issubset(union_cov):
                total_groups = len(selected_indices) + len(combo)
                total_literals = sum(
                    sum(1 for bit in prime_implicants[i][0] if bit is not None)
                    for i in selected_indices
                ) + literal_count

                score = (total_groups, total_literals)
                if best_score is None or score < best_score:
                    best_score = score
                    best_combo = combo

        if best_combo is not None:
            break

    final_indices = set(selected_indices)
    if best_combo is not None:
        final_indices.update(best_combo)

    return [prime_implicants[i] for i in sorted(final_indices)]


def pattern_to_term(pattern: tuple[int | None, ...], var_names: list[str]) -> str:
    parts = []
    for bit, var in zip(pattern, var_names):
        if bit is None:
            continue
        parts.append(var if bit == 1 else f"¬{var}")
    return " · ".join(parts) if parts else "1"


def group_cells_from_pattern(
    pattern: tuple[int | None, ...],
    row_labels: list[str],
    col_labels: list[str],
) -> set[tuple[int, int]]:
    cells = set()
    for r, row_g in enumerate(row_labels):
        for c, col_g in enumerate(col_labels):
            bits = row_g + col_g
            ok = True
            for p, b in zip(pattern, bits):
                if p is None:
                    continue
                if int(b) != p:
                    ok = False
                    break
            if ok:
                cells.add((r, c))
    return cells


def build_solution_groups(
    selected_implicants: list[tuple[tuple[int | None, ...], frozenset[int]]],
    row_labels: list[str],
    col_labels: list[str],
) -> list[Group]:
    groups = []
    for pattern, covered in selected_implicants:
        cells = group_cells_from_pattern(pattern, row_labels, col_labels)
        groups.append(
            Group(
                cells=frozenset(cells),
                minterms=frozenset(covered),
                term_bits=pattern,
            )
        )
    return groups


def solve_kmap(
    n_vars: int,
    grid_df: pd.DataFrame,
    row_labels: list[str],
    col_labels: list[str],
    var_names: list[str],
):
    minterms = []
    dontcares = []
    cell_info = []

    for r, row_g in enumerate(row_labels):
        for c, col_g in enumerate(col_labels):
            val = parse_cell_value(grid_df.iat[r, c])
            m = minterm_from_cell(row_g, col_g)
            cell_info.append(
                {
                    "row_gray": row_g,
                    "col_gray": col_g,
                    "value": val,
                    "minterm": m,
                }
            )
            if val == "1":
                minterms.append(m)
            elif val == "X":
                dontcares.append(m)

    minterms = sorted(set(minterms))
    dontcares = sorted(set(dontcares))

    vars_sym = symbols(var_names)
    sympy_expr = SOPform(vars_sym, minterms, dontcares)

    prime_implicants = qm_prime_implicants(minterms, dontcares, n_vars)
    selected_implicants = find_essential_and_cover(prime_implicants, minterms, n_vars)
    groups = build_solution_groups(selected_implicants, row_labels, col_labels)

    return {
        "minterms": minterms,
        "dontcares": dontcares,
        "sympy_expr": sympy_expr,
        "groups": groups,
        "cell_info": cell_info,
        "prime_implicants": prime_implicants,
        "selected_implicants": selected_implicants,
    }


# ============================================================
# Styling / visualization
# ============================================================

GROUP_COLORS = [
    "#FFD54F", "#81C784", "#4FC3F7", "#FF8A65", "#BA68C8", "#AED581",
    "#F06292", "#7986CB", "#4DB6AC", "#FFB74D", "#90A4AE", "#CE93D8"
]


def render_highlighted_kmap(
    grid_df: pd.DataFrame,
    groups: list[Group],
    row_labels: list[str],
    col_labels: list[str],
    var_names: list[str],
) -> pd.io.formats.style.Styler:
    cell_to_groups: dict[tuple[int, int], list[int]] = {}
    for i, grp in enumerate(groups):
        for cell in grp.cells:
            cell_to_groups.setdefault(cell, []).append(i)

    def style_func(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)

        for r in range(data.shape[0]):
            for c in range(data.shape[1]):
                base = []
                raw_val = parse_cell_value(data.iat[r, c])

                if raw_val == "1":
                    base.append("font-weight: bold")
                elif raw_val == "X":
                    base.append("font-style: italic")

                memberships = cell_to_groups.get((r, c), [])
                if not memberships:
                    styles.iat[r, c] = "; ".join(base)
                    continue

                if len(memberships) == 1:
                    color = GROUP_COLORS[memberships[0] % len(GROUP_COLORS)]
                    base.append(f"background-color: {color}")
                    base.append("border: 2px solid #333")
                else:
                    color = "#FFF59D"
                    base.append(f"background: repeating-linear-gradient(45deg, {color}, {color} 8px, white 8px, white 16px)")
                    base.append("border: 2px solid #333")

                styles.iat[r, c] = "; ".join(base)

        return styles

    return grid_df.style.apply(style_func, axis=None)


def expression_from_groups(groups: list[Group], var_names: list[str]) -> str:
    if not groups:
        return "0"
    terms = [pattern_to_term(g.term_bits, var_names) for g in groups]
    return " + ".join(terms)


# ============================================================
# UI
# ============================================================

st.title("Universal Karnaugh Map Solver")
st.markdown(
    """
Fill the map with:

- `0` = false
- `1` = true
- `X` = don't care

The app supports valid Karnaugh maps up to **16x16** and automatically highlights the groups used in the final simplification.
"""
)

with st.sidebar:
    st.header("Configuration")

    mode = st.radio("Choose input mode", ["By number of variables", "By valid map format"])

    if mode == "By number of variables":
        n_vars = st.selectbox("Number of variables", list(range(2, 9)), index=2)
    else:
        layout_map = valid_layouts_up_to_8_vars()
        selected_layout = st.selectbox("Map format", list(layout_map.keys()), index=2)
        n_vars = layout_map[selected_layout]

    default_names = [chr(ord("A") + i) for i in range(n_vars)]
    raw_names = st.text_input(
        "Variable names (comma-separated)",
        value=",".join(default_names),
        help="Example: A,B,C,D",
    )
    parsed_names = [x.strip() for x in raw_names.split(",") if x.strip()]
    var_names = parsed_names if len(parsed_names) == n_vars else default_names

    if len(parsed_names) != n_vars:
        st.warning("Invalid number of names. Default variable names are being used.")

    st.markdown("---")
    show_mapping = st.checkbox("Show cell-to-minterm mapping", value=True)
    show_prime_implicants = st.checkbox("Show prime implicants", value=False)

row_bits, col_bits, n_rows, n_cols = split_variables(n_vars)
row_labels = gray_code(row_bits)
col_labels = gray_code(col_bits)

row_vars = var_names[:row_bits]
col_vars = var_names[row_bits:]

st.subheader("Map structure")
st.write(
    f"**Variables:** {n_vars} | "
    f"**Rows:** {n_rows} ({row_bits} bits) | "
    f"**Columns:** {n_cols} ({col_bits} bits)"
)

c1, c2 = st.columns(2)
with c1:
    st.write(f"**Row variables:** {''.join(row_vars) if row_vars else '—'}")
    st.write(f"**Gray order:** {row_labels}")
with c2:
    st.write(f"**Column variables:** {''.join(col_vars) if col_vars else '—'}")
    st.write(f"**Gray order:** {col_labels}")

state_key = f"kmap_state_{n_vars}"
if state_key not in st.session_state:
    st.session_state[state_key] = build_empty_df(row_labels, col_labels)

df_current = st.session_state[state_key].copy()

st.subheader("Fill the Karnaugh map")
edited_df = st.data_editor(
    df_current,
    width="stretch",
    num_rows="fixed",
    key=f"editor_{n_vars}",
)

if not isinstance(edited_df, pd.DataFrame):
    edited_df = pd.DataFrame(edited_df)

edited_df = edited_df.reindex(index=row_labels, columns=col_labels, fill_value="0")

for col in edited_df.columns:
    edited_df[col] = edited_df[col].map(parse_cell_value)

edited_df.index = row_labels
edited_df.columns = col_labels

st.session_state[state_key] = edited_df

edited_df = edited_df.applymap(parse_cell_value)
st.session_state[state_key] = edited_df

a, b, c, d = st.columns(4)

with a:
    if st.button("Fill all with 0", width="stretch"):
        st.session_state[state_key] = build_empty_df(row_labels, col_labels)
        st.rerun()

with b:
    if st.button("Fill all with 1", width="stretch"):
        st.session_state[state_key] = pd.DataFrame(
            [["1"] * n_cols for _ in range(n_rows)],
            index=row_labels,
            columns=col_labels,
        )
        st.rerun()

with c:
    if st.button("Checkerboard demo", width="stretch"):
        demo = pd.DataFrame(
            [[str((r + c_) % 2) for c_ in range(n_cols)] for r in range(n_rows)],
            index=row_labels,
            columns=col_labels,
        )
        st.session_state[state_key] = demo
        st.rerun()

with d:
    if st.button("Fill with X", width="stretch"):
        demo_x = pd.DataFrame(
            [["X"] * n_cols for _ in range(n_rows)],
            index=row_labels,
            columns=col_labels,
        )
        st.session_state[state_key] = demo_x
        st.rerun()

st.markdown("---")

if st.button("Solve Karnaugh Map", width="stretch"):
    result = solve_kmap(
        n_vars=n_vars,
        grid_df=edited_df,
        row_labels=row_labels,
        col_labels=col_labels,
        var_names=var_names,
    )

    minterms = result["minterms"]
    dontcares = result["dontcares"]
    groups = result["groups"]

    st.success("Map solved successfully.")

    st.subheader("Final result")
    if len(minterms) == 0 and len(dontcares) == 0:
        st.code("0", language="text")
    else:
        final_expr = expression_from_groups(groups, var_names)
        st.code(final_expr, language="text")

    st.write(f"**Minterms:** {minterms}")
    st.write(f"**Don't cares:** {dontcares}")
    st.write(f"**SymPy simplified form:** {format_expr_pretty(result['sympy_expr'])}")

    st.subheader("Highlighted grouping")
    styled_map = render_highlighted_kmap(edited_df, groups, row_labels, col_labels, var_names)
    st.dataframe(styled_map, width="stretch")

    st.subheader("Groups used in the solution")
    if not groups:
        st.info("No groups were needed because the function is 0.")
    else:
        legend_rows = []
        for i, grp in enumerate(groups, start=1):
            legend_rows.append(
                {
                    "Group": i,
                    "Color": GROUP_COLORS[(i - 1) % len(GROUP_COLORS)],
                    "Cells": sorted(list(grp.cells)),
                    "Minterms covered": sorted(list(grp.minterms)),
                    "Term": pattern_to_term(grp.term_bits, var_names),
                    "Group size": len(grp.cells),
                }
            )
        legend_df = pd.DataFrame(legend_rows)
        st.dataframe(legend_df, width="stretch")

    if show_mapping:
        st.subheader("Cell to minterm mapping")
        map_df = pd.DataFrame(result["cell_info"])
        st.dataframe(map_df, width="stretch")

    if show_prime_implicants:
        st.subheader("Prime implicants")
        prime_rows = []
        for pattern, covered in result["prime_implicants"]:
            prime_rows.append(
                {
                    "Pattern": str(pattern),
                    "Term": pattern_to_term(pattern, var_names),
                    "Covered minterms": sorted(list(covered)),
                    "Literal count": sum(1 for bit in pattern if bit is not None),
                }
            )
        st.dataframe(pd.DataFrame(prime_rows), width="stretch")

    st.subheader("How the result is obtained")
    st.markdown(
        """
The app converts the Karnaugh map into minterms and don't-care terms, computes prime implicants,
selects a minimal cover, and highlights the groups used in the final simplified equation.
"""
    )