import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- 1. KONEKSI KEAMANAN ---
try:
    # Memastikan URL dan Key diambil dari Secrets Streamlit Cloud
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Gagal menyambungkan ke Database. Cek kembali pengaturan 'Secrets' di Streamlit Cloud.")
    st.stop()
    # --- DI BAWAH KODE KONEKSI SUPABASE ---
with st.sidebar:
    if st.button("🔌 Tes Koneksi Database"):
        try:
            # Mencoba menarik satu data saja untuk tes
            supabase.table("resi_data").select("count", count="exact").limit(1).execute()
            st.sidebar.success("✅ Koneksi Berhasil!")
        except Exception as e:
            st.sidebar.error("❌ Koneksi Gagal!")
            st.sidebar.code(str(e))

wib = pytz.timezone('Asia/Jakarta')
st.set_page_config(page_title="Zavascan Pro", layout="wide", page_icon="📦")

# --- 2. MENU SIDEBAR ---
with st.sidebar:
    st.title("📦 Zavascan Pro")
    selected = option_menu(
        menu_title="Navigasi",
        options=["Dashboard", "Scan Barang", "Data & Laporan", "Import Data"],
        icons=["house", "qr-code-scan", "table", "cloud-upload"],
        menu_icon="cast",
        default_index=0,
    )
    st.divider()
    st.caption(f"🕒 {datetime.now(wib).strftime('%d %b %Y | %H:%M')}")

# --- FUNGSI PEMBANTU ---
def deteksi_ekspedisi(resi):
    r = str(resi).upper().strip()
    if r.startswith("SPXID"): return "SPX Express"
    if r.startswith(("JD", "JX", "JO", "JP", "JZ")): return "J&T Express"
    return "Lainnya"

# ==========================================
# HALAMAN 1: DASHBOARD
# ==========================================
if selected == "Dashboard":
    st.header("📊 Ringkasan Gudang")
    try:
        res = supabase.table("resi_data").select("status").execute()
        if res.data:
            df_stat = pd.DataFrame(res.data)
            total = len(df_stat)
            sudah = len(df_stat[df_stat['status'].str.contains("✅", na=False)])
            belum = total - sudah
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Resi", f"{total} Pcs")
            c2.metric("Selesai Scan", f"{sudah} Pcs")
            c3.metric("Belum Scan", f"{belum} Pcs")
            st.progress(sudah/total if total > 0 else 0)
    except:
        st.info("Belum ada data masuk.")

# ==========================================
# HALAMAN 2: SCAN BARANG
# ==========================================
elif selected == "Scan Barang":
    st.header("🔍 Scanner")
    scan_input = st.text_input("Klik di sini lalu Scan...", placeholder="Masukkan Nomor Resi...")
    
    if scan_input:
        res = supabase.table("resi_data").select("*").eq("nomor_resi", scan_input).execute()
        if res.data:
            d = res.data[0]
            if "✅" in str(d.get('status')):
                st.warning(f"⚠️ SUDAH SCAN: {d.get('nama_barang')}")
            else:
                now = datetime.now(wib)
                supabase.table("resi_data").update({
                    "status": "Sudah Scan ✅",
                    "tanggal": now.strftime("%Y-%m-%d"),
                    "jam": now.strftime("%H:%M:%S")
                }).eq("nomor_resi", scan_input).execute()
                st.success(f"✅ BERHASIL: {d.get('nama_barang')}")
                st.balloons()
        else:
            st.error("❌ Resi tidak ditemukan! Silakan Import Data dulu.")

# ==========================================
# HALAMAN 3: DATA & LAPORAN
# ==========================================
elif selected == "Data & Laporan":
    st.header("📂 Data Warehouse")
    tab1, tab2 = st.tabs(["Lihat Data", "Download Excel"])
    
    with tab1:
        cari = st.text_input("Cari Resi/Barang...")
        # PERBAIKAN DI SINI: Menggunakan desc=True sesuai library terbaru
        res_data = supabase.table("resi_data").select("*").order('jam', desc=True).execute()
        if res_data.data:
            df = pd.DataFrame(res_data.data)
            if cari:
                df = df[df.apply(lambda r: cari.lower() in r.astype(str).str.lower().values, axis=1)]
            st.dataframe(df[['nomor_resi', 'nama_toko', 'nama_barang', 'status', 'jam']], use_container_width=True, hide_index=True)

    with tab2:
        tgl = st.date_input("Pilih Tanggal")
        if st.button("Generate Laporan"):
            res_lap = supabase.table("resi_data").select("*").eq("tanggal", tgl.strftime("%Y-%m-%d")).execute()
            if res_lap.data:
                out = io.BytesIO()
                pd.DataFrame(res_lap.data).to_excel(out, index=False)
                st.download_button("📥 Download Laporan", out.getvalue(), f"Laporan_{tgl}.xlsx")
            else:
                st.error("Data tidak ditemukan untuk tanggal ini.")

# ==========================================
# HALAMAN 4: IMPORT DATA
# ==========================================
elif selected == "Import Data":
    st.header("📥 Import Marketplace")
    file = st.file_uploader("Upload Excel", type=['xlsx', 'csv'])
    
    if st.button("🚀 Proses Import") and file:
        try:
            df_imp = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            df_imp.columns = df_imp.columns.str.strip()
            
            sukses, gagal = 0, 0
            pbar = st.progress(0)
            
            for i, row in df_imp.iterrows():
                resi = str(row.get('Nomor Resi', row.get('nomor resi', ''))).strip()
                
                payload = {
                    "nomor_resi": resi,
                    "nama_toko": str(row.get('Nama Toko', '-')),
                    "nama_barang": str(row.get('SKU', '-')),
                    "jumlah": str(row.get('Jumlah', '1')),
                    "ekspedisi": deteksi_ekspedisi(resi),
                    "status": "❌ Belum Scan"
                }
                
                # Kita tangkap respon dari Supabase
                try:
                    supabase.table("resi_data").insert(payload).execute()
                    sukses += 1
                except Exception as db_error:
                    gagal += 1
                    # Jika gagal, kita tampilkan alasannya sekali saja sebagai contoh
                    if gagal == 1:
                        st.error(f"Contoh error dari database: {db_error}")
                
                pbar.progress((i + 1) / len(df_imp))
                
            st.success(f"✅ Selesai! Berhasil: {sukses} | Gagal: {gagal}")
            st.info("Jika ada yang gagal, biasanya karena Nomor Resi sudah ada di database (duplikat).")
            
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")
