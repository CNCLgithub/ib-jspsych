import marimo

__generated_with = "0.19.6"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import json
    import numpy as np
    import polars as pl
    import altair as alt
    from collections.abc import Callable
    from functools import partial
    from scipy.stats import linregress, ttest_ind, chi2_contingency, fisher_exact
    import statsmodels.api as sm
    from statsmodels.formula.api import ols, logit, glm
    return alt, fisher_exact, pl, ttest_ind


@app.cell
def _(pl):
    all_models = pl.read_csv("data/study1/aggregate.csv")
    by_scene = all_models.group_by("model", "scene").agg(
        pl.col("count_error").mean().alias("count_error"),
        pl.col("time").mean().alias("time"),
    )
    return all_models, by_scene


@app.cell
def _(all_models, mo):
    mo.ui.table(all_models)
    return


@app.cell
def _(all_models, pl):
    NOTICE_THRESH = 18


    model_notice_summary = (
        all_models.with_columns(noticed=pl.col("ndetected").gt(NOTICE_THRESH))
        .group_by("model", "color")
        .agg(
            yes=pl.col("noticed").sum(),
            no=pl.col("noticed").not_().sum(),
            pct=pl.col("noticed").mean().round_sig_figs(digits=2),
        )
        .sort("model", "color")
    )

    notice_by_scene = all_models.group_by("model", "scene", "color").agg(
        pl.col("ndetected").gt(NOTICE_THRESH).mean().alias("noticed")
    )
    return model_notice_summary, notice_by_scene


@app.cell
def _(mo, model_notice_summary):
    mo.ui.table(model_notice_summary)
    return


@app.cell
def _(fisher_exact, model_notice_summary):
    _grouped = model_notice_summary.group_by("model")
    for model, g in _grouped:
        print(f"Model {model[0]}")
        dark = g.row(0)[2:4]
        light = g.row(1)[2:4]
        print(fisher_exact([dark, light]))
    return


@app.cell
def _(notice_by_scene, pl):
    notice_summary = (
        notice_by_scene.group_by("model", "color")
        .agg(
            pl.col("noticed").mean().alias("mu"),
            pl.col("noticed").std().alias("sd"),
            pl.len(),
        )
        .with_columns(se=pl.col("sd") / pl.col("len").sqrt())
        .with_columns(
            lo=pl.col("mu") - 1.96 * pl.col("se"),
            hi=pl.col("mu") + 1.96 * pl.col("se"),
        )
        .select("model", "color", "mu", "sd", "lo", "hi")
        .sort("model", "color")
    )
    return (notice_summary,)


@app.cell
def _(mo, notice_summary):
    mo.ui.table(notice_summary)
    return


@app.cell
def _(all_models, pl):
    model_perf_summary = (
        all_models.group_by("model")
        .agg(
            pl.col("count_error").mean().alias("error_mu"),
            pl.col("count_error").std().alias("error_sd"),
            pl.col("time").mean().alias("time_mu"),
            pl.col("time").std().alias("time_sd"),
            n=pl.len(),
        )
        .sort("error_mu")
    )
    return (model_perf_summary,)


@app.cell
def _(model_perf_summary):
    print(model_perf_summary)
    return


@app.cell
def _(mo, model_perf_summary):
    mo.ui.table(model_perf_summary)
    return


@app.cell
def _(by_scene, mo):
    mo.ui.table(by_scene)
    return


@app.cell
def _(all_models, alt):
    alt.Chart(all_models).mark_bar().encode(
        alt.X("count_error:Q").bin(), y="count()", row="model"
    )
    return


@app.cell
def _(by_scene, pl, ttest_ind):
    mo_by_scene = by_scene.filter(pl.col("model") == "mo")


    def compare_mo(column: str):
        for alternative in ["ja", "fr", "ta"]:
            print(f"MO vs. {alternative}")
            alt_by_scene = by_scene.filter(pl.col("model") == alternative)
            print(ttest_ind(mo_by_scene[column], alt_by_scene[column]))
    return (compare_mo,)


@app.cell
def _(compare_mo):
    compare_mo("count_error")
    return


@app.cell
def _(all_models, alt):
    alt.Chart(all_models).mark_bar().encode(
        alt.X("time:Q").bin(base=2, maxbins=30), y="count()", row="model"
    )
    return


@app.cell
def _(compare_mo):
    compare_mo("time")
    return


if __name__ == "__main__":
    app.run()
