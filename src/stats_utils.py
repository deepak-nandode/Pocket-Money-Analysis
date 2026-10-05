"""Small, dependency-light statistical helpers (numpy + scipy only)."""
import numpy as np
import pandas as pd
from scipy import stats


def welch_t(df, value, group, levels):
    """Welch two-sample t-test (does not assume equal spread) plus a Mann-Whitney check."""
    a = df.loc[df[group] == levels[0], value].dropna().to_numpy()
    b = df.loc[df[group] == levels[1], value].dropna().to_numpy()
    r = stats.ttest_ind(a, b, equal_var=False)
    ci = r.confidence_interval(0.95)
    mw = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "group_a": levels[0], "group_b": levels[1], "n_a": len(a), "n_b": len(b),
        "mean_a": a.mean(), "mean_b": b.mean(), "t": r.statistic, "df": r.df, "p": r.pvalue,
        "diff": a.mean() - b.mean(), "ci_low": ci.low, "ci_high": ci.high,
        "mannwhitney_p": mw.pvalue,
        "shapiro_p_a": stats.shapiro(a).pvalue, "shapiro_p_b": stats.shapiro(b).pvalue,
        "ratio_geo_means": float(np.exp(a.mean() - b.mean())),
        "ratio_ci_low": float(np.exp(ci.low)), "ratio_ci_high": float(np.exp(ci.high)),
    }


def one_way_anova(df, value, group, order=None):
    """One-way ANOVA plus a Kruskal-Wallis check."""
    d = df[[value, group]].dropna()
    levels = order or sorted(d[group].unique())
    samples = [d.loc[d[group] == g, value].to_numpy() for g in levels]
    f = stats.f_oneway(*samples)
    allv = np.concatenate(samples)
    resid = np.concatenate([s - s.mean() for s in samples])
    kw = stats.kruskal(*samples)
    return {
        "levels": list(levels), "n": [len(s) for s in samples],
        "means": [s.mean() for s in samples], "F": f.statistic, "p": f.pvalue,
        "df_between": len(levels) - 1, "df_within": len(allv) - len(levels),
        "shapiro_resid_p": stats.shapiro(resid).pvalue,
        "kruskal_H": kw.statistic, "kruskal_p": kw.pvalue,
    }


def chi_square(df, a, b):
    """Chi-square test of independence (no continuity correction) with a Fisher check for 2x2 tables."""
    d = df[[a, b]].dropna()
    tab = pd.crosstab(d[a], d[b])
    chi2, p, dof, exp = stats.chi2_contingency(tab, correction=False)
    fisher_p = stats.fisher_exact(tab.to_numpy())[1] if tab.shape == (2, 2) else np.nan
    return {
        "n": int(tab.to_numpy().sum()), "chi2": chi2, "dof": int(dof), "p": p,
        "fisher_p": fisher_p, "min_expected": float(exp.min()),
        "pct_cells_expected_lt5": float((exp < 5).mean() * 100),
    }, tab


# ------------------------------------------------------------------ OLS (no statsmodels)
def ols(X, y, names):
    """Ordinary least squares with classical and HC3-robust inference + diagnostics."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, k = X.shape
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    fitted = X @ beta
    resid = y - fitted
    rss = float(resid @ resid)
    tss = float(((y - y.mean()) ** 2).sum())
    df_res = n - k
    sigma2 = rss / df_res
    se = np.sqrt(np.diag(sigma2 * xtx_inv))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), df_res)
    tcrit = stats.t.ppf(0.975, df_res)
    r2 = 1 - rss / tss
    adj = 1 - (1 - r2) * (n - 1) / df_res
    F = ((tss - rss) / (k - 1)) / sigma2 if k > 1 else np.nan
    Fp = stats.f.sf(F, k - 1, df_res) if k > 1 else np.nan

    h = np.einsum("ij,jk,ik->i", X, xtx_inv, X)          # leverage
    meat = X.T @ np.diag(resid ** 2 / (1 - h) ** 2) @ X   # HC3
    se_hc3 = np.sqrt(np.diag(xtx_inv @ meat @ xtx_inv))
    p_hc3 = 2 * stats.t.sf(np.abs(beta / se_hc3), df_res)

    cook = (resid ** 2 / (k * sigma2)) * h / (1 - h) ** 2
    # Breusch-Pagan (studentised / Koenker form)
    u2 = resid ** 2
    g = np.linalg.lstsq(X, u2, rcond=None)[0]
    r2_bp = 1 - ((u2 - X @ g) ** 2).sum() / ((u2 - u2.mean()) ** 2).sum()
    bp_stat = n * r2_bp
    bp_p = stats.chi2.sf(bp_stat, k - 1)

    vif = {}
    if k > 2:
        for j in range(1, k):
            others = np.delete(X, j, axis=1)
            b_o = np.linalg.lstsq(others, X[:, j], rcond=None)[0]
            r_o = 1 - ((X[:, j] - others @ b_o) ** 2).sum() / ((X[:, j] - X[:, j].mean()) ** 2).sum()
            vif[names[j]] = 1 / (1 - r_o)

    table = pd.DataFrame({"term": names, "coef": beta, "se": se, "t": t, "p": p,
                          "ci_low": beta - tcrit * se, "ci_high": beta + tcrit * se,
                          "se_hc3": se_hc3, "p_hc3": p_hc3})
    return {
        "table": table, "n": n, "k": k, "r2": r2, "adj_r2": adj, "F": F, "F_p": Fp,
        "resid_se": np.sqrt(sigma2), "fitted": fitted, "resid": resid, "leverage": h,
        "cooks": cook, "bp_stat": bp_stat, "bp_p": bp_p, "vif": vif,
        "shapiro_resid_p": stats.shapiro(resid).pvalue,
        "std_resid": resid / (np.sqrt(sigma2) * np.sqrt(1 - h)),
    }
