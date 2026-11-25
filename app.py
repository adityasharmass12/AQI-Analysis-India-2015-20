import os
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="India Air Quality Dashboard", layout="wide")

POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
BAD = ["Poor", "Very Poor", "Severe"]
SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-monsoon"]
BUCKET_ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]


def get_season(m):
    if m in (11, 12, 1, 2):
        return "Winter"
    if m in (3, 4, 5, 6):
        return "Summer"
    if m in (7, 8, 9):
        return "Monsoon"
    return "Post-monsoon"


@st.cache_data
def prep(raw):
    df = raw.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["AQI"])
    df[POLLUTANTS] = df.groupby("City")[POLLUTANTS].transform(lambda s: s.fillna(s.median()))
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.month
    df["Season"] = df["Month"].map(get_season)
    return df


st.title("India Air Quality Dashboard")
st.caption("Daily AQI data for Indian cities, 2015 to 2020")

if os.path.exists("city_day.csv"):
    raw = pd.read_csv("city_day.csv")
else:
    up = st.file_uploader("Upload city_day.csv", type="csv")
    if up is None:
        st.stop()
    raw = pd.read_csv(up)

df = prep(raw)

cities = sorted(df["City"].unique())
city = st.sidebar.selectbox("City", cities, index=cities.index("Delhi") if "Delhi" in cities else 0)
y_min, y_max = int(df["Year"].min()), int(df["Year"].max())
years = st.sidebar.slider("Years", y_min, y_max, (y_min, y_max))

d = df[(df["City"] == city) & (df["Year"].between(*years))]
if d.empty:
    st.warning("No data for this selection.")
    st.stop()

worst = d.loc[d["AQI"].idxmax()]
bad_pct = d["AQI_Bucket"].isin(BAD).mean() * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric("Average AQI", f"{d['AQI'].mean():.0f}")
c2.metric("Worst day", f"{worst['AQI']:.0f}", worst["Date"].strftime("%d %b %Y"), delta_color="off")
c3.metric("Poor or worse days", f"{bad_pct:.1f}%")
c4.metric("Average PM2.5", f"{d['PM2.5'].mean():.0f}")

t1, t2, t3, t4, t5 = st.tabs(["Trend", "Seasons", "Pollutants", "City comparison", "Lockdown impact"])

with t1:
    m = (
        d.assign(ym=d["Date"].dt.to_period("M").dt.to_timestamp())
        .groupby("ym")["AQI"].mean().reset_index()
    )
    fig = px.line(m, x="ym", y="AQI", title=f"{city}: monthly average AQI")
    fig.update_layout(xaxis_title="", yaxis_title="AQI")
    st.plotly_chart(fig, use_container_width=True)

with t2:
    a, b = st.columns(2)
    s = d.groupby("Season")["AQI"].mean().reindex(SEASON_ORDER).reset_index()
    a.plotly_chart(px.bar(s, x="Season", y="AQI", title="Average AQI by season"), use_container_width=True)
    mo = d.groupby("Month")["AQI"].mean().reset_index()
    fig = px.line(mo, x="Month", y="AQI", markers=True, title="Average AQI by month")
    fig.update_xaxes(dtick=1)
    b.plotly_chart(fig, use_container_width=True)

with t3:
    a, b = st.columns(2)
    corr = d[POLLUTANTS + ["AQI"]].corr().round(2)
    a.plotly_chart(
        px.imshow(corr, text_auto=True, color_continuous_scale="Greys", title="Correlation with AQI"),
        use_container_width=True,
    )
    bk = d["AQI_Bucket"].value_counts().reindex(BUCKET_ORDER).dropna().reset_index()
    bk.columns = ["Category", "Days"]
    b.plotly_chart(px.bar(bk, x="Category", y="Days", title="Days by AQI category"), use_container_width=True)

with t4:
    top_n = st.slider("Number of cities to show", 5, 20, 10)
    yr = df[df["Year"].between(*years)]
    rank = (
        yr.groupby("City")
        .agg(avg_aqi=("AQI", "mean"), bad_days=("AQI_Bucket", lambda x: x.isin(BAD).sum()))
        .sort_values("avg_aqi", ascending=False)
        .head(top_n)
        .reset_index()
    )
    fig = px.bar(rank.sort_values("avg_aqi"), x="avg_aqi", y="City", orientation="h", title="Highest average AQI")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(rank.round(1), use_container_width=True, hide_index=True)

with t5:
    st.write("March to May 2020 (lockdown) vs March to May 2019")
    lock = df[df["Month"].isin([3, 4, 5]) & df["Year"].isin([2019, 2020])]
    cmp = lock.groupby(["City", "Year"])["AQI"].mean().unstack().dropna()
    cmp["change_pct"] = (cmp[2020] - cmp[2019]) / cmp[2019] * 100
    cmp = cmp.sort_values("change_pct").reset_index()
    fig = px.bar(cmp, x="change_pct", y="City", orientation="h", title="AQI change (%)")
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
    if city in cmp["City"].values:
        row = cmp[cmp["City"] == city].iloc[0]
        st.info(f"{city}: AQI {row[2019]:.0f} (2019) to {row[2020]:.0f} (2020), a {row['change_pct']:.1f}% change.")