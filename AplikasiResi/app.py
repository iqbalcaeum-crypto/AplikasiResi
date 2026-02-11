import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
from streamlit_option_menu import option_menu
import io

# --- 1. KONEKSI KEAMANAN (Membaca dari Secrets) ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Gagal memuat Secrets: {e}")
    st.stop()

wib = pytz.timezone('Asia/Jakarta')

# --- 2. SETTING HALAMAN ---
st.set_page_config(page_title="Zavascan Pro", layout="wide", page_icon="📦")

# CSS untuk mempercantik tampilan
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MENU SIDEBAR ---
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

# --- 4. LOGIKA DETEKSI EKSPEDISI ---
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
        else:
            st.info("Belum ada data di database.")
    except:
        st.error("Gagal mengambil data statistik.")

# ==========================================
# HALAMAN 2: SCAN BARANG
# ==========================================
elif selected == "Scan Barang":
    st.header("🔍 Scanning")
    scan_input = st.text_input("Klik di sini lalu Scan Barcode...", placeholder="Scan Nomor Resi...")
    
    if scan_input:
        res = supabase.table("resi_data").select("*").eq("nomor_resi", scan_input).execute()
        if res.data:
            d = res.data[0]
            if "✅" in str(d.get('status')):
                st.warning(f"⚠️ SUDAH PERNAH SCAN!\n\nBarang: {d.get('nama_barang')}")
            else:
                now = datetime.now(wib)
                supabase.table("resi_data").update({
                    "status": "Sudah Scan ✅",
                    "tanggal": now.strftime("%Y-%m-%d"),
                    "jam": now.strftime("%H:%M:%S")
                }).eq("nomor_resi", scan_input).execute()
                st.success(f"✅ BERHASIL!\n\n**{d.get('nama_barang')}**")
                st.balloons()
        else:
            st.error("❌ Resi tidak ditemukan! Pastikan sudah di-import.")

# ==========================================
# HALAMAN 3: DATA & LAPORAN
# ==========================================
elif selected == "Data & Laporan":
    st.header("📂 Data Warehouse")
    tab_data, tab_lap = st.tabs(["Lihat Semua Data", "Download Excel"])
    
    with tab_data:
        cari = st.text_input("Cari Resi/Nama...")
        res_data = supabase.table("resi_data").select("*").order('jam', ascending=False).execute()
        if res_data.data:
            df = pd.DataFrame(res_data.data)
            if cari:
                df = df[df.apply(lambda r: cari.lower() in r.astype(str).str.lower().values, axis=1)]
            st.dataframe(df[['nomor_resi', 'nama_toko', 'nama_barang', 'status', 'jam']], use_container_width=True, hide_index=True)

    with tab_lap:
        tgl = st.date_input("Pilih Tanggal")
        if st.button("Siapkan File"):
            res_lap = supabase.table("resi_data").select("*").eq("tanggal", tgl.strftime("%Y-%m-%d")).execute()
            if res_lap.data:
                out = io.BytesIO()
                pd.DataFrame(res_lap.data).to_excel(out, index=False)
                st.download_button("📥 Klik Download", out.getvalue(), f"Laporan_{tgl}.xlsx")
            else:
                st.error("Tidak ada data pada tanggal tersebut.")

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
            
            sukses, skip = 0, 0
            bar = st.progress(0)
            
            for i, row in df_imp.iterrows():
                resi = str(row.get('Nomor Resi', row.get('nomor resi', ''))).strip()
                sku = str(row.get('SKU', row.get('sku', '-'))).upper()
                
                # Filter Bonus
                if any(x in sku for x in ["JAHIT", "SOLE", "TAS", "DEKER", "BONUS"]):
                    skip += 1
                    continue
                
                payload = {
                    "nomor_resi": resi,
                    "nama_toko": str(row.get('Nama Toko', row.get('Nama Panggilan Toko BigSeller', '-'))),
                    "nama_penerima": str(row.get('Nama Penerima', '-')),
                    "nama_barang": sku,
                    "jumlah": str(row.get('Jumlah', row.get('jumlah', '1'))),
                    "ekspedisi": deteksi_ekspedisi(resi),
                    "status": "❌ Belum Scan"
                }
                try:
                    supabase.table("resi_data").insert(payload).execute()
                    sukses += 1
                except: pass
                bar.progress((i + 1) / len(df_imp))
            st.success(f"✅ Selesai! Berhasil: {sukses} | Bonus: {skip}")
        except Exception as e:
            st.error(f"Gagal Import: {e}")