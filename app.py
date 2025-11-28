import uuid
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

# Import the refactored game logic
from ksh_game import GameState

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key_that_should_be_changed'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

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
                    "team": piece.team, "name": piece.name,
                    "korean_name": piece.korean_name, "position": piece.position,
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
        "selected_pos": game_state.selected_pos, # Add selected_pos to payload
        "fen": game_state.generate_fen()
    }

def get_player_team(sid, session):
    for team, player_sid in session['players'].items():
        if player_sid == sid:
            return team
    return None

@app.route('/')
def index():
    return "KSH Game Backend is running. Active sessions: " + str(len(game_sessions))

@socketio.on('connect')
def on_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    print(f'Client disconnected: {request.sid}')
    game_id_to_cleanup = None
    for game_id, session in game_sessions.items():
        disconnected_team = get_player_team(request.sid, session)
        if disconnected_team:
            session['players'][disconnected_team] = None
            other_team = '한' if disconnected_team == '초' else '초'
            remaining_player_sid = session['players'].get(other_team)
            if remaining_player_sid:
                emit('player_disconnected', {'message': '상대방의 연결이 끊어졌습니다.'}, room=remaining_player_sid)
            else:
                game_id_to_cleanup = game_id
            break
    if game_id_to_cleanup:
        del game_sessions[game_id_to_cleanup]
        print(f"Removed empty game session: {game_id_to_cleanup}")

@socketio.on('create_game')
def on_create_game():
    player_sid = request.sid
    game_id = str(uuid.uuid4().hex)[:6]
    game = GameState()
    game_sessions[game_id] = {
        'game': game,
        'players': {'초': player_sid, '한': None}
    }
    join_room(game_id)
    print(f"Player {player_sid} created game {game_id} as team '초'")
    emit('game_created', {'game_id': game_id})
    emit('update_state', get_game_state_for_frontend(game))

@socketio.on('join_game')
def on_join_game(data):
    player_sid = request.sid
    game_id = data.get('game_id')
    if game_id not in game_sessions:
        emit('error', {'message': '해당 ID의 게임을 찾을 수 없습니다.'})
        return
    session = game_sessions[game_id]
    if session['players']['한'] is not None:
        emit('error', {'message': '이 게임은 이미 가득 찼습니다.'})
        return
    if session['players']['초'] == player_sid:
        emit('error', {'message': '자기 자신과는 플레이할 수 없습니다.'})
        return
    session['players']['한'] = player_sid
    join_room(game_id)
    print(f"Player {player_sid} joined game {game_id} as team '한'")
    emit('game_started', {'message': '양쪽 플레이어가 모두 연결되었습니다. 게임을 시작합니다!'}, room=game_id)
    emit('update_state', get_game_state_for_frontend(session['game']), room=game_id)

@socketio.on('handle_click')
def on_handle_click(data):
    """Handles any click on the board from a player."""
    player_sid = request.sid
    game_id = data.get('game_id')
    
    if game_id not in game_sessions: return
    session = game_sessions[game_id]
    game = session['game']

    if not all(session['players'].values()):
        emit('error', {'message': '상대방이 아직 참가하지 않았습니다.'})
        return

    player_team = get_player_team(player_sid, session)
    if not player_team:
        emit('error', {'message': '게임의 플레이어가 아닙니다.'})
        return

    if game.current_turn != player_team:
        # Allow deselecting even if it's not your turn
        if game.selected_pos:
             game.handle_click(data.get('pos'))
             emit('update_state', get_game_state_for_frontend(game), room=game_id)
        else:
             emit('error', {'message': '자신의 턴이 아닙니다.'})
        return
        
    if game.game_over:
        emit('error', {'message': '게임이 이미 종료되었습니다.'})
        return

    # Process the click using the unified game logic
    pos = tuple(data.get('pos'))
    game.handle_click(pos)

    # Broadcast the new state to all players
    emit('update_state', get_game_state_for_frontend(game), room=game_id)
    
    if game.game_over:
        emit('game_over', {'winner': game.winner}, room=game_id)

if __name__ == '__main__':
    print("Starting KSH Game Backend Server...")
    socketio.run(app, host='0.0.0.0', port=5000)