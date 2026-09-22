import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Setup
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Dependencies
    """)
    return


@app.cell
def _():
    import json
    import numpy as np
    import polars as pl
    import altair as alt
    from collections.abc import Callable
    from functools import partial
    from scipy.stats import (
        linregress,
        ttest_ind,
        chi2_contingency,
        fisher_exact,
    )
    import statsmodels.api as sm
    from statsmodels.formula.api import ols, logit, glm

    # alt.theme.enable("carbong100")
    alt.theme.enable("carbonwhite")
    return (
        Callable,
        alt,
        chi2_contingency,
        fisher_exact,
        json,
        linregress,
        np,
        pl,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Type Definitions
    """)
    return


@app.cell
def _(pl):
    # Polars dataseries types
    Parent = pl.Enum(["grouped", "lone"])
    Color = pl.Enum(["light", "dark"])
    Model = pl.Enum(["Human", "mo", "ja", "ta", "fr", "ecc"])
    return Color, Model, Parent


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Trial design
    """)
    return


@app.cell
def _():
    exp = "target-ensemble"
    version = "2025-06-09_W96KtK-v2-preregistered"
    return exp, version


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Ground truth counts
    """)
    return


@app.cell
def _(exp, json, np, pl, version):
    col_count_schema = {"scene": pl.UInt8, "count": pl.Int64}
    # repair version name for manifest; is the same for main and swapped experiments
    base_version = (
        version.replace("-swapped", "")
        .replace("-batch2", "")
        .replace("-all", "")
        .replace("-replication", "")
        .replace("-preregistered", "")
    )
    with open(f"data/{exp}-{base_version}-manifest.json", "r") as file:
        manifest = json.load(file)

    # gt_counts_raw = [3, 3, 4, 4, 5, 3]  # manifest["counts"]
    gt_counts_raw = manifest["counts"]
    nscenes = len(gt_counts_raw)

    gt_counts = pl.DataFrame(
        {"scene": np.arange(nscenes) + 1, "count": gt_counts_raw},
        schema=col_count_schema,
    )
    gt_counts
    return gt_counts, nscenes


@app.cell
def _(Parent, nscenes, pl):
    trial_design = pl.DataFrame(
        [
            [scene + 1, par]
            for par in ["grouped", "lone"]
            for scene in range(nscenes)
        ],
        schema={"scene": pl.UInt8, "parent": Parent},
        orient="row",
    )
    return (trial_design,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Human data
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exclusion Criteria
    """)
    return


@app.cell(hide_code=True)
def _(ctrl_ex_rate, main_ex_rate, mo, np):
    mo.md(f"""
    Exclusion Rate for Unswapped = {np.round(main_ex_rate * 100, decimals=1)}%

    Exclusion Rate for Swapped = {np.round(ctrl_ex_rate * 100, decimals=1)}%
    """)
    return


@app.cell(hide_code=True)
def _(PARAMS):
    PARAMS
    return


@app.cell
def _(mo):
    PARAMS = mo.md(
        """
        - Screen notice responses: {screen_notice}
        - Minimum performance threshold: {perf_thresh}
        """
    ).batch(
        screen_notice=mo.ui.switch(
            value=True,
        ),
        perf_thresh=mo.ui.slider(
            start=0, stop=10, step=0.25, value=2.0, show_value=True
        ),
    )
    return (PARAMS,)


@app.cell
def _():
    # Only consider noticing responses as true if the corresponding description
    # contains at least one of the following substrings
    hit_list = ["split", "merge", "two", "2", "appear", "extra", "new"]

    def clean_hit(desc: str):
        return any(substring in desc for substring in hit_list)

    return (clean_hit,)


@app.cell
def _(gt_counts, pl):
    def calc_performance(df: pl.DataFrame):
        """Calculates the average absolute tracking error per subject"""
        count_errors = (
            df.rename({"count": "measured"})
            .select(["uid", "scene", "measured"])
            .join(gt_counts, on="scene", how="left")
            .with_columns(error=abs(pl.col("count") - pl.col("measured")))
            .group_by("uid")
            .agg(pl.col("error").mean())
        )
        return count_errors

    return (calc_performance,)


@app.cell
def _(PARAMS, calc_performance, pl):
    def exclude_subjects(notice: pl.DataFrame, counts: pl.DataFrame):
        """Excludes subjects that have an average absolute error > `ERROR_THRESH`"""
        perf = calc_performance(counts)
        passed = perf.filter(
            pl.col("error") < PARAMS.value["perf_thresh"]
        ).select("uid")
        n_original = perf.select(pl.len()).item()
        n_passed = passed.select(pl.len()).item()
        ex_rate = (n_original - n_passed) / n_original
        # First 120 subjects
        passed = passed.head(n=120).join(notice, on="uid", how="left")
        return (passed, ex_rate, perf)

    return (exclude_subjects,)


@app.cell
def _(pl):
    notice_schema = {
        "uid": pl.UInt16,
        "scene": pl.UInt8,
        "grouped": pl.Boolean,
        "noticed": pl.Boolean,
        "description": pl.String,
        "rt": pl.Float32,
        "order": pl.UInt8,
    }
    count_schema = {
        "uid": pl.UInt16,
        "scene": pl.UInt8,
        "count": pl.Int64,
        "rt": pl.Float32,
        "order": pl.UInt8,
    }
    return count_schema, notice_schema


@app.cell
def _(
    PARAMS,
    Parent,
    clean_hit,
    count_schema,
    exclude_subjects,
    notice_schema,
    pl,
    trial_design,
):
    def load_behavior(path: str, uid_offset=0):
        # Load bounce count data
        count_df = pl.read_csv(
            path + "_counts.csv", schema=count_schema
        ).with_columns(order=pl.col("order").rank().over("uid"))

        # Load notice data
        noticed_raw = pl.read_csv(path + "_noticed.csv", schema=notice_schema)
        # Exclude subjects that count poorly
        noticed_df, ex_rate, perf = exclude_subjects(noticed_raw, count_df)
        perf = perf.with_columns(
            uid=pl.col("uid") + uid_offset
        )  # keep uid's distinct

        # Optionally, filter out responses by description
        if PARAMS.value["screen_notice"]:
            noticed_df = noticed_df.with_columns(
                noticed=pl.when(pl.col("noticed"))
                .then(
                    pl.col("description").map_elements(
                        clean_hit, return_dtype=pl.Boolean
                    )
                )
                .otherwise(False),
            )
        # Add factor and design columns
        noticed_df = noticed_df.with_columns(
            parent=pl.when(pl.col("grouped"))
            .then(pl.lit("grouped"))
            .otherwise(pl.lit("lone"))
            .cast(Parent)
        ).select(pl.all().exclude("grouped"))
        noticed_df = (
            trial_design.join(noticed_df, on=["scene", "parent"], how="left")
            .fill_null(0.0)
            .with_columns(uid=pl.col("uid") + uid_offset)  # keep uid's distinct
        )

        return (noticed_df, ex_rate, perf)

    return (load_behavior,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Loading human data
    """)
    return


