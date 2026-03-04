import marimo

__generated_with = "0.19.6"
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
    from scipy.stats import linregress, ttest_ind, chi2_contingency, fisher_exact
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
        partial,
        pl,
        ttest_ind,
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
    Model = pl.Enum(["Human", "mo", "ja", "ta", "fr"])
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
            .then(pl.lit("grouped"))
            .otherwise(pl.lit("lone"))
            .cast(Parent)
        ).select(pl.all().exclude("grouped"))
        noticed_df = trial_design.join(
            noticed_df, on=["scene", "parent"], how="left"
        ).fill_null(0.0)

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
    main_noticed, main_ex_rate, main_perf = load_behavior(f"data/{exp}-{version}")
    main_noticed = main_noticed.with_columns(color=pl.lit("light").cast(Color))
    main_perf = main_perf.with_columns(color=pl.lit("light").cast(Color))
    ctrl_noticed, ctrl_ex_rate, ctrl_perf = load_behavior(
        f"data/{exp}-{version}-swapped"
    )
    ctrl_noticed = ctrl_noticed.with_columns(color=pl.lit("dark").cast(Color))
    ctrl_perf = ctrl_perf.with_columns(color=pl.lit("dark").cast(Color))

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
    ## Chi-Squared
    """)
    return


@app.cell
def _(chi2_contingency, fisher_exact, human_notice_summary, pl):
    ChiSquaredResult = pl.Struct({"statistic": pl.Float64, "p_value": pl.Float64})

    _grouped = human_notice_summary.row(0)[2:4]
    _alone = human_notice_summary.row(1)[2:4]
    _table = [_alone, _grouped]
    chi_squared_human_light = chi2_contingency(_table)
    print(fisher_exact(_table))

    _grouped = human_notice_summary.row(2)[2:4]
    _alone = human_notice_summary.row(3)[2:4]
    _table = [_alone, _grouped]
    print(fisher_exact(_table))
    # chi_squared_human_dark = chi2_contingency([_alone, _grouped])
    return (chi_squared_human_light,)


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


@app.cell
def _(all_noticed, mo, pl):
    mo.ui.table(
        all_noticed.group_by("scene", "color", "parent")
        .agg(
            yes=pl.col("noticed").sum(),
            no=pl.col("noticed").not_().sum(),
            pct=pl.col("noticed").mean().round_sig_figs(digits=2),
        )
        .sort("color", "parent")
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


    all_models = load_models("data/study2/aggregate.csv")
    return (all_models,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Chi-Squared
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


@app.cell
def _(chi2_contingency, fisher_exact, model_summary):
    _grouped = model_summary.row(0)[3:5]
    _alone = model_summary.row(1)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    chi_squared_mo_unswapped = chi2_contingency(_table)
    print(fisher_exact(_table))

    _grouped = model_summary.row(2)[3:5]
    _alone = model_summary.row(3)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    print(fisher_exact(_table))
    return (chi_squared_mo_unswapped,)


@app.cell
def _(fisher_exact, model_summary):
    _grouped = model_summary.row(4)[3:5]
    _alone = model_summary.row(5)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    print(fisher_exact(_table))

    _grouped = model_summary.row(6)[3:5]
    _alone = model_summary.row(7)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    print(fisher_exact(_table))
    return


@app.cell
def _(fisher_exact, model_summary):
    _grouped = model_summary.row(8)[3:5]
    _alone = model_summary.row(9)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    print(fisher_exact(_table))

    _grouped = model_summary.row(10)[3:5]
    _alone = model_summary.row(11)[3:5]
    _table = [_alone, _grouped]
    print(_table)
    print(fisher_exact(_table))
    return


@app.cell
def _(chi_squared_mo_unswapped, mo):
    mo.ui.table(
        data=[
            {
                "model": "MO",
                "color": "Light",
                "Chi-Squared": chi_squared_mo_unswapped.statistic,
                "p-value": chi_squared_mo_unswapped.pvalue,
            }
        ]
    )
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


@app.cell
def _(alt, mo, notice_by_design):
    mo.ui.altair_chart(
        alt.Chart(notice_by_design)
        .mark_bar()
        .transform_calculate(model_color="[datum.model, datum.color]")
        .encode(alt.X("parent:O"), alt.Y("pct:Q").title("Noticed (%)"))
        .properties(width=180, height=180)
        .facet("model_color:N")
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Modelling trial-level noticing
    """)
    return


@app.cell
def _(linregress, pl):
    CorResult = pl.Struct({"r": pl.Float64, "p_value": pl.Float64})


    def fit_model(data: pl.Struct):
        x = data.struct.field("covariate")
        y = data.struct.field("noticed")
        try:
            result = linregress(x, y)
            return {
                "r^2": result.rvalue**2,
                "p_value": result.pvalue,
            }
        except:
            return {"r^2": float("nan"), "p_value": float("nan")}
    return CorResult, fit_model


