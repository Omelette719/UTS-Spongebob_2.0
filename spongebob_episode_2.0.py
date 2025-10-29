import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px  # Mengimpor Plotly Express
import re
import ast

def safe_literal_eval(s):
    """
    Mengevaluasi representasi string dari literal Python (seperti list) dengan aman.
    Mengembalikan list kosong jika evaluasi gagal atau input bukan string.
    """
    if not isinstance(s, str):
        return []
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return result
        else:
            return []
    except (ValueError, SyntaxError, TypeError):
        return []

@st.cache_data
def load_and_clean_data():
    """
    Memuat, membersihkan, dan mengubah data episode SpongeBob.
    """
    df = pd.read_csv('spongebob_episodes.csv')

    # 1. Bersihkan Airdate dan Buat Air Year
    df['Air Year'] = df['Airdate'].str.extract(r'(\d{4})').astype(float)
    df = df.dropna(subset=['Air Year'])
    df['Air Year'] = df['Air Year'].astype(int)

    # 2. Bersihkan Running time -> Runtime (Minutes) [METRIK BARU]
    def parse_runtime(rt_str):
        if not isinstance(rt_str, str):
            return np.nan
        minutes, seconds = 0, 0
        min_match = re.search(r'(\d+)\s*minute', rt_str)
        if min_match:
            minutes = int(min_match.group(1))
        sec_match = re.search(r'(\d+)\s*second', rt_str)
        if sec_match:
            seconds = int(sec_match.group(1))
        total_minutes = minutes + (seconds / 60)
        return total_minutes if total_minutes > 0 else np.nan
    df['Runtime (Minutes)'] = df['Running time'].apply(parse_runtime)

    # 3. Bersihkan U.S. viewers (millions)
    df['Viewers (Millions)'] = pd.to_numeric(df['U.S. viewers (millions)'], errors='coerce')

    # 4. Buat Viewers per Minute [METRIK BARU]
    df['Viewers per Minute'] = df['Viewers (Millions)'] / df['Runtime (Minutes)']
    df['Viewers per Minute'] = df['Viewers per Minute'].replace([np.inf, -np.inf], np.nan)

    # 5. Pilih dan Ganti Nama Kolom Inti
    core_cols = [
        'title', 'Episode №', 'Season №', 'Air Year', 
        'Runtime (Minutes)', 'Viewers (Millions)', 'Viewers per Minute',
        'Writer(s)', 'characters'
    ]
    df_clean = df[core_cols].copy()
    df_clean = df_clean.dropna(subset=[
        'title', 'Season №', 'Air Year', 'Runtime (Minutes)', 'Viewers (Millions)'
    ])
    df_clean = df_clean.drop_duplicates(subset=['title', 'Episode №'])

    # 6. Proses DataFrame yang Diexplode untuk Karakter dan Penulis
    
    # Proses Karakter
    df_chars = df_clean[['title', 'Episode №', 'Season №', 'Air Year', 'Viewers (Millions)', 'characters']].copy()
    df_chars = df_chars.dropna(subset=['characters'])
    df_chars['character_list'] = df_chars['characters'].str.split(',')
    df_chars_exploded = df_chars.explode('character_list')
    df_chars_exploded['Character'] = df_chars_exploded['character_list'].str.strip()
    main_char_map = {
        'SpongeBob SquarePants': 'SpongeBob SquarePants', 'Patrick Star': 'Patrick Star',
        'Squidward Tentacles': 'Squidward Tentacles', 'Eugene H. Krabs': 'Mr. Krabs',
        'Mr. Krabs': 'Mr. Krabs', 'Sandy Cheeks': 'Sandy Cheeks',
        'Sheldon J. Plankton': 'Plankton', 'Plankton': 'Plankton', 'Gary the Snail': 'Gary the Snail'
    }
    df_chars_exploded['Character'] = df_chars_exploded['Character'].map(main_char_map).fillna(df_chars_exploded['Character'])
    df_chars_exploded = df_chars_exploded[~df_chars_exploded['Character'].str.contains('Incidental|French Narrator', case=False, na=False)]
    df_chars_exploded = df_chars_exploded[df_chars_exploded['Character'] != '']
    df_chars_exploded = df_chars_exploded.drop(columns=['characters', 'character_list'])
    
    # Proses Penulis
    df_writers = df_clean[['title', 'Episode №', 'Season №', 'Air Year', 'Viewers (Millions)', 'Writer(s)']].copy()
    df_writers = df_writers.dropna(subset=['Writer(s)'])
    df_writers['writer_list'] = df_writers['Writer(s)'].apply(safe_literal_eval)
    df_writers_exploded = df_writers.explode('writer_list')
    df_writers_exploded = df_writers_exploded.dropna(subset=['writer_list'])
    df_writers_exploded['Writer'] = df_writers_exploded['writer_list'].str.strip()
    df_writers_exploded = df_writers_exploded[df_writers_exploded['Writer'] != '']
    df_writers_exploded = df_writers_exploded.drop(columns=['Writer(s)', 'writer_list'])

    return df_clean, df_chars_exploded, df_writers_exploded