@app.cell
def dataload(Color, exp, load_behavior, pl, version):
    main_noticed, main_ex_rate, main_perf = load_behavior(
        f"data/{exp}-{version}"
    )
    main_noticed = main_noticed.with_columns(color=pl.lit("light").cast(Color))
    main_perf = main_perf.with_columns(color=pl.lit("light").cast(Color))
    ctrl_noticed, ctrl_ex_rate, ctrl_perf = load_behavior(
        f"data/{exp}-{version}-swapped",
        uid_offset=1000,
    )
    ctrl_noticed = ctrl_noticed.with_columns(color=pl.lit("dark").cast(Color))
    ctrl_perf = ctrl_perf.with_columns(color=pl.lit("dark").cast(Color))

    all_noticed = pl.concat([main_noticed, ctrl_noticed]).cast(
        {"scene": pl.UInt8}
    )
    all_perf = pl.concat([main_perf, ctrl_perf])
    return (
        all_noticed,
        all_perf,
        ctrl_ex_rate,
        ctrl_noticed,
        main_ex_rate,
        main_noticed,
    )


@app.cell
def _(all_noticed):
    all_noticed.write_csv("./data/study2-human_noticing.csv")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Part 1: Human Analyses
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Summary statistics
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Counting accuracy
    """)
    return


@app.cell(hide_code=True)
def _(PARAMS, count_schema, exp, gt_counts, pl, version):
    count_df_raw = (
        pl.read_csv(
            f"data/{exp}-{version}" + "_counts.csv", schema=count_schema
        )
        .rename({"count": "measured"})
        .select(["uid", "scene", "measured"])
        .join(gt_counts, on="scene", how="left")
        .with_columns(
            error_abs=(pl.col("count") - pl.col("measured")).abs(),
            error_pct=(pl.col("count") - pl.col("measured")).abs()
            / pl.col("count"),
        )
        .group_by("uid")
        .agg(pl.col("error_abs").mean(), pl.col("error_pct").mean())
    )
    count_df_raw.filter(
        pl.col("error_abs") < PARAMS.value["perf_thresh"]
    ).describe()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Noticing rates
    """)
    return


@app.cell
def _(all_noticed, pl):
    human_notice_summary = (
        all_noticed.group_by("color", "parent")
        .agg(
            yes=pl.col("noticed").sum(),
            no=pl.col("noticed").not_().sum(),
            pct=pl.col("noticed").mean().round_sig_figs(digits=2),
        )
        .sort("color", "parent")
    )
    return (human_notice_summary,)


@app.cell
def _(human_notice_summary, mo):
    mo.ui.table(human_notice_summary)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Average human performance
    """)
    return


@app.cell
def _(all_perf, pl):
    all_perf.select(pl.col("error").abs().mean())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Chi-Squared
    """)
    return


@app.cell
def _(chi2_contingency, human_notice_summary, pl):
    ChiSquaredResult = pl.Struct(
        {"statistic": pl.Float64, "p_value": pl.Float64}
    )

    _grouped = human_notice_summary.row(0)[2:4]
    _alone = human_notice_summary.row(1)[2:4]
    _table = [_alone, _grouped]
    chi_squared_human_light = chi2_contingency(_table)
    print(f"Unswapped Chi-squared: {chi_squared_human_light}")

    # no swapped counts; cannot do chi-squared
    # chi_squared_human_dark = chi2_contingency([_alone, _grouped])
    return (chi_squared_human_light,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Fisher Exact
    """)
    return


@app.cell
def _(fisher_exact, human_notice_summary):
    _grouped = human_notice_summary.row(0)[2:4]
    _alone = human_notice_summary.row(1)[2:4]
    _table = [_alone, _grouped]
    print(f"Unswapped: {fisher_exact(_table)}")

    _grouped = human_notice_summary.row(2)[2:4]
    _alone = human_notice_summary.row(3)[2:4]
    _table = [_alone, _grouped]
    print(f"Swapped: {fisher_exact(_table)}")
    return


@app.cell
def _(chi_squared_human_light, mo):
    mo.ui.table(
        data=[
            {
                "model": "Human",
                "color": "Light",
                "Chi-Squared": chi_squared_human_light.statistic,
                "p-value": chi_squared_human_light.pvalue,
            }
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Part 2: Model analyses
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Loading model runs
    """)
    return


