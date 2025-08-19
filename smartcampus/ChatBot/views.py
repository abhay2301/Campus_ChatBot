# smartcampus/chatbot/views.py
'''Views for the ChatBot application.'''

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import os
from pathlib import Path
import google.generativeai as genai
import time
import requests
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

# Load knowledge base
BASE_DIR = Path(__file__).resolve().parent.parent
KB_PATH = os.path.join(BASE_DIR, 'ChatBot', 'knowledge_base.json')

# Cache for knowledge base to avoid repeated file reads
_knowledge_base_cache = None

def load_knowledge_base():
    """Load the knowledge base from JSON file with caching"""
    global _knowledge_base_cache
    
    if _knowledge_base_cache is not None:
        return _knowledge_base_cache
    
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            _knowledge_base_cache = json.load(f)
            logger.info("Knowledge base loaded successfully")
            return _knowledge_base_cache
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {str(e)}")
        return None

def scrape_website_content(url, max_chars=1000):
    """Scrape content from college website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit text length
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        return text
    
    except Exception as e:
        logger.error(f"Error scraping website {url}: {str(e)}")
        return None

def get_college_website_info(query, kb_data):
    """Get college website information and optionally scrape content"""
    if not kb_data or 'college_info' not in kb_data:
        return None
    
    college_info = kb_data['college_info']
    website = college_info.get('website', '')
    
    query_lower = query.lower()
    
    # Check if user is asking for website or college details
    if any(word in query_lower for word in ['website', 'site', 'url', 'link']):
        return f"Our official college website is: {website}\n\nYou can find detailed information about:\n• Admissions: {college_info.get('admissions_url', '')}\n• Courses: {college_info.get('courses_url', '')}\n• Contact: {college_info.get('contact_url', '')}"
    
    # If asking for college details, provide website and try to scrape content
    if any(word in query_lower for word in ['college detail', 'about college', 'college info', 'tell me about', 'what is sit']):
        response = f"Here are the details about {college_info.get('name', 'our college')}:\n\n"
        response += f"🌐 Official Website: {website}\n\n"
        
        # Try to scrape some content from the main website
        scraped_content = scrape_website_content(website)
        if scraped_content:
            response += f"Website Content Preview:\n{scraped_content}\n\n"
        
        response += f"For more detailed information, please visit: {website}"
        return response
    
    return None

def search_knowledge_base(query, kb_data):
    """Enhanced search for answers in the knowledge base with website integration"""
    if not kb_data:
        return None
    
    # First check for website-related queries
    website_info = get_college_website_info(query, kb_data)
    if website_info:
        return website_info
    
    query_lower = query.lower().strip()
    
    # Remove common stop words and clean the query
    stop_words = ['the', 'is', 'at', 'which', 'on', 'what', 'how', 'can', 'i', 'you', 'a', 'an', 'and', 'or', 'but', 'in', 'with', 'to']
    query_words = [word for word in query_lower.split() if word not in stop_words and len(word) > 2]
    
    # Search in FAQs with improved matching
    if 'faqs' in kb_data:
        best_match = None
        best_score = 0
        
        for faq in kb_data['faqs']:
            question_lower = faq['question'].lower()
            
            # Calculate matching score
            matches = sum(1 for word in query_words if word in question_lower)
            if matches > 0:
                score = matches / len(query_words) if query_words else 0
                if score > best_score and score >= 0.3:
                    best_score = score
                    best_match = faq['answer']
        
        if best_match:
            # If the FAQ answer doesn't include website but query might need it, append website
            if 'website' not in best_match.lower() and any(word in query_lower for word in ['more info', 'detail', 'website']):
                college_info = kb_data.get('college_info', {})
                website = college_info.get('website', '')
                if website:
                    best_match += f"\n\nFor more information, visit: {website}"
            return best_match
    
    # Search in structured sections with website links
    admission_keywords = ['admission', 'apply', 'eligibility', 'requirement', 'join', 'enroll']
    exam_keywords = ['exam', 'test', 'schedule', 'midterm', 'final', 'examination']
    placement_keywords = ['placement', 'job', 'company', 'salary', 'package', 'career', 'employment']
    
    college_info = kb_data.get('college_info', {})
    
    if any(word in query_lower for word in admission_keywords):
        admissions = kb_data.get('admissions', {})
        response = ""
        
        if 'process' in query_lower or 'how' in query_lower or 'step' in query_lower:
            response = f"Admission Process:\n{admissions.get('process', 'Information not available')}"
        elif 'requirement' in query_lower or 'eligibility' in query_lower or 'criteria' in query_lower:
            response = f"Admission Requirements:\n{admissions.get('requirements', 'Information not available')}"
        elif 'deadline' in query_lower or 'last date' in query_lower or 'when' in query_lower:
            response = f"Admission Deadline:\n{admissions.get('deadline', 'Information not available')}"
        else:
            response = f"Admission Information:\n\nProcess: {admissions.get('process', 'Not available')}\n\nRequirements: {admissions.get('requirements', 'Not available')}\n\nDeadline: {admissions.get('deadline', 'Not available')}"
        
        # Add website link for admissions
        if college_info.get('admissions_url'):
            response += f"\n\n🌐 For detailed admission information, visit: {college_info.get('admissions_url')}"
        elif college_info.get('website'):
            response += f"\n\n🌐 For more details, visit: {college_info.get('website')}"
        
        return response
    
    if any(word in query_lower for word in exam_keywords):
        exams = kb_data.get('exams', {})
        response = f"Exam Information:\n\nSchedule: {exams.get('schedule', 'Not available')}\n\nRules: {exams.get('rules', 'Not available')}"
        if college_info.get('website'):
            response += f"\n\n🌐 For more exam details, visit: {college_info.get('website')}"
        return response
    
    if any(word in query_lower for word in placement_keywords):
        placements = kb_data.get('placements', {})
        response = f"Placement Information:\n\nCompanies: {placements.get('companies', 'Not available')}\n\nStatistics: {placements.get('stats', 'Not available')}"
        if college_info.get('website'):
            response += f"\n\n🌐 For detailed placement reports, visit: {college_info.get('website')}"
        return response
    
    return None

def get_gemini_response(query, kb_context="", retry_count=0):
    """Get response from Gemini 2.0 Flash API with website context"""
    max_retries = 2
    
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            logger.warning("Gemini API key not found")
            return "I apologize, but I'm currently operating with limited capabilities. I can help you with questions about admissions, exams, and placements using our college database."
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Enhanced context with website information
        context = f"""You are JARVIS, an AI assistant for SIT college. You are professional, helpful, and consistent in your responses. 
        Always address users respectfully as 'Sir' or 'Madam'.
        
        College Information Context:
        {kb_context}
        
        When users ask for college details or more information, always mention the official website and encourage them to visit it.
        If you don't have specific information, suggest they check the college website.
        
        User Question: {query}
        
        Provide intelligent, conversational responses. Include website links when relevant."""
        
        response = model.generate_content(
            context,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=400,
                top_p=0.9,
                top_k=40,
                candidate_count=1,
                stop_sequences=None,
            ),
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH", 
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        )
        
        if not response.text or response.text.strip() == "":
            return "I apologize, but I cannot generate a response to that query. Please try rephrasing your question."
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Gemini API error: {str(e)}")
        if retry_count < max_retries:
            time.sleep(2 ** retry_count)
            return get_gemini_response(query, kb_context, retry_count + 1)
        return "I'm having trouble accessing my advanced capabilities right now, but I can still help with college-specific questions."

def is_college_specific_query(query):
    """Determine if query is about college-specific information"""
    college_keywords = [
        'admission', 'fee', 'exam', 'placement', 'course', 'eligibility',
        'sit', 'college', 'university', 'semester', 'hostel', 'faculty',
        'b.tech', 'engineering', 'deadline', 'requirement', 'scholarship',
        'website', 'contact', 'about college', 'college detail'
    ]
    return any(keyword in query.lower() for keyword in college_keywords)

def get_intelligent_response(query, kb_data):
    """Intelligent routing between knowledge base and Gemini AI with website integration"""
    # First, try knowledge base for college-specific questions
    kb_answer = search_knowledge_base(query, kb_data)
    
    if kb_answer and is_college_specific_query(query):
        logger.info("Using knowledge base response with website info")
        return kb_answer
    
    # Prepare enhanced context from knowledge base for Gemini
    kb_context = ""
    if kb_data:
        college_info = kb_data.get('college_info', {})
        kb_context = f"""College Website: {college_info.get('website', 'Not available')}
        Admissions: {kb_data.get('admissions', {})}
        Exams: {kb_data.get('exams', {})}
        Placements: {kb_data.get('placements', {})}"""
    
    logger.info("Using Gemini 2.0 Flash AI response with website context")
    return get_gemini_response(query, kb_context)

def chatbot_ui(request):
    """Render the main chatbot interface"""
    return render(request, 'chatbot_ui.html')

@csrf_exempt
def chatbot_view(request):
    """Handle chatbot API requests with website integration"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('query', '').strip()
            
            if not user_query:
                return JsonResponse({'error': 'No query provided'}, status=400)
            
            if len(user_query) > 500:
                return JsonResponse({'response': 'Please keep your question under 500 characters for better processing.'})
            
            logger.info(f"User query: {user_query}")
            
            # Load knowledge base
            kb_data = load_knowledge_base()
            
            # Get intelligent response using routing system
            response = get_intelligent_response(user_query, kb_data)
            
            logger.info(f"Bot response: {response[:100]}...")
            return JsonResponse({'response': response})
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return JsonResponse({'error': 'Invalid JSON format in request'}, status=400)
        
        except Exception as e:
            logger.error(f"Unexpected error in chatbot_view: {str(e)}", exc_info=True)
            return JsonResponse({'response': 'I apologize, but I encountered a technical issue. Please try rephrasing your question or ask about our college admissions, exams, or placement information.'})
    
    return JsonResponse({'error': 'Only POST method allowed'}, status=405)
