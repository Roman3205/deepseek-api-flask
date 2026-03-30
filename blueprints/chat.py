from flask import Blueprint, make_response, request, jsonify
from openai import OpenAI
from os import getenv
from dotenv import load_dotenv
import uuid
import requests

load_dotenv()

openai = OpenAI(base_url="https://api.deepseek.com", api_key=getenv('DEEPSEEK_API_KEY'))

chat_bp = Blueprint('chat', __name__)

sessions = {}

@chat_bp.route('/ask', methods=['POST'])
def ask_chat():
    body = request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')
    new_chat = body.get('new_chat', False)

    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())

    if new_chat or session_id not in sessions:
        sessions[session_id] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]

    if len(sessions[session_id]) < 22:  # 1 system message + 10 user + 10 assistant messages
        sessions[session_id].append({"role": "user", "content": message})

    try:
        chat_response = openai.chat.completions.create(
            model="deepseek-chat",
            messages=sessions[session_id],
            temperature=1.3,
            max_tokens=1024
        )

        if len(sessions[session_id]) < 22: # 1 system message + 10 user + 10 assistant messages
            sessions[session_id].append({"role": "assistant", "content": chat_response.choices[0].message.content}) 

        response = make_response(jsonify({"response": chat_response.choices[0].message.content}))
        
        response.set_cookie(
            'session_id', 
            session_id, 
            httponly=True, 
            samesite='Lax', 
            max_age=60*60*24*30
        )

        return response
    
    except Exception as e:
        if session_id in sessions and sessions[session_id]:
            sessions[session_id].pop()

        return jsonify({"error": str(e)}), 500
    
@chat_bp.route('/code', methods=['POST'])
def gen_code():
    body = request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')

    try:
        code_response = openai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates code. You must answer only in markdown code snippets."},
                {"role": "user", "content": message}
            ],
            temperature=1.3,
            max_tokens=2048
        )

        return code_response.choices[0].message.content

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@chat_bp.route('/json-answer', methods=['POST'])
def json_answer():
    body = request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')

    system_message = """
        The user will provide some exam text. Please parse the "question" and "answer" and output them in JSON format. 

        EXAMPLE INPUT: 
        Which is the highest mountain in the world?

        EXAMPLE JSON OUTPUT:
        {
            "question": "Which is the highest mountain in the world?",
            "hints": ["height is more than 8000 meters", "located in the Himalayas"],
            "answer": "Mount Everest"
        }
    """

    try:
        json_response = openai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            temperature=1.3,
            response_format={"type": "json_object"},
            max_tokens=1024
        )

        return json_response.choices[0].message.content

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/balance/get', methods=['GET'])
def get_balance():
    try:
        response = requests.get(
            'https://api.deepseek.com/user/balance',
            headers={'Authorization': f'Bearer {getenv("DEEPSEEK_API_KEY")}'}
        )

        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({"error": "Failed to fetch balance", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@chat_bp.route('/models/get', methods=['GET'])
def get_models():
    try:
        response = requests.get(
            'https://api.deepseek.com/models',
            headers={'Authorization': f'Bearer {getenv("DEEPSEEK_API_KEY")}'}
        )

        if response.status_code == 200:
            return response.json()
        else:
            return openai.models.list().model_dump_json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
