# SQL Lineage Analyzer

A comprehensive tool for analyzing SQL queries, extracting data lineage information, and visualizing data flows with AI-powered insights.

## Overview

SQL Lineage Analyzer helps data engineers, analysts, and governance teams understand how data transforms and flows through SQL queries. The application extracts column-level lineage from SQL code, visualizes relationships, and provides AI-enhanced insights about the transformations.

## Features

- **SQL Analysis**: Parse and analyze complex SQL queries to extract column-level lineage
- **Interactive Visualizations**: View lineage as network diagrams, directed graphs, and tables
- **AI-Powered Insights**: Get detailed explanations of SQL transformations using local LLAMA model
- **Metadata Management**: Import, manage and export table/column metadata
- **Lineage Exporting**: Export lineage information in various formats

## Installation

### Prerequisites

- Python 3.11+ 
- Virtual environment (recommended)

### Setup

1. Clone the repository
2. Create and activate a virtual environment:
   ```
   python -m venv sqllinege-new
   .\sqllinege-new\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements-minimal.txt
   ```
   
4. The local LLM integration uses the LLAMA model located at:
   ```
   /v/region/na/appl/bi/infats/data/files/PROD/userarea/sysdict_da/Llama
   ```

## Running the Application

Launch the application with:

```
streamlit run streamlit_app.py
```

## Components

### 1. SQL Analysis

The SQL Analysis tab is the core of the application, allowing you to:

- Upload SQL files, paste SQL queries, or use sample queries
- Parse and analyze complex SQL statements
- Visualize column-level data lineage
- Explore detailed relationship maps

Visualizations include:
- Interactive network diagrams
- Lineage diagrams with tables and columns
- HTML reports
- Textual lineage representation
- LLM-powered insights (when enabled)

### 2. Metadata Manager

The Metadata Manager helps you:

- Import metadata from files (CSV, JSON, SQL)
- Paste metadata directly
- View and manage current metadata
- Export metadata in various formats
- Auto-generate descriptions for tables and columns (using LLM)

The metadata enhances lineage analysis by providing context and descriptions for database objects.

### 3. Lineage Exporter

The Lineage Exporter tab allows you to:

- Upload SQL files or enter SQL queries
- Upload reference metadata in different formats
- Export lineage data as CSV files
- Generate formatted lineage reports

This component is useful for sharing lineage information with other systems or team members.

### 4. LLM Integration

The application integrates with a local LLAMA model to provide:

- Detailed SQL query explanations
- Data lineage insights and recommendations
- Natural language descriptions of tables and columns

To enable LLM features:
1. Ensure you have the required packages installed: `transformers` and `torch`
2. The model is configured to use the path: `/v/region/na/appl/bi/infats/data/files/PROD/userarea/sysdict_da/Llama`
3. Enable LLM integration in the sidebar

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Ensure all required packages are installed:
   ```
   pip install -r requirements-minimal.txt
   ```

2. **LLM integration issues**: Make sure you have `transformers` and `torch` installed and that the model path exists

3. **Streamlit errors**: Make sure you're using a supported Python version

4. **Visualization problems**: If diagrams don't render correctly, try the text-based representations

## License

[License Information]

## Credits

SQL Lineage Analyzer uses several open-source technologies:
- Streamlit for the web interface
- Hugging Face Transformers for local LLM integration
- Graphviz for lineage visualization
- Various Python libraries for SQL parsing and analysis 