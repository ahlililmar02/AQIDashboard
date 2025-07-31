
import streamlit as st
import pandas as pd
import psycopg2
import folium
from streamlit_folium import st_folium
import numpy as np
from scipy.spatial import cKDTree
from folium import CircleMarker
import geopandas as gpd
from shapely.geometry import Point
from sklearn.metrics import r2_score
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

st.markdown("""
	<style>
		html, body, .stApp {
			max-height: 1000px;
			overflow-y: auto;
		}
	</style>
""", unsafe_allow_html=True)


# 🔽 Navbar
# Sidebar navigation


with st.sidebar:
    page = option_menu(
        "Main Menu",
        ["Air Quality Monitor", "Download Data", "AOD Derived PM2.5 Heatmap"],
        icons=["bar-chart", "download", "cloud"],
        menu_icon="cast",
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
@st.cache_data
def load_data():
	creds = st.secrets["postgres"]

	conn = psycopg2.connect(
		host=creds["host"],
		port=creds["port"],
		dbname=creds["dbname"],
		user=creds["user"],
		password=creds["password"]
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


if page == "Air Quality Monitor":
	st.title("Real-Time Air Quality Dashboard")

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

	for _, row in df_latest.iterrows():
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

	st.subheader("🗺️ Air Quality Jakarta Map")
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
						<div style="font-size: 20px; font-weight: 600; margin-bottom: 10px;">
							Latest from {latest_row["station"]}
						</div>
					""", unsafe_allow_html=True)
					# 📊 Scorecards
					
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
								<h3 style='font-size:18px;margin:0;'>{label}</h3>
								<p style='font-size:24px;margin:0;'>{value}</p>
							</div>
						"""

					# Column 1: Time
					col1.markdown(card_style(label="Time", value=time_value), unsafe_allow_html=True)

					# Column 2: AQI with color
					col2.markdown(card_style(label="AQI", value=f"{aqi_value:.0f}", color=color), unsafe_allow_html=True)

					# Column 3: PM2.5
					col3.markdown(card_style(label="PM2.5", value=f"{pm_value:.1f} µg/m³"), unsafe_allow_html=True)

					# Optional spacing
					st.markdown("<br>", unsafe_allow_html=True)
			
			with st.container(key="time_series"):
					# 📈 Time series
					st.markdown("""
					<div style="font-size: 22px; font-weight: 600; margin-bottom: 10px;">
						Time Series
					</div>
					""", unsafe_allow_html=True)

					st.line_chart(station_df_today.set_index("time")[["aqi", "PM2.5"]], height=290,use_container_width=True)
			
			from datetime import timedelta
			
			start_of_week = today - timedelta(days=today.weekday())  # Monday
			end_of_week = start_of_week + timedelta(days=6)          # Sunday

			# 🧹 Filter data for the current station and week
			mask = (station_df["time"] >= start_of_week) & (station_df["time"] <= end_of_week)

			
			
			# 📈 Display as bar chart
			with st.container(key="bar_chart"):
				st.markdown("""
					<div style="font-size: 22px; font-weight: 600; margin-bottom: 10px;">
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
				<div style="font-size: 22px; font-weight: 600; margin-bottom: 10px;">
					Highest AQI Today
				</div>
				""", unsafe_allow_html=True)

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
						margin-bottom: 8px;
						box-shadow: 0 1px 2px rgba(0,0,0,0.08);
					">
						<div style="font-size: 16px; font-weight: bold;">
							#{i} {station}
						</div>
						<div style="font-size: 14px;">
							AQI: <b>{int(aqi)}</b> | PM2.5: <b>{pm25:.1f} µg/m³</b>
						</div>
					</div>
					""", unsafe_allow_html=True)

			

			with st.container(key="right_box_low"):
				# Bottom 5
				st.markdown("""
				<div style="font-size: 22px; font-weight: 600; margin-bottom: 10px;">
					Lowest AQI Today
				</div>
				""", unsafe_allow_html=True)
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
						margin-bottom: 8px;
						box-shadow: 0 1px 2px rgba(0,0,0,0.08);
					">
						<div style="font-size: 16px; font-weight: bold;">
							#{i} {station}
						</div>
						<div style="font-size: 14px;">
							AQI: <b>{int(aqi)}</b> | PM2.5: <b>{pm25:.1f} µg/m³</b>
						</div>
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

	st.html(f"<style>{css2}</style>")
	with st.container(key="about"):
			st.markdown("""
				### What is the Air Quality Index (AQI)?
				The **Air Quality Index (AQI)** is a standardized indicator used to communicate how polluted the air currently is or how polluted it is forecast to become. Here's how to interpret the AQI values:

				<style>
				.aqi-table {
					border-collapse: collapse;
					width: 100%;
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
					<th>Level of Health Concern</th>
				</tr>
				<tr>
					<td>0 – 50</td>
					<td style="background-color:#009966; color:white;">Good</td>
				</tr>
				<tr>
					<td>51 – 100</td>
					<td style="background-color:#ffde33;">Moderate</td>
				</tr>
				<tr>
					<td>101 – 150</td>
					<td style="background-color:#ff9933;">Unhealthy for Sensitive Groups</td>
				</tr>
				<tr>
					<td>151 – 200</td>
					<td style="background-color:#cc0033; color:white;">Unhealthy</td>
				</tr>
				<tr>
					<td>201 – 300</td>
					<td style="background-color:#660099; color:white;">Very Unhealthy</td>
				</tr>
				<tr>
					<td>301+</td>
					<td style="background-color:#7e0023; color:white;">Hazardous</td>
				</tr>
				</table>
			""", unsafe_allow_html=True)


# 📁 PAGE 2: FILTER & DOWNLOAD
elif page == "Download Data":
	st.title("Download Air Quality Data")
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
			station_filter = st.multiselect("Station", options=df["station"].unique())
			date_range = st.date_input("Date range", [])
			submit = st.form_submit_button("Filter")

	filtered = df.copy()
	if station_filter:
		filtered = filtered[filtered["station"].isin(station_filter)]
	if len(date_range) == 2:
		start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
		filtered = filtered[(filtered["time"] >= start) & (filtered["time"] <= end)]

	st.write(f"Filtered rows: {len(filtered)}")
	st.dataframe(filtered)

	csv = filtered.to_csv(index=False).encode('utf-8')
	st.download_button("Download as CSV", data=csv, file_name="air_quality_filtered.csv", mime="text/csv")




elif page == "AOD Derived PM2.5 Heatmap":
	st.title("AOD Derived PM2.5 Heatmap Over Jakarta")

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
		selected_date = st.selectbox("📅 Select a date", available_dates)
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
	st.subheader(f"{source_name} on {selected_date}")

	# Show map
	with st.container(key="heatmap"):
		st_folium(m, height=500, use_container_width=True)

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
				r2 = r2_score(matched_real, matched_est)
				mae = np.abs(matched_real - matched_est).mean()

				# Reuse the same DataFrame with 'lat,lon' index
				scatter_df = pd.DataFrame({
					"latitude": gdf_matched["latitude_right"],
					"longitude": gdf_matched["longitude_right"],
					"Real PM2.5": gdf_matched["PM2.5"],
					"AOD-Derived PM2.5": gdf_matched["pm25_estimated"]
				})

				# Add lat,lon label
				scatter_df["lat,lon"] = scatter_df["latitude"].round(4).astype(str) + ", " + scatter_df["longitude"].round(4).astype(str)
				scatter_df.set_index("lat,lon", inplace=True)

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
		st.subheader("Comparison (Matched Spatial + Date)")

		with st.container(key="scatter"):
			# Results
			# Score card layout
			st.markdown("<br>", unsafe_allow_html=True)
			col1, col2, col3 = st.columns(3)

			with col1:
				st.metric(label="R² Score", value=f"{r2:.3f}")
			with col2:
				st.metric(label="Mean Absolute Error", value=f"{mae:.2f} µg/m³")
			with col3:
				st.metric(label="Sample Size", value=f"{len(matched_real):,}")
			# ✅ Explicitly select y-columns to avoid mixed-type error
			st.markdown("<br>", unsafe_allow_html=True)

			st.scatter_chart(scatter_df[["Real PM2.5", "AOD-Derived PM2.5"]],height=400, use_container_width=True)

