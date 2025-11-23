import streamlit as st
import os
from src.agent_brain import get_ai_response, analyze_uploaded_image 
from src.pdf_generator import create_build_pdf

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI PC Agent (Gemini)", page_icon="🤖", layout="wide")
st.title("🤖 AI PC Builder (Powered by Gemini)")

# --- SETUP RESET UPLOADER ---
# variabel dinamis agar uploader bisa di-reset otomatis
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

def reset_uploader():
    st.session_state["uploader_key"] += 1

# --- SIDEBAR (KONTROL & UPLOAD) ---
with st.sidebar:
    st.header("Menu Kontrol")
    
    # 1. Tombol Reset Chat
    if st.button("Reset Percakapan", use_container_width=True):
        st.session_state.messages = []
        if 'last_build_data' in st.session_state:
            del st.session_state['last_build_data']
        st.rerun()
    
    st.divider()
    
    # 2. Fitur Upload Foto
    st.header("Cek Komponen")    
    uploaded_file = st.file_uploader(
        "Pilih foto...", 
        type=["jpg", "png", "jpeg"], 
        key=f"uploader_{st.session_state['uploader_key']}" 
    )
    
    if uploaded_file:
        # Tampilkan preview kecil
        st.image(uploaded_file, caption="Preview Foto", use_container_width=True)
        
        if st.button("Kirim & Analisis", type="primary", use_container_width=True):
            with st.spinner("Sedang mengirim ke AI..."):
                image_bytes = uploaded_file.getvalue()
                
                # 1. Simpan Gambar User ke History (Agar muncul di chat utama)
                st.session_state.messages.append({"role": "user", "content": image_bytes})
                
                # 2. Analisis AI Vision
                analysis_result = analyze_uploaded_image(image_bytes)
                
                # 3. Simpan Jawaban AI ke History
                st.session_state.messages.append({"role": "assistant", "content": analysis_result})
                
                # 4. RESET UPLOADER 
                reset_uploader()
                
                # Refresh halaman
                st.rerun()

# --- INISIALISASI SESSION MESSAGES ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya siap membantu. Mau rakit PC budget berapa? Atau upload foto komponen di sebelah kiri jika bingung."}
    ]

# --- TAMPILKAN HISTORY CHAT ---
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        # Cek tipe konten: Gambar (Bytes) atau Teks (String)
        if isinstance(message["content"], bytes):
            st.image(message["content"], caption="Foto dari User", width=300)
        else:
            st.markdown(message["content"])
        
        # Render Tombol PDF jika jawaban ini hasil rakitan)
        if "build_data" in message and message["build_data"]:
            build_data = message["build_data"]
            pdf_bytes = create_build_pdf(build_data)
            btn_key = f"download_btn_{i}"
            st.download_button(
                label="Download Laporan PDF",
                data=pdf_bytes,
                file_name=f"RakitPC_Hybrid_{i}.pdf",
                mime="application/pdf",
                key=btn_key
            )

# --- INPUT TEXT USER ---
if prompt := st.chat_input("Ketik pesan di sini..."):
    
    # 1. Tampilkan Input User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Proses Jawaban AI
    with st.chat_message("assistant"):
        with st.spinner("Sedang berpikir..."):
            response_text = get_ai_response(prompt, st.session_state.messages)
            st.markdown(response_text)
            
            # Cek apakah ada data rakitan baru untuk PDF
            current_build_data = None
            if 'last_build_data' in st.session_state:
                current_build_data = st.session_state['last_build_data']
                
                # Tampilkan tombol PDF langsung untuk respon ini
                pdf_bytes = create_build_pdf(current_build_data)
                st.download_button(
                    label="Download Laporan PDF",
                    data=pdf_bytes,
                    file_name="RakitPC_Hybrid_New.pdf",
                    mime="application/pdf",
                    key="download_btn_new"
                )
                
                # Bersihkan session sementara
                del st.session_state['last_build_data']

    # 3. Simpan Jawaban AI ke History
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_text,
        "build_data": current_build_data 
    })

    st.rerun()