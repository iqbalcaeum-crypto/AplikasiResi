import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- KONFIGURASI KEAMANAN ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
wib = pytz.timezone('Asia/Jakarta')

# --- SETTING HALAMAN ---
st.set_page_config(page_title="Zavascan Pro Dashboard", layout="wide", page_icon="📦")

# --- CSS CUSTOM (Agar lebih cantik) ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div.stButton > button:first-child { background-color: #007bff; color: white; border-radius: 5px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- MENU NAVIGASI ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/679/679821.png", width=80) # Logo Gudang
    st.title("Zavascan v3.0")
    selected = option_menu(
        menu_title="Main Menu",
        options=["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=["house", "qr-code-scan", "table", "cloud-upload"],
        menu_icon="cast",
        default_index=0,
    )
    st.info(f"User: Admin Gudang\nTime: {datetime.now(wib).strftime('%H:%M')}")

# --- 1. DASHBOARD (Ringkasan) ---
if selected == "Dashboard":
    st.header("📊 Ringkasan Gudang Hari Ini")
    
    # Ambil data statistik
    res = supabase.table("resi_data").select("status").execute()
    df_stat = pd.DataFrame(res.data)
    
    col1, col2, col3 = st.columns(3)
    if not df_stat.empty:
        total = len(df_stat)
        sudah = len(df_stat[df_stat['status'].str.contains("✅")])
        belum = total - sudah
        
        col1.metric("Total Paket", f"{total} Pcs")
        col2.metric("Selesai Scan", f"{sudah} Pcs", delta=f"{sudah/total*100:.1f}%")
        col3.metric("Belum Scan", f"{belum} Pcs", delta=f"-{belum}", delta_color="inverse")
    else:
        st.info("Belum ada data. Silakan ke menu Import.")

# --- 2. SCAN BARANG ---
elif selected == "Scan Barang":
    st.header("🔍 Scanner Barcode")
    st.write("Arahkan scanner atau ketik nomor resi di bawah ini.")
    
    scan_input = st.text_input("Input Resi", placeholder="Scan disini...", label_visibility="collapsed")
    
    if scan_input:
        res = supabase.table("resi_data").select("*").eq("nomor_resi", scan_input).execute()
        if res.data:
            d = res.data[0]
            if "✅" in str(d.get('status')):
                st.warning(f"⚠️ RESI SUDAH PERNAH SCAN!\n\nBarang: {d.get('nama_barang')}")
            else:
                now = datetime.now(wib)
                supabase.table("resi_data").update({
                    "status": "Sudah Scan ✅",
                    "tanggal": now.strftime("%Y-%m-%d"),
                    "jam": now.strftime("%H:%M:%S")
                }).eq("nomor_resi", scan_input).execute()
                st.success(f"✅ BERHASIL SCAN!\n\n**{d.get('nama_barang')}**")
                st.balloons()
        else:
            st.error("❌ Resi tidak ditemukan di database!")

# --- 3. DATA & LAPORAN ---
elif selected == "Data & Laporan":
    st.header("📂 Data & Laporan")
    
    tab1, tab2 = st.tabs(["Lihat Data", "Download Excel"])
    
    with tab1:
        search = st.text_input("Cari Nama/Resi/Barang...")
        data_res = supabase.table("resi_data").select("*").order('jam', ascending=False).execute()
        if data_res.data:
            df = pd.DataFrame(data_res.data)
            if search:
                df = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]
            st.dataframe(df[['nomor_resi', 'nama_toko', 'nama_barang', 'status', 'jam']], use_container_width=True, hide_index=True)

    with tab2:
        tgl = st.date_input("Pilih Tanggal")
        if st.button("Generate Laporan"):
            res_lap = supabase.table("resi_data").select("*").eq("tanggal", tgl.strftime("%Y-%m-%d")).execute()
            if res_lap.data:
                output = io.BytesIO()
                pd.DataFrame(res_lap.data).to_excel(output, index=False)
                st.download_button("📥 Download Excel", output.getvalue(), f"Laporan_{tgl}.xlsx")
            else:
                st.error("Data tanggal tersebut kosong.")

# --- 4. IMPORT DATA ---
elif selected == "Import Data":
    st.header("📥 Import Data Marketplace")
    st.write("Gunakan menu ini untuk memasukkan data resi dari Excel Shopee/Lazada/TikTok.")
    
    file = st.file_uploader("Pilih File Excel/CSV", type=['xlsx', 'csv'])
    if st.button("🚀 Mulai Import"):
        if file:
            # (Gunakan logika import Anda yang lama di sini)
            st.success("Proses Import Selesai!")
        else:
            st.warning("Pilih file dulu.")