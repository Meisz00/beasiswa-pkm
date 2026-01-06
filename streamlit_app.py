import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
import io


# Fungsi Weighted Product Model
def weighted_product(df, id_column, bobot, jenis_kriteria):
    calculation_df = df.copy()
    
    total_bobot = sum(bobot.values())
    bobot_normalized = {k: v / total_bobot for k, v in bobot.items()}

    for col in bobot.keys():
        if jenis_kriteria[col] == "Cost":
            calculation_df[col] = 1 / calculation_df[col]

    calculation_df["Skor WPM"] = np.prod([calculation_df[col] ** bobot_normalized[col] for col in bobot.keys()], axis=0)
    calculation_df["Skor WPM Normalized"] = calculation_df["Skor WPM"] / calculation_df["Skor WPM"].sum()
    
    result_df = pd.concat([df[id_column], calculation_df[["Skor WPM", "Skor WPM Normalized"]]], axis=1)
    return result_df.sort_values(by="Skor WPM", ascending=False)

def find_optimal_allocation(sorted_results):
    cumulative_scores = np.cumsum(sorted_results["Skor WPM Normalized"])
    optimal_count = len(cumulative_scores[cumulative_scores <= 0.8])
    return max(1, optimal_count)

def allocate_funds(result_df, total_dana, num_recipients):
    selected_df = result_df.head(num_recipients).copy()
    total_score = selected_df["Skor WPM"].sum()
    selected_df["Skor WPM Normalized"] = selected_df["Skor WPM"] / total_score
    selected_df["Alokasi Beasiswa"] = selected_df["Skor WPM Normalized"] * total_dana
    selected_df["Alokasi Beasiswa"] = selected_df["Alokasi Beasiswa"].round(0).astype(int)
    return selected_df

# Streamlit UI
st.set_page_config(page_title="Alokasi Beasiswa Pendidikan Mahasiswa Kurang Mampu", layout="wide")

# Inisialisasi session state untuk navigasi dan hasil
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'final_results' not in st.session_state:
    st.session_state.final_results = None
if 'display_results' not in st.session_state:
    st.session_state.display_results = None
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# CSS styling
home_css = """
<style>
    body {
        background-image: url('https://png.pngtree.com/thumb_back/fh260/background/20250423/pngtree-education-savings-and-scholarship-concept-image_17212092.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp {
        background-color: rgba(255, 255, 255, 0.7);
    }
</style>
"""

table_css = """
<style>
    div[data-testid="stTable"] table {
        width: 100%;
        border-collapse: collapse;
    }
    div[data-testid="stTable"] th {
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 10px !important;
        color: black !important;
    }
    div[data-testid="stTable"] td {
        text-align: center !important;
        padding: 8px !important;
    }
</style>
"""

# Sidebar Menu dengan Button
with st.sidebar:
    st.header("Menu")
    if st.button("🏠 Beranda", use_container_width=True):
        st.session_state.current_page = 'home'
        # Reset hasil ketika kembali ke beranda
        st.session_state.final_results = None
        st.session_state.display_results = None
        st.session_state.uploaded_file = None
    if st.button("📖 Tata Cara & Proses Pengerjaan", use_container_width=True):
        st.session_state.current_page = 'tata_cara'
        # Reset hasil ketika kembali ke tata cara
        st.session_state.final_results = None
        st.session_state.display_results = None
        st.session_state.uploaded_file = None
    if st.button("📊 Perhitungan", use_container_width=True):
        st.session_state.current_page = 'perhitungan'
        # Reset hasil ketika masuk ke perhitungan
        st.session_state.final_results = None
        st.session_state.display_results = None

