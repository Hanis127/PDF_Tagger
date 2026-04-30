import json
import pandas as pd
import re
import os

with open("C:\\Users\\dmc-admin\\PycharmProjects\\PDFTagger/tags.json", "r", encoding="utf-8") as f:
    data = json.load(f)

AREAS_TEXT = """01 ID
02 OD
03 Ohranění
04 Zámek/Šev
05 Cín
06 Podložka
07 Drážka/Díra/Notch
08 Rod Guide
09 Bimetal
10 Ostatní"""
AREAS_LIST = AREAS_TEXT.split("\n")

OUTPUT_PATH = r"\\fsczmc01\e$\TEST_DOC_SCAN\Source\output.xlsx"

def classify(filename):
    name = filename.replace(".pdf", "")
    if re.match(r"^0\s\d{3}", name):
        return "Instrukce"
    if re.match(r"^\d{2}\s", name):
        return "Q Alerts"
    if re.match(r"^\d{3}\s", name):
        return "Vady"
    return "Unsorted"

def split_tags(tags):
    areas = [t for t in tags if any(k in t for k in [
        "OD", "ID", "BIMETAL", "OHRANĚNÍ",
        "CÍN", "PODLOŽKA", "DRÁŽKA", "ROD", "OSTATNÍ"
    ])]
    pnos = [t for t in tags if t not in areas]
    return areas, pnos

def add_areas_table(writer, sheet_name, df):
    worksheet = writer.sheets[sheet_name]
    start_row = 0
    worksheet.write(start_row, 4, "areas")
    for i, area in enumerate(AREAS_LIST):
        worksheet.write(start_row + i + 1, 4, area)

# ── Load existing notes from the Excel file (if it exists) ──────────────────
existing_notes = {"Vady": {}, "Instrukce": {}, "Q Alerts": {}}

if os.path.exists(OUTPUT_PATH):
    try:
        for sheet in existing_notes:
            df_existing = pd.read_excel(OUTPUT_PATH, sheet_name=sheet, dtype=str)
            if "List" in df_existing.columns and "Note" in df_existing.columns:
                # Build a dict: filename -> note (skip empty/NaN notes)
                for _, row in df_existing.iterrows():
                    note = row["Note"]
                    if pd.notna(note) and str(note).strip() != "":
                        existing_notes[sheet][row["List"]] = str(note).strip()
    except Exception as e:
        print(f"Warning: could not read existing notes ({e}). Notes will be reset.")

# ── Build dataframes ─────────────────────────────────────────────────────────
vady, instrukce, qalerts = [], [], []

for doc in data["docs"]:
    filename = doc["filename"]
    tags = doc.get("tags", [])
    areas, pnos = split_tags(tags)
    category = classify(filename)

    # Pick the right notes dict for this category
    sheet_key = {"Vady": "Vady", "Instrukce": "Instrukce", "Q Alerts": "Q Alerts"}.get(category, "Vady")
    preserved_note = existing_notes.get(sheet_key, {}).get(filename, "")

    row = {
        "List": filename,
        "Note": preserved_note,          # ← restored from previous run
        "Tags/Area": ", ".join(areas),
        "P/Nos": ", ".join(pnos)
    }

    if category == "Vady":
        vady.append(row)
    elif category == "Instrukce":
        instrukce.append(row)
    elif category == "Q Alerts":
        qalerts.append(row)

df_vady     = pd.DataFrame(vady)
df_instrukce = pd.DataFrame(instrukce)
df_qalerts  = pd.DataFrame(qalerts)

# ── Write Excel ──────────────────────────────────────────────────────────────
def autofit_columns(writer, df, sheet_name, extra_padding=2):
    worksheet = writer.sheets[sheet_name]
    for i, column in enumerate(df.columns):
        column_width = max(
            df[column].astype(str).map(len).max(),
            len(str(column))
        ) + extra_padding
        worksheet.set_column(i, i, column_width)

with pd.ExcelWriter(OUTPUT_PATH, engine="xlsxwriter") as writer:
    df_vady.to_excel(writer,      sheet_name="Vady",      index=False)
    df_instrukce.to_excel(writer, sheet_name="Instrukce", index=False)
    df_qalerts.to_excel(writer,   sheet_name="Q Alerts",  index=False)

    add_areas_table(writer, "Vady", df_vady)

    autofit_columns(writer, df_vady,      "Vady")
    autofit_columns(writer, df_instrukce, "Instrukce")
    autofit_columns(writer, df_qalerts,   "Q Alerts")

print("Done! Notes preserved across runs.")