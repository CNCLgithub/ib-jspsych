import marimo

__generated_with = "0.20.4"
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

    # alt.theme.enable("carbong100")
    alt.theme.enable("carbonwhite")
    return (pl,)


@app.cell
def _(pl):
    # Polars dataseries types
    Color = pl.Enum(["light", "dark"])
    Param = pl.Enum(["w", "inv_t", "a_mho"])
    return Color, Param


@app.cell
def _(Color, Param, pl):
    def load_model(path: str):
        df = pl.read_csv(
            path,
            schema={
                "param": Param,
                "param_val": pl.Float64,
                "scene": pl.UInt8,
                "color": Color,
                "chain": pl.Int64,
                "ndetected": pl.Int64,
                "expected_count": pl.Float64,
                "count_error": pl.Float64,
                "time": pl.Float64,
            },
        ).with_columns(
            noticed=pl.col("ndetected") > 24,
        )
        return df


    model_runs = load_model("data/sensitivity-1/aggregate.csv")

    model_trial_level = model_runs.group_by(
        "param", "param_val", "color", "scene"
    ).agg(covariate=pl.col("noticed").mean())
    return (model_runs,)


@app.cell
def _(model_runs, pl):
    noticing_rates = (
        model_runs.group_by("param", "param_val", "color")
        .agg(pl.col("noticed").mean())
        .sort("param", "param_val", "color")
    )
    return (noticing_rates,)


@app.cell
def _(mo, noticing_rates):
    mo.ui.table(noticing_rates)
    return


if __name__ == "__main__":
    app.run()
