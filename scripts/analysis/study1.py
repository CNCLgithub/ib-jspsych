import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import numpy as np
    import polars as pl
    import altair as alt
    from scipy.stats import fisher_exact

    return alt, fisher_exact, pl


@app.cell
def _(pl):
    all_models = pl.read_csv("data/study1/aggregate.csv")
    by_scene = all_models.group_by("model", "scene").agg(
        pl.col("count_error").mean().alias("count_error"),
        pl.col("time").mean().alias("time"),
    )
    return (all_models,)


@app.cell
def _(all_models, pl):
    NOTICE_THRESH = 24


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
    return NOTICE_THRESH, model_notice_summary


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
def _(NOTICE_THRESH, all_models, alt, pl):
    # 1. Aggregate empirical model detection rates
    model_rates = (
        all_models.with_columns(noticed=pl.col("ndetected").gt(NOTICE_THRESH))
        .group_by("model", "color")
        .agg((pl.col("noticed").mean() * 100).alias("notice_rate"))
    )

    # 2. Append human empirical baseline from Simons & Chabris (1999)
    human_baseline = pl.DataFrame(
        {
            "model": ["human", "human"],
            "color": ["light", "dark"],
            "notice_rate": [94.0, 5.8],
        }
    )

    # 3. Model metadata and ordering
    metadata = pl.DataFrame(
        {
            "model": ["human", "mo", "ta", "ja", "fr"],
            "model_label": [
                "Humans*",
                "Multigranular\nOptimization",
                "Task\nAgnostic",
                "Just\nAttention",
                "Fixed\nResource",
            ],
            "order": [0, 1, 2, 3, 4],
            "stroke_color": [
                "#e67319",
                "#0085db",
                "transparent",
                "transparent",
                "transparent",
            ],
        }
    )

    chart_df = (
        pl.concat([human_baseline, model_rates])
        .join(metadata, on="model")
        .sort("order")
    )

    # 4. Construct Altair grouped bar plot
    category_order = [
        "Humans*",
        "Multigranular\nOptimization",
        "Task\nAgnostic",
        "Just\nAttention",
        "Fixed\nResource",
    ]

    chart = (
        alt.Chart(chart_df)
        .mark_bar(strokeWidth=1.5)
        .encode(
            x=alt.X("color:N", title=None, axis=None, sort=["light", "dark"]),
            y=alt.Y(
                "notice_rate:Q",
                title="Notice Rate (%)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(
                    values=[5, 50, 100],
                    tickCount=3,
                    titleFontSize=14,
                    labelFontSize=12,
                    domainWidth=1.5,
                ),
            ),
            color=alt.Color(
                "color:N",
                scale=alt.Scale(
                    domain=["light", "dark"],
                    range=["#ebebeb", "#3a3a3a"],
                ),
                legend=alt.Legend(
                    title="Gorilla\nshade",
                    titleFontSize=12,
                    labelFontSize=11,
                    orient="right",
                ),
            ),
            stroke=alt.Stroke(
                "stroke_color:N",
                scale=None,
                legend=None,
            ),
            column=alt.Column(
                "model_label:N",
                title=None,
                sort=category_order,
                header=alt.Header(
                    labelAngle=-45,
                    labelAlign="right",
                    labelBaseline="top",
                    labelFontSize=11,
                    labelPadding=6,
                ),
            ),
        )
        .configure_view(stroke=None)
        .configure_axis(grid=False)
        .properties(width=30, height=180)
    )

    chart
    return


if __name__ == "__main__":
    app.run()
