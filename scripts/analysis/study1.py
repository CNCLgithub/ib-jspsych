import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import polars as pl
    import altair as alt
    from scipy.stats import fisher_exact

    return alt, fisher_exact, pl


@app.cell(hide_code=True)
def _3(mo):
    mo.md(r"""
    ### Load the study data

    Reads `data/study1/aggregate.csv` into `all_models` — one row per trial (scene, chain, condition).
    """)
    return


@app.cell
def _(pl):
    all_models = pl.read_csv("data/study1/aggregate.csv")
    return (all_models,)


@app.cell(hide_code=True)
def _4(mo):
    mo.md(r"""
    ### Define the notice threshold and summarize detection

    A model run counts as *noticed* when `ndetected > 24`. Builds `model_notice_summary` (per model and condition: yes/no run counts and the noticed fraction via `pct`).
    """)
    return


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
    return NOTICE_THRESH, model_notice_summary


@app.cell(hide_code=True)
def _5(mo):
    mo.md(r"""
    ### Inspect the notice summary

    Renders `model_notice_summary` as an interactive data table.
    """)
    return


@app.cell
def _(mo, model_notice_summary):
    mo.ui.table(model_notice_summary)
    return


@app.cell(hide_code=True)
def _6(mo):
    mo.md(r"""
    ### Test the shade effect per model

    For each model, runs Fisher's exact test on the 2×2 table of noticed counts (dark vs. light condition) and prints the odds ratio and p-value.
    """)
    return


@app.cell
def _(fisher_exact, model_notice_summary):
    _grouped = model_notice_summary.group_by("model")
    for model, g in _grouped:
        print(f"Model {model[0]}")
        dark = g.row(0)[2:4]
        light = g.row(1)[2:4]
        print(f"\tresult: {fisher_exact([dark, light])}")
    return


@app.cell(hide_code=True)
def _7(mo):
    mo.md(r"""
    ### Figure 3 results

    Plot notice rates by model and condition

    bar chart: mean notice rate (%) per model for light and dark conditions, with the human baseline from Simons & Chabris (1999) included. Bars are outlined in orange (humans) and blue (Multigranular Optimization) to mark the models featured in the paper.
    """)
    return


@app.cell(hide_code=True)
def _(NOTICE_THRESH, all_models, pl):
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
                "#33a3dd",
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
    FONT = "Georgia, serif"
    return FONT, category_order, chart_df


@app.cell
def _(FONT, alt, category_order, chart_df, pl):
    # 1. Bar chart — no header, no config
    bar_chart = (
        alt.Chart(chart_df)
        .mark_bar(strokeWidth=3, size=28)
        .encode(
            x=alt.X(
                "color:N",
                title=None,
                axis=None,
                sort=["light", "dark"],
                scale=alt.Scale(
                    type="band", paddingInner=0.25, paddingOuter=0.4
                ),
            ),
            y=alt.Y(
                "notice_rate:Q",
                title="Notice Rate (%)",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(
                    values=[5, 50, 100],
                    tickCount=3,
                    titleFontSize=17,
                    labelFontSize=13,
                    titleFont=FONT,
                    labelFont=FONT,
                    domainWidth=1.5,
                ),
            ),
            color=alt.Color(
                "color:N",
                scale=alt.Scale(
                    domain=["light", "dark"], range=["#ebebeb", "#3a3a3a"]
                ),
                legend=alt.Legend(
                    title="Gorilla\nshade",
                    titleFontSize=14,
                    labelFontSize=12,
                    orient="right",
                    titleFont=FONT,
                    labelFont=FONT,
                ),
            ),
            stroke=alt.Stroke("stroke_color:N", scale=None, legend=None),
            column=alt.Column(
                "model_label:N",
                sort=category_order,
                title=None,
                header=alt.Header(labelFontSize=0, labelPadding=0, title=None),
            ),
        )
        .properties(width=80, height=105)  # y-axis scaled to 70% (was 150)
    )

    # 2. Label strip — one text mark per label line
    label_df = (
        pl.DataFrame({"model_label": category_order})
        .with_columns(line=pl.col("model_label").str.split("\n"))
        .explode("line")
        .with_columns(
            line_idx=(pl.col("line").cum_count().over("model_label") - 1).alias(
                "line_idx"
            )
        )
        .with_columns(
            y_pos=((pl.lit(1) - pl.col("line_idx")) * 16 + 22).alias("y_pos")
        )
    )

    text_chart = (
        alt.Chart(label_df)
        .mark_text(
            angle=330,
            align="center",
            baseline="middle",
            fontSize=13,
            font=FONT,
        )
        .encode(
            text="line:N",
            x=alt.X(value=32),
            y=alt.Y("y_pos:Q", title=None, axis=None),
            column=alt.Column(
                "model_label:N",
                sort=category_order,
                title=None,
                header=alt.Header(labelFontSize=0, labelPadding=0, title=None),
            ),
        )
        .properties(width=64, height=48)
    )

    # 3. Concatenate; config at top level
    chart = (
        alt.vconcat(bar_chart, text_chart, spacing=0)
        .configure_view(stroke=None)
        .configure_axis(grid=False)
        .configure_facet(spacing=18)
    )

    chart
    return


if __name__ == "__main__":
    app.run()
