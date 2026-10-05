"""
03_build_report.py
Builds report/Pocket_Money_Statistical_Report.pdf from results/results.json, the CSV tables
and the figures.  Numbers are read from the results files so the report always matches the code.
NOTE: the interpretation sentences were written after inspecting these results; if you change
the data or the cleaning rules, re-read them.

Run from the project root (after 02_analysis.py):  python src/03_build_report.py
"""
import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
OUT = ROOT / "report" / "Pocket_Money_Statistical_Report.pdf"
OUT.parent.mkdir(exist_ok=True)
R = json.loads((RES / "results.json").read_text())
CLEAN = json.loads((ROOT / "data" / "processed" / "cleaning_log.json").read_text())
T = R["tests"]
M1, M2, M2N = R["model1"], R["model2"], R["model2_no_outliers"]

NAVY = colors.HexColor("#2F5D8A")
LIGHT = colors.HexColor("#EAF1F8")
ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9.6, leading=13.6, alignment=TA_JUSTIFY, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=8, leading=10.5, textColor=colors.HexColor("#444444"))
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, textColor=NAVY, spaceBefore=10, spaceAfter=6)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, textColor=NAVY, spaceBefore=8, spaceAfter=4)
title = ParagraphStyle("title", parent=ss["Title"], fontSize=24, textColor=NAVY, leading=29)
sub = ParagraphStyle("sub", parent=body, fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor("#555555"))
cell = ParagraphStyle("cell", parent=body, fontSize=8, leading=10, alignment=0, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)


def P(t, s=body):
    return Paragraph(t, s)


def B(items):
    return [Paragraph(t, bullet, bulletText="\u2022") for t in items]


