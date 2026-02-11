import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz
import io

# ==========================================
# 1. KONEKSI DATABASE
# ==========================================
SUPABASE_URL = "https://cflbnbftnpjdzxutgnxu.supabase.co"
SUPABASE_KEY = "sb_publishable_zinSYTqVe4kBjNsFYNNFOw_zvOMvHa9"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except:
    st.error("Koneksi Supabase Gagal.")
    st.stop()

wib = pytz.timezone('Asia/Jakarta')
st.set_page_config(page_title="Zavascan Pro v3", layout="wide")

# ==========================================
# 2. MENU ADMIN & IMPORT (SUDAH DIPINTARKAN)
# ==========================================
with st.sidebar:
    st.header("⚙️ Panel Admin")
    file = st.file_uploader("Upload Excel Marketplace", type=['xlsx', 'csv'])
    
    if st.button("🚀 Proses Import Data") and file:
        try:
            df = pd.read_excel(file) if file.name.endswith('.xlsx') else pd.read_csv(file)
            df.columns = df.columns.str.strip() # Bersihkan spasi di nama kolom
            
            sukses, skip = 0, 0
            for i, row in df.iterrows():
                resi = str(row.get('Nomor Resi', row.get('nomor resi', ''))).strip()
                sku = str(row.get('SKU', row.get('sku', ''))).upper()
                
                # Filter Bonus
                if any(x in sku for x in ["JAHIT", "SOLE", "TAS", "DEKER", "BONUS"]):
                    skip += 1
                    continue
                
                payload = {
                    "nomor_resi": resi,
                    "nama_toko": str(row.get('Nama Toko', 
                    row.get('nama toko', 
                    row.get('Toko', 
                    row.get('Nama Panggilan Toko BigSeller', 
                    row.get('Shop Name', '-')))))),
                    "nama_penerima": str(row.get('Nama Penerima', row.get('Penerima', '-'))),
                    "no_pesanan": str(row.get('Nomor Pesanan', '-')),
                    "nama_barang": sku,
                    "jumlah": str(row.get('Jumlah', row.get('jumlah', row.get('Qty', '1')))),
                    "ekspedisi": "Otomatis", # Akan diupdate saat scan atau via rumus
                    "status": "❌ Belum Scan"
                }
                try:
                    supabase.table("resi_data").insert(payload).execute()
                    sukses += 1
                except: pass
            st.success(f"Berhasil: {sukses} | Bonus Dibuang: {skip}")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    # --- FITUR BARU: DOWNLOAD LAPORAN ---
    st.header("📥 Download Laporan")
    tgl_laporan = st.date_input("Pilih Tanggal Laporan", datetime.now(wib))
    
    if st.button("📊 Siapkan File Excel"):
        tgl_str = tgl_laporan.strftime("%Y-%m-%d")
        res = supabase.table("resi_data").select("*").eq("tanggal", tgl_str).execute()
        
        if res.data:
            df_laporan = pd.DataFrame(res.data)
            # Proses konversi ke Excel di memori
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_laporan.to_excel(writer, index=False, sheet_name='Laporan_Scan')
            
            st.download_button(
                label="📥 Klik Untuk Download Excel",
                data=output.getvalue(),
                file_name=f"Laporan_Zavascan_{tgl_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Tidak ada data hasil scan pada tanggal tersebut.")

# ==========================================
# 3. TAMPILAN SCANNER (UTAMA)
# ==========================================
st.title("📦 Zavascan Pro")
scan_input = st.text_input("🔍 KLIK DISINI LALU SCAN BARCODE...", key="main_scan")

if scan_input:
    res = supabase.table("resi_data").select("*").eq("nomor_resi", scan_input).execute()
    if res.data:
        data = res.data[0]
        if "✅" in str(data.get('status')):
            st.warning(f"⚠️ SUDAH SCAN: {data.get('nama_barang')}")
        else:
            now = datetime.now(wib)
            supabase.table("resi_data").update({
                "status": "Sudah Scan ✅",
                "tanggal": now.strftime("%Y-%m-%d"),
                "jam": now.strftime("%H:%M:%S")
            }).eq("nomor_resi", scan_input).execute()
            st.success(f"✅ BERHASIL: {data.get('nama_barang')}")
            st.balloons()
    else:
        st.error("❌ Resi tidak ditemukan! Import data dulu.")

# ==========================================
# 4. TABEL DATA (MONITORING)
# ==========================================
st.markdown("---")
st.subheader("📊 Data Masuk Terkini")
try:
    response = supabase.table("resi_data").select("*").order('jam', ascending=False).limit(10).execute()
    if response.data:
        df_display = pd.DataFrame(response.data)
        st.dataframe(df_display[['nomor_resi', 'nama_toko', 'nama_barang', 'status', 'jam']], use_container_width=True, hide_index=True)
except:
    st.info("Menunggu data...")