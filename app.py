import uuid
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import the refactored game logic
from ksh_game import GameState, PIECE_FEN_MAP

app = Flask(__name__)
# In a real app, use a more secure, environment-variable-based secret key
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Dictionary to store game sessions
# game_sessions = { 'game_id': {'game': GameState(), 'players': [sid1, sid2]} }
game_sessions = {}

def get_game_state_for_frontend(game_state):
    """Prepares a JSON-serializable version of the game state for the client."""
    board_for_frontend = []
    for r_idx, row in enumerate(game_state.board_state):
        row_for_frontend = []
        for c_idx, piece in enumerate(row):
            if piece:
                is_deactivated = False
                if piece.general_group and piece.general_group != '중앙' and piece.name != 'Su':
                    group_key = f"{piece.team}_{piece.general_group}"
                    if game_state.deactivated_groups.get(group_key, False):
                        is_deactivated = True

                row_for_frontend.append({
                    "team": piece.team,
                    "name": piece.name,
                    "korean_name": piece.korean_name,
                    "position": piece.position,
                    "is_deactivated": is_deactivated,
                })
            else:
                row_for_frontend.append(None)
        board_for_frontend.append(row_for_frontend)

    return {
        "board_state": board_for_frontend,
        "current_turn": game_state.current_turn,
        "game_over": game_state.game_over,
        "winner": game_state.winner,
        "valid_moves": game_state.valid_moves,
        "deactivated_groups": game_state.deactivated_groups,
        "in_check_team": game_state.in_check_team,
        "checked_su_pos": game_state.checked_su_pos,
        "fen": game_state.generate_fen()
    }


@app.route('/')
def index():
    return "KSH Game Backend is running. Active sessions: " + str(len(game_sessions))

@socketio.on('connect')
def on_connect():
    print(f'Client connected: {request.sid}')
    emit('my response', {'data': 'Connected to KSH backend'})

@socketio.on('disconnect')
def on_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Find which game the disconnected player was in and notify the other player
    game_id_to_remove = None
    for game_id, session in game_sessions.items():
        if request.sid in session['players']:
            session['players'].remove(request.sid)
            if len(session['players']) == 0:
                game_id_to_remove = game_id
            else:
                # Notify remaining player
                emit('player_disconnected', {'message': 'The other player has disconnected.'}, room=session['players'][0])
            break
    if game_id_to_remove:
        del game_sessions[game_id_to_remove]
        print(f"Removed empty game session: {game_id_to_remove}")


@socketio.on('create_game')
def on_create_game():
    """Creates a new game session."""
    player_sid = request.sid
    game_id = str(uuid.uuid4().hex)[:6] # Short, unique ID
    game = GameState()
    
    game_sessions[game_id] = {
        'game': game,
        'players': [player_sid]
    }
    
    join_room(game_id)
    print(f"Player {player_sid} created and joined game {game_id}")
    
    emit('game_created', {'game_id': game_id})
    emit('update_state', get_game_state_for_frontend(game))


@socketio.on('join_game')
def on_join_game(data):
    """Allows a second player to join a game."""
    player_sid = request.sid
    game_id = data.get('game_id')
    
    if game_id not in game_sessions:
        emit('error', {'message': 'Game not found.'})
        return
        
    session = game_sessions[game_id]
    
    if len(session['players']) >= 2:
        emit('error', {'message': 'This game is already full.'})
        return
    
    if player_sid in session['players']:
        emit('error', {'message': 'You are already in this game.'})
        return

    session['players'].append(player_sid)
    join_room(game_id)
    
    print(f"Player {player_sid} joined game {game_id}")
    
    # Notify both players that the game is starting
    emit('game_started', {'message': 'Both players are connected. The game begins!'}, room=game_id)
    
    # Send the current state to everyone in the room
    emit('update_state', get_game_state_for_frontend(session['game']), room=game_id)


@socketio.on('make_move')
def on_make_move(data):
    """Handles a player's move."""
    player_sid = request.sid
    game_id = data.get('game_id')
    from_pos = tuple(data.get('from_pos'))
    to_pos = tuple(data.get('to_pos'))

    if game_id not in game_sessions:
        emit('error', {'message': 'Game not found.'})
        return
        
    session = game_sessions[game_id]
    game = session['game']
    
    # Determine player team by their order in the list ('초' is first, '한' is second)
    try:
        player_index = session['players'].index(player_sid)
        player_team = '초' if player_index == 0 else '한'
    except ValueError:
        emit('error', {'message': 'You are not a player in this game.'})
        return

    if game.current_turn != player_team:
        emit('error', {'message': 'Not your turn.'})
        return
        
    if game.game_over:
        emit('error', {'message': 'The game is already over.'})
        return

    # --- Perform the move using the game logic ---
    # 1. Select the piece
    game.select_piece(from_pos)
    
    # 2. Check if the destination is a valid move for the selected piece
    if to_pos in game.valid_moves:
        # If valid, the second select_piece call will trigger move_piece internally
        game.select_piece(to_pos)
        
        # Broadcast the new state to all players in the game room
        emit('update_state', get_game_state_for_frontend(game), room=game_id)
        
        if game.game_over:
            emit('game_over', {'winner': game.winner}, room=game.id)
    else:
        # If the move is invalid, just send an error to the player who tried
        game.selected_piece = None
        game.valid_moves = []
        emit('error', {'message': 'Invalid move.'})
        # Also send the current state back to them to reset their selection
        emit('update_state', get_game_state_for_frontend(game))


if __name__ == '__main__':
    print("Starting KSH Game Backend Server...")
    socketio.run(app, host='0.0.0.0', port=5000)