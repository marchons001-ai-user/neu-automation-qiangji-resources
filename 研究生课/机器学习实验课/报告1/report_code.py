import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression, SGDRegressor, Ridge, Lasso
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures
from timeit import default_timer


def load_data(test_rate):
    """Load Boston housing data from a local CSV file."""
    df = pd.read_csv("boston_house_prices.csv")
    if "MEDV" not in df.columns:
        raise ValueError("CSV file must contain a MEDV column as target.")

    X = df.drop("MEDV", axis=1).values.astype(np.float64)
    y = df["MEDV"].values.astype(np.float64)
    return train_test_split(X, y, test_size=test_rate, random_state=42)


def standardize(X_train, X_test):
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1
    return (X_train - mean) / std, (X_test - mean) / std


class LinearRegressionNumpy:
    def __init__(self, num_features):
        np.random.seed(42)
        self.w = np.random.randn(num_features)
        self.b = 0.0

    def forward(self, X):
        return X.dot(self.w) + self.b

    @staticmethod
    def loss(y_pred, y_true):
        return np.mean((y_pred - y_true) ** 2)

    @staticmethod
    def gradient(X, y_true, y_pred):
        n = X.shape[0]
        dw = X.T @ (y_pred - y_true) / n
        db = np.mean(y_pred - y_true)
        return dw, db

    def update(self, dw, db, eta):
        self.w -= eta * dw
        self.b -= eta * db

    def train_bgd(self, X_train, y_train, epochs=1000, eta=0.01):
        losses = []
        for _ in range(epochs):
            y_pred = self.forward(X_train)
            losses.append(self.loss(y_pred, y_train))
            dw, db = self.gradient(X_train, y_train, y_pred)
            self.update(dw, db, eta)
        return losses


def evaluate(name, model, X_train, y_train, X_test, y_test):
    start = default_timer()
    model.fit(X_train, y_train)
    elapsed = default_timer() - start
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    print(f"{name}:")
    print(f"  time: {elapsed:.4f}s")
    print(
        f"  train MSE={mean_squared_error(y_train, train_pred):.2f}, "
        f"R2={r2_score(y_train, train_pred):.2f}"
    )
    print(
        f"  test  MSE={mean_squared_error(y_test, test_pred):.2f}, "
        f"R2={r2_score(y_test, test_pred):.2f}"
    )
    return test_pred


def run_experiment(test_rate=0.45):
    X_train, X_test, y_train, y_test = load_data(test_rate)
    X_train_scaled, X_test_scaled = standardize(X_train, X_test)

    custom_model = LinearRegressionNumpy(X_train_scaled.shape[1])
    start = default_timer()
    losses = custom_model.train_bgd(X_train_scaled, y_train)
    custom_time = default_timer() - start
    custom_train_pred = custom_model.forward(X_train_scaled)
    custom_test_pred = custom_model.forward(X_test_scaled)

    print(f"test rate = {test_rate}")
    print("custom BGD:")
    print(f"  time: {custom_time:.4f}s")
    print(
        f"  train MSE={mean_squared_error(y_train, custom_train_pred):.2f}, "
        f"R2={r2_score(y_train, custom_train_pred):.2f}"
    )
    print(
        f"  test  MSE={mean_squared_error(y_test, custom_test_pred):.2f}, "
        f"R2={r2_score(y_test, custom_test_pred):.2f}"
    )

    lr_pred = evaluate(
        "sklearn LinearRegression",
        LinearRegression(),
        X_train_scaled,
        y_train,
        X_test_scaled,
        y_test,
    )
    sgd_pred = evaluate(
        "sklearn SGDRegressor",
        SGDRegressor(max_iter=1000, tol=1e-3, penalty=None, eta0=0.01, random_state=42),
        X_train_scaled,
        y_train,
        X_test_scaled,
        y_test,
    )

    plt.figure(figsize=(12, 8))
    plt.subplot(2, 2, 1)
    plt.plot(losses)
    plt.title("Training Loss")
    plt.xlabel("Epochs")
    plt.ylabel("MSE")

    for idx, (pred, label, marker) in enumerate(
        [(custom_test_pred, "Custom BGD", "o"), (lr_pred, "LinearRegression", "x"), (sgd_pred, "SGDRegressor", "^")],
        start=2,
    ):
        plt.subplot(2, 2, idx)
        plt.scatter(y_test, pred, marker=marker, alpha=0.5, label=label)
        plt.plot([10, 50], [10, 50], "k--", lw=2)
        plt.xlabel("True Values")
        plt.ylabel("Predictions")
        plt.legend()

    plt.tight_layout()
    plt.savefig("RESULT.png", dpi=180)
    return X_train_scaled, X_test_scaled, y_train, y_test


def run_extensions(X_train, X_test, y_train, y_test):
    ridge = Ridge(alpha=1.0)
    lasso = Lasso(alpha=0.1, max_iter=10000)
    poly = PolynomialFeatures(degree=2, include_bias=False)

    evaluate("Ridge", ridge, X_train, y_train, X_test, y_test)
    evaluate("Lasso", lasso, X_train, y_train, X_test, y_test)

    X_train_poly = poly.fit_transform(X_train)
    X_test_poly = poly.transform(X_test)
    evaluate("Polynomial degree=2", LinearRegression(), X_train_poly, y_train, X_test_poly, y_test)


if __name__ == "__main__":
    data = run_experiment(test_rate=0.45)
    run_extensions(*data)
