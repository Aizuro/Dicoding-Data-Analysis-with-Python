# Library
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
import geopandas as gpd
from shapely.geometry import Point, LineString
import folium
from streamlit_folium import folium_static
sns.set(style='dark')

# Function
def create_daily_orders_df(df):
    daily_orders_df = df.resample(rule='D', on='order_purchase_timestamp').agg({
        "order_id": "nunique",
        "price": "sum"
    })
    daily_orders_df = daily_orders_df.reset_index()
    daily_orders_df.rename(columns={
        "order_id": "order_count",
        "price": "revenue"
    }, inplace=True)
    
    return daily_orders_df


def create_top_product_df(df):
    product_summary = df.groupby('product_category_name_english').agg(
        total_orders=('order_id', 'count'),
        total_revenue=('price', 'sum')
    ).sort_values(by='total_orders', ascending=False)

    return product_summary


def create_relation_deliveryNreview_df(df):
    max_delivery_speed = df['delivery_speed'].max()  # Nilai maksimum dari delivery_speed

    return max_delivery_speed


def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_id", as_index=False).agg({
        "customer": "first",
        "order_purchase_timestamp": "max", # Mengambil tanggal order terakhir
        "order_id": "count",
        "price": "sum"
    })
    rfm_df.columns = ["customer_id", "customer", "max_order_timestamp", "frequency", "monetary"]
    
    rfm_df["max_order_timestamp"] = rfm_df["max_order_timestamp"].dt.date
    recent_date = df["order_purchase_timestamp"].dt.date.max()
    rfm_df["recency"] = rfm_df["max_order_timestamp"].apply(lambda x: (recent_date - x).days)
    rfm_df.drop("max_order_timestamp", axis=1, inplace=True)
    
    return rfm_df


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

# Dataset
all_df = pd.read_csv("all_data.csv")
customerNseller_loc_df = pd.read_csv("customer_seller_loc.csv")

datetime_columns = ["order_purchase_timestamp", "shipping_limit_date", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
all_df.sort_values(by="order_purchase_timestamp", inplace=True)
all_df.reset_index(inplace=True)
 
for column in datetime_columns:
    all_df[column] = pd.to_datetime(all_df[column])

# Komponen Filter
min_date = all_df["order_purchase_timestamp"].min()
max_date = all_df["order_purchase_timestamp"].max()
 
with st.sidebar:
    # Menambahkan logo perusahaan
    st.image("https://github.com/dicodingacademy/assets/raw/main/logo.png")
    
    # Mengambil start_date & end_date dari date_input
    start_date, end_date = st.date_input(
        label='Time Range', min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

# Filter berdasarkan waktu
main_df = all_df[(all_df["order_purchase_timestamp"] >= str(start_date)) & 
                (all_df["order_purchase_timestamp"] <= str(end_date))]

# Membuat data hasil filter
filtered_daily_orders_df = create_daily_orders_df(main_df)
top_product_df = create_top_product_df(main_df)
relation_deliveryNreview_df = create_relation_deliveryNreview_df(main_df)
rfm_df = create_rfm_df(main_df)
geospatial_df = create_geospatial_df(customerNseller_loc_df)

st.header('Dicoding Collection Dashboard :sparkles:')

# PERFORMANCE OVERVIEW
st.subheader('Performance Overview')
 
col1, col2 = st.columns(2)
 
with col1:
    total_orders = filtered_daily_orders_df.order_count.sum()
    st.metric("Total orders", value=total_orders)
 
with col2:
    total_revenue = format_currency(filtered_daily_orders_df.revenue.sum(), "AUD", locale='es_CO') 
    st.metric("Total Revenue", value=total_revenue)
 
fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    filtered_daily_orders_df["order_purchase_timestamp"],
    filtered_daily_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#90CAF9"
)
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)
 
st.pyplot(fig)

# TOP PRODUCTS ORDER (Pertanyaan 1)
st.subheader('Top Products (Order)')

fig, ax = plt.subplots(nrows=1, ncols=2, figsize=(24, 6))

colors = ["#72BCD4", "#D3D3D3", "#D3D3D3", "#D3D3D3", "#D3D3D3"]

sns.barplot(x="total_orders", y="product_category_name_english", data=top_product_df.head(5), palette=colors, ax=ax[0])
ax[0].set_ylabel(None)
ax[0].set_xlabel(None)
ax[0].set_title("Best Performing Product", loc="center", fontsize=15)
ax[0].tick_params(axis ='y', labelsize=12)

sns.barplot(x="total_orders", y="product_category_name_english", data=top_product_df.sort_values(by="total_orders", ascending=True).head(5), palette=colors, ax=ax[1])
ax[1].set_ylabel(None)
ax[1].set_xlabel(None)
ax[1].invert_xaxis()
ax[1].yaxis.set_label_position("right")
ax[1].yaxis.tick_right()
ax[1].set_title("Worst Performing Product", loc="center", fontsize=15)
ax[1].tick_params(axis='y', labelsize=12)

