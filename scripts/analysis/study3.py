import marimo

__generated_with = "0.24.0"
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
    from scipy import stats
    from scipy.stats import ttest_ind, ttest_rel, linregress, ttest_1samp

    # alt.theme.enable("carbong100")
    alt.theme.enable("carbonwhite")
    return alt, linregress, np, pl, stats, ttest_1samp, ttest_ind


@app.cell
def _(pl):
    Model = pl.Enum(["mo", "ja", "ta", "fr"])
    return (Model,)


@app.cell
def _(Model, pl):
    def load_models(path: str):
        df = (
            pl.read_csv(
                path,
                schema={
                    "scene": pl.UInt8,
                    "ndark": pl.Int64,
                    "chain": pl.Int64,
                    "gt_count": pl.Int64,
                    "expected_count": pl.Float64,
                    "count_error": pl.Float64,
                    "time": pl.Float64,
                    "bytes": pl.Float64,
                    "model": Model,
                },
            )
            .with_columns(
                count_error=pl.col("count_error") * 100,
                mbs=pl.col("bytes") * 1e-9,
            )
            # Remove first run to exclude JIT contamination
            .filter(pl.col("chain") != 1)
        )
        return df

    runs = load_models("data/study3/aggregate.csv")
    return (runs,)


@app.cell
def _(mo, runs):
    mo.ui.table(runs)
    return


@app.cell
def _(mo, pl, runs):
    by_cond = (
        runs.group_by("model", "ndark")
        .agg(pl.col("count_error", "time", "mbs").mean())
        .sort("ndark", "model")
    )
    mo.ui.table(by_cond)
    return


@app.cell
def _(mo, pl, runs):
    _cols = ["count_error", "time", "mbs"]
    by_model = (
        runs.group_by("model")
        .agg(
            [
                pl.col(_cols).mean().name.suffix("_mean"),
                pl.col(_cols).std().name.suffix("_std"),
            ]
        )
        .sort("model")
    )
    mo.ui.table(by_model)
    return


@app.cell(hide_code=True)
def _(alt, runs):
    # ---------------------------------------------------------------- style --
    FONT = "Georgia, serif"
    AXIS_TITLE_SIZE = 17
    TICK_LABEL_SIZE = 13
    TITLE_SIZE = 21
    LEGEND_TITLE_SIZE = 15
    LEGEND_LABEL_SIZE = 13

    # keyed by the actual values in the data
    MODEL_COLORS = {
        "fr": "#c85a1e",  # Fixed Resource  (orange)
        "ta": "#b04fc4",  # Task Agnostic   (magenta)
        "ja": "#3aa93a",  # Just Attention  (green)
        "mo": "#33a3dd",  # Multigranular Optimization (blue)
    }

    PANEL_TITLES = {
        "time": "b  Runtime vs. Load",
        "count_error": "c  Accuracy vs. Load",
        "mbs": "d  Memory vs. Load",
    }

    COLUMNS = ["time", "count_error", "mbs"]

    def model_scale():
        return alt.Scale(
            domain=list(MODEL_COLORS), range=list(MODEL_COLORS.values())
        )

    LEGEND_LABELS = (
        alt.expr.join(
            [
                {
                    "fr": "Fixed Resource",
                    "ta": "Task Agnostic",
                    "ja": "Just Attention",
                    "mo": "Multigranular Optimization",
                }
            ],
            format={"value": ""},
        )
        if False
        else None
    )  # see note below

    # 1. Per-column axis titles, via a dict (same pattern as PANEL_TITLES)
    AXIS_TITLES = {
        "time": "Wallclock Runtime (s)",
        "count_error": "Count Error (%)",
        "mbs": "Memory Volume (GB)",
    }
    # inside make_panel:

    # ---------------------------------------------------------------- panels --
    def make_panel(col):


        _band = (
            alt.Chart(runs)
            .mark_errorband(extent="ci", borders=False)
            .encode(
                alt.X("ndark:O", axis=alt.Axis(grid=False, title="Number of Dark Objects")),
                alt.Y(
                    col,
                    type="quantitative",
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(
                        title=AXIS_TITLES[col],
                        titleFont=FONT,
                        titleFontSize=AXIS_TITLE_SIZE,
                        tickCount=6,
                    ),
                ),
                color=alt.Color(
                    "model:N",
                    scale=model_scale(),
                    legend=alt.Legend(
                        title="Model",
                        titleFontSize=LEGEND_TITLE_SIZE,
                        labelFontSize=LEGEND_LABEL_SIZE,
                        labelExpr="{'fr':'Fixed Resource','ta':'Task Agnostic',"
                        "'ja':'Just Attention','mo':'Multigranular Optimization'}"
                        "[datum.label] || datum.label",
                    ),
                ),
            )
        )

        _line = (
            alt.Chart(runs)
            .mark_line()
            .encode(
                alt.X("ndark:O", axis=alt.Axis(grid=False)),
                alt.Y(
                    col,
                    aggregate="mean",
                    type="quantitative",
                    scale=alt.Scale(zero=False),
                    axis=alt.Axis(tickCount=6)
                ),
                color=alt.Color("model:N", scale=model_scale(), legend=None),
            )
        )

        return (_band + _line).properties(
            height=200,
            width=250,
            title=alt.Title(
                PANEL_TITLES[col],
                font=FONT,
                fontSize=TITLE_SIZE,
                fontWeight="normal",
                anchor="start",
                dy=-10,
            ),
        )

    # ---------------------------------------------------------------- chart --
    _chart = (
        alt.concat(*[make_panel(c) for c in COLUMNS])
        .resolve_scale(y="independent")
        .properties(background="white")
        .configure_axis(
            grid=False,
            domain=True,
            labelFont=FONT,
            labelFontSize=TICK_LABEL_SIZE,
            titleFont=FONT,
            titleFontSize=AXIS_TITLE_SIZE,
            titleFontWeight="normal",
            labelFontWeight="normal",
            tickCount=6,
        )
        .configure_view(stroke=None)
        .configure_legend(labelLimit=0)
    )

    _chart
    return


