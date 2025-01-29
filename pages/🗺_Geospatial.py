import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import folium
from streamlit_folium import folium_static

def create_geospatial_df(df):
    df['seller_location'] = df.apply(lambda row: Point(row['lon_y'], row['lat_y']), axis=1)
    df['customer_location'] = df.apply(lambda row: Point(row['lon_x'], row['lat_x']), axis=1)

    # Konversi ke GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry='seller_location', crs="EPSG:4326")
    gdf['delivery_line'] = gdf.apply(lambda row: LineString([row['seller_location'], row['customer_location']]), axis=1)

    m = folium.Map(location=[-34.6037, -58.3816], zoom_start=6)

    # Tambahkan garis penghubung dan tampilkan kecepatan pengiriman
    for _, row in gdf.iterrows():
        line = folium.PolyLine(
            locations=[
                [row['lat_y'], row['lon_y']],
                [row['lat_x'], row['lon_x']]
            ],
            color='blue' if row['delivery_speed'] <= 3 else 'red',  # Warna berdasarkan kecepatan pengiriman
            weight=3,
            tooltip=f"From: {row['seller_city']} To: {row['customer_city']} | Speed: {row['delivery_speed']} days"
        )
        line.add_to(m)

    # Tambahkan marker untuk kota penjual dan pembeli
    for _, row in gdf.iterrows():
        folium.Marker(
            location=[row['lat_y'], row['lon_y']],
            popup=f"Seller: {row['seller_city']}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)

        folium.Marker(
            location=[row['lat_x'], row['lon_x']],
            popup=f"Customer: {row['customer_city']}",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)

    return m

customerNseller_loc_df = pd.read_csv("customer_seller_loc.csv")

geospatial_df = create_geospatial_df(customerNseller_loc_df)

customer_city = customerNseller_loc_df["customer_city"].unique().tolist()
with st.sidebar:
    selected_data = st.multiselect("Select City", customer_city, customer_city)

st.subheader("Geospatial")
folium_static(geospatial_df)