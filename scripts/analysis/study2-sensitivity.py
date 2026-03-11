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
    return json, linregress, np, pl


@app.cell
def _(pl):
    # Polars dataseries types
    Parent = pl.Enum(["grouped", "lone"])
    Color = pl.Enum(["light", "dark"])
    Param = pl.Enum(["w", "inv_t", "m_mho", "a_mho"])
    return Color, Param, Parent


@app.cell
def _(json, np, pl):
    exp = "target-ensemble"
    version = "2025-06-09_W96KtK-v2-preregistered"

    col_count_schema = {"scene": pl.UInt8, "count": pl.Int64}
    # repair version name for manifest; is the same for main and swapped experiments
    base_version = (
        version.replace("-swapped", "")
        .replace("-batch2", "")
        .replace("-all", "")
        .replace("-replication", "")
        .replace("-preregistered", "")
    )
    with open(f"./data/{exp}-{base_version}-manifest.json", "r") as file:
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
    return


@app.cell
def _(Color, Parent, pl):
    human_noticing = pl.read_csv(
        "./data/study2-human_noticing.csv",
        schema={
            "scene": pl.UInt8,
            "parent": Parent,
            "uid": pl.Float64,
            "noticed": pl.Boolean,
            "description": pl.String,
            "rt": pl.Float64,
            "order": pl.Float64,
            "color": Color,
        },
    )
    human_trial_level = human_noticing.group_by("color", "parent", "scene").agg(
        pl.col("noticed").mean()
    )
    return (human_trial_level,)


@app.cell
def _(Color, Param, Parent, gt_counts, pl):
    def load_model(path: str):
        df = (
            pl.read_csv(
                path,
                schema={
                    "param": Param,
                    "param_val": pl.Float64,
                    "scene": pl.UInt8,
                    "color": Color,
                    "parent": Parent,
                    "chain": pl.Int64,
                    "ndetected": pl.Int64,
                    "expected_count": pl.Float64,
                    "count_error": pl.Float64,
                    "time": pl.Float64,
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


    model_runs = load_model("data/sensitivity/aggregate.csv")

    model_trial_level = model_runs.group_by(
        "param", "param_val", "color", "parent", "scene"
    ).agg(covariate=pl.col("noticed").mean())
    return (model_trial_level,)


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

    return CorResult, fit_model


@app.cell
def _(human_trial_level, model_trial_level, pl):
    full_df = human_trial_level.join(
        model_trial_level, on=["scene", "parent", "color"], how="left"
    ).with_columns(pl.col("noticed").fill_null(strategy="zero"))
    return (full_df,)


@app.cell
def _(full_df, mo):
    mo.ui.table(full_df)
    return


@app.cell
def _(CorResult, fit_model, full_df, pl):
    fits = (
        full_df.group_by("param", "param_val")
        .agg(
            regression=pl.struct("covariate", "noticed").map_batches(
                fit_model,
                return_dtype=CorResult,
                returns_scalar=True,
            )
        )
        .unnest("regression")
        .sort("param", "param_val")
    )
    return (fits,)


@app.cell
def _(fits, mo):
    mo.ui.table(fits)
    return


@app.cell
def _(
    CorResult,
    Model,
    all_models,
    ctrl_noticed,
    fit_model,
    main_noticed,
    pl,
    swapped_df,
    unswapped_df,
):
    def fit_models_to_human(human: pl.DataFrame, model: pl.DataFrame):
        results = []

        for name, val in model.group_by("param", ""):
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
                    fit_model,
                    return_dtype=CorResult,
                    returns_scalar=True,
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
    return


if __name__ == "__main__":
    app.run()
