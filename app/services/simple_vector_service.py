"""
Temporary simple vector storage service for development/testing.
This replaces Pinecone for now to get the system working.
"""

from typing import List, Dict, Any, Optional
import logging
import uuid
import math
from datetime import datetime
from app.config import get_settings
from app.models.schemas import PatientRecord, SearchResult

logger = logging.getLogger(__name__)
settings = get_settings()


class SimpleVectorService:
    """Simple in-memory vector storage service for testing."""
    
    def __init__(self):
        self.vectors = {}  # {id: {"vector": [...], "metadata": {...}}}
        self.dimension = settings.vector_dimension
        self.top_k = settings.top_k_results
        logger.info("Initialized SimpleVectorService (temporary replacement for Pinecone)")
    
    async def search_patient_history(self, query: str, query_embedding: List[float]) -> SearchResult:
        """
        Search patient history using cosine similarity.
        """
        try:
            logger.info(f"Searching patient history for query: {query[:100]}...")
            
            if not self.vectors:
                logger.info("No vectors stored yet")
                return SearchResult(
                    records=[],
                    query=query,
                    total_results=0
                )
            
            # Calculate similarities
            similarities = []
            
            for record_id, data in self.vectors.items():
                stored_vector = data["vector"]
                
                # Cosine similarity calculation without numpy
                dot_product = sum(a * b for a, b in zip(query_embedding, stored_vector))
                norm_query = math.sqrt(sum(a * a for a in query_embedding))
                norm_stored = math.sqrt(sum(a * a for a in stored_vector))
                
                if norm_query > 0 and norm_stored > 0:
                    similarity = dot_product / (norm_query * norm_stored)
                else:
                    similarity = 0.0
                
                similarities.append({
                    "record_id": record_id,
                    "score": float(similarity),
                    "metadata": data["metadata"]
                })
            
            # Sort by similarity and get top K
            similarities.sort(key=lambda x: x["score"], reverse=True)
            top_results = similarities[:self.top_k]
            
            # Convert to PatientRecord objects
            patient_records = []
            for result in top_results:
                metadata = result["metadata"]
                
                patient_record = PatientRecord(
                    record_id=result["record_id"],
                    patient_id=metadata.get("patient_id"),
                    content=metadata.get("content", ""),
                    metadata=metadata,
                    score=result["score"],
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
        Upsert a patient record to the vector storage.
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
            
            # Store vector and metadata
            self.vectors[record_id] = {
                "vector": embedding,
                "metadata": record_metadata
            }
            
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
        Upsert multiple patient records in batch.
        """
        try:
            record_ids = []
            
            for record in records:
                record_id = await self.upsert_patient_record(
                    content=record["content"],
                    embedding=record["embedding"],
                    metadata=record.get("metadata"),
                    record_id=record.get("record_id")
                )
                record_ids.append(record_id)
            
            logger.info(f"Batch upserted {len(record_ids)} records")
            
            return record_ids
            
        except Exception as e:
            logger.error(f"Error batch upserting records: {str(e)}")
            raise Exception(f"Failed to batch upsert records: {str(e)}")
    
    async def delete_record(self, record_id: str) -> bool:
        """
        Delete a record from the vector storage.
        """
        try:
            if record_id in self.vectors:
                del self.vectors[record_id]
                logger.info(f"Deleted record with ID: {record_id}")
                return True
            else:
                logger.warning(f"Record {record_id} not found for deletion")
                return False
            
        except Exception as e:
            logger.error(f"Error deleting record: {str(e)}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector storage.
        """
        try:
            return {
                "total_vector_count": len(self.vectors),
                "dimension": self.dimension,
                "index_fullness": 0.0,  # Not applicable for in-memory storage
                "storage_type": "simple_memory"
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
simple_vector_service = SimpleVectorService()


def get_simple_vector_service() -> SimpleVectorService:
    """Get simple vector service instance."""
    return simple_vector_service