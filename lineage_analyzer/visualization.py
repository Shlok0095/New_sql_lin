# lineage_analyzer/visualization.py
import os
from typing import Dict, List, Set, Tuple, Optional
import csv



class LineageVisualizer:
    """Visualizes SQL lineage information."""
    
    @staticmethod
    def generate_mermaid_diagram(column_mappings: Dict[str, List[str]], 
                               title: str = "SQL Column Lineage") -> str:
        """Generate a Mermaid flowchart diagram for column lineage."""
        result = ["graph TD"]
        result.append(f"    title[{title}]")
        result.append("    classDef table fill:#f9f,stroke:#333,stroke-width:2px")
        result.append("    classDef column fill:#bbf,stroke:#333,stroke-width:1px")
        
        # Track nodes to avoid duplicates
        nodes = set()
        
        # Process mappings
        for target_col, source_cols in column_mappings.items():
            # Extract table and column names
            if '.' in target_col:
                target_table, target_column = target_col.split('.', 1)
            else:
                target_table = "Unknown"
                target_column = target_col
                
            # Create table node if not exists
            target_table_id = f"table_{target_table.replace('.', '_')}"
            if target_table_id not in nodes:
                result.append(f"    {target_table_id}[{target_table}]")
                result.append(f"    class {target_table_id} table")
                nodes.add(target_table_id)
                
            # Create column node if not exists
            target_col_id = f"col_{target_table.replace('.', '_')}_{target_column.replace('.', '_')}"
            if target_col_id not in nodes:
                result.append(f"    {target_col_id}[{target_column}]")
                result.append(f"    class {target_col_id} column")
                result.append(f"    {target_table_id} --> {target_col_id}")
                nodes.add(target_col_id)
                
            # Process source columns
            for source_col in source_cols:
                if not source_col:
                    continue
                    
                # Handle function expressions
                if 'Function:' in source_col:
                    function_id = f"func_{len(nodes)}"
                    result.append(f"    {function_id}[{source_col}]")
                    result.append(f"    {function_id} --> {target_col_id}")
                    nodes.add(function_id)
                    continue
                    
                # Extract table and column names for source
                if '.' in source_col:
                    source_table, source_column = source_col.split('.', 1)
                else:
                    source_table = "Unknown"
                    source_column = source_col
                    
                # Handle function notation
                if ' (in ' in source_column:
                    source_column, func_name = source_column.split(' (in ', 1)
                    func_name = func_name.rstrip(')')
                    source_col = f"{source_table}.{source_column}"
                
                # Create source table node if not exists
                source_table_id = f"table_{source_table.replace('.', '_')}"
                if source_table_id not in nodes:
                    result.append(f"    {source_table_id}[{source_table}]")
                    result.append(f"    class {source_table_id} table")
                    nodes.add(source_table_id)
                    
                # Create source column node if not exists
                source_col_id = f"col_{source_table.replace('.', '_')}_{source_column.replace('.', '_')}"
                if source_col_id not in nodes:
                    result.append(f"    {source_col_id}[{source_column}]")
                    result.append(f"    class {source_col_id} column")
                    result.append(f"    {source_table_id} --> {source_col_id}")
                    nodes.add(source_col_id)
                    
                # Create relationship between source and target column
                result.append(f"    {source_col_id} --> {target_col_id}")
                
        return "\n".join(result)
    
    @staticmethod
    def generate_html_report(column_mappings: Dict[str, List[str]], 
                           title: str = "SQL Column Lineage Report") -> str:
        """Generate an HTML report for column lineage."""
        html = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"    <title>{title}</title>",
            "    <style>",
            "        body { font-family: Arial, sans-serif; margin: 20px; }",
            "        h1 { color: #333; }",
            "        table { border-collapse: collapse; width: 100%; }",
            "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "        th { background-color: #f2f2f2; }",
            "        tr:nth-child(even) { background-color: #f9f9f9; }",
            "        .table-name { color: #9c27b0; font-weight: bold; }",
            "        .column-name { color: #2196f3; }",
            "    </style>",
            "</head>",
            "<body>",
            f"    <h1>{title}</h1>",
            "    <table>",
            "        <tr>",
            "            <th>Target Column</th>",
            "            <th>Source Columns</th>",
            "        </tr>"
        ]
        
        # Add mappings to table
        for target_col, source_cols in column_mappings.items():
            # Format target column with table and column highlighting
            if '.' in target_col:
                target_table, target_column = target_col.split('.', 1)
                formatted_target = f"<span class='table-name'>{target_table}</span>.<span class='column-name'>{target_column}</span>"
            else:
                formatted_target = f"<span class='column-name'>{target_col}</span>"
                
            # Format source columns
            formatted_sources = []
            for source_col in source_cols:
                if not source_col:
                    continue
                    
                if 'Function:' in source_col:
                    formatted_sources.append(f"<i>{source_col}</i>")
                    continue
                    
                if '.' in source_col:
                    source_table, source_column = source_col.split('.', 1)
                    
                    # Handle function notation
                    if ' (in ' in source_column:
                        column_part, func_part = source_column.split(' (in ', 1)
                        func_part = func_part.rstrip(')')
                        formatted_sources.append(
                            f"<span class='table-name'>{source_table}</span>.<span class='column-name'>{column_part}</span> (in {func_part})"
                        )
                    else:
                        formatted_sources.append(
                            f"<span class='table-name'>{source_table}</span>.<span class='column-name'>{source_column}</span>"
                        )
                else:
                    formatted_sources.append(f"<span class='column-name'>{source_col}</span>")
            
            # Add row to table
            html.append("        <tr>")
            html.append(f"            <td>{formatted_target}</td>")
            html.append(f"            <td>{', '.join(formatted_sources)}</td>")
            html.append("        </tr>")
        
        # Close HTML
        html.extend([
            "    </table>",
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html)
    
    @staticmethod
    def save_diagram(diagram_content: str, output_path: str) -> None:
        """Save diagram content to a file."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write content to file
            with open(output_path, 'w') as f:
                f.write(diagram_content)
                
            print(f"Diagram saved to: {output_path}")
            
        except Exception as e:
            print(f"Error saving diagram: {str(e)}")
    
    @staticmethod
    def generate_text_report(column_mappings: Dict[str, List[str]]) -> str:
        """Generate a simple text report of column lineage."""
        lines = ["SQL Column Lineage Report", "=" * 25, ""]
        
        # Group by target table
        table_groups = {}
        for target_col, source_cols in column_mappings.items():
            if '.' in target_col:
                target_table, target_column = target_col.split('.', 1)
            else:
                target_table = "Unknown"
                target_column = target_col
                
            if target_table not in table_groups:
                table_groups[target_table] = {}
                
            table_groups[target_table][target_column] = source_cols
            
        # Generate report by table
        for table, columns in table_groups.items():
            lines.append(f"Table: {table}")
            lines.append("-" * (len(table) + 7))
            
            for column, sources in columns.items():
                lines.append(f"  Column: {column}")
                lines.append("    Sources:")
                
                if not sources:
                    lines.append("      No source information available")
                else:
                    for source in sources:
                        if source:
                            lines.append(f"      - {source}")
                
                lines.append("")
            
            lines.append("")
            
        return "\n".join(lines)

class LineageExporter:
    """Exports SQL lineage information to different formats."""
    
    @staticmethod
    def export_source_target_csv(column_mappings: Dict[str, List[str]], output_path: str) -> None:
        """
        Export column lineage to CSV in Source/Target format:
        Source Table, Source Column, Target Table, Target Column
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create CSV with header
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Source Table', 'Source Column', 'Target Table', 'Target Column'])
                
                # Process each mapping
                for target_col, source_cols in column_mappings.items():
                    # Parse target into table and column
                    if '.' in target_col:
                        target_table, target_column = target_col.split('.', 1)
                    else:
                        target_table = "Unknown"
                        target_column = target_col
                    
                    # Process each source
                    for source_col in source_cols:
                        if not source_col:
                            continue
                        
                        # Handle function sources
                        if 'Function:' in source_col:
                            # For functions, use function name as source
                            writer.writerow(['Function', source_col, target_table, target_column])
                            continue
                        
                        # Parse source into table and column
                        if '.' in source_col:
                            source_table, source_column = source_col.split('.', 1)
                            
                            # Handle function notation
                            if ' (in ' in source_column:
                                source_column, func_name = source_column.split(' (in ', 1)
                                func_name = func_name.rstrip(')')
                            
                            writer.writerow([source_table, source_column, target_table, target_column])
                        else:
                            writer.writerow(['Unknown', source_col, target_table, target_column])
            
            print(f"Source-Target CSV exported to: {output_path}")
            
        except Exception as e:
            print(f"Error exporting to Source-Target CSV: {str(e)}")
    
    @staticmethod
    def export_metadata_csv(metadata_store, output_path: str) -> None:
        """
        Export metadata to CSV in format:
        Table Name, Column Name, Table Description, Column Description
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create CSV with header
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Table Name', 'Column Name', 'Table Description', 'Column Description'])
                
                # Process metadata
                for db_name, tables in metadata_store.metadata.items():
                    for table_name, columns in tables.items():
                        # Try to get table description
                        table_desc = ""
                        if '_table_properties' in columns:
                            table_desc = columns['_table_properties'].get('description', '')
                        
                        for column_name, properties in columns.items():
                            # Skip special properties entry
                            if column_name == '_table_properties':
                                continue
                                
                            # Get column description if available
                            column_desc = properties.get('description', '')
                            
                            # Write row
                            writer.writerow([table_name, column_name, table_desc, column_desc])
            
            print(f"Metadata CSV exported to: {output_path}")
            
        except Exception as e:
            print(f"Error exporting to Metadata CSV: {str(e)}") 