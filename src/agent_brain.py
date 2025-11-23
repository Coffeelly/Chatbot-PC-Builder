import os
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from src.logic_engine import DataManager
from src.search_tool import PriceSearcher
import base64
from langchain_core.messages import HumanMessage

load_dotenv()

# --- SETUP TOOLS ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
data_path = os.path.join(project_root, 'data')
manager = DataManager(data_dir=data_path)
manager.load_data()
searcher = PriceSearcher()

# --- DEFINISI TOOLS  ---

@tool
def recommend_part_tool(category: str, max_budget_idr: int):
    """
    Gunakan alat ini jika user meminta rekomendasi komponen APAPUN (CPU, RAM, Motherboard, PSU, Casing, Storage) secara satuan.
    Input: category (string), max_budget_idr (int).
    """
    return manager.recommend_any_part(category, max_budget_idr)

@tool
def check_real_price_tool(product_name: str):
    """
    Gunakan alat ini untuk mengecek harga asli/real-time suatu produk spesifik di Tokopedia/Indonesia.
    Input: Nama produk.
    Output: Harga dalam Rupiah.
    """
    price = searcher.check_price(product_name)
    if price: return f"Harga real-time {product_name}: Rp {price:,}"
    return f"Harga {product_name} tidak ditemukan."

@tool
def build_pc_tool(
    budget_idr: int, 
    owned_cpu: str = None, 
    owned_gpu: str = None, 
    owned_motherboard: str = None,
    owned_ram: str = None,
    owned_case: str = None,
    owned_storage: str = None,
    owned_psu: str = None,
    owned_cooler: str = None
):
    """
    Merakit PC Fullset dengan validasi harga Real-Time otomatis.
    Juga menangani kasus jika user sudah memiliki komponen tertentu.
    Output berupa dictionary spesifikasi lengkap.
    """
    print(f"\nSTARTING HYBRID BUILD (Target: Rp {budget_idr:,})")
    
    owned_parts = {}
    if owned_cpu: owned_parts['cpu'] = owned_cpu
    if owned_gpu: owned_parts['gpu'] = owned_gpu
    if owned_motherboard: owned_parts['motherboard'] = owned_motherboard
    if owned_ram: owned_parts['ram'] = owned_ram
    if owned_case: owned_parts['case'] = owned_case
    if owned_storage: owned_parts['storage'] = owned_storage
    if owned_psu: owned_parts['psu'] = owned_psu
    if owned_cooler: owned_parts['cooler'] = owned_cooler

    current_budget = budget_idr
    
    for attempt in range(2):
        build_res = manager.generate_build(current_budget, owned_parts=owned_parts)
        if "error" in build_res: return build_res

        print(f"   Cek Harga Real-Time (Percobaan {attempt+1})...")
        total_real = 0
        
        comps = ['cpu', 'motherboard', 'gpu', 'ram', 'storage', 'psu', 'case', 'cooler']
        for comp in comps:
            if comp in build_res and not build_res[comp].get('is_owned', False):
                item_name = build_res[comp]['name']
                real_price = searcher.check_price(item_name, category=comp)
                
                if real_price:
                    build_res[comp]['price_real_idr'] = real_price
                    total_real += real_price
                else:
                    est_price = int(build_res[comp]['price'] * 16000)
                    build_res[comp]['price_real_idr'] = est_price
                    total_real += est_price
            elif comp in build_res and build_res[comp].get('is_owned', False):
                 build_res[comp]['price_real_idr'] = 0

        build_res['total_real_idr'] = total_real
        
        diff = total_real - budget_idr
        if diff <= 0:
            build_res['status'] = "Sukses - Masuk Budget"
            
            # SIMPAN DATA UNTUK PDF
            st.session_state['last_build_data'] = build_res
            
            return build_res
        else:
            print(f"   Overbudget Rp {diff:,.0f}. Downgrading...")
            current_budget -= (diff + 300_000)
            if current_budget < 1_000_000: break

    build_res['status'] = f"Overbudget Rp {total_real - budget_idr:,.0f}"
    
    # SIMPAN DATA MESKIPUN OVERBUDGET
    st.session_state['last_build_data'] = build_res
    
    return build_res

# --- LIST TOOLS ---
tools = [build_pc_tool, recommend_part_tool, check_real_price_tool]

# --- GEMINI SETUP ---
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Anda adalah AI PC Builder Indonesia yang profesional dan santai.\n"
        "TUGAS UTAMA: Membantu user merakit PC gaming/kerja dengan budget Rupiah.\n\n"
        "ATURAN MUTLAK:\n"
        "1. GUNAKAN BAHASA INDONESIA YANG BAIK DAN BENAR untuk seluruh percakapan. DILARANG KERAS menggunakan bahasa Rusia, Mandarin, atau bahasa asing lain selain istilah teknis IT (Inggris).\n"
        "2. Ingat konteks percakapan sebelumnya.\n"
        "3. JIKA USER MEMINTA PERUBAHAN (Ganti budget, ganti komponen, atau 'sesuaikan lagi'), ANDA WAJIB MEMANGGIL TOOL `build_pc_tool` LAGI dengan parameter baru.\n"
        "4. DILARANG KERAS mengarang/menghitung tabel sendiri tanpa memanggil tool. Data harus valid dari Python.\n"
        "5. Tampilkan tabel output rapi dengan Newline per baris.\n"
        "6. Gunakan price_real_idr untuk harga.\n"
        "7. Beri tahu user tombol download PDF ada di bawah chat."
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def get_ai_response(user_input, message_history=[]):
    """
    Fungsi utama yang mengonversi history Streamlit ke LangChain.
    """
    lc_history = []
    
    for msg in message_history:
        content = msg["content"]
        
        # Jika content adalah bytes (Gambar), ubah jadi teks placeholder
        if isinstance(content, bytes):
            content = "[USER MENGUPLOAD FOTO KOMPONEN UNTUK DIANALISIS]"
        # --------------------------------
        
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=str(content)))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=str(content)))
    
    try:
        response = agent_executor.invoke({
            "input": user_input,
            "chat_history": lc_history
        })
        return response["output"]
    except Exception as e:
        return f"Error: {str(e)}"
    
def analyze_uploaded_image(image_bytes):
    """
    Fungsi khusus untuk menganalisis gambar komponen PC.
    """
    # 1. Encode gambar ke Base64 agar bisa dikirim ke API
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    # 2. Setup Model Vision 
    vision_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # 3. Buat Prompt Khusus
    prompt_text = (
        "Anda adalah Ahli Hardware Komputer. Analisis gambar ini.\n"
        "TUGAS:\n"
        "1. Identifikasi apakah gambar ini adalah Komponen PC (CPU, GPU, RAM, Mobo, PSU, Case, Storage, Cooler).\n"
        "2. Jika INI BUKAN komponen PC (misal: pemandangan, hewan, selfie, makanan), katakan: 'Maaf, saya tidak mengenali gambar ini sebagai komponen PC.'\n"
        "3. Jika INI ADALAH komponen PC, sebutkan:\n"
        "   - Nama Produk / Model (seakurat mungkin)\n"
        "   - Spesifikasi Utama (VRAM, Speed, Socket, dll yang terlihat)\n"
        "   - Estimasi kegunaan (misal: 'Cocok untuk gaming 1080p')\n"
        "4. Jawab dalam Bahasa Indonesia yang santai."
    )
    
    # 4. Kirim ke Gemini
    try:
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image_b64}"}
            ]
        )
        response = vision_llm.invoke([message])
        return response.content
    except Exception as e:
        return f"Gagal menganalisis gambar: {str(e)}"