# --- Kode Aplikasi Streamlit ---

# URL untuk tema
BG_IMAGE_URL = "https://wallpapercave.com/wp/wp2439160.jpg"
LOGO_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/thumb/5/5c/SpongeBob_SquarePants_logo.svg/1200px-SpongeBob_SquarePants_logo.svg.png"

# 1. Konfigurasi Halaman
st.set_page_config(
    page_title="SpongeBob BI Dashboard",
    page_icon="🍍",
    layout="wide"
)

# 2. CSS Kustom untuk Latar Belakang dan Styling
page_bg_css = f"""
<style>
[data-testid="stAppViewContainer"] > .main {{
    background-image: url("{BG_IMAGE_URL}");
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
    background-attachment: fixed;
}}
[data-testid="stSidebar"] {{
    background-color: rgba(240, 242, 246, 0.85);
}}
[data-testid="stAppViewContainer"] .block-container {{
    background-color: rgba(255, 255, 255, 0.90);
    border-radius: 10px;
    padding: 2rem;
    margin: 1rem;
}}
h1, h2, h3 {{
    color: #003A90; /* Biru SpongeBob */
    font-weight: bold;
}}
.logo-container {{
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 1rem;
    background-color: rgba(255, 255, 255, 0.9);
    border-radius: 10px;
    margin-bottom: 1rem;
}}
</style>
"""
st.markdown(page_bg_css, unsafe_allow_html=True)

