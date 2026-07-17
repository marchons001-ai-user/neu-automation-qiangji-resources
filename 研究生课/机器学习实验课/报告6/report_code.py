from __future__ import annotations

import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    AdaBoostClassifier,
    BaggingClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.impute import SimpleImputer
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
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier


warnings.filterwarnings("ignore", category=FutureWarning)

RANDOM_STATE = 42
TARGET = "Loan_Status"
ID_COLUMN = "Loan_ID"


def configure_plot_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 10,
        }
    )


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    expected = {
        "Loan_ID",
        "Gender",
        "Married",
        "Dependents",
        "Education",
        "Self_Employed",
        "ApplicantIncome",
        "CoapplicantIncome",
        "LoanAmount",
        "Loan_Amount_Term",
        "Credit_History",
        "Property_Area",
        "Loan_Status",
    }
    missing_columns = expected.difference(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
    return df


def engineer_features(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.drop(columns=[ID_COLUMN]).copy()

    dependents_numeric = (
        df["Dependents"].replace({"3+": "3"}).pipe(pd.to_numeric, errors="coerce")
    )
    total_income = df["ApplicantIncome"] + df["CoapplicantIncome"]
    loan_amount = df["LoanAmount"]
    loan_term = df["Loan_Amount_Term"]

    df["Dependents_Numeric"] = dependents_numeric
    df["TotalIncome"] = total_income
    df["LogTotalIncome"] = np.log1p(total_income)
    df["LogLoanAmount"] = np.log1p(loan_amount)
    df["LoanIncomeRatio"] = loan_amount / total_income.replace(0, np.nan)
    df["InstallmentProxy"] = loan_amount / loan_term.replace(0, np.nan)
    df["IncomePerDependent"] = total_income / (dependents_numeric.fillna(0) + 1)
    df["HasCoapplicant"] = np.where(df["CoapplicantIncome"] > 0, "Yes", "No")
    df["CreditHistoryMissing"] = np.where(df["Credit_History"].isna(), "Yes", "No")
    return df


def make_preprocessor(X: pd.DataFrame) -> tuple[ColumnTransformer, list[str], list[str]]:
    numeric_columns = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_columns = [column for column in X.columns if column not in numeric_columns]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_columns),
            ("cat", categorical_pipeline, categorical_columns),
        ],
        remainder="drop",
    )
    return preprocessor, numeric_columns, categorical_columns


