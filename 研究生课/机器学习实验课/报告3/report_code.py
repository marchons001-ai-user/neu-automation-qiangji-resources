# -*- coding: utf-8 -*-
"""
报告3：基于汽车行驶记录的油耗预测实验。

任务目标：
1. 读取 measurements.xlsx 数据集；
2. 以 consume（L/100km）为目标变量，根据汽油类型及其他行驶/环境特征预测油耗；
3. 完成数据预处理、探索性分析、建模评价和结果可视化；
4. 输出报告所需的图表与关键结果文件。
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore")

TARGET_COL = "consume"
RANDOM_STATE = 42


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def load_data(data_path: Path) -> pd.DataFrame:
    if not data_path.exists():
        raise FileNotFoundError(f"找不到数据文件：{data_path}")
    df = pd.read_excel(data_path)
    expected_cols = {
        "distance",
        "consume",
        "speed",
        "temp_inside",
        "temp_outside",
        "specials",
        "gas_type",
        "AC",
        "rain",
        "sun",
        "refill_liters",
        "refill_gas",
    }
    missing_cols = expected_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"数据集缺少字段：{sorted(missing_cols)}")
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["has_special"] = data["specials"].notna().astype(int)
    data["has_refill"] = data["refill_liters"].notna().astype(int)
    data["temp_diff_inside_outside"] = data["temp_inside"] - data["temp_outside"]
    data["distance_per_speed"] = data["distance"] / data["speed"].replace(0, np.nan)
    data["speed_temp_interaction"] = data["speed"] * data["temp_outside"]
    data["rain_ac"] = data["rain"] * data["AC"]
    data["sun_ac"] = data["sun"] * data["AC"]
    return data


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    rmse = mean_squared_error(y_true, y_pred, squared=False)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    nrmse = rmse / (float(np.max(y_true)) - float(np.min(y_true)))
    return {"RMSE": rmse, "MAE": mae, "R2": r2, "NRMSE": nrmse}


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    categorical_features = [
        col
        for col in ["gas_type", "specials", "refill_gas"]
        if col in X.columns
    ]
    numeric_features = [col for col in X.columns if col not in categorical_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="none")),
            ("onehot", make_one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )


def get_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    names: list[str] = []
    for transformer_name, transformer, columns in preprocessor.transformers_:
        if transformer_name == "remainder" or transformer == "drop":
            continue
        if transformer_name == "cat":
            encoder = transformer.named_steps["onehot"]
            names.extend(encoder.get_feature_names_out(columns).tolist())
        else:
            names.extend(list(columns))
    return names


def save_overview(df: pd.DataFrame, out_dir: Path) -> None:
    ensure_dir(out_dir)
    df.head(10).to_csv(out_dir / "head_10.csv", index=False, encoding="utf-8-sig")
    df.dtypes.astype(str).rename("dtype").to_csv(
        out_dir / "dtypes.csv", encoding="utf-8-sig"
    )
    df.isna().sum().rename("missing_count").to_csv(
        out_dir / "missing_values.csv", encoding="utf-8-sig"
    )
    df.describe(include="all").to_csv(out_dir / "describe.csv", encoding="utf-8-sig")

    gas_summary = (
        df.groupby("gas_type")[TARGET_COL]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .sort_index()
    )
    gas_summary.to_csv(out_dir / "consume_by_gas_type.csv", encoding="utf-8-sig")

    binary_summary = (
        df[["AC", "rain", "sun", TARGET_COL]]
        .groupby(["AC", "rain", "sun"])
        .agg(["count", "mean"])
    )
    binary_summary.to_csv(out_dir / "consume_by_weather_ac.csv", encoding="utf-8-sig")


def plot_eda(df: pd.DataFrame, fig_dir: Path) -> None:
    ensure_dir(fig_dir)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    ax.hist(df[TARGET_COL], bins=24, color="#3B82F6", edgecolor="white")
    ax.set_title("Distribution of Fuel Consumption")
    ax.set_xlabel("consume (L/100km)")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(fig_dir / "target_consume_distribution.png", dpi=220)
    plt.close(fig)

    gas_stats = (
        df.groupby("gas_type")[TARGET_COL]
        .agg(["mean", "std", "count"])
        .reindex(["E10", "SP98"])
    )
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.bar(
        gas_stats.index,
        gas_stats["mean"],
        yerr=gas_stats["std"],
        capsize=5,
        color=["#F97316", "#2563EB"],
        alpha=0.88,
    )
    ax.set_title("Average Consumption by Gas Type")
    ax.set_xlabel("gas type")
    ax.set_ylabel("mean consume (L/100km)")
    for i, (idx, row) in enumerate(gas_stats.iterrows()):
        ax.text(i, row["mean"] + 0.08, f"n={int(row['count'])}", ha="center")
    fig.tight_layout()
    fig.savefig(fig_dir / "consume_by_gas_type.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for gas, color in [("E10", "#F97316"), ("SP98", "#2563EB")]:
        sub = df[df["gas_type"] == gas]
        ax.scatter(
            sub["speed"],
            sub[TARGET_COL],
            label=gas,
            alpha=0.65,
            s=32,
            color=color,
            edgecolor="none",
        )
    ax.set_title("Speed and Fuel Consumption")
    ax.set_xlabel("speed (km/h)")
    ax.set_ylabel("consume (L/100km)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "speed_vs_consume.png", dpi=220)
    plt.close(fig)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    corr = df[numeric_cols].corr()
    fig, ax = plt.subplots(figsize=(8.2, 6.2))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_title("Numeric Feature Correlation")
    fig.tight_layout()
    fig.savefig(fig_dir / "correlation_heatmap.png", dpi=220)
    plt.close(fig)


def evaluate_models(X: pd.DataFrame, y: pd.Series, out_dir: Path, fig_dir: Path) -> dict:
    ensure_dir(out_dir)
    ensure_dir(fig_dir)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )

    preprocessor = build_preprocessor(X_train)
    models = {
        "GasType_LinearRegression": Pipeline(
            steps=[
                (
                    "preprocess",
                    ColumnTransformer(
                        transformers=[
                            (
                                "cat",
                                Pipeline(
                                    steps=[
                                        (
                                            "imputer",
                                            SimpleImputer(
                                                strategy="constant",
                                                fill_value="none",
                                            ),
                                        ),
                                        ("onehot", make_one_hot_encoder()),
                                    ]
                                ),
                                ["gas_type"],
                            )
                        ]
                    ),
                ),
                ("model", LinearRegression()),
            ]
        ),
        "Full_LinearRegression": Pipeline(
            steps=[("preprocess", preprocessor), ("model", LinearRegression())]
        ),
        "Full_Ridge": Pipeline(
            steps=[
                ("preprocess", build_preprocessor(X_train)),
                ("model", Ridge(alpha=1.0, random_state=RANDOM_STATE)),
            ]
        ),
        "Full_RandomForest": Pipeline(
            steps=[
                ("preprocess", build_preprocessor(X_train)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=500,
                        max_depth=None,
                        min_samples_leaf=3,
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "Full_GradientBoosting": Pipeline(
            steps=[
                ("preprocess", build_preprocessor(X_train)),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=180,
                        learning_rate=0.04,
                        max_depth=3,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }

    cv = KFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    rows = []
    predictions = {}
    for name, model in models.items():
        scoring = {
            "neg_rmse": "neg_root_mean_squared_error",
            "neg_mae": "neg_mean_absolute_error",
            "r2": "r2",
        }
        cv_scores = cross_validate(model, X, y, cv=cv, scoring=scoring, n_jobs=-1)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        predictions[name] = y_pred
        metrics = regression_metrics(y_test, y_pred)
        rows.append(
            {
                "model": name,
                "test_RMSE": metrics["RMSE"],
                "test_MAE": metrics["MAE"],
                "test_R2": metrics["R2"],
                "test_NRMSE": metrics["NRMSE"],
                "cv_RMSE_mean": -cv_scores["test_neg_rmse"].mean(),
                "cv_RMSE_std": cv_scores["test_neg_rmse"].std(),
                "cv_MAE_mean": -cv_scores["test_neg_mae"].mean(),
                "cv_R2_mean": cv_scores["test_r2"].mean(),
            }
        )

    result_df = pd.DataFrame(rows).sort_values("test_RMSE")
    result_df.to_csv(out_dir / "model_comparison.csv", index=False, encoding="utf-8-sig")

    best_name = result_df.iloc[0]["model"]
    best_model = models[best_name]
    best_pred = predictions[best_name]
    prediction_df = pd.DataFrame({"actual": y_test, "predicted": best_pred})
    prediction_df.to_csv(
        out_dir / "best_model_predictions.csv", index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(5.2, 5.0))
    ax.scatter(y_test, best_pred, s=38, alpha=0.75, color="#2563EB", edgecolor="none")
    low = min(float(y_test.min()), float(np.min(best_pred)))
    high = max(float(y_test.max()), float(np.max(best_pred)))
    ax.plot([low, high], [low, high], color="#DC2626", lw=1.5, linestyle="--")
    ax.set_title(f"Actual vs Predicted ({best_name})")
    ax.set_xlabel("actual consume")
    ax.set_ylabel("predicted consume")
    fig.tight_layout()
    fig.savefig(fig_dir / "best_prediction_scatter.png", dpi=220)
    plt.close(fig)

    ordered = prediction_df.reset_index(drop=True).head(80)
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    ax.plot(ordered.index, ordered["actual"], label="actual", color="#111827", lw=1.6)
    ax.plot(
        ordered.index,
        ordered["predicted"],
        label="predicted",
        color="#2563EB",
        lw=1.4,
    )
    ax.set_title(f"First 80 Test Samples ({best_name})")
    ax.set_xlabel("test sample index")
    ax.set_ylabel("consume (L/100km)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "best_prediction_curve.png", dpi=220)
    plt.close(fig)

    if "RandomForest" in best_name:
        fitted_preprocessor = best_model.named_steps["preprocess"]
        feature_names = get_feature_names(fitted_preprocessor)
        importances = best_model.named_steps["model"].feature_importances_
        importance_df = (
            pd.DataFrame({"feature": feature_names, "importance": importances})
            .sort_values("importance", ascending=False)
            .head(20)
        )
    else:
        rf_model = models["Full_RandomForest"]
        rf_model.fit(X_train, y_train)
        fitted_preprocessor = rf_model.named_steps["preprocess"]
        feature_names = get_feature_names(fitted_preprocessor)
        importances = rf_model.named_steps["model"].feature_importances_
        importance_df = (
            pd.DataFrame({"feature": feature_names, "importance": importances})
            .sort_values("importance", ascending=False)
            .head(20)
        )
    importance_df.to_csv(
        out_dir / "feature_importance_top20.csv", index=False, encoding="utf-8-sig"
    )

    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    plot_df = importance_df.sort_values("importance")
    ax.barh(plot_df["feature"], plot_df["importance"], color="#0F766E")
    ax.set_title("Top 20 Feature Importances")
    ax.set_xlabel("importance")
    fig.tight_layout()
    fig.savefig(fig_dir / "feature_importance_top20.png", dpi=220)
    plt.close(fig)

    summary = {
        "best_model": best_name,
        "best_metrics": result_df.iloc[0].to_dict(),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="measurements.xlsx")
    parser.add_argument("--output", default="results_fuel_consumption")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_path = Path(args.data)
    if not data_path.is_absolute():
        data_path = base_dir / data_path

    output_dir = ensure_dir(base_dir / args.output)
    fig_dir = ensure_dir(base_dir / "figures")
    overview_dir = ensure_dir(output_dir / "01_data_overview")
    model_dir = ensure_dir(output_dir / "02_modeling")

    df = load_data(data_path)
    df_engineered = add_features(df)

    save_overview(df, overview_dir)
    plot_eda(df, fig_dir)

    y = df_engineered[TARGET_COL]
    X = df_engineered.drop(columns=[TARGET_COL])
    summary = evaluate_models(X, y, model_dir, fig_dir)

    print("数据规模：", df.shape)
    print("缺失值数量：")
    print(df.isna().sum())
    print("\n按汽油类型统计油耗：")
    print(
        df.groupby("gas_type")[TARGET_COL]
        .agg(["count", "mean", "median", "std", "min", "max"])
        .round(4)
    )
    print("\n最佳模型：", summary["best_model"])
    print("最佳模型测试集指标：")
    for key, value in summary["best_metrics"].items():
        print(f"{key}: {value}")
    print(f"\n结果已保存到：{output_dir}")


if __name__ == "__main__":
    main()
