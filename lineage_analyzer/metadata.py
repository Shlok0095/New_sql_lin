# lineage_analyzer/metadata.py

from typing import Dict, List, Optional
import json
import re
import csv
import io

class MetadataStore:
    """Manages metadata about databases, tables, and columns."""
    
    def __init__(self):
        self.metadata = {}  # Structure: {db: {table: {column: properties}}}
        
    def add_database(self, database_name: str) -> None:
        """Add a database to the metadata store."""
        if database_name not in self.metadata:
            self.metadata[database_name] = {}
            
    def add_table(self, table_name: str, database_name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Add a table to the metadata store."""
        if '.' in table_name and not database_name:
            # Handle fully qualified table names
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
        
        if not database_name:
            database_name = 'default'
            
        self.add_database(database_name)
        
        if table_name not in self.metadata[database_name]:
            self.metadata[database_name][table_name] = {}
            # Add special entry for table properties
            self.metadata[database_name][table_name]['_table_properties'] = {}
            
        # Add table description if provided
        if description:
            self.set_table_description(table_name, description, database_name)
            
    def add_column(self, column_name: str, table_name: str, 
                  database_name: Optional[str] = None, 
                  properties: Optional[Dict] = None,
                  description: Optional[str] = None) -> None:
        """Add a column to the metadata store."""
        if '.' in table_name and not database_name:
            # Handle fully qualified table names
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        self.add_table(table_name, database_name)
        
        if not database_name:
            database_name = 'default'
            
        if properties is None:
            properties = {}
            
        # Add description to properties if provided
        if description:
            properties['description'] = description
            
        self.metadata[database_name][table_name][column_name] = properties
        
    def set_table_description(self, table_name: str, description: str, database_name: Optional[str] = None) -> None:
        """Set the description for a table."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        # Ensure table exists
        self.add_table(table_name, database_name)
        
        # Make sure the _table_properties entry exists
        if '_table_properties' not in self.metadata[database_name][table_name]:
            self.metadata[database_name][table_name]['_table_properties'] = {}
            
        # Set the description
        self.metadata[database_name][table_name]['_table_properties']['description'] = description
    
    def set_column_description(self, column_name: str, table_name: str, 
                              description: str, database_name: Optional[str] = None) -> None:
        """Set the description for a column."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        # Ensure column exists
        if not self.column_exists(table_name, column_name, database_name):
            self.add_column(column_name, table_name, database_name)
            
        # Add description to properties
        self.metadata[database_name][table_name][column_name]['description'] = description
    
    def get_table_description(self, table_name: str, database_name: Optional[str] = None) -> str:
        """Get the description for a table."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        if (database_name in self.metadata and 
            table_name in self.metadata[database_name] and
            '_table_properties' in self.metadata[database_name][table_name]):
            return self.metadata[database_name][table_name]['_table_properties'].get('description', '')
        
        return ''
    
    def get_column_description(self, column_name: str, table_name: str, 
                              database_name: Optional[str] = None) -> str:
        """Get the description for a column."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        if self.column_exists(table_name, column_name, database_name):
            return self.metadata[database_name][table_name][column_name].get('description', '')
        
        return ''
    
    def get_columns(self, table_name: str, database_name: Optional[str] = None) -> List[str]:
        """Get all columns for a specific table."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        if (database_name in self.metadata and 
            table_name in self.metadata[database_name]):
            return list(self.metadata[database_name][table_name].keys())
        
        return []
    
    def column_exists(self, table_name: str, column_name: str, 
                     database_name: Optional[str] = None) -> bool:
        """Check if a column exists in a table."""
        if '.' in table_name and not database_name:
            parts = table_name.split('.')
            if len(parts) == 2:
                database_name, table_name = parts
                
        if not database_name:
            database_name = 'default'
            
        return (database_name in self.metadata and
                table_name in self.metadata[database_name] and
                column_name in self.metadata[database_name][table_name])
    
    def import_metadata_from_file(self, file_path: str) -> None:
        """Import metadata from a file based on file extension."""
        if file_path.lower().endswith('.json'):
            self._import_metadata_from_json_file(file_path)
        elif file_path.lower().endswith('.csv'):
            self.import_metadata_from_csv(file_path)
        elif file_path.lower().endswith('.pdf'):
            self.import_metadata_from_pdf(file_path)
        elif file_path.lower().endswith('.sql'):
            with open(file_path, 'r') as f:
                self.load_metadata_from_sql(f.read())
        else:
            print(f"Unsupported file format: {file_path}")
            
    def _import_metadata_from_json_file(self, file_path: str) -> None:
        """Import metadata from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            for db_name, tables in data.items():
                self.add_database(db_name)
                for table_name, columns in tables.items():
                    self.add_table(table_name, db_name)
                    for column_name, properties in columns.items():
                        self.add_column(column_name, table_name, db_name, properties)
                        
        except Exception as e:
            print(f"Error importing metadata from JSON: {str(e)}")
    
    def import_metadata_from_csv(self, file_path: str) -> None:
        """Import metadata from a CSV file.
        
        Expected CSV format:
        database_name,table_name,column_name,property1,property2,...
        """
        try:
            with open(file_path, 'r', newline='') as f:
                # Use a DictReader which is more robust for handling CSV
                reader = csv.DictReader(f)
                
                # Check if we have the required columns
                required_fields = ['database_name', 'table_name', 'column_name']
                missing_fields = [field for field in required_fields if field not in reader.fieldnames]
                
                if missing_fields:
                    raise ValueError(f"CSV is missing required fields: {', '.join(missing_fields)}")
                
                # Process each row
                for row in reader:
                    db_name = row['database_name'] or 'default'
                    table_name = row['table_name']
                    column_name = row['column_name']
                    
                    # Create properties dictionary from additional columns
                    properties = {}
                    for key in row.keys():
                        if key not in required_fields and row[key]:
                            properties[key] = row[key]
                    
                    # Add to metadata store
                    self.add_column(column_name, table_name, db_name, properties)
                    
        except Exception as e:
            print(f"Error importing metadata from CSV: {str(e)}")
    
    def import_metadata_from_pdf(self, file_path: str) -> None:
        """Extract metadata from a PDF file.
        
        Requires PyPDF2 or a similar PDF processing library.
        """
        try:
            # Try to import PyPDF2
            try:
                import PyPDF2  # type: ignore
            except ImportError:
                print("PyPDF2 is required for PDF processing. Install it with 'pip install PyPDF2'")
                return
                
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                
                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    text += pdf_reader.pages[page_num].extract_text()
                
                # Process the extracted text to find table and column definitions
                # This is a simplified approach - actual implementation might be more complex
                # depending on the PDF structure
                self._process_metadata_text(text)
                
        except Exception as e:
            print(f"Error importing metadata from PDF: {str(e)}")
    
    def process_pasted_metadata(self, text: str, format_type: str = "auto") -> None:
        """Process metadata from pasted text in various formats."""
        if format_type == "auto":
            # Try to detect the format
            format_type = self._detect_format(text)
            
        if format_type == "json":
            try:
                data = json.loads(text)
                for db_name, tables in data.items():
                    self.add_database(db_name)
                    for table_name, columns in tables.items():
                        self.add_table(table_name, db_name)
                        for column_name, properties in columns.items():
                            self.add_column(column_name, table_name, db_name, properties)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {str(e)}")
                
        elif format_type == "csv":
            try:
                f = io.StringIO(text)
                # Use DictReader for more robust CSV parsing
                reader = csv.DictReader(f)
                
                # Check if we have the required columns
                required_fields = ['database_name', 'table_name', 'column_name']
                missing_fields = [field for field in required_fields if field not in reader.fieldnames]
                
                if missing_fields:
                    raise ValueError(f"CSV is missing required fields: {', '.join(missing_fields)}")
                
                # Process each row
                for row in reader:
                    db_name = row['database_name'] or 'default'
                    table_name = row['table_name']
                    column_name = row['column_name']
                    
                    # Create properties dictionary from additional columns
                    properties = {}
                    for key in row.keys():
                        if key not in required_fields and row[key]:
                            properties[key] = row[key]
                    
                    # Add to metadata store
                    self.add_column(column_name, table_name, db_name, properties)
            except Exception as e:
                print(f"Error processing CSV text: {str(e)}")
                
        elif format_type == "sql":
            self.load_metadata_from_sql(text)
            
        else:
            print(f"Unsupported format: {format_type}")
    
    def _detect_format(self, text: str) -> str:
        """Attempt to detect the format of the pasted text."""
        text = text.strip()
        
        # Check if it looks like JSON
        if text.startswith('{') and text.endswith('}'):
            try:
                json.loads(text)
                return "json"
            except:
                pass
                
        # Check if it looks like CSV
        if ',' in text and '\n' in text:
            try:
                f = io.StringIO(text)
                reader = csv.reader(f)
                headers = next(reader)
                if len(headers) >= 3:  # At least 3 columns for db, table, column
                    return "csv"
            except:
                pass
                
        # Check if it looks like SQL
        if re.search(r'CREATE\s+TABLE', text, re.IGNORECASE):
            return "sql"
            
        # Default fallback
        return "unknown"
    
    def _process_metadata_text(self, text: str) -> None:
        """Process extracted text to find table and column definitions.
        
        This is a generic method that tries to find patterns that might indicate
        table and column definitions.
        """
        # Look for table definitions
        table_pattern = r'(?:TABLE|ENTITY)\s+([a-zA-Z0-9_\.]+)'
        column_pattern = r'(?:COLUMN|FIELD|ATTRIBUTE)\s+([a-zA-Z0-9_]+)\s+(?:TYPE|:)?\s*([a-zA-Z0-9_\(\)]+)'
        
        # Find tables
        tables = re.finditer(table_pattern, text, re.IGNORECASE)
        current_table = None
        current_db = None
        
        for table_match in tables:
            table_name = table_match.group(1).strip()
            
            # Extract database name if present
            if '.' in table_name:
                parts = table_name.split('.')
                if len(parts) == 2:
                    current_db, current_table = parts
            else:
                current_table = table_name
                current_db = 'default'
                
            self.add_table(current_table, current_db)
            
            # Look for columns related to this table
            # Use the text after the table name until the next table or end of text
            table_pos = table_match.end()
            next_table_match = re.search(table_pattern, text[table_pos:], re.IGNORECASE)
            
            if next_table_match:
                section_text = text[table_pos:table_pos + next_table_match.start()]
            else:
                section_text = text[table_pos:]
                
            # Find columns in this section
            column_matches = re.finditer(column_pattern, section_text, re.IGNORECASE)
            
            for col_match in column_matches:
                column_name = col_match.group(1).strip()
                data_type = col_match.group(2).strip() if col_match.group(2) else "unknown"
                
                self.add_column(
                    column_name,
                    current_table,
                    current_db,
                    {'data_type': data_type}
                )
    
    def export_metadata_to_file(self, file_path: str) -> None:
        """Export metadata to a file."""
        if file_path.lower().endswith('.json'):
            self._export_metadata_to_json(file_path)
        elif file_path.lower().endswith('.csv'):
            self.export_metadata_to_csv(file_path)
        else:
            print(f"Unsupported export format: {file_path}")
    
    def _export_metadata_to_json(self, file_path: str) -> None:
        """Export metadata to a JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Error exporting metadata to JSON: {str(e)}")
    
    def export_metadata_to_csv(self, file_path: str) -> None:
        """Export metadata to a CSV file."""
        try:
            # Collect all property keys from all columns
            property_keys = set()
            for db in self.metadata.values():
                for table in db.values():
                    for column_props in table.values():
                        property_keys.update(column_props.keys())
                        
            # Sort property keys for consistent output
            property_keys = sorted(property_keys)
            
            # Write to CSV
            with open(file_path, 'w', newline='') as f:
                # Use these specific fieldnames for header
                fieldnames = ['database_name', 'table_name', 'column_name'] + list(property_keys)
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write data
                for db_name, tables in self.metadata.items():
                    for table_name, columns in tables.items():
                        for column_name, properties in columns.items():
                            # Create a row dictionary
                            row = {
                                'database_name': db_name,
                                'table_name': table_name,
                                'column_name': column_name
                            }
                            
                            # Add properties
                            for key, value in properties.items():
                                row[key] = value
                                
                            writer.writerow(row)
        except Exception as e:
            print(f"Error exporting metadata to CSV: {str(e)}")
                
    def load_metadata_from_sql(self, sql_text: str) -> None:
        """Extract and load metadata from SQL CREATE statements."""
        import re
        
        # Extract CREATE TABLE statements
        create_table_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP|TEMPORARY\s+)?TABLE\s+([^\s(]+)\s*\(([^)]+)\)'
        create_table_matches = re.finditer(create_table_pattern, sql_text, re.IGNORECASE | re.DOTALL)
        
        for match in create_table_matches:
            table_name = match.group(1).strip()
            columns_text = match.group(2).strip()
            
            # Extract database name if present
            database_name = None
            if '.' in table_name:
                parts = table_name.split('.')
                if len(parts) == 2:
                    database_name, table_name = parts
            
            # Add table to metadata
            self.add_table(table_name, database_name)
            
            # Extract columns
            column_pattern = r'([^\s,]+)\s+([^,]+?)(?:,|$)'
            column_matches = re.finditer(column_pattern, columns_text)
            
            for col_match in column_matches:
                column_name = col_match.group(1).strip()
                data_type = col_match.group(2).strip()
                
                # Add column to metadata
                self.add_column(
                    column_name, 
                    table_name, 
                    database_name, 
                    {'data_type': data_type}
                )
                
        # Extract CREATE VIEW statements
        create_view_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([^\s(]+)\s+AS\s+SELECT\s+(.+?)\s+FROM'
        create_view_matches = re.finditer(create_view_pattern, sql_text, re.IGNORECASE | re.DOTALL)
        
        for match in create_view_matches:
            view_name = match.group(1).strip()
            columns_text = match.group(2).strip()
            
            # Extract database name if present
            database_name = None
            if '.' in view_name:
                parts = view_name.split('.')
                if len(parts) == 2:
                    database_name, view_name = parts
            
            # Add view to metadata
            self.add_table(view_name, database_name)
            
            # Extract columns
            columns = []
            current_column = ""
            parenthesis_level = 0
            
            for char in columns_text:
                if char == '(':
                    parenthesis_level += 1
                    current_column += char
                elif char == ')':
                    parenthesis_level -= 1
                    current_column += char
                elif char == ',' and parenthesis_level == 0:
                    columns.append(current_column.strip())
                    current_column = ""
                else:
                    current_column += char
            
            # Add the last column
            if current_column:
                columns.append(current_column.strip())
            
            # Process column names
            for col_expr in columns:
                # Check for column aliases
                alias_match = re.search(r'(.*?)\s+AS\s+([^\s,]+)$', col_expr, re.IGNORECASE)
                if alias_match:
                    column_name = alias_match.group(2).strip()
                else:
                    # For columns without aliases, use a derived name
                    column_name = self._derive_column_name(col_expr)
                
                # Add column to metadata
                self.add_column(
                    column_name,
                    view_name,
                    database_name,
                    {'derived_from': col_expr}
                )
    
    def _derive_column_name(self, expr: str) -> str:
        """Derive a column name from an expression without an alias."""
        import re
        
        # Check if it's a simple column reference
        simple_col_match = re.search(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', expr)
        if simple_col_match:
            return simple_col_match.group(2)
        
        # Check if it's a function call
        func_col_match = re.search(r'([a-zA-Z0-9_]+)\(', expr)
        if func_col_match:
            func_name = func_col_match.group(1)
            return f"{func_name}_result"
        
        # Default to the expression itself if it's simple enough
        if len(expr) <= 30 and not re.search(r'[^a-zA-Z0-9_]', expr):
            return expr
        
        return "derived_column"

    def import_reference_metadata_csv(self, file_path: str) -> None:
        """
        Import reference metadata from CSV in format:
        Table Name, Column Name, Table Description, Column Description
        """
        try:
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                
                # Read header to identify columns
                header = next(reader)
                
                # Determine column indices based on header
                table_name_idx = header.index('Table Name') if 'Table Name' in header else 0
                column_name_idx = header.index('Column Name') if 'Column Name' in header else 1
                table_desc_idx = header.index('Table Description') if 'Table Description' in header else 2
                column_desc_idx = header.index('Column Description') if 'Column Description' in header else 3
                
                # Process each row
                for row in reader:
                    if len(row) < 2:  # Need at least table and column
                        continue
                        
                    table_name = row[table_name_idx]
                    column_name = row[column_name_idx]
                    
                    # Get descriptions if available
                    table_desc = row[table_desc_idx] if len(row) > table_desc_idx else ""
                    column_desc = row[column_desc_idx] if len(row) > column_desc_idx else ""
                    
                    # Add to metadata store
                    self.add_table(table_name, description=table_desc)
                    self.add_column(column_name, table_name, description=column_desc)
                    
        except Exception as e:
            print(f"Error importing reference metadata from CSV: {str(e)}") 