plt.suptitle("Best and Worst Performing Product by Number of Orders", fontsize=20)
st.pyplot(fig)

# Pie Chart: Kontribusi pendapatan per kategori
fig, ax = plt.subplots(figsize=(8, 8))
top5 = top_product_df.head(5)
top5['total_revenue'].plot(kind='pie', autopct='%1.1f%%', colormap='summer', startangle=90)
plt.title("Revenue Contribution from Top 5 Product Categories")
plt.ylabel(None)
st.pyplot(fig)

# Relationship between Delivery Speed and Review Score (Pertanyaan 2)
st.subheader("Delivery Speed and Review Score Relation")

fast = relation_deliveryNreview_df[relation_deliveryNreview_df['delivery_category'] == 'Cepat']
normal = relation_deliveryNreview_df[relation_deliveryNreview_df['delivery_category'] == 'Normal']
slow = relation_deliveryNreview_df[relation_deliveryNreview_df['delivery_category'] == 'Lambat']
very_slow = relation_deliveryNreview_df[relation_deliveryNreview_df['delivery_category'] == 'Sangat Lambat']

col1, col2, col3, col4 = st.columns(4)

with col1:
    fast_score = fast.review_score.mean()
    st.metric("Fast", value=fast_score)
 
with col2:
    normal_score = normal.review_score.mean()
    st.metric("Fast", value=normal_score)

with col3:
    slow_score = slow.review_score.mean()
    st.metric("Fast", value=slow_score)

with col4:
    very_slow_score = very_slow.review_score.mean()
    st.metric("Fast", value=very_slow_score)
    
bins = [0, 25, 50, 100, relation_deliveryNreview_df + 1]  # Tambahkan nilai maksimum + 1 ke bins
labels = ['Fast', 'Normal', 'Slow', 'Very Slow']

main_df['delivery_category'] = pd.cut(
    main_df['delivery_speed'],
    bins=bins,
    labels=labels,
    include_lowest=True
)

fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(
    x='delivery_category',
    y='review_score',
    data=main_df,
    palette='viridis'
)
plt.title("Distribution of Review Scores by Delivery Category", fontsize=14)
plt.xlabel("Delivery Category")
plt.ylabel("Review Scores")
st.pyplot(fig)

# RFM
st.subheader("Best Customer Based on RFM Parameters")
 
col1, col2, col3 = st.columns(3)
 
with col1:
    avg_recency = round(rfm_df.recency.mean(), 1)
    st.metric("Average Recency (days)", value=avg_recency)
 
with col2:
    avg_frequency = round(rfm_df.frequency.mean(), 2)
    st.metric("Average Frequency", value=avg_frequency)
 
with col3:
    avg_frequency = format_currency(rfm_df.monetary.mean(), "AUD", locale='es_CO') 
    st.metric("Average Monetary", value=avg_frequency)
 
fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(60, 15))
colors = ["#90CAF9", "#90CAF9", "#90CAF9", "#90CAF9", "#90CAF9"]
 
sns.barplot(y="recency", x="customer", data=rfm_df.sort_values(by="recency", ascending=True).head(3), palette=colors, ax=ax[0])
ax[0].set_ylabel(None)
ax[0].set_xlabel("customer", fontsize=30)
ax[0].set_title("By Recency (days)", loc="center", fontsize=50)
ax[0].tick_params(axis='y', labelsize=40)
ax[0].tick_params(axis='x', labelsize=35)
 
sns.barplot(y="frequency", x="customer", data=rfm_df.sort_values(by="frequency", ascending=False).head(3), palette=colors, ax=ax[1])
ax[1].set_ylabel(None)
ax[1].set_xlabel("customer", fontsize=30)
ax[1].set_title("By Frequency", loc="center", fontsize=50)
ax[1].tick_params(axis='y', labelsize=30)
ax[1].tick_params(axis='x', labelsize=35)
 
sns.barplot(y="monetary", x="customer", data=rfm_df.sort_values(by="monetary", ascending=False).head(3), palette=colors, ax=ax[2])
ax[2].set_ylabel(None)
ax[2].set_xlabel("customer", fontsize=30)
ax[2].set_title("By Monetary", loc="center", fontsize=50)
ax[2].tick_params(axis='y', labelsize=30)
ax[2].tick_params(axis='x', labelsize=35)
 
st.pyplot(fig)

# GEOSPATIAL ANALYSIS (Rata-rata jarak dari kota ke kota lain)
st.subheader("Average Intercity Delivery Speed")
folium_static(geospatial_df)

st.caption('Copyright (c) Dicoding 2023')
