import marimo

__generated_with = "0.16.3"
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
    return pl, ttest_ind


@app.cell
def _(pl):
    def load_model(name: str):
        pathname = name.replace(" ", "_")
        df = pl.read_csv(f"data/study1/{pathname}.csv").with_columns(
            model=pl.lit(name)
        )
        return df


    mo_model = load_model("MO")
    ac_model = load_model("JA")
    fr_model = load_model("FR")
    all_models = pl.concat([mo_model, ac_model, fr_model], how="vertical")
    return (all_models,)


@app.cell
def _(all_models, mo):
    mo.ui.table(all_models)
    return


@app.cell
def _(all_models, pl):
    model_perf_summary = (
        all_models.group_by("model")
        .agg(
            pl.col("count_error_mean").mean().alias("error_mu"),
            pl.col("count_error_mean").std().alias("error_sd"),
        )
        .sort("error_mu")
    )
    return (model_perf_summary,)


@app.cell
def _(mo, model_perf_summary):
    mo.ui.table(model_perf_summary)
    return


@app.cell
def _(all_models, pl, ttest_ind):
    _perf_mo = all_models.filter(pl.col("model") == "MO")
    _perf_ac = all_models.filter(pl.col("model") == "JA")
    perf_mo_vs_ac = ttest_ind(
        _perf_mo["count_error_mean"], _perf_ac["count_error_mean"]
    )
    print(perf_mo_vs_ac)
    return


@app.cell
def _(all_models, pl, ttest_ind):
    _perf_mo = all_models.filter(pl.col("model") == "MO")
    _perf_fr = all_models.filter(pl.col("model") == "FR")
    perf_mo_vs_fr = ttest_ind(
        _perf_mo["count_error_mean"], _perf_fr["count_error_mean"]
    )
    print(perf_mo_vs_fr)
    return


if __name__ == "__main__":
    app.run()
