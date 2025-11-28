from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!' # Consider using a stronger, randomly generated key in production
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    return "KSH Game Backend is running. Connect via WebSocket."

@socketio.on('connect')
def test_connect():
    print('Client connected')
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(msg):
    print('Message: ' + msg)
    emit('my response', {'data': msg}, broadcast=True) # Echo message to all connected clients

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
