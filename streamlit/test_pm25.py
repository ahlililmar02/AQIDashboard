import streamlit as st
import pandas as pd
import leafmap.foliumap as leafmap

# Load and prepare data
df_pm25 = pd.read_csv("pm25_latest.csv", parse_dates=["date"])
df_pm25['date'] = pd.to_datetime(df_pm25['date'])

# Sidebar: Date selection
available_dates = sorted(df_pm25['date'].dt.date.unique(), reverse=True)
selected_date = st.selectbox("Select a date", available_dates)

# Filter by selected date
selected_df = df_pm25[df_pm25['date'].dt.date == selected_date]

# Clean data: Drop NaN and ensure numeric types
selected_df = selected_df.dropna(subset=["latitude", "longitude", "pm25_estimated"])
selected_df = selected_df.astype({"latitude": float, "longitude": float, "pm25_estimated": float})

# Page title
st.title("PM2.5 Heatmap over Jabodetabek (Leafmap)")
st.markdown(f"**Date selected:** {selected_date}")

# Create a Leafmap map
m = leafmap.Map(center=[-6.2, 106.8], zoom=9)

# Add Heatmap layer
m.add_heatmap(
    data=selected_df,
    latitude="latitude",
    longitude="longitude",
    value="pm25_estimated",
    name="PM2.5 Heatmap",
    radius=12,
)

# Optional: Add basemap, layer control
m.add_basemap("CartoDB.DarkMatter")
m.add_layer_control()

# Show the map in Streamlit
m.to_streamlit(height=600)

# Optional: Show raw data
with st.expander("Show raw data"):
    st.dataframe(selected_df)
