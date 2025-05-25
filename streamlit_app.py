import os
import streamlit as st  # type: ignore
import tempfile
from bs4 import BeautifulSoup  # type: ignore
import streamlit.components.v1 as components  # type: ignore
import yaml  # type: ignore
import re
import html
from dotenv import load_dotenv  # type: ignore
import io
import json
import base64
from pathlib import Path
import pandas as pd
import graphviz

# Load environment variables
load_dotenv()

from lineage_analyzer.analyzer import LineageAnalyzer
from lineage_analyzer.extractor import SQLComponentExtractor
from lineage_analyzer.metadata import MetadataStore
from lineage_analyzer.visualization import LineageVisualizer
from lineage_analyzer.utils import read_sql_file
from lineage_analyzer.llm_integration import LLMIntegration

# Import our new lineage exporter component
from lineage_exporter_ui import lineage_exporter_tab

# Set page configuration with dark theme
st.set_page_config(
    page_title="SQL Lineage Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "SQL Lineage Analyzer v2.0 - Powered by Local LLAMA Model"
    }
)

# Add custom CSS
st.markdown("""
<style>
    /* Simplified color palette with eye-friendly colors */
    :root {
        --primary-color: #4f86f7;
        --secondary-color: #6ca0dc;
        --accent-color: #8a5cf5;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
        --background-color: #f8f9fa;
        --card-background: #ffffff;
        --text-color: #333333;
        --text-muted: #6c757d;
        --border-color: #dee2e6;
    }
    
    /* Simplified global styles */
    body {
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        color: var(--text-color);
        background-color: var(--background-color);
    }
    
    h1, h2, h3, h4, h5 {
        font-weight: 600;
        color: var(--text-color);
    }
    
    /* Simplified section headers */
    .section-header {
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        background-color: #f1f5f9;
        border-left: 4px solid var(--primary-color);
        border-radius: 4px;
    }
    
    /* Input container */
    .input-container {
        background-color: white;
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    }
    
    /* Table styling */
    .lineage-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1rem;
    }
    
    .lineage-table th, .lineage-table td {
        padding: 0.75rem;
        text-align: left;
        border: 1px solid var(--border-color);
    }
    
    .lineage-table th {
        background-color: #f1f5f9;
        font-weight: 600;
    }
    
    /* Source and function cells */
    .source-cell {
        color: var(--primary-color);
        font-weight: 500;
    }
    
    .function-cell {
        color: var(--accent-color);
        font-weight: 500;
    }
    
    /* LLM Insights styling */
    .llm-insight-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-color);
        margin: 1rem 0 0.5rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
    }
    
    .llm-icon {
        margin-right: 0.5rem;
    }
    
    .llm-insight-box {
        background-color: white;
        border: 1px solid var(--border-color);
        border-left: 4px solid var(--primary-color);
        border-radius: 6px;
        padding: 1rem;
        font-size: 0.95rem;
        line-height: 1.5;
        margin-bottom: 1.25rem;
    }
    
    /* App header */
    .app-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
        padding: 1rem;
        border-radius: 6px;
        background-color: white;
        border-bottom: 2px solid var(--primary-color);
    }
    
    .main-header {
        font-size: 1.8rem;
        margin: 0;
        color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

def parse_html_to_graph(html_content):
    """
    Parse HTML content to extract lineage data for visualization.
    This extracts relationships from the HTML report and converts it to a format
    suitable for visualization.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        table_rows = soup.find_all('tr')[1:]  # Skip header row
        
        nodes = []
        edges = []
        node_mapping = {}  # To prevent duplicate nodes
        
        for row in table_rows:
            cells = row.find_all('td')
            if len(cells) != 2:
                continue
            
            # Parse target column
            target_cell = cells[0]
            target_spans = target_cell.find_all('span')
            if len(target_spans) == 2:
                target_table = target_spans[0].text
                target_column = target_spans[1].text
                target_id = f"{target_table}.{target_column}"
                
                # Add table node if not exists
                if target_table not in node_mapping:
                    table_id = len(nodes)
                    nodes.append({
                        "id": table_id,
                        "label": target_table,
                        "group": "table",
                        "color": "#f9f",
                        "size": 20
                    })
                    node_mapping[target_table] = table_id
                
                # Add column node if not exists
                if target_id not in node_mapping:
                    col_id = len(nodes)
                    nodes.append({
                        "id": col_id,
                        "label": target_column,
                        "group": "column",
                        "color": "#bbf",
                        "size": 15
                    })
                    node_mapping[target_id] = col_id
                    
                    # Add edge from table to column
                    edges.append({
                        "from": node_mapping[target_table],
                        "to": node_mapping[target_id],
                        "arrows": "to"
                    })
                
                # Parse source columns
                source_cell = cells[1]
                source_pairs = source_cell.get_text(separator=',').split(',')
                
                for source_text in source_pairs:
                    source_text = source_text.strip()
                    if not source_text:
                        continue
                    
                    # Check if it's a function
                    if "Function:" in source_text:
                        # Add function node
                        if source_text not in node_mapping:
                            func_id = len(nodes)
                            nodes.append({
                                "id": func_id,
                                "label": source_text,
                                "group": "function",
                                "color": "#fdd",
                                "size": 10
                            })
                            node_mapping[source_text] = func_id
                        
                        # Add edge from function to target column
                        edges.append({
                            "from": node_mapping[source_text],
                            "to": node_mapping[target_id],
                            "arrows": "to"
                        })
                    elif "." in source_text:
                        # Handle table.column format
                        parts = source_text.split('.')
                        if len(parts) >= 2:
                            source_table = parts[0].strip()
                            source_column = parts[1].strip()
                            source_id = f"{source_table}.{source_column}"
                            
                            # Add source table node if not exists
                            if source_table not in node_mapping:
                                table_id = len(nodes)
                                nodes.append({
                                    "id": table_id,
                                    "label": source_table,
                                    "group": "table",
                                    "color": "#f9f",
                                    "size": 20
                                })
                                node_mapping[source_table] = table_id
                            
                            # Add source column node if not exists
                            if source_id not in node_mapping:
                                col_id = len(nodes)
                                nodes.append({
                                    "id": col_id,
                                    "label": source_column,
                                    "group": "column",
                                    "color": "#bbf",
                                    "size": 15
                                })
                                node_mapping[source_id] = col_id
                                
                                # Add edge from table to column
                                edges.append({
                                    "from": node_mapping[source_table],
                                    "to": node_mapping[source_id],
                                    "arrows": "to"
                                })
                            
                            # Add edge from source column to target column
                            edges.append({
                                "from": node_mapping[source_id],
                                "to": node_mapping[target_id],
                                "arrows": "to"
                            })
        
        # Return graph data
        return {
            "nodes": nodes,
            "edges": edges
        }
        
    except Exception as e:
        st.error(f"Error parsing HTML: {str(e)}")
        return {"nodes": [], "edges": []}

def visualize_graph(graph_data):
    """
    Visualize the graph data using Streamlit.
    Uses vis.js to render the network diagram.
    """
    # Check if we have valid data to visualize
    if not graph_data["nodes"]:
        st.warning("No column relationships found to visualize.")
        return
        
    # Prepare the network visualization HTML
    network_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>SQL Lineage Visualization</title>
        <script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.2/dist/vis-network.min.js"></script>
        <style type="text/css">
            #mynetwork {{
                width: 100%;
                height: 600px;
                border: 1px solid lightgray;
                background-color: #f9f9f9;
            }}
            .legend {{
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid #ddd;
                padding: 10px;
                font-family: Arial, sans-serif;
            }}
            .legend-item {{
                margin: 5px 0;
                display: flex;
                align-items: center;
            }}
            .color-box {{
                width: 15px;
                height: 15px;
                margin-right: 5px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div id="mynetwork"></div>
        <div class="legend">
            <div class="legend-item"><span class="color-box" style="background-color:#f9f;"></span> Table</div>
            <div class="legend-item"><span class="color-box" style="background-color:#bbf;"></span> Column</div>
            <div class="legend-item"><span class="color-box" style="background-color:#fdd;"></span> Function</div>
        </div>
        <script type="text/javascript">
            const nodes = new vis.DataSet({graph_data['nodes']});
            const edges = new vis.DataSet({graph_data['edges']});
            
            const container = document.getElementById('mynetwork');
            const data = {{
                nodes: nodes,
                edges: edges
            }};
            const options = {{
                nodes: {{
                    shape: 'box',
                    margin: 10,
                    font: {{
                        size: 14
                    }}
                }},
                edges: {{
                    width: 2,
                    smooth: {{
                        type: 'curvedCW',
                        roundness: 0.2
                    }}
                }},
                physics: {{
                    enabled: true,
                    solver: 'forceAtlas2Based',
                    forceAtlas2Based: {{
                        gravitationalConstant: -50,
                        centralGravity: 0.01,
                        springLength: 150,
                        springConstant: 0.08
                    }},
                    stabilization: {{
                        iterations: 100
                    }}
                }},
                layout: {{
                    hierarchical: {{
                        enabled: false,
                        direction: "UD",
                        sortMethod: "directed",
                        levelSeparation: 150
                    }}
                }}
            }};
            const network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    
    # Display the network visualization
    components.html(network_html, height=620)

def format_lineage_as_table(column_mappings):
    """Format column mappings as an HTML table for better display"""
    html_content = """
    <table class="lineage-table">
        <tr>
            <th>Target Column</th>
            <th>Source</th>
        </tr>
    """
    
    for target, sources in column_mappings.items():
        html_content += f"<tr><td>{target}</td><td>"
        
        for i, source in enumerate(sources):
            css_class = "function-cell" if "Function:" in source else "source-cell"
            html_content += f'<span class="{css_class}">{html.escape(source)}</span>'
            if i < len(sources) - 1:
                html_content += "<br>"
                
        html_content += "</td></tr>"
        
    html_content += "</table>"
    return html_content

def display_visualizations(viz_tabs, column_mappings, statement_idx, sql_statement=None, use_llm=False):
    """Display different visualizations for column mappings."""
    # Tab 1: Interactive Network
    with viz_tabs[0]:
        try:
            # Parse column mappings into graph data
            graph_data = parse_html_to_graph(
                LineageVisualizer.generate_html_report(column_mappings, "")
            )
            
            # Display interactive graph
            visualize_graph(graph_data)
        except Exception as e:
            st.error(f"Error generating interactive network: {str(e)}")
    
    # Tab 2: Lineage Diagram
    with viz_tabs[1]:
        try:
            st.info("SQL lineage diagram visualizes table and column relationships.")
            
            # Create a Graphviz diagram instead of Mermaid
            graph = graphviz.Digraph()
            graph.attr('node', shape='box', style='filled', color='#4f86f7', 
                      fillcolor='#e7f0ff', fontname='Arial')
            graph.attr('edge', color='#666666')
            graph.attr(rankdir='LR')  # Left to right layout
            
            # Track nodes to avoid duplicates
            added_nodes = set()
            
            # First add all nodes
            for target, sources in column_mappings.items():
                if not target:
                    continue
                    
                # Process target
                if "." in target:
                    target_parts = target.split(".")
                    target_table = target_parts[0].strip()
                    target_column = target_parts[1].strip() if len(target_parts) > 1 else ""
                    target_label = f"{target_table}.{target_column}"
                else:
                    target_label = target
                
                # Add target node if not already added
                if target not in added_nodes:
                    graph.node(target, label=target_label, fillcolor='#d1e7dd', color='#198754')
                    added_nodes.add(target)
                
                # Process sources
                for source in sources:
                    if not source:
                        continue
                    
                    # Add source node if not already added
                    if source not in added_nodes:
                        # Different style for functions
                        if "Function:" in source:
                            graph.node(source, label=source, shape='ellipse', 
                                     fillcolor='#fff3cd', color='#ffc107')
                        else:
                            graph.node(source, label=source)
                        added_nodes.add(source)
                    
                    # Add edge from source to target
                    graph.edge(source, target)
            
            # Display the graph if we have nodes
            if added_nodes:
                st.graphviz_chart(graph, use_container_width=True)
            else:
                st.warning("No relationships found to create a diagram.")
            
            # Also create a text representation as backup
            with st.expander("Text Representation", expanded=False):
                st.markdown("### Lineage Relationships")
                for target, sources in column_mappings.items():
                    if sources:  # Only show if there are sources
                        st.markdown(f"**{target}** ← {', '.join(sources)}")
                    
        except Exception as e:
            st.error(f"Error generating diagram: {str(e)}")
            st.warning("Unable to generate diagram. Using text representation instead.")
            
            # Fallback to text representation
            st.markdown("### Lineage Relationships")
            for target, sources in column_mappings.items():
                if sources:  # Only show if there are sources
                    st.markdown(f"**{target}** ← {', '.join(sources)}")
    
    # Tab 3: HTML Report
    with viz_tabs[2]:
        try:
            html_content = LineageVisualizer.generate_html_report(
                column_mappings,
                f"SQL Lineage Report (Statement {statement_idx+1})"
            )
            components.html(html_content, height=400, scrolling=True)
        except Exception as e:
            st.error(f"Error generating HTML report: {str(e)}")
    
    # Tab 4: Text Report
    with viz_tabs[3]:
        try:
            # Format column mappings as an HTML table
            lineage_table = format_lineage_as_table(column_mappings)
            st.markdown(lineage_table, unsafe_allow_html=True)

            with st.expander("View Raw Text Report"):
                text_content = LineageVisualizer.generate_text_report(column_mappings)
                st.markdown(f"<div class='report-box'>{html.escape(text_content)}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error generating text report: {str(e)}")
    
    # Tab 5: LLM Insights (only shown if SQL statement is provided and LLM is available and enabled)
    if len(viz_tabs) > 4 and sql_statement and use_llm:
        with viz_tabs[4]:
            # Initialize LLM integration
            llm = LLMIntegration()
            
            if not llm.is_enabled():
                st.warning("LLM integration is not available. Please check that you have the transformers and torch packages installed and that the LLAMA model path is correct.")
                st.info("To enable LLM integration, install the required packages with: `pip install transformers torch`")
                st.info("The model should be located at: `/v/region/na/appl/bi/infats/data/files/PROD/userarea/sysdict_da/Llama`")
            else:
                # Display source-target lineage table first
                st.markdown('<div class="llm-insight-header"><span class="llm-icon">🔄</span> Source-Target Lineage</div>', unsafe_allow_html=True)
                
                # Convert column mappings to source-target format
                lineage_data = []
                
                # First, build a mapping of aliases to full table names
                alias_map = {}
                
                # Inspect SQL to extract table aliases
                if sql_statement:
                    # Simple regex to find table names and their aliases
                    # Look for patterns like "FROM table_name [AS] alias" or "JOIN table_name [AS] alias"
                    table_patterns = [
                        r'FROM\s+([a-zA-Z0-9_\.]+)\s+(?:AS\s+)?([a-zA-Z0-9_]+)',
                        r'JOIN\s+([a-zA-Z0-9_\.]+)\s+(?:AS\s+)?([a-zA-Z0-9_]+)'
                    ]
                    
                    for pattern in table_patterns:
                        matches = re.finditer(pattern, sql_statement, re.IGNORECASE)
                        for match in matches:
                            if len(match.groups()) >= 2:
                                table_name = match.group(1).strip()
                                alias = match.group(2).strip()
                                alias_map[alias] = table_name
                
                # Now process the column mappings with alias resolution
                for target_col, source_cols in column_mappings.items():
                    if '.' in target_col:
                        target_parts = target_col.split('.', 1)
                        target_table = target_parts[0].strip()
                        target_column = target_parts[1].strip() if len(target_parts) > 1 else ""
                    else:
                        target_table = "Unknown"
                        target_column = target_col
                    
                    for source_col in source_cols:
                        if not source_col:
                            continue
                        
                        if 'Function:' in source_col:
                            source_table = "Function"
                            source_column = source_col
                        elif '.' in source_col:
                            source_parts = source_col.split('.', 1)
                            alias = source_parts[0].strip()
                            # Use the alias map to get the full table name, if available
                            source_table = alias_map.get(alias, alias)
                            source_column = source_parts[1].strip() if len(source_parts) > 1 else ""
                        else:
                            source_table = "Unknown"
                            source_column = source_col
                        
                        lineage_data.append({
                            "Source Table": source_table,
                            "Source Column": source_column,
                            "Target Table": target_table,
                            "Target Column": target_column
                        })
                
                if lineage_data:
                    df = pd.DataFrame(lineage_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Add download button for lineage data
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Lineage Data (CSV)",
                        data=csv,
                        file_name="lineage_data.csv",
                        mime="text/csv",
                        key=f"download_lineage_csv_{statement_idx}"
                    )
                else:
                    st.info("No column lineage data available for tabular display.")
                
                # Show LLM insights
                with st.spinner("Generating SQL explanation with LLM..."):
                    # First generate and display SQL explanation
                    sql_explanation = llm.generate_sql_explanation(sql_statement)
                    
                    if sql_explanation:
                        st.markdown('<div class="llm-insight-header"><span class="llm-icon">🔍</span> SQL Analysis</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="llm-insight-box">{sql_explanation}</div>', unsafe_allow_html=True)
                        
                        # Add download button for SQL explanation
                        st.download_button(
                            label="Download SQL Analysis (TXT)",
                            data=sql_explanation,
                            file_name="sql_analysis.txt",
                            mime="text/plain",
                            key=f"download_sql_analysis_{statement_idx}"
                        )
                    else:
                        st.error("Failed to generate SQL explanation.")
                
                with st.spinner("Generating lineage insights with LLM..."):
                    # Then generate and display lineage insights
                    lineage_insights = llm.generate_lineage_insights(column_mappings, sql_statement)
                    
                    if lineage_insights:
                        st.markdown('<div class="llm-insight-header"><span class="llm-icon">💡</span> Lineage Insights</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="llm-insight-box">{lineage_insights}</div>', unsafe_allow_html=True)
                        
                        # Add download button for lineage insights
                        st.download_button(
                            label="Download Lineage Insights (TXT)",
                            data=lineage_insights,
                            file_name="lineage_insights.txt",
                            mime="text/plain",
                            key=f"download_lineage_insights_{statement_idx}"
                        )
                    else:
                        st.error("Failed to generate lineage insights.")
                
                # Add a combined download option for all insights
                if sql_explanation and lineage_insights:
                    combined_insights = f"""SQL LINEAGE ANALYSIS REPORT
=========================

SQL ANALYSIS
-----------
{sql_explanation}

LINEAGE INSIGHTS
---------------
{lineage_insights}

SOURCE-TARGET MAPPINGS
--------------------
{df.to_string(index=False) if lineage_data else "No lineage data available"}
"""
                    
                    st.download_button(
                        label="Download Complete Report (TXT)",
                        data=combined_insights,
                        file_name="sql_lineage_report.txt",
                        mime="text/plain",
                        key=f"download_complete_report_{statement_idx}"
                    )
                
                # Add custom CSS for LLM insights
                st.markdown("""
                <style>
                    .llm-insight-header {
                        font-size: 1.4rem;
                        font-weight: 600;
                        color: #1e40af;
                        margin: 1.5rem 0 0.75rem 0;
                        padding-bottom: 0.5rem;
                        border-bottom: 1px solid #bfdbfe;
                        display: flex;
                        align-items: center;
                    }
                    
                    .llm-icon {
                        margin-right: 0.5rem;
                        font-size: 1.3rem;
                    }
                    
                    .llm-insight-box {
                        background-color: #f1f5f9;
                        border: 1px solid #cbd5e1;
                        border-left: 4px solid #2563eb;
                        border-radius: 8px;
                        padding: 1.2rem;
                        font-family: 'Segoe UI', 'Roboto', sans-serif;
                        font-size: 1rem;
                        line-height: 1.6;
                        color: #1e293b;
                        margin-bottom: 1.5rem;
                    }
                    
                    .llm-insight-box strong, .llm-insight-box b {
                        color: #0f172a;
                    }
                    
                    .llm-insight-box ul, .llm-insight-box ol {
                        padding-left: 1.5rem;
                        margin: 0.75rem 0;
                    }
                    
                    .llm-insight-box li {
                        margin-bottom: 0.5rem;
                    }
                    
                    .llm-insight-box h1, .llm-insight-box h2, .llm-insight-box h3 {
                        color: #1e40af;
                        margin: 1rem 0 0.5rem 0;
                    }
                    
                    .llm-insight-box h1 {
                        font-size: 1.4rem;
                    }
                    
                    .llm-insight-box h2 {
                        font-size: 1.3rem;
                    }
                    
                    .llm-insight-box h3 {
                        font-size: 1.2rem;
                    }
                    
                    .llm-insight-box code {
                        background-color: #e2e8f0;
                        padding: 0.2rem 0.4rem;
                        border-radius: 4px;
                        font-family: 'Consolas', 'Monaco', monospace;
                        font-size: 0.9em;
                        color: #334155;
                    }
                    
                    .llm-insight-box table {
                        border-collapse: collapse;
                        width: 100%;
                        margin: 1rem 0;
                    }
                    
                    .llm-insight-box table th, .llm-insight-box table td {
                        border: 1px solid #cbd5e1;
                        padding: 0.5rem;
                        text-align: left;
                    }
                    
                    .llm-insight-box table th {
                        background-color: #e2e8f0;
                        font-weight: 600;
                    }
                </style>
                """, unsafe_allow_html=True)
    elif len(viz_tabs) > 4:
        with viz_tabs[4]:
            st.info("LLM-powered insights are disabled. Enable them in the sidebar configuration.")
            st.markdown("""
            LLM integration provides:
            1. In-depth SQL query analysis
            2. Data lineage insights and recommendations
            3. Potential optimization suggestions
            """)
            
            if not use_llm:
                st.button("Enable LLM Features", on_click=lambda: st.session_state.update({"use_llm": True}))

def metadata_manager_tab():
    """Metadata management tab for importing and exporting metadata."""
    st.header("Metadata Manager")
    st.markdown("Import and manage metadata for tables and columns from various sources")
    
    # Initialize metadata store in session state if not exists
    if 'metadata_store' not in st.session_state:
        st.session_state.metadata_store = MetadataStore()
    
    # Create sub-tabs
    import_tab, paste_tab, view_tab, describe_tab = st.tabs(["Import from File", "Paste Metadata", "Current Metadata", "Auto-Generate Descriptions"])
    
    # Import from file tab
    with import_tab:
        st.subheader("Import from File")
        
        uploaded_file = st.file_uploader(
            "Choose a metadata file", 
            type=["json", "csv", "sql", "pdf"],
            help="Upload JSON, CSV, SQL or PDF files containing database metadata",
            key="metadata_file_uploader"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if uploaded_file is not None:
                # Display file details
                file_details = {
                    "Filename": uploaded_file.name,
                    "File size": f"{uploaded_file.size} bytes",
                    "File type": uploaded_file.type
                }
                st.write("File Details:")
                st.json(file_details)
        
        with col2:
            if uploaded_file is not None:
                if st.button("Import Metadata", type="primary", key="import_metadata_button"):
                    try:
                        # Create a temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                            # Write the uploaded file to the temporary file
                            tmp.write(uploaded_file.getvalue())
                            tmp_path = tmp.name
                        
                        # Import metadata from the temporary file
                        with st.spinner("Importing metadata..."):
                            st.session_state.metadata_store.import_metadata_from_file(tmp_path)
                            
                            # Get metadata stats
                            db_count = len(st.session_state.metadata_store.metadata)
                            table_count = sum(len(tables) for tables in st.session_state.metadata_store.metadata.values())
                            
                            # Show success message
                            st.success(f"Successfully imported metadata: {db_count} databases, {table_count} tables")
                        
                        # Remove the temporary file
                        os.unlink(tmp_path)
                        
                    except Exception as e:
                        st.error(f"Error importing metadata: {str(e)}")
    
    # Paste metadata tab
    with paste_tab:
        st.subheader("Paste Metadata")
        
        format_type = st.selectbox(
            "Select format", 
            ["auto", "json", "csv", "sql"],
            help="Select the format of the pasted metadata",
            key="metadata_format_selector"
        )
        
        pasted_content = st.text_area(
            "Paste metadata content below:", 
            height=300,
            help="Paste JSON, CSV, or SQL metadata content",
            key="metadata_paste_area"
        )
        
        if st.button("Process Pasted Content", type="primary", key="process_pasted_content_button"):
            if pasted_content:
                try:
                    with st.spinner("Processing pasted metadata..."):
                        st.session_state.metadata_store.process_pasted_metadata(pasted_content, format_type)
                        
                        # Get metadata stats
                        db_count = len(st.session_state.metadata_store.metadata)
                        table_count = sum(len(tables) for tables in st.session_state.metadata_store.metadata.values())
                        
                        # Show success message
                        st.success(f"Successfully processed metadata: {db_count} databases, {table_count} tables")
                except Exception as e:
                    st.error(f"Error processing metadata: {str(e)}")
            else:
                st.warning("Please paste metadata content to process")
    
    # Auto-Generate Descriptions tab
    with describe_tab:
        st.subheader("Auto-Generate Descriptions")
        st.markdown("Generate descriptions for tables and columns based on their names")
        
        # Check if there's metadata to describe
        metadata_store = st.session_state.metadata_store
        db_count = len(metadata_store.metadata)
        table_count = sum(len(tables) for tables in metadata_store.metadata.values())
        
        if table_count == 0:
            st.warning("No tables available for description. Please add metadata first.")
        else:
            # Create dropdowns to select which tables/columns to describe
            selected_db = st.selectbox(
                "Select Database:",
                options=list(metadata_store.metadata.keys()),
                key="describe_db_selector"
            )
            
            if selected_db:
                tables = list(metadata_store.metadata[selected_db].keys())
                selected_table = st.selectbox(
                    "Select Table:",
                    options=tables,
                    key="describe_table_selector"
                )
                
                if selected_table:
                    # Option to describe table, columns or both
                    describe_option = st.radio(
                        "What would you like to describe?",
                        ["Table Only", "Columns Only", "Both Table and Columns"],
                        key="describe_option"
                    )
                    
                    # Get columns for the selected table
                    columns = [col for col in metadata_store.metadata[selected_db][selected_table].keys() 
                              if col != '_table_properties']
                    
                    # Show a preview of table and columns
                    st.markdown("### Preview")
                    st.markdown(f"**Table:** {selected_table}")
                    st.markdown("**Columns:**")
                    st.write(", ".join(columns))
                    
                    # Button to generate descriptions
                    if st.button("Generate Descriptions", type="primary", key="generate_descriptions_btn"):
                        with st.spinner("Generating descriptions..."):
                            # Check if LLM is available
                            llm = LLMIntegration()
                            if not llm.is_enabled():
                                st.error("LLM integration is not available. Please check that you have the transformers and torch packages installed and that the LLAMA model path is correct.")
                            else:
                                success = False
                                
                                # Generate table description
                                if describe_option in ["Table Only", "Both Table and Columns"]:
                                    # Prepare prompt for table description
                                    table_prompt = f"Describe the table named '{selected_table}' based on its column names: {', '.join(columns)}"
                                    
                                    # Get description from LLM
                                    table_description = llm.generate_text(table_prompt)
                                    
                                    if table_description:
                                        # Save table description
                                        if '_table_properties' not in metadata_store.metadata[selected_db][selected_table]:
                                            metadata_store.metadata[selected_db][selected_table]['_table_properties'] = {}
                                        
                                        metadata_store.metadata[selected_db][selected_table]['_table_properties']['description'] = table_description
                                        st.success(f"Generated description for table {selected_table}")
                                        success = True
                                
                                # Generate column descriptions
                                if describe_option in ["Columns Only", "Both Table and Columns"]:
                                    # Get table description if available
                                    table_description = ""
                                    if '_table_properties' in metadata_store.metadata[selected_db][selected_table]:
                                        table_description = metadata_store.metadata[selected_db][selected_table]['_table_properties'].get('description', '')
                                    
                                    # Process each column
                                    for column in columns:
                                        # Prepare prompt for column description
                                        column_prompt = f"Describe the column '{column}' in table '{selected_table}'"
                                        if table_description:
                                            column_prompt += f". The table is described as: {table_description}"
                                        
                                        # Get description from LLM
                                        column_description = llm.generate_text(column_prompt)
                                        
                                        if column_description:
                                            # Save column description
                                            if 'description' not in metadata_store.metadata[selected_db][selected_table][column]:
                                                metadata_store.metadata[selected_db][selected_table][column]['description'] = column_description
                                            else:
                                                metadata_store.metadata[selected_db][selected_table][column]['description'] = column_description
                                    
                                    st.success(f"Generated descriptions for columns in {selected_table}")
                                    success = True
                                
                                if success:
                                    st.session_state.metadata_store = metadata_store
                                    st.rerun()
                
                # Option to describe all tables and columns in the database
                st.markdown("---")
                st.markdown("### Batch Description Generation")
                
                if st.button("Generate Descriptions for All Tables", key="generate_all_descriptions_btn"):
                    with st.spinner("Generating descriptions for all tables and columns..."):
                        # Check if LLM is available
                        llm = LLMIntegration()
                        if not llm.is_enabled():
                            st.error("LLM integration is not available. Please check that you have the transformers and torch packages installed and that the LLAMA model path is correct.")
                        else:
                            success = False
                            
                            # Process all tables in the selected database
                            for table_name in metadata_store.metadata[selected_db].keys():
                                # Get columns for the table
                                columns = [col for col in metadata_store.metadata[selected_db][table_name].keys() 
                                          if col != '_table_properties']
                                
                                if not columns:
                                    continue
                                
                                # Generate table description
                                table_prompt = f"Describe the table named '{table_name}' based on its column names: {', '.join(columns)}"
                                table_description = llm.generate_text(table_prompt)
                                
                                if table_description:
                                    # Save table description
                                    if '_table_properties' not in metadata_store.metadata[selected_db][table_name]:
                                        metadata_store.metadata[selected_db][table_name]['_table_properties'] = {}
                                    
                                    metadata_store.metadata[selected_db][table_name]['_table_properties']['description'] = table_description
                                    success = True
                                
                                # Generate column descriptions
                                for column in columns:
                                    # Prepare prompt for column description
                                    column_prompt = f"Describe the column '{column}' in table '{table_name}'"
                                    if table_description:
                                        column_prompt += f". The table is described as: {table_description}"
                                    
                                    # Get description from LLM
                                    column_description = llm.generate_text(column_prompt)
                                    
                                    if column_description:
                                        # Save column description
                                        if column not in metadata_store.metadata[selected_db][table_name]:
                                            metadata_store.metadata[selected_db][table_name][column] = {}
                                        
                                        metadata_store.metadata[selected_db][table_name][column]['description'] = column_description
                                
                            if success:
                                st.session_state.metadata_store = metadata_store
                                st.success(f"Generated descriptions for all tables and columns in {selected_db}")
                                st.rerun()
    
    # Current metadata tab
    with view_tab:
        st.subheader("Current Metadata")
        
        # Get metadata stats
        db_count = len(st.session_state.metadata_store.metadata)
        table_count = sum(len(tables) for tables in st.session_state.metadata_store.metadata.values())
        column_count = sum(
            sum(len(columns) for columns in tables.values())
            for tables in st.session_state.metadata_store.metadata.values()
        )
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Databases", db_count)
        col2.metric("Tables", table_count)
        col3.metric("Columns", column_count)
        
        # Display metadata as JSON
        if db_count > 0:
            st.markdown("### Metadata Content")
            
            # Create expandable sections for each database
            for db_name, tables in st.session_state.metadata_store.metadata.items():
                with st.expander(f"Database: {db_name}"):
                    # Create tables for each database
                    for table_name, columns in tables.items():
                        st.markdown(f"**Table: {table_name}**")
                        
                        # Display table description if available
                        if '_table_properties' in columns and 'description' in columns['_table_properties']:
                            st.markdown(f"*Description: {columns['_table_properties']['description']}*")
                        
                        # Create dataframe for columns
                        if columns:
                            # Process columns into a format suitable for display
                            table_data = []
                            for col_name, properties in columns.items():
                                if col_name == '_table_properties':
                                    continue
                                row = {"Column Name": col_name}
                                
                                # Change "derived_from" to "source"
                                if 'derived_from' in properties:
                                    row["source"] = properties['derived_from']
                                else:
                                    row["source"] = ""
                                
                                # Add other properties
                                for prop_name, prop_value in properties.items():
                                    if prop_name != 'derived_from':
                                        row[prop_name] = prop_value
                                
                                table_data.append(row)
                            
                            # Display as table
                            if table_data:
                                st.table(table_data)
            
            # Export options
            st.markdown("### Export Metadata")
            col1, col2 = st.columns(2)
            
            # JSON export
            with col1:
                if st.button("Export as JSON", key="export_json_button"):
                    # Export to a string
                    json_str = json.dumps(st.session_state.metadata_store.metadata, indent=2)
                    
                    # Create download link
                    b64 = base64.b64encode(json_str.encode()).decode()
                    href = f'<a href="data:application/json;base64,{b64}" download="metadata.json">Download JSON</a>'
                    st.markdown(href, unsafe_allow_html=True)
            
            # CSV export
            with col2:
                if st.button("Export as CSV", key="export_csv_button"):
                    # Create a StringIO to hold the CSV data
                    csv_io = io.StringIO()
                    
                    # Create CSV data
                    # Collect all property keys from all columns
                    property_keys = set()
                    for db in st.session_state.metadata_store.metadata.values():
                        for table in db.values():
                            for column_props in table.values():
                                property_keys.update(column_props.keys())
                    
                    # Sort property keys for consistent output
                    property_keys = sorted(property_keys)
                    
                    # Write header
                    header = ['database_name', 'table_name', 'column_name'] + list(property_keys)
                    csv_io.write(','.join(header) + '\n')
                    
                    # Write data
                    for db_name, tables in st.session_state.metadata_store.metadata.items():
                        for table_name, columns in tables.items():
                            for column_name, properties in columns.items():
                                row = [db_name, table_name, column_name]
                                
                                # Add properties in the same order as the header
                                for key in property_keys:
                                    row.append(str(properties.get(key, '')))
                                
                                csv_io.write(','.join(row) + '\n')
                    
                    # Create download link
                    b64 = base64.b64encode(csv_io.getvalue().encode()).decode()
                    href = f'<a href="data:text/csv;base64,{b64}" download="metadata.csv">Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("No metadata loaded yet. Import metadata using the tabs above.")

def main():
    """Main Streamlit application."""
    st.markdown("""
    <div class="app-header">
        <h1 class="main-header">SQL Lineage Analyzer</h1>
        <div class="header-badge">v2.0</div>
    </div>
    
    <div class="app-description">
        <p>Analyze SQL queries to extract and visualize column-level lineage information with AI-powered insights.</p>
        <div class="feature-badges">
            <span class="feature-badge">Data Flow Visualization</span>
            <span class="feature-badge">Column Mapping</span>
            <span class="feature-badge">AI Insights</span>
        </div>
    </div>
    
    <style>
        .app-header {
            display: flex;
            align-items: center;
            margin-bottom: 0.75rem;
            background-color: #f8fafc;
            padding: 1rem;
            border-radius: 8px;
            border-bottom: 3px solid #2563eb;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .main-header {
            color: #1e293b;
            font-size: 2.2rem;
            margin: 0;
            padding: 0;
            border: none;
        }
        
        .header-badge {
            background-color: #2563eb;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-left: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .app-description {
            margin-bottom: 2rem;
            padding: 0 0.5rem;
        }
        
        .app-description p {
            font-size: 1.1rem;
            color: #475569;
            margin-bottom: 1rem;
            font-weight: 500;
        }
        
        .feature-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
        }
        
        .feature-badge {
            background-color: #e0e7ff;
            color: #3730a3;
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            border: 1px solid #c7d2fe;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for configuration
    st.sidebar.title("Configuration")
    
    # Option to use sample query or upload/paste
    input_option = st.sidebar.radio(
        "Choose input method:",
        ["Upload SQL file", "Paste SQL query", "Use sample query"]
    )
    
    # LLM integration settings
    st.sidebar.markdown("---")
    st.sidebar.subheader("LLM Integration")
    
    # Check if LLM integration is available
    llm = LLMIntegration()
    llm_available = llm.is_enabled()
    
    if not llm_available:
        st.sidebar.warning("LLM integration is not available.")
        st.sidebar.info("To enable LLM features, please:")
        st.sidebar.markdown("1. Install required packages: `pip install transformers torch`")
        st.sidebar.markdown("2. Make sure the LLAMA model is available at the configured path")
        use_llm = False
    else:
        use_llm = st.sidebar.checkbox("Enable LLM-powered insights", value=True, 
                                      help="Use LLM to generate enhanced SQL explanations and lineage insights")
    
    # Metadata options - simplified since we now have a dedicated metadata tab
    st.sidebar.markdown("---")
    st.sidebar.subheader("Metadata")
    use_metadata = st.sidebar.checkbox("Use current metadata", value=True, 
                                    help="Use the metadata from the Metadata Manager",
                                    key="use_current_metadata")
    
    if not use_metadata:
        # Reset metadata store if not using current metadata
        if 'metadata_store' in st.session_state:
            st.session_state.metadata_store = MetadataStore()
    
    # Create main tabs - add our new Exporter tab
    tab1, tab2, tab3, tab4 = st.tabs(["SQL Analysis", "Metadata Manager", "Lineage Exporter", "Settings"])
    
    # Initialize sql_content variable
    sql_content = ""
    
    # SQL Analysis tab
    with tab1:
        # ... [Keep the existing code for SQL input and analysis] ...
        st.markdown("""
        <div class="section-header">
            <span class="section-icon">📄</span>
            <h2>SQL Input</h2>
        </div>
        
        <style>
            .section-header {
                display: flex;
                align-items: center;
                margin-bottom: 1rem;
                background: linear-gradient(90deg, rgba(67, 97, 238, 0.1), transparent);
                padding: 0.5rem 1rem;
                border-radius: 8px;
            }
            
            .section-icon {
                font-size: 1.5rem;
                margin-right: 0.75rem;
            }
            
            .section-header h2 {
                font-size: 1.4rem;
                margin: 0;
                color: var(--primary-color);
                font-weight: 600;
            }
            
            .input-container {
                background-color: white;
                border-radius: 8px;
                padding: 1.5rem;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
                margin-bottom: 1.5rem;
            }
        </style>
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="input-container">', unsafe_allow_html=True)
            
            if input_option == "Upload SQL file":
                uploaded_file = st.file_uploader("Upload SQL file", type=["sql"], key="sql_analysis_file_uploader")
                if uploaded_file:
                    sql_content = uploaded_file.getvalue().decode("utf-8")
                    st.success("SQL file uploaded successfully!")
            
            elif input_option == "Paste SQL query":
                sql_content = st.text_area("Enter your SQL query:", height=200)
            
            else:  # Use sample query
                st.markdown('<p style="color: var(--primary-color); font-weight: 500; margin-bottom: 0.5rem;">Sample SQL Query:</p>', unsafe_allow_html=True)
                sql_content = """
                -- Create a stored procedure for high-value order processing
                CREATE PROCEDURE ProcessHighValueOrders
                AS
                BEGIN
                    -- Create temp table for high value orders
                    SELECT 
                        o.order_id,
                        o.customer_id,
                        c.customer_name,
                        o.order_date,
                        o.total_amount,
                        (o.total_amount * 0.15) AS discount_amount,
                        (o.total_amount * 0.85) AS final_amount,
                        o.status
                    INTO #high_value_orders
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    WHERE o.total_amount > 1000
                    AND o.status = 'processing';
                    
                    -- Update orders with discount
                    UPDATE o
                    SET 
                        o.discount_amount = hvo.discount_amount, 
                        o.total_amount = hvo.final_amount,
                        o.status = 'processed',
                        o.process_date = GETDATE()
                    FROM orders o
                    JOIN #high_value_orders hvo ON o.order_id = hvo.order_id;
                    
                    -- Insert into order history
                    INSERT INTO order_history (order_id, customer_id, action_type, action_date, amount, notes)
                    SELECT 
                        order_id,
                        customer_id,
                        'DISCOUNT_APPLIED',
                        GETDATE(),
                        discount_amount,
                        'High value order automatic discount'
                    FROM #high_value_orders;
                    
                    -- Drop the temp table
                    DROP TABLE #high_value_orders;
                END;
                """
                
                st.code(sql_content, language="sql")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Run analysis button
        if sql_content.strip():
            st.markdown("""
            <div class="action-container">
                <style>
                    .action-container {
                        display: flex;
                        justify-content: center;
                        margin-bottom: 2rem;
                    }
                </style>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Analyze SQL", type="primary", use_container_width=False):
                with st.spinner("Analyzing SQL..."):
                    # Initialize analyzer with metadata
                    metadata_store = st.session_state.metadata_store if 'metadata_store' in st.session_state else MetadataStore()
                    analyzer = LineageAnalyzer(metadata_store)
                    
                    # Extract SQL statements
                    extractor = SQLComponentExtractor()
                    statements = extractor.extract_sql_statements(sql_content)
                    
                    if not statements:
                        st.error("No valid SQL statements found in the input.")
                    else:
                        st.success(f"Found {len(statements)} SQL statement(s) to analyze.")
                        
                        # Create tabs for each statement with more descriptive names
                        tab_labels = [f"Statement {i+1}" for i in range(len(statements))]
                        statement_tabs = st.tabs(tab_labels)
                        
                        # Analyze each statement
                        for i, statement in enumerate(statements):
                            with statement_tabs[i]:
                                # Update metadata store with discovered metadata
                                metadata_store.load_metadata_from_sql(statement)
                                
                                # Analyze statement and store the column mappings
                                column_mappings = analyzer.analyze_sql(statement)
                                
                                # Check if there's lineage data
                                has_lineage = bool(column_mappings)
                                
                                if has_lineage:
                                    # Display visualizations
                                    display_visualizations(
                                        st.tabs(["Interactive Network", "Lineage Diagram", "HTML Report", "Text Report", "LLM Insights"]),
                                        column_mappings,
                                        i,
                                        statement,
                                        use_llm
                                    )
                                else:
                                    st.info("No lineage data found for this statement. It might be a DDL statement or not contain any data transformation logic.")
                                    # Add a unique key to the checkbox
                                    if st.checkbox("Show SQL Statement", value=True, key=f"show_sql_{i}"):
                                        st.code(statement, language="sql")
    
    # Metadata Manager tab
    with tab2:
        metadata_manager_tab()
    
    # Lineage Exporter tab - NEW
    with tab3:
        lineage_exporter_tab()
    
    # Settings tab
    with tab4:
        st.header("Settings")
        st.markdown("Configure the analyzer settings")
        
        # SQL parser options
        st.subheader("SQL Parser Options")
        sql_syntax = st.selectbox("SQL Syntax", ["ANSI", "MySQL", "PostgreSQL", "SQLite", "MSSQL"], index=0)
        
        # Visualization options
        st.subheader("Visualization Options")
        st.checkbox("Show table nodes", value=True, key="settings_show_table_nodes")
        st.checkbox("Show intermediate nodes", value=True, key="settings_show_intermediate_nodes")
        st.color_picker("Table node color", value="#6d28d9", key="settings_table_color")
        st.color_picker("Column node color", value="#2563eb", key="settings_column_color")
        
        # Apply settings
        if st.button("Apply Settings"):
            st.success("Settings applied successfully!")

# Run the app
if __name__ == "__main__":
    main() 