from fpdf import FPDF
import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Laporan Rakitan PC Hybrid AI', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def clean_text(text):
    """
    Membersihkan teks dari karakter yang tidak didukung.
    Mengubah karakter aneh menjadi tanda tanya (?) agar PDF tidak error.
    """
    if not isinstance(text, str):
        text = str(text)
    # Paksa encode ke latin-1, ganti error dengan '?', lalu decode balik
    return text.encode('latin-1', 'replace').decode('latin-1')

def create_build_pdf(build_data):
    """
    Membuat file PDF dari data rakitan.
    """
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Tanggal
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(0, 10, f"Tanggal Generate: {clean_text(now)}", 0, 1)
    
    # Total Harga
    total_price = build_data.get('total_real_idr', 0)
    status = build_data.get('status', 'Unknown')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, clean_text(f"Total Estimasi: Rp {total_price:,.0f}"), 0, 1)
    pdf.ln(5)
    
    # Tabel Header
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 10, "Kategori", 1, 0, 'C', 1)
    pdf.cell(100, 10, "Nama Produk", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Harga (IDR)", 1, 1, 'C', 1)
    
    # Isi Tabel
    pdf.set_font("Arial", size=10)
    comps = ['cpu', 'motherboard', 'gpu', 'ram', 'storage', 'psu', 'case', 'cooler']
    
    for comp in comps:
        if comp in build_data:
            item = build_data[comp]
            name = item.get('name', '-')
            
            # Harga
            price = item.get('price_real_idr', item.get('price', 0) * 16000)
            is_owned = item.get('is_owned', False)
            
            if is_owned:
                price_str = "SUDAH PUNYA"
                pdf.set_text_color(0, 100, 0) # Hijau
            else:
                price_str = f"Rp {price:,.0f}"
                pdf.set_text_color(0, 0, 0) # Hitam
            
            # --- PEMBERSIHAN DATA PENTING ---
            # bersihkan nama produk dan string harga sebelum ditulis ke sel PDF
            safe_name = clean_text(name)
            safe_price = clean_text(price_str)
            safe_comp = clean_text(comp.upper())
            
            # Potong nama jika terlalu panjang agar tabel tidak hancur
            if len(safe_name) > 40:
                safe_name = safe_name[:37] + "..."
            
            pdf.cell(40, 10, safe_comp, 1)
            pdf.cell(100, 10, safe_name, 1)
            pdf.cell(50, 10, safe_price, 1, 1, 'R')
            
    # Output
    return pdf.output(dest='S').encode('latin-1')