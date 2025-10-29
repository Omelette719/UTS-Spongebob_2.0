import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
import plotly.graph_objects as go
# Pastikan 'statsmodels' ada di requirements.txt untuk 'trendline="lowess"'

# --- Konfigurasi Halaman & Tema ---
st.set_page_config(
    page_title="Dashboard BI Episode SpongeBob SquarePants",
    page_icon="🍍",
    layout="wide"
)

# URL untuk gambar online (logo dan background)
SPONGEBOB_LOGO_URL = "https://www.pinclipart.com/picdir/big/566-5662181_spongebob-logo-spongebob-squarepants-logo-clipart.png"
BIKINI_BOTTOM_BG_URL = "https://wallpapers.com/images/hd/spongebob-flower-background-2928-x-1431-gmoyqoppdrorzpj9.jpg"

# Custom CSS untuk tema Bikini Bottom (Overlay 0.6)
st.markdown(
    f"""
    <style>
    /* Mengatur background dengan gambar Bikini Bottom dan menambahkan overlay gelap */
    .stApp {{
        /* Menerapkan linear-gradient (overlay hitam 60% transparan) di atas URL gambar */
        background: 
            linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
            url("{BIKINI_BOTTOM_BG_URL}");
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}

    /* Membuat sidebar dan konten utama lebih kontras */
    .st-emotion-cache-18ni4ap, .st-emotion-cache-12fmw37, .st-emotion-cache-10trblm {{
        background-color: rgba(255, 255, 255, 0.9); /* Putih semi-transparan untuk konten */
        border-radius: 10px;
        padding: 20px;
    }}
    /* Font dan warna teks untuk header */
    h1, h2, h3, h4, .css-vk3wp0 {{
        color: #00008B;
        font-family: 'Comic Sans MS', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(255, 255, 0, 0.8);
    }}
    /* Card/Kotak untuk metrik */
    [data-testid="stMetricValue"] {{
        font-size: 2.5rem;
        color: #FFD700;
        font-weight: bold;
        text-shadow: 1px 1px 2px #00008B;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Fungsi Data Cleaning & Metrik ---
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path)

    # A. Data Cleaning: Airdate & Viewers
    df['Airdate'] = df['Airdate'].replace('1997/1998', 'January 1, 1998')
    df['Airdate'] = pd.to_datetime(df['Airdate'], errors='coerce')
    median_viewers = pd.to_numeric(df['U.S. viewers (millions)'], errors='coerce').median()
    df['U.S. viewers (millions)'] = pd.to_numeric(df['U.S. viewers (millions)'], errors='coerce').fillna(median_viewers)

    # B. Metric 1: Runtime_Sec & Runtime_Min
    def parse_running_time(time_str):
        if pd.isna(time_str): return np.nan
        minutes, seconds = 0, 0
        min_match = re.search(r'(\d+)\s+minutes?', time_str)
        if min_match: minutes = int(min_match.group(1))
        sec_match = re.search(r'(\d+)\s+seconds?', time_str)
        if sec_match: seconds = int(sec_match.group(1))
        return (minutes * 60) + seconds

    df['Runtime_Sec'] = df['Running time'].apply(parse_running_time)
    df['Runtime_Sec'] = df['Runtime_Sec'].fillna(df['Runtime_Sec'].mean())
    df['Runtime_Min'] = df['Runtime_Sec'] / 60

    # C. Metric 2: Lead_Writers_Count
    def count_writers(writer_str):
        if pd.isna(writer_str): return 0
        cleaned_str = str(writer_str).strip("[]'\"")
        return len([w.strip() for w in cleaned_str.split(',') if w.strip()])

    df['Lead_Writers_Count'] = df['Writer(s)'].apply(count_writers)

    # D. Metric 3: Viewers_Per_Minute (VPM)
    df['Viewers_Per_Minute'] = df['U.S. viewers (millions)'] / df['Runtime_Min']

    # E. Extract unique writers for filter
    all_writers = set()
    for writers_list in df['Writer(s)'].dropna():
        cleaned_str = str(writers_list).strip("[]'\"")
        for writer in cleaned_str.split(','):
            if writer.strip():
                all_writers.add(writer.strip())
    
    df = df.dropna(subset=['Airdate'])

    return df, sorted(list(all_writers))

# Memuat data
try:
    df, unique_writers = load_data("spongebob_episodes.csv")
except FileNotFoundError:
    st.error("File 'spongebob_episodes.csv' tidak ditemukan. Pastikan file berada di direktori yang sama.")
    st.stop()


# --- Sidebar: Filter Dashboard ---
with st.sidebar:
    # PERBAIKAN: Menggunakan width='stretch' untuk st.image
    st.image(SPONGEBOB_LOGO_URL, width='stretch') 
    st.markdown("---")
    st.subheader("🛠️ Filter Dashboard")
    
    # Filter 1: Season (All/Per Season)
    season_options = ["All Seasons"] + [f"Season {s}" for s in sorted(df['Season №'].unique())]
    selected_season_display = st.selectbox("Pilih Musim:", options=season_options, index=0)

    # Filter 2: Airdate Range
    min_date = df['Airdate'].min().date()
    max_date = df['Airdate'].max().date()
    date_range = st.slider("Pilih Rentang Tanggal Tayang:", min_value=min_date, max_value=max_date,
                           value=(min_date, max_date), format="YYYY-MM-DD")

    # Filter 3: Writer
    selected_writer = st.selectbox("Pilih Penulis (Writer(s)): ", options=["Semua Penulis"] + unique_writers)

# Menerapkan Filter
if selected_season_display == "All Seasons":
    df_filtered = df.copy()
else:
    selected_season_num = int(selected_season_display.split(' ')[1])
    df_filtered = df[df['Season №'] == selected_season_num].copy()

df_filtered = df_filtered[
    (df_filtered['Airdate'].dt.date >= date_range[0]) & 
    (df_filtered['Airdate'].dt.date <= date_range[1])
]

if selected_writer != "Semua Penulis":
    df_filtered = df_filtered[df_filtered['Writer(s)'].fillna('').str.contains(selected_writer, case=False, na=False)]

if df_filtered.empty:
    st.error("Tidak ada data yang sesuai dengan filter yang dipilih.")
    st.stop()

# --- Main Dashboard ---
st.title("🍍 Dashboard BI Episode SpongeBob SquarePants")

# Sejarah dan Konteks
with st.expander("Konteks: Sejarah Singkat dan Analisis Bisnis", expanded=False):
    st.markdown("""
    **SpongeBob SquarePants** diciptakan oleh ahli biologi laut dan animator **Stephen Hillenburg**.
    Dashboard ini dibuat untuk menganalisis tren kinerja, mendiagnosis faktor keberhasilan, dan memberikan rekomendasi strategis (preskriptif) untuk produksi episode mendatang.

    **Metrik Utama Baru (Dibuat Saat Data Cleaning):**
    1.  **`Runtime_Sec`**: Durasi episode yang bersih dalam detik.
    2.  **`Lead_Writers_Count`**: Jumlah penulis utama per episode (Kompleksitas Tim Kreatif).
    3.  **`Viewers_Per_Minute` (VPM)**: Efisiensi episode dalam menarik penonton per unit waktu tayang.
    """)

st.markdown("---")

## Bagian I: Ringkasan Metrik & Analisis DeskriptIF

st.header("⭐ Ringkasan Data & Metrik Utama")
col1, col2, col3 = st.columns(3)

with col1:
    avg_viewers = df_filtered['U.S. viewers (millions)'].mean()
    st.metric(label="Rata-rata Penonton (Jutaan)", value=f"{avg_viewers:.2f} Jt")

with col2:
    total_episodes = len(df_filtered)
    st.metric(label="Total Episode", value=f"{total_episodes}")

with col3:
    avg_vpm = df_filtered['Viewers_Per_Minute'].mean()
    st.metric(label="Rata-rata Penonton/Menit", value=f"{avg_vpm:.2f}")

st.markdown("---")

col_vis_1, col_vis_2 = st.columns(2)

with col_vis_1:
    st.subheader("1. Tren Viewership Tahunan")
    st.markdown("**Analisis: Deskriptif** | *Pertanyaan:* Bagaimana popularitas SpongeBob (diukur dari jumlah penonton) berubah dari tahun ke tahun?")
    
    # Data Prep V1: Rata-rata Penonton per Tahun
    df_trend = df_filtered.copy()
    df_trend['Airdate_Year'] = df_trend['Airdate'].dt.year
    df_trend = df_trend.groupby('Airdate_Year')['U.S. viewers (millions)'].mean().reset_index()
    
    fig1 = px.line(
        df_trend, x='Airdate_Year', y='U.S. viewers (millions)', markers=True,
        title='Tren Rata-rata Penonton Tahunan',
        labels={'Airdate_Year': 'Tahun Tayang', 'U.S. viewers (millions)': 'Rata-rata Penonton (Jutaan)'}
    )
    fig1.update_traces(line_color='#00008B', marker_color='#FFD700', marker_size=8)
    
    # PERBAIKAN: Menggunakan use_container_width=True (cara standar)
    st.plotly_chart(fig1, use_container_width=True) 

with col_vis_2:
    st.subheader("2. Stabilitas Viewership Episode per Musim")
    st.markdown("**Analisis: Diagnostik** | *Pertanyaan:* Seberapa stabil (variatif) penonton dalam setiap musim? Apakah Musim X memiliki rentang penonton yang lebar atau stabil?")
    
    # --- Perbaikan: Mengubah Season № menjadi string untuk Box Plot ---
    df_temp = df_filtered.copy()
    df_temp['Season_Category'] = df_temp['Season №'].astype(str)
    
    fig2 = px.box(
        df_temp, 
        x='Season_Category', 
        y='U.S. viewers (millions)', 
        title='Distribusi & Stabilitas Viewership Episode per Musim',
        labels={'Season_Category': 'Nomor Musim', 'U.S. viewers (millions)': 'Penonton (Jutaan)'},
        color='Season_Category', 
        color_discrete_sequence=px.colors.qualitative.Plotly
    )
    # PERBAIKAN: Menggunakan use_container_width=True
    st.plotly_chart(fig2, use_container_width=True) 

st.markdown("---")

## Bagian II: Analisis Diagnostik (Kontributor & Karakter)

st.header("🐙 Diagnosis: Menggali Penyebab Perubahan Viewership")
st.markdown("Visualisasi ini membantu mendiagnosis penyebab tren (Visual 1) dan stabilitas (Visual 2).")

col_vis_3, col_vis_6 = st.columns(2)

with col_vis_3:
    st.subheader("3. Peringkat Penulis Berdasarkan Rata-rata Penonton")
    st.markdown("**Analisis: Diagnostik** | *Pertanyaan:* Siapakah 10 penulis individu yang secara konsisten menghasilkan episode dengan rata-rata penonton tertinggi?")
    
    # Data Prep V3: Explode Writers
    writer_exploded = df_filtered.copy()
    writer_exploded['Writer'] = writer_exploded['Writer(s)'].fillna('').astype(str).str.strip("[]'\"")
    writer_exploded['Writer'] = writer_exploded['Writer'].apply(lambda x: [w.strip() for w in x.split(',') if w.strip()])
    writer_exploded = writer_exploded.explode('Writer')
    
    writer_performance = writer_exploded.groupby('Writer')['U.S. viewers (millions)'].mean().reset_index()
    writer_performance.columns = ['Writer', 'Avg_Viewers']
    writer_performance = writer_performance[writer_performance['Writer'] != ''].nlargest(10, 'Avg_Viewers').sort_values(by='Avg_Viewers', ascending=True)

    fig3 = px.bar(
        writer_performance, x='Avg_Viewers', y='Writer', orientation='h',
        title=f'Top 10 Penulis Paling Sukses ({selected_season_display})',
        labels={'Avg_Viewers': 'Rata-rata Penonton (Jutaan)', 'Writer': 'Penulis'},
        color='Avg_Viewers', color_continuous_scale=px.colors.sequential.Sunset_r
    )
    fig3.update_layout(yaxis={'categoryorder':'total ascending'}) 
    
    # PERBAIKAN: Menggunakan use_container_width=True
    st.plotly_chart(fig3, use_container_width=True) 

with col_vis_6:
    st.subheader("4. Fokus Karakter Utama per Musim")
    st.markdown("**Analisis: Diagnostik** | *Pertanyaan:* Bagaimana alokasi fokus cerita pada karakter utama bergeser dari musim ke musim?")

    # Data Prep V6: Karakter Heatmap
    MAIN_CHARS = ['SpongeBob SquarePants', 'Patrick Star', 'Squidward Tentacles', 'Eugene H. Krabs', 'Sandy Cheeks']
    
    char_count_df = df_filtered[['Season №', 'characters']].copy()
    
    for char in MAIN_CHARS:
        char_count_df[char] = char_count_df['characters'].fillna('').apply(lambda x: 1 if re.search(r'\b' + re.escape(char) + r'\b', x) else 0)

    # Agregasi: Hitung episode kemunculan per musim
    heatmap_data = char_count_df.groupby('Season №')[MAIN_CHARS].sum()
    heatmap_data = heatmap_data.apply(lambda x: x / x.sum(), axis=1).fillna(0) # Proporsi penampilan dalam musim

    # Mengubah wide-form ke long-form dan rename kolom
    heatmap_data_reset = heatmap_data.reset_index() 
    heatmap_data_reset = heatmap_data_reset.rename(columns={'Season №': 'Season_No'})
    
    heatmap_data_long = heatmap_data_reset.melt(
        id_vars='Season_No',
        value_vars=MAIN_CHARS,
        var_name='Character',
        value_name='Proportion'
    )

    # Menggunakan go.Figure dan go.Heatmap
    fig6 = go.Figure(data=go.Heatmap(
        x=heatmap_data_long['Character'],
        y=heatmap_data_long['Season_No'],
        z=heatmap_data_long['Proportion'],
        colorscale=px.colors.sequential.Blues,
        colorbar=dict(title="Proporsi")
    ))

    fig6.update_layout(
        title='Proporsi Fokus Karakter Utama (Per Musim)',
        xaxis_title='Karakter',
        yaxis_title='Nomor Musim',
        yaxis=dict(dtick=1)
    )
    
    # PERBAIKAN: Menggunakan use_container_width=True
    st.plotly_chart(fig6, use_container_width=True)

st.markdown("---")

## Bagian III: Analisis Preskriptif (Optimasi Strategi)

st.header("🧠 Preskriptif: Rekomendasi Durasi & Sumber Daya")
st.markdown("Visualisasi ini memberikan rekomendasi strategis untuk memaksimalkan kinerja episode mendatang.")

col_vis_4, col_vis_5 = st.columns(2)

with col_vis_4:
    st.subheader("5. Durasi Episode vs. Jumlah Penonton")
    st.markdown("**Analisis: Preskriptif** | *Pertanyaan:* Apakah ada durasi tayang optimal yang menghasilkan *viewership* tertinggi?")
    
    # Data Prep V4: Scatter Plot Durasi
    # (Membutuhkan 'statsmodels' di requirements.txt)
    fig4 = px.scatter(
        df_filtered,
        x='Runtime_Min',
        y='U.S. viewers (millions)',
        trendline="lowess", 
        hover_data=['title', 'Season №'],
        title='Durasi Episode (Menit) vs. Viewership',
        labels={'Runtime_Min': 'Durasi Episode (Menit)', 'U.S. viewers (millions)': 'Penonton (Jutaan)'},
        color='Season №', color_continuous_scale=px.colors.sequential.Rainbow
    )
    # PERBAIKAN: Menggunakan use_container_width=True
    st.plotly_chart(fig4, use_container_width=True) 


with col_vis_5:
    st.subheader("6. Jumlah Penulis vs. Efisiensi Viewership (VPM)")
    st.markdown("**Analisis: Preskriptif** | *Pertanyaan:* Berapa jumlah penulis ideal untuk mencapai VPM paling efisien? (Optimasi Biaya Kreatif)")
    
    # Data Prep V5: Aggregate VPM dan hitung episode per Writer Count
    vpm_agg = df_filtered.groupby('Lead_Writers_Count').agg(
        Avg_VPM=('Viewers_Per_Minute', 'mean'),
        Total_Episodes=('Episode №', 'count')
    ).reset_index()
    
    fig5 = px.scatter(
        vpm_agg,
        x='Lead_Writers_Count',
        y='Avg_VPM',
        size='Total_Episodes',
        title='Efisiensi VPM vs. Jumlah Penulis (Optimasi Tim Kreatif)',
        labels={'Lead_Writers_Count': 'Jumlah Penulis Utama', 'Avg_VPM': 'Rata-rata Penonton/Menit (VPM)'},
        color='Total_Episodes', color_continuous_scale=px.colors.sequential.Aggrnyl
    )
    
    # Garis Rata-rata VPM Global
    fig5.add_hline(y=avg_vpm, line_dash="dash", line_color="red", annotation_text=f"Avg VPM Global: {avg_vpm:.2f}")
    fig5.update_layout(xaxis=dict(dtick=1))

    # PERBAIKAN: Menggunakan use_container_width=True
    st.plotly_chart(fig5, use_container_width=True) 

st.markdown("---")
st.info("✅ Error 'statsmodels' dan peringatan 'use_container_width' telah diatasi. Pastikan 'statsmodels' ada di requirements.txt Anda!")
