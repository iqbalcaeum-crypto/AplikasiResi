import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- 1. KONEKSI (DENGAN PEMBERSIH SPASI) ---
try:
    # .strip() di bawah ini gunanya menghapus spasi hantu di awal/akhir URL & Key
    raw_url = st.secrets["SUPABASE_URL"]
    raw_key = st.secrets["SUPABASE_KEY"]
    
    url = raw_url.strip().replace(" ", "")
    key = raw_key.strip().replace(" ", "")
    
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Konfigurasi Secrets bermasalah: {e}")
    st.stop()

wib = pytz.timezone('Asia/Jakarta')

# --- 2. MENU ---
with st.sidebar:
    st.title("📦 ZARS & HYBER")
    selected = option_menu(
        "Menu Utama", 
        ["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=['house', 'qr-code-scan', 'table', 'cloud-upload'], 
        menu_icon="cast", 
        default_index=0
    )

# --- 3. LOGIKA DATA & LAPORAN (PERBAIKAN ERROR ORDER) ---
if selected == "Dashboard":
    st.header("📊 Dashboard")
    st.write("Selamat datang, Pak Bos!")

elif selected == "Data & Laporan":
    st.header("📂 Laporan Gudang")
    try:
        # Gunakan format desc=True untuk versi terbaru
        res = supabase.table("resi_data").select("*").order("jam", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Belum ada data di database.")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")

elif selected == "Import Data":
    st.header("📥 Import Marketplace")
    file = st.file_uploader("Upload Excel", type=['xlsx'])
    if st.button("🚀 Proses") and file:
        st.info("Sedang memproses... Tunggu sampai selesai.")
        # ... kode import tetap sama ...
