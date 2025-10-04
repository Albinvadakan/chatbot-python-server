import openai
from typing import List, Dict, Any, Optional
import logging
from app.config import get_settings
from app.models.schemas import EmbeddingResponse, PatientRecord

logger = logging.getLogger(__name__)
settings = get_settings()


class OpenAIService:
    """Service for handling OpenAI API interactions."""
    
    def __init__(self):
        try:
            # Initialize OpenAI client with just the API key
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
            
            self.model = settings.openai_model
            self.embedding_model = settings.openai_embedding_model
            self.max_tokens = settings.max_tokens
            self.temperature = settings.temperature
            
            logger.info(f"OpenAI service initialized with model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {str(e)}")
            # Don't raise exception, allow service to start
            self.client = None
            logger.warning("OpenAI service will be unavailable")
    
    async def generate_chat_response(
        self, 
        query: str, 
        patient_context: Optional[List[PatientRecord]] = None,
        is_patient_specific: bool = False,
        patient_name: Optional[str] = None
    ) -> str:
        """
        Generate AI response using OpenAI GPT model.
        
        Args:
            query: User query/question
            patient_context: Optional list of relevant patient records
            is_patient_specific: Whether this is a patient-specific query requiring filtered data
            patient_name: Name of the patient for personalized responses
            
        Returns:
            Generated AI response
        """
        try:
            if self.client is None:
                raise Exception("OpenAI client not initialized")
                
            # Build context-aware prompt
            system_prompt = self._build_system_prompt(patient_context, is_patient_specific, patient_name)
            
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
            if self.client is None:
                raise Exception("OpenAI client not initialized")
                
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
    
    def _build_system_prompt(
        self, 
        patient_context: Optional[List[PatientRecord]] = None, 
        is_patient_specific: bool = False,
        patient_name: Optional[str] = None
    ) -> str:
        """
        Build system prompt with optional patient context and privacy guidelines.
        
        Args:
            patient_context: Optional list of patient records for context
            is_patient_specific: Whether this is a patient-specific query
            patient_name: Name of the patient for personalized responses
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful medical assistant chatbot. You provide informative and accurate responses about medical queries based on available patient data and general medical knowledge.

Important guidelines:
- Always prioritize patient safety and privacy
- Provide helpful information but remind users to consult healthcare professionals for medical decisions
- Be clear about the limitations of AI-generated medical advice
- Maintain a professional and empathetic tone"""

        if is_patient_specific:
            # Add privacy protection guidelines for patient-specific queries
            base_prompt += """

CRITICAL PRIVACY REQUIREMENTS:
- This is a PATIENT-SPECIFIC query requiring strict privacy protection
- ONLY use information that belongs to the specified patient
- DO NOT include or reference any other patient's data
- If no relevant patient records are found, clearly state that no records are available
- Focus responses on the specific patient's data only"""
            
            if patient_name:
                base_prompt += f"""
- The patient's name is: {patient_name}
- Personalize responses appropriately while maintaining professionalism"""
        else:
            # For general queries, allow broader information
            base_prompt += """

GENERAL INFORMATION MODE:
- This is a general medical/hospital information query
- You can provide broad, non-patient-specific information
- Include general medical knowledge, hospital services, department information, etc.
- No patient privacy restrictions apply for this type of query"""
        
        if patient_context and len(patient_context) > 0:
            context_section = "\n\nRelevant Records:\n"
            for i, record in enumerate(patient_context, 1):
                context_section += f"\nRecord {i}:\n"
                context_section += f"Content: {record.content[:500]}...\n"
                if record.metadata:
                    context_section += f"Metadata: {record.metadata}\n"
                if record.score:
                    context_section += f"Relevance Score: {record.score:.3f}\n"
            
            base_prompt += context_section
            
            if is_patient_specific:
                base_prompt += f"\n\nUse ONLY the above patient-specific records to provide responses. Do not include information from other patients."
            else:
                base_prompt += f"\n\nUse the above records along with general medical knowledge to provide comprehensive responses."
        elif is_patient_specific:
            base_prompt += "\n\nNo patient-specific records found. Inform the user that no records are available for their query."
        
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
            if self.client is None:
                raise Exception("OpenAI client not initialized")
                
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