from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from datetime import datetime
import urllib.parse

app = Flask(__name__)
CORS(app)

# শুধুমাত্র টেক্সট এপিআই ইউআরএল
AI_API_BASE_URL = "https://mkllm.hideme.eu.org/"

# Smart System Prompt: টেক্সট-অনলি, মাল্টি-ল্যাঙ্গুয়েজ এবং সংক্ষিপ্ত উত্তরের নির্দেশিকা
SMART_SYSTEM_PROMPT = """You are a highly intelligent, fast, and helpful AI assistant.
Strict Rules you MUST follow:
1. Text-Only: You are a pure text-based AI. You CANNOT generate, display, or process images. If a user asks for an image, politely decline and say you only work with text.
2. Language: ALWAYS reply in the exact language the user used to ask the question (e.g., if Bengali, reply in Bengali).
3. Conciseness: Give the absolutely shortest, simplest, and most direct answer possible. Avoid long paragraphs, complex words, or unnecessary details. Get straight to the point."""

@app.route('/chat', methods=['GET'])
def chat():
    """
    একমাত্র এবং সবচেয়ে সহজ টেক্সট চ্যাট এন্ডপয়েন্ট
    ব্যবহার: /chat?prompt=আপনার প্রশ্ন
    """
    user_prompt = request.args.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({
            'success': False, 
            'error': 'অনুগ্রহ করে একটি প্রশ্ন (prompt) দিন।'
        }), 400
    
    # AI-এর জন্য স্মার্ট প্রম্পট তৈরি করা
    full_prompt = f"{SMART_SYSTEM_PROMPT}\n\nUser: {user_prompt}\nYour response:"
    
    try:
        # AI সার্ভারে রিকোয়েস্ট পাঠানো
        encoded_prompt = urllib.parse.quote(full_prompt)
        response = requests.get(f"{AI_API_BASE_URL}{encoded_prompt}", timeout=30)
        response.raise_for_status()
        
        # ক্লিন টেক্সট রেসপন্স
        ai_response = response.text.strip()
        
        return jsonify({
            'success': True,
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False, 
            'error': 'সার্ভার টাইমআউট হয়েছে (৩০ সেকেন্ড)। অনুগ্রহ করে আবার চেষ্টা করুন।'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': 'সার্ভার ব্যস্ত আছে বা উত্তর পেতে সমস্যা হচ্ছে।', 
            'details': str(e)
        }), 502

@app.route('/', methods=['GET'])
def index():
    """রুট এন্ডপয়েন্ট: সার্ভার স্ট্যাটাস চেক করার জন্য"""
    return jsonify({
        'name': 'Smart Text AI API',
        'status': 'Active',
        'usage': 'GET /chat?prompt=your_question_here'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # প্রোডাকশনের জন্য debug=False
    app.run(host='0.0.0.0', port=port, debug=False)