# 3. Muat Data
try:
    df_episodes, df_chars, df_writers = load_and_clean_data()
    
    # --- 4. Filter Sidebar ---
    st.sidebar.header("🍍 Filter Dasbor")
    
    all_seasons = sorted(df_episodes['Season №'].unique())
    selected_seasons = st.sidebar.multiselect("Filter berdasarkan Musim", all_seasons, default=all_seasons)
    
    min_year = int(df_episodes['Air Year'].min())
    max_year = int(df_episodes['Air Year'].max())
    selected_years = st.sidebar.slider("Filter berdasarkan Tahun Tayang", min_year, max_year, (min_year, max_year))
    
    top_characters = list(df_chars['Character'].value_counts().head(20).index)
    main_cast_order = ['SpongeBob SquarePants', 'Patrick Star', 'Squidward Tentacles', 'Mr. Krabs', 'Sandy Cheeks', 'Plankton', 'Gary the Snail']
    ordered_top_chars = [char for char in main_cast_order if char in top_characters] + [char for char in top_characters if char not in main_cast_order]
    selected_character = st.sidebar.selectbox("Filter berdasarkan Penampilan Karakter", ['Semua Karakter'] + ordered_top_chars)
    
    # --- 5. Filter DataFrame berdasarkan pilihan ---
    df_ep_filtered = df_episodes[
        (df_episodes['Season №'].isin(selected_seasons)) &
        (df_episodes['Air Year'] >= selected_years[0]) &
        (df_episodes['Air Year'] <= selected_years[1])
    ]
    
    if selected_character != 'Semua Karakter':
        episode_ids_with_char = df_chars[
            (df_chars['Character'] == selected_character)
        ].apply(lambda row: (row['title'], row['Episode №']), axis=1).unique()
        df_ep_filtered = df_ep_filtered[
            df_ep_filtered.apply(lambda row: (row['title'], row['Episode №']), axis=1).isin(episode_ids_with_char)
        ]

    df_chars_filtered = df_chars[
        (df_chars['Season №'].isin(selected_seasons)) &
        (df_chars['Air Year'] >= selected_years[0]) &
        (df_chars['Air Year'] <= selected_years[1])
    ]
    df_writers_filtered = df_writers[
        (df_writers['Season №'].isin(selected_seasons)) &
        (df_writers['Air Year'] >= selected_years[0]) &
        (df_writers['Air Year'] <= selected_years[1])
    ]

    # --- 6. Tata Letak Halaman Utama ---
    st.markdown(f'<div class="logo-container"><img src="{LOGO_IMAGE_URL}" width="300"></div>', unsafe_allow_html=True)
    st.title("SpongeBob SquarePants: Dasbor BI 🍍")

    with st.expander("Klik untuk membaca sejarah singkat SpongeBob SquarePants"):
        st.write("""
        *SpongeBob SquarePants* diciptakan oleh pendidik ilmu kelautan dan animator Stephen Hillenburg. 
        Serial ini tayang perdana pada 1 Mei 1999... (teks sejarah seperti sebelumnya)
        """)

    if df_ep_filtered.empty:
        st.warning("Tidak ada data yang cocok dengan kriteria filter Anda. Harap perluas pilihan Anda.")
    else:
        # --- NARASI BAGIAN 1: Gambaran Umum (Deskriptif) ---
        st.header("📈 Gambaran Umum")
        st.markdown(f"Analisis berdasarkan **{len(df_ep_filtered)}** episode yang cocok dengan filter Anda.")
        
        kpi_cols = st.columns(4)
        avg_viewers = df_ep_filtered['Viewers (Millions)'].mean()
        avg_runtime = df_ep_filtered['Runtime (Minutes)'].mean()
        avg_vpm = df_ep_filtered['Viewers per Minute'].mean()
        
        kpi_cols[0].metric("Total Episode", f"{len(df_ep_filtered)}")
        kpi_cols[1].metric("Rata-rata Penonton", f"{avg_viewers:.2f} Juta")
        kpi_cols[2].metric("Rata-rata Durasi", f"{avg_runtime:.2f} mnt")
        kpi_cols[3].metric("Rata-rata Penonton / Menit", f"{avg_vpm:.3f} Juta")
        
        st.subheader("Tren Penonton dari Waktu ke Waktu")
        st.markdown("Grafik ini menunjukkan jumlah rata-rata penonton A.S. (dalam jutaan) per tahun.")
        
        viewers_by_year = df_ep_filtered.groupby('Air Year')['Viewers (Millions)'].mean().reset_index()
        
        # PLOTLY: Grafik Garis
        fig_time = px.line(
            viewers_by_year, 
            x='Air Year', 
            y='Viewers (Millions)', 
            title="Rata-rata Penonton A.S. berdasarkan Tahun",
            markers=True,
            labels={'Air Year': 'Tahun Tayang', 'Viewers (Millions)': 'Rata-rata Penonton (Juta)'}
        )
        fig_time.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_time, use_container_width=True)

        # --- NARASI BAGIAN 2: Penyelaman Performa (Diagnostik) ---
        st.header("🔍 Penyelaman Performa")
        st.markdown("Mari kita diagnosis karakteristik *apa* yang berkorelasi dengan kinerja.")
        
        diag_cols = st.columns(2)
        
        with diag_cols[0]:
            st.subheader("Kinerja berdasarkan Musim")
            viewers_by_season = df_ep_filtered.groupby('Season №')['Viewers (Millions)'].mean().reset_index()
            
            # PLOTLY: Grafik Batang
            fig_season = px.bar(
                viewers_by_season,
                x='Season №',
                y='Viewers (Millions)',
                title="Rata-rata Penonton berdasarkan Musim",
                color='Season №',
                labels={'Season №': 'Musim', 'Viewers (Millions)': 'Rata-rata Penonton (Juta)'}
            )
            fig_season.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_season, use_container_width=True)
            
        with diag_cols[1]:
            st.subheader("Durasi vs. Jumlah Penonton")
            
            # PLOTLY: Scatter Plot
            fig_scatter = px.scatter(
                df_ep_filtered,
                x='Runtime (Minutes)',
                y='Viewers (Millions)',
                title="Durasi Episode vs. Penonton",
                hover_data=['title', 'Season №'],
                labels={'Runtime (Minutes)': 'Durasi (Menit)', 'Viewers (Millions)': 'Penonton (Juta)'}
            )
            fig_scatter.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- NARASI BAGIAN 3: Elemen Kreatif (Diagnostik) ---
        st.header("🎨 Analisis Elemen Kreatif")
        st.markdown("Karakter dan penulis mana yang paling terlibat dalam episode yang dipilih?")
        
        creative_cols = st.columns(2)
        
        with creative_cols[0]:
            st.subheader("Karakter Paling Sering Muncul")
            top_15_chars = df_chars_filtered['Character'].value_counts().head(15).reset_index()
            top_15_chars.columns = ['Character', 'Appearance Count']
            
            # PLOTLY: Grafik Batang Horizontal
            fig_char_freq = px.bar(
                top_15_chars,
                x='Appearance Count',
                y='Character',
                title="15 Karakter Paling Sering Muncul",
                orientation='h',
                labels={'Appearance Count': 'Jumlah Penampilan', 'Character': 'Karakter'}
            )
            fig_char_freq.update_yaxes(categoryorder="total ascending")
            fig_char_freq.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_char_freq, use_container_width=True)
            
        with creative_cols[1]:
            st.subheader("Penulis Paling Produktif")
            top_15_writers = df_writers_filtered['Writer'].value_counts().head(15).reset_index()
            top_15_writers.columns = ['Writer', 'Episode Count']
            
            # PLOTLY: Grafik Batang Horizontal
            fig_writer_freq = px.bar(
                top_15_writers,
                x='Episode Count',
                y='Writer',
                title="15 Penulis Paling Produktif",
                orientation='h',
                labels={'Episode Count': 'Jumlah Episode Ditulis', 'Writer': 'Penulis'}
            )
            fig_writer_freq.update_yaxes(categoryorder="total ascending")
            fig_writer_freq.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_writer_freq, use_container_width=True)

        # --- NARASI BAGIAN 4: Wawasan yang Dapat Ditindaklanjuti (Prediktif & Preskriptif) ---
        st.header("💡 Wawasan & Analisis yang Dapat Ditindaklanjuti")
        
        st.subheader("Karakter Mana yang Mendorong Jumlah Penonton?")
        st.markdown("""
        Grafik ini menunjukkan jumlah penonton *rata-rata* untuk episode yang menampilkan 10 karakter
        paling sering muncul. **Pertanyaan Bisnis:** Apakah episode yang menampilkan karakter tertentu 
        berkorelasi dengan jumlah penonton yang lebih tinggi?
        """)
        
        top_10_char_names = list(df_chars_filtered['Character'].value_counts().head(10).index)
        df_top_10_chars = df_chars_filtered[df_chars_filtered['Character'].isin(top_10_char_names)]
        avg_viewers_by_char = df_top_10_chars.groupby('Character')['Viewers (Millions)'].mean().reset_index()
        
        # PLOTLY: Grafik Batang Horizontal
        fig_char_viewers = px.bar(
            avg_viewers_by_char,
            x='Viewers (Millions)',
            y='Character',
            title="Rata-rata Penonton berdasarkan 10 Karakter Teratas",
            orientation='h',
            labels={'Viewers (Millions)': 'Rata-rata Penonton (Juta)', 'Character': 'Karakter'}
        )
        fig_char_viewers.update_yaxes(categoryorder="total ascending")
        fig_char_viewers.update_traces(marker_color='#FFD700') # Warna emas
        fig_char_viewers.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_char_viewers, use_container_width=True)
        
        # Wawasan
        st.subheader("Analisis & Rekomendasi")
        
        st.markdown("""
        **Analisis Deskriptif:**
        * Dasbor menunjukkan **{count}** episode dari **{season_count}** musim (dari **{year_start}** hingga **{year_end}**).
        * Rata-rata penonton dalam pilihan ini adalah **{viewers:.2f} juta**.
        * Grafik 'Tren Penonton' menunjukkan puncak sekitar awal 2000-an, konsisten dengan peningkatan awal popularitas besar-besaran acara tersebut.
        """.format(
            count=len(df_ep_filtered),
            season_count=df_ep_filtered['Season №'].nunique(),
            year_start=selected_years[0],
            year_end=selected_years[1],
            viewers=avg_viewers
        ))
        
        st.markdown("""
        **Analisis Diagnostik:**
        * Grafik 'Kinerja berdasarkan Musim' mengidentifikasi musim mana (dalam pilihan Anda) yang memiliki rata-rata penonton tertinggi. 
        * Scatter plot 'Durasi vs. Jumlah Penonton' membantu mendiagnosis apakah ada "titik optimal" untuk durasi episode. Seringkali, tidak ada korelasi yang kuat, yang menunjukkan bahwa *konten* lebih penting daripada *durasi*.
        """)
        
        st.markdown("""
        **Analisis Prediktif & Preskriptif:**
        * **Prediktif:** Berdasarkan grafik 'Rata-rata Penonton berdasarkan 10 Karakter Teratas', episode yang menampilkan karakter seperti **SpongeBob SquarePants** dan **Patrick Star** secara konsisten menjadi jangkar penonton acara tersebut. Tren menunjukkan bahwa jumlah penonton untuk episode baru akan tetap kuat selama mereka fokus pada pemeran inti ini.
        * **Preskriptif (Wawasan yang Dapat Ditindaklanjuti):** Untuk mengoptimalkan potensi penonton pada proyek baru atau episode spesial, pertimbangkan alur cerita yang banyak menampilkan pemeran inti (SpongeBob, Patrick, Squidward) yang tidak hanya paling sering muncul tetapi juga terkait dengan episode berkinerja tinggi. Gunakan filter 'Filter berdasarkan Penampilan Karakter' di sidebar untuk menjelajahi ini sendiri!
        """)

except FileNotFoundError:
    st.error(f"Error: File `spongebob_episodes.csv` tidak ditemukan.")
except Exception as e:
    st.error(f"Terjadi kesalahan saat memuat atau memproses data: {e}")
    st.exception(e)
