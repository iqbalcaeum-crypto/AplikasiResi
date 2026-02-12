import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu

# --- 1. DIAGNOSA KONEKSI ---
st.set_page_config(page_title="Zavascan Pro", layout="wide")

def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip("/")
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Masalah pada Secrets atau URL: {e}")
        return None

supabase = init_connection()

if supabase:
    try:
        # Tes panggil database ringan
        supabase.table("resi_data").select("count", count="exact").limit(1).execute()
        # st.success("✅ Database Terhubung!") # Aktifkan ini hanya untuk tes
    except Exception as e:
        st.error(f"❌ Database Supabase sedang OFFLINE atau Paused. Silakan cek dashboard Supabase. Error: {e}")
        st.stop()
else:
    st.stop()

# --- 2. MENU & LOGIKA ---
wib = pytz.timezone('Asia/Jakarta')

with st.sidebar:
    st.title("📦 ZARS & HYBER")
    selected = option_menu(
        "Menu Utama", 
        ["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=['house', 'qr-code-scan', 'table', 'cloud-upload'], 
        menu_icon="cast", 
        default_index=0
    )

# --- HALAMAN DATA & LAPORAN (FIX SYNTAX) ---
if selected == "Data & Laporan":
    st.header("📂 Laporan Gudang")
    try:
        # Gunakan desc=True (Format terbaru 2026)
        res = supabase.table("resi_data").select("*").order("jam", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Belum ada data.")
    except Exception as e:
        st.error(f"Gagal memuat tabel: {e}")

# Sisa kode (Dashboard, Scan, Import) bisa dilanjutkan di bawah sini...
