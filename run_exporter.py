#!/usr/bin/env python
"""
Simple script to run the lineage exporter UI as a standalone Streamlit app.
"""
import streamlit as st
from lineage_exporter_ui import lineage_exporter_tab

# Set page configuration
st.set_page_config(
    page_title="SQL Lineage Exporter",
    page_icon="📊",
    layout="wide"
)

# Add some styling
st.markdown("""
<style>
    .header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1E65F3;
        margin-bottom: 1rem;
    }
    .description {
        font-size: 1.1rem;
        color: #424242;
        margin-bottom: 2rem;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #808080;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.markdown('<div class="header">SQL Lineage Exporter</div>', unsafe_allow_html=True)
st.markdown('<div class="description">Extract, manage, and export SQL lineage data with natural language processing capabilities.</div>', unsafe_allow_html=True)

# Initialize session state
if 'lineage_ready_for_export' not in st.session_state:
    st.session_state.lineage_ready_for_export = False

if 'metadata_ready_for_export' not in st.session_state:
    st.session_state.metadata_ready_for_export = False

# Run the exporter tab
lineage_exporter_tab()

# Footer
st.markdown('<div class="footer">SQL Lineage Analyzer and Exporter v2.0</div>', unsafe_allow_html=True) 