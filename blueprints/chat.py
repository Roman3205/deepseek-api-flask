from quart import Blueprint, make_response, request, jsonify, Response, current_app
from openai import AsyncOpenAI
from os import getenv
from dotenv import load_dotenv
import uuid
import aiohttp
import certifi
import ssl
import json

load_dotenv()

open_weather_api_key = getenv('OPENWEATHER_API_KEY')

openai = AsyncOpenAI(base_url="https://api.deepseek.com", api_key=getenv('DEEPSEEK_API_KEY'))

chat_bp = Blueprint('chat', __name__)

@chat_bp.before_app_serving
async def startup():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    connector = aiohttp.TCPConnector(ssl=ssl_context)

    current_app.aiohttp_session = aiohttp.ClientSession(connector=connector)

@chat_bp.after_app_serving
async def shutdown():
    if hasattr(current_app, 'aiohttp_session'):
        await current_app.aiohttp_session.close()

sessions = {}


async def get_weather(location: str) -> str:
    if not location:
        raise ValueError("Location is required")

    params = {
        "q": location,
        "appid": open_weather_api_key,
        "units": "metric",
        "lang": "en"
    }

    try:
        session = current_app.aiohttp_session

        async with session.get('https://api.openweathermap.org/data/2.5/weather', params=params) as response:
            if response.status == 200:
                data = await response.json()
                temp = data['main']['temp']
                return f"{temp}°C."
            elif response.status == 404:
                return f"City '{location}' not found."
            else:
                return f"Failed to get weather data. Status: {response.status}"
    except Exception as e:
        return f"An error occurred while fetching weather data: {str(e)}"


@chat_bp.route('/ask-stream', methods=['POST'])
async def chat_stream():
    body = await request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')

    async def generate():
        full_response = ""
        try:
            stream = await openai.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message}
                ],
                temperature=1.3,
                max_tokens=4096,
                stream=True,
            )

            async for chunk in stream:
                if content := chunk.choices[0].delta.reasoning_content:
                    full_response += content
                    yield f"data: {json.dumps({'type': "reasoning", 'content': content})}\n\n"
                elif content := chunk.choices[0].delta.content:
                    full_response += content
                    yield f"data: {json.dumps({'type': "response", 'content': content})}\n\n"

        except Exception as e:
            yield f"error: {e}\n\n"

    response = Response(generate(), mimetype='text/event-stream')

    return response

@chat_bp.route('/ask', methods=['POST'])
async def ask_chat():
    body = await request.get_json()

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
        chat_response = await openai.chat.completions.create(
            model="deepseek-chat",
            messages=sessions[session_id],
            temperature=1.3,
            max_tokens=2048,
        )

        if len(sessions[session_id]) < 22: # 1 system message + 10 user + 10 assistant messages
            sessions[session_id].append({"role": "assistant", "content": chat_response.choices[0].message.content}) 

        response = await make_response(jsonify({"response": chat_response.choices[0].message.content}))

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
async def gen_code():
    body = await request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')

    try:
        code_response = await openai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates code. You must answer only in markdown code snippets."},
                {"role": "user", "content": message}
            ],
            temperature=0.0,
            max_tokens=2048
        )

        return code_response.choices[0].message.content

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@chat_bp.route('/json-answer', methods=['POST'])
async def json_answer():
    body = await request.get_json()

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
        json_response = await openai.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            temperature=1.3,
            response_format={"type": "json_object"},
            max_tokens=2048
        )

        return json_response.choices[0].message.content

    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/balance/get', methods=['GET'])
async def get_balance():
    try:
        session = current_app.aiohttp_session

        async with session.get(
                'https://api.deepseek.com/user/balance',
                headers={'Authorization': f'Bearer {getenv("DEEPSEEK_API_KEY")}'}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    details = await response.text()
                    return jsonify({"error": "Failed to fetch balance", "details": details}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@chat_bp.route('/models/get', methods=['GET'])
async def get_models():
    try:
        session = current_app.aiohttp_session
        
        async with session.get(
                'https://api.deepseek.com/models',
                headers={'Authorization': f'Bearer {getenv("DEEPSEEK_API_KEY")}'}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    models = await openai.models.list()
                    return models.model_dump_json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/weather', methods=['GET'])
async def weather_chat():
    body = await request.get_json()

    if not body or 'message' not in body:
        return jsonify({"error": "No message provided"}), 400
    
    message = body.get('message')

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather of a location, the user should supply a location first.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city only, e.g. San Francisco, London, Moscow, etc.",
                        }
                    },
                    "required": ["location"]
                },
            }
        },
    ]

    messages = [{"role": "user", "content": message}]

    try:
        response = await openai.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            tools=tools,
            temperature=1.3,
            max_tokens=2048,
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            messages.append(response_message)

            args = json.loads(tool_call.function.arguments)
            location = args.get('location')

            print(location)
            weather_result = await get_weather(location)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": weather_result
            })

            final_response = await openai.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=tools
            )
            
            return final_response.choices[0].message.content
        
        else:
            return message.content

    except Exception as e:
        return jsonify({"error": str(e)}), 500