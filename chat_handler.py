import google.generativeai as genai
import os
import re

class ChatHandler:
    def __init__(self):
        self.artwork_context = None
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def set_artwork_context(self, artwork_data):
        """Store the artwork analysis data to use as context for chat."""
        self.artwork_context = artwork_data
    
    def get_chat_response(self, user_message):
        """Generate a response based on the artwork context and user message."""
        if not self.artwork_context:
            return {"error": "No artwork has been analyzed yet. Please upload an image first."}
        
        # Construct the context-aware prompt with formatting instructions
        context = f"""Based on the following artwork analysis:
        Summary: {self.artwork_context['summary']}
        Critique: {self.artwork_context['critique']}
        Similar Artists: {', '.join(self.artwork_context['similarArtists'])}
        Similar Paintings: {', '.join(self.artwork_context['similarPaintings'])}
        
        Please respond to this user message about the artwork: {user_message}
        
        IMPORTANT FORMATTING INSTRUCTIONS:
        1. Structure your response with clear sections using bold headings (**Heading**) when appropriate
        2. Use bullet points (- point) for lists of related information
        3. Use markdown formatting: **bold** for emphasis, *italic* for titles or terms
        4. If mentioning specific techniques, artists, or periods, highlight them with `code` formatting
        5. Organize longer responses into 2-3 paragraphs maximum
        6. If providing numerical data, present it in a structured way
        7. Keep your response concise and well-formatted
        8. When comparing multiple items, use numbered lists (1. First item)
        9. If you're uncertain about something, clearly indicate this
        10. End with a thoughtful conclusion or follow-up question
        
        Your response should be informative yet conversational, and well-structured for easy reading.
        """
        
        try:
            response = self.model.generate_content(context)
            response.resolve()
            formatted_response = self.enhance_response_formatting(response.text)
            return {"response": formatted_response}
        except Exception as e:
            return {"error": f"Failed to generate response: {str(e)}"}
    
    def enhance_response_formatting(self, text):
        """Enhance the formatting of the AI response."""
        # Ensure proper markdown formatting
        enhanced_text = text
        
        # Fix inconsistent bullet points
        enhanced_text = re.sub(r'^\s*•\s*', '- ', enhanced_text, flags=re.MULTILINE)
        enhanced_text = re.sub(r'^\s*\*\s+([^*])', r'- \1', enhanced_text, flags=re.MULTILINE)
        
        # Ensure proper bold formatting
        enhanced_text = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', enhanced_text)
        
        # Ensure proper italic formatting
        enhanced_text = re.sub(r'(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)', r'*\1*', enhanced_text)
        
        # Ensure proper code formatting
        enhanced_text = re.sub(r'`([^`]+)`', r'`\1`', enhanced_text)
        
        # Add spacing after paragraphs
        enhanced_text = re.sub(r'(\n\n|\n)(?=\w)', r'\n\n', enhanced_text)
        
        # Format numbered lists consistently
        enhanced_text = re.sub(r'^\s*(\d+)\.\s*', r'\1. ', enhanced_text, flags=re.MULTILINE)
        
        # Add a clear conclusion if not present
        if not re.search(r'(In conclusion|To summarize|Overall|In summary)', enhanced_text, re.IGNORECASE):
            enhanced_text += "\n\n**In conclusion**, I hope this helps with your understanding of the artwork. Is there anything specific you'd like me to elaborate on?"
        
        return enhanced_text



# Create a global instance
chat_handler = ChatHandler()