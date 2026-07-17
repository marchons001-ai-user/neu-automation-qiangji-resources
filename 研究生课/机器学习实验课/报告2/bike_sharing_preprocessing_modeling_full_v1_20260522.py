# -*- coding: utf-8 -*-
"""
共享单车小时租赁数量预测：数据预处理 + 特征工程 + 建模完整脚本

对应流程：
1. 数据预览
2. 相关分析
3. 直接建模
4. 特征工程
5. 特征编码
6. 离散化
7. 构造新特征
8. 异常值检测和处理
9. 数值特征标准化
10. 重新建模

运行方式：
    python bike_sharing_preprocessing_modeling_full_v1_20260522.py --data hour.csv

说明：
- 目标变量：cnt，即每小时自行车租借总数
- casual 和 registered 相加等于 cnt，属于目标泄漏字段，建模时必须删除
- 默认采用按时间顺序 80%/20% 划分训练集和测试集，更符合“小时租赁数量预测”的场景
"""

import argparse
import io
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


warnings.filterwarnings("ignore")


# =========================
# 0. 基本配置
# =========================

TARGET_COL = "cnt"

# casual + registered = cnt，不能作为输入特征，否则会造成严重的数据泄漏
LEAKAGE_COLS = ["casual", "registered"]

REQUIRED_COLS = [
    "dteday", "season", "yr", "mnth", "hr", "holiday", "weekday",
    "workingday", "weathersit", "temp", "atemp", "hum", "windspeed", "cnt"
]


def make_one_hot_encoder():
    """兼容不同 sklearn 版本的 OneHotEncoder 写法。"""
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_data_path(user_path):
    """
    优先使用命令行传入路径。
    如果未传入，则在当前目录自动搜索包含 Bike Sharing Hour 数据字段的 csv。
    """
    if user_path is not None:
        p = Path(user_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"找不到数据文件：{user_path}")

    candidates = list(Path(".").glob("*.csv"))
    for p in candidates:
        try:
            tmp = pd.read_csv(p, nrows=5)
            if all(c in tmp.columns for c in REQUIRED_COLS):
                return p
        except Exception:
            pass

    raise FileNotFoundError(
        "未指定 --data，且当前目录没有找到符合要求的 csv。\n"
        "请使用：python 脚本名.py --data hour.csv"
    )


# =========================
# 1. 数据读取与预览
# =========================

def load_data(data_path):
    df = pd.read_csv(data_path)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"数据缺少必要字段：{missing}")

    # 日期字段处理
    df["dteday"] = pd.to_datetime(df["dteday"])
    df["datetime"] = df["dteday"] + pd.to_timedelta(df["hr"], unit="h")

    # 按时间排序，保证后面时间切分合理
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def save_data_overview(df, out_dir):
    overview_dir = ensure_dir(out_dir / "01_data_overview")

    # 前 10 行
    df.head(10).to_csv(overview_dir / "head_10.csv", index=False, encoding="utf-8-sig")

    # info 信息
    buffer = io.StringIO()
    df.info(buf=buffer)
    (overview_dir / "data_info.txt").write_text(buffer.getvalue(), encoding="utf-8")

    # 描述性统计
    df.describe(include="all").to_csv(overview_dir / "describe.csv", encoding="utf-8-sig")

    # 缺失值统计
    missing_df = pd.DataFrame({
        "missing_count": df.isna().sum(),
        "missing_ratio": df.isna().mean()
    }).sort_values("missing_count", ascending=False)
    missing_df.to_csv(overview_dir / "missing_values.csv", encoding="utf-8-sig")

    # 目标变量分布图
    plt.figure(figsize=(9, 5))
    plt.hist(df[TARGET_COL], bins=50)
    plt.title("Distribution of hourly bike rental count")
    plt.xlabel("cnt")
    plt.ylabel("frequency")
    plt.tight_layout()
    plt.savefig(overview_dir / "target_cnt_distribution.png", dpi=200)
    plt.close()

    # 每小时平均租借量
    hourly_mean = df.groupby("hr")[TARGET_COL].mean()
    plt.figure(figsize=(9, 5))
    plt.plot(hourly_mean.index, hourly_mean.values, marker="o")
    plt.title("Average bike rental count by hour")
    plt.xlabel("hour")
    plt.ylabel("average cnt")
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig(overview_dir / "average_cnt_by_hour.png", dpi=200)
    plt.close()

    print("\n[1] 数据预览完成")
    print(f"    数据规模：{df.shape[0]} 行，{df.shape[1]} 列")
    print(f"    预览文件保存到：{overview_dir}")