# Halaman-halaman
if st.session_state.current_page == 'home':
    st.markdown(home_css, unsafe_allow_html=True)
    
    st.markdown("<h1 style='color: black !important;'>Alokasi Beasiswa Pendidikan Mahasiswa Kurang Mampu</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: black !important;'>🏠 Selamat Datang di Situs Alokasi Beasiswa Pendidikan</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="home-content">
    Situs ini dirancang untuk membantu Anda menghitung alokasi beasiswa pendidikan menggunakan metode <strong>Weighted Product</strong> dengan modal yang dimiliki.
    <br><br>
    Dengan situs ini, Anda dapat:
    <br>
    - Menghitung alokasi beasiswa pendidikan untuk seluruh alternatif.<br>
    - Menghitung alokasi beasiswa pendidikan dengan jumlah alternatif yang optimal.<br>
    - Menghitung alokasi beasiswa pendidikan dengan jumlah alternatif yang diinginkan.
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.current_page == 'tata_cara':
    st.header("📖 Tata Cara Penggunaan")
    st.write("""
    1. Upload file dalam format **Excel** yang **berisi data teks** hanya untuk ID/label patokan dan **berisi data numerik** untuk seluruh kriteria yang digunakan. Jika terdapat kriteria yang bertipe kategori, maka dapat diubah terlebih dahulu menjadi numerik dengan mengikuti skala pembobotan. Jangan menggunakan skala 0 agar tidak mengganggu perhitungan.
    2. Pilih variabel yang akan digunakan untuk perhitungan.
    3. Tentukan bobot tiap variabel (1-5) dengan ketentuan seperti tabel di bawah, lalu bobot akan dinormalisasi otomatis.
    4. Pilih apakah variabel termasuk **Cost** (semakin kecil semakin baik) atau **Benefit** (semakin besar semakin baik).
    5. Masukkan total dana yang tersedia.
    6. Pilih metode alokasi beasiswa, apakah dana akan dibagi ke seluruh alternatif atau ada nominal tertentu.
    7. Klik **Hitung Alokasi Beasiswa** untuk melihat hasilnya.
    """)
    
    st.subheader("📌 Keterangan Bobot")
    
    html_table = """
    <style>
        .custom-table {
            width: 100%;
            text-align: center;
            border-collapse: collapse;
        }
        .custom-table th, .custom-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
        }
        .custom-table th {
            background-color: #f0f2f6;
        }
    </style>
    <table class="custom-table">
        <tr>
            <th>Nilai Bobot</th>
            <th>Keterangan</th>
        </tr>
        <tr>
            <td>1</td>
            <td>Tidak terlalu penting</td>
        </tr>
        <tr>
            <td>2</td>
            <td>Kurang penting</td>
        </tr>
        <tr>
            <td>3</td>
            <td>Cukup penting</td>
        </tr>
        <tr>
            <td>4</td>
            <td>Penting</td>
        </tr>
        <tr>
            <td>5</td>
            <td>Sangat penting</td>
        </tr>
    </table>
    """
    
    st.markdown(html_table, unsafe_allow_html=True)

    st.subheader("🔢 Proses Pengerjaan")
    st.write("""
    1. Data akan diproses menggunakan metode Weighted Product Model (WPM) sesuai dengan bobot dan jenis kriteria (Cost atau Benefit) yang telah ditentukan.
    2. Normalisasi bobot dilakukan dengan membagi setiap bobot dengan total bobot keseluruhan, sehingga totalnya menjadi 1.
    3. Bobot yang telah dinormalisasi digunakan sebagai pangkat pada setiap kriteria. Jika kriteria adalah Cost, bobotnya dibuat negatif, sedangkan untuk Benefit, bobot tetap positif.
    4. Perhitungan vektor S dilakukan dengan mengalikan setiap nilai kriteria yang telah dipangkatkan berdasarkan bobot normalisasi.
    5. Normalisasi vektor S dilakukan dengan membagi nilai vektor S setiap alternatif dengan total vektor S keseluruhan, sehingga totalnya menjadi 1. Hasil ini disebut sebagai vektor V.
    6. Perangkingan dilakukan dengan mengurutkan nilai vektor V dari yang terbesar ke yang terkecil.
    7. Penentuan alokasi beasiswa dilakukan dengan mengalikan nilai vektor V dengan total modal dana yang tersedia, sehingga beasiswa dialokasikan secara proporsional berdasarkan prioritas.      
    """)

elif st.session_state.current_page == 'perhitungan':
    st.markdown(table_css, unsafe_allow_html=True)
    st.header("📊 Perhitungan Alokasi Beasiswa")

    uploaded_file = st.file_uploader("Upload Data Excel", type=["xlsx"], key="file_uploader")
    
    # Cek apakah file yang di-upload berbeda dari yang sebelumnya
    if uploaded_file is not None:
        if st.session_state.uploaded_file != uploaded_file:
            # Reset hasil ketika file diupload
            st.session_state.final_results = None
            st.session_state.display_results = None
            st.session_state.uploaded_file = uploaded_file
        
        df = pd.read_excel(uploaded_file)

        if df.select_dtypes(include=["object"]).shape[1] > 1:
            st.warning("⚠️ Data yang diupload mengandung kolom dengan tipe data teks. Harap ubah data menjadi numerik untuk kolom kriteria, kecuali kolom label/ID! (Abaikan pesan ini jika kolom kriteria sudah bertipe data numerik).")

        st.write("Data yang diupload:")
        st.dataframe(df)

        string_columns = df.select_dtypes(include=['object']).columns
        id_column = st.selectbox("Pilih kolom ID/Label:", df.columns if len(string_columns) == 0 else string_columns)
        
        available_columns = [col for col in df.columns if col != id_column]
        selected_columns = st.multiselect("Pilih variabel untuk perhitungan:", available_columns)

        bobot = {}
        jenis_kriteria = {}
        for col in selected_columns:
            with st.container():
                st.markdown(f"<div class='box'><b>{col}</b>", unsafe_allow_html=True)
                bobot[col] = st.slider(f"Bobot untuk {col} (1-5):", 1, 5, 3)
                jenis_kriteria[col] = st.radio(f"Jenis Kriteria untuk {col}:", ["Benefit", "Cost"], horizontal=True)
                st.markdown("<hr style='border: 1px solid black;'>", unsafe_allow_html=True)

        total_dana = st.number_input("Total Alokasi Beasiswa (Rp):", min_value=0, value=1000000000, step=1000000)
        
        allocation_type = st.radio(
            "Pilih metode alokasi beasiswa:",
            ["Alokasi untuk Seluruh Alternatif", "Alokasi untuk Jumlah Alternatif Optimal", "Alokasi Custom"],
            horizontal=True
        )

        custom_allocation_count = None
        if allocation_type == "Alokasi Custom":
            custom_allocation_count = st.number_input(
                "Jumlah penerima beasiswa:",
                min_value=1,
                max_value=len(df),
                value=min(5, len(df))
            )

        if st.button("Hitung Alokasi Beasiswa"):
            if len(selected_columns) > 0:
                hasil = weighted_product(df, id_column, bobot, jenis_kriteria)
                
                if allocation_type == "Alokasi untuk Seluruh Alternatif":
                    num_recipients = len(df)
                    st.write(f"📋 **Menampilkan {num_recipients} penerima beasiswa**")
                elif allocation_type == "Alokasi untuk Jumlah Alternatif Optimal":
                    num_recipients = find_optimal_allocation(hasil)
                    st.write(f"🎯 **Jumlah optimal penerima beasiswa: {num_recipients} penerima**")
                else:
                    num_recipients = custom_allocation_count
                    st.write(f"📋 **Menampilkan {num_recipients} penerima beasiswa teratas**")
                
                final_results = allocate_funds(hasil, total_dana, num_recipients)
                
                # Simpan hasil ke session state
                st.session_state.final_results = final_results
                
                display_results = final_results[[id_column, "Alokasi Beasiswa"]].copy()
                display_results["Alokasi Beasiswa"] = display_results["Alokasi Beasiswa"].apply(lambda x: f"Rp{x:,.0f}")
                st.session_state.display_results = display_results

                # Menampilkan grafik
                chart_data = final_results[[id_column, "Alokasi Beasiswa"]].copy()

# Menampilkan hasil jika sudah dihitung sebelumnya
if st.session_state.final_results is not None and st.session_state.display_results is not None:
    st.write("📊 **Hasil Perhitungan Alokasi Beasiswa:**")
    st.table(st.session_state.display_results.set_index(id_column).rename_axis(None))
    
    # Menampilkan grafik
    st.write("📊 **Visualisasi Alokasi Beasiswa:**")
    chart_data = st.session_state.final_results[[id_column, "Alokasi Beasiswa"]].copy()
    chart_data = chart_data.sort_values(by="Alokasi Beasiswa", ascending=False)
    chart = alt.Chart(chart_data).mark_bar(color='#8ab3cf').encode(
        x=alt.X("Alokasi Beasiswa:Q", title="Alokasi Beasiswa (Rp)"),
        y=alt.Y(f"{id_column}:N", sort="-x", title="Mahasiswa"),
        tooltip=[alt.Tooltip(f"{id_column}:N", title="Mahasiswa"), alt.Tooltip("Alokasi Beasiswa:Q", title="Alokasi Beasiswa", format=",")]
    ).properties(
        width=700,
        height=500
    ).configure_axis(
        labelFontSize=12
    )
    st.altair_chart(chart, use_container_width=True)

if st.session_state.final_results is not None:
        # Prepare export results
        export_results = st.session_state.final_results[[id_column, "Alokasi Beasiswa"]].copy()
        export_results["Alokasi Beasiswa"] = export_results["Alokasi Beasiswa"].apply(lambda x: int(x))

        excel_buffer = io.BytesIO()
        export_results.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="📥 Download Hasil Perhitungan (.xlsx)",
            data=excel_buffer,
            file_name=f"Hasil_Alokasi_Beasiswa_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_button_persistent"
        )