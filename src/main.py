from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from dotenv import load_dotenv
from mem0 import Memory
import asyncio
import json
import os

from utils import get_mem0_client
from connection_manager import get_connection_manager, managed_mem0_client

load_dotenv()

# Default user ID for memory operations
DEFAULT_USER_ID = "user"

# Create a dataclass for our application context
@dataclass
class Mem0Context:
    """Context for the Mem0 MCP server."""
    mem0_client: Memory

@asynccontextmanager
async def mem0_lifespan(server: FastMCP) -> AsyncIterator[Mem0Context]:
    """
    Manages the Mem0 client lifecycle using connection manager.
    
    Args:
        server: The FastMCP server instance
        
    Yields:
        Mem0Context: The context containing the Mem0 client
    """
    print("Initializing Mem0 client with connection manager...")
    connection_manager = get_connection_manager()
    
    try:
        # 启动定期清理线程
        connection_manager.start_periodic_cleanup(interval=300)  # 每5分钟清理一次
        
        # 获取管理的客户端
        mem0_client = connection_manager.get_client("main_server")
        print("Mem0 client initialized successfully")
        
        # 记录初始连接数
        initial_connections = connection_manager.get_connection_count()
        print(f"Initial database connections: {initial_connections}")
        
        yield Mem0Context(mem0_client=mem0_client)
        
    except Exception as e:
        print(f"Error initializing Mem0 client: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        print("Cleaning up Mem0 client with connection manager...")
        try:
            # 释放主服务器客户端
            connection_manager.release_client("main_server")
            
            # 停止定期清理线程
            connection_manager.stop_periodic_cleanup()
            
            # 清理所有客户端
            connection_manager.cleanup_all()
            
            # 记录最终连接数
            final_connections = connection_manager.get_connection_count()
            print(f"Final database connections: {final_connections}")
            
            print("Connection manager cleanup completed")
        except Exception as cleanup_error:
            print(f"Error during connection manager cleanup: {cleanup_error}")
        
        print("Mem0 client lifecycle management completed")

# Initialize FastMCP server with the Mem0 client as context
mcp = FastMCP(
    "mcp-mem0",
    description="MCP server for long term memory storage and retrieval with Mem0",
    lifespan=mem0_lifespan,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8050"))
)        

@mcp.tool()
async def save_memory(ctx: Context, text: str) -> str:
    """Save information to your long-term memory.

    This tool is designed to store any type of information that might be useful in the future.
    The content will be processed and indexed for later retrieval through semantic search.

    Args:
        ctx: The MCP server provided context which includes the Mem0 client
        text: The content to store in memory, including any relevant details and context
    """
    try:
        mem0_client = ctx.request_context.lifespan_context.mem0_client
        messages = [{"role": "user", "content": text}]
        mem0_client.add(messages, user_id=DEFAULT_USER_ID)
        return f"Successfully saved memory: {text[:100]}..." if len(text) > 100 else f"Successfully saved memory: {text}"
    except Exception as e:
        return f"Error saving memory: {str(e)}"

@mcp.tool()
async def get_all_memories(ctx: Context) -> str:
    """Get all stored memories for the user.
    
    Call this tool when you need complete context of all previously memories.

    Args:
        ctx: The MCP server provided context which includes the Mem0 client

    Returns a JSON formatted list of all stored memories, including when they were created
    and their content. Results are paginated with a default of 50 items per page.
    """
    try:
        mem0_client = ctx.request_context.lifespan_context.mem0_client
        memories = mem0_client.get_all(user_id=DEFAULT_USER_ID)
        if isinstance(memories, dict) and "results" in memories:
            flattened_memories = [memory["memory"] for memory in memories["results"]]
        else:
            flattened_memories = memories
        return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error retrieving memories: {str(e)}"

@mcp.tool()
async def search_memories(ctx: Context, query: str, limit: int = 3) -> str:
    """Search memories using semantic search.

    This tool should be called to find relevant information from your memory. Results are ranked by relevance.
    Always search your memories before making decisions to ensure you leverage your existing knowledge.

    Args:
        ctx: The MCP server provided context which includes the Mem0 client
        query: Search query string describing what you're looking for. Can be natural language.
        limit: Maximum number of results to return (default: 3)
    """
    try:
        mem0_client = ctx.request_context.lifespan_context.mem0_client
        memories = mem0_client.search(query, user_id=DEFAULT_USER_ID, limit=limit)
        if isinstance(memories, dict) and "results" in memories:
            flattened_memories = [memory["memory"] for memory in memories["results"]]
        else:
            flattened_memories = memories
        return json.dumps(flattened_memories, indent=2)
    except Exception as e:
        return f"Error searching memories: {str(e)}"

async def main():
    try:
        print("Starting MCP-Mem0 server...")
        transport = os.getenv("TRANSPORT", "sse")
        host = os.getenv("HOST", "0.0.0.0")
        port = os.getenv("PORT", "8050")
        
        print(f"Transport: {transport}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        
        # Check critical environment variables
        llm_provider = os.getenv('LLM_PROVIDER')
        llm_api_key = os.getenv('LLM_API_KEY')
        database_url = os.getenv('DATABASE_URL')
        
        print(f"LLM Provider: {llm_provider}")
        print(f"API Key configured: {'Yes' if llm_api_key else 'No'}")
        print(f"Database URL configured: {'Yes' if database_url else 'No'}")
        
        if transport == 'sse':
            print(f"Server will be available at: http://{host}:{port}")
            # Run the MCP server with sse transport
            await mcp.run_sse_async()
        else:
            print("Running with stdio transport")
            # Run the MCP server with stdio transport
            await mcp.run_stdio_async()
    except Exception as e:
        print(f"Error in main function: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import sys
        sys.exit(1)
