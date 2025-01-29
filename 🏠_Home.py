# Library
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from babel.numbers import format_currency
import plotly.express as px
import plotly.graph_objs as go
sns.set(style='dark')

st.set_page_config(layout="wide")

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
        product_category_name_english=('product_category_name_english', 'first'),
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

# Dataset
all_df = pd.read_csv("all_data.csv")

datetime_columns = ["order_purchase_timestamp", "shipping_limit_date", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"]
all_df.sort_values(by="order_purchase_timestamp", inplace=True)
all_df.reset_index(inplace=True)
 
for column in datetime_columns:
    all_df[column] = pd.to_datetime(all_df[column])

# Komponen Filter
min_date = all_df["order_purchase_timestamp"].min()
max_date = all_df["order_purchase_timestamp"].max()
 
with st.sidebar:
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

#================================================= VISUALIZATION =======================================================#

# ------------------PERFORMANCE OVERVIEW------------------
st.subheader('Performance Overview')
 
col1, col2 = st.columns(2)

with col1:
    total_orders = filtered_daily_orders_df.order_count.sum()
    st.metric("Total Orders", value=total_orders)

with col2:
    total_revenue = format_currency(filtered_daily_orders_df.revenue.sum(), "AUD", locale='es_CO') 
    st.metric("Total Revenue", value=total_revenue)

# Membuat grafik menggunakan Plotly
fig = go.Figure()

# Menambahkan trace untuk grafik
fig.add_trace(go.Scatter(
    x=filtered_daily_orders_df["order_purchase_timestamp"],
    y=filtered_daily_orders_df["order_count"],
    mode='lines+markers',
    line=dict(width=2, color="#90CAF9"),
    marker=dict(size=8),
    hovertemplate='<b>Timestamp:</b> %{x}<br>' +
                  '<b>Order Count:</b> %{y}<br>' +
                  '<b>Total Revenue:</b> ' + format_currency(filtered_daily_orders_df.revenue.sum(), "AUD", locale='es_CO') + '<br>' +
                  '<extra></extra>'  # Ini menghilangkan teks tambahan
))

# Mengatur layout untuk grafik
fig.update_layout(
    title='Daily Orders Over Time',
    xaxis_title='Order Purchase Timestamp',
    yaxis_title='Order Count',
    xaxis_tickangle=-45,
    yaxis=dict(tickfont=dict(size=20)),
    xaxis=dict(tickfont=dict(size=15)),
    height=600  # Atur tinggi grafik untuk responsivitas
)

# Menampilkan grafik di Streamlit
st.plotly_chart(fig, use_container_width=True)

#-------------- TOP PRODUCTS ORDER (Pertanyaan 1) --------------
best_products = top_product_df.head(5)
fig_best = px.bar(best_products, 
                  x='total_orders', 
                  y='product_category_name_english', 
                  title='Best Performing Product',
                  orientation='h',
                  color_discrete_sequence=["#72BCD4"])
fig_best.update_traces(hovertemplate='<b>Product:</b> %{y}<br>' +
                                      '<b>Total Orders:</b> %{x}<br>' +
                                      '<extra></extra>')

# Membuat bar chart untuk produk terburuk
worst_products = top_product_df.sort_values(by="total_orders", ascending=True).head(5)
fig_worst = px.bar(worst_products, 
                   x='total_orders', 
                   y='product_category_name_english', 
                   title='Worst Performing Product',
                   orientation='h',
                   color_discrete_sequence=["#D3D3D3"])
fig_worst.update_traces(hovertemplate='<b>Product:</b> %{y}<br>' +
                                       '<b>Total Orders:</b> %{x}<br>' +
                                       '<extra></extra>')

# Mengatur dua kolom untuk grafik
col1, col2 = st.columns(2)

# Menampilkan grafik pada kolom yang sesuai
col1.plotly_chart(fig_best, use_container_width=True)
col2.plotly_chart(fig_worst, use_container_width=True)


# ------- Pie Chart: Kontribusi pendapatan per kategori ----------
top5 = top_product_df.head(5)

fig = px.pie(top5, values='total_revenue', names='product_category_name_english', 
             title='Revenue Contribution from Top 5 Product Categories')
fig.update_traces(hovertemplate='<b>Product:</b> %{label}<br>' +
                                '<b>Total Orders:</b> %{value}<br>' +
                                '<extra></extra>')
st.plotly_chart(fig)


# ---------------------Relationship between Delivery Speed and Review Score (Pertanyaan 2)----------------------
st.subheader("Delivery Speed and Review Score Correlation")

# Menghitung rata-rata skor review per kategori pengiriman
average_scores = main_df.groupby('delivery_category')['review_score'].mean().reset_index()

# Membuat kolom untuk menampilkan hasil
col1, col2, col3, col4 = st.columns(4)

# Menampilkan rata-rata untuk setiap kategori
categories = ['Cepat', 'Normal', 'Lambat', 'Sangat Lambat']
scores = {category: average_scores[average_scores['delivery_category'] == category]['review_score'].values[0] if not average_scores[average_scores['delivery_category'] == category].empty else 0 for category in categories}

with col1:
    st.metric("Fast", value=f"{scores['Cepat']:.2f}")

with col2:
    st.metric("Normal", value=f"{scores['Normal']:.2f}")

with col3:
    st.metric("Slow", value=f"{scores['Lambat']:.2f}")

with col4:
    st.metric("Very Slow", value=f"{scores['Sangat Lambat']:.2f}")

# Mendefinisikan bins untuk kategori pengiriman
bins = [0, 25, 50, 100, relation_deliveryNreview_df + 1]  # Tambahkan nilai maksimum + 1 ke bins
labels = ['Cepat', 'Normal', 'Lambat', 'Sangat Lambat']

main_df['delivery_category'] = pd.cut(
    main_df['delivery_speed'],
    bins=bins,
    labels=labels,
    include_lowest=True
)

# Membuat boxplot menggunakan Plotly
fig = px.box(main_df, 
              x='delivery_category', 
              y='review_score', 
              title="Distribution of Review Scores by Delivery Category",
              color='delivery_category',
              color_discrete_sequence=px.colors.sequential.Viridis)

# Mengatur layout untuk grafik
fig.update_layout(
    xaxis_title="Delivery Category",
    yaxis_title="Review Scores",
    title_font_size=14
)

# Menampilkan grafik di Streamlit
st.plotly_chart(fig, use_container_width=True)

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
    avg_monetary = format_currency(rfm_df.monetary.mean(), "AUD", locale='es_CO') 
    st.metric("Average Monetary", value=avg_monetary)

# Membuat grafik menggunakan Matplotlib
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Recency
recency_top3 = rfm_df.sort_values(by="recency", ascending=True).head(3)
recency_bars = recency_top3.plot(kind='bar', x='customer', y='recency', ax=axes[0], title="By Recency (days)")
axes[0].set_xlabel('Customer')
axes[0].set_ylabel('Recency (days)')
axes[0].tick_params(axis='x', rotation=45)
for i, v in enumerate(recency_top3['recency']):
    axes[0].text(i, v, str(round(v, 1)), ha='center', va='bottom', fontweight='bold')

# Frequency 
frequency_top3 = rfm_df.sort_values(by="frequency", ascending=False).head(3)
frequency_bars = frequency_top3.plot(kind='bar', x='customer', y='frequency', ax=axes[1], title="By Frequency")
axes[1].set_xlabel('Customer')
axes[1].set_ylabel('Frequency')
axes[1].tick_params(axis='x', rotation=45)
for i, v in enumerate(frequency_top3['frequency']):
    axes[1].text(i, v, str(round(v, 2)), ha='center', va='bottom', fontweight='bold')

# Monetary
monetary_top3 = rfm_df.sort_values(by="monetary", ascending=False).head(3)
monetary_bars = monetary_top3.plot(kind='bar', x='customer', y='monetary', ax=axes[2], title="By Monetary")
axes[2].set_xlabel('Customer')
axes[2].set_ylabel('Monetary')
axes[2].tick_params(axis='x', rotation=45)
for i, v in enumerate(monetary_top3['monetary']):
    axes[2].text(i, v, format_currency(v, "AUD", locale='es_CO'), ha='center', va='bottom', fontweight='bold')

# Menghilangkan legenda
for ax in axes:
    ax.legend().set_visible(False)

st.pyplot(fig)

st.caption('Github : Aizuro')