# =========================
# 2. 相关分析
# =========================

def save_correlation_analysis(df, out_dir):
    corr_dir = ensure_dir(out_dir / "02_correlation_analysis")

    # 数值相关性，保留 casual/registered 供说明，但建模不会使用
    numeric_df = df.select_dtypes(include=[np.number]).copy()
    corr = numeric_df.corr()
    corr.to_csv(corr_dir / "correlation_matrix.csv", encoding="utf-8-sig")

    # 与目标 cnt 的相关性
    target_corr = corr[TARGET_COL].sort_values(ascending=False)
    target_corr.to_csv(corr_dir / "target_cnt_correlation.csv", encoding="utf-8-sig")

    # 热力图
    plt.figure(figsize=(12, 10))
    im = plt.imshow(corr.values, aspect="auto")
    plt.colorbar(im, fraction=0.046, pad=0.04)
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=90)
    plt.yticks(range(len(corr.index)), corr.index)
    plt.title("Correlation heatmap")
    plt.tight_layout()
    plt.savefig(corr_dir / "correlation_heatmap.png", dpi=200)
    plt.close()

    print("\n[2] 相关分析完成")
    print("    注意：casual 和 registered 与 cnt 高度相关，但它们是目标泄漏字段，建模时已删除。")
    print(f"    相关性结果保存到：{corr_dir}")


# =========================
# 3. 通用建模工具
# =========================

def time_order_train_test_split(df, test_ratio=0.2):
    """
    时间序列类问题不建议随机打乱。
    这里用前 80% 时间作为训练集，后 20% 时间作为测试集。
    """
    n = len(df)
    split_idx = int(n * (1 - test_ratio))
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    return train_df, test_df


def regression_metrics(y_true, y_pred):
    y_pred = np.asarray(y_pred)
    y_pred = np.maximum(y_pred, 0)  # 租赁数量不应为负

    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))

    y_true = np.asarray(y_true)
    nrmse = rmse / (y_true.max() - y_true.min() + 1e-12)

    return {
        "RMSE": rmse,
        "MAE": mae,
        "R2": r2,
        "NRMSE": float(nrmse)
    }


def evaluate_model(model, X_train, y_train, X_test, y_test):
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    return regression_metrics(y_test, pred), pred


def save_prediction_plot(y_true, y_pred, save_path, title, max_points=500):
    n = min(len(y_true), max_points)
    plt.figure(figsize=(12, 5))
    plt.plot(np.arange(n), np.asarray(y_true)[:n], label="true")
    plt.plot(np.arange(n), np.asarray(y_pred)[:n], label="pred")
    plt.title(title)
    plt.xlabel("test sample index")
    plt.ylabel("cnt")
    plt.legend()
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    plt.close()


# =========================
# 4. 直接建模：未做复杂预处理
# =========================

