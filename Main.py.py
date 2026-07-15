import pyreadstat
import os
import re

# =========================
# FILE PATH
# =========================
file_path = r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav"

df, meta = pyreadstat.read_sav(file_path)

output_lines = []
processed_scales = set()


def clean_number(val):
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


def get_base_name(var):
    match = re.match(r"(.*?)(_R\d+)?$", var)
    return match.group(1)


for var in meta.column_names:

    if var not in meta.variable_value_labels:
        continue

    labels_dict = meta.variable_value_labels[var]

    numeric_values = []
    dk_values = []

    for val, label in labels_dict.items():
        val = clean_number(val)
        if isinstance(val, (int, float)):
            numeric_values.append(int(val))
        else:
            dk_values.append((val, label))

    numeric_values = sorted(list(set(numeric_values)))

    if len(numeric_values) not in [4, 5, 6, 11]:
        continue

    scale_signature = tuple(
        sorted((num, labels_dict[num]) for num in numeric_values)
    )

    if scale_signature in processed_scales:
        continue

    base = get_base_name(var)

    # =========================================
    # START DEFINE
    # =========================================
    output_lines.append(f"Const {base}_list=\"_")

    # =========================================
    # LABELS
    # =========================================
    for num in numeric_values:
        label_text = labels_dict[num]

        if len(numeric_values) == 6 and num == max(numeric_values):
            output_lines.append(f"_{num} '{label_text}',_")
        else:
            output_lines.append(f"_{num} '{label_text} (Fac={num})' [Factor={num}],_")

    for val, label in dk_values:
        output_lines.append(f"_{val} '{label}' [Missing],_")

    # =========================================
    # 4 / 5 / 6 SCALE
    # =========================================
    if len(numeric_values) in [4, 5, 6]:

        output_lines.append("Txt1 '' Text(),_")
        output_lines.append("m1 'Mean Score' Mean() [decimals=2],_")
        output_lines.append("st 'SD' Stddev() [decimals=2],_")
        output_lines.append("Txt2 '' Text(),_")

        # ✅ FIX: remove last value if 6-scale (treat as NA)
        if len(numeric_values) == 6:
            factor_values = numeric_values[:-1]
        else:
            factor_values = numeric_values

        max_val = max(factor_values)
        min_val = min(factor_values)

        if len(factor_values) >= 5:
            output_lines.append(f"N1 'Top 2 Box' combine({{_{max_val},_{max_val-1}}}),_")
            output_lines.append(f"N2 'Top Box' combine({{_{max_val}}}),_")
            output_lines.append(f"N3 'Bottom 2 Box' combine({{_{min_val},_{min_val+1}}}),_")
            output_lines.append(f"N4 'Bottom Box' combine({{_{min_val}}})\"")
        else:
            output_lines.append(f"N1 'Top Box' combine({{_{max_val}}}),_")
            output_lines.append(f"N2 'Bottom Box' combine({{_{min_val}}})\"")

    # =========================================
    # 11 POINT SCALE
    # =========================================
    if len(numeric_values) == 11:

        min_val = min(numeric_values)

        output_lines.append("Break '' Text(),_")
        output_lines.append("M1 'Mean' Mean() [decimals=2],_")
        output_lines.append("SD 'SD' Stddev() [decimals=2],_")
        output_lines.append("Break1 '' Text(),_")

        if min_val == 0:
            output_lines.append("N1 'Top 3 Box (NET)' combine({_10,_9,_8}),_")
            output_lines.append("N2 'Top 2 Box (NET)' combine({_10,_9}),_")
            output_lines.append("N3 'Bottom 3 Box (NET)' combine({_0,_1,_2}),_")
            output_lines.append("N4 'Bottom 2 Box (NET)' combine({_0,_1}),_")
            output_lines.append("Break2 '' Text(),_")
            output_lines.append("N11 'Promoters' combine({_10,_9}),_")
            output_lines.append("N12 'Passives' combine({_8,_7}),_")
            output_lines.append("N13 'Detractor' combine({_0,_1,_2,_3,_4,_5,_6}),_")
            output_lines.append("N14 'NPS Scores' derived('(N11-N13)')\"")
        else:
            output_lines.append("N1 'Top 3 Box (NET)' combine({_11,_10,_9}),_")
            output_lines.append("N2 'Top 2 Box (NET)' combine({_11,_10}),_")
            output_lines.append("N3 'Bottom 3 Box (NET)' combine({_1,_2,_3}),_")
            output_lines.append("N4 'Bottom 2 Box (NET)' combine({_1,_2}),_")
            output_lines.append("Break2 '' Text(),_")
            output_lines.append("N11 'Promoters' combine({_11,_10}),_")
            output_lines.append("N12 'Passives' combine({_9,_8}),_")
            output_lines.append("N13 'Detractor' combine({_1,_2,_3,_4,_5,_6,_7}),_")
            output_lines.append("N14 'NPS Scores' derived('(N11-N13)')\"")

    output_lines.append("\n")

    processed_scales.add(scale_signature)


