"""
02_analysis.py
EDA, descriptive statistics, hypothesis tests, correlation and regression for the
pocket-money survey.  Writes tables to results/ and figures to figures/.

Run from the project root (after 01_clean_data.py):  python src/02_analysis.py
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

np.random.seed(42)   # seaborn strip-plot jitter uses the global random state: fixes the figures between runs
import pandas as pd
import seaborn as sns
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats_utils import chi_square, ols, one_way_anova, welch_t  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed" / "pocket_money_clean.csv"
RES = ROOT / "results"
FIG = ROOT / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

ALPHA = 0.05
PALETTE = ["#2F5D8A", "#E07A3F", "#4C9F70", "#B5485D", "#8E7CC3", "#C9A227"]
sns.set_theme(style="whitegrid", context="notebook", font="DejaVu Sans")
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 160, "axes.titleweight": "bold",
                     "axes.titlesize": 11, "axes.labelsize": 10})

df = pd.read_csv(DATA)
R = {}  # everything that goes into results.json

# ----------------------------------------------------------------- derived groupings
df["living2"] = np.where(df["living"].isin(["In hostel", "In room"]),
                         "Away from family", "With family")
df["income3"] = df["income_group"].replace({"50-70k": "50k+", "70k+": "50k+"})
LIVING_ORDER = ["With Parents", "With Relatives", "In room", "In hostel"]
INCOME_ORDER = ["10-30k", "30-50k", "50-70k", "70k+"]


def pct(x, d=1):
    return round(100 * x, d)


# ================================================================= 1. DESCRIPTIVES
N = len(df)
R["n_total"] = N
R["n_pm_usable"] = int(df["pm_received_rs"].notna().sum())

cat_rows = []
for col, label in [("gender", "Gender"), ("age_group", "Age"), ("stream", "Stream"),
                   ("origin", "Home area"), ("living", "Living arrangement"),
                   ("income_group", "Family monthly income (Rs)"),
                   ("recv_mode", "How pocket money is received"),
                   ("invests", "Invests savings"),
                   ("same_every_month", "Needs the same amount every month")]:
    vc = df[col].value_counts()
    for lvl, cnt in vc.items():
        cat_rows.append({"variable": label, "level": lvl, "n": int(cnt), "percent": pct(cnt / N)})
for col, label in [("use_academic", "Spends on academic items"), ("use_personal", "Spends on personal items"),
                   ("use_lending", "Lends to friends"), ("use_other", "Other spending"),
                   ("app_phonepe", "Uses PhonePe"), ("app_gpay", "Uses GPay"),
                   ("app_paytm", "Uses Paytm")]:
    cat_rows.append({"variable": label, "level": "Yes", "n": int(df[col].sum()), "percent": pct(df[col].mean())})
cat_tab = pd.DataFrame(cat_rows)
cat_tab.to_csv(RES / "descriptive_categorical.csv", index=False)

num_rows = []
for col, label in [("pm_received_rs", "Pocket money received (Rs/month)"),
                   ("log_pm", "ln(pocket money)"), ("saved_pct", "Share saved (%)"),
                   ("spent_pct", "Share spent (%)"), ("family_income_k", "Family income (Rs '000)"),
                   ("family_size_n", "Family size"), ("earners", "Earners in family")]:
    s = df[col].dropna()
    num_rows.append({"variable": label, "n": len(s), "mean": s.mean(), "sd": s.std(), "min": s.min(),
                     "q1": s.quantile(.25), "median": s.median(), "q3": s.quantile(.75),
                     "max": s.max(), "skewness": stats.skew(s), "cv_pct": 100 * s.std() / s.mean() if s.mean() else np.nan})
num_tab = pd.DataFrame(num_rows)
num_tab.round(3).to_csv(RES / "descriptive_numeric.csv", index=False)
R["pm_desc"] = num_tab.iloc[0].to_dict()
R["saved_desc"] = num_tab.iloc[2].to_dict()
R["pm_skew_raw"] = float(stats.skew(df["pm_received_rs"].dropna()))
R["pm_skew_log"] = float(stats.skew(df["log_pm"].dropna()))
R["pm_shapiro_raw_p"] = float(stats.shapiro(df["pm_received_rs"].dropna()).pvalue)
R["pm_shapiro_log_p"] = float(stats.shapiro(df["log_pm"].dropna()).pvalue)
R["pm_outliers_iqr"] = int(df["pm_outlier_iqr"].sum())
R["pm_geo_mean"] = float(np.exp(df["log_pm"].mean()))
R["pm_top_share"] = float(df.loc[df["pm_received_rs"] >= 2000, "pm_received_rs"].notna().sum())
R["pct_academic"] = pct(df["use_academic"].mean())
R["pct_personal"] = pct(df["use_personal"].mean())
R["pct_lending"] = pct(df["use_lending"].mean())
R["pct_invest"] = pct(df["invests_flag"].mean())
R["pct_same_every_month"] = pct(df["same_every_month_flag"].mean())
R["pct_phonepe"] = pct(df["app_phonepe"].mean())
R["pct_no_app"] = pct(df["app_none_reported"].mean())
R["pct_rural"] = pct((df["origin"] == "Rural").mean())
R["pct_male"] = pct(df["male"].mean())
R["pct_stream"] = {k: pct(v / N) for k, v in df["stream"].value_counts().items()}
R["invest_where"] = {k: int(v) for k, v in df["invest_where"].value_counts().items()}
R["pct_saved_zero"] = pct((df["saved_pct"] == 0).mean())
R["pct_spent_all"] = pct((df["spent_pct"] == 100).mean())

grp_rows = []
for col in ["gender", "origin", "living", "income_group", "stream", "recv_mode"]:
    g = df.groupby(col)["pm_received_rs"].agg(["count", "mean", "median", "std"]).reset_index()
    g.insert(0, "grouping", col)
    g = g.rename(columns={col: "group", "std": "sd"})
    gm = df.groupby(col)["log_pm"].apply(lambda s: np.exp(s.mean())).rename("geo_mean")
    g = g.merge(gm, left_on="group", right_index=True)
    grp_rows.append(g)
grp = pd.concat(grp_rows)
grp.round(1).to_csv(RES / "pocket_money_by_group.csv", index=False)

# ================================================================= 2. HYPOTHESIS TESTS
tests = []  # (id, family, description, p, effect text)
RT = {}

# ---- Welch t-tests on ln(pocket money)
t_gender = welch_t(df, "log_pm", "gender", ["Male", "Female"])
t_origin = welch_t(df, "log_pm", "origin", ["Urban", "Rural"])
RT["T1_gender"], RT["T2_origin"] = t_gender, t_origin
tests.append(("T1", "Welch t-test", "ln(pocket money): Male vs Female", t_gender["p"]))
tests.append(("T2", "Welch t-test", "ln(pocket money): Urban vs Rural", t_origin["p"]))

# ---- One-way ANOVA on ln(pocket money)
an_living = one_way_anova(df, "log_pm", "living", LIVING_ORDER)
an_income = one_way_anova(df, "log_pm", "income_group", INCOME_ORDER)
an_stream = one_way_anova(df, "log_pm", "stream", ["Science", "Commerce", "Arts"])
RT["A1_living"], RT["A2_income"], RT["A3_stream"] = an_living, an_income, an_stream
tests.append(("A1", "One-way ANOVA", "ln(pocket money) by living arrangement (4 groups)", an_living["p"]))
tests.append(("A2", "One-way ANOVA", "ln(pocket money) by family income band (4 groups)", an_income["p"]))
tests.append(("A3", "One-way ANOVA", "ln(pocket money) by stream (3 groups)", an_stream["p"]))

# ---- Mann-Whitney on the banded savings share
a = df.loc[df["living2"] == "Away from family", "saved_pct"]
b = df.loc[df["living2"] == "With family", "saved_pct"]
mw = stats.mannwhitneyu(a, b, alternative="two-sided")
RT["M1_saved_living2"] = {"median_away": float(a.median()), "median_family": float(b.median()),
                          "mean_away": float(a.mean()), "mean_family": float(b.mean()),
                          "n_away": len(a), "n_family": len(b), "U": float(mw.statistic), "p": float(mw.pvalue)}
tests.append(("M1", "Mann-Whitney U", "Share of pocket money saved: away from family vs with family", mw.pvalue))

# ---- Chi-square tests of independence
chi_specs = [
    ("C1", "invests", "gender", "Invests savings x Gender"),
    ("C2", "invests", "origin", "Invests savings x Home area (rural/urban)"),
    ("C3", "invests", "income3", "Invests savings x Family income (3 bands)"),
    ("C4", "same_every_month", "living2", "Needs same amount monthly x Living (family/away)"),
    ("C5", "use_personal", "gender", "Spends on personal items x Gender"),
    ("C6", "recv_mode", "origin", "Mode of receiving pocket money x Home area"),
]
chi_tables = {}
for cid, a_, b_, desc in chi_specs:
    res, tab = chi_square(df, a_, b_)
    res["description"] = desc
    RT[cid] = res
    chi_tables[cid] = tab
    tests.append((cid, "Chi-square", desc, res["p"]))
    tab.to_csv(RES / f"contingency_{cid}.csv")

summ = pd.DataFrame(tests, columns=["id", "test", "description", "p_raw"])
summ["significant_raw_0.05"] = summ["p_raw"] < ALPHA
summ.round(4).to_csv(RES / "hypothesis_tests_summary.csv", index=False)
R["tests"] = RT
R["tests_summary"] = summ.to_dict(orient="records")
R["n_tests"] = len(summ)
R["n_sig_raw"] = int(summ["significant_raw_0.05"].sum())

# ================================================================= 3. CORRELATION
cvars = {"pm_received_rs": "Pocket money", "family_income_k": "Family income",
         "family_size_n": "Family size", "earners": "Earners", "saved_pct": "% saved",
         "invests_flag": "Invests", "male": "Male", "urban": "Urban"}
cd = df[list(cvars)].copy()
sp = cd.corr(method="spearman")
pv = pd.DataFrame(np.nan, index=cd.columns, columns=cd.columns)
for i in cd.columns:
    for j in cd.columns:
        if i != j:
            ok = cd[[i, j]].dropna()
            pv.loc[i, j] = stats.spearmanr(ok[i], ok[j]).pvalue
sp.rename(index=cvars, columns=cvars).round(3).to_csv(RES / "correlation_spearman.csv")
pv.rename(index=cvars, columns=cvars).round(4).to_csv(RES / "correlation_spearman_pvalues.csv")
ok = df[["log_pm", "family_income_k"]].dropna()
pr = stats.pearsonr(ok["log_pm"], ok["family_income_k"])
R["corr"] = {
    "pm_income_spearman": float(sp.loc["pm_received_rs", "family_income_k"]),
    "pm_income_spearman_p": float(pv.loc["pm_received_rs", "family_income_k"]),
    "logpm_income_pearson": float(pr.statistic), "logpm_income_pearson_p": float(pr.pvalue),
    "pm_saved_spearman": float(sp.loc["pm_received_rs", "saved_pct"]),
    "pm_saved_spearman_p": float(pv.loc["pm_received_rs", "saved_pct"]),
    "income_size_spearman": float(sp.loc["family_income_k", "family_size_n"]),
    "income_size_spearman_p": float(pv.loc["family_income_k", "family_size_n"]),
    "income_earners_spearman": float(sp.loc["family_income_k", "earners"]),
    "income_earners_spearman_p": float(pv.loc["family_income_k", "earners"]),
    "saved_invests_spearman": float(sp.loc["saved_pct", "invests_flag"]),
    "saved_invests_spearman_p": float(pv.loc["saved_pct", "invests_flag"]),
    "pm_invests_spearman": float(sp.loc["pm_received_rs", "invests_flag"]),
    "pm_invests_spearman_p": float(pv.loc["pm_received_rs", "invests_flag"]),
}
# all pairs sorted by |rho|
pairs = []
cols = list(cvars)
for i_, i in enumerate(cols):
    for j in cols[i_ + 1:]:
        pairs.append({"var1": cvars[i], "var2": cvars[j], "spearman_rho": sp.loc[i, j], "p": pv.loc[i, j]})
pairs = pd.DataFrame(pairs).sort_values("spearman_rho", key=np.abs, ascending=False)
pairs.round(4).to_csv(RES / "correlation_pairs_ranked.csv", index=False)
R["corr_top_pairs"] = pairs.head(5).to_dict(orient="records")

# ================================================================= 4. REGRESSION
reg = df.dropna(subset=["log_pm"]).copy()
reg["living_hostel"] = (reg["living"] == "In hostel").astype(int)
reg["living_room"] = (reg["living"] == "In room").astype(int)
reg["living_relatives"] = (reg["living"] == "With Relatives").astype(int)

# --- Model 1: simple linear regression
X1 = np.column_stack([np.ones(len(reg)), reg["family_income_k"]])
m1 = ols(X1, reg["log_pm"], ["Intercept", "Family income (Rs '000)"])
# --- Model 2: multiple linear regression
terms = ["family_income_k", "family_size_n", "earners", "male", "urban",
         "living_hostel", "living_room", "living_relatives"]
names2 = ["Intercept", "Family income (Rs '000)", "Family size", "Earners", "Male",
          "Urban", "Lives in hostel*", "Lives in a room*", "Lives with relatives*"]
X2 = np.column_stack([np.ones(len(reg))] + [reg[t] for t in terms])
m2 = ols(X2, reg["log_pm"], names2)
# --- Sensitivity: drop IQR outliers on the raw scale
reg_no = reg[reg["pm_outlier_iqr"] == 0]
X2n = np.column_stack([np.ones(len(reg_no))] + [reg_no[t] for t in terms])
m2n = ols(X2n, reg_no["log_pm"], names2)


def pct_effect(row):
    """Percent change in pocket money for a 1-unit (or Rs 10k for income) change."""
    scale = 10 if "income" in row["term"].lower() else 1
    return pd.Series({"pct_change": 100 * (np.exp(scale * row["coef"]) - 1),
                      "pct_low": 100 * (np.exp(scale * row["ci_low"]) - 1),
                      "pct_high": 100 * (np.exp(scale * row["ci_high"]) - 1)})


t1, t2, t2n = m1["table"].copy(), m2["table"].copy(), m2n["table"].copy()
for t in (t1, t2, t2n):
    t[["pct_change", "pct_low", "pct_high"]] = t.apply(pct_effect, axis=1)
t1.round(4).to_csv(RES / "regression_model1_simple.csv", index=False)
t2.round(4).to_csv(RES / "regression_model2_multiple.csv", index=False)
t2n.round(4).to_csv(RES / "regression_model2_without_outliers.csv", index=False)


def model_summary(m, tab):
    return {"n": m["n"], "r2": m["r2"], "adj_r2": m["adj_r2"], "F": m["F"], "F_p": m["F_p"],
            "resid_se": m["resid_se"], "bp_p": m["bp_p"], "shapiro_resid_p": m["shapiro_resid_p"],
            "max_vif": max(m["vif"].values()) if m["vif"] else None,
            "n_cook_gt_4n": int((m["cooks"] > 4 / m["n"]).sum()), "max_cook": float(m["cooks"].max()),
            "coefs": tab.to_dict(orient="records")}


R["model1"] = model_summary(m1, t1)
R["model2"] = model_summary(m2, t2)
R["model2_no_outliers"] = model_summary(m2n, t2n)
R["model2_vif"] = m2["vif"]
pd.Series(m2["vif"], name="VIF").round(3).to_csv(RES / "regression_model2_vif.csv")

# ================================================================= 5. FIGURES
def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)


def bar_counts(ax, series, title, order=None, color=PALETTE[0], rot=0):
    vc = series.value_counts()
    if order:
        vc = vc.reindex(order)
    ax.bar(vc.index.astype(str), vc.values, color=color)
    for i, v in enumerate(vc.values):
        ax.text(i, v + 1, f"{v}\n({100 * v / N:.0f}%)", ha="center", va="bottom", fontsize=8)
    ax.set_title(title)
    ax.set_ylim(0, vc.max() * 1.28)
    ax.set_ylabel("Respondents")
    ax.tick_params(axis="x", rotation=rot, labelsize=8)
    ax.grid(axis="x", visible=False)


# Fig 1 demographics
fig, axs = plt.subplots(2, 3, figsize=(12, 7))
bar_counts(axs[0, 0], df["gender"], "Gender", ["Male", "Female"], PALETTE[0])
bar_counts(axs[0, 1], df["origin"], "Home area", ["Rural", "Urban"], PALETTE[1])
bar_counts(axs[0, 2], df["stream"], "Stream", ["Science", "Commerce", "Arts"], PALETTE[2])
bar_counts(axs[1, 0], df["age_group"], "Age", ["17", "18", "19", "20+"], PALETTE[3])
bar_counts(axs[1, 1], df["living"], "Living arrangement", LIVING_ORDER, PALETTE[4], rot=15)
bar_counts(axs[1, 2], df["income_group"], "Family monthly income (Rs)", INCOME_ORDER, PALETTE[5])
fig.suptitle(f"Who responded? (N = {N})", fontweight="bold", y=1.0)
save(fig, "fig01_demographics.png")

# Fig 2 distribution of pocket money
pm = df["pm_received_rs"].dropna()
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
axs[0].hist(pm, bins=np.arange(0, 10501, 500), color=PALETTE[0], edgecolor="white")
axs[0].axvline(pm.median(), color=PALETTE[1], ls="--", lw=2, label=f"Median Rs {pm.median():.0f}")
axs[0].axvline(pm.mean(), color=PALETTE[3], ls="--", lw=2, label=f"Mean Rs {pm.mean():.0f}")
axs[0].set(title="Monthly pocket money (raw)", xlabel="Rs per month", ylabel="Respondents")
axs[0].legend(fontsize=8)
lp = df["log_pm"].dropna()
axs[1].hist(lp, bins=14, color=PALETTE[2], edgecolor="white", density=True)
xs = np.linspace(lp.min(), lp.max(), 200)
axs[1].plot(xs, stats.norm.pdf(xs, lp.mean(), lp.std()), color="black", lw=1.5, label="Normal fit")
axs[1].set(title="ln(pocket money)", xlabel="ln(Rs)", ylabel="Density")
axs[1].legend(fontsize=8)
stats.probplot(lp, dist="norm", plot=axs[2])
axs[2].set_title("Normal Q-Q plot of ln(pocket money)")
axs[2].get_lines()[0].set(markerfacecolor=PALETTE[2], markeredgecolor=PALETTE[2], markersize=4)
axs[2].get_lines()[1].set(color="black")
save(fig, "fig02_pocket_money_distribution.png")

# Fig 3 pocket money by group
fig, axs = plt.subplots(2, 2, figsize=(11, 8))
for ax, (col, order, title) in zip(axs.ravel(), [
        ("gender", ["Male", "Female"], "By gender"), ("origin", ["Urban", "Rural"], "By home area"),
        ("living", LIVING_ORDER, "By living arrangement"), ("income_group", INCOME_ORDER, "By family income (Rs/month)")]):
    d = df.dropna(subset=["pm_received_rs"])
    sns.boxplot(data=d, x=col, y="pm_received_rs", order=order, ax=ax, color="#CFE0EF", fliersize=0, linewidth=1.2)
    sns.stripplot(data=d, x=col, y="pm_received_rs", order=order, ax=ax, color=PALETTE[0], alpha=.45, size=3, jitter=.22)
    ax.set_yscale("log")
    ax.set_yticks([10, 100, 500, 1000, 5000, 10000])
    ax.set_yticklabels(["10", "100", "500", "1k", "5k", "10k"])
    ax.set(title=title, xlabel="", ylabel="Pocket money, Rs/month (log scale)")
    ax.tick_params(axis="x", labelsize=9)
    for i, o in enumerate(order):
        n_ = int((d[col] == o).sum())
        ax.text(i, 8, f"n={n_}", ha="center", fontsize=8, color="#444")
    ax.set_ylim(6, 16000)
save(fig, "fig03_pocket_money_by_group.png")

# Fig 4 usage
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
use = pd.Series({"Academic items": df["use_academic"].mean(), "Personal items": df["use_personal"].mean(),
                 "Lending to friends": df["use_lending"].mean(), "Other": df["use_other"].mean()}) * 100
apps = pd.Series({"PhonePe": df["app_phonepe"].mean(), "GPay": df["app_gpay"].mean(),
                  "Paytm": df["app_paytm"].mean(), "Other app": df["app_other"].mean(),
                  "No app reported": df["app_none_reported"].mean()}) * 100
mode = df["recv_mode"].value_counts(normalize=True) * 100
for ax, s, title, c in [(axs[0], use, "What pocket money is spent on\n(multiple answers allowed)", PALETTE[0]),
                        (axs[1], apps, "Payment apps used\n(multiple answers allowed)", PALETTE[1]),
                        (axs[2], mode, "How pocket money is received", PALETTE[2])]:
    s = s.sort_values()
    ax.barh(s.index, s.values, color=c)
    for i, v in enumerate(s.values):
        ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
    ax.set(title=title, xlim=(0, 100), xlabel="% of respondents")
    ax.grid(axis="y", visible=False)
save(fig, "fig04_usage_and_payment.png")

# Fig 5 saving and investing
fig, axs = plt.subplots(1, 3, figsize=(13, 4))
sv = df["saved_pct"].value_counts().sort_index()
axs[0].bar([f"{int(k)}" for k in sv.index], sv.values, color=PALETTE[2])
axs[0].set(title="Share of pocket money saved\n(band midpoint, %)", xlabel="% saved", ylabel="Respondents")
axs[0].tick_params(axis="x", labelsize=8)
inv = df.groupby("income_group")["invests_flag"].agg(["mean", "count"]).reindex(INCOME_ORDER)
axs[1].bar(inv.index, inv["mean"] * 100, color=PALETTE[3])
for i, (m_, c_) in enumerate(zip(inv["mean"], inv["count"])):
    axs[1].text(i, m_ * 100 + 1, f"{m_ * 100:.0f}%\n(n={c_})", ha="center", fontsize=8)
axs[1].set(title="% who invest savings,\nby family income", xlabel="Family monthly income (Rs)",
           ylabel="% investing", ylim=(0, 60))
iw = df["invest_where"].value_counts()
axs[2].bar(iw.index, iw.values, color=PALETTE[4])
for i, v in enumerate(iw.values):
    axs[2].text(i, v + .5, str(v), ha="center", fontsize=9)
axs[2].set(title=f"Where investors put savings\n(n = {int(iw.sum())} investors)", ylabel="Respondents")
save(fig, "fig05_saving_and_investing.png")

# Fig 6 correlation heatmap
fig, ax = plt.subplots(figsize=(7.5, 6.2))
mask = np.triu(np.ones_like(sp, dtype=bool), k=1)
sns.heatmap(sp.rename(index=cvars, columns=cvars), mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            vmin=-1, vmax=1, square=True, linewidths=.5, cbar_kws={"shrink": .8}, ax=ax, annot_kws={"size": 8})
ax.set_title("Spearman rank correlations")
save(fig, "fig06_correlation_heatmap.png")

# Fig 7 income vs pocket money with fitted line
fig, ax = plt.subplots(figsize=(7.5, 5))
rng = np.random.default_rng(42)
jx = reg["family_income_k"] + rng.uniform(-3, 3, len(reg))
ax.scatter(jx, reg["pm_received_rs"], s=22, alpha=.5, color=PALETTE[0], label="Respondents (x jittered)")
xs = np.linspace(20, 110, 100)
b0, b1 = m1["table"]["coef"]
ax.plot(xs, np.exp(b0 + b1 * xs), color=PALETTE[1], lw=2.5, label="Fitted: exp(b0 + b1 x income)")
ax.set_yscale("log")
ax.set_yticks([10, 100, 500, 1000, 5000, 10000])
ax.set_yticklabels(["10", "100", "500", "1k", "5k", "10k"])
ax.set(xlabel="Family monthly income, Rs '000 (band midpoint)", ylabel="Pocket money, Rs/month (log scale)",
       title=f"Simple linear regression: ln(pocket money) ~ family income\nR\u00b2 = {m1['r2']:.3f}, p = {t1.loc[1, 'p']:.3f}")
ax.legend(fontsize=8)
save(fig, "fig07_simple_regression.png")

# Fig 8 regression diagnostics
fig, axs = plt.subplots(2, 2, figsize=(10.5, 8))
f_, r_ = m2["fitted"], m2["resid"]
axs[0, 0].scatter(f_, r_, s=18, alpha=.6, color=PALETTE[0])
axs[0, 0].axhline(0, color="black", lw=1)
axs[0, 0].set(title="Residuals vs fitted", xlabel="Fitted ln(pocket money)", ylabel="Residual")
stats.probplot(m2["std_resid"], dist="norm", plot=axs[0, 1])
axs[0, 1].set_title("Normal Q-Q of standardised residuals")
axs[0, 1].get_lines()[0].set(markerfacecolor=PALETTE[0], markeredgecolor=PALETTE[0], markersize=4)
axs[0, 1].get_lines()[1].set(color="black")
axs[1, 0].scatter(f_, np.sqrt(np.abs(m2["std_resid"])), s=18, alpha=.6, color=PALETTE[2])
axs[1, 0].set(title="Scale-location", xlabel="Fitted ln(pocket money)", ylabel="sqrt(|std. residual|)")
axs[1, 1].stem(np.arange(m2["n"]), m2["cooks"], markerfmt=" ", basefmt=" ", linefmt=PALETTE[3])
axs[1, 1].axhline(4 / m2["n"], color="black", ls="--", lw=1, label="4/n rule of thumb")
axs[1, 1].set(title="Cook's distance", xlabel="Observation", ylabel="Cook's D")
axs[1, 1].legend(fontsize=8)
save(fig, "fig08_regression_diagnostics.png")

# Fig 9 coefficient plot
cp = t2.iloc[1:].copy().iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5))
colors = [PALETTE[1] if p < ALPHA else "#8A8A8A" for p in cp["p"]]
ax.hlines(range(len(cp)), cp["pct_low"], cp["pct_high"], color=colors, lw=2.5)
ax.scatter(cp["pct_change"], range(len(cp)), color=colors, zorder=3, s=45)
ax.axvline(0, color="black", lw=1)
ax.set_yticks(range(len(cp)))
ax.set_yticklabels(cp["term"], fontsize=9)
ax.set(title="Multiple regression: effect on pocket money\n(orange = p < 0.05; income effect is per Rs 10,000)")
ax.set_xlabel("% change in pocket money (95% CI)\n* reference group: lives with parents")
save(fig, "fig09_regression_coefficients.png")

# ================================================================= 6. SAVE
def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


(RES / "results.json").write_text(json.dumps(clean(R), indent=2))
print("Analysis finished. Figures:", len(list(FIG.glob('*.png'))), "| tables:", len(list(RES.glob('*.csv'))))
