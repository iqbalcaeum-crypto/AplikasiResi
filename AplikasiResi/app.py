import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Zavascan Pro", layout="wide", page_icon="📦")

# --- 2. KONEKSI KE SUPABASE ---
try:
    # Memanggil dari Secrets Streamlit Cloud
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Gagal memuat konfigurasi Secrets. Pastikan SUPABASE_URL dan SUPABASE_KEY sudah benar di settings.")
    st.stop()

wib = pytz.timezone('Asia/Jakarta')

# --- 3. MENU NAVIGASI ---
with st.sidebar:
    st.title("📦 Zavascan Pro")
    selected = option_menu(
        menu_title="Main Menu",
        options=["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=["house", "qr-code-scan", "table", "cloud-upload"],
        menu_icon="cast",
        default_index=0,
    )
    st.divider()
    st.caption(f"Status: Online | {datetime.now(wib).strftime('%H:%M')}")

# --- 4. LOGIKA APLIKASI ---

def deteksi_ekspedisi(resi):
    r = str(resi).upper().strip()
    if r.startswith("SPXID"): return "SPX Express"
    if r.startswith(("JD", "JX", "JO", "JP", "JZ")): return "J&T Express"
    return "Lainnya"

if selected == "Dashboard":
    st.header("📊 Ringkasan Gudang")
    try:
        res = supabase.table("resi_data").select("status").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            total = len(df)
            sudah = len(df[df['status'].str.contains("✅", na=False)])
            c1, c2 = st.columns(2)
            c1.metric("Total Resi", f"{total} Pcs")
            c2.metric("Selesai Scan", f"{sudah} Pcs")
            st.progress(sudah/total if total > 0 else 0)
    except:
        st.info("Belum ada data. Silakan ke menu Import Data.")

elif selected == "Scan Barang":
    st.header("🔍 Scanner")
    scan_input = st.text_input("Klik & Scan Barcode...", placeholder="Masukkan Resi...")
    if scan_input:
        try:
            res = supabase.table("resi_data").select("*").eq("nomor_resi", scan_input).execute()
            if res.data:
                d = res.data[0]
                if "✅" in str(d.get('status')):
                    st.warning(f"SUDAH SCAN: {d.get('nama_barang')}")
                else:
                    now = datetime.now(wib)
                    supabase.table("resi_data").update({
                        "status": "Sudah Scan ✅",
                        "tanggal": now.strftime("%Y-%m-%d"),
                        "jam": now.strftime("%H:%M:%S")
                    }).eq("nomor_resi", scan_input).execute()
                    st.success(f"BERHASIL: {d.get('nama_barang')}")
                    st.balloons()
            else:
                st.error("Resi tidak ditemukan di database!")
        except Exception as e:
            st.error(f"Error Database: {e}")

elif selected == "Data & Laporan":
    st.header("📂 Laporan")
    try:
        # Perbaikan syntax .order terbaru
        res = supabase.table("resi_data").select("*").order("jam", desc=True).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df[['nomor_resi', 'nama_toko', 'nama_barang', 'status', 'jam']], use_container_width=True)
            
            # Fitur Download
            out = io.BytesIO()
            df.to_excel(out, index=False)
            st.download_button("📥 Download Excel", out.getvalue(), "Laporan_Gudang.xlsx")
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")

elif selected == "Import Data":
    st.header("📥 Import Excel")
    file = st.file_uploader("Upload File", type=['xlsx', 'csv'])
    if st.button("Proses Import") and file:
        df_imp = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
        df_imp.columns = df_imp.columns.str.strip()
        
        sukses, gagal = 0, 0
        pbar = st.progress(0)
        for i, row in df_imp.iterrows():
            payload = {
                "nomor_resi": str(row.get('Nomor Resi', row.get('nomor resi', ''))).strip(),
                "nama_toko": str(row.get('Nama Panggilan Toko BigSeller', '-')),
                "nama_barang": str(row.get('SKU', '-')),
                "jumlah": str(row.get('Jumlah', '1')),
                "ekspedisi": deteksi_ekspedisi(str(row.get('Nomor Resi', ''))),
                "status": "❌ Belum Scan"
            }
            try:
                supabase.table("resi_data").insert(payload).execute()
                sukses += 1
            except: 
                gagal += 1
            pbar.progress((i + 1) / len(df_imp))
        st.success(f"Selesai! Berhasil: {sukses}, Gagal/Duplikat: {gagal}")
