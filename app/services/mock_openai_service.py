import logging
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.models.schemas import EmbeddingResponse, PatientRecord

logger = logging.getLogger(__name__)
settings = get_settings()


class MockOpenAIService:
    """Mock OpenAI service for testing without real API calls."""
    
    def __init__(self):
        self.client = "mock"
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
        logger.info("Mock OpenAI service initialized")
    
    async def generate_chat_response(
        self, 
        query: str, 
        patient_context: Optional[List[PatientRecord]] = None
    ) -> str:
        """Generate a mock AI response."""
        context_info = ""
        if patient_context:
            context_info = f" Based on {len(patient_context)} patient record(s),"
        
        return f"Mock AI Response:{context_info} Your query was: '{query}'. This is a simulated response for testing purposes."
    
    async def generate_embedding(self, text: str) -> EmbeddingResponse:
        """Generate a mock embedding."""
        # Return a mock embedding vector (1536 dimensions for ada-002 compatibility)
        mock_embedding = [0.1] * 1536
        
        return EmbeddingResponse(
            embedding=mock_embedding,
            model=self.embedding_model,
            dimensions=len(mock_embedding)
        )
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for multiple texts."""
        mock_embedding = [0.1] * 1536
        return [mock_embedding for _ in texts]


# Global service instance (using mock for now)
openai_service = MockOpenAIService()


def get_openai_service():
    """Get OpenAI service instance."""
    return openai_service