# =====================================================
# ADDITIONAL BLOCK: AUTO CREATE SumZ BASED ON _R GRIDS
# =====================================================

r_pattern = re.compile(r"(.+)_R(\d+)$")

grid_tracker = {}

for var in meta.column_names:

    m = r_pattern.match(var)
    if not m:
        continue

    base = m.group(1)
    idx = int(m.group(2))

    if base not in grid_tracker:
        grid_tracker[base] = []

    grid_tracker[base].append(idx)


sum_index = 1

for base, rows in grid_tracker.items():

    rows = sorted(rows)

    output_lines.append(f"Const SumZ{sum_index}=\"_")
    output_lines.append("    b '' base(),_")

    for i in rows:

        if i == rows[-1]:
            output_lines.append(
                f"X{i}  '' base('{base}[{{_{i}}}].{base} IS NOT NULL')[IsHidden=True],_{i}\""
            )
        else:
            output_lines.append(
                f"X{i}  '' base('{base}[{{_{i}}}].{base} IS NOT NULL')[IsHidden=True],_{i},_"
            )

    output_lines.append("\n")

    sum_index += 1


# =========================
# SAVE FILE
# =========================
output_path = os.path.join(os.path.dirname(file_path), "Define.txt")

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("✅ Define file generated successfully!")
print("📁 Saved at:", output_path)

import pyreadstat
import re
from pathlib import Path
from pandas.api.types import is_numeric_dtype
from collections import defaultdict

# -----------------------------
# INPUT SPSS FILE
# -----------------------------
input_sav = Path(
    r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav"
)

df, meta = pyreadstat.read_sav(str(input_sav))

# -----------------------------
# CLEAN QUESTION TEXT
# -----------------------------
def get_main_question(label):

    clean = str(label).replace('\xa0', ' ').replace('\u200b', '')
    parts = clean.split(" - ")

    if len(parts) > 1:
        return parts[0].strip()

    return clean.strip()


# -----------------------------
# CHECK SAME VALUE LABELS
# -----------------------------
def same_value_labels(var1, var2):

    v1 = meta.variable_value_labels.get(var1, {})
    v2 = meta.variable_value_labels.get(var2, {})

    return v1 == v2


# -----------------------------
# CHECK IF _R GROUP IS GRID
# -----------------------------
def r_group_is_grid(base):

    r_vars = r_groups.get(base, [])

    # ✅ Updated logic: allow single _R variable grids
    if len(r_vars) == 1:
        return True

    if len(r_vars) < 2:
        return False

    first_labels = meta.variable_value_labels.get(r_vars[0], {})

    for v in r_vars[1:]:
        if meta.variable_value_labels.get(v, {}) != first_labels:
            return False

    return True


# -----------------------------
# PATTERNS
# -----------------------------
mc_pattern = re.compile(r'^(.+?)_O(\d+)$')
grid_pattern = re.compile(r'^(T_[A-Za-z0-9]+)_([0-9]+)$')
r_pattern = re.compile(r'^(.+?)_R(\d+)$')
rc_grid_pattern = re.compile(r'^(.*?)_R\d+_C\d+$')


# -----------------------------
# GROUP STORAGE
# -----------------------------
mc_groups = defaultdict(list)
grid_groups = defaultdict(list)
r_groups = defaultdict(list)
rc_grid_groups = defaultdict(list)


# -----------------------------
# COLLECT VARIABLE GROUPS
# -----------------------------
for var in df.columns:

    if rc_grid_pattern.match(var):
        rc_grid_groups[rc_grid_pattern.match(var).group(1)].append(var)

    elif mc_pattern.match(var):
        mc_groups[mc_pattern.match(var).group(1)].append(var)

    elif grid_pattern.match(var):
        grid_groups[grid_pattern.match(var).group(1)].append(var)

    elif r_pattern.match(var):
        r_groups[r_pattern.match(var).group(1)].append(var)