def build_models(preprocessor: ColumnTransformer) -> dict[str, Pipeline]:
    shallow_tree = DecisionTreeClassifier(
        max_depth=3,
        min_samples_leaf=8,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    voting_estimators = [
        (
            "lr",
            LogisticRegression(
                C=0.8,
                class_weight="balanced",
                max_iter=3000,
                random_state=RANDOM_STATE,
            ),
        ),
        (
            "rf",
            RandomForestClassifier(
                n_estimators=350,
                min_samples_leaf=2,
                max_features="sqrt",
                class_weight="balanced_subsample",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
        (
            "gb",
            GradientBoostingClassifier(
                n_estimators=180,
                learning_rate=0.035,
                max_depth=2,
                min_samples_leaf=8,
                subsample=0.85,
                random_state=RANDOM_STATE,
            ),
        ),
    ]

    estimators = {
        "Majority_Baseline": DummyClassifier(strategy="most_frequent"),
        "DecisionTree": DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=8,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "Bagging": BaggingClassifier(
            estimator=DecisionTreeClassifier(
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
            n_estimators=300,
            max_samples=0.85,
            max_features=0.9,
            bootstrap=True,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=500,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=500,
            min_samples_leaf=2,
            max_features="sqrt",
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "AdaBoost": AdaBoostClassifier(
            estimator=clone(shallow_tree),
            n_estimators=220,
            learning_rate=0.035,
            algorithm="SAMME",
            random_state=RANDOM_STATE,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=250,
            learning_rate=0.03,
            max_depth=2,
            min_samples_leaf=8,
            subsample=0.85,
            random_state=RANDOM_STATE,
        ),
        "SoftVoting": VotingClassifier(
            estimators=voting_estimators,
            voting="soft",
            weights=[1, 2, 2],
            n_jobs=-1,
        ),
    }
    return {
        name: Pipeline(
            steps=[("preprocess", clone(preprocessor)), ("model", estimator)]
        )
        for name, estimator in estimators.items()
    }


def save_data_overview(raw_df: pd.DataFrame, output_dir: Path) -> None:
    overview_dir = output_dir / "01_data_overview"
    overview_dir.mkdir(parents=True, exist_ok=True)
    raw_df.head(10).to_csv(overview_dir / "first_10_rows.csv", index=False, encoding="utf-8-sig")
    raw_df.dtypes.astype(str).rename("dtype").to_csv(
        overview_dir / "column_types.csv", encoding="utf-8-sig"
    )
    raw_df.isna().sum().rename("missing_count").to_csv(
        overview_dir / "missing_values.csv", encoding="utf-8-sig"
    )
    raw_df[TARGET].value_counts().rename("count").to_csv(
        overview_dir / "target_distribution.csv", encoding="utf-8-sig"
    )
    raw_df.describe(include="all").transpose().to_csv(
        overview_dir / "descriptive_statistics.csv", encoding="utf-8-sig"
    )


def plot_exploratory_figures(raw_df: pd.DataFrame, figure_dir: Path, output_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    y_order = ["N", "Y"]
    colors = ["#C44E52", "#4C72B0"]

    missing = raw_df.isna().sum().sort_values(ascending=True)
    missing = missing[missing > 0]
    fig, ax = plt.subplots(figsize=(8.2, 4.7))
    ax.barh(missing.index, missing.values, color="#5B8FF9")
    for index, value in enumerate(missing.values):
        ax.text(value + 0.8, index, str(value), va="center")
    ax.set_xlabel("Missing count")
    ax.set_title("Missing Values by Feature")
    fig.tight_layout()
    fig.savefig(figure_dir / "missing_values.png", dpi=220)
    plt.close(fig)

    counts = raw_df[TARGET].value_counts().reindex(y_order)
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    bars = ax.bar(counts.index, counts.values, color=colors)
    for bar, value in zip(bars, counts.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 7,
            f"{value} ({value / len(raw_df):.1%})",
            ha="center",
        )
    ax.set_ylim(0, counts.max() * 1.18)
    ax.set_xlabel("Loan status")
    ax.set_ylabel("Count")
    ax.set_title("Loan Approval Class Distribution")
    fig.tight_layout()
    fig.savefig(figure_dir / "target_distribution.png", dpi=220)
    plt.close(fig)

    numeric_features = [
        "ApplicantIncome",
        "CoapplicantIncome",
        "LoanAmount",
        "Loan_Amount_Term",
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for ax, feature in zip(axes.flat, numeric_features):
        values = [raw_df.loc[raw_df[TARGET] == label, feature].dropna() for label in y_order]
        ax.boxplot(values, tick_labels=y_order, showfliers=False, patch_artist=True)
        for patch, color in zip(ax.artists, colors):
            patch.set_facecolor(color)
        ax.set_title(feature)
        ax.set_xlabel("Loan status")
    fig.suptitle("Numeric Features by Loan Status", y=1.01)
    fig.tight_layout()
    fig.savefig(figure_dir / "numeric_features_by_status.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    category_features = ["Credit_History", "Education", "Property_Area", "Married"]
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.5))
    for ax, feature in zip(axes.flat, category_features):
        temp = raw_df[[feature, TARGET]].copy()
        temp[feature] = temp[feature].fillna("Missing").astype(str)
        approval = temp.groupby(feature)[TARGET].apply(lambda series: (series == "Y").mean())
        approval = approval.sort_values()
        ax.bar(approval.index, approval.values, color="#55A868")
        ax.set_ylim(0, 1)
        ax.set_title(feature)
        ax.set_ylabel("Approval rate")
        ax.tick_params(axis="x", rotation=25)
    fig.suptitle("Approval Rates for Selected Categorical Features", y=1.01)
    fig.tight_layout()
    fig.savefig(figure_dir / "categorical_approval_rates.png", dpi=220, bbox_inches="tight")
    plt.close(fig)

    engineered = engineer_features(raw_df)
    correlation_columns = [
        "ApplicantIncome",
        "CoapplicantIncome",
        "LoanAmount",
        "Loan_Amount_Term",
        "Credit_History",
        "Dependents_Numeric",
        "TotalIncome",
        "LoanIncomeRatio",
        "InstallmentProxy",
        "IncomePerDependent",
    ]
    corr_df = engineered[correlation_columns + [TARGET]].copy()
    corr_df["Loan_Status_Code"] = corr_df[TARGET].map({"N": 0, "Y": 1})
    corr = corr_df[correlation_columns + ["Loan_Status_Code"]].corr()
    corr.to_csv(output_dir / "01_data_overview" / "numeric_correlation.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(9.3, 7.4))
    image = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(np.arange(len(corr.columns)))
    ax.set_yticks(np.arange(len(corr.index)))
    ax.set_xticklabels(corr.columns, rotation=55, ha="right", fontsize=8)
    ax.set_yticklabels(corr.index, fontsize=8)
    ax.set_title("Numeric Feature Correlation")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(figure_dir / "correlation_heatmap.png", dpi=220)
    plt.close(fig)


def evaluate_models(
    models: dict[str, Pipeline],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Pipeline]]:
    model_dir = output_dir / "02_model_results"
    model_dir.mkdir(parents=True, exist_ok=True)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "accuracy": "accuracy",
        "balanced_accuracy": "balanced_accuracy",
        "precision_macro": "precision_macro",
        "recall_macro": "recall_macro",
        "f1_macro": "f1_macro",
        "roc_auc": "roc_auc",
    }
    test_rows: list[dict[str, float | str]] = []
    cv_rows: list[dict[str, float | str]] = []
    fitted_models: dict[str, Pipeline] = {}

    for name, pipeline in models.items():
        cv_result = cross_validate(
            pipeline,
            X_train,
            y_train,
            cv=cv,
            scoring=scoring,
            n_jobs=-1,
            error_score="raise",
        )
        cv_row: dict[str, float | str] = {"model": name}
        for metric in scoring:
            values = cv_result[f"test_{metric}"]
            cv_row[f"cv_{metric}_mean"] = float(values.mean())
            cv_row[f"cv_{metric}_std"] = float(values.std(ddof=1))
        cv_rows.append(cv_row)

        fitted = clone(pipeline).fit(X_train, y_train)
        fitted_models[name] = fitted
        prediction = fitted.predict(X_test)
        probability = fitted.predict_proba(X_test)[:, list(fitted.classes_).index("Y")]
        test_rows.append(
            {
                "model": name,
                "accuracy": accuracy_score(y_test, prediction),
                "balanced_accuracy": balanced_accuracy_score(y_test, prediction),
                "precision_macro": precision_score(y_test, prediction, average="macro", zero_division=0),
                "recall_macro": recall_score(y_test, prediction, average="macro", zero_division=0),
                "f1_macro": f1_score(y_test, prediction, average="macro", zero_division=0),
                "roc_auc": roc_auc_score((y_test == "Y").astype(int), probability),
            }
        )

    test_results = pd.DataFrame(test_rows).sort_values("f1_macro", ascending=False)
    cv_results = pd.DataFrame(cv_rows).sort_values("cv_f1_macro_mean", ascending=False)
    test_results.to_csv(model_dir / "test_metrics.csv", index=False, encoding="utf-8-sig")
    cv_results.to_csv(model_dir / "cross_validation_metrics.csv", index=False, encoding="utf-8-sig")
    return test_results, cv_results, fitted_models


def plot_model_results(
    test_results: pd.DataFrame,
    cv_results: pd.DataFrame,
    fitted_models: dict[str, Pipeline],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    figure_dir: Path,
    output_dir: Path,
) -> tuple[str, dict[str, object]]:
    merged = test_results.merge(
        cv_results[["model", "cv_f1_macro_mean", "cv_f1_macro_std"]], on="model"
    ).sort_values("f1_macro")
    y_positions = np.arange(len(merged))
    fig, ax = plt.subplots(figsize=(9.0, 5.8))
    ax.barh(y_positions - 0.18, merged["f1_macro"], height=0.34, label="Test Macro-F1")
    ax.barh(y_positions + 0.18, merged["cv_f1_macro_mean"], height=0.34, label="CV Macro-F1")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(merged["model"])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Score")
    ax.set_title("Model Performance Comparison")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(figure_dir / "model_comparison.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    for name in test_results["model"]:
        if name == "Majority_Baseline":
            continue
        model = fitted_models[name]
        probability = model.predict_proba(X_test)[:, list(model.classes_).index("Y")]
        false_positive_rate, true_positive_rate, _ = roc_curve(
            (y_test == "Y").astype(int), probability
        )
        auc_value = roc_auc_score((y_test == "Y").astype(int), probability)
        ax.plot(false_positive_rate, true_positive_rate, label=f"{name} ({auc_value:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC Curves on the Test Set")
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(figure_dir / "roc_curves.png", dpi=220)
    plt.close(fig)

    candidate_cv = cv_results[cv_results["model"] != "Majority_Baseline"]
    best_name = str(candidate_cv.iloc[0]["model"])
    best_model = fitted_models[best_name]
    best_prediction = best_model.predict(X_test)
    best_probability = best_model.predict_proba(X_test)[:, list(best_model.classes_).index("Y")]

    matrix = confusion_matrix(y_test, best_prediction, labels=["N", "Y"])
    fig, ax = plt.subplots(figsize=(5.8, 5.0))
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=["N", "Y"])
    display.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"{best_name} Confusion Matrix")
    fig.tight_layout()
    fig.savefig(figure_dir / "best_confusion_matrix.png", dpi=220)
    plt.close(fig)

    importance = permutation_importance(
        best_model,
        X_test,
        y_test,
        scoring="f1_macro",
        n_repeats=40,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    importance_table = pd.DataFrame(
        {
            "feature": X_test.columns,
            "importance_mean": importance.importances_mean,
            "importance_std": importance.importances_std,
        }
    ).sort_values("importance_mean", ascending=False)
    importance_table.to_csv(
        output_dir / "02_model_results" / "permutation_importance.csv",
        index=False,
        encoding="utf-8-sig",
    )
    plot_importance = importance_table.head(20).sort_values("importance_mean")
    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    ax.barh(
        plot_importance["feature"],
        plot_importance["importance_mean"],
        xerr=plot_importance["importance_std"],
        color="#4C72B0",
        alpha=0.9,
    )
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Decrease in Macro-F1 after permutation")
    ax.set_title(f"Permutation Importance: {best_name}")
    fig.tight_layout()
    fig.savefig(figure_dir / "feature_importance_top20.png", dpi=220)
    plt.close(fig)

    report = classification_report(y_test, best_prediction, output_dict=True, zero_division=0)
    pd.DataFrame(report).transpose().to_csv(
        output_dir / "02_model_results" / "best_classification_report.csv",
        encoding="utf-8-sig",
    )
    pd.DataFrame(matrix, index=["actual_N", "actual_Y"], columns=["pred_N", "pred_Y"]).to_csv(
        output_dir / "02_model_results" / "best_confusion_matrix.csv",
        encoding="utf-8-sig",
    )

    summary = {
        "best_model": best_name,
        "confusion_matrix": matrix.tolist(),
        "classification_report": report,
        "test_roc_auc": float(roc_auc_score((y_test == "Y").astype(int), best_probability)),
        "top_features": importance_table.head(10).to_dict(orient="records"),
    }
    return best_name, summary


def main() -> None:
    configure_plot_style()
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / "loan.csv"
    figure_dir = base_dir / "figures"
    output_dir = base_dir / "results_loan_ensemble"
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_data(data_path)
    save_data_overview(raw_df, output_dir)
    plot_exploratory_figures(raw_df, figure_dir, output_dir)

    model_df = engineer_features(raw_df)
    X = model_df.drop(columns=[TARGET])
    y = model_df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        stratify=y,
        random_state=RANDOM_STATE,
    )

    preprocessor, numeric_columns, categorical_columns = make_preprocessor(X)
    models = build_models(preprocessor)
    test_results, cv_results, fitted_models = evaluate_models(
        models, X_train, X_test, y_train, y_test, output_dir
    )
    best_name, best_summary = plot_model_results(
        test_results,
        cv_results,
        fitted_models,
        X_test,
        y_test,
        figure_dir,
        output_dir,
    )

    summary = {
        "data_shape": list(raw_df.shape),
        "missing_cells": int(raw_df.isna().sum().sum()),
        "duplicate_rows": int(raw_df.duplicated().sum()),
        "target_counts": raw_df[TARGET].value_counts().to_dict(),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "best_model": best_name,
        "best_model_details": best_summary,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print(f"Data shape: {raw_df.shape}")
    print(f"Missing cells: {raw_df.isna().sum().sum()}")
    print(f"Target counts: {raw_df[TARGET].value_counts().to_dict()}")
    print(f"Train/test sizes: {len(X_train)}/{len(X_test)}")
    print("\nTest metrics:")
    print(test_results.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print("\nCross-validation metrics:")
    print(
        cv_results[
            [
                "model",
                "cv_accuracy_mean",
                "cv_balanced_accuracy_mean",
                "cv_f1_macro_mean",
                "cv_roc_auc_mean",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print(f"\nBest model selected by CV Macro-F1: {best_name}")


if __name__ == "__main__":
    main()
