from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import requests
import os
import re
from datetime import datetime
import urllib.parse

app = Flask(__name__)
CORS(app)

AI_API_BASE_URL = "https://mkllm.hideme.eu.org/"

# Smart System Prompt: AI-কে বাধ্য করা হচ্ছে ছোট, সহজ এবং ইউজার যে ভাষায় প্রশ্ন করবে সেই ভাষায় উত্তর দিতে।
SMART_SYSTEM_PROMPT = """You are a highly intelligent, fast, and helpful AI assistant.
Strict Rules you MUST follow:
1. Language: ALWAYS reply in the exact language the user used to ask the question (e.g., if Bengali, reply in Bengali).
2. Conciseness: Give the absolutely shortest, simplest, and most direct answer possible. Avoid long paragraphs, complex words, or unnecessary details. Get straight to the point.
3. Images: If asked to generate an image, reply ONLY with the image URL formatted exactly like this: @https://image.pollinations.ai/prompt/YOUR_PROMPT_HERE@"""

def extract_image_urls(text):
    """AI এর উত্তর থেকে ইমেজের লিংক আলাদা করার ফাংশন"""
    pattern = r'@?(https://image\.pollinations\.ai/prompt/[^@\s]+)@?'
    matches = re.findall(pattern, text)
    return list(set(matches))

@app.route('/chat', methods=['GET'])
def chat():
    """
    একমাত্র এবং সবচেয়ে সহজ চ্যাট এন্ডপয়েন্ট
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
        response = requests.get(f"{AI_API_BASE_URL}{encoded_prompt}", timeout=30) # Vercel এর জন্য টাইমআউট কমানো হয়েছে
        response.raise_for_status()
        
        ai_response = response.text.strip()
        image_urls = extract_image_urls(ai_response)
        
        # ইউজারকে দেখানোর জন্য টেক্সট থেকে ইমেজের লিংকগুলো মুছে ফেলা
        clean_response = ai_response
        for url in image_urls:
            clean_response = clean_response.replace(f'@{url}@', '').replace(url, '').strip()
            
        # যদি ইউজার শুধু ছবি চায়, তবে টেক্সট খালি থাকলে একটি ডিফল্ট মেসেজ দেওয়া
        if not clean_response and image_urls:
            clean_response = "আপনার ছবিটি তৈরি করা হয়েছে।"

        return jsonify({
            'success': True,
            'response': clean_response,
            'images': image_urls,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': 'সার্ভার ব্যস্ত আছে বা উত্তর পেতে সমস্যা হচ্ছে।', 
            'details': str(e)
        }), 502

@app.route('/image', methods=['GET'])
def generate_image_direct():
    """
    সরাসরি ব্রাউজারে ছবি দেখার এন্ডপয়েন্ট
    ব্যবহার: /image?prompt=ছবির বর্ননা
    """
    prompt = request.args.get('prompt', '').strip()
    if not prompt:
        return jsonify({'success': False, 'error': 'ছবির বর্ননা (prompt) দিন'}), 400
    
    image_url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
    return redirect(image_url)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