def fp(p):
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def table(rows, widths, header=True, zebra=True):
    data = [[Paragraph(str(c), cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#BBBBBB")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(st))
    return t


def fig(name, width_cm, caption):
    from PIL import Image as PILImage
    w, h = PILImage.open(FIG / name).size
    img = Image(str(FIG / name), width=width_cm * cm, height=width_cm * cm * h / w)
    return KeepTogether([img, P(f"<i>{caption}</i>", small), Spacer(1, 6)])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(2 * cm, 1.2 * cm, "Pocket Money Expenditure Analysis - Statistical Report")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


S = []
# ------------------------------------------------------------------ title page
S += [Spacer(1, 5 * cm), P("Pocket Money Expenditure Analysis", title),
      P("A statistical study of how college students receive, spend, save and invest their pocket money", sub),
      Spacer(1, 1.2 * cm),
      P(f"Survey of {R['n_total']} college students &nbsp;|&nbsp; Python (pandas, SciPy, NumPy, Matplotlib, Seaborn)", sub),
      Spacer(1, .6 * cm),
      P("Prepared by: Deepak Nandode &nbsp;|&nbsp; Applied statistics project", sub),
      P("Data: survey collected by Vaishnavi Deshmukh (Aug-Sep 2023), used with permission", sub),
      Spacer(1, 4 * cm),
      P("Methods: data cleaning, descriptive statistics, exploratory visualisation, Welch t-tests, one-way ANOVA, "
        "chi-square tests of independence, Mann-Whitney and Kruskal-Wallis checks, "
        "Spearman and Pearson correlation, simple and multiple linear regression with diagnostics and a sensitivity analysis.", sub),
      PageBreak()]

# ------------------------------------------------------------------ 1 summary
d = R["pm_desc"]
S += [P("1. Executive summary", h1),
      P(f"<b>Question.</b> What drives how much pocket money a college student gets, and how do students use and manage it? "
        f"Data: {R['n_total']} survey responses ({R['n_pm_usable']} with a usable monthly pocket-money amount).")]
liv = T["A1_living"]
S += B([
    f"<b>Typical amount.</b> The median student gets <b>Rs {d['median']:.0f}</b> a month (mean Rs {d['mean']:.0f}; the mean is pulled up by a "
    f"few large values, skewness {d['skewness']:.1f}). Half of students receive between Rs {d['q1']:.0f} and Rs {d['q3']:.0f}.",
    f"<b>Where you live matters most.</b> Living away from parents is by far the strongest factor (one-way ANOVA, F(3, {liv['df_within']}) = {liv['F']:.2f}, "
    f"{fp(liv['p'])}). Students in a rented room or hostel receive roughly 2.6 to 3.3 times the pocket money "
    f"of students living with their parents, after controlling for other factors. This is the only effect that is robust to every check performed.",
    f"<b>Other differences are weaker.</b> Males, urban students and higher-income families receive more in some tests (p between 0.01 and 0.05), "
    f"but these mostly disappear when 13 very large amounts are set aside, and with twelve tests run a p-value just under 0.05 can be a chance result.",
    f"<b>Saving and investing.</b> About {R['pct_invest']:.0f}% of students invest some savings (mostly 'Other' options, then the stock market). "
    f"Students who receive more pocket money save a smaller share of it (Spearman rho = {R['corr']['pm_saved_spearman']:.2f}, {fp(R['corr']['pm_saved_spearman_p'])}).",
    f"<b>Model fit.</b> The multiple regression explains {100 * M2['r2']:.0f}% of the variation in log pocket money "
    f"(adjusted R<super>2</super> = {M2['adj_r2']:.2f}); family income alone explains only {100 * M1['r2']:.1f}%.",
    f"<b>Spending pattern.</b> {R['pct_academic']:.0f}% spend on academic items (photocopies, projects, college events), against {R['pct_personal']:.0f}% on personal items "
    f"such as food, films and trips (multiple answers allowed)."])

# ------------------------------------------------------------------ 2 data and cleaning
S += [P("2. Data and cleaning", h1),
      P("The data come from a bilingual (English/Marathi) online questionnaire answered by students in August-September 2023. "
        "It records demographics, family background, the amount of pocket money received, how it is spent, saved and invested, "
        "and payment habits. The file was not analysed as received; the following steps were applied (all reproducible in "
        "<font face='Courier'>src/01_clean_data.py</font>).")]
S += B([
    "<b>Privacy.</b> E-mail addresses, exact timestamps and free-text suggestions were removed before any analysis or publication. Department and the parents\' occupations were also left out of the published data because they could identify individuals; no analysis uses them.",
    "<b>Headers.</b> The questionnaire has duplicate column names (\"Which way?\" appears three times), so columns were renamed by position and Marathi text was stripped from multi-select answers.",
    f"<b>Duplicates.</b> Two rows have identical answers but were submitted on different days, so they were kept as separate respondents. No repeated timestamps were found.",
    f"<b>Pocket money.</b> {CLEAN['pm_received_ranges_to_midpoint']} answers given as ranges (e.g. 1000-2000) were converted to the midpoint; "
    f"{CLEAN['pm_received_unusable_text_or_blank']} answers (6 blank, 4 such as \"only when needed\") could not be quantified and were excluded from pocket-money analyses, leaving n = {R['n_pm_usable']}.",
    "<b>Share spent / saved.</b> Banded answers (e.g. \"30% to 40%\") were converted to band midpoints. The extreme options had been typed as 0 and 1; "
    f"1 was treated as 100%, which cross-tabulation supports. Spent + saved is within 10 points of 100% for {100 * CLEAN['spent_plus_saved_within_10pts_of_100']:.0f}% of respondents, so "
    "the share saved is used as the main savings measure.",
    "<b>Income, family size.</b> Income bands were coded to midpoints (Rs 20k, 40k, 60k, 85k, 110k per month); \"More than 6\" family members was coded 7. "
    "The two sparsest income bands (70-100k, above 100k) were merged as \"70k+\" for group comparisons.",
    f"<b>Outliers.</b> {R['pm_outliers_iqr']} respondents lie above the IQR upper fence (Rs {CLEAN['pm_iqr_upper_fence']:.0f}). They are real answers, not errors, so they were "
    "kept; the analysis uses ln(pocket money) and a sensitivity check re-fits the model without them.",
    "<b>Constant column.</b> Every respondent answered \"Yes\" to \"Do you take pocket money from parents?\", so that variable carries no information and was dropped."])
S += [P("<b>Assumption to note:</b> the questionnaire does not state the time period of the pocket-money amount; it is treated as a monthly amount "
        "(the follow-up question asks whether the respondent needs the same amount \"every month\"). A few very small values (Rs 10-50) may "
        "refer to a different period and cannot be verified.", body)]

# ------------------------------------------------------------------ 3 descriptive
S += [P("3. Descriptive statistics", h1), P("3.1 Who responded", h2),
      P(f"Respondents are {R['pct_male']:.0f}% male, {R['pct_rural']:.0f}% from rural areas and {R['pct_stream']['Science']:.0f}% from the science stream. "
        "Most are 17-19 years old, 45% live with their parents and 56% come from families earning Rs 10,000-30,000 a month. "
        "Because the sample is concentrated in a few groups, comparisons involving small groups (living with relatives, n = 12; arts stream, n = 13; income above Rs 70k, n = 13) have low power."),
      fig("fig01_demographics.png", 16.5, "Figure 1. Profile of the 203 respondents.")]
num = pd.read_csv(RES / "descriptive_numeric.csv")
rows = [["Variable", "n", "Mean", "SD", "Min", "Q1", "Median", "Q3", "Max", "Skew"]]
for _, r in num.iterrows():
    rows.append([r["variable"], int(r["n"])] + [f"{r[c]:.0f}" if abs(r[c]) >= 100 else (f"{r[c]:.1f}" if abs(r[c]) >= 10 else f"{r[c]:.2f}") for c in
                                              ["mean", "sd", "min", "q1", "median", "q3", "max", "skewness"]])
S += [P("3.2 Numeric variables", h2),
      table(rows, [4.6 * cm, .9 * cm, 1.5 * cm, 1.4 * cm, 1.1 * cm, 1.1 * cm, 1.5 * cm, 1.3 * cm, 1.3 * cm, 1.2 * cm]),
      Spacer(1, 6),
      P(f"Pocket money is strongly right-skewed (skewness {R['pm_skew_raw']:.2f}; coefficient of variation {d['cv_pct']:.0f}%) and fails a normality test "
        f"(Shapiro-Wilk {fp(R['pm_shapiro_raw_p'])}). After a log transformation the skewness falls to {R['pm_skew_log']:.2f} and the shape is close to normal "
        f"(Figure 2), although the Shapiro-Wilk test still detects small departures ({fp(R['pm_shapiro_log_p'])}). All parametric tests below therefore use ln(pocket money), with "
        "non-parametric tests reported as a robustness check. The geometric mean "
        f"(Rs {R['pm_geo_mean']:.0f}) is a better 'typical' value than the arithmetic mean."),
      fig("fig02_pocket_money_distribution.png", 17, "Figure 2. Pocket money before and after log transformation, with Q-Q plot."),
      P("3.3 Behaviour and payment habits", h2),
      P(f"Pocket money is mostly used for academic items ({R['pct_academic']:.0f}%); {R['pct_personal']:.0f}% report personal spending and {R['pct_lending']:.0f}% lend money to friends. "
        f"PhonePe is the most-used payment app ({R['pct_phonepe']:.0f}%), and {R['pct_no_app']:.0f}% reported no app. On average respondents save about "
        f"{R['saved_desc']['mean']:.0f}% of their pocket money; {R['pct_saved_zero']:.0f}% save nothing. {R['pct_invest']:.0f}% invest, and "
        f"{R['pct_same_every_month']:.0f}% say they need the same amount every month."),
      fig("fig04_usage_and_payment.png", 17, "Figure 3. Spending categories, payment apps and mode of receiving pocket money."),
      fig("fig05_saving_and_investing.png", 17, "Figure 4. Savings share, investment rate by family income, and investment choices."),
      PageBreak()]

# ------------------------------------------------------------------ 4 EDA by group
g = pd.read_csv(RES / "pocket_money_by_group.csv")
sel = g[g["grouping"].isin(["gender", "origin", "living", "income_group", "stream"])]
rows = [["Group", "n", "Median (Rs)", "Mean (Rs)", "Geo-mean (Rs)"]]
for _, r in sel.iterrows():
    rows.append([f"{r['grouping']}: {r['group']}", int(r["count"]), f"{r['median']:.0f}", f"{r['mean']:.0f}", f"{r['geo_mean']:.0f}"])
S += [P("4. Exploratory analysis: pocket money by group", h1),
      P("Figure 5 and the table show how pocket money differs across groups (log scale). The clearest visual gap is between students living with "
        "parents (median Rs 250) and those living in a room or hostel (median Rs 500-1,000). Differences by gender, home area and family income are "
        "smaller and overlap heavily, apart from the small top income band."),
      fig("fig03_pocket_money_by_group.png", 15.5, "Figure 5. Pocket money by gender, home area, living arrangement and family income (log scale)."),
      table(rows, [6.2 * cm, 1.4 * cm, 2.6 * cm, 2.6 * cm, 3 * cm]), PageBreak()]

# ------------------------------------------------------------------ 5 hypothesis tests
S += [P("5. Hypothesis tests", h1),
      P("All tests use a 5% significance level. Twelve tests were run, so a p-value just under 0.05 could be a chance result; conclusions therefore lean on "
        "effects that stay consistent across several checks. 'Parametric' tests were applied to ln(pocket money); the non-parametric "
        "equivalent is shown in the notes as a robustness check.")]
summ = pd.read_csv(RES / "hypothesis_tests_summary.csv")
rows = [["ID", "Test", "Comparison", "p", "Significant at 5%?"]]
for _, r in summ.iterrows():
    rows.append([r["id"], r["test"], r["description"], "<0.001" if r["p_raw"] < 0.001 else f"{r['p_raw']:.4f}", "Yes" if r["significant_raw_0.05"] else "No"])
S += [table(rows, [1.1 * cm, 2.6 * cm, 8.4 * cm, 1.6 * cm, 3.0 * cm]), Spacer(1, 8)]

t1, t2 = T["T1_gender"], T["T2_origin"]
S += [P("5.1 Welch t-tests (two groups)", h2)]
S += B([
    f"<b>T1 - Gender.</b> Hypotheses: H0 mean ln(pocket money) is equal for males and females. Males receive more: geometric-mean ratio {t1['ratio_geo_means']:.2f} "
    f"(95% CI {t1['ratio_ci_low']:.2f} to {t1['ratio_ci_high']:.2f}); t({t1['df']:.1f}) = {t1['t']:.2f}, {fp(t1['p'])}. "
    f"The Mann-Whitney check is borderline ({fp(t1['mannwhitney_p'])}), so this is suggestive, not conclusive.",
    f"<b>T2 - Home area.</b> No evidence of a difference between urban and rural students: ratio {t2['ratio_geo_means']:.2f} (95% CI {t2['ratio_ci_low']:.2f} to {t2['ratio_ci_high']:.2f}), "
    f"t({t2['df']:.1f}) = {t2['t']:.2f}, {fp(t2['p'])}. Welch's version was used because it does not assume the two groups have equal spread."])

a1, a2, a3 = T["A1_living"], T["A2_income"], T["A3_stream"]
S += [P("5.2 One-way ANOVA (three or more groups)", h2)]
S += B([
    f"<b>A1 - Living arrangement.</b> Strong evidence of differences: F({a1['df_between']}, {a1['df_within']}) = {a1['F']:.2f}, {fp(a1['p'])}. "
    f"Median pocket money is Rs 250 for students living with parents, Rs 500 in a hostel and Rs 1,000 in a rented room. "
    f"The Kruskal-Wallis test, which does not need bell-shaped data, was also run ({fp(a1['kruskal_p'])}) and agrees.",
    f"<b>A2 - Family income.</b> F({a2['df_between']}, {a2['df_within']}) = {a2['F']:.2f}, {fp(a2['p'])}. The difference comes from the 70k+ group "
    f"(n = 13; geometric mean Rs 1,556 against Rs 424-501 in the other bands); the three lower bands look alike. With only 13 students in the top band this is not conclusive.",
    f"<b>A3 - Stream.</b> F({a3['df_between']}, {a3['df_within']}) = {a3['F']:.2f}, {fp(a3['p'])}. Arts students receive the least "
    f"(geometric mean Rs 217 against Rs 574 for Science), but Arts has just 11 usable respondents. Treat as exploratory."])
m1 = T["M1_saved_living2"]
S += [P("5.3 Mann-Whitney U test (savings share)", h2),
      P(f"<b>M1.</b> The share saved is a banded, ordinal measure, so a rank test was used. Students living away from family save a median of {m1['median_away']:.0f}% versus "
        f"{m1['median_family']:.0f}% for those at home, which is not a significant difference (U = {m1['U']:.0f}, {fp(m1['p'])}). Despite getting more pocket money, students away "
        "from home do not save a smaller share.")]
S += [P("5.4 Chi-square tests of independence", h2),
      P("Chi-square tests were used for pairs of categorical variables. Every table meets the usual condition that expected "
        "counts are at least 5 (smallest expected count 6.9).")]
rows = [["ID", "Association tested", "n", "Chi-square", "df", "p"]]
for cid in ["C1", "C2", "C3", "C4", "C5", "C6"]:
    c = T[cid]
    rows.append([cid, c["description"], c["n"], f"{c['chi2']:.2f}", c["dof"], f"{c['p']:.3f}"])
S += [table(rows, [1.1 * cm, 8.6 * cm, 1.4 * cm, 2.4 * cm, 1.2 * cm, 2.0 * cm]), Spacer(1, 6),
      P("None of the six associations is statistically significant. The closest is investing by family income (C3, p = 0.066): the share of students who invest is about 21% in the lowest income band, 38% in the middle band and 29% in the highest, "
        "which is not a clean upward trend, and the sample is too small to confirm any pattern. Gender, home area and living arrangement are "
        "not associated with investing, needing a fixed monthly amount, personal spending, or the mode (cash/online) in which pocket money is received."),
      PageBreak()]

# ------------------------------------------------------------------ 6 correlation
c = R["corr"]
S += [P("6. Correlation analysis", h1),
      P("Spearman rank correlations were used because pocket money is skewed and several variables are ordinal. Figure 6 shows the matrix; all pairs are saved in "
        "<font face='Courier'>results/correlation_pairs_ranked.csv</font>."),
      fig("fig06_correlation_heatmap.png", 11.5, "Figure 6. Spearman correlation matrix (lower triangle).")]
S += B([
    f"<b>Pocket money vs % saved: rho = {c['pm_saved_spearman']:.2f} ({fp(c['pm_saved_spearman_p'])}).</b> A weak negative link: students who receive more save a smaller share of it. "
    "This is the clearest correlation in the data.",
    f"<b>Pocket money vs family income:</b> Spearman rho = {c['pm_income_spearman']:.2f} ({fp(c['pm_income_spearman_p'])}); Pearson r on ln(pocket money) = {c['logpm_income_pearson']:.2f} ({fp(c['logpm_income_pearson_p'])}). "
    "Family income is only very weakly related to pocket money, a recurring theme in this study.",
    f"<b>Family income vs earners:</b> rho = {c['income_earners_spearman']:.2f} ({fp(c['income_earners_spearman_p'])}), borderline; income is unrelated to family size (rho = {c['income_size_spearman']:.2f}).",
    "<b>Correlation is not causation.</b> These are associations in a cross-sectional sample."])
S += [PageBreak()]

# ------------------------------------------------------------------ 7 regression
def coef_rows(model):
    rows = [["Term", "Coef (ln scale)", "SE", "p", "p (robust HC3)", "% change in pocket money (95% CI)"]]
    for r in model["coefs"]:
        pc = (f"{r['pct_change']:.0f}% ({r['pct_low']:.0f} to {r['pct_high']:.0f})" if r["term"] != "Intercept" else "-")
        rows.append([r["term"], f"{r['coef']:.4f}", f"{r['se']:.4f}", "&lt;0.001" if r["p"] < .001 else f"{r['p']:.3f}",
                     "&lt;0.001" if r["p_hc3"] < .001 else f"{r['p_hc3']:.3f}", pc])
    return rows


inc1 = M1["coefs"][1]
S += [P("7. Regression analysis", h1),
      P("The response variable is ln(pocket money); coefficients are therefore interpreted as percentage changes: "
        "a coefficient b means a change of (exp(b) - 1) x 100% in pocket money. Family income is expressed per Rs 10,000 of monthly income."),
      P("7.1 Simple linear regression: ln(pocket money) on family income", h2),
      P(f"Each additional Rs 10,000 of family monthly income is associated with a {inc1['pct_change']:.1f}% higher pocket money "
        f"(95% CI {inc1['pct_low']:.1f}% to {inc1['pct_high']:.1f}%; {fp(inc1['p'])}). However R<super>2</super> is only {M1['r2']:.3f}: family income explains about "
        f"{100 * M1['r2']:.1f}% of the variation, so it is a poor predictor on its own."),
      fig("fig07_simple_regression.png", 11.5, "Figure 7. Fitted simple regression on the original Rs scale (log axis)."),
      P("7.2 Multiple linear regression", h2),
      P(f"Predictors: family income, family size, number of earners, gender, home area and living arrangement (reference: lives with parents). n = {M2['n']}."),
      table(coef_rows(M2), [3.7 * cm, 2.1 * cm, 1.6 * cm, 1.5 * cm, 2.3 * cm, 5.3 * cm]), Spacer(1, 6),
      P(f"<b>Fit:</b> R<super>2</super> = {M2['r2']:.3f}, adjusted R<super>2</super> = {M2['adj_r2']:.3f}, F = {M2['F']:.2f} ({fp(M2['F_p'])}), residual standard error = {M2['resid_se']:.2f} (log units). "
        "Living in a room or hostel has by far the largest effect: holding other variables fixed, pocket money is about 158% higher (hostel) and 227% higher (room) than for students living with parents. "
        "Family income (about +13% per Rs 10,000), male gender (+46%) and urban home (+64%) are significant at 5%, whereas family size and number of earners are not. "
        "Living with relatives is not significant, but only 10 respondents are in that group, so the confidence interval is very wide."),
      fig("fig09_regression_coefficients.png", 13, "Figure 8. Estimated effects with 95% confidence intervals."),
      P("7.3 Model diagnostics", h2)]
S += B([
    f"<b>Multicollinearity:</b> all variance inflation factors are below {M2['max_vif']:.2f} (rule of thumb: concern above 5-10).",
    f"<b>Constant variance:</b> Breusch-Pagan test {fp(M2['bp_p'])}; no evidence of heteroscedasticity. Robust HC3 standard errors give the same conclusions (except that the male effect is borderline, p = 0.051).",
    f"<b>Normality of residuals:</b> the Q-Q plot is close to a straight line, with a few very small pocket-money values in the lower tail; Shapiro-Wilk detects a mild departure ({fp(M2['shapiro_resid_p'])}). With n = {M2['n']} "
    "and consistent robust results this is not a serious concern.",
    f"<b>Influence:</b> {M2['n_cook_gt_4n']} observations exceed the 4/n guideline for Cook's distance, but the largest value is {M2['max_cook']:.2f}, far below 1, so no single respondent drives the results."])
S += [fig("fig08_regression_diagnostics.png", 14.5, "Figure 9. Diagnostic plots for the multiple regression."), PageBreak()]

# ------------------------------------------------------------------ 8 sensitivity
S += [P("8. Sensitivity analysis: are the results robust?", h1),
      P(f"The model was re-fitted after removing the {R['pm_outliers_iqr']} respondents above the IQR fence (pocket money above Rs {CLEAN['pm_iqr_upper_fence']:.0f}), leaving n = {M2N['n']}.")]
rows = [["Term", "Full model: % change (p)", "Without large amounts: % change (p)"]]
for a_, b_ in zip(M2["coefs"][1:], M2N["coefs"][1:]):
    rows.append([a_["term"], f"{a_['pct_change']:.0f}% ({'&lt;0.001' if a_['p'] < .001 else format(a_['p'], '.3f')})",
                 f"{b_['pct_change']:.0f}% ({'&lt;0.001' if b_['p'] < .001 else format(b_['p'], '.3f')})"])
S += [table(rows, [5 * cm, 5.5 * cm, 6.2 * cm]), Spacer(1, 6),
      P(f"The effect of living in a room or hostel is almost unchanged (about +160% to +173%) and stays highly significant. By contrast, the effects of family income, gender and home area "
        f"shrink and become non-significant (R<super>2</super> falls to {M2N['r2']:.2f}). These three effects therefore depend on a small number of respondents who receive large amounts and should "
        "be described as tentative. This agrees with the ANOVA, where the income effect was driven by the 13 respondents in the top income band.")]

# ------------------------------------------------------------------ 9 conclusions
S += [P("9. Conclusions", h1)]
S += B([
    "<b>Living arrangement is the dominant driver of pocket money.</b> Students living in a room or hostel receive roughly 2.6-3.3 times as much as those living with parents, regardless of income, gender or home area. "
    "A plausible explanation is that they must cover food, rent and travel themselves, but the survey cannot prove this.",
    "<b>Family income, gender and home area matter much less than expected.</b> They show small or borderline effects that mostly disappear when the large amounts are removed.",
    "<b>Saving and investing are largely unrelated to demographics.</b> No significant association was found between investing and gender, home area or living arrangement; students with more pocket money tend to save a smaller share.",
    "<b>Practical implication.</b> A college or financial-literacy programme looking for students who need money-management support should target students living away from home, who handle the largest amounts."])
S += [P("10. Limitations", h1)]
S += B([
    "<b>Convenience sample</b> of students from one institution (answered voluntarily); the results cannot be generalised to all students.",
    "<b>Self-reported, banded data.</b> Percent spent/saved and family income are in bands; midpoints add measurement error.",
    "<b>Unstated time period</b> for pocket money (assumed monthly) and a few implausibly small values.",
    "<b>Small subgroups</b> (living with relatives n = 10-12, arts n = 11-13, income above Rs 70k n = 13) limit statistical power.",
    "<b>Observational, cross-sectional data:</b> associations are not causal. Several predictors are related (e.g. gender and living arrangement), which regression only partly separates.",
    "<b>Multiple comparisons:</b> twelve tests were run, so an isolated p-value just under 0.05 may be a chance finding."])
S += [P("11. Reproducibility", h1),
      P("Run <font face='Courier'>python src/01_clean_data.py</font>, then <font face='Courier'>python src/02_analysis.py</font>, then "
        "<font face='Courier'>python src/03_build_report.py</font>. All tables are in <font face='Courier'>results/</font> and all figures in <font face='Courier'>figures/</font>. "
        "OLS, Breusch-Pagan, HC3 errors, VIF and Cook's distance are implemented directly with NumPy/SciPy in <font face='Courier'>src/stats_utils.py</font>.")]

doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
                        title="Pocket Money Expenditure Analysis - Statistical Report", author="Deepak Nandode")
doc.build(S, onFirstPage=lambda c, d: None, onLaterPages=footer)
print("Report written to", OUT)