def direct_modeling(df, out_dir):
    """
    直接建模：只删除明显不能直接输入/会泄漏的字段，然后直接训练模型。
    这一步作为基线，用于和后面的“预处理 + 特征工程”结果对比。
    """
    model_dir = ensure_dir(out_dir / "03_direct_modeling")

    drop_cols = [TARGET_COL, "datetime", "dteday", "instant"] + LEAKAGE_COLS
    raw_features = [c for c in df.columns if c not in drop_cols]

    train_df, test_df = time_order_train_test_split(df, test_ratio=0.2)

    X_train = train_df[raw_features]
    y_train = train_df[TARGET_COL]
    X_test = test_df[raw_features]
    y_test = test_df[TARGET_COL]

    # 所有字段此时都是数值字段，但 season/weathersit 等仍只是原始编号
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), raw_features)
        ],
        remainder="drop"
    )

    models = {
        "Direct_Ridge_logTarget": TransformedTargetRegressor(
            regressor=Pipeline([
                ("preprocess", preprocessor),
                ("model", Ridge(alpha=1.0))
            ]),
            func=np.log1p,
            inverse_func=np.expm1
        ),
        "Direct_RandomForest": RandomForestRegressor(
            n_estimators=80,
            max_depth=18,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
    }

    results = []
    predictions = {}

    # RandomForest 不需要标准化，这里为了和 Ridge 处理流程统一，仍保留原始数值输入
    for name, model in models.items():
        if name == "Direct_RandomForest":
            model_to_fit = model
        else:
            model_to_fit = model

        metrics, pred = evaluate_model(model_to_fit, X_train, y_train, X_test, y_test)
        metrics["model"] = name
        results.append(metrics)
        predictions[name] = pred

    result_df = pd.DataFrame(results).set_index("model").sort_values("RMSE")
    result_df.to_csv(model_dir / "direct_model_comparison.csv", encoding="utf-8-sig")

    best_name = result_df.index[0]
    save_prediction_plot(
        y_test,
        predictions[best_name],
        model_dir / "direct_best_prediction_curve.png",
        f"Direct modeling best prediction: {best_name}"
    )

    print("\n[3] 直接建模完成")
    print(result_df)
    print(f"    直接建模结果保存到：{model_dir}")

    return result_df


# =========================
# 5-8. 特征工程、编码、离散化、新特征、异常值处理
# =========================

def add_engineered_features(df):
    """
    特征工程：
    - 日期时间特征
    - 周期性特征
    - 离散化特征
    - 业务逻辑新特征
    """
    df = df.copy()

    if "datetime" not in df.columns:
        df["dteday"] = pd.to_datetime(df["dteday"])
        df["datetime"] = df["dteday"] + pd.to_timedelta(df["hr"], unit="h")

    # 日期特征
    df["day"] = df["dteday"].dt.day
    df["dayofyear"] = df["dteday"].dt.dayofyear
    df["weekofyear"] = df["dteday"].dt.isocalendar().week.astype(int)

    # 周期性特征：小时、月份、星期
    df["hr_sin"] = np.sin(2 * np.pi * df["hr"] / 24)
    df["hr_cos"] = np.cos(2 * np.pi * df["hr"] / 24)
    df["mnth_sin"] = np.sin(2 * np.pi * df["mnth"] / 12)
    df["mnth_cos"] = np.cos(2 * np.pi * df["mnth"] / 12)
    df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)

    # 离散化：把连续气象变量分箱
    df["temp_bin"] = pd.cut(
        df["temp"],
        bins=[-np.inf, 0.25, 0.50, 0.75, np.inf],
        labels=["cold", "cool", "warm", "hot"]
    )

    df["hum_bin"] = pd.cut(
        df["hum"],
        bins=[-np.inf, 0.30, 0.60, 0.80, np.inf],
        labels=["dry", "normal", "wet", "very_wet"]
    )

    df["windspeed_bin"] = pd.cut(
        df["windspeed"],
        bins=[-np.inf, 0.15, 0.30, 0.45, np.inf],
        labels=["low", "middle", "high", "very_high"]
    )

    # 构造业务特征
    df["is_weekend"] = df["weekday"].isin([0, 6]).astype(int)
    df["is_night"] = ((df["hr"] <= 5) | (df["hr"] >= 22)).astype(int)
    df["is_daytime"] = ((df["hr"] >= 7) & (df["hr"] <= 20)).astype(int)
    df["is_commute_hour"] = df["hr"].isin([7, 8, 17, 18]).astype(int)

    # 工作日通勤高峰、非工作日白天休闲高峰
    df["is_peak_hour"] = (
        ((df["workingday"] == 1) & (df["hr"].isin([7, 8, 17, 18]))) |
        ((df["workingday"] == 0) & (df["hr"].between(10, 16)))
    ).astype(int)

    df["bad_weather"] = (df["weathersit"] >= 3).astype(int)
    df["good_weather"] = (df["weathersit"] == 1).astype(int)

    # 交互特征
    df["feel_temp_diff"] = df["atemp"] - df["temp"]
    df["temp_hum_interaction"] = df["temp"] * df["hum"]
    df["temp_wind_interaction"] = df["temp"] * df["windspeed"]
    df["hum_wind_interaction"] = df["hum"] * df["windspeed"]
    df["workingday_commute"] = df["workingday"] * df["is_commute_hour"]
    df["weekend_daytime"] = df["is_weekend"] * df["is_daytime"]
    df["bad_weather_peak"] = df["bad_weather"] * df["is_peak_hour"]

    return df


