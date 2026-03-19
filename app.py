from flask import Flask, request, jsonify, Response, redirect
from flask_cors import CORS
import requests
import os
import json
import re
from datetime import datetime
import urllib.parse

app = Flask(__name__)
CORS(app)

# Configuration
AI_API_BASE_URL = "https://mkllm.hideme.eu.org/"
IMAGE_API_BASE_URL = "https://image.pollinations.ai/prompt/"
DEFAULT_AI_NAME = "Diablo"

# Model configurations
MODEL_PROMPTS = {
    '2.0 Pro': "You are a helpful AI assistant named Diablo.GPT. Give reply in user ask for language. You are capable of generating code snippets in various programming languages upon request. You can also generate images. To generate an image, respond with a message containing only the image URL, formatted like this: @https://image.pollinations.ai/prompt/YOUR_PROMPT_HERE@ . And create minimum 2 different image by prompt. You also able to edit the image by user's instruction. Your creator is Code Library. Give friendly responses. Provide detailed and comprehensive responses to all queries.",
    
    '2.0 Mini': "You are a logical and concise AI assistant. Give reply in user ask for language. Your primary function is to provide direct answers and factual information without unnecessary embellishment. You can generate code snippets and images, but keep your responses brief and to the point. Your name is Diablo.GPT.",
    
    '1.75 oD': "You are a creative and conversational AI assistant named Diablo.GPT. Give reply in user ask for language. You enjoy storytelling, writing poetry, and brainstorming new ideas. You are able to generate images and complex code, and you always provide engaging and elaborate responses.",
    
    '1.5 mini': "You are only a text-based AI assistant and you do not generate any images or codes. Your name is Diablo.GPT, and your responses are always based on the text provided to you, without any visual or programming elements. Your responses should be concise and focused on the provided text.",
    
    'Imagine Mini': "Give reply in user ask for language. You are an AI assistant specialized in generating images. Your sole purpose is to create images based on user descriptions. You must respond with only the image URL, formatted as: @https://image.pollinations.ai/prompt/YOUR_PROMPT_HERE@ ."
}

def extract_image_urls(text):
    """Extract image URLs from AI response"""
    # Pattern for @https://image.pollinations.ai/prompt/...@
    pattern = r'@(https://image\.pollinations\.ai/prompt/[^@\s]+)@'
    matches = re.findall(pattern, text)
    
    # Also check for plain URLs
    plain_pattern = r'(https://image\.pollinations\.ai/prompt/[^\s@]+)'
    plain_matches = re.findall(plain_pattern, text)
    
    all_urls = list(set(matches + plain_matches))
    return all_urls

def build_conversation_context(history, current_message, model):
    """Build the full prompt with system instructions and history"""
    system_prompt = MODEL_PROMPTS.get(model, MODEL_PROMPTS['2.0 Pro'])
    
    conversation_parts = [system_prompt, "\nConversation:"]
    
    for msg in history:
        if msg.get('isThinking'):
            continue
        prefix = "User" if msg.get('type') == 'user' else "AI"
        conversation_parts.append(f"{prefix}: {msg.get('message', '')}")
    
    conversation_parts.append(f"User: {current_message}")
    conversation_parts.append("Your response:")
    
    return "\n".join(conversation_parts)

@app.route('/chat', methods=['GET'])
def chat():
    """
    Main chat endpoint
    URL format: http://localhost:5000/chat?prompt={question}
    """
    user_prompt = request.args.get('prompt', '').strip()
    model = request.args.get('model', '2.0 Pro')
    history_json = request.args.get('history', '[]')
    direct_image = request.args.get('direct_image', 'false').lower() == 'true'
    
    if not user_prompt:
        return jsonify({
            'success': False,
            'error': 'Missing prompt parameter'
        }), 400
    
    try:
        history = json.loads(history_json) if history_json else []
    except json.JSONDecodeError:
        history = []
    
    # Build full prompt with context
    full_prompt = build_conversation_context(history, user_prompt, model)
    
    try:
        # Forward to external AI API
        encoded_prompt = urllib.parse.quote(full_prompt)
        response = requests.get(f"{AI_API_BASE_URL}{encoded_prompt}", timeout=60)
        response.raise_for_status()
        
        ai_response = response.text.strip()
        
        # Extract image URLs from response
        image_urls = extract_image_urls(ai_response)
        
        # If direct_image=true and only one image URL found, redirect to it
        if direct_image and len(image_urls) == 1:
            return redirect(image_urls[0])
        
        # Clean up response (remove @ wrappers for display)
        clean_response = ai_response
        for url in image_urls:
            clean_response = clean_response.replace(f'@{url}@', url)
        
        return jsonify({
            'success': True,
            'response': clean_response,
            'raw_response': ai_response,
            'images': image_urls,
            'image_count': len(image_urls),
            'model': model,
            'ai_name': DEFAULT_AI_NAME,
            'timestamp': datetime.now().isoformat(),
            'prompt_received': user_prompt
        })
        
    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Request timeout',
            'message': 'AI took too long to respond'
        }), 504
        
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to get AI response'
        }), 502

