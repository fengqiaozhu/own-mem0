from mem0 import Memory
import os

# Custom instructions for memory processing
# These aren't being used right now but Mem0 does support adding custom prompting
# for handling memory retrieval and processing.
CUSTOM_INSTRUCTIONS = """
Extract the Following Information:  

- Key Information: Identify and save the most important details.
- Context: Capture the surrounding context to understand the memory's relevance.
- Connections: Note any relationships to other topics or memories.
- Importance: Highlight why this information might be valuable in the future.
- Source: Record where this information came from when applicable.
"""

def get_mem0_client():
    # Get LLM provider and configuration
    llm_provider = os.getenv('LLM_PROVIDER')
    llm_api_key = os.getenv('LLM_API_KEY')
    llm_model = os.getenv('LLM_CHOICE')
    embedding_model = os.getenv('EMBEDDING_MODEL_CHOICE')
    embedding_dims = os.getenv('EMBEDDING_DIMS')
    
    # Initialize config dictionary
    config = {}
    
    # Configure LLM based on provider
    if llm_provider == 'openai' or llm_provider == 'openrouter':
        llm_config = {
            "model": llm_model,
            "temperature": 0.2,
            "max_tokens": 2000,
        }
        
        # Set base URL if provided
        llm_base_url = os.getenv('LLM_BASE_URL')
        if llm_base_url:
            llm_config["openai_base_url"] = llm_base_url
        
        config["llm"] = {
            "provider": "openai",
            "config": llm_config
        }
        
        # Set API key in environment if not already set
        if llm_api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = llm_api_key
            
        # For OpenRouter, set the specific API key
        if llm_provider == 'openrouter' and llm_api_key:
            os.environ["OPENROUTER_API_KEY"] = llm_api_key
    
    elif llm_provider == 'ollama':
        config["llm"] = {
            "provider": "ollama",
            "config": {
                "model": llm_model,
                "temperature": 0.2,
                "max_tokens": 2000,
            }
        }
        
        # Set base URL for Ollama if provided
        llm_base_url = os.getenv('LLM_BASE_URL')
        if llm_base_url:
            config["llm"]["config"]["ollama_base_url"] = llm_base_url
    
    # Configure embedder based on provider
    if llm_provider == 'openai':
        # Default embedding dimensions for different OpenAI models
        default_dims = 1536  # Default for text-embedding-3-small
        if embedding_model == "text-embedding-3-large":
            default_dims = 3072
        elif embedding_model == "text-embedding-ada-002":
            default_dims = 1536
        
        embedder_config = {
            "model": embedding_model or "text-embedding-3-small",
            "embedding_dims": int(embedding_dims) if embedding_dims else default_dims
        }
        
        # Set base URL if provided
        llm_base_url = os.getenv('LLM_BASE_URL')
        if llm_base_url:
            embedder_config["openai_base_url"] = llm_base_url
        
        config["embedder"] = {
            "provider": "openai",
            "config": embedder_config
        }
        
        # Set API key in environment if not already set
        if llm_api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = llm_api_key
    
    elif llm_provider == 'ollama':
        # Default embedding dimensions for different Ollama models
        default_dims = 768  # Default for nomic-embed-text
        if embedding_model and "nomic-embed-text" in embedding_model:
            default_dims = 768
        elif embedding_model and "all-minilm" in embedding_model:
            default_dims = 384
        
        config["embedder"] = {
            "provider": "ollama",
            "config": {
                "model": embedding_model or "nomic-embed-text",
                "embedding_dims": int(embedding_dims) if embedding_dims else default_dims
            }
        }
        
        # Set base URL for Ollama if provided
        embedding_base_url = os.getenv('LLM_BASE_URL')
        if embedding_base_url:
            config["embedder"]["config"]["ollama_base_url"] = embedding_base_url
    
    # Configure Supabase vector store
    # Get the embedding dimensions from the embedder config
    embedder_dims = config.get("embedder", {}).get("config", {}).get("embedding_dims", 1536)
    
    config["vector_store"] = {
        "provider": "supabase",
        "config": {
            "connection_string": os.environ.get('DATABASE_URL', ''),
            "collection_name": "mem0_memories",
            "embedding_model_dims": embedder_dims
        }
    }

    # config["custom_fact_extraction_prompt"] = CUSTOM_INSTRUCTIONS
    
    # Create and return the Memory client
    return Memory.from_config(config)