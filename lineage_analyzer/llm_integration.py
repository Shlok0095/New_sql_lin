import os
import logging
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flag to track if transformers is available
TRANSFORMERS_AVAILABLE = False

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
    print("DEBUG: Transformers package imported successfully")
except ImportError:
    logger.warning("Transformers package not installed. LLM integration will not be available.")
    TRANSFORMERS_AVAILABLE = False
    print("DEBUG: Transformers package import failed")

class LLMIntegration:
    """Class for integrating with local LLM models for enhanced SQL lineage explanations."""
    
    def __init__(self):
        """Initialize the LLM integration with local model."""
        # Path to the local LLAMA model directory
        self.model_dir = "/v/region/na/appl/bi/infats/data/files/PROD/userarea/sysdict_da/Llama"
        
        self.is_available = TRANSFORMERS_AVAILABLE
        
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers package not installed. Install with: pip install transformers torch")
            self.is_available = False
            self.tokenizer = None
            self.model = None
            return
        
        try:
            # Load the tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
            
            # Load the model
            self.model = AutoModelForCausalLM.from_pretrained(self.model_dir, local_files_only=True, device_map="cpu")
            
            # Set the model to evaluation mode
            self.model.eval()
            
            logger.info("Local LLM model initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing local LLM model: {str(e)}")
            self.is_available = False
            self.tokenizer = None
            self.model = None
    
    def is_enabled(self) -> bool:
        """Check if LLM integration is available and enabled."""
        return self.is_available
    
    def ask_question(self, question: str, max_tokens: int = 200) -> str:
        """
        Generate a response to a given question using the local LLM model.
        
        Args:
            question: The question to ask the model
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            str: The model's response
        """
        if not self.is_enabled():
            return ""
        
        try:
            # Tokenize the input question
            inputs = self.tokenizer(question, return_tensors="pt").to("cpu")
            
            # Generate a response
            with torch.no_grad():
                output_tokens = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    eos_token_id=self.tokenizer.eos_token_id
                )
                
            # Decode and return the response
            response = self.tokenizer.decode(output_tokens[0], skip_special_tokens=True)
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return ""
    
    def generate_sql_explanation(self, sql_statement: str) -> Optional[str]:
        """Generate an explanation for the given SQL statement."""
        if not self.is_enabled():
            return None
        
        prompt = f"""
        # SQL Query Analysis

        Below is a SQL query that needs detailed analysis. Your task is to explain exactly what this query does, focusing on data engineering aspects.

        ```sql
        {sql_statement}
        ```

        ## Analysis Requirements

        Please provide a comprehensive explanation that includes:

        1. **Main Purpose**: Explain the overall goal of this query in a concise one-sentence summary.
        
        2. **Data Sources**:
           - List all source tables and their purpose in the query
           - Identify temporary tables created during execution
           - Note any views or other data structures referenced
        
        3. **Data Flow & Transformations**:
           - Trace how data moves between tables step by step
           - Explain each major transformation (joins, aggregations, filtering)
           - Describe any complex calculations or business logic
           - Identify where and how data reshaping occurs
        
        4. **Output Structure**:
           - Describe the final output format and its columns
           - Explain the business meaning of calculated fields
           - Note any derived or transformed columns and their significance
        
        5. **Technical Considerations**:
           - Identify potential performance considerations
           - Note any SQL-specific techniques being used

        Format your response as a clear, technical explanation that would help a data engineer understand this query's purpose and flow. Use bullet points where appropriate for clarity.
        """
        
        system_context = "You are an expert SQL analyzer specializing in data lineage and data engineering. You provide detailed, accurate, and technically precise explanations of SQL queries with a focus on data flow and transformations."
        
        full_prompt = system_context + "\n\n" + prompt
        
        return self.ask_question(full_prompt, max_tokens=1500)
    
    def generate_lineage_insights(self, column_mappings: Dict[str, List[str]], sql_statement: str) -> Optional[str]:
        """Generate insights about the data lineage."""
        if not self.is_enabled():
            return None
        
        # Convert column mappings to a readable format
        mappings_text = ""
        for target, sources in column_mappings.items():
            sources_str = ", ".join(sources)
            mappings_text += f"Target: {target} <- Sources: {sources_str}\n"
        
        prompt = f"""
        # Data Lineage Analysis and Optimization

        I need you to analyze both a SQL query and its resulting column-level lineage mappings to provide valuable data engineering insights.

        ## SQL Query
        ```sql
        {sql_statement}
        ```

        ## Column Lineage Mappings
        ```
        {mappings_text}
        ```

        ## Analysis Requirements

        Based on both the SQL and column mappings above, provide a comprehensive analysis including:

        1. **Data Flow Patterns**:
           - Visualize and explain the data flow from source to target tables
           - Identify central or key tables in the data pipeline
           - Explain how the column lineage demonstrates data transformations
           - Note any complex dependencies between tables and columns

        2. **Data Quality Considerations**:
           - Identify potential data quality issues or risks
           - Note any transformations that might impact data integrity
           - Highlight columns with complex transformations that may need validation
           - Identify potential null handling issues or type conversion concerns

        3. **Critical Path Analysis**:
           - Identify the most important tables and columns in this lineage
           - Determine which source tables/columns have the most downstream impact
           - Highlight any bottlenecks in the data flow

        4. **Optimization Recommendations**:
           - Suggest specific SQL optimization opportunities
           - Recommend any structural improvements to the query or data model
           - Identify opportunities for improved data pipeline design
           - Suggest monitoring points for data quality or performance

        Format your response as a detailed technical analysis with specific, actionable insights that would help a data engineer understand and improve this data pipeline.
        """
        
        system_context = "You are a data lineage and SQL optimization expert with extensive experience in data engineering. You provide insightful, technical, and practical analysis of SQL data flows, with a focus on improvement opportunities and best practices."
        
        full_prompt = system_context + "\n\n" + prompt
        
        return self.ask_question(full_prompt, max_tokens=1500)
    
    def generate_response(self, prompt: str, system_prompt: str = None) -> Optional[str]:
        """
        Generate a response for a generic prompt.
        
        Args:
            prompt: The user prompt to send to the LLM
            system_prompt: Optional system prompt to set the context
            
        Returns:
            Optional[str]: The generated response or None if an error occurs
        """
        if not self.is_enabled():
            return None
        
        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant specializing in data and SQL analysis."
        
        full_prompt = system_prompt + "\n\n" + prompt
        
        return self.ask_question(full_prompt, max_tokens=1500)
    
    def generate_text(self, prompt: str) -> Optional[str]:
        """
        Generate a short text description based on the given prompt.
        
        Args:
            prompt: The prompt asking for a description
            
        Returns:
            Optional[str]: The generated text or an empty string if an error occurs
        """
        if not self.is_enabled():
            return ""
        
        system_context = "You are a helpful assistant specialized in describing database structures. Keep descriptions concise and informative, focusing on the likely purpose and content of database elements based on their names."
        
        full_prompt = system_context + "\n\n" + prompt
        
        return self.ask_question(full_prompt, max_tokens=200) 