@app.cell
def _(Color, Model, Parent, gt_counts, pl):
    def load_models(path: str):
        df = (
            pl.read_csv(
                path,
                schema={
                    "scene": pl.UInt8,
                    "color": Color,
                    "parent": Parent,
                    "chain": pl.Int64,
                    "ndetected": pl.Int64,
                    "expected_count": pl.Float64,
                    "count_error": pl.Float64,
                    "time": pl.Float64,
                    "model": Model,
                },
            )
            .join(gt_counts, on="scene")
            .with_columns(
                count_error=(pl.col("expected_count") - pl.col("count")).abs()
                / pl.col("count"),
                error_time=pl.col("count_error") * pl.col("time"),
                noticed=pl.col("ndetected") > 24,
            )
        )
        return df

    all_models = (
        load_models("data/study2/aggregate.csv")
    )
    return (all_models,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Chi-Squared and Fisher Exact
    """)
    return


@app.cell
def _(all_models, pl):
    model_summary = (
        all_models.group_by("model", "color", "parent")
        .agg(
            yes=pl.col("noticed").sum(),
            no=pl.col("noticed").not_().sum(),
            pct=pl.col("noticed").mean().round_sig_figs(digits=2),
        )
        .sort("model", "color", "parent")
    )
    return (model_summary,)


@app.cell
def _(mo, model_summary):
    mo.ui.table(model_summary)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Multigranular Optimization
    """)
    return


@app.cell
def _(chi2_contingency, fisher_exact, model_summary):
    _grouped = model_summary.row(0)[3:5]
    _alone = model_summary.row(1)[3:5]
    _table = [_alone, _grouped]
    print("Unswapped")
    chi_squared_mo_unswapped = chi2_contingency(_table)
    print(fisher_exact(_table))

    print("Swapped")
    _grouped = model_summary.row(2)[3:5]
    _alone = model_summary.row(3)[3:5]
    _table = [_alone, _grouped]
    print(fisher_exact(_table))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Just Attention
    """)
    return


@app.cell
def _(fisher_exact, model_summary):
    _grouped = model_summary.row(4)[3:5]
    _alone = model_summary.row(5)[3:5]
    _table = [_alone, _grouped]
    print("Unswapped")
    print(fisher_exact(_table))

    print("Swapped")
    _grouped = model_summary.row(6)[3:5]
    _alone = model_summary.row(7)[3:5]
    _table = [_alone, _grouped]
    print(fisher_exact(_table))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Task Agnostic
    """)
    return


@app.cell
def _(fisher_exact, model_summary):
    _grouped = model_summary.row(8)[3:5]
    _alone = model_summary.row(9)[3:5]
    _table = [_alone, _grouped]
    print("Unswapped")
    print(fisher_exact(_table))

    _grouped = model_summary.row(10)[3:5]
    _alone = model_summary.row(11)[3:5]
    _table = [_alone, _grouped]
    print("Swapped")
    print(fisher_exact(_table))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Fixed Resource
    """)
    return


@app.cell
def _(fisher_exact, model_summary):
    _grouped = model_summary.row(12)[3:5]
    _alone = model_summary.row(13)[3:5]
    _table = [_alone, _grouped]
    print("Unswapped")
    print(fisher_exact(_table))

    _grouped = model_summary.row(14)[3:5]
    _alone = model_summary.row(15)[3:5]
    _table = [_alone, _grouped]
    print("Swapped")
    print(fisher_exact(_table))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Noticing rates by design
    """)
    return


@app.cell
def _(Model, human_notice_summary, model_summary, pl):
    notice_by_design = pl.concat(
        [
            model_summary.select(["model", "color", "parent", "pct"]),
            human_notice_summary.with_columns(
                model=pl.lit("Human").cast(Model)
            ).select(["model", "color", "parent", "pct"]),
        ],
        how="vertical",
    ).sort(["model", "color", "parent"])
    return (notice_by_design,)


