import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- 1. KONFIGURASI AWAL (Harus Paling Atas) ---
st.set_page_config(page_title="ZARS & HYBER Warehouse", layout="wide", page_icon="📦")

# --- 2. FUNGSI KONEKSI ---
def init_connection():
    try:
        # Menghapus spasi dan karakter tak terlihat
        url = st.secrets["SUPABASE_URL"].strip().replace(" ", "")
        key = st.secrets["SUPABASE_KEY"].strip().replace(" ", "")
        return create_client(url, key)
    except Exception as e:
        return f"Error Konfigurasi: {e}"

supabase = init_connection()
wib = pytz.timezone('Asia/Jakarta')

# --- 3. SIDEBAR MENU (TETAP MUNCUL MESKIPUN ERROR) ---
with st.sidebar:
    st.title("📦 Gudang ZARS/HYBER")
    selected = option_menu(
        "Main Menu", 
        ["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=['house', 'qr-code-scan', 'table', 'cloud-upload'], 
        menu_icon="cast", default_index=0
    )
    st.divider()
    if isinstance(supabase, str):
        st.error("⚠️ Koneksi Database Gagal")
    else:
        st.success("✅ Database Terhubung")

# --- 4. LOGIKA HALAMAN ---

if selected == "Dashboard":
    st.header("📊 Ringkasan Gudang")
    st.info("Selamat datang! Gunakan menu di samping untuk mulai memproses resi.")

elif selected == "Import Data":
    st.header("📥 Import Data Marketplace")
    st.write("Gunakan menu ini untuk memasukkan data resi dari Excel ke database.")
    
    if isinstance(supabase, str):
        st.error(f"Fitur Import tidak bisa digunakan karena: {supabase}")
    else:
        file = st.file_uploader("Pilih File Excel", type=['xlsx'])
        if st.button("🚀 Mulai Import") and file:
            try:
                df_imp = pd.read_excel(file)
                # Menghapus spasi di nama kolom
                df_imp.columns = df_imp.columns.str.strip()
                
                sukses, gagal = 0, 0
                progress = st.progress(0)
                
                for i, row in df_imp.iterrows():
                    # Ambil data dari kolom Excel
                    resi = str(row.get('Nomor Resi', '')).strip()
                    if not resi or resi == 'nan': continue
                    
                    payload = {
                        "nomor_resi": resi,
                        "nama_toko": str(row.get('Nama Toko', '-')),
                        "nama_barang": str(row.get('SKU', '-')),
                        "jumlah": str(row.get('Jumlah', '1')),
                        "status": "❌ Belum Scan"
                    }
                    
                    try:
                        supabase.table("resi_data").insert(payload).execute()
                        sukses += 1
                    except:
                        gagal += 1
                    
                    progress.progress((i + 1) / len(df_imp))
                
                st.success(f"✅ Selesai! {sukses} data masuk, {gagal} gagal/duplikat.")
            except Exception as e:
                st.error(f"Gagal membaca file: {e}")

elif selected == "Data & Laporan":
    st.header("📂 Laporan Data")
    if isinstance(supabase, str):
        st.error("Koneksi bermasalah.")
    else:
        try:
            # Perbaikan Syntax .order terbaru
            res = supabase.table("resi_data").select("*").order("jam", desc=True).execute()
            if res.data:
                st.dataframe(pd.DataFrame(res.data), use_container_width=True)
            else:
                st.info("Belum ada data resi. Silakan Import dulu.")
        except Exception as e:
            st.error(f"Error Database: {e}")
