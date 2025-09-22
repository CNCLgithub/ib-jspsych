import marimo

__generated_with = "0.14.12"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(r""" ## Setup""")
    return


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
    return (
        Callable,
        alt,
        chi2_contingency,
        json,
        linregress,
        logit,
        np,
        ols,
        partial,
        pl,
        sm,
        ttest_ind,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Type Definitions""")
    return


@app.cell
def _(pl):
    # Polars dataseries types
    Parent = pl.Enum(["Grouped", "Alone"])
    Color = pl.Enum(["Light", "Dark"])
    Model = pl.Enum(["MO", "Just AC", "Fixed Resource"])
    return Color, Model, Parent


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Loading data""")
    return


@app.cell
def _():
    exp = "target-ensemble"
    version = "2025-06-09_W96KtK-v2-preregistered"
    return exp, version


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""#### Ground truth counts""")
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
        .replace("-v2", "")
        .replace("-preregistered", "")
    )
    with open(f"data/{exp}-{base_version}-manifest.json", "r") as file:
        manifest = json.load(file)

    gt_counts_raw = manifest["counts"]
    nscenes = len(gt_counts_raw)

    gt_counts = pl.DataFrame(
        {"scene": np.arange(nscenes) + 1, "count": gt_counts_raw},
        schema=col_count_schema,
    )
    gt_counts
    return base_version, gt_counts, nscenes


