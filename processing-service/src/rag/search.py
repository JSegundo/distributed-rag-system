# processing-service/src/rag/search.py
import os
import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import time
from openai import OpenAI

from storage.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class VectorSearch:
    """Handles vector search operations using pgvector"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the vector search service
        
        Args:
            db_manager: Database connection manager
        """
        # Store the database manager
        self.db_manager = db_manager
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY environment variable not set")
            
        self.client = OpenAI(api_key=api_key)
        logger.info("Vector search service initialized")
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text using OpenAI API
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        response = self.client.embeddings.create(
            model="text-embedding-3-large",
            input=[text],
            dimensions=1536
        )
        return response.data[0].embedding
    
    def search(self, query: str, document_id: Optional[int] = None, 
               top_k: int = 5, min_score: float = 0.0) -> List[Dict[str, Any]]:
        """
        Search for similar text chunks using vector similarity
        
        Args:
            query: Search query text
            document_id: Optional ID to limit search to a specific document
            top_k: Number of results to return
            min_score: Minimum similarity score threshold
            
        Returns:
            List of search results with text and metadata
        """
        start_time = time.time()
        
        try:
            # Generate embedding for the query
            logger.info(f"Generating embedding for query: {query}")
            query_embedding = self._generate_embedding(query)
            
            # Build the query
            sql = """
            SELECT 
                c.id, 
                c.document_id, 
                c.chunk_text as text, 
                c.metadata,
                1 - (c.embedding <=> %s::vector) as score
            FROM chunks c
            """
            
            params = [query_embedding]
            
            # Add document filter if specified
            if document_id is not None:
                sql += " WHERE c.document_id = %s"
                params.append(document_id)
            
            # Order by score
            sql += " ORDER BY score DESC"
            
            # Add limit
            sql += " LIMIT %s"
            params.append(top_k)
            
            # Execute query using the database manager
            results = self.db_manager.execute_query(sql, tuple(params), dict_cursor=True)
            
            # Filter results by minimum score and convert to list of dicts
            search_results = []
            for row in results:
                if row['score'] < min_score:
                    continue
                    
                # Parse metadata if it's a string
                if isinstance(row['metadata'], str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse metadata as JSON for chunk {row.get('id')}: {e}")
                        
                # Ensure text is not too long for response
                if len(row['text']) > 1000:
                    row['text'] = row['text'][:997] + '...'
                    
                search_results.append(dict(row))
            
            logger.info(f"Found {len(search_results)} results in {time.time() - start_time:.3f}s")
            return search_results
                
        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            raise