@app.cell
def _(mo, notice_by_design):
    mo.ui.table(notice_by_design)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Figure 5
    """)
    return


@app.cell
def _(alt, notice_by_design, pl):
    FONT = "Georgia, serif"

    MODEL_ORDER = ["Human", "mo", "ja", "ta", "fr"]

    MODEL_LABELS = {
        "Human": "Humans",
        "mo": "Multigranular\nOptimization",
        "ja": "Just\nAttention",
        "ta": "Task\nAgnostic",
        "fr": "Fixed\nResource",
    }

    FILL_MAP = {
        ("Human", "light"): "#f5f5f5",
        ("Human", "dark"): "#3a3a3a",
        ("mo", "light"): "#f5f5f5",
        ("mo", "dark"): "#3a3a3a",
        ("ja", "light"): "#f5f5f5",
        ("ja", "dark"): "#3a3a3a",
        ("ta", "light"): "#f5f5f5",
        ("ta", "dark"): "#3a3a3a",
        ("fr", "light"): "#f5f5f5",
        ("fr", "dark"): "#3a3a3a",
    }

    STROKE_MAP = {
        ("Human", "light"): "#e67319",
        ("Human", "dark"): "transparent",
        ("mo", "light"): "#33a3dd",
        ("mo", "dark"): "transparent",
        ("ja", "light"): "transparent",
        ("ja", "dark"): "transparent",
        ("ta", "light"): "transparent",
        ("ta", "dark"): "transparent",
        ("fr", "light"): "transparent",
        ("fr", "dark"): "transparent",
    }

    MODEL_GLYPHS = {
        ("Human", "light"): "○",
        ("Human", "dark"): "●",
        ("mo", "light"): "○○",
        ("mo", "dark"): "●●",
        ("ja", "light"): "○",
        ("ja", "dark"): "●",
        ("ta", "light"): "○○",
        ("ta", "dark"): "●●",
        ("fr", "light"): "○",
        ("fr", "dark"): "●",
    }

    glyph_df = notice_by_design.with_columns(
        pct=pl.col("pct") * 100 + 0.5,
        fill=pl.struct(["model", "color"]).map_elements(
            lambda s: FILL_MAP[(s["model"], s["color"])], return_dtype=pl.String
        ),
        stroke_fill=pl.struct(["model", "color"]).map_elements(
            lambda s: STROKE_MAP[(s["model"], s["color"])],
            return_dtype=pl.String,
        ),
        glyph=pl.struct(["model", "color"]).map_elements(
            lambda s: MODEL_GLYPHS[(s["model"], s["color"])],
            return_dtype=pl.String,
        ),
    )

    bar_chart = (
        alt.Chart(glyph_df)
        .mark_bar(strokeWidth=1.5)
        .encode(
            x=alt.X(
                "color:N",
                title=None,
                axis=None,
                sort=["light", "dark"],
                scale=alt.Scale(type="band", paddingOuter=0.3),
            ),
            xOffset=alt.XOffset(
                "parent:N",
                sort=[
                    "lone",
                    "grouped",
                ],  # light-lone, light-grouped, dark-lone, dark-grouped
            ),
            y=alt.Y(
                "pct:Q",
                title="Noticed (%)",
                scale=alt.Scale(domain=[-5, 100]),
                axis=alt.Axis(
                    values=[0, 25, 50, 75, 100],
                    titleFontSize=17,
                    labelFontSize=13,
                    titleFont=FONT,
                    labelFont=FONT,
                    domainWidth=1.5,
                ),
            ),
            color=alt.Color("fill:N", scale=None, legend=None),
            stroke=alt.Stroke("stroke_fill:N", scale=None, legend=None),
            column=alt.Column(
                "model:N",
                sort=MODEL_ORDER,
                title=None,
                header=alt.Header(labelFontSize=0, labelPadding=0, title=None),
            ),
        )
        .properties(width=80, height=110)
        .configure_view(stroke=None)
        .configure_axis(grid=False)
    )

    bar_chart
    return (FONT,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Modelling trial-level noticing
    """)
    return


@app.cell
def _(linregress, pl):
    CorResult = pl.Struct({"r^2": pl.Float64, "p_value": pl.Float64})

    def safe_linear_fit(x, y):
        try:
            result = linregress(x, y)
            return {
                "r^2": result.rvalue**2,
                "p_value": result.pvalue,
            }
        except:
            return {"r^2": float("nan"), "p_value": float("nan")}

    def fit_model(data: pl.Struct):
        x = data.struct.field("covariate")
        y = data.struct.field("noticed")
        return safe_linear_fit(x, y)

    return CorResult, fit_model, safe_linear_fit


@app.cell
def _(CorResult, all_models, all_noticed, fit_model, periphery_df_stub, pl):
    def fit_models_to_human(humans: pl.DataFrame, models: pl.DataFrame):

        df = humans.join(
            models, on=["scene", "parent", "color"], how="left"
        ).with_columns(pl.col("noticed").fill_null(strategy="zero"))

        fits = (
            df.group_by("model")
            .agg(
                regression=pl.struct("covariate", "noticed").map_batches(
                    fit_model,
                    return_dtype=CorResult,
                    returns_scalar=True,
                )
            )
            .unnest("regression")
            .sort("model")
        )
        return fits

    models_trial_lvl = (
        all_models.group_by(
        "model", "color", "parent", "scene"
    ).agg(covariate=pl.col("noticed").mean())
    .vstack(periphery_df_stub)
    )
    model_names = (
        models_trial_lvl.select(pl.col("model").unique())
        .sort("model")["model"]
        .to_numpy()
    )
    humans_trial_lvl = all_noticed.group_by("color", "parent", "scene").agg(
        pl.col("noticed").mean()
    )
    model_fits = fit_models_to_human(humans_trial_lvl, models_trial_lvl)
    print(model_fits)
    return fit_models_to_human, humans_trial_lvl, model_names, models_trial_lvl


@app.cell
def _(mo, models_trial_lvl):
    mo.ui.table(models_trial_lvl)
    return


