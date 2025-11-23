import pandas as pd
import os
import sys
import re

class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.required_files = {
            "cpu": "cpu.csv",
            "gpu": "video-card.csv",
            "motherboard": "motherboard.csv",
            "ram": "memory.csv",
            "storage": "internal-hard-drive.csv",
            "psu": "power-supply.csv",
            "case": "case.csv",
            "cooler": "cpu-cooler.csv"
        }
        self.data = {} 

    def load_data(self):
        """Memuat data dan membuang data tidak berguna (Harga 0)."""
        print(f"Memuat data dari folder: {self.data_dir}...")
        
        # --- WHITELIST ---
        ALLOWED_SOCKETS = ["AM5", "AM4", "LGA1851", "LGA1700", "LGA1200"]
        
        # 1. LOAD MOTHERBOARD
        mobo_path = os.path.join(self.data_dir, "motherboard.csv")
        if os.path.exists(mobo_path):
            df_mobo = pd.read_csv(mobo_path)
            df_mobo.columns = df_mobo.columns.str.strip()
            
            # Cleaning Harga
            if 'price' in df_mobo.columns:
                df_mobo['price'] = pd.to_numeric(df_mobo['price'].astype(str).str.replace('$', '', regex=False), errors='coerce').fillna(0.0)
                
                # --- HAPUS HARGA 0 ---
                initial_len = len(df_mobo)
                df_mobo = df_mobo[df_mobo['price'] > 5] # Hapus harga di bawah $5 (Error data)
                print(f"   Cleaning Harga Mobo: Dibuang {initial_len - len(df_mobo)} baris data error (Harga $0).")
                # --------------------------------
            
            # Cleaning Socket
            if 'socket' in df_mobo.columns:
                df_mobo['socket'] = df_mobo['socket'].astype(str).str.strip()
                df_mobo = df_mobo[df_mobo['socket'].isin(ALLOWED_SOCKETS)]
                self.valid_sockets = set(df_mobo['socket'].unique())

            self.data['motherboard'] = df_mobo
            print(f"   MOTHERBOARD : {len(df_mobo)} baris.")
        
        # 2. LOAD FILE LAINNYA
        for key, filename in self.required_files.items():
            if key == 'motherboard': continue 
            
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    df.columns = df.columns.str.strip()
                    
                    # Cleaning Harga
                    if 'price' in df.columns:
                        df['price'] = pd.to_numeric(df['price'].astype(str).str.replace('$', '', regex=False), errors='coerce').fillna(0.0)
                        
                        # --- HAPUS HARGA 0 ---
                        before = len(df)
                        df = df[df['price'] > 1] 
                        if len(df) < before:
                            print(f"   {key.upper()}: Dibuang {before - len(df)} baris data harga nol.")
                        # --------------------------------
                    
                    # Logic CPU Socket Inference 
                    if key == 'cpu':
                        df['socket'] = df['name'].apply(self._infer_socket)
                        df = df[df['socket'].isin(self.valid_sockets)]
                    
                    self.data[key] = df
                    print(f"   {key.upper().ljust(12)} : {len(df)} baris.")
                except Exception as e:
                    print(f"   Gagal memuat {filename}: {e}")
            else:
                print(f"   File tidak ditemukan: {filename}")

        return self.data

    def _infer_socket(self, cpu_name):
        """
        Menebak Socket
        """
        name = str(cpu_name).upper()
        
        # --- AMD RYZEN ---
        if "RYZEN" in name:
            match = re.search(r'(\d{4})', name)
            if match:
                model_num = int(match.group(1))
                if model_num >= 7000: return "AM5"
                elif 1000 <= model_num < 6000: return "AM4"
            
            if "THREADRIPPER" in name:
                if "7000" in name: return "sTR5"
                if "39" in name or "3000" in name: return "sTRX4"
                return "TR4"

        elif "ATHLON" in name:
             if re.search(r'2\d\dGE', name) or "3000G" in name or "X4 9" in name: return "AM4"

        # --- INTEL CORE ---
        if "CORE" in name:
            match = re.search(r'(\d{4,5})', name) 
            if match:
                model_num = int(match.group(1))
                # Logic Generasi
                if 15000 <= model_num: return "LGA1851"      # Core Ultra / 15th Gen
                if 12000 <= model_num < 15000: return "LGA1700"  # Gen 12, 13, 14
                if 10000 <= model_num < 12000: return "LGA1200"  # Gen 10, 11
                if 6000 <= model_num < 10000: return "LGA1151"   # Gen 6,7,8,9 (Akan terfilter otomatis nanti jika mobo tak ada)

        elif "PENTIUM" in name or "CELERON" in name:
            match = re.search(r'G(\d{4})', name)
            if match:
                num = int(match.group(1))
                if num >= 6900: return "LGA1700"
                if 5800 <= num < 6900: return "LGA1200"
        
        return None

    def _infer_memory_type(self, mobo_row):
        """Menebak tipe RAM (DDR4/DDR5) berdasarkan Socket & Nama Motherboard."""
        socket = mobo_row['socket']
        name = mobo_row['name'].upper()
        
        # Aturan Pasti
        if socket == "AM5": return "DDR5"
        if socket == "AM4": return "DDR4"
        if socket == "LGA1200": return "DDR4"
        if socket == "LGA1151": return "DDR4"
        
        # Aturan Ambigu (LGA1700 bisa DDR4 atau DDR5)
        if socket == "LGA1700":
            if "DDR4" in name: return "DDR4"
            return "DDR5" # Asumsi default mobo Z690/Z790 modern adalah DDR5 jika tak tertulis DDR4
            
        return "DDR4" 
    def _find_part_specs(self, category, part_name):
        """Mencari spesifikasi teknis dari komponen yang dimiliki user."""
        df = self.data.get(category)
        if df is None: return None
        
        # Cari yang namanya mirip
        results = df[df['name'].str.contains(part_name, case=False)]
        if results.empty: return None
        
        return results.iloc[0] # Kembalikan baris pertama yang cocok
    
    def generate_build(self, budget_idr, owned_parts=None):
        """
        Algoritma Perakit PC.
        """
        if owned_parts is None: owned_parts = {}
        
        IDR_TO_USD_RATE = 16000 
        budget_usd = budget_idr / IDR_TO_USD_RATE
        
        print(f"\nRAKIT PC (Budget Sisa: Rp{budget_idr:,}) | Owned: {list(owned_parts.keys())}")

        build = {}
        total_estimated_usd = 0
        
        # --- CONSTRAINT CHECKING ---
        constraint_socket = None
        constraint_ram_type = None
        
        # Proses Owned Parts
        for category, part_name in owned_parts.items():
            category = category.lower().strip()
            # Normalisasi
            if category == 'vga': category = 'gpu'
            if category == 'processor': category = 'cpu'
            if category == 'mobo': category = 'motherboard'
            
            # Cari spesifikasi
            owned_spec = self._find_part_specs(category, part_name)
            
            if owned_spec is not None:
                build[category] = owned_spec.to_dict()
                if category == 'motherboard':
                    constraint_socket = str(owned_spec['socket']).strip()
                    constraint_ram_type = self._infer_memory_type(owned_spec)
                elif category == 'cpu':
                    constraint_socket = self._infer_socket(owned_spec['name'])
            else:
                # Dummy jika tidak ketemu
                build[category] = {'name': f"{part_name} (Milik User)", 'price': 0, 'is_owned': True}
                if category == 'cpu': constraint_socket = self._infer_socket(part_name)

            build[category]['price'] = 0
            build[category]['is_owned'] = True

        # --- 0.1 ALOKASI BUDGET ---
        # Urutan prioritas pemilihan
        priority_order = [
            'gpu', 'cpu', 'motherboard', 'ram', 
            'storage', 'psu', 'case', 'cooler'
        ]
        
        allocs = {
            "gpu": 0.35, "cpu": 0.20, "motherboard": 0.12, 
            "ram": 0.08, "storage": 0.08, "psu": 0.08, 
            "case": 0.06, "cooler": 0.03
        }

        # --- SELECTOR ---
        def select_item_force(df, target_budget, constraints=None):
            """
            Mencoba memilih item sesuai budget. 
            JIKA GAGAL/KOSONG: Ambil item termurah (Force Select) agar komponen tidak hilang.
            """
            if df is None or df.empty: return None
            
            # Terapkan Constraints (Socket/RAM Type)
            df_filtered = df.copy()
            if constraints:
                for col, val in constraints.items():
                    if val and col in df_filtered.columns:
                        if col == 'socket': 
                            # Logic khusus socket agar lebih loose (AM5 == AM5)
                            df_filtered = df_filtered[df_filtered['socket'].astype(str).str.strip() == val]
                        elif col == 'name_contains':
                            # Logic khusus RAM (DDR4/DDR5)
                            if val == 'DDR5':
                                df_filtered = df_filtered[df_filtered['name'].str.contains("DDR5", case=False)]
                            else:
                                df_filtered = df_filtered[~df_filtered['name'].str.contains("DDR5", case=False)]
            
            # Jika filter constraint membuat data kosong (misal tidak ada Mobo Socket X), kembalikan None 
            if df_filtered.empty: return None
            # Coba cari yang masuk budget
            candidates = df_filtered[df_filtered['price'] <= target_budget].sort_values('price', ascending=False)
            
            if not candidates.empty:
                return candidates.iloc[0]
            else:
                # Jika budget tidak cukup ambil yang termurah dari yang cocok.
                print(f"      Budget habis untuk kategori ini. Mengambil termurah.")
                return df_filtered.sort_values('price').iloc[0]

        # --- 1. LOOPING UTAMA  ---
        for comp in priority_order:
            if comp in build: continue # Skip jika user sudah punya
            
            budget_part = budget_usd * allocs.get(comp, 0.05)
            df = self.data.get(comp)
            
            # Siapkan Constraints
            current_constraints = {}
            
            if comp == 'cpu':
                current_constraints['socket'] = constraint_socket
            elif comp == 'motherboard':
                # Bersihkan kolom socket di DF sementara
                if df is not None: df['socket'] = df['socket'].astype(str).str.replace(' ', '')
                current_constraints['socket'] = constraint_socket
            elif comp == 'ram':
                if not constraint_ram_type: constraint_ram_type = "DDR4" # Default
                current_constraints['name_contains'] = constraint_ram_type
            
            # Pilih Barang
            item = select_item_force(df, budget_part, current_constraints)
            
            if item is not None:
                build[comp] = item.to_dict()
                total_estimated_usd += item['price']
                
                # Update Constraints untuk langkah berikutnya
                if comp == 'cpu' and not constraint_socket:
                    constraint_socket = item['socket']
                if comp == 'motherboard':
                    constraint_ram_type = self._infer_memory_type(item)
                
                print(f"   {comp.upper()}: {item['name']}")
            else:
                # Jika item None, berarti database kosong untuk constraint tersebut
                error_msg = f"Stok Kosong/Tidak Kompatibel ({constraint_socket})"
                print(f"   {comp.upper()}: {error_msg}")
                build[comp] = {"name": f"ERROR: {error_msg}", "price": 0}

        build['estimated_total_usd'] = total_estimated_usd
        build['estimated_total_idr'] = total_estimated_usd * IDR_TO_USD_RATE
        
        return build

    def recommend_any_part(self, category, max_budget_idr):
        """
        Fungsi Universal untuk merekomendasikan komponen apapun berdasarkan budget.
        category: 'cpu', 'gpu', 'ram', 'motherboard', 'storage', 'psu', 'case'
        """
        # Validasi kategori agar sesuai dengan key di self.data
        valid_categories = ['cpu', 'gpu', 'ram', 'motherboard', 'storage', 'psu', 'case', 'cooler']
        category = category.lower().strip()
        
        # jika LLM mengirim 'vga' atau 'processor'
        if category == 'vga' or category == 'video card': category = 'gpu'
        if category == 'processor': category = 'cpu'
        if category == 'ssd' or category == 'hdd': category = 'storage'
        if category == 'mobo': category = 'motherboard'
        
        if category not in valid_categories:
            return {"error": f"Kategori '{category}' tidak valid. Pilih antara: {valid_categories}"}

        df = self.data.get(category)
        if df is None or df.empty:
            return {"error": f"Data untuk kategori {category} kosong."}

        # Konversi 
        budget_usd = max_budget_idr / 16000
        
        # Logika Filter:
        # Ambil barang dengan harga di bawah budget user.
        # Batasi range minimal 10% dari budget agar tidak merekomendasikan barang terlalu murah.
        min_price = budget_usd * 0.1 
        
        candidates = df[
            (df['price'] <= budget_usd) & 
            (df['price'] >= min_price)
        ].sort_values('price', ascending=False) # Prioritaskan yang harganya mendekati budget
        
        if candidates.empty:
            return {"error": f"Tidak ditemukan {category} di bawah Rp {max_budget_idr:,.0f} (Mungkin budget terlalu rendah)."}
            
        # Ambil Top 5
        recommendations = candidates.head(5).to_dict('records')
        
        return {
            "category": category,
            "budget_limit": max_budget_idr,
            "recommendations": recommendations
        }
    