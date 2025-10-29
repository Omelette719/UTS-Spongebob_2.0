import streamlit as st
import pandas as pd
import numpy as np
import re
import plotly.express as px
import plotly.graph_objects as go

# --- Konfigurasi Halaman & Tema ---
st.set_page_config(
    page_title="Dashboard Analisis Episode SpongeBob SquarePants",
    page_icon="🍍",
    layout="wide"
)

# URL untuk gambar online (logo dan background)
SPONGEBOB_LOGO_URL = "https://www.pinclipart.com/picdir/big/566-5662181_spongebob-logo-spongebob-squarepants-logo-clipart.png"
BIKINI_BOTTOM_BG_URL = "https://wallpapers.com/images/hd/spongebob-flower-background-2928-x-1431-gmoyqoppdrorzpj9.jpg" # Contoh placeholder gambar bawah laut

# Custom CSS untuk tema Bikini Bottom (CSS OVERLAY DIPERBAIKI)
st.markdown(
    f"""
    <style>
    /* Mengatur background dengan gambar Bikini Bottom dan menambahkan overlay gelap */
    .stApp {{
        /* Menerapkan linear-gradient (overlay hitam 40% transparan) di atas URL gambar */
        background: 
            linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
            url("{BIKINI_BOTTOM_BG_URL}");
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}

    /* Membuat sidebar dan konten utama lebih transparan agar background terlihat */
    .st-emotion-cache-18ni4ap, .st-emotion-cache-12fmw37, .st-emotion-cache-10trblm {{
        background-color: rgba(255, 255, 255, 0.9); /* Putih semi-transparan untuk konten */
        border-radius: 10px;
        padding: 20px;
    }}
    /* Font dan warna teks untuk header */
    h1, h2, h3, h4, .css-vk3wp0 {{
        color: #00008B; /* Dark Blue - Warna air laut */
        font-family: 'Comic Sans MS', cursive, sans-serif;
        text-shadow: 2px 2px 4px rgba(255, 255, 0, 0.8); /* Kuning Bayangan */
    }}
    /* Card/Kotak untuk metrik */
    [data-testid="stMetricValue"] {{
        font-size: 2.5rem;
        color: #FFD700; /* Emas - Warna nanas SpongeBob */
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

    # A. Clean 'Airdate'
    df['Airdate'] = df['Airdate'].replace('1997/1998', 'January 1, 1998')
    df['Airdate'] = pd.to_datetime(df['Airdate'], errors='coerce')

    # B. Clean 'U.S. viewers (millions)'
    median_viewers = pd.to_numeric(df['U.S. viewers (millions)'], errors='coerce').median()
    df['U.S. viewers (millions)'] = pd.to_numeric(df['U.S. viewers (millions)'], errors='coerce').fillna(median_viewers)

    # C. Create 'Runtime_Sec' & 'Runtime_Min' (Metric 1)
    def parse_running_time(time_str):
        if pd.isna(time_str): return np.nan
        minutes = 0
        seconds = 0
        min_match = re.search(r'(\d+)\s+minutes?', time_str)
        if min_match: minutes = int(min_match.group(1))
        sec_match = re.search(r'(\d+)\s+seconds?', time_str)
        if sec_match: seconds = int(sec_match.group(1))
        return (minutes * 60) + seconds

    df['Runtime_Sec'] = df['Running time'].apply(parse_running_time)
    df['Runtime_Sec'] = df['Runtime_Sec'].fillna(df['Runtime_Sec'].mean())
    df['Runtime_Min'] = df['Runtime_Sec'] / 60

    # D. Create 'Lead_Writers_Count' (Metric 2)
    def count_writers(writer_str):
        if pd.isna(writer_str): return 0
        cleaned_str = str(writer_str).strip("[]'\"")
        return len([w.strip() for w in cleaned_str.split(',') if w.strip()])

    df['Lead_Writers_Count'] = df['Writer(s)'].apply(count_writers)

    # E. Create 'Viewers_Per_Minute' (Metric 3)
    df['Viewers_Per_Minute'] = df['U.S. viewers (millions)'] / df['Runtime_Min']

    # F. Extract unique writers for filtering
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
    st.image(SPONGEBOB_LOGO_URL, use_container_width=True) 
    st.markdown("---")
    st.subheader("🛠️ Filter Dashboard")
    
    # --- Filter 1: Season ---
    season_options = ["All Seasons"] + [f"Season {s}" for s in sorted(df['Season №'].unique())]
    selected_season_display = st.selectbox(
        "Pilih Musim:",
        options=season_options,
        index=0
    )

    # --- Filter 2: Airdate Range ---
    min_date = df['Airdate'].min().date()
    max_date = df['Airdate'].max().date()
    date_range = st.slider(
        "Pilih Rentang Tanggal Tayang:",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )

    # --- Filter 3: Writer ---
    selected_writer = st.selectbox(
        "Pilih Penulis (Writer(s)): ",
        options=["Semua Penulis"] + unique_writers
    )

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
st.title("📊 Dashboard Analisis Episode SpongeBob SquarePants")

# --- Sejarah Singkat Ditempatkan di sini ---
with st.expander("Klik untuk membaca Sejarah Singkat SpongeBob SquarePants", expanded=False):
    st.markdown("""
    **SpongeBob SquarePants** diciptakan oleh ahli biologi laut dan animator **Stephen Hillenburg**.
    Episode pertamanya tayang pada **1 Mei 1999** setelah Nickelodeon Kids' Choice Awards.
    Ide dasarnya berasal dari komik edukasi Hillenburg, *The Intertidal Zone*, yang menampilkan karakter spons awal.
    Acara ini dengan cepat menjadi salah satu serial animasi terpanjang dan paling populer, disukai oleh anak-anak maupun orang dewasa di seluruh dunia karena humornya yang unik dan karakter-karakternya yang ikonik.
    """)

st.markdown("---")

# --- Bagian 1: Metrik Utama (Deskriptif) ---
st.header("⭐ Metrik Utama Episode Terpilih")
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

# ==============================================================================
# VISUALISASI 1: ANALISIS DESKRIPTIF - Tren Penonton dari Waktu ke Waktu (Plotly Line Chart)
# ==============================================================================
st.header("📈 1. Tren Historis: Bagaimana Viewership Berubah Seiring Waktu?")
st.markdown("**Alur Cerita: Deskriptif** | Visualisasi ini menunjukkan perubahan rata-rata penonton per musim, memberikan gambaran umum tentang tren popularitas serial ini.")

# Agregasi data per musim 
df_viewership = df_filtered.groupby('Season №')['U.S. viewers (millions)'].mean().reset_index()
df_viewership.columns = ['Season_No', 'Avg_Viewers']

# Plotly Line Chart
fig1 = px.line(
    df_viewership,
    x='Season_No',
    y='Avg_Viewers',
    markers=True,
    title='Rata-rata Penonton Episode per Musim',
    labels={'Season_No': 'Nomor Musim', 'Avg_Viewers': 'Rata-rata Penonton (Jutaan)'}
)
fig1.update_traces(line_color='#00008B', marker_color='#FFD700', marker_size=8) 
fig1.update_layout(xaxis=dict(dtick=1))
fig1.update_layout(hovermode="x unified") 

st.plotly_chart(fig1, use_container_width=True)

st.markdown("""
<p style='font-style: italic; color: #555;'>
<strong>Insight Deskriptif:</strong> Garis ini dapat mengidentifikasi puncak popularitas dan fase penurunan atau pemulihan. Penurunan atau kenaikan tajam menjadi pertanyaan yang perlu didiagnosis pada visualisasi berikutnya.
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# VISUALISASI 2: ANALISIS DIAGNOSTIK - Karakter Paling Sering Muncul (Plotly Bar Chart)
# ==============================================================================
st.header("🐙 2. Analisis Konten: Siapa Karakter Utama di Bikini Bottom?")
st.markdown("**Alur Cerita: Diagnostik** | Analisis ini menggali komposisi konten, mengidentifikasi karakter mana yang paling sering digunakan, berpotensi menjelaskan mengapa episode di puncak popularitas berkinerja baik atau buruk.")

# Menghitung frekuensi karakter
character_counts = {}
for char_list in df_filtered['characters'].dropna():
    cleaned_chars = str(char_list).strip("[]'\"").split(',')
    for char in cleaned_chars:
        char_name = char.strip()
        if len(char_name) > 2 and char_name not in ["Incidentals", "Incidental", "Incidental 2", "Incidental 3", "Fred"]:
             character_counts[char_name] = character_counts.get(char_name, 0) + 1

# Top 10 Karakter
top_characters = pd.DataFrame(
    sorted(character_counts.items(), key=lambda item: item[1], reverse=True)[:10],
    columns=['Character', 'Appearances']
)

# Plotly Bar Chart
fig2 = px.bar(
    top_characters.sort_values(by='Appearances', ascending=True),
    x='Appearances',
    y='Character',
    orientation='h',
    title=f'Top 10 Karakter Paling Sering Muncul pada {selected_season_display}',
    labels={'Appearances': 'Jumlah Kemunculan Episode'},
    color='Appearances',
    color_continuous_scale=px.colors.sequential.Tealgrn
)
fig2.update_layout(yaxis={'categoryorder':'total ascending'}) 

st.plotly_chart(fig2, use_container_width=True)

st.markdown("""
<p style='font-style: italic; color: #555;'>
<strong>Insight Diagnostik:</strong> Visualisasi ini menunjukkan fokus naratif. Jika karakter sekunder sering muncul dalam musim yang memiliki *Viewership* tinggi, ini bisa menjadi faktor kesuksesan yang perlu dipertimbangkan.
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ==============================================================================
# VISUALISASI 3: ANALISIS PRESKRIPTIF/DIAGNOSTIK - Viewers Per Minute vs. Writer Count (Plotly Scatter Plot)
# ==============================================================================
st.header("🧠 3. Analisis Efisiensi: Seberapa Efektif Tim Penulis?")
st.markdown("**Alur Cerita: Preskriptif/Diagnostik** | Plot ini menguji hubungan antara kompleksitas tim penulis (`Lead_Writers_Count`) dengan efisiensi penonton (`Viewers_Per_Minute`). Tujuannya adalah untuk memberikan rekomendasi optimasi sumber daya kreatif di masa depan.")

# Plotly Scatter Plot
fig3 = px.scatter(
    df_filtered,
    x='Lead_Writers_Count',
    y='Viewers_Per_Minute',
    hover_data=['title', 'Season №'],
    title=f'Efisiensi Penonton (VPM) vs. Jumlah Penulis Episode pada {selected_season_display}',
    labels={'Lead_Writers_Count': 'Jumlah Penulis Utama', 'Viewers_Per_Minute': 'Penonton (Jutaan) per Menit'},
    color='Season №',
    color_continuous_scale=px.colors.sequential.Rainbow
)

# Menambahkan garis rata-rata VPM (garis preskriptif)
mean_vpm = df_filtered['Viewers_Per_Minute'].mean()
fig3.add_hline(
    y=mean_vpm, 
    line_dash="dash", 
    line_color="red", 
    annotation_text=f"Rata-rata VPM: {mean_vpm:.2f}",
    annotation_position="bottom right"
)

fig3.update_layout(xaxis=dict(dtick=1))
fig3.update_traces(marker=dict(size=10, opacity=0.7, line=dict(width=1, color='Black')))

st.plotly_chart(fig3, use_container_width=True)

st.markdown(f"""
<p style='font-style: italic; color: #555;'>
<strong>Insight Preskriptif:</strong> Titik-titik di atas garis merah (VPM tinggi) menunjukkan episode yang efisien. **Tindakan Lanjutan (Preskriptif):** Analisis dapat berfokus pada episode ini untuk merekomendasikan jumlah penulis optimal (biasanya 2-3 orang) yang paling sukses dalam menarik penonton per menit di musim yang dipilih.
</p>
""", unsafe_allow_html=True)

st.markdown("---")

st.info("👋 Dashboard Analisis Selesai. Selamat Menjelajah Bikini Bottom!")