@app.cell
def _(CorResult, Model, all_models, ctrl_noticed, fit_model, main_noticed, pl):
    def fit_models_to_human(
        unswapped_df: pl.DataFrame, swapped_df: pl.DataFrame, models
    ):
        results = []

        for name, model in models:
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
            fit = fit.with_columns(model=pl.lit(name[0]))
            results.append(fit)

        results = (
            pl.concat(results, how="vertical")
            .select(["model", "r^2", "p_value"])
            .with_columns(model=pl.col("model").cast(Model))
            .sort("model")
        )
        return results


    models_trial_lvl = all_models.group_by("model", "color", "parent", "scene").agg(
        covariate=pl.col("noticed").mean()
    )

    models_grouped = models_trial_lvl.group_by("model")
    model_fits = fit_models_to_human(main_noticed, ctrl_noticed, models_grouped)
    model_names = model_fits["model"].to_numpy()
    print(model_fits)
    return fit_models_to_human, model_names, models_grouped, models_trial_lvl


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
    return (ordinary_by_subj,)


@app.cell
def _(
    Callable,
    ctrl_noticed,
    fit_models_to_human,
    main_noticed,
    model_names,
    models_grouped,
    np,
    ordinary_by_subj,
    pl,
):
    def bootstrap_model_fits(
        steps: int = 10000,
        rng: Callable = ordinary_by_subj,
    ):
        n = models_grouped.len().height
        samples = np.zeros((steps, n))
        for i in range(steps):
            fit_df = fit_models_to_human(
                rng(main_noticed), rng(ctrl_noticed), models_grouped
            )
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
    fit_samples = bootstrap_model_fits(2000)
    return (fit_samples,)


@app.cell
def _(fit_samples, np):
    mo_cis = np.percentile(fit_samples.select("mo").to_numpy(), [2.5, 97.5])
    ja_cis = np.percentile(fit_samples.select("ja").to_numpy(), [2.5, 97.5])
    fr_cis = np.percentile(fit_samples.select("fr").to_numpy(), [2.5, 97.5])
    ta_cis = np.percentile(fit_samples.select("ta").to_numpy(), [2.5, 97.5])
    return fr_cis, ja_cis, mo_cis, ta_cis


@app.cell(hide_code=True)
def _(fr_cis, ja_cis, mo, mo_cis, ta_cis):
    mo.md(rf"""
    MO 95% CIs = {mo_cis}

    JA 95% CIs = {ja_cis}

    TA 95% CIs = {ta_cis}

    FR 95% CIs = {fr_cis}
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
    return (
        mo_vs_fr_CIs,
        mo_vs_fr_pval,
        mo_vs_ja_CIs,
        mo_vs_ja_diff,
        mo_vs_ja_pval,
        mo_vs_ta_CIs,
        mo_vs_ta_pval,
    )


@app.cell(hide_code=True)
def _(
    mo,
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
    """)
    return


@app.cell
def _(fit_samples, mo):
    mo.ui.table(fit_samples)
    return


@app.cell
def _(Model, alt, fit_samples, model_names):
    _df = fit_samples.unpivot(
        model_names, index="sample", variable_name="model", value_name="r^2"
    ).cast({"model": Model})

    alt.Chart(_df).mark_bar().encode(
        alt.X("r^2:Q").bin(step=0.025).title("Explained Variance"),
        alt.Row("model:N"),
        y="count()",
    )
    return


@app.cell
def _(alt, mo_vs_ja_diff):
    alt.Chart(mo_vs_ja_diff).mark_bar().encode(
        alt.X("diff:Q")
        .bin(maxbins=30)
        .title("MO - Just Attention (Explained Variance)"),
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
        alt.X("samples:Q").bin(step=0.025).title("Difference: Unswapped - Swapped"),
        y="count()",
    ).properties(title="Main Exp - Ctrl Exp")
    return


@app.cell
def _(cis, mo, pval):
    mo.md(f"""
    p-value = {pval}

    95 % CIs = {cis}
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
        # alt.Text("scene:N"),
    )

    _points = _base.mark_point(size=200)
    _labels = _base.mark_text()
    _chart = (
        _points
        + _points.transform_regression("covariate", "noticed", method="linear")
        .mark_line()
        .transform_fold(["reg-line"], as_=["Regression", "y"])
        .encode(alt.Color("Regression:N"), alt.Shape("Regression:N"))
        + _labels
    )
    mo.ui.altair_chart(_chart)
    return (model_vs_noticing,)


@app.cell
def _(mo, model_vs_noticing):
    mo.ui.table(model_vs_noticing)
    return


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


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Counting performance
    """)
    return


