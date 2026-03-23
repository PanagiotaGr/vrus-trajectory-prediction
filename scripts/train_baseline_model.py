import csv
import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

path = os.path.expanduser("~/imptc_project/results/pedestrian_full_context.csv")

df = pd.read_csv(path)

# --- basic cleaning ---
df = df.dropna()

# --- encode categorical ---
df["nearest_type"] = df["nearest_type"].map({
    "vrus": 0,
    "vehicles": 1
})

# --- features ---
features = [
    "nearest_type",
    "nearest_dist",
    "n_neighbors_found"
]

X = df[features]
y = df["displacement"]

# --- split ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# --- model ---
model = RandomForestRegressor(n_estimators=50)
model.fit(X_train, y_train)

# --- evaluation ---
preds = model.predict(X_test)

mae = mean_absolute_error(y_test, preds)

print("MAE:", mae)