@app.route('/image/direct', methods=['GET'])
def direct_image():
    """
    Get direct image from AI prompt
    URL format: http://localhost:5000/image/direct?prompt={description}
    Redirects directly to the generated image
    """
    user_prompt = request.args.get('prompt', '').strip()
    model = request.args.get('model', 'Imagine Mini')
    
    if not user_prompt:
        return jsonify({
            'success': False,
            'error': 'Missing prompt parameter'
        }), 400
    
    # Build prompt for image generation
    system_prompt = MODEL_PROMPTS.get(model, MODEL_PROMPTS['Imagine Mini'])
    full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\nYour response:"
    
    try:
        # Get AI response
        encoded_prompt = urllib.parse.quote(full_prompt)
        response = requests.get(f"{AI_API_BASE_URL}{encoded_prompt}", timeout=60)
        response.raise_for_status()
        
        ai_response = response.text.strip()
        image_urls = extract_image_urls(ai_response)
        
        if not image_urls:
            return jsonify({
                'success': False,
                'error': 'No image URL found in AI response',
                'ai_response': ai_response
            }), 404
        
        # Redirect to first image
        return redirect(image_urls[0])
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/image', methods=['GET'])
def generate_image():
    """
    Image generation endpoint
    URL format: http://localhost:5000/image?prompt={description}
    """
    prompt = request.args.get('prompt', '').strip()
    direct = request.args.get('direct', 'false').lower() == 'true'
    
    if not prompt:
        return jsonify({
            'success': False,
            'error': 'Missing prompt parameter'
        }), 400
    
    try:
        # Build Pollinations URL
        encoded_prompt = urllib.parse.quote(prompt)
        image_url = f"{IMAGE_API_BASE_URL}{encoded_prompt}"
        
        # If direct=true, redirect to image
        if direct:
            return redirect(image_url)
        
        return jsonify({
            'success': True,
            'imageUrl': image_url,
            'prompt': prompt,
            'direct_url': image_url,
            'open_link': f'/image?prompt={encoded_prompt}&direct=true'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/open', methods=['GET'])
def open_link():
    """
    Universal opener - detects content type and opens appropriately
    URL format: http://localhost:5000/open?url={encoded_url}
    """
    target_url = request.args.get('url', '').strip()
    
    if not target_url:
        return jsonify({
            'success': False,
            'error': 'Missing url parameter'
        }), 400
    
    try:
        # Decode if double-encoded
        decoded = urllib.parse.unquote(target_url)
        if decoded != target_url:
            target_url = decoded
        
        # Validate URL
        if not target_url.startswith(('http://', 'https://')):
            target_url = 'https://' + target_url
        
        # Redirect to the URL
        return redirect(target_url)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/models', methods=['GET'])
def get_models():
    """Get available models"""
    models = [
        {'id': '2.0 Pro', 'name': '2.0 Pro', 'description': 'Fastest response'},
        {'id': '2.0 Mini', 'name': '2.0 Mini', 'description': 'Logical response'},
        {'id': '1.75 oD', 'name': '1.75 oD', 'description': 'More creative'},
        {'id': '1.5 mini', 'name': '1.5 mini', 'description': 'Older model'},
        {'id': 'Imagine Mini', 'name': 'Imagine Mini', 'description': 'Basic image model'}
    ]
    
    return jsonify({
        'success': True,
        'models': models
    })

@app.route('/config', methods=['GET'])
def get_config():
    """Get API configuration"""
    return jsonify({
        'success': True,
        'endpoints': {
            'chat': '/chat?prompt={question}',
            'chat_direct_image': '/chat?prompt={question}&direct_image=true',
            'image': '/image?prompt={description}',
            'image_direct': '/image?prompt={description}&direct=true',
            'image_ai': '/image/direct?prompt={description}',
            'open': '/open?url={encoded_url}',
            'models': '/models'
        },
        'ai_name': DEFAULT_AI_NAME,
        'version': '1.1.0'
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'Diablo.GPT API',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API info"""
    return jsonify({
        'name': 'Diablo.GPT API',
        'version': '1.1.0',
        'features': [
            'Text chat with context',
            'Image generation',
            'Direct image links',
            'Automatic URL detection'
        ],
        'endpoints': {
            'chat': 'GET /chat?prompt={question}&model={model}&history={json}&direct_image={bool}',
            'image_direct': 'GET /image/direct?prompt={description}',
            'image': 'GET /image?prompt={description}&direct={bool}',
            'open': 'GET /open?url={encoded_url}',
            'models': 'GET /models',
            'config': 'GET /config'
        },
        'examples': [
            'http://localhost:5000/chat?prompt=Hello',
            'http://localhost:5000/image/direct?prompt=a beautiful sunset',
            'http://localhost:5000/image?prompt=cat&direct=true',
            'http://localhost:5000/open?url=https://google.com'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)