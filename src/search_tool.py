import os
import re
from dotenv import load_dotenv
from langchain_community.utilities import GoogleSerperAPIWrapper

load_dotenv()

class PriceSearcher:
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY tidak ditemukan di .env")
        self.search = GoogleSerperAPIWrapper(serper_api_key=self.api_key)

    def _extract_price_idr(self, text):
        if not text: return None
        # Regex menangkap: Rp 1.500.000, Rp 1500000, 1.5jt
        price_pattern = r'Rp\s?\.?\s?([0-9]{1,3}(?:\.[0-9]{3})*(?:[0-9]+)?)'
        matches = re.findall(price_pattern, text, re.IGNORECASE)
        
        prices = []
        for match in matches:
            clean_num = match.replace('.', '')
            try:
                val = int(clean_num)
                # Filter angka tidak masuk akal
                if 10_000 < val < 100_000_000: 
                    prices.append(val)
            except:
                continue
        
        if prices: return min(prices) # Ambil termurah yang logis
        return None

    def check_price(self, product_name, category=None):
        """
        Mencari harga dengan Query yang lebih spesifik berdasarkan kategori.
        """
        # Optimasi Query biar gak nyasar ke PC Rakitan
        prefix = "jual"
        if category == 'cpu': prefix = "jual processor"
        elif category == 'gpu': prefix = "jual vga card"
        elif category == 'motherboard': prefix = "jual motherboard"
        elif category == 'ram': prefix = "jual ram pc"
        
        query = f"site:tokopedia.com {prefix} {product_name} harga"
        print(f"Searching: {query}...")
        
        try:
            results = self.search.results(query)
            organic_results = results.get('organic', [])
            if not organic_results: return None

            valid_prices = []
            
            # Blacklist kata kunci "PC Fullset"
            blacklist = ["rakitan", "fullset", "pc gaming", "komputer", "laptop", "notebook", "paket", "bundle", "siap pakai"]

            for item in organic_results[:4]: 
                title = item.get('title', '').lower()
                snippet = item.get('snippet', '').lower()
                full_text = title + " " + snippet

                # 1. Cek Blacklist (Strict)
                if any(bad_word in full_text for bad_word in blacklist):
                    print(f"   Skipped (Blacklist): {title[:30]}...")
                    continue
                
                # 2. Nama produk wajib ada di judul 
                # Misal cari 'Ryzen 5 5600', judul harus ada '5600'
                keywords = product_name.lower().split()
                # Ambil keyword angka/seri aja (misal: 5600, 12400, 3060) karena 'Intel'/'AMD' terlalu umum
                important_keys = [k for k in keywords if any(char.isdigit() for char in k)]
                
                if important_keys:
                    if not any(k in title for k in important_keys):
                         print(f"   Skipped (Name Mismatch): {title[:30]}...")
                         continue

                price = self._extract_price_idr(item.get('title', '') + " " + item.get('snippet', ''))
                if price:
                    valid_prices.append(price)
                    print(f"   Valid: {title[:30]}... -> Rp {price:,}")

            if valid_prices:
                # Ambil Median agar aman dari harga palsu
                valid_prices.sort()
                return int(valid_prices[len(valid_prices)//2])
            
            return None

        except Exception as e:
            print(f"Error searching {product_name}: {e}")
            return None