@app.cell
def _(pl, runs):
    _cols = ["count_error", "time", "mbs"]
    by_ndark = runs.group_by("model", "ndark").agg(
        [
            pl.col(_cols).mean().name.suffix("_mean"),
            pl.col(_cols).std().name.suffix("_std"),
            (pl.col(_cols).std() / pl.col(_cols).count().sqrt()).name.suffix(
                "_se"
            ),
        ]
    )
    return (by_ndark,)


@app.cell
def _(by_ndark, mo):
    mo.ui.table(by_ndark)
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
    compare_mo("mbs")
    return


@app.cell
def _(by_ndark, linregress, pl):
    def fit(g, cov):
        reg = linregress(g["ndark"], g[cov])
        return {
            "slope": reg.slope,
            "intercept": reg.intercept,
            "r2": reg.rvalue**2,
            "se": reg.stderr,
            "pvalue": reg.pvalue,
        }

    slopes = (
        by_ndark.group_by("model", maintain_order=True)
        .map_groups(
            lambda g: pl.DataFrame([{**{"model": g["model"][0]}, **fit(g, "mbs_mean")}])
        )
        .sort("slope")
    )
    print(slopes)
    return (slopes,)


@app.cell
def _(np, pl, slopes, stats):
    def compare_slopes(model_a, model_b):
        b_ja, se_ja = slopes.filter(pl.col("model") == model_b)["slope", "se"]
        b_mo, se_mo = slopes.filter(pl.col("model") == model_a)["slope", "se"]
        n = 4  # points per model; fit residual df = n-2

        diff = b_ja - b_mo
        se_diff = np.sqrt(se_ja**2 + se_mo**2)
        t = diff / se_diff
        # Welch–Satterthwaite df for two slope SEs
        df_ws = (se_ja**2 + se_mo**2) ** 2 / (
            se_ja**4 / (n - 2) + se_mo**4 / (n - 2)
        )
        p_two = 2 * (1 - stats.t.cdf(abs(t), df_ws))
        return (df_ws.item(), t.item(), p_two.item())

    return (compare_slopes,)