def clip_outliers_iqr(train_df, test_df, numeric_cols, out_dir, k=1.5):
    """
    异常值处理：
    只用训练集计算 IQR 上下界，再同时裁剪训练集和测试集。
    这样可以避免使用测试集信息造成数据泄漏。
    """
    outlier_dir = ensure_dir(out_dir / "08_outlier_processing")

    train_df = train_df.copy()
    test_df = test_df.copy()

    records = []
    for col in numeric_cols:
        q1 = train_df[col].quantile(0.25)
        q3 = train_df[col].quantile(0.75)
        iqr = q3 - q1

        # 如果变量几乎没有波动，就跳过
        if pd.isna(iqr) or iqr == 0:
            continue

        low = q1 - k * iqr
        high = q3 + k * iqr

        train_outliers = ((train_df[col] < low) | (train_df[col] > high)).sum()
        test_outliers = ((test_df[col] < low) | (test_df[col] > high)).sum()

        train_df[col] = train_df[col].clip(low, high)
        test_df[col] = test_df[col].clip(low, high)

        records.append({
            "feature": col,
            "lower_bound": low,
            "upper_bound": high,
            "train_outlier_count": int(train_outliers),
            "test_outlier_count": int(test_outliers)
        })

    outlier_report = pd.DataFrame(records)
    outlier_report.to_csv(outlier_dir / "iqr_outlier_clip_report.csv", index=False, encoding="utf-8-sig")

    print("\n[8] 异常值检测和处理完成")
    print(f"    IQR 裁剪报告保存到：{outlier_dir}")

    return train_df, test_df, outlier_report


# =========================
# 9-10. 标准化后重新建模
# =========================

def engineered_modeling(df, out_dir):
    model_dir = ensure_dir(out_dir / "10_engineered_modeling")

    df_fe = add_engineered_features(df)

    train_df, test_df = time_order_train_test_split(df_fe, test_ratio=0.2)

    # 类别特征：需要 one-hot 编码
    categorical_features = [
        "season", "mnth", "hr", "weekday", "weathersit",
        "temp_bin", "hum_bin", "windspeed_bin"
    ]

    # 二值特征：可以直接作为数值输入
    binary_features = [
        "yr", "holiday", "workingday",
        "is_weekend", "is_night", "is_daytime", "is_commute_hour",
        "is_peak_hour", "bad_weather", "good_weather",
        "workingday_commute", "weekend_daytime", "bad_weather_peak"
    ]

    # 连续数值特征：需要标准化
    numeric_features = [
        "temp", "atemp", "hum", "windspeed",
        "day", "dayofyear", "weekofyear",
        "hr_sin", "hr_cos", "mnth_sin", "mnth_cos",
        "weekday_sin", "weekday_cos",
        "feel_temp_diff",
        "temp_hum_interaction", "temp_wind_interaction", "hum_wind_interaction"
    ]

    # 异常值处理只对连续数值特征做，不对类别编号和二值变量做
    train_df, test_df, _ = clip_outliers_iqr(
        train_df=train_df,
        test_df=test_df,
        numeric_cols=numeric_features,
        out_dir=out_dir,
        k=1.5
    )

    feature_cols = categorical_features + binary_features + numeric_features

    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COL]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COL]

    # 特征编码 + 数值标准化
    # 类别特征：OneHotEncoder
    # 连续特征：StandardScaler
    # 二值特征：passthrough
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", make_one_hot_encoder(), categorical_features),
            ("num", StandardScaler(), numeric_features),
            ("bin", "passthrough", binary_features)
        ],
        remainder="drop"
    )

    models = {
        "FE_Ridge_logTarget": TransformedTargetRegressor(
            regressor=Pipeline([
                ("preprocess", preprocessor),
                ("model", Ridge(alpha=1.0))
            ]),
            func=np.log1p,
            inverse_func=np.expm1
        ),
        "FE_RandomForest_logTarget": TransformedTargetRegressor(
            regressor=Pipeline([
                ("preprocess", preprocessor),
                ("model", RandomForestRegressor(
                    n_estimators=20,
                    max_depth=14,
                    min_samples_leaf=3,
                    random_state=42,
                    n_jobs=1
                ))
            ]),
            func=np.log1p,
            inverse_func=np.expm1
        ),
    }

    results = []
    predictions = {}
    fitted_models = {}

    for name, model in models.items():
        metrics, pred = evaluate_model(model, X_train, y_train, X_test, y_test)
        metrics["model"] = name
        results.append(metrics)
        predictions[name] = pred
        fitted_models[name] = model

    result_df = pd.DataFrame(results).set_index("model").sort_values("RMSE")
    result_df.to_csv(model_dir / "engineered_model_comparison.csv", encoding="utf-8-sig")

    best_name = result_df.index[0]
    best_pred = predictions[best_name]

    # 保存最优模型预测曲线
    save_prediction_plot(
        y_test,
        best_pred,
        model_dir / "engineered_best_prediction_curve.png",
        f"Engineered modeling best prediction: {best_name}",
        max_points=500
    )

    # 保存预测明细
    pred_df = pd.DataFrame({
        "datetime": test_df["datetime"].values,
        "true_cnt": y_test.values,
        "pred_cnt": np.maximum(best_pred, 0)
    })
    pred_df.to_csv(model_dir / "best_model_predictions.csv", index=False, encoding="utf-8-sig")

    # 尝试输出特征重要性：仅对树模型有效
    try:
        best_model = fitted_models[best_name]
        inner_pipeline = best_model.regressor_
        final_model = inner_pipeline.named_steps["model"]
        if hasattr(final_model, "feature_importances_"):
            feature_names = inner_pipeline.named_steps["preprocess"].get_feature_names_out()
            importance_df = pd.DataFrame({
                "feature": feature_names,
                "importance": final_model.feature_importances_
            }).sort_values("importance", ascending=False)
            importance_df.to_csv(model_dir / "feature_importance.csv", index=False, encoding="utf-8-sig")

            top = importance_df.head(20).iloc[::-1]
            plt.figure(figsize=(10, 8))
            plt.barh(top["feature"], top["importance"])
            plt.title(f"Top 20 feature importance: {best_name}")
            plt.xlabel("importance")
            plt.tight_layout()
            plt.savefig(model_dir / "feature_importance_top20.png", dpi=200)
            plt.close()
    except Exception as e:
        print(f"    特征重要性输出跳过，原因：{e}")

    print("\n[4-10] 特征工程、编码、离散化、异常值处理、标准化和重新建模完成")
    print(result_df)
    print(f"    重新建模结果保存到：{model_dir}")

    return result_df


