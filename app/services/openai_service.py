import openai
from typing import List, Dict, Any, Optional
import logging
from app.config import get_settings
from app.models.schemas import EmbeddingResponse, PatientRecord

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize OpenAI client
openai.api_key = settings.openai_api_key


class OpenAIService:
    """Service for handling OpenAI API interactions."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature
    
    async def generate_chat_response(
        self, 
        query: str, 
        patient_context: Optional[List[PatientRecord]] = None
    ) -> str:
        """
        Generate AI response using OpenAI GPT model.
        
        Args:
            query: User query/question
            patient_context: Optional list of relevant patient records
            
        Returns:
            Generated AI response
        """
        try:
            # Build context-aware prompt
            system_prompt = self._build_system_prompt(patient_context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            logger.info(f"Generating chat response for query: {query[:100]}...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                n=1,
                stop=None
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"Generated response length: {len(ai_response)}")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            raise Exception(f"Failed to generate AI response: {str(e)}")
    
    async def generate_embedding(self, text: str) -> EmbeddingResponse:
        """
        Generate text embedding using OpenAI embedding model.
        
        Args:
            text: Text to be embedded
            
        Returns:
            EmbeddingResponse with embedding vector
        """
        try:
            logger.info(f"Generating embedding for text length: {len(text)}")
            
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text.replace("\n", " "),
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            
            return EmbeddingResponse(
                embedding=embedding,
                model=self.embedding_model,
                dimensions=len(embedding)
            )
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise Exception(f"Failed to generate embedding: {str(e)}")
    
    def _build_system_prompt(self, patient_context: Optional[List[PatientRecord]] = None) -> str:
        """
        Build system prompt with optional patient context.
        
        Args:
            patient_context: Optional list of patient records for context
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful medical assistant chatbot. You provide informative and accurate responses about medical queries based on available patient data and general medical knowledge.

Important guidelines:
- Always prioritize patient safety and privacy
- Provide helpful information but remind users to consult healthcare professionals for medical decisions
- If patient records are provided, use them to give contextual responses
- Be clear about the limitations of AI-generated medical advice
- Maintain a professional and empathetic tone"""
        
        if patient_context and len(patient_context) > 0:
            context_section = "\n\nRelevant Patient Records:\n"
            for i, record in enumerate(patient_context, 1):
                context_section += f"\nRecord {i}:\n"
                context_section += f"Content: {record.content[:500]}...\n"
                if record.metadata:
                    context_section += f"Metadata: {record.metadata}\n"
                if record.score:
                    context_section += f"Relevance Score: {record.score:.3f}\n"
            
            base_prompt += context_section
            base_prompt += "\n\nUse the above patient records to provide contextual and relevant responses."
        
        return base_prompt
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch with chunking for better performance.
        
        Args:
            texts: List of texts to be embedded
            
        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            
            # OpenAI has a limit of 2048 inputs per request
            batch_size = 2000
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                # Clean texts
                cleaned_texts = [text.replace("\n", " ") for text in batch_texts]
                
                try:
                    response = self.client.embeddings.create(
                        model=self.embedding_model,
                        input=cleaned_texts,
                        encoding_format="float"
                    )
                    
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                    logger.info(f"Generated embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch_embeddings)} embeddings)")
                    
                except Exception as batch_error:
                    logger.error(f"Error in batch {i//batch_size + 1}: {str(batch_error)}")
                    # Create empty embeddings for failed batch to maintain order
                    empty_embeddings = [[0.0] * 1536 for _ in batch_texts]  # Ada-002 dimension
                    all_embeddings.extend(empty_embeddings)
            
            logger.info(f"Generated {len(all_embeddings)} total embeddings")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise Exception(f"Failed to generate batch embeddings: {str(e)}")


# Global service instance
openai_service = OpenAIService()


def get_openai_service() -> OpenAIService:
    """Get OpenAI service instance."""
    return openai_service