@app.cell
def _(Parent, nscenes, pl):
    trial_design = pl.DataFrame(
        [
            [scene + 1, par]
            for par in ["Grouped", "Alone"]
            for scene in range(nscenes)
        ],
        schema={"scene": pl.UInt8, "parent": Parent},
        orient="row",
    )
    return (trial_design,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""#### Human data""")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Exclusion Criteria""")
    return


@app.cell
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
    def load_behavior(path: str):
        # Load bounce count data
        count_df = pl.read_csv(
            path + "_counts.csv", schema=count_schema
        ).with_columns(order=pl.col("order").rank().over("uid"))

        # Load notice data
        noticed_raw = pl.read_csv(path + "_noticed.csv", schema=notice_schema)
        # Exclude subjects that count poorly
        noticed_df, ex_rate, perf = exclude_subjects(noticed_raw, count_df)
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
            .then(pl.lit("Grouped"))
            .otherwise(pl.lit("Alone"))
            .cast(Parent)
        ).select(pl.all().exclude("grouped"))
        noticed_df = trial_design.join(
            noticed_df, on=["scene", "parent"], how="left"
        ).fill_null(0.0)

        return (noticed_df, ex_rate, perf)
    return (load_behavior,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""### Loading human data""")
    return


@app.cell
def dataload(Color, exp, load_behavior, pl, version):
    main_noticed, main_ex_rate, main_perf = load_behavior(f"data/{exp}-{version}")
    main_noticed = main_noticed.with_columns(color=pl.lit("Light").cast(Color))
    main_perf = main_perf.with_columns(color=pl.lit("Light").cast(Color))

    ctrl_noticed, ctrl_ex_rate, ctrl_perf = load_behavior(
        f"data/{exp}-{version}-swapped"
    )
    ctrl_noticed = ctrl_noticed.with_columns(color=pl.lit("Dark").cast(Color))
    ctrl_perf = ctrl_perf.with_columns(color=pl.lit("Dark").cast(Color))

    all_noticed = pl.concat([main_noticed, ctrl_noticed]).cast({"scene": pl.UInt8})
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
def _(main_noticed, pl, ttest_ind):
    ttest_ind(
        main_noticed.filter(pl.col("parent") == "Alone")["noticed"],
        main_noticed.filter(pl.col("parent") == "Grouped")["noticed"],
    )
    main_noticed.filter(pl.col("parent") == "Alone")["noticed"].mean()
    return


@app.cell
def _(chi2_contingency, main_noticed, pl):
    _df = (
        main_noticed.group_by(
            "parent",
        )
        .agg(yes=pl.col("noticed").sum(), no=pl.col("noticed").not_().sum())
        .sort("parent")
    )
    print(_df)
    _grouped = _df.row(0)[1:3]
    _alone = _df.row(1)[1:3]
    print(chi2_contingency([_alone, _grouped]))
    return


@app.cell
def _(chi2_contingency, ctrl_noticed, pl):
    _df = (
        ctrl_noticed.group_by(
            "parent",
        )
        .agg(yes=pl.col("noticed").sum(), no=pl.col("noticed").not_().sum())
        .sort("parent")
    )
    print(_df)
    _grouped = _df.row(0)[1:3]
    _alone = _df.row(1)[1:3]
    print(chi2_contingency([_alone, _grouped]))
    return


@app.cell
def _(all_noticed, chi2_contingency, pl):
    _df = (
        all_noticed.group_by(
            "color",
        )
        .agg(yes=pl.col("noticed").sum(), no=pl.col("noticed").not_().sum())
        .sort("color")
    )
    print(_df)
    _unswapped = _df.row(0)[1:3]
    _swapped = _df.row(1)[1:3]
    print(chi2_contingency([_unswapped, _swapped]))
    return


@app.cell
def _(main_noticed, ols, pl):
    # Just the unswapped data
    _df = main_noticed.cast({"parent": pl.UInt32, "color": pl.UInt32}).cast(
        {"parent": pl.Float32, "color": pl.Float32, "noticed": pl.Float32}
    )
    # linear model of parent on noticing
    _fit = ols("noticed ~ parent", data=_df).fit()
    print(_fit.summary())
    return


@app.cell
def _(all_noticed, logit, pl):
    # Data from both unswapped and swapped
    _df = all_noticed.cast({"parent": pl.UInt32, "color": pl.UInt32}).cast(
        {"parent": pl.Float32, "color": pl.Float32, "noticed": pl.Float32}
    )
    print(
        all_noticed.group_by("parent", "color")
        .agg(pl.col("noticed").mean())
        .select("color", "parent", "noticed")
        .sort("color", "parent")
    )
    _fit = logit("noticed ~ color + parent", data=_df).fit()
    # _table = sm.stats.anova_lm(_fit, typ=2)  # Type 2 Anova DataFrame
    print(_fit.summary())
    # print(f"Interaction coefficient: {_fit.params['parent:color']:.4f}")
    # print(f"Interaction p-value: {_fit.pvalues['parent:color']:.4f}")
    print(_fit.get_margeff().summary())
    return


@app.cell
def _(all_noticed, ols, pl, sm):
    # Data from both unswapped and swapped
    _df = all_noticed.cast({"parent": pl.UInt32, "color": pl.UInt32}).cast(
        {"parent": pl.Float32, "color": pl.Float32, "noticed": pl.Float32}
    )
    _fit = ols("noticed ~ parent*color", data=_df).fit()
    _table = sm.stats.anova_lm(_fit, typ=2)  # Type 2 Anova DataFrame
    print(_fit.summary())
    print(_table)
    return


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
    ERROR_TRESH = 1.0


    def exclude_subjects(notice: pl.DataFrame, counts: pl.DataFrame):
        """Excludes subjects that have an average absolute error > `ERROR_THRESH`"""
        perf = calc_performance(counts)
        passed = perf.filter(pl.col("error") < PARAMS.value["perf_thresh"]).select(
            "uid"
        )
        n_original = perf.select(pl.len()).item()
        n_passed = passed.select(pl.len()).item()
        ex_rate = (n_original - n_passed) / n_original
        # First 120 subjects
        passed = passed.head(n=120).join(notice, on="uid", how="left")
        return (passed, ex_rate, perf)
    return (exclude_subjects,)


@app.cell
def _(pl):
    def notice_metric(df: pl.DataFrame):
        noticed_by_group = (
            df.group_by("parent").agg(pl.mean("noticed")).sort("parent")
        )
        grouped, alone = noticed_by_group["noticed"]
        return alone - grouped
    return (notice_metric,)


@app.cell
def _(
    CorResult,
    crowding,
    ctrl_noticed,
    fit_model,
    full_model,
    main_noticed,
    np,
    pl,
):
    def fit_models_to_human(
        unswapped_df: pl.DataFrame, swapped_df: pl.DataFrame, models
    ):
        n = len(models)
        results = np.zeros(n)

        for i, name in enumerate(models):
            model = models[name]
            model_vs_noticing = (
                pl.concat([unswapped_df, swapped_df])
                .group_by("color", "scene", "parent")
                .agg(pl.mean("noticed"))
                .with_columns(pl.col("scene").cast(pl.UInt8))
                .join(model, on=["scene", "parent", "color"], how="left")
                .with_columns(pl.col("noticed").fill_null(strategy="zero"))
            )

            fit = model_vs_noticing.select(
                regression=pl.struct("covariate", "noticed").map_batches(
                    fit_model, return_dtype=CorResult
                )
            ).unnest("regression")
            results[i] = fit["r^2"].item()

        return results


    models = {"MO": full_model, "Crowding": crowding}
    model_names = list(models.keys())
    print(fit_models_to_human(main_noticed, ctrl_noticed, models))
    return fit_models_to_human, model_names, models


@app.cell
def _(Callable, notice_metric, partial, pl):
    def difference_metric(metric: Callable, a: pl.DataFrame, b: pl.DataFrame):
        return metric(a) - metric(b)


    diff_notice_metric = partial(difference_metric, notice_metric)
    diff_notice_metric.__doc__ = "The difference in noticing differences"
    return (diff_notice_metric,)


@app.cell
def _(Callable, np, pl):
    def ordinary_by_subj(df: pl.DataFrame):
        sample = (
            df.group_by("uid")
            .agg(pl.all())
            .sample(fraction=1.0, with_replacement=True)
            .explode(pl.all().exclude("uid"))
        )
        return sample


    def bootstrap_noticing_differences(
        metric: Callable,
        a: pl.DataFrame,
        b: pl.DataFrame,
        rng: Callable,
        steps: int = 10000,
    ):
        samples = np.zeros(steps)
        for i in range(steps):
            samples[i] = metric(rng(a), rng(b))

        return samples
    return bootstrap_noticing_differences, ordinary_by_subj


@app.cell
def _(
    Callable,
    ctrl_noticed,
    fit_models_to_human,
    main_noticed,
    model_names,
    models,
    np,
    ordinary_by_subj,
    pl,
):
    def bootstrap_model_fits(
        steps: int = 10000,
        rng: Callable = ordinary_by_subj,
    ):
        n = len(models)
        samples = np.zeros((steps, n))
        for i in range(steps):
            samples[i] = fit_models_to_human(
                rng(main_noticed), rng(ctrl_noticed), models
            )

        _boot_dict = {
            model: samples[:, i] for (i, model) in enumerate(model_names)
        }
        _boot_dict["sample"] = range(steps)
        boot_df = pl.DataFrame(_boot_dict)
        return boot_df
    return (bootstrap_model_fits,)


@app.cell
def _(bootstrap_model_fits):
    fit_samples = bootstrap_model_fits(2000)
    return (fit_samples,)


@app.cell
def _(fit_samples, np, pl):
    full_vs_crowding_diff = fit_samples.select(
        diff=pl.col("MO") - pl.col("Crowding")
    )

    full_vs_crowding_CIs = np.percentile(
        full_vs_crowding_diff["diff"].to_numpy(), [2.5, 97.5]
    )

    full_vs_crowding_pval = (
        full_vs_crowding_diff.select(pl.col("diff") < 0).mean().item()
    )
    return full_vs_crowding_CIs, full_vs_crowding_diff, full_vs_crowding_pval


@app.cell
def _(full_vs_crowding_CIs, full_vs_crowding_pval, mo):
    mo.md(
        rf"""
    Full model > crowding: p-value = {full_vs_crowding_pval}

    Full model > crowding: 95% CIs = {full_vs_crowding_CIs}
    """
    )
    return


@app.cell
def _(Model, alt, fit_samples, model_names):
    _df = fit_samples.unpivot(
        model_names, index="sample", variable_name="model", value_name="r^2"
    ).cast({"model": Model})
    alt.Chart(_df).mark_bar().encode(
        alt.X("r^2:Q").bin(maxbins=50).title("Explained Variance"),
        alt.Row("model:N"),
        y="count()",
    )
    return


@app.cell
def _(alt, full_vs_crowding_diff):
    alt.Chart(full_vs_crowding_diff).mark_bar().encode(
        alt.X("diff:Q")
        .bin(maxbins=30)
        .title("Full - Crowding (Explained Variance)"),
        y="count()",
    )
    return


@app.cell
def _(
    bootstrap_noticing_differences,
    ctrl_noticed,
    diff_notice_metric,
    main_noticed,
    ordinary_by_subj,
):
    samples = bootstrap_noticing_differences(
        diff_notice_metric, main_noticed, ctrl_noticed, ordinary_by_subj
    )
    return (samples,)


@app.cell
def _(np, samples):
    cis = np.percentile(samples, [2.5, 97.5])
    pval = np.mean(samples < 0.0)
    return cis, pval


@app.cell
def _(alt, pl, samples):
    _df = pl.DataFrame({"samples": samples})
    alt.Chart(_df).mark_bar().encode(
        alt.X("samples:Q")
        .bin(maxbins=50)
        .title("Difference: Unswapped - Swapped"),
        y="count()",
    ).properties(title="Main Exp - Ctrl Exp")
    return


@app.cell
def _(cis, mo, pval):
    mo.md(
        f"""
    p-value = {pval}

    95 % CIs = {cis}
    """
    )
    return


@app.cell
def _(Color, main_noticed, pl):
    main_agg_result = (
        main_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
        .with_columns(color=pl.lit("Light").cast(Color))
    )
    return (main_agg_result,)


@app.cell
def _(Color, ctrl_noticed, pl):
    ctrl_agg_result = (
        ctrl_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
        .with_columns(color=pl.lit("Dark").cast(Color))
    )
    return (ctrl_agg_result,)


@app.cell
def _(ctrl_noticed, mo):
    mo.ui.table(ctrl_noticed)
    return


@app.cell
def _(ctrl_agg_result, main_agg_result, pl):
    agg_result = (
        pl.concat([main_agg_result, ctrl_agg_result])
        .select("color", "parent", "noticed", "len")
        .sort(["color", "parent"], descending=[False, True])
    )
    print(agg_result)
    return


@app.cell
def _(alt, crowding, ctrl_noticed, main_noticed, mo, pl):
    crowding_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(crowding, on=["scene", "parent"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero"))
        .sort("parent", "covariate")
    )

    _chart = (
        alt.Chart(crowding_vs_noticing)
        .mark_point(size=200)
        .encode(
            alt.X("covariate:Q")
            .title("Inverse Crowding (Avg. L2 distance)")
            .scale(zero=False),
            alt.Y("noticed:Q").title("% Noticed").scale(padding=0.1),
            alt.Shape("parent:N"),
            alt.Color("color:N"),
        )
    )
    _chart = _chart + _chart.transform_regression(
        "covariate", "noticed", method="linear"
    ).mark_line().transform_fold(["reg-line"], as_=["Regression", "y"]).encode(
        alt.Color("Regression:N"), alt.Shape("Regression:N")
    )
    mo.ui.altair_chart(_chart)
    return (crowding_vs_noticing,)


@app.cell
def _(crowding_vs_noticing, linregress, pl):
    CorResult = pl.Struct({"r": pl.Float64, "p_value": pl.Float64})


    def fit_model(data: pl.Struct):
        x = data.struct.field("covariate")
        y = data.struct.field("noticed")
        result = linregress(x, y)
        return {
            "r^2": result.rvalue**2,
            "p_value": result.pvalue,
        }


    print(
        crowding_vs_noticing.group_by("color", maintain_order=True)
        .agg(
            regression=pl.struct("covariate", "noticed").map_elements(
                fit_model, return_dtype=CorResult
            )
        )
        .unnest("regression")
    )
    print(
        crowding_vs_noticing.select(
            regression=pl.struct("covariate", "noticed").map_batches(
                fit_model, return_dtype=CorResult
            )
        ).unnest("regression")
    )
    return CorResult, fit_model


@app.cell
def _(alt, ctrl_noticed, full_model, main_noticed, mo, pl):
    model_vs_noticing = (
        pl.concat([main_noticed, ctrl_noticed])
        .group_by("color", "scene", "parent")
        .agg(pl.mean("noticed"))
        .with_columns(pl.col("scene").cast(pl.UInt8))
        .join(full_model, on=["scene", "parent", "color"], how="left")
        .with_columns(pl.col("noticed").fill_null(strategy="zero"))
    )

    _base = alt.Chart(model_vs_noticing).encode(
        alt.X("covariate:Q").title("Model % Noticed").scale(zero=False),
        alt.Y("noticed:Q").title("Human % Noticed").scale(padding=0.25),
        alt.Shape("parent:N"),
        alt.Color("color:N"),
        alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=200)
    _labels = _base.mark_text()

    _chart = _points + _labels

    _chart = _points + _points.transform_regression(
        "covariate", "noticed", method="linear"
    ).mark_line().transform_fold(["reg-line"], as_=["Regression", "y"]).encode(
        alt.Color("Regression:N"), alt.Shape("Regression:N")
    )
    mo.ui.altair_chart(_chart)
    return (model_vs_noticing,)


@app.cell
def _(CorResult, fit_model, model_vs_noticing, pl):
    print(
        model_vs_noticing.group_by("color", maintain_order=True)
        .agg(
            regression=pl.struct("covariate", "noticed").map_elements(
                fit_model, return_dtype=CorResult
            )
        )
        .unnest("regression")
    )
    print(
        model_vs_noticing.select(
            regression=pl.struct("covariate", "noticed").map_batches(
                fit_model, return_dtype=CorResult
            )
        ).unnest("regression")
    )
    return


@app.cell
def _():
    return


@app.cell
def _(crowding_vs_noticing, mo):
    mo.ui.table(crowding_vs_noticing)
    return


@app.cell
def _(all_noticed, pl):
    with pl.Config(tbl_rows=50):
        print(
            all_noticed.group_by("color", "parent")
            .agg(pl.mean("noticed"), pl.len())
            .sort("color", "parent")
        )
    return


@app.cell
def _(ctrl_noticed, pl):
    with pl.Config(tbl_rows=50):
        print(
            ctrl_noticed.group_by("scene", "parent")
            .agg(pl.mean("noticed"), pl.len())
            .with_columns(pl.col("noticed").fill_null(strategy="zero"))
            .sort("scene", "parent")
        )
    return


@app.cell
def _(alt, main_noticed):
    _chart = (
        alt.Chart(main_noticed)
        .mark_bar()
        .transform_aggregate(count="count()", groupby=["description"])
        .transform_window(
            rank="rank()",
            sort=[
                alt.SortField("count", order="descending"),
                alt.SortField("description", order="ascending"),
            ],
        )
        .transform_filter(alt.datum.rank <= 10)
        .encode(
            y=alt.Y(
                "description:N",
                sort="-x",
                axis=alt.Axis(title=None),
            ),
            x=alt.X("count:Q", title="Number of records"),
            tooltip=[
                alt.Tooltip("description:N"),
                alt.Tooltip("count:Q", format=",.0f", title="Number of records"),
            ],
        )
        .properties(title="Top 10 {column}", width="container")
        .configure_view(stroke=None)
        .configure_axis(grid=False)
    )
    _chart
    return


@app.cell
def _(all_perf, alt):
    print(all_perf)
    (
        alt.Chart(all_perf).mark_bar().encode(
            alt.X("error:Q")
            .bin(maxbins=50)
            .title("Subject average performance"),
        y="count()",
        ).properties(title="Main Exp - Ctrl Exp")
    )
    return


@app.cell
def _(Color, Model, Parent, base_version, exp, pl):

    _color_snippets = pl.DataFrame(
        {
            "parent": ["Grouped", "Grouped", "Alone", "Alone"],
            "color": ["Light", "Dark", "Light", "Dark"],
        },
        schema={"parent": Parent, "color": Color},
    )
    crowding = (
        pl.read_csv(
            f"data/{exp}-{base_version}-crowding_stats.csv",
            schema={"scene": pl.UInt8, "Alone": pl.Float32, "Grouped": pl.Float32},
        )
        .unpivot(
            index="scene",
            on=["Alone", "Grouped"],
            variable_name="parent",
            value_name="crowding",
        )
        .cast({"parent": Parent})
        .rename({"crowding": "covariate"})
        .with_columns(model=pl.lit("Crowding").cast(Model))
        .join(_color_snippets, on="parent", how="left")
    )
    return (crowding,)


@app.cell
def _(Color, Model, Parent, pl):
    def load_model(name: str):
        pathname = name.replace(" ", "_").lower()
        df = (
            pl.read_csv(f"data/{pathname}.csv")
            .with_columns(
                color=pl.when(pl.col("color") == "light")
                .then(pl.lit("Light"))
                .otherwise(pl.lit("Dark")),
                parent=pl.when(pl.col("parent") == "lone")
                .then(pl.lit("Alone"))
                .otherwise(pl.lit("Grouped")),
            )
            .rename({"noticed": "covariate"})
            .cast(
                {
                    "scene": pl.UInt8,
                    "color": Color,
                    "parent": Parent,
                    "covariate": pl.Float64,
                }
            )
            .with_columns(model=pl.lit(name).cast(Model))
        )
        return df


    full_model = load_model("MO")
    just_ac_model = load_model("Just AC")
    return (full_model,)


@app.cell
def _(ctrl_ex_rate, main_ex_rate, mo, np):
    mo.md(
        f"""
    Exclusion Rate for Unswapped = {np.round(main_ex_rate * 100, decimals=1)}%

    Exclusion Rate for Swapped = {np.round(ctrl_ex_rate * 100, decimals=1)}%
    """
    )
    return


if __name__ == "__main__":
    app.run()
