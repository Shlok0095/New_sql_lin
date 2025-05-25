from typing import Dict, List, Optional, Any
import json
import os
import re
from .metadata import MetadataStore
from .llm_integration import LLMIntegration

class LLMMetadataParser:
    """Uses LLM to parse and extract metadata from various file formats and content."""
    
    def __init__(self, llm_integration: Optional[LLMIntegration] = None):
        self.llm = llm_integration or LLMIntegration()
        
    def extract_metadata_from_text(self, text: str, metadata_store: MetadataStore) -> bool:
        """
        Extract metadata from natural language text using LLM.
        
        Args:
            text: Natural language text describing tables and columns
            metadata_store: MetadataStore instance to populate
            
        Returns:
            bool: True if extraction was successful
        """
        if not self.llm.is_enabled():
            print("LLM integration is not available. Falling back to pattern matching.")
            return self._fallback_extract_from_text(text, metadata_store)
            
        # Prompt the LLM to extract structured metadata
        prompt = f"""
        Extract database metadata from the following text. 
        Identify tables, columns, data types, and descriptions.
        
        Text:
        {text}
        
        Format your response as JSON with the structure:
        {{
            "tables": [
                {{
                    "table_name": "table_name",
                    "description": "table description",
                    "columns": [
                        {{
                            "name": "column_name",
                            "data_type": "data type (if available)",
                            "description": "column description (if available)"
                        }}
                    ]
                }}
            ]
        }}
        
        Return ONLY the JSON, with no additional text before or after it.
        """
        
        try:
            response = self.llm.generate_response(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                metadata = json.loads(json_str)
                
                # Process the extracted metadata
                if 'tables' in metadata:
                    for table in metadata['tables']:
                        table_name = table.get('table_name', '')
                        table_desc = table.get('description', '')
                        
                        if not table_name:
                            continue
                            
                        # Add table with description
                        metadata_store.add_table(table_name, description=table_desc)
                        
                        # Process columns
                        for column in table.get('columns', []):
                            column_name = column.get('name', '')
                            data_type = column.get('data_type', '')
                            column_desc = column.get('description', '')
                            
                            if not column_name:
                                continue
                                
                            # Prepare properties dict
                            properties = {}
                            if data_type:
                                properties['data_type'] = data_type
                                
                            # Add column with description
                            metadata_store.add_column(
                                column_name, 
                                table_name, 
                                properties=properties,
                                description=column_desc
                            )
                    
                    return True
                    
            # If we couldn't extract valid JSON, fall back to pattern matching
            return self._fallback_extract_from_text(text, metadata_store)
                
        except Exception as e:
            print(f"Error using LLM to extract metadata: {str(e)}")
            return self._fallback_extract_from_text(text, metadata_store)
            
    def extract_metadata_from_pdf(self, pdf_content: str, metadata_store: MetadataStore) -> bool:
        """
        Extract metadata from PDF content using LLM.
        
        Args:
            pdf_content: Text extracted from a PDF file
            metadata_store: MetadataStore instance to populate
            
        Returns:
            bool: True if extraction was successful
        """
        # This method is similar to extract_metadata_from_text but with PDF-specific prompting
        if not self.llm.is_enabled():
            print("LLM integration is not available.")
            return False
            
        # Prompt the LLM to extract structured metadata from PDF content
        prompt = f"""
        Extract database metadata from the following text extracted from a PDF document. 
        Focus on finding table definitions, column names, data types, and descriptions.
        
        Text from PDF:
        {pdf_content[:10000]}  # Limit to first 10000 chars to stay within token limits
        
        Format your response as JSON with the structure:
        {{
            "tables": [
                {{
                    "table_name": "table_name",
                    "description": "table description",
                    "columns": [
                        {{
                            "name": "column_name",
                            "data_type": "data type (if available)",
                            "description": "column description (if available)"
                        }}
                    ]
                }}
            ]
        }}
        
        Return ONLY the JSON, with no additional text before or after it.
        """
        
        try:
            response = self.llm.generate_response(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                metadata = json.loads(json_str)
                
                # Process the extracted metadata (same as in extract_metadata_from_text)
                if 'tables' in metadata:
                    for table in metadata['tables']:
                        table_name = table.get('table_name', '')
                        table_desc = table.get('description', '')
                        
                        if not table_name:
                            continue
                            
                        # Add table with description
                        metadata_store.add_table(table_name, description=table_desc)
                        
                        # Process columns
                        for column in table.get('columns', []):
                            column_name = column.get('name', '')
                            data_type = column.get('data_type', '')
                            column_desc = column.get('description', '')
                            
                            if not column_name:
                                continue
                                
                            # Prepare properties dict
                            properties = {}
                            if data_type:
                                properties['data_type'] = data_type
                                
                            # Add column with description
                            metadata_store.add_column(
                                column_name, 
                                table_name, 
                                properties=properties,
                                description=column_desc
                            )
                    
                    return True
                    
            return False
                
        except Exception as e:
            print(f"Error using LLM to extract metadata from PDF: {str(e)}")
            return False
            
    def _fallback_extract_from_text(self, text: str, metadata_store: MetadataStore) -> bool:
        """
        Fallback method to extract metadata using pattern matching.
        
        Args:
            text: Natural language text describing tables and columns
            metadata_store: MetadataStore instance to populate
            
        Returns:
            bool: True if extraction was partially successful
        """
        success = False
        
        # Look for patterns like "TABLE_XXX table holds data about XXX with columns:"
        table_pattern = re.compile(r'(?:The\s+)?(\w+)\s+table\s+(?:holds|stores|contains)\s+(?:data\s+about|information\s+(?:about|on|with))?\s*([\w\s]+)(?:with)?\s*(?:columns|with):?', re.IGNORECASE)
        
        # Find all table definitions in the text
        for table_match in table_pattern.finditer(text):
            table_name = table_match.group(1).strip()
            table_desc = table_match.group(2).strip() if table_match.group(2) else ""
            
            # Add table to metadata with description
            metadata_store.add_table(table_name, description=table_desc)
            success = True
            
            # Extract text section for this table until the next table or end of input
            table_pos = table_match.end()
            next_table_match = table_pattern.search(text[table_pos:])
            
            if next_table_match:
                section_text = text[table_pos:table_pos + next_table_match.start()]
            else:
                section_text = text[table_pos:]
            
            # Find columns in this section - looking for patterns like:
            # COLUMN_NAME which is/for/that XXX,
            column_pattern = re.compile(r'(\w+)\s+(?:which|that|for|is|as)\s+(?:is\s+)?(?:an?|the)?\s*([\w\s,]+)(?:,|\.|\n|$)', re.IGNORECASE)
            
            for col_match in column_pattern.finditer(section_text):
                column_name = col_match.group(1).strip()
                column_desc = col_match.group(2).strip() if col_match.group(2) else ""
                
                # Add column to metadata with description
                if column_name and column_name.lower() not in ['columns', 'column', 'and', 'with', 'has']:
                    metadata_store.add_column(column_name, table_name, description=column_desc)
        
        # If no tables found with the first pattern, try an alternative pattern
        if not success:
            # Alternative pattern for tables and columns
            alt_table_pattern = re.compile(r'(?:The\s+)?(\w+)(?:\s+table)?\s*:?\s*([\w\s,]*)(?:\s+has(?:\/with)?\s+columns:?|:)', re.IGNORECASE)
            
            for table_match in alt_table_pattern.finditer(text):
                table_name = table_match.group(1).strip()
                table_desc = table_match.group(2).strip() if table_match.group(2) else ""
                
                # Check if it looks like a table name
                if not table_name or table_name.lower() in ['table', 'column', 'following']:
                    continue
                
                # Add table to metadata with description
                metadata_store.add_table(table_name, description=table_desc)
                success = True
                
                # Extract text section for this table
                table_pos = table_match.end()
                next_table_match = alt_table_pattern.search(text[table_pos:])
                
                if next_table_match:
                    section_text = text[table_pos:table_pos + next_table_match.start()]
                else:
                    section_text = text[table_pos:]
                
                # Use a simpler column pattern for bullet-list style metadata
                column_pattern = re.compile(r'[-*•]?\s*(\w+)\s+(?:[-–—]|for|is|as)\s+([\w\s,.]+)(?:,|\.|\n|$)', re.IGNORECASE)
                
                for col_match in column_pattern.finditer(section_text):
                    column_name = col_match.group(1).strip()
                    column_desc = col_match.group(2).strip() if col_match.group(2) else ""
                    
                    # Add column to metadata with description
                    if column_name and column_name.lower() not in ['columns', 'column', 'and', 'with', 'has']:
                        metadata_store.add_column(column_name, table_name, description=column_desc)
        
        # Check for tabular format as well (unchanged from before)
        lines = text.strip().split('\n')
        if len(lines) > 1 and ('ObjectName' in lines[0] or 'Table Name' in lines[0]):
            # Handle tabular format
            header = lines[0].strip().split(',')
            header = [h.strip() for h in header]
            
            # Find column indices
            table_idx = None
            column_idx = None
            datatype_idx = None
            
            for i, h in enumerate(header):
                if h.lower() in ['objectname', 'table', 'table name']:
                    table_idx = i
                elif h.lower() in ['fieldname', 'column', 'column name']:
                    column_idx = i
                elif h.lower() in ['dataformat', 'data type', 'type']:
                    datatype_idx = i
            
            # If we found table and column indices, process the data
            if table_idx is not None and column_idx is not None:
                for i in range(1, len(lines)):
                    row = lines[i].strip().split(',')
                    row = [cell.strip() for cell in row]
                    
                    if len(row) <= max(table_idx, column_idx):
                        continue
                        
                    table_name = row[table_idx]
                    column_name = row[column_idx]
                    
                    # Add table and column
                    metadata_store.add_table(table_name)
                    
                    properties = {}
                    if datatype_idx is not None and datatype_idx < len(row):
                        properties['data_type'] = row[datatype_idx]
                        
                    metadata_store.add_column(column_name, table_name, properties=properties)
                    success = True
        
        return success 