from typing import Optional
import os
import logging
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import Chroma

MAX_QUESTION_LENGTH = 500

logger = logging.getLogger(__name__)

def get_answer(video_id: str, question: str) -> Optional[str]:
    try:
        logger.info(f"Starting QA processing for video {video_id}")
        
        # Validate inputs
        if not video_id or len(video_id) > 100:
            logger.error(f"Invalid video ID: {video_id}")
            raise ValueError("Invalid video ID")
            
        if not question or len(question) > MAX_QUESTION_LENGTH:
            logger.error(f"Invalid question length: {len(question)}")
            raise ValueError("Question too long or empty")

        # Initialize embeddings
        logger.debug(f"Initializing embeddings for video {video_id}")
        embedding_function = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        
        chroma_path = f"chroma_db/{video_id}"
        logger.debug(f"Chroma DB path: {os.path.abspath(chroma_path)}")
        
        # Check/create vectorstore
        if not os.path.exists(chroma_path):
            from app.utils.transcript import get_transcript
            transcript = get_transcript(video_id)
            if not transcript:
                return "No transcript available for this video"
                
            Chroma.from_texts(
                [transcript],
                embedding=embedding_function,
                persist_directory=chroma_path
            )
        
        vectorstore = Chroma(
            persist_directory=chroma_path,
            embedding_function=embedding_function
        )

        # Comprehensive prompt template for complete, accurate answers
        prompt_template = """You are an intelligent assistant analyzing a YouTube video transcript.
Your goal is to answer the user's question with **complete accuracy** while clearly separating what is in the transcript from what comes from your own knowledge.

Strict Rules for Answering:

1. **Buddy Mode (General Chatbot)**:
   - When question includes 'buddy', respond as full AI assistant
   - Answer any question using comprehensive knowledge
   - No restrictions on topics or individuals
   - Maintain natural, helpful tone

2. Buddy mode (user question **starts with** buddy or Buddy):
   -if user ask something having keyword "buddy" in it, respond like a general AI assistant
   - Ignore the transcript and answer from your own general knowledge/database.
   - You may expand freely—no need for disclaimers or transcript references.

3. Beyond mode (user question **starts with** “beyond the transcript”):
   - First check if the transcript mentions the user’s keywords.
     - **If yes:**  
       1. Quote the transcript excerpt **verbatim**.  
       2. Then add supplemental context prefaced by “Beyond the video:” using your own knowledge.  
     - **If no:**  
       Reply **only**: “The transcript does not mention <keywords>.”
     3.Still relate to video context when applicable

4. **Exhaustive answers for lists and multi-part questions**:  
   - Include every relevant item (e.g., all players, all wickets, all mentioned topics).  
   - Avoid duplicates and preserve the order they appear in the transcript.  
   - Present each item on a **new line only** (no bullets, no dashes, no asterisks). The frontend will format it as needed.

5. **Natural, clean writing style**:  
   - Use proper sentence alignment and paragraph breaks.  
   - Do not include symbols such as "*", "-", or "•" in the text.  
   - Keep the tone conversational but clear.

6. **Context-aware conversation**:  
   - If the user says "hello", "thanks", "ok", or other casual phrases, reply politely and naturally (e.g., "Hello! How can I help?" or "You’re welcome!").  
   - Avoid unnecessary greetings unless the user initiates.

7. **Transcript-derived answers must always begin with**:  
   "Based on the video:"  
   Then continue with the findings from the transcript.

8. **Fallback Global Knowledge Mode**:  
   - If the transcript is empty, irrelevant, or the user explicitly wants extra context, provide an answer from general knowledge.  
   - Start such answers with: "The transcript does not cover this, but based on general knowledge…" to make it clear.

9. **Language Handling**:  
   - If the transcript is in Hindi (or mixed Hindi/English) and the user’s question is also in Hindi or Hinglish, respond in Hinglish naturally.  
   - Do not force English in these cases; match the user’s language style.
10. **No Hallucinations** – 
11. **Video-Specific Responses**:
   - For coding tutorials:
     * Detect and use the programming language from video content
     * Provide complete, executable code blocks when requested
     * Include syntax highlighting matching the language
     * Add relevant comments and explanations
     * use code snippet for code blocks
   - For other tutorials:
     * Create structured notes with timestamps
     * Extract key concepts and procedural steps
     * Generate actionable summaries
     * Include visual indicators (🔹, ⚡) for important points
   - Format all responses using markdown for better readability


Transcript Context:
{context}

User Question:
{question}

Final Answer:
"""
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # Create QA chain with proper prompt including context
        logger.debug("Creating QA chain")
        qa_chain = RetrievalQA.from_chain_type(
            llm=ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.3
            ),
            chain_type="stuff",
            retriever=vectorstore.as_retriever(),
            chain_type_kwargs={
                "prompt": prompt,
                "document_variable_name": "context"
            }
        )

        # Execute QA chain with robust error handling
        logger.info(f"Processing question: {question[:50]}...")
        try:
            result = qa_chain.invoke({"query": question})
            if not result or not result.get("result"):
                logger.warning("Empty or invalid response from QA chain")
                return "I couldn't find a definitive answer in the video"
                
            answer = result['result'].strip()
            
            # Filter out low-confidence answers
            if any(phrase.lower() in answer.lower() for phrase in ["i don't know", "i'm not sure"]):
                return "The video doesn't specifically mention this, but it discusses: " + \
                       answer.replace("I don't know", "").replace("I'm not sure", "")
                
            return f"Answer: {answer}"
            
        except Exception as e:
            logger.error(f"QA processing error: {str(e)}", exc_info=True)
            return "I couldn't process your question at this time"
            
    except Exception as e:
        logger.error(f"QA system error: {str(e)}", exc_info=True)
        return "System Error: Please try again later"