@app.cell
def _(mo, models_trial_lvl):
    mo.ui.table(models_trial_lvl)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Boostrapped analyses
    """)
    return


@app.cell
def _(pl):
    def ordinary_by_subj(df: pl.DataFrame):
        """Samples subjects with replacement"""
        sample = (
            df.group_by("uid")
            .agg(pl.all())
            .sample(fraction=1.0, with_replacement=True)
            .explode(pl.all().exclude("uid"))
        )
        return sample

    def split_by_subj(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
        """
        Randomly splits the dataframe into two roughly equally sized groups based on unique subjects (uid).

        The split is done at the subject level (each uid goes entirely into one group or the other).
        Returns a tuple (group_A, group_B).

        Parameters
        ----------
        df : pl.DataFrame
            Input dataframe containing at least a 'uid' column

        Returns
        -------
        tuple[pl.DataFrame, pl.DataFrame]
            (group_A, group_B) — two dataframes with disjoint sets of uids
        """
        # Get unique uids and shuffle them
        unique_subjects = (
            df.select("uid")
            .unique()
            .with_row_index()  # temporary index to help with splitting
        )

        n_subjects = unique_subjects.height
        if n_subjects < 2:
            raise ValueError(
                "DataFrame must contain at least 2 unique subjects to split"
            )

        # Shuffle the subjects
        shuffled = unique_subjects.sample(
            n=n_subjects,
            shuffle=True,
        )

        # Split into two roughly equal parts
        mid = n_subjects // 2

        groupA_uids = shuffled.head(mid).select("uid")
        groupB_uids = shuffled.tail(n_subjects - mid).select("uid")

        # Join back to original data
        groupA = df.join(groupA_uids, on="uid", how="inner")
        groupB = df.join(groupB_uids, on="uid", how="inner")

        return groupA, groupB

    return ordinary_by_subj, split_by_subj


@app.cell
def _(
    Callable,
    Color,
    CorResult,
    Parent,
    all_noticed,
    fit_model,
    np,
    nscenes,
    pl,
    split_by_subj,
):
    _trial_design = pl.DataFrame(
        [
            [scene + 1, col, par]
            for par in ["grouped", "lone"]
            for col in ["light", "dark"]
            for scene in range(nscenes)
        ],
        schema={"scene": pl.UInt8, "color": Color, "parent": Parent},
        orient="row",
    )

    def bootstrap_notice_rate(df: pl.DataFrame):
        df = df.group_by("scene", "color", "parent").agg(
            pl.col("noticed").mean()
        )
        df = (
            _trial_design.join(df, on=["scene", "color", "parent"], how="left")
            .fill_null(0.0)
            .cast({"scene": pl.UInt8})
            .sort("scene", "color", "parent")
        )
        return df

    def bootstrap_subject_split_half_step(rng: Callable = split_by_subj):
        a, b = rng(all_noticed)
        a = bootstrap_notice_rate(a)
        b = bootstrap_notice_rate(b)
        df = a.rename({"noticed": "covariate"}).join(
            b, on=["scene", "color", "parent"], how="left"
        )
        return df

    def bootstrap_subject_split_half(
        steps: int = 10000,
    ):
        samples = np.zeros(steps)
        for i in range(steps):
            df = bootstrap_subject_split_half_step()
            samples[i] = df.select(
                regression=pl.struct("covariate", "noticed").map_batches(
                    fit_model, return_dtype=CorResult, returns_scalar=True
                )
            ).unnest("regression")["r^2"][0]

        return samples

    return (bootstrap_notice_rate,)


@app.cell
def _(models_trial_lvl, pl):
    models_trial_lvl.select(pl.col("model").unique()).sort("model")[
        "model"
    ].to_numpy()
    return


@app.cell
def _(
    Callable,
    all_noticed,
    bootstrap_notice_rate,
    fit_models_to_human,
    model_names,
    models_trial_lvl,
    np,
    ordinary_by_subj,
    pl,
):
    def bootstrap_model_fits(
        steps: int = 10000,
        rng: Callable = ordinary_by_subj,
    ):
        n = model_names.shape[0]
        samples = np.zeros((steps, n))
        for i in range(steps):
            human_sample = bootstrap_notice_rate(rng(all_noticed))
            fit_df = fit_models_to_human(human_sample, models_trial_lvl)
            samples[i] = fit_df["r^2"].to_numpy()

        _boot_dict = {
            str(model): samples[:, i] for (i, model) in enumerate(model_names)
        }
        _boot_dict["sample"] = range(steps)
        boot_df = pl.DataFrame(_boot_dict)
        return boot_df

    return (bootstrap_model_fits,)


@app.cell
def _(bootstrap_model_fits):
    fit_samples = bootstrap_model_fits(10000)
    return (fit_samples,)


@app.cell
def _(fit_samples, np):
    mo_cis = np.percentile(fit_samples.select("mo").to_numpy(), [2.5, 97.5])
    ja_cis = np.percentile(fit_samples.select("ja").to_numpy(), [2.5, 97.5])
    fr_cis = np.percentile(fit_samples.select("fr").to_numpy(), [2.5, 97.5])
    ta_cis = np.percentile(fit_samples.select("ta").to_numpy(), [2.5, 97.5])
    ecc_cis = np.percentile(fit_samples.select("ecc").to_numpy(), [2.5, 97.5])
    return ecc_cis, fr_cis, ja_cis, mo_cis, ta_cis


@app.cell(hide_code=True)
def _(ecc_cis, fr_cis, ja_cis, mo, mo_cis, ta_cis):
    mo.md(rf"""
    MO 95% CIs = {mo_cis}

    JA 95% CIs = {ja_cis}

    TA 95% CIs = {ta_cis}

    FR 95% CIs = {fr_cis}

    ECC 95% CIs = {ecc_cis}
    """)
    return


@app.cell
def _(fit_samples, np, pl):
    mo_vs_ja_diff = fit_samples.select(diff=pl.col("mo") - pl.col("ja"))

    mo_vs_ja_CIs = np.percentile(mo_vs_ja_diff["diff"].to_numpy(), [2.5, 97.5])

    mo_vs_ja_pval = mo_vs_ja_diff.select(pl.col("diff") < 0).mean().item()

    mo_vs_ta_diff = fit_samples.select(diff=pl.col("mo") - pl.col("ta"))

    mo_vs_ta_CIs = np.percentile(mo_vs_ta_diff["diff"].to_numpy(), [2.5, 97.5])

    mo_vs_ta_pval = mo_vs_ta_diff.select(pl.col("diff") < 0).mean().item()

    mo_vs_fr_diff = fit_samples.select(diff=pl.col("mo") - pl.col("fr"))

    mo_vs_fr_CIs = np.percentile(mo_vs_fr_diff["diff"].to_numpy(), [2.5, 97.5])

    mo_vs_fr_pval = mo_vs_fr_diff.select(pl.col("diff") < 0).mean().item()

    mo_vs_ecc_diff = fit_samples.select(diff=pl.col("mo") - pl.col("ecc"))

    mo_vs_ecc_CIs = np.percentile(mo_vs_ecc_diff["diff"].to_numpy(), [2.5, 97.5])

    mo_vs_ecc_pval = mo_vs_ecc_diff.select(pl.col("diff") < 0).mean().item()
    return (
        mo_vs_ecc_CIs,
        mo_vs_ecc_pval,
        mo_vs_fr_CIs,
        mo_vs_fr_pval,
        mo_vs_ja_CIs,
        mo_vs_ja_pval,
        mo_vs_ta_CIs,
        mo_vs_ta_pval,
    )


@app.cell(hide_code=True)
def _(
    mo,
    mo_vs_ecc_CIs,
    mo_vs_ecc_pval,
    mo_vs_fr_CIs,
    mo_vs_fr_pval,
    mo_vs_ja_CIs,
    mo_vs_ja_pval,
    mo_vs_ta_CIs,
    mo_vs_ta_pval,
):
    mo.md(rf"""
    MO > Just Attention: p-value = {mo_vs_ja_pval}

    MO > Just Attention: 95% CIs = {mo_vs_ja_CIs}

    MO > Task Agnostic: p-value = {mo_vs_ta_pval}

    MO > Task Agnostic: 95% CIs = {mo_vs_ta_CIs}

    MO > Fixed Resource: p-value = {mo_vs_fr_pval}

    MO > Fixed Resource: 95% CIs = {mo_vs_fr_CIs}

    MO > Peripheral Eccentricity: p-value = {mo_vs_ecc_pval}

    MO > Peripheral Eccentricity: 95% CIs = {mo_vs_ecc_CIs}
    """)
    return


@app.cell
def _(Color, main_noticed, pl):
    main_agg_result = (
        main_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
        .with_columns(color=pl.lit("light").cast(Color))
    )
    return (main_agg_result,)


@app.cell
def _(Color, ctrl_noticed, pl):
    ctrl_agg_result = (
        ctrl_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
        .with_columns(color=pl.lit("dark").cast(Color))
    )
    return (ctrl_agg_result,)


@app.cell
def _(ctrl_agg_result, main_agg_result, pl):
    agg_result = (
        pl.concat([main_agg_result, ctrl_agg_result])
        .select("color", "parent", "noticed", "len")
        .sort(["color", "parent"], descending=[False, True])
    )
    print(agg_result)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Figure 5c
    """)
    return


