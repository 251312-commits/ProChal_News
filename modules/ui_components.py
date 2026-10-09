def inject_casino_theme():
    if st.session_state.get('page') == 'login':
        st.markdown(
            """
            <style>
            .block-container {
                padding-top: 2rem !important;
            }
            .stApp {
                background-color: #f4f6f9 !important;
                background-image: none !important;
                color: #1e293b !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                padding: 25px 20px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
            }
            h1, h2, h3 {
                color: #1e3a8a !important;
                text-shadow: none !important;
                text-align: center !important;
                font-weight: 800 !important;
            }
            .user-icon-circle {
                width: 75px;
                height: 75px;
                background: #eff6ff;
                border: 2px solid #3b82f6;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px auto;
                font-size: 36px;
                color: #2563eb;
            }
            .stTextInput > div > div > input {
                background-color: #f8fafc !important;
                color: #0f172a !important;
                font-weight: 600 !important;
                border: 1.5px solid #cbd5e1 !important;
                border-radius: 10px !important;
                height: 48px !important;
                text-align: center !important;
            }
            .stTextInput > div > div > input:focus {
                border-color: #2563eb !important;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
                background-color: #ffffff !important;
            }
            .stTextInput label {
                color: #334155 !important;
                font-weight: 600 !important;
            }
            .stButton > button {
                background: #2563eb !important;
                color: #ffffff !important;
                font-weight: 700 !important;
                font-size: 1rem !important;
                border-radius: 10px !important;
                height: 48px !important;
                border: none !important;
                box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.25) !important;
            }
            .warning-note {
                background-color: #fef2f2;
                border-left: 4px solid #ef4444;
                color: #991b1b;
                padding: 12px;
                border-radius: 8px;
                font-size: 0.85rem;
                text-align: left;
                margin-top: 15px;
                margin-bottom: 15px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <style>
            .block-container {
                padding-top: 1.2rem !important;
                padding-bottom: 1rem !important;
            }
            header[data-testid="stHeader"] {
                background-color: transparent !important;
            }

            .stApp {
                background-color: #05000a !important; 
                background-image: none !important; 
                color: #ffffff;
            }
            .neon-promo-banner {
                display: flex;
                flex-direction: row;
                background-color: #110022;
                border: 2px solid #8A2BE2;
                box-shadow: 0 0 15px #8A2BE2, inset 0 0 10px #8A2BE2;
                margin-top: 5px;
                margin-bottom: 25px;
                padding: 10px;
                border-radius: 5px;
                align-items: stretch;
            }
            .neon-left-box {
                flex: 1.2;
                box-shadow: 0 0 15px rgba(255, 0, 255, 0.5), inset 0 0 10px rgba(255, 0, 255, 0.3);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 10px;
                background: rgba(255, 0, 255, 0.05);
                border-radius: 5px;
            }
            .neon-numbers {
                color: #FFFFFF;
                font-size: 1.8rem;
                font-weight: 900;
                text-shadow: 2px 2px 0px #FF00FF, 0 0 15px #FF00FF;
                text-align: center;
                line-height: 1.2;
            }
            .neon-numbers span { color: #FF00FF; }
            .neon-right-box {
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding-left: 15px;
                text-align: center;
            }
            .neon-logo-text {
                color: #ffffff;
                font-size: 3.5rem;
                font-weight: 900;
                text-shadow: 0 0 20px #8A2BE2, 0 0 40px #FF00FF;
                margin-bottom: -10px;
                letter-spacing: -3px;
            }
            .neon-sub-text {
                color: #FFD700;
                font-weight: 900;
                font-size: 1.1rem;
                text-shadow: 1px 1px 2px #000;
                margin-top: 5px;
            }
            .neon-sub-text-2 { color: #FF6347; font-weight: 900; font-size: 1rem; }
            h1, h2, h3 {
                color: #ffffff !important;
                text-shadow: 0 0 10px #8A2BE2, 0 0 20px #FF00FF !important;
                text-align: center;
            }
            .stButton > button {
                background: linear-gradient(to right, #4B0082, #8A2BE2) !important;
                color: #ffffff !important;
                font-weight: 900 !important;
                border: none !important;
                box-shadow: 0 0 10px #FF00FF;
            }
            .stTextInput > div > div > input {
                background-color: #000000 !important;
                color: #FF00FF !important;
                font-weight: bold;
                border: 2px solid #8A2BE2 !important;
                text-align: center;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
