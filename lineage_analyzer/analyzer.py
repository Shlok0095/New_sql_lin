# lineage_analyzer/analyzer.py
import re
from typing import Dict, List, Set, Tuple, Optional
from .metadata import MetadataStore

class LineageAnalyzer:
    def __init__(self, metadata_store: Optional[MetadataStore] = None):
        self.metadata_store = metadata_store or MetadataStore()
        
    def analyze_sql(self, sql_text: str) -> Dict[str, List[str]]:
        """
        Analyze SQL text to identify source-target column relationships.
        Returns a dictionary mapping target columns to their source columns.
        """
        # Normalize SQL text
        sql_text = self._normalize_sql(sql_text)
        
        # Extract basic components
        target_table = self._extract_target_table(sql_text)
        source_tables = self._extract_source_tables(sql_text)
        
        # Extract column relationships
        column_mappings = self._extract_column_mappings(sql_text, target_table, source_tables)
        
        return column_mappings
    
    def _normalize_sql(self, sql_text: str) -> str:
        """Normalize SQL text for consistent analysis"""
        # Remove comments
        sql_text = re.sub(r'--.*?$', ' ', sql_text, flags=re.MULTILINE)
        sql_text = re.sub(r'/\*.*?\*/', ' ', sql_text, flags=re.DOTALL)
        
        # Normalize whitespace
        sql_text = re.sub(r'\s+', ' ', sql_text)
        
        return sql_text.strip()
    
    def _extract_target_table(self, sql_text: str) -> str:
        """Extract the target table from SQL text"""
        # For INSERT statements
        insert_match = re.search(r'INSERT\s+INTO\s+([^\s(]+)', sql_text, re.IGNORECASE)
        if insert_match:
            return insert_match.group(1).strip()
        
        # For CREATE TABLE statements
        create_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP|TEMPORARY\s+)?TABLE\s+([^\s(]+)', 
                                sql_text, re.IGNORECASE)
        if create_match:
            return create_match.group(1).strip()
        
        # For CREATE VIEW statements
        view_match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([^\s(]+)', 
                              sql_text, re.IGNORECASE)
        if view_match:
            return view_match.group(1).strip()
        
        return "Unknown"
    
    def _extract_source_tables(self, sql_text: str) -> List[str]:
        """Extract source tables from SQL text"""
        source_tables = []
        
        # Find all FROM clauses and the tables that follow them
        from_clauses = re.finditer(r'FROM\s+([^\s,;()]+)', sql_text, re.IGNORECASE)
        for match in from_clauses:
            source_tables.append(match.group(1).strip())
        
        # Find all JOIN clauses and the tables that follow them
        join_clauses = re.finditer(r'JOIN\s+([^\s,;()]+)', sql_text, re.IGNORECASE)
        for match in join_clauses:
            source_tables.append(match.group(1).strip())
        
        return source_tables
    
    def _extract_column_mappings(self, sql_text: str, target_table: str, 
                                source_tables: List[str]) -> Dict[str, List[str]]:
        """Extract column mappings between source and target tables"""
        column_mappings = {}
        
        # Handle INSERT statements
        if "INSERT INTO" in sql_text.upper():
            # Extract target columns from INSERT INTO statement
            insert_cols_match = re.search(
                r'INSERT\s+INTO\s+[^\s(]+\s*\(([^)]+)\)', sql_text, re.IGNORECASE)
            
            if insert_cols_match:
                target_columns = [col.strip() for col in insert_cols_match.group(1).split(',')]
                
                # Try to find SELECT statement for source columns
                select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_text, re.IGNORECASE)
                if select_match:
                    source_columns_text = select_match.group(1)
                    
                    # Split by commas, but handle function calls with commas
                    source_columns = []
                    current_column = ""
                    parenthesis_level = 0
                    
                    for char in source_columns_text:
                        if char == '(':
                            parenthesis_level += 1
                            current_column += char
                        elif char == ')':
                            parenthesis_level -= 1
                            current_column += char
                        elif char == ',' and parenthesis_level == 0:
                            source_columns.append(current_column.strip())
                            current_column = ""
                        else:
                            current_column += char
                    
                    # Add the last column
                    if current_column:
                        source_columns.append(current_column.strip())
                    
                    # Map columns based on position
                    for i, target_col in enumerate(target_columns):
                        if i < len(source_columns):
                            source_col = source_columns[i]
                            column_mappings[f"{target_table}.{target_col}"] = [self._extract_column_source(source_col, source_tables)]
        
        # Handle CREATE TABLE or VIEW statements
        elif "CREATE" in sql_text.upper() and "SELECT" in sql_text.upper():
            # Extract the SELECT part
            select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_text, re.IGNORECASE)
            if select_match:
                select_columns_text = select_match.group(1)
                
                # Parse column aliases
                column_expressions = []
                current_expression = ""
                parenthesis_level = 0
                
                for char in select_columns_text:
                    if char == '(':
                        parenthesis_level += 1
                        current_expression += char
                    elif char == ')':
                        parenthesis_level -= 1
                        current_expression += char
                    elif char == ',' and parenthesis_level == 0:
                        column_expressions.append(current_expression.strip())
                        current_expression = ""
                    else:
                        current_expression += char
                
                # Add the last expression
                if current_expression:
                    column_expressions.append(current_expression.strip())
                
                # Process each column expression
                for expr in column_expressions:
                    # Handle column aliases
                    alias_match = re.search(r'(.*?)\s+AS\s+([^\s,]+)$', expr, re.IGNORECASE)
                    if alias_match:
                        source_expr = alias_match.group(1).strip()
                        target_col = alias_match.group(2).strip()
                        column_mappings[f"{target_table}.{target_col}"] = [self._extract_column_source(source_expr, source_tables)]
                    else:
                        # For columns without aliases, use the full expression
                        # Try to determine a name from the expression
                        col_name = self._derive_column_name(expr)
                        column_mappings[f"{target_table}.{col_name}"] = [self._extract_column_source(expr, source_tables)]
        
        return column_mappings
    
    def _extract_column_source(self, column_expr: str, source_tables: List[str]) -> str:
        """Extract source column information from a column expression"""
        # Handle simple column references
        simple_col_match = re.search(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', column_expr)
        if simple_col_match:
            return f"{simple_col_match.group(1)}.{simple_col_match.group(2)}"
        
        # Handle function calls - try to extract column references inside the function
        func_col_match = re.search(r'([a-zA-Z0-9_]+)\(([^)]+)\)', column_expr)
        if func_col_match:
            func_name = func_col_match.group(1)
            func_args = func_col_match.group(2)
            
            # Check for column references in function arguments
            arg_col_match = re.search(r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)', func_args)
            if arg_col_match:
                return f"{arg_col_match.group(1)}.{arg_col_match.group(2)} (in {func_name})"
            
            return f"Function: {func_name}({func_args})"
        
        # If it's a simple column without a table qualifier, try to infer the table
        if re.match(r'^[a-zA-Z0-9_]+$', column_expr) and source_tables:
            for table in source_tables:
                if self.metadata_store.column_exists(table, column_expr):
                    return f"{table}.{column_expr}"
        
        return column_expr
    
    def _derive_column_name(self, expr: str) -> str:
        """Derive a column name from an expression without an alias"""
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