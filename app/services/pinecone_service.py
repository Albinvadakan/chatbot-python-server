from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime
from app.config import get_settings
from app.models.schemas import PatientRecord, SearchResult

logger = logging.getLogger(__name__)
settings = get_settings()


class PineconeService:
    """Service for handling Pinecone vector database operations."""
    
    def __init__(self):
        # Initialize Pinecone with the new API (version 5.0+)
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.dimension = settings.vector_dimension
        self.top_k = settings.top_k_results
        self._index = None
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize Pinecone index connection."""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                logger.warning(f"Index '{self.index_name}' does not exist. Creating new index...")
                # Create index with timeout handling
                try:
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud='aws',
                            region='us-east-1'
                        )
                    )
                    logger.info(f"Index creation initiated: {self.index_name}")
                    
                    # Wait for index to be ready (with timeout)
                    import time
                    max_wait_time = 60  # 1 minute timeout for startup
                    wait_interval = 5
                    elapsed_time = 0
                    
                    while elapsed_time < max_wait_time:
                        try:
                            index_description = self.pc.describe_index(self.index_name)
                            if index_description.status.ready:
                                logger.info(f"Index {self.index_name} is ready!")
                                break
                            else:
                                logger.info(f"Index {self.index_name} is still initializing... ({elapsed_time}s elapsed)")
                                time.sleep(wait_interval)
                                elapsed_time += wait_interval
                        except Exception as e:
                            logger.warning(f"Error checking index status: {str(e)}")
                            time.sleep(wait_interval)
                            elapsed_time += wait_interval
                    
                    if elapsed_time >= max_wait_time:
                        logger.warning(f"Index creation timeout after {max_wait_time}s. Proceeding anyway...")
                        
                except Exception as create_error:
                    logger.error(f"Failed to create index: {str(create_error)}")
                    raise create_error
            
            # Connect to index
            self._index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            
        except Exception as e:
            logger.error(f"Error initializing Pinecone index: {str(e)}")
            # Don't raise exception, allow service to start without Pinecone
            logger.warning("Pinecone service will be unavailable")
    
    @property
    def index(self):
        """Get Pinecone index instance."""
        if self._index is None:
            self._initialize_index()
        return self._index
    
    async def search_patient_history(self, query: str, query_embedding: List[float]) -> SearchResult:
        """
        Search patient history using vector similarity.
        
        Args:
            query: Original query string
            query_embedding: Query embedding vector
            
        Returns:
            SearchResult with matching patient records
        """
        try:
            logger.info(f"Searching patient history for query: {query[:100]}...")
            
            # Perform vector search
            search_response = self.index.query(
                vector=query_embedding,
                top_k=self.top_k,
                include_metadata=True,
                include_values=False
            )
            
            # Convert results to PatientRecord objects
            patient_records = []
            for match in search_response.matches:
                metadata = match.metadata or {}
                
                patient_record = PatientRecord(
                    record_id=match.id,
                    patient_id=metadata.get("patient_id"),
                    content=metadata.get("content", ""),
                    metadata=metadata,
                    score=float(match.score),
                    timestamp=self._parse_timestamp(metadata.get("timestamp"))
                )
                patient_records.append(patient_record)
            
            logger.info(f"Found {len(patient_records)} matching records")
            
            return SearchResult(
                records=patient_records,
                query=query,
                total_results=len(patient_records)
            )
            
        except Exception as e:
            logger.error(f"Error searching patient history: {str(e)}")
            raise Exception(f"Failed to search patient history: {str(e)}")
    
    async def upsert_patient_record(
        self, 
        content: str, 
        embedding: List[float], 
        metadata: Optional[Dict[str, Any]] = None,
        record_id: Optional[str] = None
    ) -> str:
        """
        Upsert a patient record to the vector database.
        
        Args:
            content: Text content of the record
            embedding: Embedding vector for the content
            metadata: Additional metadata for the record
            record_id: Optional custom record ID
            
        Returns:
            Record ID of the upserted record
        """
        try:
            if record_id is None:
                record_id = str(uuid.uuid4())
            
            # Prepare metadata
            record_metadata = {
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "content_length": len(content)
            }
            
            if metadata:
                record_metadata.update(metadata)
            
            # Upsert to Pinecone
            self.index.upsert(
                vectors=[{
                    "id": record_id,
                    "values": embedding,
                    "metadata": record_metadata
                }]
            )
            
            logger.info(f"Upserted record with ID: {record_id}")
            
            return record_id
            
        except Exception as e:
            logger.error(f"Error upserting patient record: {str(e)}")
            raise Exception(f"Failed to upsert patient record: {str(e)}")
    
    async def upsert_patient_records_batch(
        self, 
        records: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Upsert multiple patient records in batch with chunking for better performance.
        
        Args:
            records: List of record dictionaries with 'content', 'embedding', and optional 'metadata'
            
        Returns:
            List of record IDs
        """
        try:
            logger.info(f"Starting batch upsert of {len(records)} records")
            
            # Process in chunks to avoid timeout and memory issues
            chunk_size = 100  # Pinecone recommends max 100 vectors per upsert
            all_record_ids = []
            
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                vectors = []
                chunk_record_ids = []
                
                for record in chunk:
                    record_id = record.get("record_id", str(uuid.uuid4()))
                    chunk_record_ids.append(record_id)
                    
                    metadata = {
                        "content": record["content"],
                        "timestamp": datetime.utcnow().isoformat(),
                        "content_length": len(record["content"])
                    }
                    
                    if record.get("metadata"):
                        metadata.update(record["metadata"])
                    
                    vectors.append({
                        "id": record_id,
                        "values": record["embedding"],
                        "metadata": metadata
                    })
                
                # Upsert this chunk
                try:
                    self.index.upsert(vectors=vectors)
                    all_record_ids.extend(chunk_record_ids)
                    logger.info(f"Upserted chunk {i//chunk_size + 1}/{(len(records) + chunk_size - 1)//chunk_size} ({len(vectors)} vectors)")
                except Exception as chunk_error:
                    logger.error(f"Error upserting chunk {i//chunk_size + 1}: {str(chunk_error)}")
                    # Continue with other chunks instead of failing completely
                    continue
            
            logger.info(f"Batch upsert completed: {len(all_record_ids)}/{len(records)} records successful")
            
            return all_record_ids
            
        except Exception as e:
            logger.error(f"Error batch upserting records: {str(e)}")
            raise Exception(f"Failed to batch upsert records: {str(e)}")
    
    async def delete_record(self, record_id: str) -> bool:
        """
        Delete a record from the vector database.
        
        Args:
            record_id: ID of the record to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            self.index.delete(ids=[record_id])
            logger.info(f"Deleted record with ID: {record_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting record: {str(e)}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Pinecone index.
        
        Returns:
            Dictionary with index statistics
        """
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": dict(stats.namespaces) if stats.namespaces else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {}
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None
        
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


# Global service instance
pinecone_service = PineconeService()


def get_pinecone_service() -> PineconeService:
    """Get Pinecone service instance."""
    return pinecone_service