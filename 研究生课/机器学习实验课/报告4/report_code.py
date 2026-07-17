# -*- coding: utf-8 -*-
"""
Report 4: Student performance level classification with xAPI-Edu-Data.

The script reads kalboard360_xAPI_Edu_Data.csv, performs exploratory analysis,
builds several classification models, and saves the tables/figures used by the
LaTeX report.
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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC


warnings.filterwarnings("ignore")

TARGET_COL = "Class"
CLASS_ORDER = ["L", "M", "H"]
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
        raise FileNotFoundError(f"Cannot find data file: {data_path}")
    df = pd.read_csv(data_path)
    expected_cols = {
        "gender",
        "NationalITy",
        "PlaceofBirth",
        "StageID",
        "GradeID",
        "SectionID",
        "Topic",
        "Semester",
        "Relation",
        "raisedhands",
        "VisITedResources",
        "AnnouncementsView",
        "Discussion",
        "ParentAnsweringSurvey",
        "ParentschoolSatisfaction",
        "StudentAbsenceDays",
        "Class",
    }
    missing_cols = expected_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_cols)}")
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    activity_cols = [
        "raisedhands",
        "VisITedResources",
        "AnnouncementsView",
        "Discussion",
    ]
    data["activity_total"] = data[activity_cols].sum(axis=1)
    data["activity_mean"] = data[activity_cols].mean(axis=1)
    data["activity_std"] = data[activity_cols].std(axis=1)
    data["resource_per_raise"] = data["VisITedResources"] / (
        data["raisedhands"] + 1.0
    )
    data["discussion_per_resource"] = data["Discussion"] / (
        data["VisITedResources"] + 1.0
    )
    data["announcement_share"] = data["AnnouncementsView"] / (
        data["activity_total"] + 1.0
    )

    data["parent_answer_yes"] = (
        data["ParentAnsweringSurvey"].str.lower().eq("yes").astype(int)
    )
    data["school_satisfaction_good"] = (
        data["ParentschoolSatisfaction"].str.lower().eq("good").astype(int)
    )
    data["absence_above_7"] = (
        data["StudentAbsenceDays"].str.lower().eq("above-7").astype(int)
    )
    data["relation_mum"] = data["Relation"].str.lower().eq("mum").astype(int)
    data["is_female"] = data["gender"].str.upper().eq("F").astype(int)
    data["born_in_kuwait"] = data["PlaceofBirth"].str.lower().eq("kuwait").astype(int)
    data["nationality_kw"] = data["NationalITy"].str.upper().eq("KW").astype(int)
    data["grade_num"] = (
        data["GradeID"].astype(str).str.extract(r"G-(\d+)")[0].astype(float)
    )
    data["is_lower_level"] = data["StageID"].str.lower().eq("lowerlevel").astype(int)

    data["high_activity"] = (
        data["activity_total"] >= data["activity_total"].median()
    ).astype(int)
    data["absence_parent_risk"] = (
        data["absence_above_7"] * (1 - data["parent_answer_yes"])
    )
    data["support_good_no_absence"] = (
        data["school_satisfaction_good"] * (1 - data["absence_above_7"])
    )
    return data


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    categorical_features = X.select_dtypes(include=["object"]).columns.tolist()
    numeric_features = [col for col in X.columns if col not in categorical_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
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


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "Accuracy": accuracy_score(y_true, y_pred),
        "Macro_Precision": precision_score(
            y_true, y_pred, labels=CLASS_ORDER, average="macro", zero_division=0
        ),
        "Macro_Recall": recall_score(
            y_true, y_pred, labels=CLASS_ORDER, average="macro", zero_division=0
        ),
        "Macro_F1": f1_score(
            y_true, y_pred, labels=CLASS_ORDER, average="macro", zero_division=0
        ),
        "Balanced_Accuracy": balanced_accuracy_score(y_true, y_pred),
    }


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

    class_counts = df[TARGET_COL].value_counts().reindex(CLASS_ORDER)
    class_counts.rename("count").to_csv(
        out_dir / "class_distribution.csv", encoding="utf-8-sig"
    )

    numeric_cols = [
        "raisedhands",
        "VisITedResources",
        "AnnouncementsView",
        "Discussion",
    ]
    activity_by_class = df.groupby(TARGET_COL)[numeric_cols].agg(["mean", "median"])
    activity_by_class = activity_by_class.reindex(CLASS_ORDER)
    activity_by_class.to_csv(out_dir / "activity_by_class.csv", encoding="utf-8-sig")

    categorical_cols = [
        "gender",
        "StageID",
        "Semester",
        "Relation",
        "ParentAnsweringSurvey",
        "ParentschoolSatisfaction",
        "StudentAbsenceDays",
    ]
    with (out_dir / "category_crosstab.txt").open("w", encoding="utf-8") as f:
        for col in categorical_cols:
            f.write(f"\n[{col}]\n")
            f.write(pd.crosstab(df[col], df[TARGET_COL]).to_string())
            f.write("\n")


def plot_eda(df: pd.DataFrame, fig_dir: Path) -> None:
    ensure_dir(fig_dir)
    plt.style.use("seaborn-v0_8-whitegrid")

    class_counts = df[TARGET_COL].value_counts().reindex(CLASS_ORDER)
    fig, ax = plt.subplots(figsize=(5.8, 4.0))
    ax.bar(class_counts.index, class_counts.values, color=["#EF4444", "#3B82F6", "#10B981"])
    ax.set_title("Class Distribution")
    ax.set_xlabel("performance class")
    ax.set_ylabel("count")
    for i, value in enumerate(class_counts.values):
        ax.text(i, value + 3, str(int(value)), ha="center")
    fig.tight_layout()
    fig.savefig(fig_dir / "class_distribution.png", dpi=220)
    plt.close(fig)

    numeric_cols = [
        "raisedhands",
        "VisITedResources",
        "AnnouncementsView",
        "Discussion",
    ]
    means = df.groupby(TARGET_COL)[numeric_cols].mean().reindex(CLASS_ORDER)
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    x = np.arange(len(numeric_cols))
    width = 0.24
    colors = ["#EF4444", "#3B82F6", "#10B981"]
    for offset, class_name, color in zip([-width, 0, width], CLASS_ORDER, colors):
        ax.bar(x + offset, means.loc[class_name].values, width, label=class_name, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(numeric_cols, rotation=15, ha="right")
    ax.set_title("Learning Activity Mean by Class")
    ax.set_ylabel("mean value")
    ax.legend(title="Class")
    fig.tight_layout()
    fig.savefig(fig_dir / "activity_mean_by_class.png", dpi=220)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(8.6, 6.2))
    axes = axes.ravel()
    for ax, col in zip(axes, numeric_cols):
        data = [df.loc[df[TARGET_COL] == cls, col] for cls in CLASS_ORDER]
        ax.boxplot(data, labels=CLASS_ORDER, patch_artist=True)
        ax.set_title(col)
        ax.set_xlabel("Class")
        ax.set_ylabel("value")
    fig.tight_layout()
    fig.savefig(fig_dir / "activity_boxplots_by_class.png", dpi=220)
    plt.close(fig)

    numeric_all = df.select_dtypes(include=[np.number]).columns.tolist()
    corr_df = df[numeric_all + [TARGET_COL]].copy()
    corr_df["class_code"] = corr_df[TARGET_COL].map({"L": 0, "M": 1, "H": 2})
    corr = corr_df[numeric_all + ["class_code"]].corr()
    corr.to_csv(fig_dir.parent / "results_student_performance" / "01_data_overview" / "numeric_correlation.csv", encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(8.2, 6.4))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    ax.set_title("Numeric Feature Correlation")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(fig_dir / "correlation_heatmap.png", dpi=220)
    plt.close(fig)


def build_models(preprocessor: ColumnTransformer) -> dict[str, Pipeline]:
    return {
        "Majority_Baseline": Pipeline(
            steps=[
                ("preprocess", preprocessor),
                ("model", DummyClassifier(strategy="most_frequent")),
            ]
        ),
        "LogisticRegression": Pipeline(
            steps=[
                ("preprocess", preprocessor),
                (
                    "model",
                    LogisticRegression(
                        C=1.8,
                        max_iter=3000,
                        class_weight="balanced",
                        multi_class="auto",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "SVM_RBF": Pipeline(
            steps=[
                ("preprocess", preprocessor),
                (
                    "model",
                    SVC(
                        C=6.0,
                        gamma="scale",
                        kernel="rbf",
                        class_weight="balanced",
                        probability=True,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "RandomForest": Pipeline(
            steps=[
                ("preprocess", preprocessor),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=500,
                        max_depth=None,
                        min_samples_leaf=2,
                        class_weight="balanced_subsample",
                        random_state=RANDOM_STATE,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
        "GradientBoosting": Pipeline(
            steps=[
                ("preprocess", preprocessor),
                (
                    "model",
                    GradientBoostingClassifier(
                        n_estimators=160,
                        learning_rate=0.05,
                        max_depth=3,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def evaluate_models(
    models: dict[str, Pipeline],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    out_dir: Path,
    fig_dir: Path,
) -> tuple[str, Pipeline, pd.DataFrame, pd.DataFrame]:
    ensure_dir(out_dir)
    ensure_dir(fig_dir)
    rows: list[dict[str, float | str]] = []
    cv_rows: list[dict[str, float | str]] = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "accuracy": "accuracy",
        "macro_f1": "f1_macro",
        "balanced_accuracy": "balanced_accuracy",
    }

    best_name = ""
    best_model: Pipeline | None = None
    best_macro_f1 = -np.inf

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = classification_metrics(y_test, y_pred)
        rows.append({"Model": name, **metrics})

        cv_result = cross_validate(
            model,
            pd.concat([X_train, X_test], axis=0),
            pd.concat([y_train, y_test], axis=0),
            cv=cv,
            scoring=scoring,
            n_jobs=None,
        )
        cv_rows.append(
            {
                "Model": name,
                "CV_Accuracy_Mean": float(cv_result["test_accuracy"].mean()),
                "CV_Macro_F1_Mean": float(cv_result["test_macro_f1"].mean()),
                "CV_Balanced_Accuracy_Mean": float(
                    cv_result["test_balanced_accuracy"].mean()
                ),
            }
        )

        report = classification_report(
            y_test,
            y_pred,
            labels=CLASS_ORDER,
            target_names=CLASS_ORDER,
            digits=4,
            zero_division=0,
        )
        (out_dir / f"{name}_classification_report.txt").write_text(
            report, encoding="utf-8"
        )

        if metrics["Macro_F1"] > best_macro_f1:
            best_macro_f1 = metrics["Macro_F1"]
            best_name = name
            best_model = model

    results = pd.DataFrame(rows).sort_values(
        ["Macro_F1", "Accuracy"], ascending=False
    )
    cv_results = pd.DataFrame(cv_rows).sort_values(
        ["CV_Macro_F1_Mean", "CV_Accuracy_Mean"], ascending=False
    )
    results.to_csv(out_dir / "model_comparison.csv", index=False, encoding="utf-8-sig")
    cv_results.to_csv(
        out_dir / "cross_validation_results.csv", index=False, encoding="utf-8-sig"
    )

    assert best_model is not None
    y_best = best_model.predict(X_test)
    pd.DataFrame({"y_true": y_test.values, "y_pred": y_best}).to_csv(
        out_dir / "best_model_predictions.csv", index=False, encoding="utf-8-sig"
    )

    cm = confusion_matrix(y_test, y_best, labels=CLASS_ORDER)
    cm_df = pd.DataFrame(cm, index=CLASS_ORDER, columns=CLASS_ORDER)
    cm_df.to_csv(out_dir / "best_confusion_matrix.csv", encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=CLASS_ORDER).plot(
        ax=ax, cmap="Blues", colorbar=False, values_format="d"
    )
    ax.set_title(f"Confusion Matrix: {best_name}")
    fig.tight_layout()
    fig.savefig(fig_dir / "best_confusion_matrix.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    plot_results = results.sort_values("Macro_F1", ascending=True)
    ax.barh(plot_results["Model"], plot_results["Macro_F1"], color="#2563EB")
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Macro-F1")
    ax.set_title("Model Comparison")
    for i, value in enumerate(plot_results["Macro_F1"]):
        ax.text(value + 0.01, i, f"{value:.3f}", va="center")
    fig.tight_layout()
    fig.savefig(fig_dir / "model_comparison_macro_f1.png", dpi=220)
    plt.close(fig)

    return best_name, best_model, results, cv_results


def save_feature_importance(
    best_model: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    out_dir: Path,
    fig_dir: Path,
) -> pd.DataFrame:
    preprocess = best_model.named_steps["preprocess"]
    model = best_model.named_steps["model"]
    feature_names = get_feature_names(preprocess)

    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
        source = "model_importance"
    else:
        transformed = preprocess.transform(X_test)
        perm = permutation_importance(
            model,
            transformed,
            y_test,
            scoring="f1_macro",
            n_repeats=20,
            random_state=RANDOM_STATE,
        )
        values = perm.importances_mean
        source = "permutation_importance"

    importance = (
        pd.DataFrame({"feature": feature_names, "importance": values, "source": source})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    importance.to_csv(out_dir / "feature_importance_top20.csv", index=False, encoding="utf-8-sig")

    top = importance.head(20).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.2, 6.0))
    ax.barh(top["feature"], top["importance"], color="#10B981")
    ax.set_title("Top 20 Feature Importance")
    ax.set_xlabel("importance")
    fig.tight_layout()
    fig.savefig(fig_dir / "feature_importance_top20.png", dpi=220)
    plt.close(fig)
    return importance


def run(data_path: Path, output_root: Path) -> None:
    result_dir = ensure_dir(output_root / "results_student_performance")
    overview_dir = ensure_dir(result_dir / "01_data_overview")
    model_dir = ensure_dir(result_dir / "02_modeling")
    fig_dir = ensure_dir(output_root / "figures")

    df = load_data(data_path)
    engineered = add_features(df)
    save_overview(df, overview_dir)
    plot_eda(df, fig_dir)

    X = engineered.drop(columns=[TARGET_COL])
    y = engineered[TARGET_COL]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    preprocessor = build_preprocessor(X)
    models = build_models(preprocessor)
    best_name, best_model, results, cv_results = evaluate_models(
        models, X_train, X_test, y_train, y_test, model_dir, fig_dir
    )
    importance = save_feature_importance(best_model, X_test, y_test, model_dir, fig_dir)

    summary = {
        "data_shape": list(df.shape),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "class_distribution": df[TARGET_COL].value_counts().reindex(CLASS_ORDER).to_dict(),
        "best_model": best_name,
        "best_test_metrics": results.loc[results["Model"] == best_name].iloc[0].to_dict(),
        "best_cv_metrics": cv_results.loc[cv_results["Model"] == best_name].iloc[0].to_dict(),
        "top_features": importance.head(10)[["feature", "importance"]].to_dict("records"),
    }
    (model_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Data shape:", df.shape)
    print("Class distribution:")
    print(df[TARGET_COL].value_counts().reindex(CLASS_ORDER).to_string())
    print("\nModel comparison:")
    print(results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nCross validation:")
    print(cv_results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nBest model:", best_name)
    print("Top features:")
    print(importance.head(10).to_string(index=False, float_format=lambda x: f"{x:.4f}"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("kalboard360_xAPI_Edu_Data.csv"),
        help="Path to xAPI Edu Data CSV file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("."),
        help="Directory for generated report tables and figures.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.data, args.output)
