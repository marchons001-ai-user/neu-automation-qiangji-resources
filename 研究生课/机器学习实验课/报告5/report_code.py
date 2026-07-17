# -*- coding: utf-8 -*-
"""Report 5: clustering automobile styles with the ISLR Auto dataset.

The script performs data validation, exploratory analysis, preprocessing,
cluster-number selection, algorithm comparison, cluster profiling, and saves
all tables/figures used by the LaTeX report.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_samples,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore")

RANDOM_STATE = 42
NUMERIC_COLUMNS = [
    "mpg",
    "cylinders",
    "displacement",
    "horsepower",
    "weight",
    "acceleration",
    "year",
]
CATEGORICAL_COLUMNS = ["origin"]
ALL_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS
ORIGIN_NAMES = {1: "USA", 2: "Europe", 3: "Japan"}
COLORS = ["#2563EB", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6"]


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
    missing_columns = set(ALL_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_columns)}")
    df = df[ALL_COLUMNS].copy()
    for column in ALL_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df.isna().any().any():
        bad = df.isna().sum()
        raise ValueError(f"Numeric conversion produced missing values:\n{bad[bad > 0]}")
    return df


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_COLUMNS),
            ("origin", make_one_hot_encoder(), CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
    )


def save_overview(df: pd.DataFrame, out_dir: Path) -> None:
    ensure_dir(out_dir)
    df.head(10).to_csv(out_dir / "head_10.csv", index=False, encoding="utf-8-sig")
    df.dtypes.astype(str).rename("dtype").to_csv(
        out_dir / "dtypes.csv", encoding="utf-8-sig"
    )
    df.isna().sum().rename("missing_count").to_csv(
        out_dir / "missing_values.csv", encoding="utf-8-sig"
    )
    df.describe().T.to_csv(out_dir / "describe.csv", encoding="utf-8-sig")
    df["origin"].map(ORIGIN_NAMES).value_counts().rename("count").to_csv(
        out_dir / "origin_distribution.csv", encoding="utf-8-sig"
    )
    df["cylinders"].value_counts().sort_index().rename("count").to_csv(
        out_dir / "cylinder_distribution.csv", encoding="utf-8-sig"
    )


def plot_eda(df: pd.DataFrame, fig_dir: Path) -> None:
    ensure_dir(fig_dir)
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    axes[0].hist(df["mpg"], bins=18, color="#2563EB", edgecolor="white")
    axes[0].axvline(df["mpg"].mean(), color="#DC2626", linestyle="--", label="mean")
    axes[0].set(title="Distribution of Fuel Economy", xlabel="mpg", ylabel="count")
    axes[0].legend()
    cylinder_counts = df["cylinders"].value_counts().sort_index()
    axes[1].bar(
        cylinder_counts.index.astype(str), cylinder_counts.values, color="#10B981"
    )
    axes[1].set(title="Cylinder Distribution", xlabel="cylinders", ylabel="count")
    for i, value in enumerate(cylinder_counts.values):
        axes[1].text(i, value + 3, str(int(value)), ha="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(fig_dir / "basic_distributions.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    corr = df[NUMERIC_COLUMNS].corr()
    fig, ax = plt.subplots(figsize=(8.2, 6.5))
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        square=True,
        linewidths=0.4,
        ax=ax,
    )
    ax.set_title("Correlation Heatmap of Numeric Features")
    fig.tight_layout()
    fig.savefig(fig_dir / "correlation_heatmap.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    origin_plot = df.copy()
    origin_plot["origin_name"] = origin_plot["origin"].map(ORIGIN_NAMES)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    sns.boxplot(data=origin_plot, x="origin_name", y="mpg", ax=axes[0], palette="Set2")
    axes[0].set(title="Fuel Economy by Origin", xlabel="origin", ylabel="mpg")
    sns.scatterplot(
        data=origin_plot,
        x="weight",
        y="mpg",
        hue="origin_name",
        palette="Set2",
        alpha=0.78,
        ax=axes[1],
    )
    axes[1].set(title="Weight vs. Fuel Economy", xlabel="weight", ylabel="mpg")
    axes[1].legend(title="origin")
    fig.tight_layout()
    fig.savefig(fig_dir / "origin_and_weight_mpg.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def evaluate_labels(X: np.ndarray, labels: np.ndarray) -> dict[str, float]:
    unique = np.unique(labels)
    if len(unique) < 2 or len(unique) >= len(labels):
        return {
            "Silhouette": np.nan,
            "Calinski_Harabasz": np.nan,
            "Davies_Bouldin": np.nan,
        }
    return {
        "Silhouette": silhouette_score(X, labels),
        "Calinski_Harabasz": calinski_harabasz_score(X, labels),
        "Davies_Bouldin": davies_bouldin_score(X, labels),
    }


def scan_kmeans(X: np.ndarray, out_dir: Path, fig_dir: Path) -> pd.DataFrame:
    rows = []
    for k in range(2, 9):
        model = KMeans(n_clusters=k, n_init=50, random_state=RANDOM_STATE)
        labels = model.fit_predict(X)
        metrics = evaluate_labels(X, labels)
        rows.append(
            {
                "k": k,
                "Inertia": model.inertia_,
                **metrics,
                "Min_Cluster_Size": np.bincount(labels).min(),
                "Max_Cluster_Size": np.bincount(labels).max(),
            }
        )
    results = pd.DataFrame(rows)
    results.to_csv(out_dir / "kmeans_k_selection.csv", index=False, encoding="utf-8-sig")

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 3.8))
    axes[0].plot(results["k"], results["Inertia"], marker="o", color="#2563EB")
    axes[0].set(title="Elbow Method", xlabel="number of clusters k", ylabel="inertia")
    axes[1].plot(results["k"], results["Silhouette"], marker="o", color="#10B981")
    axes[1].set(title="Silhouette Score", xlabel="number of clusters k", ylabel="score")
    axes[2].plot(
        results["k"], results["Davies_Bouldin"], marker="o", color="#EF4444"
    )
    axes[2].set(title="Davies-Bouldin Index", xlabel="number of clusters k", ylabel="index")
    for ax in axes:
        ax.set_xticks(results["k"])
    fig.tight_layout()
    fig.savefig(fig_dir / "kmeans_k_selection.png", dpi=240, bbox_inches="tight")
    plt.close(fig)
    return results


def select_dbscan(X: np.ndarray) -> tuple[DBSCAN, np.ndarray, dict[str, float]]:
    candidates = []
    for min_samples in [5, 6, 8, 10]:
        for eps in np.arange(0.6, 1.61, 0.1):
            model = DBSCAN(eps=float(eps), min_samples=min_samples)
            labels = model.fit_predict(X)
            mask = labels != -1
            n_clusters = len(set(labels[mask]))
            noise_ratio = 1.0 - mask.mean()
            if n_clusters < 2 or mask.sum() < 0.6 * len(labels):
                continue
            score = silhouette_score(X[mask], labels[mask])
            candidates.append((score - 0.25 * noise_ratio, score, noise_ratio, model, labels))
    if not candidates:
        model = DBSCAN(eps=1.0, min_samples=8)
        labels = model.fit_predict(X)
        return model, labels, {"Silhouette": np.nan, "Noise_Ratio": 1.0}
    _, score, noise_ratio, model, labels = max(candidates, key=lambda item: item[0])
    return model, labels, {"Silhouette": score, "Noise_Ratio": noise_ratio}


def compare_algorithms(
    X: np.ndarray, n_clusters: int, out_dir: Path
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    labels_by_model: dict[str, np.ndarray] = {}
    labels_by_model["KMeans"] = KMeans(
        n_clusters=n_clusters, n_init=50, random_state=RANDOM_STATE
    ).fit_predict(X)
    labels_by_model["Agglomerative_Ward"] = AgglomerativeClustering(
        n_clusters=n_clusters, linkage="ward"
    ).fit_predict(X)
    labels_by_model["Gaussian_Mixture"] = GaussianMixture(
        n_components=n_clusters, covariance_type="full", n_init=20, random_state=RANDOM_STATE
    ).fit_predict(X)
    dbscan_model, dbscan_labels, dbscan_info = select_dbscan(X)
    labels_by_model["DBSCAN"] = dbscan_labels

    kmeans_labels = labels_by_model["KMeans"]
    rows = []
    for name, labels in labels_by_model.items():
        if name == "DBSCAN":
            mask = labels != -1
            n_found = len(set(labels[mask]))
            metrics = evaluate_labels(X[mask], labels[mask]) if n_found >= 2 else {}
            rows.append(
                {
                    "Model": name,
                    "Clusters": n_found,
                    "Noise_Ratio": dbscan_info["Noise_Ratio"],
                    "Silhouette": metrics.get("Silhouette", np.nan),
                    "Calinski_Harabasz": metrics.get("Calinski_Harabasz", np.nan),
                    "Davies_Bouldin": metrics.get("Davies_Bouldin", np.nan),
                    "ARI_vs_KMeans": adjusted_rand_score(kmeans_labels[mask], labels[mask]),
                    "Parameters": f"eps={dbscan_model.eps:.1f}, min_samples={dbscan_model.min_samples}",
                }
            )
        else:
            metrics = evaluate_labels(X, labels)
            rows.append(
                {
                    "Model": name,
                    "Clusters": len(np.unique(labels)),
                    "Noise_Ratio": 0.0,
                    **metrics,
                    "ARI_vs_KMeans": adjusted_rand_score(kmeans_labels, labels),
                    "Parameters": f"k={n_clusters}",
                }
            )
    comparison = pd.DataFrame(rows).sort_values("Silhouette", ascending=False)
    comparison.to_csv(out_dir / "algorithm_comparison.csv", index=False, encoding="utf-8-sig")
    return comparison, labels_by_model


def kmeans_stability(X: np.ndarray, n_clusters: int, out_dir: Path) -> dict[str, float]:
    reference = KMeans(
        n_clusters=n_clusters, n_init=50, random_state=RANDOM_STATE
    ).fit_predict(X)
    scores = []
    for seed in range(20):
        labels = KMeans(n_clusters=n_clusters, n_init=10, random_state=seed).fit_predict(X)
        scores.append(adjusted_rand_score(reference, labels))
    stability = {
        "mean_ari": float(np.mean(scores)),
        "std_ari": float(np.std(scores)),
        "min_ari": float(np.min(scores)),
        "max_ari": float(np.max(scores)),
    }
    pd.Series(stability).to_csv(out_dir / "kmeans_stability.csv", encoding="utf-8-sig")
    return stability


def ordered_cluster_labels(df: pd.DataFrame, labels: np.ndarray) -> tuple[np.ndarray, dict[int, str]]:
    temp = df.copy()
    temp["raw_cluster"] = labels
    means = temp.groupby("raw_cluster")["mpg"].mean().sort_values(ascending=False)
    order = means.index.tolist()
    if len(order) == 2:
        names = ["Fuel-efficient and light", "High-power and heavy"]
    else:
        names = [f"Style {i + 1}" for i in range(len(order))]
    raw_to_name = {raw: names[i] for i, raw in enumerate(order)}
    named = np.array([raw_to_name[label] for label in labels], dtype=object)
    return named, raw_to_name


def save_cluster_profiles(
    df: pd.DataFrame,
    labels: np.ndarray,
    out_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    names, _ = ordered_cluster_labels(df, labels)
    clustered = df.copy()
    clustered["cluster"] = names
    order = clustered.groupby("cluster")["mpg"].mean().sort_values(ascending=False).index
    profile = clustered.groupby("cluster")[ALL_COLUMNS].mean().reindex(order)
    counts = clustered["cluster"].value_counts().reindex(order).rename("count").to_frame()
    counts["ratio"] = counts["count"] / len(clustered)
    origin_share = pd.crosstab(
        clustered["cluster"], clustered["origin"].map(ORIGIN_NAMES), normalize="index"
    ).reindex(order)
    cylinder_share = pd.crosstab(
        clustered["cluster"], clustered["cylinders"], normalize="index"
    ).reindex(order)

    profile.to_csv(out_dir / "cluster_profiles.csv", encoding="utf-8-sig")
    counts.to_csv(out_dir / "cluster_sizes.csv", encoding="utf-8-sig")
    origin_share.to_csv(out_dir / "cluster_origin_share.csv", encoding="utf-8-sig")
    cylinder_share.to_csv(out_dir / "cluster_cylinder_share.csv", encoding="utf-8-sig")
    clustered.to_csv(out_dir / "clustered_auto_data.csv", index=False, encoding="utf-8-sig")
    return profile, counts, origin_share, names


def plot_clustering_results(
    df: pd.DataFrame,
    X: np.ndarray,
    labels: np.ndarray,
    names: np.ndarray,
    profile: pd.DataFrame,
    origin_share: pd.DataFrame,
    fig_dir: Path,
) -> dict[str, float]:
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X)
    explained = pca.explained_variance_ratio_
    ordered_names = profile.index.tolist()
    color_map = {name: COLORS[i] for i, name in enumerate(ordered_names)}

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    for name in ordered_names:
        mask = names == name
        ax.scatter(
            X_pca[mask, 0],
            X_pca[mask, 1],
            s=30,
            alpha=0.76,
            color=color_map[name],
            label=f"{name} (n={mask.sum()})",
        )
    ax.axhline(0, color="gray", linewidth=0.6)
    ax.axvline(0, color="gray", linewidth=0.6)
    ax.set(
        title="PCA Projection of Automobile Clusters",
        xlabel=f"PC1 ({explained[0] * 100:.1f}% variance)",
        ylabel=f"PC2 ({explained[1] * 100:.1f}% variance)",
    )
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "pca_clusters.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    sample_scores = silhouette_samples(X, labels)
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    y_lower = 10
    for i, raw_label in enumerate(np.unique(labels)):
        values = np.sort(sample_scores[labels == raw_label])
        size = len(values)
        y_upper = y_lower + size
        display_name = names[labels == raw_label][0]
        ax.fill_betweenx(
            np.arange(y_lower, y_upper), 0, values, color=color_map[display_name], alpha=0.8
        )
        ax.text(-0.08, y_lower + 0.5 * size, display_name, fontsize=9, va="center")
        y_lower = y_upper + 10
    avg_score = silhouette_score(X, labels)
    ax.axvline(avg_score, color="#DC2626", linestyle="--", label=f"mean={avg_score:.3f}")
    ax.set(title="Silhouette Plot of the Final Clustering", xlabel="silhouette coefficient", ylabel="samples")
    ax.set_yticks([])
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "silhouette_plot.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    radar_features = ["mpg", "cylinders", "displacement", "horsepower", "weight", "acceleration", "year"]
    standardized_profile = (profile[radar_features] - df[radar_features].mean()) / df[radar_features].std()
    angles = np.linspace(0, 2 * np.pi, len(radar_features), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(7.0, 6.0), subplot_kw={"polar": True})
    for name in ordered_names:
        values = standardized_profile.loc[name].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=name, color=color_map[name])
        ax.fill(angles, values, alpha=0.10, color=color_map[name])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(radar_features)
    ax.set_title("Standardized Cluster Profiles", pad=18)
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.12))
    fig.tight_layout()
    fig.savefig(fig_dir / "cluster_profile_radar.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    plot_df = df.copy()
    plot_df["cluster"] = names
    sns.scatterplot(
        data=plot_df,
        x="weight",
        y="mpg",
        hue="cluster",
        palette=color_map,
        alpha=0.78,
        ax=axes[0],
    )
    axes[0].set(title="Clusters in Weight-MPG Space", xlabel="weight", ylabel="mpg")
    axes[0].legend(title="cluster", fontsize=8)
    origin_share.plot(kind="bar", stacked=True, ax=axes[1], color=["#2563EB", "#F59E0B", "#10B981"])
    axes[1].set(title="Origin Composition by Cluster", xlabel="cluster", ylabel="proportion")
    axes[1].tick_params(axis="x", rotation=10)
    axes[1].legend(title="origin")
    fig.tight_layout()
    fig.savefig(fig_dir / "cluster_interpretation.png", dpi=240, bbox_inches="tight")
    plt.close(fig)

    return {
        "pca_pc1_ratio": float(explained[0]),
        "pca_pc2_ratio": float(explained[1]),
        "pca_total_ratio": float(explained.sum()),
        "final_silhouette": float(avg_score),
    }


def run_experiment(data_path: Path, output_root: Path) -> dict[str, object]:
    overview_dir = ensure_dir(output_root / "results_auto_clustering" / "01_data_overview")
    model_dir = ensure_dir(output_root / "results_auto_clustering" / "02_clustering")
    fig_dir = ensure_dir(output_root / "figures")

    df = load_data(data_path)
    save_overview(df, overview_dir)
    plot_eda(df, fig_dir)

    preprocessor = build_preprocessor()
    X = preprocessor.fit_transform(df)
    k_results = scan_kmeans(X, model_dir, fig_dir)
    best_k = int(k_results.loc[k_results["Silhouette"].idxmax(), "k"])

    comparison, labels_by_model = compare_algorithms(X, best_k, model_dir)
    stability = kmeans_stability(X, best_k, model_dir)
    final_model_name = comparison.loc[
        comparison["Model"] != "DBSCAN", "Silhouette"
    ].idxmax()
    final_model_name = str(comparison.loc[final_model_name, "Model"])
    final_labels = labels_by_model[final_model_name]

    profile, counts, origin_share, names = save_cluster_profiles(df, final_labels, model_dir)
    plot_summary = plot_clustering_results(
        df, X, final_labels, names, profile, origin_share, fig_dir
    )

    summary = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_values": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "transformed_features": int(X.shape[1]),
        "best_k": best_k,
        "final_model": final_model_name,
        "final_cluster_sizes": {str(k): int(v) for k, v in counts["count"].items()},
        "kmeans_stability": stability,
        **plot_summary,
    }
    with (model_dir / "summary.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)

    print("Experiment completed.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\nAlgorithm comparison:")
    print(comparison.round(4).to_string(index=False))
    print("\nFinal cluster profiles:")
    print(profile.round(2).to_string())
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auto dataset clustering experiment")
    parser.add_argument("--data", type=Path, default=Path("数据集.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("."))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_experiment(args.data, args.output_root)