# =========================
# 主函数
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=str,
        default=None,
        help="共享单车小时数据 csv 路径，例如 hour.csv"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="results_bike_sharing_preprocessing",
        help="结果输出目录"
    )
    args = parser.parse_args()

    data_path = resolve_data_path(args.data)
    out_dir = ensure_dir(args.out)

    print("=" * 80)
    print("共享单车小时租赁数量预测：数据预处理完整流程")
    print("=" * 80)
    print(f"数据文件：{data_path}")
    print(f"输出目录：{out_dir.resolve()}")

    df = load_data(data_path)

    # 1. 数据预览
    save_data_overview(df, out_dir)

    # 2. 相关分析
    save_correlation_analysis(df, out_dir)

    # 3. 直接建模
    direct_result = direct_modeling(df, out_dir)

    # 4-10. 特征工程后重新建模
    engineered_result = engineered_modeling(df, out_dir)

    # 汇总直接建模与重新建模结果
    summary_dir = ensure_dir(out_dir / "summary")
    direct_result2 = direct_result.copy()
    direct_result2["stage"] = "direct_modeling"

    engineered_result2 = engineered_result.copy()
    engineered_result2["stage"] = "engineered_modeling"

    all_results = pd.concat([direct_result2, engineered_result2], axis=0)
    all_results = all_results.sort_values("RMSE")
    all_results.to_csv(summary_dir / "all_model_comparison.csv", encoding="utf-8-sig")

    print("\n" + "=" * 80)
    print("全部流程完成：模型对比结果")
    print("=" * 80)
    print(all_results)

    best_model_name = all_results.index[0]
    print("\n最优模型：", best_model_name)
    print("最优模型指标：")
    print(all_results.iloc[0])
    print(f"\n全部结果已保存到：{out_dir.resolve()}")

    print("\n建模注意事项：")
    print("1. casual 和 registered 已删除，因为它们相加就是 cnt，属于目标泄漏。")
    print("2. 本脚本采用时间顺序切分训练集/测试集，避免用未来数据预测过去。")
    print("3. 重新建模阶段包含：特征编码、离散化、新特征构造、异常值处理、标准化。")
    print("4. 如果课程要求随机划分，可把 time_order_train_test_split 改成 train_test_split。")


if __name__ == "__main__":
    main()
