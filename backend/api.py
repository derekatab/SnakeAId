from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Prepare the prompt with safety guidelines
        system_prompt = """
        You are a snake bite emergency response system. Your role is to provide immediate, clear, and safe guidance.
        
        Rules:
        1. Always prioritize getting medical help immediately
        2. Never attempt to identify specific snake species
        3. Focus on immediate safety and first aid
        4. Keep responses clear and concise
        5. Include emergency number 999
        6. Adapt the response based on whether it's about the person messaging or someone else
        
        Base your response on this template, but vary it naturally:
        'Move [yourself/them] away from the snake. \n Remove tight items like rings/bracelets. Keep [them/yourself] calm and still. \n Keep the affected limb still and straight. Don't tie anything around it or try to cut/suck the bite. \n If transport is far, make a stretcher using available materials. Get to a health facility immediately. \n If [they feel/you feel] dizzy or vomit, lay on the left side. Watch breathing and be ready to help if needed.'
        """
        
        # Combine system prompt with user message
        prompt = f"{system_prompt}\n\nUser message: {request.message}\n\nResponse:"
        
        # Generate response using Gemini
        response = model.generate_content(prompt)
        
        # If response is unclear or empty, use fallback
        if not response or not response.text:
            raise HTTPException(status_code=500, detail="Failed to generate response")
            
        return {"response": response.text}
        
    except Exception as e:
        # Return fallback message on any error
        fallback = "Immediately move away from the area where the bite occurred. If the snake is still attached use a stick or tool to make it let go. Seek medical support immediately: the emergency number in this area is 999."
        return {"response": fallback}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5001)