# -----------------------------
# SORT RC GRID VARIABLES
# -----------------------------
for g in rc_grid_groups:
    rc_grid_groups[g].sort()


# -----------------------------
# PRINT TRACKERS
# -----------------------------
printed_mc = set()
printed_grid = set()
printed_rc = set()

output_lines = []


# -----------------------------
# MAIN LOOP
# -----------------------------
sum_index1 =1

for var in df.columns:

    # -----------------------------
    # RC GRID (B4_R1_C1)
    # -----------------------------
    rc_match = rc_grid_pattern.match(var)

    if rc_match:

        base = rc_match.group(1)

        if base in printed_rc:
            continue

        printed_rc.add(base)

        first_var = rc_grid_groups[base][0]

        lbl = meta.column_labels[
            meta.column_names.index(first_var)
        ] or ""

        clean_qlabel = get_main_question(lbl)

        output_lines.append("")

        output_lines.append(
            f'for each cat in TableDoc.DataSet.MdmDocument.fields["{base}"].categories'
        )

        output_lines.append(
            '    TableDoc.Tables.AddNew("Table" + ctext(TableDoc.Tables.Count+1), '
            f'"{base}[" + cat.name + "].{base} * axis(" + BREAKID + ")", '
            f'"{clean_qlabel}" + " - " + cat.label)'
        )

        output_lines.append("next")
        output_lines.append("")

        output_lines.append(
            'TableDoc.Tables.AddNew("Table" + ctext(TableDoc.Tables.Count+1), '
            f'"{base}[..].{base} * {base}", '
            f'"{clean_qlabel}. - Summary Grid")'
        )

        output_lines.append("")
        continue


    # -----------------------------
    # HANDLE _R VARIABLES
    # -----------------------------
    r_match = r_pattern.match(var)

    if r_match:

        base = r_match.group(1)

        # GRID if value labels same
        if r_group_is_grid(base):

            if base in printed_grid:
                continue

            printed_grid.add(base)

            first_var = r_groups[base][0]

            lbl = meta.column_labels[
                meta.column_names.index(first_var)
            ] or ""

            clean_qlabel = get_main_question(lbl)

            output_lines.append("")

            output_lines.append(
                f'for each cat in TableDoc.DataSet.MdmDocument.fields["{base}"].categories'
            )

            output_lines.append(
                '    TableDoc.Tables.AddNew("Table" + ctext(TableDoc.Tables.Count+1), '
                f'"{base}[" + cat.name + "].{base} {{"+{base}_list+"}}* axis(" + BREAKID + ")", '
                f'"{clean_qlabel}" + " - " + cat.label)'
            )

            output_lines.append("next")

            output_lines.append(
                'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1),'
                f'"{base}[..].{base}{{"+{base}_list+"}} * {base}",'
                f'"{clean_qlabel}. - Summary Grid")'
            )

            output_lines.append(
                'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
                f'"{base}_Sum_T2B{{"+SUMZ{sum_index1}+"}} * axis(" + BREAKID + ")", '
                f'"{clean_qlabel}. Summary Top 2 Box")'
            )

            output_lines.append(
                'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
                f'"{base}_Sum_TB{{"+SUMZ{sum_index1}+"}} * axis(" + BREAKID + ")", '
                f'"{clean_qlabel}. Summary Top Box")'
            )

            output_lines.append(
                'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
                f'"{base}_Sum_B2B{{"+SUMZ{sum_index1}+"}} * axis(" + BREAKID + ")", '
                f'"{clean_qlabel}. Summary Bottom 2 Box")'
            )

            output_lines.append(
                'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
                f'"{base}_Sum_BB{{"+SUMZ{sum_index1}+"}} * axis(" + BREAKID + ")", '
                f'"{clean_qlabel}. Summary Bottom Box")'
            )

            output_lines.append("")
            sum_index1 +=1
            continue


        # MULTIPLE CHOICE if labels differ
        else:

            if r_match.group(2) != "1":
                continue

            lbl = meta.column_labels[
                meta.column_names.index(var)
            ] or ""

            safe_label = get_main_question(lbl).replace('"', "'")

            output_lines.append(
                f'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
                f'"{base} * axis(" + BREAKID + ")", '
                f'"{safe_label}")'
            )

            output_lines.append("")
            continue
    

    # -----------------------------
    # MULTIPLE CHOICE (_O)
    # -----------------------------
    mc_match = mc_pattern.match(var)

    if mc_match:

        base = mc_match.group(1)

        if base in printed_mc:
            continue

        printed_mc.add(base)

        lbl = meta.column_labels[
            meta.column_names.index(var)
        ] or ""

        safe_label = get_main_question(lbl).replace('"', "'")

        output_lines.append(
            f'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
            f'"{base} * axis(" + BREAKID + ")", '
            f'"{safe_label}")'
        )

        output_lines.append("")
        continue


    # -----------------------------
    # NORMAL GRID (T_Q1_1)
    # -----------------------------
    grid_match = grid_pattern.match(var)

    if grid_match:

        base = grid_match.group(1)

        if base in printed_grid:
            continue

        printed_grid.add(base)

        lbl = meta.column_labels[
            meta.column_names.index(grid_groups[base][0])
        ] or ""

        clean_qlabel = get_main_question(lbl)

        output_lines.append("")

        output_lines.append(
            f'for each cat in TableDoc.DataSet.MdmDocument.fields["{base}"].categories'
        )

        output_lines.append(
            '    TableDoc.Tables.AddNew("Table" + ctext(TableDoc.Tables.Count+1), '
            f'"{base}[" + cat.name + "].{base} * axis(" + BREAKID + ")", '
            f'"{clean_qlabel}" + " - " + cat.label)'
        )

        output_lines.append("next")
        output_lines.append("")
        continue


    # -----------------------------
    # SINGLE / CATEGORICAL
    # -----------------------------
    val_labels = meta.variable_value_labels.get(var, {})
    lbl = meta.column_labels[
        meta.column_names.index(var)
    ] or ""

    safe_label = get_main_question(lbl).replace('"', "'")

    if val_labels:

        output_lines.append(
            f'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
            f'"{var} * axis(" + BREAKID + ")", '
            f'"{safe_label}")'
        )

        output_lines.append("")
        continue


    # -----------------------------
    # NUMERIC MEAN
    # -----------------------------
    if is_numeric_dtype(df[var]):

        output_lines.append(
            f'TableDoc.Coding.CreateCategorizedVariable("{var}", "{var}.coding", "{{value}}")'
        )

        output_lines.append("")

        output_lines.append(
            f'TableDoc.Tables.AddNew("Table"+ctext(TableDoc.Tables.Count+1), '
            f'"{var}.coding{{..,txt \'\' text(),Mean \'Mean\' Mean({var})[decimals=2]}}'
            f'*Axis(" + BREAKID + ")", '
            f'"[{safe_label}] {safe_label}")'
        )

        output_lines.append("")

        output_lines.append(
            f'TableDoc.Tables["Table"+CText(TableDoc.Tables.Count)].Rules.AddNew(0,0)'
        )

        output_lines.append("")


