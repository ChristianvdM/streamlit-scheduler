import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
from io import BytesIO
import base64

# Set black theme using custom CSS
st.set_page_config(page_title="Production Team Scheduler", layout="wide")
st.markdown(
    """
    <style>
        body {
            background-color: #000000;
            color: white;
        }
        .stApp {
            background-color: #000000;
        }
        .css-1d391kg, .css-1v0mbdj, .css-hxt7ib, .css-ffhzg2, .css-1c7y2kd {
            background-color: #000000 !important;
            color: white !important;
        }
        .stButton>button {
            background-color: #444;
            color: white;
        }
        .stDownloadButton>button {
            background-color: #444;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Load and center the logo using Streamlit's image uploader with base64 fallback
with open("image.png", "rb") as img_file:
    encoded = base64.b64encode(img_file.read()).decode()
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{encoded}' width='300'>
        </div>
    """, unsafe_allow_html=True)

st.title("📅 Production Team Scheduler – August 2025")

st.markdown("Upload your **Skills CSV** and **Availability CSV** below. Then click 'Generate Schedule' to preview and download the Excel file.")

skills_file = st.file_uploader("Upload skills CSV", type="csv")
availability_file = st.file_uploader("Upload availability CSV", type="csv")

if skills_file and availability_file:
    # [rest of your scheduling logic remains unchanged below here]
    pass
