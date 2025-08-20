
import streamlit as st
import pandas as pd
import os
import psycopg2
import folium
from streamlit_folium import st_folium
import numpy as np
from scipy.spatial import cKDTree
from folium import CircleMarker
import geopandas as gpd
from shapely.geometry import Point
from sklearn.metrics import mean_squared_error
from streamlit_option_menu import option_menu


# Set wide layout
st.set_page_config(
	page_title="Air Quality Dashboard",
	layout="wide",
	initial_sidebar_state="auto",
	menu_items={
		'Get Help': 'https://www.extremelycoolapp.com/help',
		'Report a bug': "https://www.extremelycoolapp.com/bug",
		'About': "# This is a header. This is an *extremely* cool app!"
	}
)

# Inject custom CSS to zoom page to 80%
#st.markdown(	""" <style>	html, body, [class*="css"]  {		zoom: 0.8;		}</style>""",unsafe_allow_html=True)

with st.sidebar:
	st.title("Jakarta Air Quality Dashboard")  # Title without icon

	page = option_menu(
		menu_title=None,
		options=["Air Quality Monitor", "Download Data", "AOD Derived PM2.5 Heatmap", "About"],
		icons=["bar-chart", "download", "cloud", "info-circle"],
		default_index=0
	)




st.markdown("""
	<style>
		body {
			background-color: #f0f0f0;
		}
		.stApp {
			background-color: #f0f0f0;
		}
	</style>
""", unsafe_allow_html=True)

# Connect and read data
@st.cache_data(ttl=3600)  # 3600 seconds = 1 hour
def load_data():
	conn = psycopg2.connect(
		host=os.environ.get("DB_HOST"),
		port=os.environ.get("DB_PORT"),
		dbname=os.environ.get("DB_NAME"),
		user=os.environ.get("DB_USER"),
		password=os.environ.get("DB_PASS")
	)

	query = """
		SELECT *
		FROM tes
	"""
	query2 = """
		SELECT date, latitude, longitude, mean_aod, pm25_estimated
		FROM daily_data
	"""
	

	df = pd.read_sql(query, conn)
	df_pm25 = pd.read_sql(query2, conn)
	conn.close()
	return df, df_pm25


# 🚀 LOAD DATA
df, df_pm25 = load_data()

# Filter for today
today = pd.Timestamp.now().normalize()
df_today = df[df["time"] >= today]

# Group average per station
df_today_avg = df_today.groupby("station")[["aqi", "PM2.5"]].mean().reset_index()
df_today_avg = df_today_avg[df_today_avg["aqi"].notna() & (df_today_avg["aqi"] != 0)]