# -----------------------------
# WRITE OUTPUT
# -----------------------------
output_path = input_sav.parent / "MRS.txt"

with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))

print("✅ MRS table syntax generated successfully:")
print(output_path)

import pyreadstat
import re
from pathlib import Path
from collections import defaultdict

# ==============================
# 1. INPUT SPSS FILE
# ==============================
sav_path = Path(
    r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav"
)

df, meta = pyreadstat.read_sav(sav_path)

# ==============================
# 2. GRID PATTERN (_R variables and T_xx grids)
# ==============================
r_pattern    = re.compile(r'^(.+?)_R(\d+)$')  # Q4_R1 etc
grid_pattern = re.compile(r'^(T_[A-Za-z0-9]+)_(\d+)$')  # T_xx grids

grid_groups = defaultdict(list)

# Collect T_xx grids
for var in meta.column_names:
    m = grid_pattern.match(var)
    if m:
        base_q = m.group(1)
        grid_groups[base_q].append(var)

# Collect _R variables that have matching value labels
r_groups = defaultdict(list)

for var in meta.column_names:
    m = r_pattern.match(var)
    if m:
        base, idx = m.groups()
        r_groups[base].append(var)

for base, vars_list in r_groups.items():

    # 🔹 NEW: allow single variable grids
    if len(vars_list) == 1:
        grid_groups[base].extend(vars_list)
        continue

    # Check value labels across all variables
    sig_list = [
        tuple(sorted(meta.variable_value_labels.get(v, {}).items()))
        for v in vars_list
    ]

    # If all signatures are identical AND non-empty → treat as GRID
    if all(sig == sig_list[0] and sig for sig in sig_list):
        grid_groups[base].extend(vars_list)
    # else → ignore (do not include in grid)

