from quart import Quart, make_response, Blueprint
from blueprints.chat import chat_bp

app = Quart(__name__)

app.register_blueprint(chat_bp, url_prefix='/chat')

@app.route('/ping')
async def test():
    response = make_response('pong')
    response.headers['Content-Type'] = 'text/plain'
    response.status_code = 200
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)