@app.cell(hide_code=True)
def _(
    mo,
    mo_vs_fr_dof,
    mo_vs_fr_p,
    mo_vs_fr_t,
    mo_vs_ja_dof,
    mo_vs_ja_p,
    mo_vs_ja_t,
    mo_vs_ta_dof,
    mo_vs_ta_p,
    mo_vs_ta_t,
):
    mo.md(rf"""
    Difference in slopes between MO and JA: t({"{dof:.3f}".format(dof=mo_vs_ja_dof)})={"{t:.3f}".format(t=mo_vs_ja_t)}, p={"{p:.3f}".format(p=mo_vs_ja_p)}

    Difference in slopes between MO and TA: t({"{dof:.3f}".format(dof=mo_vs_ta_dof)})={"{t:.3f}".format(t=mo_vs_ta_t)}, p={"{p:.3f}".format(p=mo_vs_ta_p)}

    Difference in slopes between MO and FR: t({"{dof:.3f}".format(dof=mo_vs_fr_dof)})={"{t:.3f}".format(t=mo_vs_fr_t)}, p={"{p:.3f}".format(p=mo_vs_fr_p)}
    """)
    return


@app.cell
def _(compare_slopes):
    mo_vs_ja_dof, mo_vs_ja_t, mo_vs_ja_p = compare_slopes("mo", "ja")
    return mo_vs_ja_dof, mo_vs_ja_p, mo_vs_ja_t


@app.cell
def _(compare_slopes):
    mo_vs_fr_dof, mo_vs_fr_t, mo_vs_fr_p = compare_slopes("mo", "fr")
    return mo_vs_fr_dof, mo_vs_fr_p, mo_vs_fr_t


@app.cell
def _(compare_slopes):
    mo_vs_ta_dof, mo_vs_ta_t, mo_vs_ta_p = compare_slopes("mo", "ta")
    return mo_vs_ta_dof, mo_vs_ta_p, mo_vs_ta_t


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
        pl.col("mbs").mean(),
    )
    print(by_scene)
    return (by_scene,)


@app.cell
def _(by_scene, np, pl, stats, ttest_1samp):
    mo_by_scene = by_scene.filter(pl.col("model") == "mo").sort(
        "scene", "ndark"
    )

    def compare_by_scene(column: str):
        print(f"### Comparing {column} ###")
        for alternative in ["ja", "fr", "ta"]:
            alt_runs = by_scene.filter(pl.col("model") == alternative).sort(
                "scene", "ndark"
            )
            # result = ttest_rel(mo_by_scene[column], alt_runs[column])
            # print(
            #     f"  MO vs. {alternative}: \t"
            #     + f"t(DF={result.df:.3g}): {result.statistic:.3g}, p: {result.pvalue:.3g}"
            # )
            log_ratio = mo_by_scene[column].log() - alt_runs[column].log()
            result = ttest_1samp(log_ratio, popmean=0)

            # --- Effect size: geometric mean ratio with 95% CI ---
            n = len(log_ratio)
            mean_log = log_ratio.mean()
            sem = log_ratio.std(ddof=1) / np.sqrt(n)
            ci_log = stats.t.ppf(0.975, df=n - 1) * sem

            geo_mean_ratio = np.exp(mean_log)
            ci = (np.exp(mean_log - ci_log), np.exp(mean_log + ci_log))
            print(
                f"  MO vs. {alternative}: \t"
                + f"t(DF={result.df:.3g}): {result.statistic:.3g}, p: {result.pvalue:.3g}"
            )
            print(
                f"    geometric mean ratio A/B = {geo_mean_ratio:.3f}, "
                f"95% CI [{ci[0]:.3f}, {ci[1]:.3f}]"
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
def _(compare_by_scene):
    compare_by_scene("mbs")
    return


@app.cell
def _(alt, by_scene):
    _band = (
        alt.Chart(by_scene)
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
        alt.Chart(by_scene)
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
        .repeat(column=["count_error", "time", "mbs"])
    )

    _chart
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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Debugging FR
    """)
    return


@app.cell
def _(pl, runs):
    fr_data = runs.filter(pl.col("model") == "fr")
    return (fr_data,)


@app.cell
def _(fr_data, mo):
    mo.ui.table(fr_data)
    return


if __name__ == "__main__":
    app.run()