# ==============================
# 3. OUTPUT FILE
# ==============================
output_path = sav_path.parent / "Meta Summary.txt"

# ==============================
# 4. WRITE SYNTAX
# ==============================
with open(output_path, "w", encoding="utf-8") as f:

    for base_q, vars_list in grid_groups.items():

        # ---- CHECK VALUE LABELS (use first variable as reference)
        first_var = vars_list[0]
        value_labels = meta.variable_value_labels.get(first_var, {})

        # Skip if NO value labels
        if not value_labels:
            continue

        # ---- Collect COLUMN LABELS (statements)
        statements = []

        for var in vars_list:
            try:
                idx = meta.column_names.index(var)
                lbl = meta.column_labels[idx] or ""
            except ValueError:
                lbl = ""

            if lbl.strip():
                clean_lbl = lbl.strip()

                # ✅ TRIM everything before " - "
                if " - " in clean_lbl:
                    clean_lbl = clean_lbl.split(" - ", 1)[1].strip()

                statements.append(clean_lbl)

        # Skip if no column labels
        if not statements:
            continue

        summaries = [
            ("T2b", "Top 2 Box Summary"),
            ("Tb",  "Top Box Summary"),
            ("B2b", "Bottom 2 Box Summary"),
            ("Bb",  "Bottom Box Summary"),
        ]

        for suffix, title in summaries:
            summary_var = f"{base_q}_Sum_{suffix}"

            f.write(f'{summary_var} "{title} "\n')
            f.write('\tcategorical [..]\n')
            f.write('\t {\n')

            for i, stmt in enumerate(statements, start=1):
                clean_stmt = stmt.replace('"', "'")
                comma = "," if i < len(statements) else ""
                f.write(f'\t\t_{i} "{clean_stmt}"{comma}\n')

            f.write('\t};\n\n')

print("✅ Grid summaries generated ONLY where value labels exist and match")
print("📄 Output file:", output_path)

import pyreadstat
import re
from pathlib import Path
from collections import defaultdict

# =========================
# CONFIG (FIXED)
# =========================
TB  = [5]
T2B = [4, 5]
B2B = [1, 2]
BB  = [1]

# =========================
# INPUT FILE
# =========================
sav_path = Path(
    r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav"
)

df, meta = pyreadstat.read_sav(str(sav_path))

# =========================
# DETECT GRID VARIABLES
# T_xx grids AND _R variables where value labels match
# =========================
grid_pattern = re.compile(r'^(T_[A-Za-z0-9]+)_(\d+)$')   # T_xx grids
r_pattern    = re.compile(r'^(.+?)_R(\d+)$')             # _R rows

grids = defaultdict(list)

# --- T_xx grids
for var in df.columns:
    m = grid_pattern.match(var)
    if m:
        grids[m.group(1)].append(var)

# --- _R variables
r_groups = defaultdict(list)

for var in df.columns:
    m = r_pattern.match(var)
    if m:
        base, _ = m.groups()
        r_groups[base].append(var)

# Include _R as grid if value labels match
for base, vars_list in r_groups.items():

    # ✅ Updated logic: allow single variable grids
    if len(vars_list) == 1:
        grids[base].extend(vars_list)
        continue

    sig_list = [
        tuple(sorted(meta.variable_value_labels.get(v, {}).items()))
        for v in vars_list
    ]

    if all(sig == sig_list[0] and sig for sig in sig_list):
        grids[base].extend(vars_list)
    # else ignore

# Sort each grid numerically
for g in grids:
    grids[g].sort(key=lambda x: int(re.search(r'(\d+)$', x).group(1)))

# =========================
# OUTPUT FILE
# =========================
output_path = sav_path.parent / "Event Summary.txt"

