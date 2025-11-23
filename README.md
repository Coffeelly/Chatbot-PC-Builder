# Hybrid PC Builder Agent (Indonesian Market)

An intelligent PC Builder Chatbot designed specifically for the Indonesian market.

Unlike standard LLMs that often generate incorrect hardware compatibility or outdated prices, this Hybrid Agent combines the reasoning power of Google Gemini with a deterministic Logic Engine utilizing a comprehensive computer component dataset and Real-time Search API to provide accurate, compatible, and budget-friendly PC builds in Rupiah (IDR).

**Dataset Source:** https://github.com/docyx/pc-part-dataset/tree/main

## Key Features

- Hybrid Logic Engine: Uses a local CSV database and strict Python algorithms to ensure 100% hardware compatibility (e.g., ensuring CPU Socket matches Motherboard, DDR4 vs DDR5 RAM check).
- Real-Time Indonesian Pricing: Integrates with Google Search API to fetch actual prices from local marketplaces (Tokopedia/Shopee) instead of using outdated USD MSRP.
- Visual Component Analysis: Users can upload photos of hardware components, and the AI (Gemini Vision) will identify the model and specifications.
- Dynamic Budget Loop: If the real-time price exceeds the user's budget, the agent automatically recalculates and selects lower-tier non-critical components to fit the budget without user intervention.
- Smart Constraint Handling: Can build a PC around parts the user already owns (e.g., "I already have a GTX 1070, build the rest for 5 million IDR").
- PDF Report Generation: One-click export of the final build recommendation into a professional PDF file.

## System Architecture

This project solves the "LLM Hallucination" problem by separating logic from language generation:

1. The Brain (Gemini 2.0): Understands user intent (Chat, Image, or Constraints).
2. The Logic (Python/Pandas): Selects compatible parts based on strict rules from a local dataset.
3. The Eyes (Search Tool): Verifies the actual price of selected parts on the web.
4. The UI (Streamlit): Delivers the result in an interactive chat interface.

## Tech Stack

- Frontend: Streamlit
- LLM & Vision: Google Gemini 2.0 Flash (langchain-google-genai)
- Orchestration: LangChain (Tools & Agents)
- Data Processing: Pandas (CSV Database)
- Search Engine: Serper.dev (Google Search Wrapper)
- Document Generation: FPDF

## Installation & Setup

Follow these steps to run the project locally using Conda:

### 1. Clone the Repository

```
git clone https://github.com/Coffeelly/Chatbot-PC-Builder.git
cd Chatbot-PC-Builder
```

### 2. Install Dependencies

This project uses an environment.yml file to manage dependencies.

```
conda env create -f environment.yml
conda activate chatbot-pc-builder
```

### 3. Configure API Keys

Create a .env file in the root directory. You need API keys from Google AI Studio and Serper.dev.

```
GOOGLE_API_KEY="your_google_gemini_api_key"
SERPER_API_KEY="your_serper_api_key"
```

### 4. Run the Application

```
streamlit run app.py
```

## Project Structure

```
chatbot-pc-builder/
├── app.py          # Main Streamlit Frontend application
├── environment.yml # Conda environment configuration
├── .env            # API Keys (Not uploaded to GitHub)
├── data/           # CSV Dataset (CPUs, GPUs, Motherboards, etc.)
└── src/
    ├── agent_brain.py   # LangChain Agent configuration & Tool definitions
    ├── logic_engine.py  # Pandas logic for part selection & compatibility
    ├── search_tool.py   # Real-time pricing searcher (Serper)
    └── pdf_generator.py # PDF report generation logic
```

## Demo Video

https://github.com/user-attachments/assets/93d7a840-fa8d-41ef-b5b2-ad2e2c2c7979