with open("static/style.css") as f:
	st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if page == "Air Quality Monitor":
	st.markdown(f"""
							<div style="font-size: 24px; font-weight: 600; margin-bottom: 10px;">
								Real-Time Air Quality Dashboard
							</div>
						""", unsafe_allow_html=True)
						
	css3 = """
	.st-key-about {
		background-color: white;
		padding: 20px;
		border-radius: 10px;
		margin-bottom: 20px;
	}
	"""

	st.html(f"<style>{css3}</style>")

	with st.container(key="about"):
			st.markdown("""
			<div style="font-size:16px; font-weight:500; margin-bottom:10px;">
					What is Air Quality Index (AQI)?
				</div>
			   
			<div style="font-size:14px; font-weight:300; margin-bottom:10px;">
			Air Quality Index (AQI) is an indicator used to communicate how polluted the air currently is, and what associated health effects might be a concern for you. The AQI focuses on health effects you may experience within a few hours or days after breathing polluted air. Here's how to interpret the AQI values:
			</div>
			<style>
				.aqi-table {
					border-collapse: collapse;
					width: 100%;
					font-size: 12px;
				}
				.aqi-table th, .aqi-table td {
					border: 1px solid #ddd;
					padding: 8px;
					text-align: center;
				}
				.aqi-table th {
					background-color: #f2f2f2;
				}
			</style>

			<table class="aqi-table">
			<tr>
				<th>AQI Range</th>
				<th>PM2.5 (µg/m³)</th>
				<th>Level of Health Concern</th>
			</tr>
			<tr>
				<td>0 – 50</td>
				<td>0.0 – 12.0</td>
				<td style="background-color:#66c2a4;">Good</td>
			</tr>
			<tr>
				<td>51 – 100</td>
				<td>12.1 – 35.4</td>
				<td style="background-color:#ffe066;">Moderate</td>
			</tr>
			<tr>
				<td>101 – 150</td>
				<td>35.5 – 55.4</td>
				<td style="background-color:#ffb266;">Unhealthy for Sensitive Groups</td>
			</tr>
			<tr>
				<td>151 – 200</td>
				<td>55.5 – 150.4</td>
				<td style="background-color:#ff6666;">Unhealthy</td>
			</tr>
			<tr>
				<td>201 – 300</td>
				<td>150.5 – 250.4</td>
				<td style="background-color:#b266ff;">Very Unhealthy</td>
			</tr>
			<tr>
				<td>301+</td>
				<td>250.5+</td>
				<td style="background-color:#d2798f;">Hazardous</td>
			</tr>
			</table>
			""", unsafe_allow_html=True)

	
	import datetime
	
	# Get today's date (without time)
	today = pd.to_datetime(datetime.date.today())

	# Filter to only today's data

	# ✅ Get latest data per station *from today's data only*
	df_latest = df.sort_values("time").groupby("station", as_index=False).last()
	df_latest = df_latest[df_latest["time"].dt.normalize() == today]

	# ✅ Add color
	def get_rgba_color(aqi, alpha=0.7):
		if pd.isna(aqi): return f"rgba(200, 200, 200, {alpha})"
		elif aqi <= 50: return f"rgba(0, 228, 0, {alpha})"
		elif aqi <= 100: return f"rgba(255, 255, 0, {alpha})"
		elif aqi <= 150: return f"rgba(255, 126, 0, {alpha})"
		elif aqi <= 200: return f"rgba(255, 0, 0, {alpha})"
		elif aqi <= 300: return f"rgba(143, 63, 151, {alpha})"
		else: return f"rgba(126, 0, 35, {alpha})"

	df_latest["color"] = df_latest["aqi"].apply(get_rgba_color)

	css = """
	.st-key-selector_box {
		background-color: white;
		padding: 20px;
		border-radius: 10px;
		margin-bottom: 20px;
	}
	"""
	st.html(f"<style>{css}</style>")

	# 🔘 Selectors with custom container
	with st.container(key="selector_box"):
		sourceid_list = df_latest["sourceid"].unique()

		# Set default for source ID (e.g., first one or a specific value)
		default_source = sourceid_list[0]  # or 'SOME_SOURCE_ID' if you know the ID
		selected_source = st.selectbox("🛰️ Select Source ID", sourceid_list, index=list(sourceid_list).index(default_source))

		stations_in_source = df_latest[df_latest["sourceid"] == selected_source]["station"].unique()

		# Set default for station (e.g., first one or a specific station)
		default_station = stations_in_source[0]
		selected_station = st.selectbox("📍 Select Station", stations_in_source, index=list(stations_in_source).index(default_station))

		selected_row = df_latest[df_latest["station"] == selected_station].iloc[0]
		center = [selected_row["latitude"], selected_row["longitude"]]


	st.markdown("<br>", unsafe_allow_html=True)

	# 🗺️ Build folium map
	m = folium.Map(
		location=center,
		zoom_start=13,
		control_scale=True,
		scrollWheelZoom=True,
		tiles="CartoDB positron",
	)

	from folium.features import DivIcon

	# Filter hanya data dari selected_source
	filtered_df = df_latest[df_latest["sourceid"] == selected_source]

	# Loop untuk semua station dalam source itu
	for _, row in filtered_df.iterrows():
		aqi = row["aqi"]
		color = row["color"]
		label = f"{int(aqi)}" if pd.notna(aqi) else "?"

		is_selected = row["station"] == selected_station
		size = 28 if is_selected else 24
		font_size = "11px" if is_selected else "10px"
		border = "2px solid white" if is_selected else "none"

		folium.Marker(
			location=[row["latitude"], row["longitude"]],
			icon=DivIcon(
				icon_size=(size, size),
				icon_anchor=(size // 2, size // 2),
				html=f"""
				<div style='
					background-color:{color};
					color:white;
					font-size:{font_size};
					font-weight:bold;
					border-radius:50%;
					width:{size}px;
					height:{size}px;
					text-align:center;
					line-height:{size}px;
					box-shadow: 0 0 2px #333;
					border:{border};'>
					{label}
				</div>
				""",
			),
			tooltip=f"{row['station']}",
			popup=folium.Popup(
				f"""
				<div style='font-size: 13px; line-height: 1.5'>
					<b>Station:</b> {row['station']}<br/>
					<b>Latest Time:</b> {row['time'].strftime('%Y-%m-%d %H:%M')}<br/>
					<b>AQI:</b> {row['aqi']:.0f}<br/>
					<b>PM2.5:</b> {row['PM2.5']:.1f} µg/m³
				</div>
				""",
				max_width=500,
			),
		).add_to(m)

	# 🌍 Show map full-width
	css2 = """
	.st-key-map {
		background-color: white;
		padding: 20px;
		border-radius: 10px;
		margin-bottom: 20px;
	}
	"""
	st.html(f"<style>{css2}</style>")

	with st.container(key="map"):
		
		map_output = st_folium(m, height=500,use_container_width=True, returned_objects=["last_object_clicked"])

		# 📘 Legend
		legend_html = """
		<div style="display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px;">
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(0, 228, 0, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Good (0–50)
			</div>
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(255, 255, 0, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Moderate (51–100)
			</div>
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(255, 126, 0, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Unhealthy for SG (101–150)
			</div>
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(255, 0, 0, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Unhealthy (151–200)
			</div>
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(143, 63, 151, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Very Unhealthy (201–300)
			</div>
			<div style="display: flex; align-items: center; gap: 4px;">
				<div style="background-color: rgba(126, 0, 35, 0.7); width: 12px; height: 12px; border: 1px solid #000;"></div> Hazardous (301+)
			</div>
		</div>
		"""
		st.markdown(legend_html, unsafe_allow_html=True)
		st.markdown("<br>", unsafe_allow_html=True)

	if map_output and map_output["last_object_clicked"]:
		lat_click = map_output["last_object_clicked"]["lat"]
		lon_click = map_output["last_object_clicked"]["lng"]
		df_latest["distance"] = ((df_latest["latitude"] - lat_click)**2 + (df_latest["longitude"] - lon_click)**2)
		nearest_station = df_latest.sort_values("distance").iloc[0]["station"]
		selected_station = nearest_station
		st.success(f"📌 Selected from map: {selected_station}")

	# 7. Now compute station data (based on final selected_station)
	station_df = df[df["station"] == selected_station].sort_values("time")
	station_df_today = df_today[df_today["station"] == selected_station].sort_values("time")

	latest_row = station_df.iloc[-1]

	# 8. Split into 3 columns: left = metrics + chart, middle = space, right = top 5 AQI
	left_col, middle_col, right_col = st.columns([2.5, 0.15, 1.8])

	st.html("""
	<style>
	.st-key-left_box, .st-key-right_box,.st-key-right_box_low, .st-key-time_series, .st-key-bar_chart {
		background-color: white;
		padding: 20px;
		border-radius: 12px;
		box-shadow: 0 2px 4px rgba(0,0,0,0.1);
		margin-bottom: 20px;
	}
	</style>
	""")

	with st.container():
		with left_col:
			
			with st.container(key="left_box"):
					st.markdown(f"""
						<div style="font-size: 16px; font-weight: 600; margin-bottom: 10px;">
							Latest from {latest_row["station"]}
						</div>
					""", unsafe_allow_html=True)
					# 📊 Scorecards
					st.markdown("<br>", unsafe_allow_html=True)
					col1, col2, col3 = st.columns(3)

					# Styling values
					time_value = latest_row["time"].strftime('%H:%M')
					aqi_value = latest_row["aqi"]
					pm_value = latest_row["PM2.5"]
					color = get_rgba_color(aqi_value)

					def card_style(label, value, color="#ffffff"):
						return f"""
							<div style="
								background-color:{color};
								padding:20px;
								border-radius:12px;
								text-align:center;
							">
								<p style='font-size:14px;margin:0;'>{label}</p>
								<p style='font-size:14px;margin:0;'>{value}</p>
							</div>
						"""
					st.markdown("<br>", unsafe_allow_html=True)

					# Column 1: Time
					col1.markdown(card_style(label="Time", value=time_value), unsafe_allow_html=True)

					# Column 2: AQI with color
					col2.markdown(card_style(label="AQI", value=f"{aqi_value:.0f}", color=color), unsafe_allow_html=True)

					# Column 3: PM2.5
					col3.markdown(card_style(label="PM2.5", value=f"{pm_value:.1f} µg/m³"), unsafe_allow_html=True)

					# Optional spacing
			
			with st.container(key="time_series"):
					# 📈 Time series
					st.markdown("""
					<div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">
						Time Series
					</div>
					""", unsafe_allow_html=True)
					st.markdown("<br>", unsafe_allow_html=True)

					st.line_chart(station_df_today.set_index("time")[["aqi", "PM2.5"]], height=280,use_container_width=True)
			
			from datetime import timedelta
			
			start_of_week = today - timedelta(days=today.weekday())  # Monday
			end_of_week = start_of_week + timedelta(days=6)          # Sunday

			# 🧹 Filter data for the current station and week
			mask = (station_df["time"] >= start_of_week) & (station_df["time"] <= end_of_week)

			
			
			# 📈 Display as bar chart
			with st.container(key="bar_chart"):
				st.markdown("""
					<div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">
						Daily Average AQI and PM2.5 This Week
					</div>
				""", unsafe_allow_html=True)
				
				import altair as alt
				
				weekly_df = station_df.loc[mask].copy()

				# 1️⃣ Extract date (no hour)
				weekly_df["date"] = weekly_df["time"].dt.date  # strips hour

				# 2️⃣ Group by that date
				daily_avg = weekly_df.groupby("date")[["aqi", "PM2.5"]].mean().reset_index()

				# 3️⃣ Optional: Rename column for PM2.5
				daily_avg.rename(columns={"PM2.5": "PM2_5"}, inplace=True)

				# Ensure 'date' is a datetime, then normalize to remove the time
				daily_avg["date"] = pd.to_datetime(daily_avg["date"]).dt.normalize()

				# 🧼 Clean and prepare the data
				daily_avg["date"] = pd.to_datetime(daily_avg["date"]).dt.normalize()
				daily_avg = daily_avg[
					daily_avg["aqi"].notna() & (daily_avg["aqi"] != 0) &
					daily_avg["PM2_5"].notna() & (daily_avg["PM2_5"] != 0)
				]
				daily_avg["weekday"] = daily_avg["date"].dt.strftime("%a")  # e.g., Mon, Tue

				# 📊 Melt to long format for dual bar chart
				chart_df = daily_avg[["weekday", "PM2_5", "aqi"]].melt(id_vars="weekday", var_name="Metric", value_name="Value")

				# Define custom colors
				custom_color = alt.Scale(
					domain=["PM2_5", "aqi"],
					range=["#1f77b4", "#87CEFA"]  # dark blue for PM2.5, light blue for AQI
				)

				# Bar chart
				bar_chart = alt.Chart(chart_df).mark_bar().encode(
					x=alt.X("weekday:N", title="Day of Week", sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
					y=alt.Y("Value:Q", title="Value (µg/m³ or AQI)"),
					color=alt.Color("Metric:N", scale=custom_color),
					tooltip=["Metric", "Value"]
				).properties(
					height=280,
					width=800,
				)

				st.markdown("<br>", unsafe_allow_html=True)
				st.altair_chart(bar_chart,use_container_width=True)

		# RIGHT COLUMN: Top 5 stations
		with right_col:

			with st.container(key="right_box"):
				st.markdown("""
				<div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">
					Highest AQI Today
				</div>
				""", unsafe_allow_html=True)
				st.markdown("<br>", unsafe_allow_html=True)
				df_today_avg["color"] = df_today_avg["aqi"].apply(get_rgba_color)

				# Top 5
				top5_today = df_today_avg.sort_values("aqi", ascending=False).head(5)
				top5_today = top5_today.rename(columns={"PM2.5": "pm25"})

				for i, row in enumerate(top5_today.itertuples(index=False), start=1):
					station = row.station
					aqi = row.aqi
					pm25 = row.pm25
					color = row.color

					st.markdown(f"""
					<div style="
						background-color: #fdfdfd;
						border-left: 5px solid {color};
						padding: 16px 10px;
						border-radius: 8px;
						margin-bottom: 10px;
						box-shadow: 0 1px 2px rgba(0,0,0,0.08);
					">
						<div style="font-size: 14px; font-weight: bold;">
							#{i} {station}
						</div>
						<div style="font-size: 12px;">
							AQI: <b>{int(aqi)}</b> | PM2.5: <b>{pm25:.1f} µg/m³</b>
						</div>
					</div>
					""", unsafe_allow_html=True)

			

			with st.container(key="right_box_low"):
				# Bottom 5
				st.markdown("""
				<div style="font-size: 18px; font-weight: 600; margin-bottom: 10px;">
					Lowest AQI Today
				</div>
				""", unsafe_allow_html=True)
				st.markdown("<br>", unsafe_allow_html=True)
				low5_today = df_today_avg.sort_values("aqi", ascending=True).head(5)
				low5_today = low5_today.rename(columns={"PM2.5": "pm25"})

				for i, row in enumerate(low5_today.itertuples(index=False), start=1):
					station = row.station
					aqi = row.aqi
					pm25 = row.pm25
					color = row.color

					st.markdown(f"""
					<div style="
						background-color: #fdfdfd;
						border-left: 5px solid {color};
						padding: 16px 10px;
						border-radius: 8px;
						margin-bottom: 10px;
						box-shadow: 0 1px 2px rgba(0,0,0,0.08);
					">
						<div style="font-size: 14px; font-weight: bold;">
							#{i} {station}
						</div>
						<div style="font-size: 12px;">
							AQI: <b>{int(aqi)}</b> | PM2.5: <b>{pm25:.1f} µg/m³</b>
						</div>
					</div>
					""", unsafe_allow_html=True)
					
					
	


# 📁 PAGE 2: FILTER & DOWNLOAD
elif page == "Download Data":
	st.markdown(f"""
							<div style="font-size: 24px; font-weight: 600; margin-bottom: 10px;">
								Download Air Quality Data
							</div>
						""", unsafe_allow_html=True)
	css = """
		.st-key-selector_box {
			background-color: white;
			padding: 20px;
			border-radius: 10px;
			margin-bottom: 20px;
		}
		"""
	st.html(f"<style>{css}</style>")

	# 🔘 Selectors with custom container
	with st.container(key="selector_box"):
		with st.form("filter_form"):
			# Source ID selection (above station)
			source_id = st.selectbox("Source ID", options=sorted(df["sourceid"].unique()))
		
			# Filter stations based on selected source_id
			station_options = df[df["sourceid"] == source_id]["station"].unique()
			station_filter = st.multiselect("Station", options=sorted(station_options))
		
			# Date range filter
			date_range = st.date_input("Date range", [])
		
			# Submit button
			submit = st.form_submit_button("Filter")


	filtered = df.copy()
	if station_filter:
		filtered = filtered[filtered["station"].isin(station_filter)]
	if len(date_range) == 2:
		start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
		filtered = filtered[(filtered["time"] >= start) & (filtered["time"] <= end)]

	st.write(f"Filtered rows: {len(filtered)}")
	# Pagination setup
	page_size = 1000
	max_page = (len(filtered) - 1) // page_size + 1

	# Initialize session state for page number
	if "page_num" not in st.session_state:
		st.session_state.page_num = 1

	# Layout: Centered pagination bar
	spacer1, col_prev, col_info, col_next, spacer2 = st.columns([1, 1, 2, 1, 1])

	with col_prev:
		if st.button("Prev", use_container_width=True) and st.session_state.page_num > 1:
			st.session_state.page_num -= 1

	with col_info:
		st.markdown(
			f"<div style='text-align:center; font-weight:bold;'>Page {st.session_state.page_num} of {max_page}</div>",
			unsafe_allow_html=True,
		)

	with col_next:
		if st.button("Next", use_container_width=True) and st.session_state.page_num < max_page:
			st.session_state.page_num += 1

	# Paginate the dataframe
	start = (st.session_state.page_num - 1) * page_size
	end = start + page_size
	st.dataframe(filtered.iloc[start:end])


	csv = filtered.to_csv(index=False).encode('utf-8')
	st.download_button("Download as CSV", data=csv, file_name="air_quality_filtered.csv", mime="text/csv")




elif page == "AOD Derived PM2.5 Heatmap":
	st.markdown(f"""
							<div style="font-size: 24px; font-weight: 600; margin-bottom: 10px;">
								AOD Derived PM2.5 Heatmap Over Jakarta
							</div>
						""", unsafe_allow_html=True)

	css4 = """
	.st-key-about_aod, {
		background-color: white;
		padding: 20px;
		border-radius: 10px;
		margin-bottom: 20px;
	}
	"""

	st.html(f"<style>{css4}</style>")		

	# Convert and filter df
	df['time'] = pd.to_datetime(df['time'])
	df_10 = df[df['time'].dt.time == pd.to_datetime("10:00").time()]  # keep only rows at 10:00
	df_10['date'] = df_10['time'].dt.date  # convert to just the date

	# Convert df_pm25['date'] if needed
	df_pm25['date'] = pd.to_datetime(df_pm25['date'])

	# Filter dates with ≥75 valid AOD-derived rows
	date_counts = df_pm25.dropna(subset=["latitude", "longitude", "pm25_estimated"]) \
						 .groupby(df_pm25['date'].dt.date).size()
	filtered_dates = date_counts[date_counts >= 75].index.tolist()
	available_dates = sorted(filtered_dates, reverse=True)

	css = """
	.st-key-selector_box {
		background-color: white;
		padding: 20px;
		border-radius: 10px;
		margin-bottom: 20px;
	}
	"""
	st.html(f"<style>{css}</style>")

	# 🔘 Selectors with custom container
	with st.container(key="selector_box"):
		st.markdown("""
		<div style="font-size:16px; font-weight:500; margin-bottom:10px;">
			PM2.5 Prediction Using Aerosol Optical Depth
		</div>

		<div style="font-size:14px; font-weight:300; margin-bottom:10px;">
			This heatmap visualizes the predicted PM2.5 concentrations, which are a key indicator of ambient air quality and potential health risks. Satellite-derived Aerosol Optical Depth (AOD) has been extensively studied as a proxy for surface-level PM2.5. For instance, Paciorek et al. (2008) identified statistically significant spatiotemporal associations between AOD retrievals and ground-level PM2.5 in the eastern United States. In our current setup, we utilize a traditional machine learning algorithm, <b>XGBoost</b>, with AOD, meteorological parameters, and land-use features as predictors. The model is retrained weekly using the latest observed PM2.5 data to support continuous validation and improvement.
		</div>

		<div style="font-size:14px; font-weight:300; margin-bottom:10px;">
			The heatmap is generated from tabular spatial data that has been converted into <b>GeoDataFrames</b> using the <b>GeoPandas</b> library, with a spatial resolution of approximately 800 meters. Model performance is evaluated by comparing predicted and observed PM2.5 values from monitoring stations using the <b>Mean Squared Error (MSE)</b> metric.
		</div>
		""", unsafe_allow_html=True)
		
		st.markdown("<br>", unsafe_allow_html=True)


		selected_date = st.selectbox("📅 Select a date", available_dates)
		st.markdown("<br>", unsafe_allow_html=True)
		heatmap_type = st.radio("🛰️ Select Heatmap Source", ["AOD Derived", "Real"], horizontal=True)
		# Filter and prepare data
		if heatmap_type == "AOD Derived":
			selected_df = df_pm25[df_pm25['date'].dt.date == selected_date]
			selected_df = selected_df.dropna(subset=["latitude", "longitude", "pm25_estimated"])
			heat_data = selected_df[["latitude", "longitude", "pm25_estimated"]].values.tolist()
		else:  # Real
			selected_df = df_10[df_10['date'] == selected_date]
			selected_df = selected_df.dropna(subset=["latitude", "longitude", "PM2.5"])
			heat_data = selected_df[["latitude", "longitude", "PM2.5"]].values.tolist()

		# Map setup
		m = folium.Map(location=[-6.2, 106.9], zoom_start=11, tiles="CartoDB positron")

		# Add heatmap layer
		from folium.plugins import HeatMap
		HeatMap(heat_data, radius=15, blur=20, max_zoom=15).add_to(m)

		cssmap = """
			.st-key-heatmap {
				background-color: white;
				padding: 20px;
				border-radius: 10px;
				margin-bottom: 20px;
			}
			"""
		st.html(f"<style>{cssmap}</style>")

		source_name = "PM2.5 Estimated" if heatmap_type == "AOD Derived" else "PM2.5 Real"
		st.markdown(f"""
			<div style="font-size:16px; font-weight:500; margin-bottom:10px;">
				{source_name} on {selected_date}
			</div>
		""", unsafe_allow_html=True)


		# Show map
		#with st.container(key="heatmap"):
		st_folium(m, height=500, use_container_width=True)
		
		# Dynamic legend values
		if heatmap_type == "AOD Derived":
			pm_values = selected_df["pm25_estimated"].values
		else:
			pm_values = selected_df["PM2.5"].values

		pm_min = round(pm_values.min(), 1)
		pm_max = round(pm_values.max(), 1)

		# Legend HTML below the map
		legend_html = f"""
		<div style="
			background-color: white;
			padding: 5px;
			width: 400px;
			text-align: center;
		">
			<div style="display: flex; align-items: center; gap: 10px;">
				<b style="white-space: nowrap;"> PM2.5 (µg/m³) </b>
				<svg width="300" height="15">
					<defs>
						<linearGradient id="grad">
							<stop offset="0%" stop-color="#ADD8E6" />  
							<stop offset="33%" stop-color="#66c2a4" /> 
							<stop offset="66%" stop-color="#ffe066" /> 
							<stop offset="99%" stop-color="#ffb266" /> 
						</linearGradient>
					</defs>
					<rect x="0" y="0" width="300" height="15" fill="url(#grad)" />
				</svg>
			</div>
			<div style="display: flex; justify-content: space-between; font-size: 12px; margin-left: 90px;">
				<span>{pm_min}</span>
				<span>{pm_max}</span>
			</div>
		</div>
	"""


		st.markdown(legend_html, unsafe_allow_html=True)

	# Optional: show table
	csstab = """
		.st-key-table {
			background-color: white;
			padding: 20px;
			border-radius: 10px;
			margin-bottom: 20px;
		}
		"""
	st.html(f"<style>{csstab}</style>")
	with st.container(key="table"):
		with st.expander("Show raw data"):
			st.dataframe(selected_df)
	
	df_10['date'] = pd.to_datetime(df_10['time']).dt.date
	df_pm25['date'] = pd.to_datetime(df_pm25['date']).dt.date

	# Keep only rows with valid PM2.5 and coordinates
	real_df_all = df_10.dropna(subset=["latitude", "longitude", "PM2.5"])
	aod_df_all = df_pm25.dropna(subset=["latitude", "longitude", "pm25_estimated"])

	# Step 1: Filter to overlapping dates
	shared_dates = set(real_df_all['date']).intersection(set(aod_df_all['date']))
	real_df_all = real_df_all[real_df_all['date'].isin(shared_dates)]
	aod_df_all = aod_df_all[aod_df_all['date'].isin(shared_dates)]

	if real_df_all.empty or aod_df_all.empty:
		st.warning("No matching dates between real and AOD-derived datasets.")
	else:
		# Step 2: Convert to GeoDataFrames
		gdf_real = gpd.GeoDataFrame(
			real_df_all.copy(),
			geometry=gpd.points_from_xy(real_df_all["longitude"], real_df_all["latitude"]),
			crs="EPSG:4326"
		)
		gdf_aod = gpd.GeoDataFrame(
			aod_df_all.copy(),
			geometry=gpd.points_from_xy(aod_df_all["longitude"], aod_df_all["latitude"]),
			crs="EPSG:4326"
		)

		# Step 3: Reproject to meters
		gdf_real = gdf_real.to_crs(epsg=3857)
		gdf_aod = gdf_aod.to_crs(epsg=3857)

		# Step 4: Nearest spatial join (within 1.1 km)
		gdf_matched = gpd.sjoin_nearest(
			gdf_aod,
			gdf_real,
			how='inner',
			max_distance=880,
			distance_col="distance_m"
		)

		if gdf_matched.empty:
			st.warning("No spatially matched points found within 1.1 km.")
		else:
			# Step 5: Filter matched rows to have same date
			gdf_matched = gdf_matched[gdf_matched["date_left"] == gdf_matched["date_right"]]

			if gdf_matched.empty:
				st.warning("No spatiotemporal matches found (same date and within 1.1 km).")
			else:
				# Step 6: Extract matched values
				matched_real = gdf_matched["PM2.5"]
				matched_est = gdf_matched["pm25_estimated"]

				# Metrics
				mae = np.abs(matched_real - matched_est).mean()
				rmse = np.sqrt(mean_squared_error(matched_real, matched_est))

				scatter_df = pd.DataFrame({
					"station": gdf_matched["station"],
					"latitude": gdf_matched["latitude_right"].round(4),
					"longitude": gdf_matched["longitude_right"].round(4),
					"Real PM2.5": gdf_matched["PM2.5"],
					"AOD-Derived PM2.5": gdf_matched["pm25_estimated"]
				})
				
				scatter_df["Absolute Error"] = np.abs(scatter_df["Real PM2.5"] - scatter_df["AOD-Derived PM2.5"])
				scatter_df = scatter_df.sort_values(by="Absolute Error", ascending=True)
				scatter_df.set_index("station", inplace=True)

		csscat = """
				.st-key-scatter {
					background-color: white;
					padding: 20px;
					width: 100%;
					border-radius: 10px;
					margin-bottom: 20px;
				}
				"""
		st.html(f"<style>{csscat}</style>")
		st.markdown("""
			<div style="font-size:16px; font-weight:500; margin-bottom:10px;">
				Comparison
			</div> """, unsafe_allow_html=True)

		with st.container(key="scatter"):

			st.markdown("""
			<div style="font-size:16px; font-weight:500; margin-bottom:10px;">
				PM2.5 Prediction vs Actual PM2.5
			</div>

			<div style="font-size:14px; font-weight:300; margin-bottom:10px;">
				The prediction is evaluated using data from existing monitoring stations in Jakarta. 
				Given that the predicted PM2.5 data has an 800 m resolution, any monitoring station 
				located within the prediction radius is considered eligible to evaluate the predicted values.
			</div>
			""", unsafe_allow_html=True)

			# Results
			# Score card layout
			st.markdown("<br>", unsafe_allow_html=True)
			col1, col2, col3 = st.columns(3)

			with col1:
				st.metric(label="Root Mean Squared Error", value=f"{rmse:.3f}")
			with col2:
				st.metric(label="Mean Absolute Error", value=f"{mae:.2f} µg/m³")
			with col3:
				st.metric(label="Sample Size", value=f"{len(matched_real):,}")
			# ✅ Explicitly select y-columns to avoid mixed-type error
			st.markdown("<br>", unsafe_allow_html=True)

			st.scatter_chart(
				scatter_df.sort_values(by="Absolute Error", ascending=True)[["Real PM2.5", "AOD-Derived PM2.5"]],
				height=400,
				x_label="station",
				y_label="PM2.5",
				use_container_width=True
)

elif page == "About":
	csstab = """
		.st-key-about_site {
			background-color: white;
			padding: 20px;
			border-radius: 10px;
			margin-bottom: 20px;
			font-size: 14px;
			line-height: 1.6;
		}
	"""
	st.html(f"<style>{csstab}</style>")

	with st.container(key="about_site"):
		st.markdown("""
			<div style="font-size:18px; font-weight:600; margin-bottom:15px;">
				About This Project
			</div>

			<p>
			This platform compiles real-time and historical air quality data for Jakarta from four independent API sources. 
			The idea is so that users can explore and download the complete dataset for their own analysis or projects.  
			Beyond station measurements, the platform predicts PM2.5 concentrations for any latitude–longitude coordinate in Jakarta, 
			providing estimates in areas without direct monitoring coverage.
			</p>

			<div style="font-size:16px; font-weight:500; margin-top:20px; margin-bottom:10px;">
				Technical Overview
			</div>
			<ul>
				<li>Compile and process PM2.5 data from different APIs using <b>Python</b>.</li>
				<li><b>PostgreSQL</b> database for efficient data storage and retrieval.</li>
				<li>Containerized with <b>Docker</b> and deployed on an <b>Ubuntu</b> server.</li>
				<li>Built using <b>Streamlit</b> with integrated UI components and custom assets.</li>
				<li>Run machine learning model locally then upload it to the database.</li>
				<li>Served through <b>NGINX</b> for performance and reliability.</li>
			</ul>

			<div style="font-size:16px; font-weight:500; margin-top:20px; margin-bottom:10px;">
				References
			</div>
			<ul>
				<li>Xue, T., Zheng, Y., Geng, G., Zheng, B., Jiang, X., Zhang, Q., & He, K. (Year). "Fusing Observational, Satellite Remote Sensing and Air Quality Model Simulated Data to Estimate Spatiotemporal Variations of PM2.5 Exposure in China."</li>
				<li>Paciorek, C. J., et al. (2008). "Spatiotemporal associations between satellite-derived aerosol optical depth and PM2.5 in the eastern United States."</li>
				<li><a href="https://www.iqair.com/us/indonesia/jakarta" target="_blank">IQAir Jakarta</a></li>
				<li><a href="https://rendahemisi.jakarta.go.id/ispu" target="_blank">Jakarta Rendah Emisi</a></li>
				<li><a href="https://aqicn.org/network/menlhk/id/" target="_blank">Kementerian Lingkungan Hidup dan Kehutanan (KLHK)</a></li>
				<li><a href="https://id.usembassy.gov/u-s-embassy-jakarta-air-quality-monitor/" target="_blank">Udara Jakarta</a></li>
				<li><a href="https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5" target="_blank">ERA5 (ECMWF Reanalysis v5)</a></li>
				<li><a href="https://developers.google.com/earth-engine/datasets/tags/weather" target="_blank">Google Earth Engine</a></li>
			</ul>

			<div style="margin-top:20px; font-size:14px;">
				<p>This project is currently in an early stage of development and will improve over time.</p>
				<p>Connect with me on <a href="https://www.linkedin.com/in/yourprofile/" target="_blank">LinkedIn</a>.</p>
			</div>
			""", unsafe_allow_html=True)