with open(output_path, "w", encoding="utf-8") as f:

    for grid, vars_list in grids.items():

        if not vars_list:
            continue

        count = len(vars_list)

        # -------- GRID MAPPING --------
        for i in range(1, count + 1):
            f.write(f"{grid}[{{_{i}}}].{grid} = {vars_list[i-1]}\n")

        f.write("\n")

        # -------- LOGIC BLOCK --------
        def write_logic(values, target):

            val_str = ",".join(f"_{v}" for v in values)

            for i in range(1, count + 1):
                f.write(
                    f"if {grid}[{{_{i}}}].{grid} * ({{{val_str}}}) "
                    f"then {target} = {target} + {{_{i}}}\n"
                )

            f.write("\n")

        write_logic(TB,  f"{grid}_Sum_Tb")
        write_logic(T2B, f"{grid}_Sum_T2b")
        write_logic(B2B, f"{grid}_Sum_B2b")
        write_logic(BB,  f"{grid}_Sum_Bb")

print("✅ Logic-only syntax generated at:", output_path)


import pyreadstat
import re
from pathlib import Path
from pandas.api.types import is_numeric_dtype
from collections import defaultdict

# --------------------------------------------------
# Helpers
# --------------------------------------------------
def get_value_labels(meta, varname):
    return meta.variable_value_labels.get(varname, {})