@app.cell(hide_code=True)
def _(alt, ctrl_noticed, main_noticed, mo, models_trial_lvl, pl):
    mo_model = models_trial_lvl.filter(pl.col("model") == "mo")

    model_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(mo_model, on=["scene", "parent", "color"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero"))
    )

    _base = alt.Chart(model_vs_noticing).encode(
        alt.X("covariate:Q").title("Model % Noticed").scale(padding=0.01),
        alt.Y("noticed:Q").title("Human % Noticed").scale(padding=0.01),
        alt.Shape("parent:N"),
        alt.Color("color:N"),
        alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=250)
    _labels = _base.mark_text()
    _chart = (
        _points
        + _points.transform_regression("covariate", "noticed", method="linear")
        .mark_line()
        .transform_fold(["reg-line"], as_=["Regression", "y"])
        .encode(alt.Color("Regression:N"), alt.Shape("Regression:N"))
        + _labels
    ).properties(width=600)
    mo.ui.altair_chart(_chart)
    return mo_model, model_vs_noticing


@app.cell
def _(FONT, alt, ctrl_noticed, main_noticed, mo_model, pl):
    fig_model_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(mo_model, on=["scene", "parent", "color"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero"))
        .with_columns(
            noticed_pct=pl.col("noticed") * 100,
            covariate_pct=pl.col("covariate") * 100,
        )
    )

    # ------------------------------------------------------------------ style --
    DARK_GRAY = "#3a3a3a"
    LIGHT_GRAY = "#c9c9c9"
    LINE_COLOR = "#4d9bd6"
    LINE_WIDTH = 1.8

    _base = alt.Chart(fig_model_vs_noticing).encode(
        alt.X("covariate_pct:Q")
        .title("Model Noticed (%)")
        .scale(domain=[-4, 100])
        .axis(tickCount=6),
        alt.Y("noticed_pct:Q")
        .title("Human Noticed (%)")
        .scale(domain=[-4, 85])
        .axis(tickCount=6),
        alt.Shape(
            "parent:N",
            scale=alt.Scale(
                domain=["lone", "grouped"], range=["square", "circle"]
            ),
            legend=None,
        ),
    )

    _points = _base.mark_point(
        size=150,
        filled=True,          # let the fill channel control the interior
        strokeWidth=2.0,
    ).encode(
        fill=alt.Fill(
            "color:N",
            scale=alt.Scale(
                domain=["light", "dark"],
                range=[LIGHT_GRAY, "transparent"],
            ),
            legend=None,
        ),
        stroke=alt.Stroke(
            "color:N",
            scale=alt.Scale(
                domain=["light", "dark"], range=[LIGHT_GRAY, DARK_GRAY]
            ),
            legend=None,
        ),
        tooltip=[
            "scene:Q",
            "color:N",
            "parent:N",
            "covariate_pct:Q", 
        ],
    )

    regression = (
        _base.transform_regression(
            "covariate_pct", "noticed_pct", method="linear"
        )
        .mark_line(color=LINE_COLOR, strokeWidth=LINE_WIDTH)
        .encode(color=alt.value(LINE_COLOR), size=alt.value(LINE_WIDTH))
    )

    chart = (
        (regression + _points)
        .properties(width=500, height=250)
        .configure_view(stroke=None)
        .configure_axis(
            grid=False,
            domain=True,
            domainWidth=1.2,
            tickColor="#3a3a3a",
            labelFont=FONT,
            labelFontSize=14,
            titleFont=FONT,
            titleFontSize=17,
        )
        .configure_axisX(titlePadding=10)
        .configure_axisY(titlePadding=6)
    )

    chart
    return DARK_GRAY, LIGHT_GRAY, LINE_COLOR, LINE_WIDTH


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Centroid Analysis
    """)
    return


@app.cell
def _(Color, Model, Parent, pl):
    periphery_df_stub = (
        pl.read_csv("data/periphery.csv", 
                    schema={
                        "scene": pl.UInt8, 
                        "color": Color, 
                        "parent": Parent, 
                        "chain" : pl.Int64, 
                        "distance": pl.Float64
                    },)
        .group_by("scene", "color", "parent")
        .agg(pl.col("distance").mean().alias("covariate"))
        .with_columns(model = pl.lit("ecc").cast(Model))
        .select(["model", "color", "parent", "scene", "covariate"])
    )
    return (periphery_df_stub,)


@app.cell
def _(Color, Parent, pl):
    periphery_df = (
        pl.read_csv("data/periphery.csv", 
                    schema={
                        "scene": pl.UInt8, 
                        "color": Color, 
                        "parent": Parent, 
                        "chain" : pl.Int64, 
                        "distance": pl.Float64
                    },)
        .group_by("scene", "color", "parent")
        .agg(pl.col("distance").mean().alias("periphery"))
    )
    return (periphery_df,)


@app.cell
def _(
    DARK_GRAY,
    FONT,
    LIGHT_GRAY,
    LINE_COLOR,
    LINE_WIDTH,
    alt,
    ctrl_noticed,
    main_noticed,
    mo,
    periphery_df,
    pl,
):
    periphery_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(periphery_df, on=["scene", "parent", "color"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero") * 100)
    )

    _base = alt.Chart(periphery_vs_noticing).encode(
        alt.X("periphery:Q")
        .title("Periphery extent (world units)")
        .axis(tickCount=6),
        alt.Y("noticed:Q")
        .title("Human Noticed (%)")
        .scale(domain=[-4, 85])
        .axis(tickCount=6),
        alt.Shape(
            "parent:N",
            scale=alt.Scale(
                domain=["lone", "grouped"], range=["square", "circle"]
            ),
            legend=None,
        ),
    )

    _points = _base.mark_point(
        size=150,
        filled=True,          # let the fill channel control the interior
        strokeWidth=2.0,
    ).encode(
        fill=alt.Fill(
            "color:N",
            scale=alt.Scale(
                domain=["light", "dark"],
                range=[LIGHT_GRAY, "transparent"],
            ),
            legend=None,
        ),
        stroke=alt.Stroke(
            "color:N",
            scale=alt.Scale(
                domain=["light", "dark"], range=[LIGHT_GRAY, DARK_GRAY]
            ),
            legend=None,
        ),
        tooltip=[
            "scene:Q",
            "color:N",
            "parent:N",
            "periphery:Q", 
        ],
    )

    _regression = (
        _base.transform_regression(
            "periphery", "noticed", method="linear"
        )
        .mark_line(color=LINE_COLOR, strokeWidth=LINE_WIDTH)
        .encode(color=alt.value(LINE_COLOR), size=alt.value(LINE_WIDTH))
    )

    _chart = (
        (_regression + _points)
        .properties(width=500, height=250)
        .configure_view(stroke=None)
        .configure_axis(
            grid=False,
            domain=True,
            domainWidth=1.2,
            tickColor="#3a3a3a",
            labelFont=FONT,
            labelFontSize=14,
            titleFont=FONT,
            titleFontSize=17,
        )
        .configure_axisX(titlePadding=10)
        .configure_axisY(titlePadding=6)
    )

    mo.ui.altair_chart(_chart)
    return (periphery_vs_noticing,)


@app.cell
def _(periphery_vs_noticing, safe_linear_fit):
    safe_linear_fit(
        periphery_vs_noticing["periphery"],
        periphery_vs_noticing["noticed"],
    )
    return


@app.cell
def _(json):
    DATASET_PATH = "data/study2/animations.json"
    data = ""
    with open(DATASET_PATH) as f:
        data = json.load(f)
    return (data,)


@app.cell
def _(Color, Parent, data, np, pl):
    WINDOW = 48  # frames collected after the critical frame (inclusive window = 49 frames)

    ecc_stats = []
    centroid_stats = []
    for i, trial in enumerate(data["trials"]):
        frame = trial["gorilla"]["frame"]
        positions = np.asarray(trial["positions"])  # (frames, objects, 2)
        window = positions[
            frame : frame + WINDOW + 1
        ]  # next 48 frames after `frame`

        uswappped_centroid = window[:, 0, :]
        swapped_centroid = window[:, 4:, :].mean(axis=1)

        l_to_i = np.linalg.norm(uswappped_centroid - window[:, 3, :], axis=1)
        s_to_l = np.linalg.norm(swapped_centroid - window[:, 0, :], axis=1)
        s_to_i = np.linalg.norm(swapped_centroid - window[:, 3, :], axis=1)
        ecc_stats.append(
            {
                "scene": i + 1,
                "color": "light",
                "parent": "lone",
                "ecc": 0.0,
            }
        )

        ecc_stats.append(
            {
                "scene": i + 1,
                "color": "light",
                "parent": "grouped",
                "ecc": float(l_to_i.mean()),
            }
        )

        ecc_stats.append(
            {
                "scene": i + 1,
                "color": "dark",
                "parent": "lone",
                "ecc": float(s_to_l.mean()),
            }
        )

        ecc_stats.append(
            {
                "scene": i + 1,
                "color": "dark",
                "parent": "grouped",
                "ecc": float(s_to_i.mean()),
            }
        )

        centroid_stats.append(
            {
                "scene": i + 1,
                "critical_frame": frame,
                "l_to_i": float(l_to_i.mean()),
                "s_to_l": float(s_to_l.mean()),
                "s_to_i": float(s_to_i.mean()),
            }
        )

    ecc_stats = pl.DataFrame(
        ecc_stats,
        schema={"scene": None, "color": Color, "parent": Parent, "ecc": None},
    )
    centroid_stats = pl.DataFrame(centroid_stats)
    return centroid_stats, ecc_stats


@app.cell
def _(ecc_stats):
    ecc_stats
    return


@app.cell
def _(centroid_stats, humans_trial_lvl, pl):
    scene_notice_diff = (
        humans_trial_lvl.pivot(on="parent", values="noticed")
        .with_columns(notice_diff=pl.col("lone") - pl.col("grouped"))
        .join(centroid_stats, on="scene")
        .with_columns(
            ecc=pl.when(pl.col("color") == "dark")
            .then(pl.col("s_to_l") - pl.col("s_to_i"))
            .otherwise(pl.col("l_to_i"))
        )
    )
    scene_notice_diff
    return (scene_notice_diff,)


@app.cell
def _(alt, mo, scene_notice_diff):
    _base = alt.Chart(scene_notice_diff).encode(
        alt.X("ecc:Q").title("Δ Ecc: |Lone - Irrelevant|").scale(padding=0.01),
        alt.Y("notice_diff:Q").title("Δ Human Noticed").scale(padding=0.01),
        alt.Color("color:N"),
        alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=250)
    _labels = _base.mark_text()
    _chart = (
        _points
        + _points.transform_regression("ecc", "notice_diff", method="linear")
        .mark_line()
        .transform_fold(["reg-line"], as_=["Regression", "y"])
        .encode(alt.Color("Regression:N"), alt.Shape("Regression:N"))
        + _labels
    ).properties(width=600)
    mo.ui.altair_chart(_chart)
    return


@app.cell
def _(safe_linear_fit, scene_notice_diff):
    safe_linear_fit(scene_notice_diff["ecc"], scene_notice_diff["notice_diff"])
    return


@app.cell
def _(alt, mo, model_vs_noticing, pl):
    mo_scene_notice_diff = model_vs_noticing.pivot(
        on="parent", values=["noticed", "covariate"]
    ).with_columns(
        notice_diff=pl.col("noticed_lone") - pl.col("noticed_grouped"),
        covariate_diff=pl.col("covariate_lone") - pl.col("covariate_grouped"),
    )

    _base = alt.Chart(mo_scene_notice_diff).encode(
        alt.X("covariate_diff:Q").title("Δ Model Noticed").scale(padding=0.01),
        alt.Y("notice_diff:Q").title("Δ Human Noticed").scale(padding=0.01),
        alt.Color("color:N"),
        alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=250)
    _labels = _base.mark_text()
    _chart = (
        _points
        + _points.transform_regression(
            "covariate_diff", "notice_diff", method="linear"
        )
        .mark_line()
        .transform_fold(["reg-line"], as_=["Regression", "y"])
        .encode(alt.Color("Regression:N"), alt.Shape("Regression:N"))
        + _labels
    ).properties(width=600)
    mo.ui.altair_chart(_chart)
    return (mo_scene_notice_diff,)


@app.cell
def _(mo_scene_notice_diff, safe_linear_fit):
    safe_linear_fit(
        mo_scene_notice_diff["covariate_diff"],
        mo_scene_notice_diff["notice_diff"],
    )
    return


@app.cell
def _(alt, ctrl_noticed, ecc_stats, main_noticed, mo, pl):
    ecc_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(ecc_stats, on=["scene", "parent", "color"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero"))
    )

    _base = alt.Chart(ecc_vs_noticing).encode(
        alt.X("ecc:Q").title("Model Eccentricity").scale(padding=0.01),
        alt.Y("noticed:Q").title("Human % Noticed").scale(padding=0.01),
        alt.Shape("parent:N"),
        alt.Color("color:N"),
        # alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=250)
    _labels = _base.mark_text()
    _chart = (
        _points
        + _points.transform_regression("ecc", "noticed", method="linear")
        .mark_line()
        .transform_fold(["reg-line"], as_=["Regression", "y"])
        .encode(alt.Color("Regression:N"), alt.Shape("Regression:N"))
        + _labels
    ).properties(width=600)
    mo.ui.altair_chart(_chart)
    return (ecc_vs_noticing,)


@app.cell
def _(ecc_vs_noticing, safe_linear_fit):
    safe_linear_fit(
        ecc_vs_noticing["ecc"],
        ecc_vs_noticing["noticed"],
    )
    return


@app.cell
def _():
    return


@app.cell
def _(mo, model_vs_noticing):
    mo.ui.table(model_vs_noticing)
    return


if __name__ == "__main__":
    app.run()
