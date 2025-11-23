import streamlit as st
import os
from src.agent_brain import get_ai_response, analyze_uploaded_image 
from src.pdf_generator import create_build_pdf

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="AI PC Agent (Gemini)", page_icon="🤖", layout="wide")
st.title("🤖 AI PC Builder (Powered by Gemini)")

# --- CSS HACK ---
st.markdown("""
<style>
    .stChatInput { padding-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔧 Menu Kontrol")
    if st.button("🗑️ Reset Percakapan", use_container_width=True):
        st.session_state.messages = []
        # Hapus data sisa jika ada
        if 'last_build_data' in st.session_state: del st.session_state['last_build_data']
        if 'uploader_key' in st.session_state: st.session_state['uploader_key'] += 1
        st.rerun()
    
    st.divider()
    
    st.header("📸 Cek Komponen")
    st.info("Bingung nama komponen? Upload fotonya di sini.")
    
    # Key dinamis untuk reset uploader
    if "uploader_key" not in st.session_state: st.session_state["uploader_key"] = 0
    
    uploaded_file = st.file_uploader(
        "Pilih foto...", type=["jpg", "png", "jpeg"], 
        key=f"uploader_{st.session_state['uploader_key']}"
    )
    
    if uploaded_file:
        st.image(uploaded_file, caption="Preview", use_container_width=True)
        if st.button("🔍 Kirim & Analisis", type="primary", use_container_width=True):
            with st.spinner("Menganalisis..."):
                img_bytes = uploaded_file.getvalue()
                st.session_state.messages.append({"role": "user", "content": img_bytes})
                res = analyze_uploaded_image(img_bytes)
                st.session_state.messages.append({"role": "assistant", "content": res})
                st.session_state["uploader_key"] += 1 # Reset uploader
                st.rerun()

# --- INIT SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya siap membantu. Mau rakit PC budget berapa? Atau upload foto komponen jika bingung."}
    ]

# --- RENDER HISTORY ---
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if isinstance(message["content"], bytes):
            st.image(message["content"], caption="Foto User", width=300)
        else:
            st.markdown(message["content"])
        
        # Render Tombol PDF dari History
        if "build_data" in message and message["build_data"]:
            pdf_bytes = create_build_pdf(message["build_data"])
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_bytes,
                file_name=f"RakitPC_Hybrid_{i}.pdf",
                mime="application/pdf",
                key=f"hist_btn_{i}"
            )

# --- INPUT USER ---
if prompt := st.chat_input("Ketik pesan di sini..."):
    
    # 1. BERSIHKAN DATA LAMA 
    if 'last_build_data' in st.session_state:
        del st.session_state['last_build_data']

    # 2. Tampilkan Input User
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Proses Jawaban AI
    with st.chat_message("assistant"):
        with st.spinner("Sedang berpikir..."):
            response_text = get_ai_response(prompt, st.session_state.messages)
            st.markdown(response_text)
            
            # Tangkap Data Rakitan BARU
            current_build_data = None
            if 'last_build_data' in st.session_state:
                current_build_data = st.session_state['last_build_data']
                
                # Render tombol PDF untuk respon SAAT INI
                pdf_bytes = create_build_pdf(current_build_data)
                st.download_button(
                    label="📥 Download Laporan PDF",
                    data=pdf_bytes,
                    file_name="RakitPC_Hybrid_New.pdf",
                    mime="application/pdf",
                    key="new_btn_now"
                )

    # 4. Simpan ke History 
    st.session_state.messages.append({
        "role": "assistant", 
        "content": response_text,
        "build_data": current_build_data 
    })

    st.rerun()
