import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

os.makedirs("charts", exist_ok=True)
sns.set_style("whitegrid")

df = pd.read_csv("city_day.csv", parse_dates=["Date"])
print("Raw shape:", df.shape)
print("Cities:", df["City"].nunique())
print(df.isna().mean().sort_values(ascending=False).head(8))

df = df.dropna(subset=["AQI"])
print("Shape after dropping null AQI:", df.shape)

pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
df[pollutants] = df.groupby("City")[pollutants].transform(lambda s: s.fillna(s.median()))

df["Year"] = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Season"] = df["Month"].map(
    lambda m: "Winter" if m in (11, 12, 1, 2)
    else "Summer" if m in (3, 4, 5, 6)
    else "Monsoon" if m in (7, 8, 9)
    else "Post-monsoon"
)

city_avg = df.groupby("City")["AQI"].mean().sort_values(ascending=False)
print("\nTop 10 cities by average AQI:")
print(city_avg.head(10).round(1))

plt.figure(figsize=(9, 6))
city_avg.head(10).sort_values().plot(kind="barh", color="#444")
plt.title("Top 10 cities by average AQI (2015-2020)")
plt.xlabel("Average AQI")
plt.tight_layout()
plt.savefig("charts/top_cities.png", dpi=150)
plt.close()

delhi = df[df["City"] == "Delhi"]

monthly = delhi.groupby("Month")["AQI"].mean()
plt.figure(figsize=(9, 4))
monthly.plot(marker="o", color="#222")
plt.title("Delhi: average AQI by month")
plt.xlabel("Month")
plt.ylabel("AQI")
plt.xticks(range(1, 13))
plt.tight_layout()
plt.savefig("charts/delhi_monthly.png", dpi=150)
plt.close()

season = delhi.groupby("Season")["AQI"].mean().sort_values(ascending=False)
print("\nDelhi average AQI by season:")
print(season.round(1))

yearly = delhi.groupby("Year")["AQI"].mean()
print("\nDelhi average AQI by year:")
print(yearly.round(1))

corr = delhi[pollutants + ["AQI"]].corr()
print("\nDelhi: correlation of each pollutant with AQI:")
print(corr["AQI"].drop("AQI").sort_values(ascending=False).round(2))

plt.figure(figsize=(7, 5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="Greys")
plt.title("Delhi: pollutant correlation with AQI")
plt.tight_layout()
plt.savefig("charts/delhi_corr.png", dpi=150)
plt.close()

bucket = delhi["AQI_Bucket"].value_counts(normalize=True) * 100
print("\nDelhi: % of days by AQI category:")
print(bucket.round(1))

lock = df[(df["Month"].isin([3, 4, 5])) & (df["Year"].isin([2019, 2020]))]
lock_cmp = lock.groupby(["City", "Year"])["AQI"].mean().unstack()
lock_cmp["change_pct"] = (lock_cmp[2020] - lock_cmp[2019]) / lock_cmp[2019] * 100
lock_cmp = lock_cmp.dropna().sort_values("change_pct")

print("\nLockdown: biggest AQI falls (%):")
print(lock_cmp.head(10).round(1))
print("Average change across cities (%):", round(lock_cmp["change_pct"].mean(), 1))

plt.figure(figsize=(9, 6))
lock_cmp["change_pct"].plot(kind="barh", color="#555")
plt.title("AQI change, Mar-May 2020 vs Mar-May 2019 (%)")
plt.xlabel("% change")
plt.tight_layout()
plt.savefig("charts/lockdown_change.png", dpi=150)
plt.close()


conn = sqlite3.connect(":memory:")
df.to_sql("aqi", conn, index=False)

q1 = """
SELECT City, ROUND(AVG(AQI), 1) AS avg_aqi,
       SUM(CASE WHEN AQI_Bucket IN ('Poor','Very Poor','Severe') THEN 1 ELSE 0 END) AS bad_days
FROM aqi
GROUP BY City
ORDER BY bad_days DESC
LIMIT 10
"""
print("\nSQL: cities with most Poor-or-worse days")
print(pd.read_sql(q1, conn))

q2 = """
SELECT Year, Season, ROUND(AVG("PM2.5"), 1) AS pm25
FROM aqi
WHERE City = 'Delhi'
GROUP BY Year, Season
ORDER BY Year, pm25 DESC
"""
print("\nSQL: Delhi PM2.5 by year and season")
print(pd.read_sql(q2, conn))

print("\nDone. Charts saved in the charts/ folder.")