# --------------------------------------------------
# Read data
# --------------------------------------------------
input_sav = Path(r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav")
df, meta = pyreadstat.read_sav(str(input_sav))

# --------------------------------------------------
# Patterns
# --------------------------------------------------
mc_pattern   = re.compile(r'^(.+?)_O(\d+)$')           
r_pattern    = re.compile(r'^(.+?)_R(\d+)$')           
rc_pattern   = re.compile(r'^(.+?)_R(\d+)_C(\d+)$')     
grid_pattern = re.compile(r'^(T_[A-Za-z0-9]+)_(\d+)$')  

# --------------------------------------------------
# Step 1: Multiple Choice (_O)
# --------------------------------------------------
mc_groups = defaultdict(list)

for var in df.columns:
    if not is_numeric_dtype(df[var]):
        continue
    m = mc_pattern.match(var)
    if m:
        base, opt = m.groups()
        mc_groups[base].append((int(opt), var))

mc_valid = {k: [v for _, v in sorted(vals)] for k, vals in mc_groups.items() if len(vals) > 1}

# --------------------------------------------------
# Step 2: _R variables (decide MC vs Grid)
# --------------------------------------------------
r_groups = defaultdict(list)

for var in df.columns:
    if not is_numeric_dtype(df[var]):
        continue
    m = r_pattern.match(var)
    if m:
        base, row = m.groups()
        r_groups[base].append((int(row), var))

r_mc = {}
r_grid = {}

for base, vals in r_groups.items():

    vals_sorted = [v for _, v in sorted(vals)]

    # ✅ Updated logic: allow single variable grids
    if len(vals_sorted) == 1:
        r_grid[base] = vals_sorted
        continue

    signatures = [tuple(sorted(get_value_labels(meta, v).items())) for v in vals_sorted]

    if all(sig == signatures[0] and sig for sig in signatures):
        r_grid[base] = vals_sorted
    else:
        r_mc[base] = vals_sorted

# --------------------------------------------------
# Step 3: T_xx grids
# --------------------------------------------------
grid_groups = defaultdict(list)

for var in df.columns:
    if not is_numeric_dtype(df[var]):
        continue
    m = grid_pattern.match(var)
    if m:
        base, idx = m.groups()
        grid_groups[base].append((int(idx), var))

grid_valid = {k: [v for _, v in sorted(vals)] for k, vals in grid_groups.items() if len(vals) > 1}

# --------------------------------------------------
# Step 4: RC Matrix Event Logic
# --------------------------------------------------
rc_groups = defaultdict(list)

for var in df.columns:
    if not is_numeric_dtype(df[var]):
        continue
    m = rc_pattern.match(var)
    if m:
        base, r, c = m.groups()
        key = f"{base}_R{r}"
        rc_groups[key].append((int(c), var))

rc_valid = {k: [v for _, v in sorted(vals)] for k, vals in rc_groups.items() if len(vals) > 1}

# --------------------------------------------------
# Step 5: Write output
# --------------------------------------------------
output_path = input_sav.parent / "Event.txt"

with open(output_path, "w", encoding="utf-8") as f:

    # ---------- Multiple Choice (_O) ----------
    if mc_valid or r_mc:
        f.write("\n\n")
        for base, vars_ in mc_valid.items():
            f.write(f"{base} = " + " + ".join(vars_) + "\n\n")
        for base, vars_ in r_mc.items():
            f.write(f"{base} = " + " + ".join(vars_) + "\n\n")

    # ---------- RC Matrix ----------
    if rc_valid:
        f.write("\n\n")
        for base, vars_ in rc_valid.items():
            f.write(f"{base} = " + " + ".join(vars_) + "\n\n")

    # ---------- Grid (_R with same labels) ----------
    if r_grid or grid_valid:
        f.write("\n\n")
        for base, vars_ in r_grid.items():
            for i, v in enumerate(vars_, start=1):
                f.write(f"{base}[{{_{i}}}].{base} = {v}\n")
            f.write("\n")

        for base, vars_ in grid_valid.items():
            for i, v in enumerate(vars_, start=1):
                f.write(f"{base}[{{_{i}}}].{base} = {v}\n")
            f.write("\n")

print("✅ Output generated at:", output_path)

import re
from collections import defaultdict
from pandas.api.types import is_numeric_dtype


def get_var_label(meta, varname):
    try:
        idx = meta.column_names.index(varname)
        return meta.column_labels[idx] or varname
    except ValueError:
        return varname


def get_value_labels(meta, varname):
    return meta.variable_value_labels.get(varname, {})


# --------------------------------------------------
# Clean label for simple R grids
# --------------------------------------------------
def clean_option_label(label):

    if " - " in label:
        return label.split(" - ")[-1].strip()

    return label.strip()


# --------------------------------------------------
# Detect R blocks
# --------------------------------------------------
def detect_r_blocks(df, meta):

    r_pattern = re.compile(r'^(.+)_R(\d+)$')
    blocks = defaultdict(list)

    for var in df.columns:

        if not is_numeric_dtype(df[var]):
            continue

        if "_L" in var:
            continue

        m = r_pattern.match(var)

        if m:
            blocks[m.group(1)].append(var)

    grids = {}
    mc = {}

    for base, vars_ in blocks.items():

        vars_.sort(key=lambda x: int(r_pattern.match(x).group(2)))

        # -------------------------------
        # NEW: if only ONE variable treat as GRID
        # -------------------------------
        if len(vars_) == 1:
            grids[base] = vars_
            continue

        signatures = {
            tuple(get_value_labels(meta, v).items())
            for v in vars_
        }

        if len(signatures) == 1 and list(signatures)[0]:
            grids[base] = vars_
        else:
            mc[base] = vars_

    return grids, mc


# --------------------------------------------------
# Detect RC and LR blocks
# --------------------------------------------------
def detect_rc_blocks(df):

    rc_pattern = re.compile(r'^(.+)_R(\d+)_C(\d+)$')
    lr_pattern = re.compile(r'^(.+)_L(\d+)_R(\d+)$')

    blocks = defaultdict(list)

    for var in df.columns:

        if not is_numeric_dtype(df[var]):
            continue

        m = rc_pattern.match(var)

        if m:
            blocks[m.group(1)].append(var)
            continue

        m = lr_pattern.match(var)

        if m:
            blocks[m.group(1)].append(var)

    return blocks


# --------------------------------------------------
# Generate GRID syntax (R grids)
# --------------------------------------------------
def generate_grid_syntax(base, vars_, meta):

    merged_labels = {}

    for v in vars_:
        merged_labels.update(get_value_labels(meta, v))

    if not merged_labels:
        return []

    sorted_vals = sorted(merged_labels.items())

    lines = []

    lines.append(f'{base} " " loop')
    lines.append('{')

    for i, v in enumerate(vars_, start=1):

        raw_lbl = get_var_label(meta, v)
        clean_lbl = clean_option_label(raw_lbl).replace('"', "'")

        lines.append(f'  _{i} "{clean_lbl}",')

    if lines[-1].endswith(','):
        lines[-1] = lines[-1][:-1]

    lines.append('} fields')
    lines.append('(')
    lines.append(f'    {base} " " categorical [..]')
    lines.append('    {')

    for i, (code, lbl) in enumerate(sorted_vals):

        comma = ',' if i < len(sorted_vals) - 1 else ''

        clean_lbl = str(lbl).replace('"', "'").strip()

        lines.append(f'        _{int(float(code))} "{clean_lbl}"{comma}')

    lines.append('    };')
    lines.append(') expand grid;')
    lines.append('')

    return lines


# --------------------------------------------------
# Generate MULTIPLE CHOICE
# --------------------------------------------------
def generate_mc_from_r(base, vars_, meta):

    lines = []

    lines.append(f'{base} " " categorical [..] {{')

    merged_labels = {}

    for v in vars_:
        merged_labels.update(get_value_labels(meta, v))

    if merged_labels:

        sorted_vals = sorted(merged_labels.items())

        for i, (val, lbl) in enumerate(sorted_vals):

            comma = ',' if i < len(sorted_vals) - 1 else ''

            clean_lbl = str(lbl).replace('"', "'").strip()

            code = int(float(val))

            lines.append(f'  _{code} "{clean_lbl}"{comma}')

    else:

        for i, v in enumerate(vars_, start=1):

            raw_lbl = get_var_label(meta, v)
            lbl = clean_option_label(raw_lbl).replace('"', "'")

            comma = ',' if i < len(vars_) else ''

            lines.append(f'  _{i} "{lbl}"{comma}')

    lines.append('};\n')

    return lines


# --------------------------------------------------
# Generate LOOP GRID (RC and LR)
# --------------------------------------------------
def generate_multi_grid_syntax(base, vars_, meta):

    lr_pattern = re.compile(r'^(.+)_L(\d+)_R(\d+)$')
    rc_pattern = re.compile(r'^(.+)_R(\d+)_C(\d+)$')

    loops = {}
    merged_labels = {}

    for v in vars_:

        m_lr = lr_pattern.match(v)
        m_rc = rc_pattern.match(v)

        if m_lr:
            loop = int(m_lr.group(2))

        elif m_rc:
            loop = int(m_rc.group(2))

        else:
            continue

        var_label = get_var_label(meta, v)

        parts = var_label.split(" - ")

        if m_rc and len(parts) >= 3:
            brand = parts[-2].strip()

        elif m_lr and len(parts) >= 1:
            brand = parts[-1].strip()

        else:
            brand = clean_option_label(var_label)

        if loop not in loops:
            loops[loop] = brand

        vlabels = get_value_labels(meta, v)

        for code, lbl in vlabels.items():
            merged_labels[int(float(code))] = lbl.strip()

    sorted_loops = sorted(loops.items())
    sorted_vals = sorted(merged_labels.items())

    lines = []

    lines.append(f'{base} " " loop')
    lines.append('{')

    for i, (loop, brand) in enumerate(sorted_loops):

        comma = ',' if i < len(sorted_loops) - 1 else ''

        brand = brand.replace('"', "'")

        lines.append(f'  _{loop} "{brand}"{comma}')

    lines.append('} fields')
    lines.append('(')
    lines.append(f'    {base} " " categorical [..]')
    lines.append('    {')

    for i, (code, lbl) in enumerate(sorted_vals):

        comma = ',' if i < len(sorted_vals) - 1 else ''

        clean_lbl = str(lbl).replace('"', "'")

        lines.append(f'        _{code} "{clean_lbl}"{comma}')

    lines.append('    };')
    lines.append(') expand grid;')
    lines.append('')

    return lines

# --------------------------------------------------
# Main
# --------------------------------------------------
def generate_all_syntax(sav_path, output_path):
    df, meta = pyreadstat.read_sav(sav_path)

    grids, mc = detect_r_blocks(df, meta)
    rc_blocks = detect_rc_blocks(df)

    all_lines = []

    # Multiple choice
    for base, vars_ in mc.items():
        all_lines.extend(generate_mc_from_r(base, vars_, meta))

    # Grid
    for base, vars_ in grids.items():
        all_lines.extend(generate_grid_syntax(base, vars_, meta))

    # RC Matrix grid
    for base, vars_ in rc_blocks.items():
        all_lines.extend(generate_multi_grid_syntax(base, vars_, meta))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for line in all_lines:
            f.write(line + "\n")

    print(f"✅ Syntax written to {output_path}")

# --------------------------------------------------
# Run
# --------------------------------------------------
if __name__ == "__main__":
    sav_file = r"C:\Users\Ragul-lap01\OneDrive - 4sight-global.com\Backup  Drive's files - 4Sight UAE Data operations\Raguram\Data Processing\2026\June\DHA CSat Public Health 2026\SPSS\Public Health.sav"
    sav_path = Path(sav_file)
    output_path = sav_path.parent / "Meta.txt"

    generate_all_syntax(sav_path, output_path)