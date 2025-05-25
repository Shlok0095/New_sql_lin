import os
import re
from typing import List, Dict, Any, Optional

def normalize_sql(sql_text: str) -> str:
    """Normalize SQL text for consistent analysis."""
    # Remove comments
    sql_text = re.sub(r'--.*?$', ' ', sql_text, flags=re.MULTILINE)
    sql_text = re.sub(r'/\*.*?\*/', ' ', sql_text, flags=re.DOTALL)
    
    # Normalize whitespace
    sql_text = re.sub(r'\s+', ' ', sql_text)
    
    return sql_text.strip()

def read_sql_file(file_path: str) -> str:
    """Read SQL content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return ""

def write_to_file(content: str, file_path: str) -> bool:
    """Write content to a file."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to file {file_path}: {str(e)}")
        return False

def get_files_with_extension(directory: str, extension: str) -> List[str]:
    """Get all files with a specific extension in a directory."""
    file_paths = []
    
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    file_paths.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error scanning directory {directory}: {str(e)}")
    
    return file_paths

def extract_table_name(identifier: str) -> str:
    """Extract table name from a fully qualified identifier."""
    # Handle cases like database.schema.table
    parts = identifier.split('.')
    
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[1]  # schema.table -> table
    elif len(parts) >= 3:
        return parts[2]  # database.schema.table -> table
    
    return identifier

def extract_schema_name(identifier: str) -> str:
    """Extract schema name from a fully qualified identifier."""
    # Handle cases like database.schema.table
    parts = identifier.split('.')
    
    if len(parts) == 2:
        return parts[0]  # schema.table -> schema
    elif len(parts) >= 3:
        return parts[1]  # database.schema.table -> schema
    
    return "default"  # Default schema if not specified

def format_duration(seconds: float) -> str:
    """Format duration in seconds to a readable string."""
    if seconds < 1:
        return f"{seconds*1000:.2f} ms"
    elif seconds < 60:
        return f"{seconds:.2f} sec"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes} min {seconds:.2f} sec"
    else:
        hours = int(seconds // 3600)
        seconds = seconds % 3600
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{hours} hr {minutes} min {seconds:.2f} sec" 