@app.cell
def _(all_models, pl):
    print(
        all_models.group_by("model")
        .agg(
            pl.col("count_error").mean().alias("error_mu"),
            pl.col("count_error").std().alias("error_std"),
            pl.col("time").mean().alias("time_mu"),
            pl.col("time").std().alias("time_std"),
        )
        .sort("model")
    )
    return


@app.cell
def _(all_models, mo):
    mo.ui.table(all_models)
    return


@app.cell
def _(all_models, pl):
    model_perf_summary = (
        all_models.group_by("model", "scene", "color", "parent")
        .agg(
            pl.col("expected_count").mean(),
            pl.col("count_error").mean().alias("error_mu"),
            pl.col("count_error").std().alias("error_sd"),
        )
        .sort("model")
    )
    return (model_perf_summary,)


@app.cell
def _(gt_counts):
    gt_counts
    return


@app.cell
def _(mo, model_perf_summary):
    mo.ui.table(model_perf_summary)
    return


@app.cell
def _(all_models, pl, ttest_ind):
    _perf_mo = all_models.filter(pl.col("model") == "mo")
    _perf_ac = all_models.filter(pl.col("model") == "ja")
    print(ttest_ind(_perf_mo["count_error"], _perf_ac["count_error"]))
    print(ttest_ind(_perf_mo["time"], _perf_ac["time"]))
    return


@app.cell
def _(all_models, pl, ttest_ind):
    _perf_mo = all_models.filter(pl.col("model") == "mo")
    _perf_fr = all_models.filter(pl.col("model") == "fr")
    perf_mo_vs_fr = ttest_ind(_perf_mo["count_error"], _perf_fr["count_error"])
    print(perf_mo_vs_fr)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # MISC
    """)
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
def _(count_schema, exp, gt_counts, pl, version):
    count_df_raw = (
        pl.read_csv(f"data/{exp}-{version}" + "_counts.csv", schema=count_schema)
        .rename({"count": "measured"})
        .select(["uid", "scene", "measured"])
        .join(gt_counts, on="scene", how="left")
        .with_columns(
            error=(pl.col("count") - pl.col("measured")) / pl.col("count")
        )
        .group_by("uid")
        .agg(pl.col("error").mean())
    )
    return (count_df_raw,)


@app.cell
def _(count_df_raw, mo):
    mo.ui.table(count_df_raw)
    return


@app.cell
def _(count_df_raw):
    count_df_raw["error"].abs().mean()
    return


@app.cell
def _(count_schema, exp, gt_counts, mo, pl, version):
    mo.ui.table(
        pl.read_csv(f"data/{exp}-{version}" + "_counts.csv", schema=count_schema)
        .rename({"count": "measured"})
        .select(["uid", "scene", "measured"])
        .join(gt_counts, on="scene", how="left")
        .with_columns(
            error=(pl.col("count") - pl.col("measured")) / pl.col("count")
        )
        .group_by("scene")
        .agg(
            pl.col("count").mean(),
            pl.col("measured").mean(),
            pl.col("error").mean(),
        )
    )
    return


@app.cell
def _(alt, count_schema, exp, gt_counts, mo, pl, version):
    _count = (
        pl.read_csv(f"data/{exp}-{version}" + "_counts.csv", schema=count_schema)
        .rename({"count": "measured"})
        .select(["uid", "scene", "measured"])
        .join(gt_counts, on="scene", how="left")
    )
    mo.ui.altair_chart(
        alt.Chart(_count)
        .mark_bar()
        .encode(
            alt.X("measured:Q")
            .bin(maxbins=30)
            .scale(domain=(1, 7))
            .title("Counts"),
            y="count()",
            row="scene:O",
        )
        .properties(width=300, height=150)
    )
    return


@app.cell
def _(PARAMS, count_df_raw, pl):
    count_df_raw.with_columns(error=pl.col("error").abs()).filter(
        pl.col("error") < PARAMS.value["perf_thresh"]
    ).describe()
    return


@app.cell
def _(all_perf, alt):
    (
        alt.Chart(all_perf)
        .mark_bar()
        .encode(
            alt.X("error:Q").bin(maxbins=50).title("Subject average performance"),
            y="count()",
        )
        .properties(title="Subject Performance")
    )
    return


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
def _(Callable, notice_metric, partial, pl):
    def difference_metric(metric: Callable, a: pl.DataFrame, b: pl.DataFrame):
        return metric(a) - metric(b)


    diff_notice_metric = partial(difference_metric, notice_metric)
    diff_notice_metric.__doc__ = "The difference in noticing differences"
    return (diff_notice_metric,)


@app.cell
def _(Callable, np, pl):
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
    return (bootstrap_noticing_differences,)


if __name__ == "__main__":
    app.run()
