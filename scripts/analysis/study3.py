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
    from scipy.stats import ttest_ind, ttest_rel


    # alt.theme.enable("carbong100")
    alt.theme.enable("carbonwhite")
    return alt, pl, ttest_ind, ttest_rel


@app.cell
def _(pl):
    Model = pl.Enum(["mo", "ja", "ta", "fr"])
    return (Model,)


@app.cell
def _(Model, pl):
    def load_models(path: str):
        df = pl.read_csv(
            path,
            schema={
                "scene": pl.UInt8,
                "ndark": pl.Int64,
                "chain": pl.Int64,
                "gt_count": pl.Int64,
                "expected_count": pl.Float64,
                "count_error": pl.Float64,
                "time": pl.Float64,
                "model": Model,
            },
        ).with_columns(error_time=pl.col("count_error") * pl.col("time"))
        return df


    runs = load_models("data/study3/aggregate.csv")
    return (runs,)


@app.cell
def _(mo, runs):
    mo.ui.table(runs)
    return


@app.cell
def _(runs):
    runs.schema
    return


@app.cell
def _(alt, runs):
    _band = (
        alt.Chart(runs)
        .mark_errorband(extent="ci", borders=True)
        .encode(
            alt.X("ndark:O"),
            alt.Y(
                alt.repeat("column"),
                type="quantitative",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color("model:N"),
        )
    )

    _line = (
        alt.Chart(runs)
        .mark_line()
        .encode(
            alt.X("ndark:O"),
            alt.Y(
                alt.repeat("column"),
                aggregate="mean",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color("model:N"),
        )
    )

    _chart = (
        (_band + _line)
        .properties(height=250, width=300)
        .repeat(column=["count_error", "time"])
    )

    _chart
    return


@app.cell
def _(alt, runs):
    _band = (
        alt.Chart(runs)
        .mark_errorband(extent="ci", borders=True)
        .encode(
            alt.X("ndark:O"),
            alt.Y(
                alt.repeat("column"),
                type="quantitative",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color("model:N"),
        )
    )

    _line = (
        alt.Chart(runs)
        .mark_line()
        .encode(
            alt.X("ndark:O"),
            alt.Y(
                alt.repeat("column"),
                aggregate="mean",
                scale=alt.Scale(zero=False),
            ),
            color=alt.Color("model:N"),
        )
    )

    _chart = (
        (_band + _line)
        .properties(height=200, width=300)
        .repeat(column=["error_time"])
    )

    _chart
    return


@app.cell
def _(pl, runs, ttest_ind):
    mo_runs = runs.filter(pl.col("model") == "mo")


    def compare_mo(column: str):
        print(f"### Comparing {column} ###")
        for alternative in ["ja", "fr", "ta"]:
            alt_runs = runs.filter(pl.col("model") == alternative)
            result = ttest_ind(mo_runs[column], alt_runs[column])
            print(
                f"  MO vs. {alternative}: \t"
                + f"t(DF={result.df:.3g}): {result.statistic:.3g}, p: {result.pvalue:.3g}"
            )
    return (compare_mo,)


@app.cell
def _(compare_mo):
    compare_mo("count_error")
    compare_mo("time")
    return


@app.cell
def _(alt, runs):
    # replace _df with your data source
    _chart = (
        alt.Chart(runs)
        .mark_bar()
        .encode(
            x=alt.X(field="count_error", type="quantitative").bin(step=0.1),
            y="count()",
            color=alt.Color(field="model", type="nominal"),
            row=alt.Row(field="model", type="nominal"),
            column=alt.Column(field="ndark", type="ordinal"),
            tooltip=[
                alt.Tooltip(field="count_error", format=",.2f"),
                alt.Tooltip(aggregate="count"),
                alt.Tooltip(field="model"),
            ],
        )
        .properties(
            height=125,
            width=200,
        )
    )
    _chart
    return


@app.cell
def _(alt, runs):
    # replace _df with your data source
    _chart = (
        alt.Chart(runs)
        .mark_bar()
        .encode(
            x=alt.X(field="time", type="quantitative").bin(step=1),
            y="count()",
            color=alt.Color(field="model", type="nominal"),
            row=alt.Row(field="model", type="nominal"),
            column=alt.Column(field="ndark", type="ordinal"),
            tooltip=[
                alt.Tooltip(field="time", format=",.2f"),
                # alt.Tooltip(field='count'),
                alt.Tooltip(field="model"),
            ],
        )
        .properties(
            height=100,
            width=200,
        )
    )
    _chart
    return


@app.cell
def _(pl, runs):
    _cols = ["count_error", "time", "error_time"]
    by_ndark = runs.group_by("model", "ndark").agg(
        [
            pl.col(_cols).mean().name.suffix("_mean"),
            pl.col(_cols).std().name.suffix("_std"),
            (pl.col(_cols).std() / pl.col(_cols).count().sqrt()).name.suffix("_se"),
        ]
    )
    return (by_ndark,)


@app.cell
def _(by_ndark, mo):
    mo.ui.table(by_ndark)
    return


@app.cell
def _(alt, by_ndark):
    repeated = (
        alt.Chart(by_ndark)
        .mark_line()
        .encode(
            x=alt.X("ndark:O").title("N Dark").scale(zero=False),
            y=alt.Y(alt.repeat("column"), type="quantitative"),
            color="model:N",
        )
        .properties(width=350, height=350)
        .repeat(column=["count_error_mean", "time_mean"])
    )
    repeated
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(rf"""
    ## Scene-level
    """)
    return


@app.cell
def _(pl, runs):
    by_scene = runs.group_by("model", "scene", "ndark").agg(
        pl.col("count_error").mean(),
        pl.col("time").mean(),
        pl.col("error_time").mean(),
    )
    print(by_scene)
    return (by_scene,)


@app.cell
def _(by_scene, pl, ttest_rel):
    mo_by_scene = by_scene.filter(pl.col("model") == "mo")


    def compare_by_scene(column: str):
        print(f"### Comparing {column} ###")
        for alternative in ["ja", "fr", "ta"]:
            alt_runs = by_scene.filter(pl.col("model") == alternative)
            result = ttest_rel(mo_by_scene[column], alt_runs[column])
            print(
                f"  MO vs. {alternative}: \t"
                + f"t(DF={result.df:.3g}): {result.statistic:.3g}, p: {result.pvalue:.3g}"
            )
    return (compare_by_scene,)


@app.cell
def _(compare_by_scene):
    compare_by_scene("count_error")
    return


@app.cell
def _(compare_by_scene):
    compare_by_scene("time")
    return


@app.cell
def _(alt, by_scene, mo):
    mo.ui.altair_chart(
        alt.Chart(by_scene)
        .mark_line()
        .encode(
            x=alt.X("ndark:O").title("N Dark").scale(zero=False),
            y=alt.Y("count_error:Q").title("Error (%)").scale(zero=False),
            color="model:N",
        )
        .properties(width=160, height=160)
        .facet(
            facet="scene:N",
            columns=5,
        )
    )
    return


@app.cell
def _(alt, by_scene, mo):
    mo.ui.altair_chart(
        alt.Chart(by_scene)
        .mark_line()
        .encode(
            x=alt.X("ndark:O").title("N Dark").scale(zero=False),
            y=alt.Y("time:Q").title("Time (s)").scale(zero=False),
            color="model:N",
        )
        .properties(width=160, height=160)
        .facet(
            facet="scene:N",
            columns=5,
        )
    )
    return


@app.cell
def _(alt, by_scene, mo):
    mo.ui.altair_chart(
        alt.Chart(by_scene)
        .mark_line()
        .encode(
            x=alt.X("ndark:O").title("N Dark").scale(zero=False),
            y=alt.Y("error_time:Q").title("Error Time (% s)").scale(zero=False),
            color="model:N",
        )
        .properties(width=160, height=160)
        .facet(
            facet="scene:N",
            columns=5,
        )
    )
    return


if __name__ == "__main__":
    app.run()
