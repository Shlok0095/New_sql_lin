# lineage_analyzer/extractor.py
import re
from typing import List, Dict, Set, Tuple, Optional

class SQLComponentExtractor:
    """Extracts various components from SQL queries."""
    
    @staticmethod
    def extract_sql_statements(sql_file_content: str) -> List[str]:
        """Extract individual SQL statements from a file."""
        # Remove comments
        sql_content = re.sub(r'--.*?$', ' ', sql_file_content, flags=re.MULTILINE)
        sql_content = re.sub(r'/\*.*?\*/', ' ', sql_content, flags=re.DOTALL)
        
        # Split by semicolons but handle semicolons inside quotes
        statements = []
        current_statement = ""
        in_quote = False
        quote_char = None
        
        for char in sql_content:
            if char in ["'", '"'] and (not in_quote or quote_char == char):
                in_quote = not in_quote
                if in_quote:
                    quote_char = char
                else:
                    quote_char = None
                current_statement += char
            elif char == ';' and not in_quote:
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
            else:
                current_statement += char
        
        # Add the last statement if it exists
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    @staticmethod
    def extract_table_references(sql_text: str) -> List[str]:
        """Extract all table references from SQL text."""
        tables = set()
        
        # Extract tables from FROM clauses
        from_pattern = r'FROM\s+([^\s,;()]+)'
        from_matches = re.finditer(from_pattern, sql_text, re.IGNORECASE)
        for match in from_matches:
            tables.add(match.group(1).strip())
        
        # Extract tables from JOIN clauses
        join_pattern = r'JOIN\s+([^\s,;()]+)'
        join_matches = re.finditer(join_pattern, sql_text, re.IGNORECASE)
        for match in join_matches:
            tables.add(match.group(1).strip())
        
        # Extract tables from INSERT INTO statements
        insert_pattern = r'INSERT\s+INTO\s+([^\s(]+)'
        insert_matches = re.finditer(insert_pattern, sql_text, re.IGNORECASE)
        for match in insert_matches:
            tables.add(match.group(1).strip())
        
        # Extract tables from UPDATE statements
        update_pattern = r'UPDATE\s+([^\s,;()]+)'
        update_matches = re.finditer(update_pattern, sql_text, re.IGNORECASE)
        for match in update_matches:
            tables.add(match.group(1).strip())
        
        # Extract tables from CREATE TABLE statements
        create_table_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP|TEMPORARY\s+)?TABLE\s+([^\s(]+)'
        create_table_matches = re.finditer(create_table_pattern, sql_text, re.IGNORECASE)
        for match in create_table_matches:
            tables.add(match.group(1).strip())
        
        # Extract tables from CREATE VIEW statements
        create_view_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([^\s(]+)'
        create_view_matches = re.finditer(create_view_pattern, sql_text, re.IGNORECASE)
        for match in create_view_matches:
            tables.add(match.group(1).strip())
        
        return list(tables)
    
    @staticmethod
    def extract_column_references(sql_text: str) -> List[str]:
        """Extract all column references from SQL text."""
        columns = set()
        
        # Extract columns from qualified references (table.column)
        qualified_pattern = r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)'
        qualified_matches = re.finditer(qualified_pattern, sql_text)
        for match in qualified_matches:
            columns.add(f"{match.group(1)}.{match.group(2)}")
        
        # Extract columns from SELECT statements
        select_pattern = r'SELECT\s+(.+?)\s+FROM'
        select_matches = re.finditer(select_pattern, sql_text, re.IGNORECASE | re.DOTALL)
        for match in select_matches:
            columns_text = match.group(1)
            
            # Parse column expressions
            column_expressions = []
            current_expression = ""
            parenthesis_level = 0
            
            for char in columns_text:
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
                    columns.add(alias_match.group(2).strip())
                
                # Extract qualified column references within the expression
                qualified_refs = re.finditer(qualified_pattern, expr)
                for ref_match in qualified_refs:
                    columns.add(f"{ref_match.group(1)}.{ref_match.group(2)}")
        
        # Extract columns from INSERT statements
        insert_cols_pattern = r'INSERT\s+INTO\s+[^\s(]+\s*\(([^)]+)\)'
        insert_cols_matches = re.finditer(insert_cols_pattern, sql_text, re.IGNORECASE)
        for match in insert_cols_matches:
            cols_text = match.group(1)
            for col in cols_text.split(','):
                columns.add(col.strip())
        
        return list(columns)
    
    @staticmethod
    def extract_stored_procedure_params(sql_text: str) -> Tuple[List[str], List[str]]:
        """Extract input and output parameters from stored procedure definitions."""
        input_params = []
        output_params = []
        
        # Extract parameters from CREATE PROCEDURE statements
        create_proc_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE\s+[^\s(]+\s*\(([^)]+)\)'
        create_proc_matches = re.finditer(create_proc_pattern, sql_text, re.IGNORECASE)
        
        for match in create_proc_matches:
            params_text = match.group(1)
            param_list = params_text.split(',')
            
            for param in param_list:
                param = param.strip()
                
                # Check for direction (IN, OUT, INOUT)
                if re.search(r'\bIN\b', param, re.IGNORECASE):
                    input_params.append(param)
                elif re.search(r'\bOUT\b', param, re.IGNORECASE):
                    output_params.append(param)
                elif re.search(r'\bINOUT\b', param, re.IGNORECASE):
                    input_params.append(param)
                    output_params.append(param)
                else:
                    # Default to IN parameter if no direction specified
                    input_params.append(param)
        
        return input_params, output_params
    
    @staticmethod
    def extract_query_type(sql_text: str) -> str:
        """Determine the type of SQL query."""
        sql_text = sql_text.strip().upper()
        
        if sql_text.startswith('SELECT'):
            return 'SELECT'
        elif sql_text.startswith('INSERT'):
            return 'INSERT'
        elif sql_text.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_text.startswith('DELETE'):
            return 'DELETE'
        elif sql_text.startswith('CREATE TABLE'):
            return 'CREATE TABLE'
        elif sql_text.startswith('CREATE VIEW'):
            return 'CREATE VIEW'
        elif sql_text.startswith('CREATE PROCEDURE') or sql_text.startswith('CREATE FUNCTION'):
            return 'CREATE PROCEDURE'
        elif sql_text.startswith('ALTER'):
            return 'ALTER'
        elif sql_text.startswith('DROP'):
            return 'DROP'
        else:
            return 'UNKNOWN' 