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

    # alt.theme.enable("carbong100")
    alt.theme.enable("carbonwhite")
    return alt, linregress, pl


@app.cell
def _(pl):
    Color = pl.Enum(["light", "dark"])
    Model = pl.Enum(["MO", "AC", "FR"])
    return Color, Model


@app.cell
def _(pl):
    design_df = (
        pl.DataFrame(
            {
                "scene": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "nlight": [3, 4, 5, 6, 7, 3, 3, 3, 3],
                "ndark": [3, 3, 3, 3, 3, 4, 5, 6, 7],
            }
        )
        .with_columns(ntotal=pl.col("nlight") + pl.col("ndark"))
        .cast({"scene": pl.UInt8})
    )
    return (design_df,)


@app.cell
def _(design_df, mo):
    mo.ui.table(design_df)
    return


@app.cell
def _(Color, Model, design_df, pl):
    def load_model(pathname: str):
        df = (
            pl.read_csv(f"data/{pathname}.csv")
            .cast(
                {
                    "scene": pl.UInt8,
                    "color": Color,
                    "model": Model,
                }
            )
            .join(design_df, on="scene", how="left")
        )
        return df


    model_df = load_model("load_exp_models")
    return (model_df,)


@app.cell
def _(mo, model_df):
    mo.ui.table(model_df)
    return


@app.cell
def _(alt, model_df, pl):
    avg_load = model_df.group_by("model", "ntotal").agg(error=pl.mean("error"))
    alt.Chart(avg_load).encode(
        alt.X("ntotal:O").title("Number of objects"),
        alt.Y("error:Q").title("Error (%)").scale(zero=False),
        alt.Shape("model:N"),
        alt.Color("model:N"),
    ).mark_line(point=True)
    return


@app.cell
def _(model_df, pl):
    cog_load = (
        model_df.filter(pl.col("ndark") == 3, pl.col("color") == "light")
        .group_by("model", "nlight")
        .agg(error=pl.mean("error"), noticed=pl.mean("noticed"))
    )
    return (cog_load,)


@app.cell
def _(alt, cog_load):
    alt.Chart(cog_load).encode(
        alt.X("nlight:O").title("Number of targets"),
        alt.Y("error:Q").title("Error (%)").scale(zero=False),
        alt.Shape("model:N"),
        alt.Color("model:N"),
    ).mark_line(point=True)
    return


@app.cell
def _(alt, cog_load):
    alt.Chart(cog_load).encode(
        alt.X("nlight:O").title("Number of targets"),
        alt.Y("noticed:Q").title("Noticed (%)").scale(zero=False),
        alt.Shape("model:N"),
        alt.Color("model:N"),
    ).mark_line(point=True)
    return


@app.cell
def _(model_df, pl):
    percept_load = (
        model_df.filter(pl.col("nlight") == 3, pl.col("color") == "light")
        .group_by("model", "ntotal")
        .agg(error=pl.mean("error"), noticed=pl.mean("noticed"))
    )
    return (percept_load,)


@app.cell
def _(alt, percept_load):
    alt.Chart(percept_load).encode(
        alt.X("ntotal:O").title("Number of objects"),
        alt.Y("error:Q").title("Error (%)").scale(zero=False),
        alt.Shape("model:N"),
        alt.Color("model:N"),
    ).mark_line(point=True)
    return


@app.cell
def _(alt, percept_load):
    alt.Chart(percept_load).encode(
        alt.X("ntotal:O").title("Number of targets"),
        alt.Y("noticed:Q").title("Noticed (%)").scale(zero=False),
        alt.Shape("model:N"),
        alt.Color("model:N"),
    ).mark_line(point=True)
    return


@app.cell
def _(linregress, pl):
    CorResult = pl.Struct({"r": pl.Float64, "p_value": pl.Float64})


    def fit_model(data: pl.Struct):
        x = data.struct.field("covariate")
        y = data.struct.field("noticed")
        result = linregress(x, y)
        return {
            "r^2": result.rvalue**2,
            "p_value": result.pvalue,
        }
    return


if __name__ == "__main__":
    app.run()
