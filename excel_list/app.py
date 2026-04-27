import json
import pandas as pd
import re

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


def classify(filename):
    name = filename.replace(".pdf", "")

    # Instrukce: 0 XXX
    if re.match(r"^0\s\d{3}", name):
        return "Instrukce"

    # Q Alerts: 2 čísla + mezera
    if re.match(r"^\d{2}\s", name):
        return "Q Alerts"

    # Vady: 3 čísla + mezera
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

    start_row = 0 # len(df) + 2  # leave one blank row

    worksheet.write(start_row, 4, "areas")

    for i, area in enumerate(AREAS_LIST):
        worksheet.write(start_row + i + 1, 4, area)


# 3 separate lists
vady, instrukce, qalerts = [], [], []

for doc in data["docs"]:
    filename = doc["filename"]
    tags = doc.get("tags", [])

    areas, pnos = split_tags(tags)

    row = {
        "List": filename,
        "Note": "",
        "Tags/Area": ", ".join(areas),
        "P/Nos": ", ".join(pnos)
    }

    category = classify(filename)

    if category == "Vady":
        vady.append(row)
    elif category == "Instrukce":
        instrukce.append(row)
    elif category == "Q Alerts":
        qalerts.append(row)


df_vady = pd.DataFrame(vady)
df_instrukce = pd.DataFrame(instrukce)
df_qalerts = pd.DataFrame(qalerts)


def autofit_columns(writer, df, sheet_name, extra_padding=2):
    worksheet = writer.sheets[sheet_name]

    for i, column in enumerate(df.columns):
        column_width = max(
            df[column].astype(str).map(len).max(),
            len(str(column))
        ) + extra_padding

        worksheet.set_column(i, i, column_width)

# IMPORTANT FIX: use xlsxwriter (not openpyxl)
# with pd.ExcelWriter("\\\\fsczmc01\\TEST_DOC_SCAN\\Source\\output.xlsx", engine="xlsxwriter") as writer:
with pd.ExcelWriter(
    r"\\fsczmc01\e$\TEST_DOC_SCAN\Source\output.xlsx",
    engine="xlsxwriter"
) as writer:
    df_vady.to_excel(writer, sheet_name="Vady", index=False)
    df_instrukce.to_excel(writer, sheet_name="Instrukce", index=False)
    df_qalerts.to_excel(writer, sheet_name="Q Alerts", index=False)

    # Add your additional tables
    add_areas_table(writer, "Vady", df_vady)

    # Autofit all sheets
    autofit_columns(writer, df_vady, "Vady")
    autofit_columns(writer, df_instrukce, "Instrukce")
    autofit_columns(writer, df_qalerts, "Q Alerts")