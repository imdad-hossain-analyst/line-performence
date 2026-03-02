import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

df = pd.read_excel("final.xlsx")



st.set_page_config(page_title="Production Stability Dashboard", layout="wide")

st.title("📊 Production Stability & Anomaly Dashboard")

# Month selector



# --- Month filter ---

df['month'] = df['date'].dt.strftime('%B-%Y') 

months = ["All"] + sorted(df['month'].unique().tolist())
selected_month = st.selectbox("Select Month", months)

Floor = ["All"] + sorted(df['Floor'].unique().tolist())
selected_floor = st.selectbox("Select Floor", Floor)


# Line selector
col1 = st.columns(1)[0]
with col1:
    selected_line = st.selectbox(
        "Select Line",
        options=["All"] + sorted(df['Line'].unique().tolist())
    )

# ---- FILTERING ----
filtered_df = df.copy()


floor_risk = (
    filtered_df.groupby('Floor')['Deviation_%']
      .apply(lambda x: x.abs().mean())
      .reset_index(name='Avg_Abs_Deviation')
)

floor_risk['Floor_Risk_Rank'] = floor_risk['Avg_Abs_Deviation'].rank(
    ascending=False, method='dense'
)


if selected_month != "All":
    filtered_df = filtered_df[filtered_df['month'] == selected_month]

if selected_floor != "All":
    filtered_df = filtered_df[filtered_df['Floor'] == selected_floor]

if selected_line != "All":
    filtered_df = filtered_df[filtered_df['Line'] == selected_line]


line_risk = (
    filtered_df.groupby(['Line' , 'Floor'])['Deviation_%']
      .apply(lambda x: x.abs().mean())
      .reset_index(name='Avg_Abs_Deviation')
)

line_risk['Line_Risk_Rank'] = line_risk['Avg_Abs_Deviation'].rank(
    ascending=False, method='dense'
)

# -----------------------------
# KPI CARDS
# -----------------------------
k1, k2, k3, k4 , k5 = st.columns(5)

k1.metric("📈 Line Achievement %",
          round(filtered_df['Achievement_%'].mean(), 1))

k2.metric("⚖️ Avg Stability Score",
          round(filtered_df['Stability_Score'].mean(), 2))

k3.metric("🔺 High Spikes",
          (filtered_df['Anomaly_Flag'] == 'High Spike').sum())

k4.metric("🔻 Low Drops",
          (filtered_df['Anomaly_Flag'] == 'Low Drop').sum())

k5.metric("📊 Total Records",
          filtered_df.shape[0])

# -----------------------------
# TIME SERIES
# -----------------------------
st.subheader("📈 Achievement vs 3-Day Moving Average")

fig_ts = px.line(
    filtered_df,
    x="date",
    y=["Achievement_%", "3_Day_Line_Avg_Achievement_%"],
    markers=True
)

st.plotly_chart(fig_ts, use_container_width=True)

# -----------------------------
# ANOMALY TABLE
# -----------------------------
st.subheader("🚨 Anomaly & Management Action")


filtered_df['date'] = filtered_df['date'].dt.date
st.dataframe(
    filtered_df[
        ['date','Pg No','Line','MM Output','TTL','Achievement_%','3_Day_Line_Avg_Achievement_%','Line_average',
         'Deviation_%','Anomaly_Flag',
         'Stability_Score','Management_Action']
    ].sort_values('date', ascending=True),
    use_container_width=True
)

# -----------------------------
# LINE RISK RANKING
# -----------------------------
st.subheader("⚠️ Line Risk Ranking")

fig_risk = px.bar(
    line_risk.sort_values('Line_Risk_Rank'),
    x="Line",
    y="Avg_Abs_Deviation",
    text="Line_Risk_Rank"
)

st.plotly_chart(fig_risk, use_container_width=True)

# -----------------------------
# BUYER IN LINE
# -----------------------------
st.subheader("🛍 Buyer Distribution Across Lines")

temp = filtered_df.groupby(['Pg code','Line' ]).size().reset_index(name='Count')



line_order = sorted(temp['Line'].unique())
temp['Line'] = pd.Categorical(temp['Line'], categories=line_order, ordered=True)
temp = temp.sort_values('Line')

fig = go.Figure()

for pg in temp['Pg code'].unique():
    df_stack = temp[temp['Pg code'] == pg]
    
    fig.add_trace(go.Bar(
        x=df_stack['Line'],
        y=df_stack['Count'],
        name=pg
    ))

fig.update_layout(
    xaxis_title='Line',
    yaxis_title='Count',
    barmode='stack'
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# FLOOR RISK RANKING
# -----------------------------
st.subheader("⚠️ Floor Risk Ranking")

fig_risk1 = px.bar(
    floor_risk.sort_values('Floor_Risk_Rank'),
    x="Floor",
    y="Avg_Abs_Deviation",
    text="Floor_Risk_Rank"
)

st.plotly_chart(fig_risk1, use_container_width=True)


# -----------------------------
# 🔥 LINE RISK HEATMAP
# -----------------------------
st.subheader("🔥 Line Stability Heatmap")

heatmap_data = (
    filtered_df.assign(abs_dev = filtered_df['Deviation_%'].abs())
        .groupby(['Floor','Line'])['abs_dev']
        .mean()
        .reset_index()
)

heatmap_pivot = heatmap_data.pivot(index="Floor", columns="Line", values="abs_dev")

fig_heat = px.imshow(
    heatmap_pivot,
    text_auto=True,
    aspect="auto",
    color_continuous_scale="Reds"
)

st.plotly_chart(fig_heat, use_container_width=True)


# -----------------------------
# 🤖 AUTO INSIGHT
# -----------------------------
st.subheader("🤖 Insights")

if not line_risk.empty:
    worst_line = line_risk.sort_values("Avg_Abs_Deviation", ascending=False).iloc[0]
    best_line = line_risk.sort_values("Avg_Abs_Deviation").iloc[0]

    st.markdown(f"""
    ⚠️ **Highest Risk Line:** Line {worst_line['Line']} (Floor {worst_line['Floor']})  
    Avg Deviation: {round(worst_line['Avg_Abs_Deviation'],2)}

    ✅ **Most Stable Line:** Line {best_line['Line']} (Floor {best_line['Floor']})  
    Avg Deviation: {round(best_line['Avg_Abs_Deviation'],2)}

    📊 Overall Stability Score: {round(filtered_df['Stability_Score'].mean(),2)}

    💡 Recommendation:
    - Investigate root cause in high risk line
    - Review operator efficiency
    - Check machine downtime
    """)




# -----------------------------
# 🚨 SMART ALERT SYSTEM
# -----------------------------
st.subheader("🚨 Stability Alert System")

threshold = st.slider("Set Deviation Alert Threshold", 0.0, 20.0, 5.0)

alert_lines = (
    filtered_df.assign(abs_dev = filtered_df['Deviation_%'].abs())
        .groupby("Line")["abs_dev"]
        .mean()
        .reset_index()
)

high_risk_lines = alert_lines[alert_lines["abs_dev"] > threshold]

if not high_risk_lines.empty:
    st.error("⚠️ High Risk Lines Detected!")
    st.dataframe(high_risk_lines, use_container_width=True)
else:
    st.success("✅ All Lines Stable Under Threshold")

