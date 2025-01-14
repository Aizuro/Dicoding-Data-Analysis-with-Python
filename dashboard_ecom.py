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
    product_summary = df.groupby('product_category_name').agg(
        total_orders=('order_id', 'count'),
        total_revenue=('price', 'sum')
    ).sort_values(by='total_orders', ascending=False)

    top5_product_summary = product_summary.head(5)

    return top5_product_summary

def create_relation_deliveryNreview_df(df):
    max_delivery_speed = all_df['delivery_speed'].max()  # Nilai maksimum dari delivery_speed

    return max_delivery_speed

def create_rfm_df(df):
    rfm_df = df.groupby(by="customer_id", as_index=False).agg({
        "customer" : "first",
        "order_purchase_timestamp": "max", #mengambil tanggal order terakhir
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

def create_top_sellers_df(df):
    cluster_df = all_df.groupby(by="seller", as_index=False).agg({
    "order_id": "count",
    "price": "sum"
    })
    cluster_df.columns = ["seller", "total_orders", "total_revenue"]
    
    return cluster_df

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
        label='Rentang Waktu',min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date]
    )

main_df = all_df[(all_df["order_purchase_timestamp"] >= str(start_date)) & 
                (all_df["order_purchase_timestamp"] <= str(end_date))]

daily_orders_df = create_daily_orders_df(main_df)
top_product_df = create_top_product_df(main_df)
relation_deliveryNreview_df = create_relation_deliveryNreview_df(main_df)
rfm_df = create_rfm_df(main_df)
geospatial_df = create_geospatial_df(customerNseller_loc_df)
top_sellers_df = create_top_sellers_df(main_df)

st.header('Dicoding Collection Dashboard :sparkles:')

# PERFORMACE OVERVIEW
st.subheader('Performance Overview')
 
col1, col2 = st.columns(2)
 
with col1:
    total_orders = daily_orders_df.order_count.sum()
    st.metric("Total orders", value=total_orders)
 
with col2:
    total_revenue = format_currency(daily_orders_df.revenue.sum(), "AUD", locale='es_CO') 
    st.metric("Total Revenue", value=total_revenue)
 
fig, ax = plt.subplots(figsize=(16, 8))
ax.plot(
    daily_orders_df["order_purchase_timestamp"],
    daily_orders_df["order_count"],
    marker='o', 
    linewidth=2,
    color="#90CAF9"
)
ax.tick_params(axis='y', labelsize=20)
ax.tick_params(axis='x', labelsize=15)
 
st.pyplot(fig)

# TOP PRODUCTS ORDER (Pertanyaan 1)
st.subheader('Top Products (Order)')

fig, ax = plt.subplots(figsize=(15, 6))
sns.barplot(
    x=top_product_df.index,
    y=top_product_df['total_orders'],
    palette="viridis"
)
plt.title("Jumlah Pesanan Berdasarkan Kategori Produk", fontsize=14)
plt.xticks(rotation=45)
plt.ylabel("Jumlah Pesanan")
plt.xlabel("Kategori Produk")
st.pyplot(fig)

fig, ax = plt.subplots(figsize=(8, 8))
top_product_df['total_revenue'].plot(kind='pie', autopct='%1.1f%%', colormap='viridis', startangle=90)
plt.title("Kontribusi Pendapatan per Kategori Produk")
plt.ylabel(None)
st.pyplot(fig)

# Relationship between Delivery Speed and Review Score (Pertanyaan 2)
st.subheader("Delivery Speed and Review Score Relation")
bins = [0, 25, 50, 100, relation_deliveryNreview_df + 1]  # Tambahkan nilai maksimum + 1 ke bins
labels = ['Cepat', 'Normal', 'Lambat', 'Sangat Lambat']

all_df['delivery_category'] = pd.cut(
    all_df['delivery_speed'],
    bins=bins,
    labels=labels,
    include_lowest=True
)

fig, ax = plt.subplots(figsize=(10, 6))
sns.boxplot(
    x='delivery_category',
    y='review_score',
    data=all_df,
    palette='viridis'
)
plt.title("Distribusi Skor Ulasan Berdasarkan Kategori Pengiriman", fontsize=14)
plt.xlabel("Kategori Pengiriman")
plt.ylabel("Skor Ulasan")
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
 
sns.barplot(y="recency", x="customer", data=rfm_df.sort_values(by="recency", ascending=False).head(3), palette=colors, ax=ax[0])
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

# TOP SELLER
st.subheader("Seller Performance")
q_orders = top_sellers_df['total_orders'].quantile([0.25, 0.5, 0.75]).to_dict()
q_revenue = top_sellers_df['total_revenue'].quantile([0.25, 0.5, 0.75]).to_dict()

# Fungsi clustering berdasarkan kuartil untuk total_revenue
def quartile_revenue_cluster(revenue):
    if revenue <= q_revenue[0.25]:
        return 'Low Revenue'
    elif q_revenue[0.25] < revenue <= q_revenue[0.5]:
        return 'Moderate Revenue'
    elif q_revenue[0.5] < revenue <= q_revenue[0.75]:
        return 'High Revenue'
    else:
        return 'Very High Revenue'

# Fungsi clustering berdasarkan kuartil untuk total_orders
def quartile_order_cluster(orders):
    if orders <= q_orders[0.25]:
        return 'Low Orders'
    elif q_orders[0.25] < orders <= q_orders[0.5]:
        return 'Moderate Orders'
    elif q_orders[0.5] < orders <= q_orders[0.75]:
        return 'High Orders'
    else:
        return 'Very High Orders'

# Menentukan cluster berdasarkan kuartil
top_sellers_df['revenue_cluster'] = top_sellers_df['total_revenue'].apply(quartile_revenue_cluster)
top_sellers_df['order_cluster'] = top_sellers_df['total_orders'].apply(quartile_order_cluster)

# Menggabungkan cluster kuartil
def combine_quartile_clusters(row):
    return f"{row['revenue_cluster']} & {row['order_cluster']}"

top_sellers_df['combined_cluster'] = top_sellers_df.apply(combine_quartile_clusters, axis=1)

# Visualisasi Bubble Chart
fig, ax = plt.subplots(figsize=(12, 8))
sns.scatterplot(
    x='total_orders',
    y='total_revenue',
    size='total_revenue',  # Ukuran bubble berdasarkan total revenue
    hue='combined_cluster',  # Warna berdasarkan cluster gabungan
    data=top_sellers_df,
    style='combined_cluster',
    sizes=(100, 1000),  # Ukuran minimum dan maksimum bubble
    alpha=0.8
)

# Menambahkan label nama seller pada bubble
for i in range(top_sellers_df.shape[0]):
    plt.text(
        x=top_sellers_df['total_orders'].iloc[i], 
        y=top_sellers_df['total_revenue'].iloc[i],
        s=top_sellers_df['seller'].iloc[i],  # Nama seller
        fontsize=8
    )

# Pengaturan plot
plt.title('Clustering Berdasarkan Kuartil: Total Orders dan Total Revenue', fontsize=14)
plt.xlabel('Total Orders')
plt.ylabel('Total Revenue')
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Cluster')
plt.grid(True)
st.pyplot(fig)

# GEOSPATIAL ANALYSIS (Rata-rata jarak dari kota ke kota lain)
# st.subheader("Kecepatan Pengiriman Rata-Rata dari Kota ke Kota Lain")
# folium_static(geospatial_df)

st.caption('Copyright (c) Dicoding 2023')
