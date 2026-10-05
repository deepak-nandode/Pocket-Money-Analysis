"""
01_clean_data.py
Cleans the raw Google-Form export and writes an anonymised, analysis-ready CSV.

Run from the project root:  python src/01_clean_data.py
Input : data/raw/Pocket_Money_Dataset.xlsx  (sheet 1 = survey responses; NOT committed, contains e-mails)
Output: data/processed/pocket_money_clean.csv
        data/processed/cleaning_log.json
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Pocket_Money_Dataset.xlsx"
OUT = ROOT / "data" / "processed" / "pocket_money_clean.csv"
LOG = ROOT / "data" / "processed" / "cleaning_log.json"

# The questionnaire is bilingual (English / Marathi) and has duplicate headers
# ("Which way?" appears 3 times), so columns are renamed by position.
COLS = ["timestamp", "gender", "age", "stream", "department", "origin", "living",
        "family_size", "earners", "father_occ", "mother_occ", "family_income",
        "takes_pm", "pm_mode_recv", "pm_received", "pm_mode_recv2", "txn_app",
        "pm_use", "pm_spent", "pm_saved", "pm_save_mode", "invests",
        "invest_where", "same_every_month", "suggestions", "email"]

INCOME_MID = {  # monthly family income band -> midpoint in Rs '000
    "10,000 to 30,000": 20, "30,000 to 50,000": 40, "50,000 to 70,000": 60,
    "70,000 to 100,000": 85, "More than 100,000": 110}
INCOME_ORDER = list(INCOME_MID)
INCOME_SHORT = {"10,000 to 30,000": "10-30k", "30,000 to 50,000": "30-50k",
                "50,000 to 70,000": "50-70k", "70,000 to 100,000": "70-100k",
                "More than 100,000": ">100k"}


def band_mid(x):
    """'30% to 40%' -> 35.  Returns NaN if unparseable."""
    if pd.isna(x):
        return np.nan
    m = re.match(r"\s*(\d+)%\s*to\s*(\d+)%", str(x))
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    return np.nan


def parse_pm(x):
    """Monthly pocket money in Rs.  Ranges ('1000-2000') -> midpoint; free text -> NaN."""
    if pd.isna(x):
        return np.nan
    if isinstance(x, (int, float, np.integer, np.floating)):
        return float(x)
    s = str(x).replace(",", "").strip()
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", s)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2
    if re.fullmatch(r"\d+", s):
        return float(s)
    return np.nan


def main():
    log = {}
    df = pd.read_excel(RAW, sheet_name=0)
    df.columns = COLS
    log["rows_raw"] = len(df)

    # ---- duplicate check (done BEFORE the timestamp is dropped)
    # Two rows can share every answer yet be different people; only a repeated
    # timestamp would indicate a double submission.
    answers_only = df.drop(columns=["timestamp", "email", "suggestions"])
    log["rows_identical_in_answers"] = int(answers_only.duplicated(keep=False).sum())
    log["rows_with_repeated_timestamp"] = int(df["timestamp"].duplicated().sum())
    # -> identical answers but different timestamps (different days) => kept, not removed.

    # ---- privacy: drop direct identifiers and free text before anything is saved
    df = df.drop(columns=["email", "suggestions", "timestamp"])

    # ---- constant column
    log["takes_pm_unique_values"] = df["takes_pm"].unique().tolist()
    df = df.drop(columns=["takes_pm"])  # everyone answered "Yes" -> no information

    # ---- simple categoricals
    df["age_group"] = df["age"].astype(str).str.replace(r"Above 20.*", "20+", regex=True)
    for c in ["stream", "origin", "living"]:
        df[c] = df[c].str.strip()

    # ---- family size ("More than 6/6 पेक्षा जास्त" -> 7 = "7 or more")
    fs = df["family_size"].astype(str)
    df["family_size_n"] = np.where(fs.str.contains("More than"), 7,
                                   pd.to_numeric(fs, errors="coerce"))
    df["earners"] = pd.to_numeric(df["earners"], errors="coerce")

    # ---- family income
    df["family_income_k"] = df["family_income"].map(INCOME_MID)
    df["income_label"] = df["family_income"].map(INCOME_SHORT)
    # collapse the two sparse top bands (n=11 and n=2) for tests that need enough per cell
    df["income_group"] = df["family_income"].map({
        "10,000 to 30,000": "10-30k", "30,000 to 50,000": "30-50k",
        "50,000 to 70,000": "50-70k", "70,000 to 100,000": "70k+", "More than 100,000": "70k+"})

    # ---- pocket money received (Rs / month)
    df["pm_received_raw"] = df["pm_received"].astype(str)
    df["pm_received_rs"] = df["pm_received"].map(parse_pm)
    log["pm_received_ranges_to_midpoint"] = int(
        df["pm_received"].astype(str).str.fullmatch(r"\s*\d+\s*-\s*\d+\s*").sum())
    log["pm_received_unusable_text_or_blank"] = int(df["pm_received_rs"].isna().sum())
    df["log_pm"] = np.log(df["pm_received_rs"])

    q1, q3 = df["pm_received_rs"].quantile([.25, .75])
    hi = q3 + 1.5 * (q3 - q1)
    df["pm_outlier_iqr"] = (df["pm_received_rs"] > hi).astype(int)
    log["pm_iqr_upper_fence"] = float(hi)
    log["pm_outliers_flagged_not_removed"] = int(df["pm_outlier_iqr"].sum())

    # ---- spent / saved (% of pocket money, banded)
    # In the form the extreme options were typed as 0 and 1 (1 = 100 %).  Cross-tabs
    # support this: respondents with spent == 1 almost all report saved == 0.
    df["saved_pct"] = df["pm_saved"].map(lambda v: 0.0 if str(v).strip() == "0" else band_mid(v))
    df["spent_pct"] = df["pm_spent"].map(
        lambda v: 100.0 if str(v).strip() == "1" else (0.0 if str(v).strip() == "0" else band_mid(v)))
    df["spent_plus_saved"] = df["spent_pct"] + df["saved_pct"]
    log["spent_plus_saved_within_10pts_of_100"] = float(
        (df["spent_plus_saved"].sub(100).abs() <= 10).mean().round(3))

    # ---- multi-select: what pocket money is used for (strip the Marathi text first)
    use = df["pm_use"].fillna("").str.replace(r"/[^,]*", "", regex=True)
    df["use_academic"] = use.str.contains("Academic").astype(int)
    df["use_personal"] = use.str.contains("Personal").astype(int)
    df["use_lending"] = use.str.contains("Lending").astype(int)
    df["use_other"] = use.str.contains("Other").astype(int)

    # ---- multi-select: payment apps
    app = df["txn_app"].fillna("")
    df["app_phonepe"] = app.str.contains("Phone pay").astype(int)
    df["app_gpay"] = app.str.contains("Gpay").astype(int)
    df["app_paytm"] = app.str.contains("Paytm").astype(int)
    df["app_other"] = app.str.contains("Other|Bharat").astype(int)
    df["app_none_reported"] = df["txn_app"].isna().astype(int)

    df["recv_mode"] = df["pm_mode_recv"].str.strip()
    df["invests_flag"] = (df["invests"] == "Yes").astype(int)
    df["same_every_month_flag"] = (df["same_every_month"] == "Yes").astype(int)
    df["male"] = (df["gender"] == "Male").astype(int)
    df["urban"] = (df["origin"] == "Urban").astype(int)

    # Privacy: department (free text) and the parents' occupations are NOT kept. In a small
    # campus sample they could identify individual respondents, and no analysis uses them.
    keep = ["gender", "age_group", "stream", "origin", "living",
            "family_size_n", "earners",
            "family_income_k", "income_label", "income_group",
            "recv_mode", "pm_received_raw", "pm_received_rs", "log_pm", "pm_outlier_iqr",
            "spent_pct", "saved_pct", "spent_plus_saved",
            "use_academic", "use_personal", "use_lending", "use_other",
            "app_phonepe", "app_gpay", "app_paytm", "app_other", "app_none_reported",
            "invests", "invest_where", "invests_flag", "same_every_month",
            "same_every_month_flag", "male", "urban"]
    out = df[keep].copy()
    out.insert(0, "respondent_id", np.arange(1, len(out) + 1))

    log["columns_dropped_for_privacy"] = ["department", "father_occ", "mother_occ"]
    log["rows_clean"] = len(out)
    log["missing_by_column"] = {c: int(v) for c, v in out.isna().sum().items() if v}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    LOG.write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
