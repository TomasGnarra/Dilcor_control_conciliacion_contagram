"""
Estilos CSS y configuracion de tema para Dilcor App.
"""
import streamlit as st

def load_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --primary-red: #E30613;
            --primary-black: #1A1A1A;
            --secondary-black: #2C2C2C;
            --text-white: #FFFFFF;
            --text-gray: #CCCCCC;
            --bg-light: #F8F9FA;
            --card-bg: #FFFFFF;
            --border-color: #E0E0E0;
            --success-green: #0D7C3D;
            --warning-orange: #D4760A;
            --danger-red: #E30613;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: var(--primary-black);
            background-color: var(--bg-light);
        }

        /* --- Header Principal --- */
        .dilcor-header {
            background: var(--primary-black);
            padding: 2.5rem 2rem;
            border-radius: 0 0 16px 16px;
            text-align: center;
            margin: -6rem -4rem 2rem -4rem; /* Hack para cubrir todo el ancho superior */
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            border-bottom: 4px solid var(--primary-red);
        }
        .dilcor-logo {
            font-size: 3.5rem;
            font-weight: 800;
            color: var(--text-white);
            letter-spacing: -2px;
            margin: 0;
            line-height: 1;
        }
        .dilcor-logo span {
            color: var(--primary-red);
        }
        .dilcor-subtitle {
            font-size: 0.9rem;
            color: var(--text-gray);
            letter-spacing: 4px;
            text-transform: uppercase;
            margin-top: 0.5rem;
            font-weight: 500;
        }

        /* --- Metricas (KPI Cards) --- */
        .metric-container {
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border-color);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .metric-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            border-color: var(--primary-black);
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 800;
            color: var(--primary-black);
            line-height: 1.2;
            margin-bottom: 0.2rem;
        }
        .metric-label {
            font-size: 0.8rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        .metric-delta {
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 0.5rem;
            padding: 2px 8px;
            border-radius: 10px;
            background: #f0f0f0;
        }
        
        /* Borde superior de color segun estado */
        .border-top-red { border-top: 4px solid var(--primary-red); }
        .border-top-green { border-top: 4px solid var(--success-green); }
        .border-top-orange { border-top: 4px solid var(--warning-orange); }
        .border-top-black { border-top: 4px solid var(--primary-black); }

        /* --- Tablas / DataFrames --- */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        /* --- Sidebar & Widget Fixes --- */
        section[data-testid="stSidebar"] {
            background-color: var(--primary-black);
            border-right: 1px solid #333;
        }
        /* Forzar texto blanco en sidebar */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3, 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] label, 
        section[data-testid="stSidebar"] span {
            color: var(--text-white) !important;
        }
        
        /* Expanders en Sidebar (Fondo oscuro) */
        section[data-testid="stSidebar"] div[data-testid="stExpander"] {
            background-color: var(--secondary-black);
            border-radius: 8px;
            border: 1px solid #444;
            color: var(--text-white);
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary {
            color: var(--text-white) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] details summary:hover {
            color: var(--primary-red) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p {
            color: var(--text-gray) !important;
        }
        
        /* Radio Buttons & Checkboxes */
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
            background-color: var(--secondary-black);
            border-color: #666;
        }

        /* --- Umbrales de matching (Sidebar config) --- */
        .threshold-panel {
            background: rgba(255,255,255,0.05);
            border: 1px solid #444;
            border-radius: 12px;
            padding: 0.9rem;
            margin-bottom: 0.6rem;
        }
        .threshold-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: var(--text-white);
            margin-bottom: 0.2rem;
        }
        .threshold-help {
            font-size: 0.75rem;
            color: var(--text-gray);
            margin-bottom: 0.5rem;
        }

        
        /* --- Botones --- */
        .stButton button {
            background-color: var(--primary-black);
            color: white;
            border-radius: 6px;
            font-weight: 600;
            border: 1px solid var(--primary-black);
        }
        .stButton button:hover {
            background-color: var(--primary-red);
            border-color: var(--primary-red);
            color: white;
        }
        
        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 4px;
            color: #666;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-red) !important;
            color: white !important;
        }

    </style>
    """, unsafe_allow_html=True)

def render_header():
    st.markdown("""
    <div class="dilcor-header">
        <h1 class="dilcor-logo">D<span>i</span>lcor</h1>
        <div class="dilcor-subtitle">CONTROL DE CONCILIACIÓN BANCARIA</div>
    </div>
    <div style="margin-bottom: 2rem;"></div>
    """, unsafe_allow_html=True)
