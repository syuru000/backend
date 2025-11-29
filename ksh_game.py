import math

# --- Constants ---
BOARD_WIDTH_CELLS = 15
BOARD_HEIGHT_CELLS = 14
FEN = "3M3B3M3/RAE1REA1AER1EAR/1Q1L3K3L1Q1/N1C2NC1CN2C1N/3U3F3U3/PPP1GGG1PPP1GGG/15/15/ggg1ppp1ggg1ppp/3u3f3u/n1c2nc1cn2c1n/1q1l3k3l1q1/rae1rea1aer1ear/3m3b3m3"

# --- Piece Classes (from pieces.py) ---

class Piece:
    """모든 기물의 부모 클래스"""
    def __init__(self, team, position):
        self.team = team
        self.position = position # (y, x) 튜플
        self.name = self.__class__.__name__
        self.has_moved = False # 기물이 한 번이라도 움직였는지 여부
        self.forward_dir = -1 if team == '초' else 1
        self.general_group = '중앙'
        self.captured_general_group = None

    def get_valid_moves(self, board_state, game_state):
        raise NotImplementedError

    def _is_valid_target(self, pos, board_state, game_state):
        y, x = pos
        if not (0 <= y < game_state.BOARD_HEIGHT_CELLS and 0 <= x < game_state.BOARD_WIDTH_CELLS):
            return False
        target_piece = board_state[y][x]
        if target_piece and target_piece.team == self.team:
            return False
        return True

class Su(Piece):
    korean_name = '수'
    def _get_base_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0: continue
                ny, nx = y + dy, x + dx
                move = (ny, nx)
                if not (0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS): continue
                if not game_state.is_in_palace(move, self.team): continue
                is_diagonal_move = abs(dy) == 1 and abs(dx) == 1
                if is_diagonal_move and not game_state.is_valid_palace_diagonal_move(y, x, ny, nx, self.team): continue
                if self._is_valid_target(move, board_state, game_state):
                    moves.append(move)
        return moves

    def get_valid_moves(self, board_state, game_state):
        base_moves = self._get_base_moves(board_state, game_state)
        safe_moves = []
        opponent_team = '한' if self.team == '초' else '초'
        for move in base_moves:
            if not game_state.is_square_under_attack(move, opponent_team, board_state):
                safe_moves.append(move)
        return safe_moves

class Jang(Piece):
    korean_name = '장'
    def get_valid_moves(self, board_state, game_state):
        return Su.get_valid_moves(self, board_state, game_state)
    def _get_base_moves(self, board_state, game_state):
        return Su._get_base_moves(self, board_state, game_state)

class Cha(Piece):
    korean_name = '차'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            while 0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS:
                target = board_state[ny][nx]
                if target is None:
                    moves.append((ny, nx))
                else:
                    if target.team != self.team:
                        moves.append((ny, nx))
                    break
                ny += dy
                nx += dx
        
        palace_keys_to_check = ['초', '초_좌', '초_우','한', '한_좌', '한_우']
        for key in palace_keys_to_check:
            if not game_state.is_in_palace(self.position, self.team, check_palace_key=key): continue
            y1, x1, y2, x2 = game_state.palaces[key]
            cy, cx = (y1 + y2) // 2, (x1 + x2) // 2
            diagonal_paths = [[(y1, x1), (cy, cx), (y2, x2)], [(y1, x2), (cy, cx), (y2, x1)]]
            for path in diagonal_paths:
                if self.position in path:
                    current_idx = path.index(self.position)
                    for i in range(current_idx + 1, len(path)):
                        target_pos = path[i]
                        is_blocked = any(board_state[path[j][0]][path[j][1]] is not None for j in range(current_idx + 1, i))
                        if is_blocked: break
                        if self._is_valid_target(target_pos, board_state, game_state):
                            moves.append(target_pos)
                        if board_state[target_pos[0]][target_pos[1]] is not None: break
                    for i in range(current_idx - 1, -1, -1):
                        target_pos = path[i]
                        is_blocked = any(board_state[path[j][0]][path[j][1]] is not None for j in range(current_idx - 1, i, -1))
                        if is_blocked: break
                        if self._is_valid_target(target_pos, board_state, game_state):
                            moves.append(target_pos)
                        if board_state[target_pos[0]][target_pos[1]] is not None: break
        return moves

class Po(Piece):
    korean_name = '포'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dy, dx in directions:
            jumped = False
            ny, nx = y + dy, x + dx
            while 0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS:
                target = board_state[ny][nx]
                if not jumped:
                    if target is not None:
                        if target.name == 'Po': break
                        jumped = True
                else:
                    if target is None:
                        if self._is_valid_target((ny, nx), board_state, game_state): moves.append((ny, nx))
                    else:
                        if target.name != 'Po' and target.team != self.team:
                            if self._is_valid_target((ny, nx), board_state, game_state): moves.append((ny, nx))
                        break
                ny += dy
                nx += dx
        
        palace_keys_to_check = ['초', '초_좌', '초_우'] if self.team == '초' else ['한', '한_좌', '한_우']
        for key in palace_keys_to_check:
            if not game_state.is_in_palace(self.position, self.team, check_palace_key=key): continue
            y1, x1, y2, x2 = game_state.palaces[key]
            cy, cx = (y1 + y2) // 2, (x1 + x2) // 2
            is_corner = (self.position in [(y1, x1), (y1, x2), (y2, x1), (y2, x2)])
            if is_corner:
                jump_over_piece = board_state[cy][cx]
                if jump_over_piece and jump_over_piece.name != 'Po':
                    ty, tx = 0, 0
                    if self.position == (y1, x1): ty, tx = y2, x2
                    elif self.position == (y1, x2): ty, tx = y2, x1
                    elif self.position == (y2, x1): ty, tx = y1, x2
                    elif self.position == (y2, x2): ty, tx = y1, x1
                    target_pos = (ty, tx)
                    target_piece = board_state[ty][tx]
                    if target_piece is None or (target_piece.team != self.team and target_piece.name != 'Po'):
                        if self._is_valid_target(target_pos, board_state, game_state): moves.append(target_pos)
        return moves

class Ma(Piece):
    korean_name = '마'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        potential_moves = [
            (y - 2, x - 1, y - 1, x), (y - 2, x + 1, y - 1, x),
            (y + 2, x - 1, y + 1, x), (y + 2, x + 1, y + 1, x),
            (y - 1, x - 2, y, x - 1), (y - 1, x + 2, y, x + 1),
            (y + 1, x - 2, y, x - 1), (y + 1, x + 2, y, x + 1),
        ]
        for dest_y, dest_x, myeok_y, myeok_x in potential_moves:
            destination = (dest_y, dest_x)
            if not (0 <= myeok_y < game_state.BOARD_HEIGHT_CELLS and 0 <= myeok_x < game_state.BOARD_WIDTH_CELLS): continue
            if board_state[myeok_y][myeok_x] is not None: continue
            if self._is_valid_target(destination, board_state, game_state):
                moves.append(destination)
        return moves

class Sang(Piece):
    korean_name = '상'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        potential_moves = [
            (y - 3, x - 2, y - 1, x, y - 2, x - 1), (y - 3, x + 2, y - 1, x, y - 2, x + 1),
            (y + 3, x - 2, y + 1, x, y + 2, x - 1), (y + 3, x + 2, y + 1, x, y + 2, x + 1),
            (y - 2, x - 3, y, x - 1, y - 1, x - 2), (y - 2, x + 3, y, x + 1, y - 1, x + 2),
            (y + 2, x - 3, y, x - 1, y + 1, x - 2), (y + 2, x + 3, y, x + 1, y + 1, x + 2),
        ]
        for dest_y, dest_x, my1, mx1, my2, mx2 in potential_moves:
            m1_valid = (0 <= my1 < 14 and 0 <= mx1 < 15)
            m2_valid = (0 <= my2 < 14 and 0 <= mx2 < 15)
            if not m1_valid or not m2_valid: continue
            m1_blocked = board_state[my1][mx1] is not None
            m2_blocked = board_state[my2][mx2] is not None
            if m1_blocked or m2_blocked: continue
            if self._is_valid_target((dest_y, dest_x), board_state, game_state):
                moves.append((dest_y, dest_x))
        return moves

class Sa(Piece):
    korean_name = '사'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0: continue
                ny, nx = y + dy, x + dx
                if not (0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS): continue
                if not game_state.is_in_palace((ny, nx), self.team): continue
                is_diagonal_move = abs(dy) == 1 and abs(dx) == 1
                if is_diagonal_move and not game_state.is_valid_palace_diagonal_move(y, x, ny, nx, self.team): continue
                if self._is_valid_target((ny, nx), board_state, game_state):
                    moves.append((ny, nx))
        return moves

class Bo(Piece):
    korean_name = '보'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        forward_y = y + self.forward_dir
        if self._is_valid_target((forward_y, x), board_state, game_state): moves.append((forward_y, x))
        if self._is_valid_target((y, x - 1), board_state, game_state): moves.append((y, x - 1))
        if self._is_valid_target((y, x + 1), board_state, game_state): moves.append((y, x + 1))
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dy == 0 and dx == 0: continue
                ny, nx = y + dy, x + dx
                if not (0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS): continue
                is_diagonal_move = abs(dy) == 1 and abs(dx) == 1
                if is_diagonal_move and not game_state.is_valid_palace_diagonal_move(y, x, ny, nx, '초' or '한'): continue
        return moves

class Gi(Piece):
    korean_name = '기'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        forward_y = y + self.forward_dir
        if self._is_valid_target((forward_y, x - 1), board_state, game_state): moves.append((forward_y, x - 1))
        if self._is_valid_target((forward_y, x + 1), board_state, game_state): moves.append((forward_y, x + 1))
        if self._is_valid_target((y, x - 1), board_state, game_state): moves.append((y, x - 1))
        if self._is_valid_target((y, x + 1), board_state, game_state): moves.append((y, x + 1))
        return moves

class Bok(Piece):
    korean_name = '복'
    def _get_attack_range(self, board_state):
        y, x = self.position
        attack_range = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dy, dx in directions:
            path1, path2 = (y + dy, x + dx), (y + dy*2, x + dx*2)
            path1_y, path1_x = path1
            path2_y, path2_x = path2
            if not (0 <= path1_y < 14 and 0 <= path1_x < 15 and 0 <= path2_y < 14 and 0 <= path2_x < 15): continue
            if board_state[path1_y][path1_x] is None and board_state[path2_y][path2_x] is None:
                targets = []
                if dy != 0: targets = [(path2_y + dy, path2_x - 1), (path2_y + dy, path2_x + 1)]
                else: targets = [(path2_y - 1, path2_x + dx), (path2_y + 1, path2_x + dx)]
                for ty, tx in targets:
                    if (0 <= ty < 14 and 0 <= tx < 15): attack_range.append((ty, tx))
        return attack_range

    def get_valid_moves(self, board_state, game_state):
        moves = []
        attack_range = self._get_attack_range(board_state)
        for pos in attack_range:
            target = board_state[pos[0]][pos[1]]
            if target and target.team != self.team:
                moves.append(pos)
        return moves

class Yu(Piece):
    korean_name = '유'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        potential_moves = [
            (y - 2, x - 2, y - 1, x - 1), (y - 2, x + 2, y - 1, x + 1),
            (y + 2, x - 2, y + 1, x - 1), (y + 2, x + 2, y + 1, x + 1),
        ]
        for dest_y, dest_x, my, mx in potential_moves:
            m_valid = (0 <= my < 14 and 0 <= mx < 15)
            if not m_valid or board_state[my][mx] is not None: continue
            if self._is_valid_target((dest_y, dest_x), board_state, game_state):
                moves.append((dest_y, dest_x))
        return moves

class Gi_L(Piece):
    korean_name = '기L'
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dy, dx in directions:
            for i in range(1, 3):
                ny, nx = y + dy * i, x + dx * i
                if not (0 <= ny < 14 and 0 <= nx < 15): break
                target = board_state[ny][nx]
                if target is None:
                    moves.append((ny, nx))
                else:
                    if target.team != self.team: moves.append((ny, nx))
                    break
        return moves

class Jeon(Piece):
    korean_name = '전'
    def _is_restricted_area(self, pos, game_state):
        if game_state.is_in_inner_area(pos, '초') or game_state.is_in_inner_area(pos, '한'): return True
        if game_state.is_in_palace(pos, '초', check_main_palace_only=True) or game_state.is_in_palace(pos, '한', check_main_palace_only=True): return True
        return False
    def get_valid_moves(self, board_state, game_state):
        moves = []
        y, x = self.position
        def can_capture_target(target_pos):
            target_piece = board_state[target_pos[0]][target_pos[1]]
            return not (target_piece and target_piece.name == 'Jeon')
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            while 0 <= ny < game_state.BOARD_HEIGHT_CELLS and 0 <= nx < game_state.BOARD_WIDTH_CELLS:
                potential_move = (ny, nx)
                if self._is_restricted_area(potential_move, game_state): break
                target_piece = board_state[ny][nx]
                if target_piece is None: moves.append(potential_move)
                else:
                    if target_piece.team != self.team and target_piece.name != 'Jeon': moves.append(potential_move)
                    break
                ny += dy
                nx += dx
        palace_keys_to_check = ['초_좌', '초_우', '한_좌', '한_우']
        for key in palace_keys_to_check:
            if not game_state.is_in_palace(self.position, self.team, check_palace_key=key): continue
            y1, x1, y2, x2 = game_state.palaces[key]
            cy, cx = (y1 + y2) // 2, (x1 + x2) // 2
            diagonal_paths = [[(y1, x1), (cy, cx), (y2, x2)], [(y1, x2), (cy, cx), (y2, x1)]]
            for path in diagonal_paths:
                if self.position not in path: continue
                current_idx = path.index(self.position)
                for i in range(current_idx + 1, len(path)):
                    target_pos = path[i]
                    if any(board_state[path[j][0]][path[j][1]] for j in range(current_idx + 1, i)): break
                    if self._is_valid_target(target_pos, board_state, game_state) and not self._is_restricted_area(target_pos, game_state) and can_capture_target(target_pos): moves.append(target_pos)
                    if board_state[target_pos[0]][target_pos[1]] is not None: break
                for i in range(current_idx - 1, -1, -1):
                    target_pos = path[i]
                    if any(board_state[path[j][0]][path[j][1]] for j in range(current_idx - 1, i, -1)): break
                    if self._is_valid_target(target_pos, board_state, game_state) and not self._is_restricted_area(target_pos, game_state) and can_capture_target(target_pos): moves.append(target_pos)
                    if board_state[target_pos[0]][target_pos[1]] is not None: break
        return moves

class Hu(Piece):
    korean_name = '후'
    def get_valid_moves(self, board_state, game_state):
        # 1. Get all potential moves as if it were a Cha.
        potential_moves = Cha.get_valid_moves(self, board_state, game_state)
        
        moves = []
        opponent_team = '한' if self.team == '초' else '초'

        # Hu cannot move if it starts in the "outer-outer" area.
        if game_state.is_in_outer_outer_area(self.position, self.team):
            return []

        # 2. Filter the potential moves based on Hu's specific restrictions.
        for move in potential_moves:
            # Restricted areas Hu cannot enter:
            # 1. Its own "outer-outer" area.
            is_outside_allowed_zone = game_state.is_in_outer_outer_area(move, self.team)
            # 2. The opponent's main palace.
            is_opponent_main_palace = game_state.is_in_palace(move, opponent_team, check_main_palace_only=True)
            # 3. The opponent's inner area.
            is_opponent_inner_area = game_state.is_in_inner_area(move, opponent_team)

            # If the move is not into any of the restricted zones, it's valid.
            if not (is_outside_allowed_zone or is_opponent_main_palace or is_opponent_inner_area):
                moves.append(move)
                
        return list(set(moves)) # Use set to remove any duplicate moves

PIECE_CLASS_MAP = {'K': Su, 'Q': Jang, 'R': Cha, 'C': Po, 'N': Ma, 'E': Sang, 'A': Sa, 'P': Bo, 'G': Gi, 'M': Bok, 'U': Yu, 'L': Gi_L, 'F': Jeon, 'B': Hu, 'k': Su, 'q': Jang, 'r': Cha, 'c': Po, 'n': Ma, 'e': Sang, 'a': Sa, 'p': Bo, 'g': Gi, 'm': Bok, 'u': Yu, 'l': Gi_L, 'f': Jeon, 'b': Hu}
PIECE_FEN_MAP = {'Su': 'k', 'Jang': 'q', 'Cha': 'r', 'Po': 'c', 'Ma': 'n', 'Sang': 'e', 'Sa': 'a', 'Bo': 'p', 'Gi': 'g', 'Bok': 'm', 'Yu': 'u', 'Gi_L': 'l', 'Jeon': 'f', 'Hu': 'b'}

# --- GameState Class (from main.py, refactored) ---

class GameState:
    def __init__(self, initial_fen=FEN):
        self.BOARD_WIDTH_CELLS = BOARD_WIDTH_CELLS
        self.BOARD_HEIGHT_CELLS = BOARD_HEIGHT_CELLS
        self._initialize_board_constants()
        self._initialize_game_variables(initial_fen)

    def _initialize_board_constants(self):
        self.palaces = {
            '한': (1, 6, 3, 8), '초': (10, 6, 12, 8),
            '한_좌': (1, 0, 3, 2), '한_우': (1, 12, 3, 14),
            '초_좌': (10, 0, 12, 2), '초_우': (10, 12, 12, 14),
        }
        self.palace_diagonal_paths = {
            '한': [((1,6),(2,7)),((2,7),(3,8)),((2,7),(1,6)),((3,8),(2,7)),((1,8),(2,7)),((2,7),(3,6)),((2,7),(1,8)),((3,6),(2,7))],
            '초': [((10,6),(11,7)),((11,7),(12,8)),((11,7),(10,6)),((12,8),(11,7)),((10,8),(11,7)),((11,7),(12,6)),((11,7),(10,8)),((12,6),(11,7))],
            '한_좌': [((1,0),(2,1)),((2,1),(3,2)),((2,1),(1,0)),((3,2),(2,1)),((1,2),(2,1)),((2,1),(3,0)),((2,1),(1,2)),((3,0),(2,1))],
            '한_우': [((1,12),(2,13)),((2,13),(3,14)),((2,13),(1,12)),((3,14),(2,13)),((1,14),(2,13)),((2,13),(3,12)),((2,13),(1,14)),((3,12),(2,13))],
            '초_좌': [((10,0),(11,1)),((11,1),(12,2)),((11,1),(10,0)),((12,2),(11,1)),((10,2),(11,1)),((11,1),(12,0)),((11,1),(10,2)),((12,0),(11,1))],
            '초_우': [((10,12),(11,13)),((11,13),(12,14)),((11,13),(10,12)),((12,14),(11,13)),((10,14),(11,13)),((11,13),(12,12)),((11,13),(10,14)),((12,12),(11,13))],
        }
        self.inner_area = {'한': (1, 4, 3, 10), '초': (10, 4, 12, 10)}
        self.outer_area_bounds = {'한': (0, 3, 4, 11), '초': (9, 3, 13, 11)}

    def _initialize_game_variables(self, fen):
        self.board_state = self.parse_fen(fen)
        self.current_turn = '초'
        self.selected_pos = None # Replaces selected_piece
        self.valid_moves = []
        self.game_over = False
        self.winner = None
        self.deactivated_groups = {'초_좌': False, '초_우': False, '한_좌': False, '한_우': False}
        self.move_history = []
        self.in_check_team = None
        self.checked_su_pos = None

    def reset(self):
        self._initialize_game_variables(FEN)

    def parse_fen(self, fen_string):
        board = [[None for _ in range(self.BOARD_WIDTH_CELLS)] for _ in range(self.BOARD_HEIGHT_CELLS)]
        parts = fen_string.split('|')
        piece_fen = parts[0]
        moved_fen = parts[1] if len(parts) > 1 else None
        group_fen = parts[2] if len(parts) > 2 else None
        rows = piece_fen.split('/')
        for y, row_str in enumerate(rows):
            if y >= self.BOARD_HEIGHT_CELLS: continue
            x = 0
            i = 0
            while i < len(row_str):
                if x >= self.BOARD_WIDTH_CELLS: break
                char = row_str[i]
                if char.isdigit():
                    num_str = ""
                    j = i
                    while j < len(row_str) and row_str[j].isdigit():
                        num_str += row_str[j]
                        j += 1
                    x += int(num_str)
                    i = j
                else:
                    team = '한' if char.isupper() else '초'
                    piece_class = PIECE_CLASS_MAP.get(char.lower())
                    if piece_class:
                        piece = piece_class(team, (y, x))
                        if not group_fen:
                            if x < 4: piece.general_group = '좌'
                            elif x > 10: piece.general_group = '우'
                            else: piece.general_group = '중앙'
                        board[y][x] = piece
                    x += 1
                    i += 1
        if moved_fen:
            moved_rows = moved_fen.split('/')
            for y, row_str in enumerate(moved_rows):
                if y >= self.BOARD_HEIGHT_CELLS: continue
                x = 0
                i = 0
                while i < len(row_str):
                    if x >= self.BOARD_WIDTH_CELLS: break
                    char = row_str[i]
                    if char.isdigit():
                        num_str = ""
                        j = i
                        while j < len(row_str) and row_str[j].isdigit():
                            num_str += row_str[j]
                            j += 1
                        x += int(num_str)
                        i = j
                    else:
                        if board[y][x]: board[y][x].has_moved = True if char == 'm' else False
                        x += 1
                        i += 1
        if group_fen:
            group_rows = group_fen.split('/')
            for y, row_str in enumerate(group_rows):
                if y >= self.BOARD_HEIGHT_CELLS: continue
                x = 0
                i = 0
                while i < len(row_str):
                    if x >= self.BOARD_WIDTH_CELLS: break
                    char = row_str[i]
                    if char.isdigit():
                        num_str = ""
                        j = i
                        while j < len(row_str) and row_str[j].isdigit():
                            num_str += row_str[j]
                            j += 1
                        x += int(num_str)
                        i = j
                    else:
                        if board[y][x]:
                            if char == 'L': board[y][x].general_group = '좌'
                            elif char == 'R': board[y][x].general_group = '우'
                            elif char == 'C': board[y][x].general_group = '중앙'
                        x += 1
                        i += 1
        return board
        
    def generate_fen(self):
        piece_rows, moved_rows, group_rows = [], [], []
        for r in range(self.BOARD_HEIGHT_CELLS):
            empty_piece, empty_moved, empty_group = 0, 0, 0
            row_piece, row_moved, row_group = "", "", ""
            for c in range(self.BOARD_WIDTH_CELLS):
                piece = self.board_state[r][c]
                if piece is None:
                    empty_piece += 1
                    empty_moved += 1
                    empty_group += 1
                else:
                    if empty_piece > 0: row_piece += str(empty_piece); empty_piece = 0
                    fen_char = PIECE_FEN_MAP.get(piece.name)
                    row_piece += fen_char.upper() if piece.team == '한' else fen_char.lower()
                    if empty_moved > 0: row_moved += str(empty_moved); empty_moved = 0
                    row_moved += 'm' if piece.has_moved else '-'
                    if empty_group > 0: row_group += str(empty_group); empty_group = 0
                    if piece.general_group == '좌': row_group += 'L'
                    elif piece.general_group == '우': row_group += 'R'
                    else: row_group += 'C'
            if empty_piece > 0: row_piece += str(empty_piece)
            if empty_moved > 0: row_moved += str(empty_moved)
            if empty_group > 0: row_group += str(empty_group)
            piece_rows.append(row_piece)
            moved_rows.append(row_moved)
            group_rows.append(row_group)
        return f"{'/'.join(piece_rows)}|{'/'.join(moved_rows)}|{'/'.join(group_rows)}"

    def handle_click(self, pos):
        """A single method to handle any click, either selecting or moving."""
        if self.game_over: return
        y, x = pos
        
        # If a piece is selected and the new pos is a valid move, then move the piece
        if self.selected_pos and (y, x) in self.valid_moves:
            self.move_piece(self.selected_pos, (y, x))
            return

        target_piece = self.board_state[y][x]

        # Deselect if clicking the same piece or an invalid square
        if (self.selected_pos == (y,x)) or not target_piece or (target_piece.team != self.current_turn):
            self.selected_pos = None
            self.valid_moves = []
            return

        # If clicking a valid piece of the current turn
        group_key = f"{target_piece.team}_{target_piece.general_group}"
        if target_piece.general_group != '중앙' and target_piece.name != 'Su' and self.deactivated_groups.get(group_key, False):
            self.selected_pos = None
            self.valid_moves = []
            return

        self.selected_pos = (y,x)
        piece_to_check = self.board_state[y][x]
        
        potential_moves = piece_to_check.get_valid_moves(self.board_state, self)
        
        truly_valid_moves = []
        for move in potential_moves:
            import copy
            temp_board_state = copy.deepcopy(self.board_state)
            
            from_pos_temp = self.selected_pos
            temp_board_state[move[0]][move[1]] = temp_board_state[from_pos_temp[0]][from_pos_temp[1]]
            temp_board_state[from_pos_temp[0]][from_pos_temp[1]] = None

            in_check, _ = self.is_su_in_check(self.current_turn, temp_board_state)
            if not in_check:
                truly_valid_moves.append(move)
        
        self.valid_moves = truly_valid_moves

    def is_in_inner_area(self, pos, team):
        y, x = pos
        y1, x1, y2, x2 = self.inner_area[team]
        return y1 <= y <= y2 and x1 <= x <= x2

    def is_in_outer_area(self, pos, team):
        y, x = pos
        if not (0 <= y < self.BOARD_HEIGHT_CELLS and 0 <= x < self.BOARD_WIDTH_CELLS): return False
        y1_outer, x1_outer, y2_outer, x2_outer = self.outer_area_bounds[team]
        if not (y1_outer <= y <= y2_outer and x1_outer <= x <= x2_outer): return False
        return not self.is_in_inner_area(pos, team)

    def is_in_outer_outer_area(self, pos, team):
        y, x = pos
        if not (0 <= y < self.BOARD_HEIGHT_CELLS and 0 <= x < self.BOARD_WIDTH_CELLS): return False
        if not self.is_in_inner_area(pos, team) and not self.is_in_outer_area(pos, team):
            if self.is_in_palace(pos, team, check_main_palace_only=True): return False
            return True
        return False

    def is_in_palace(self, pos, team, check_main_palace_only=False, check_palace_key=None):
        y, x = pos
        palace_keys_to_check = [check_palace_key] if check_palace_key else []
        if not palace_keys_to_check:
            palace_keys_to_check.append(team)
            if not check_main_palace_only:
                palace_keys_to_check.extend([f"{team}_좌", f"{team}_우"])
        
        # A bit of a hack, but Cha and Hu can move along any palace lines
        if self.selected_pos and not check_main_palace_only:
             piece = self.board_state[self.selected_pos[0]][self.selected_pos[1]]
             if piece and piece.name in ['Cha', 'Hu']:
                 palace_keys_to_check.extend(['초', '한', '초_좌', '초_우', '한_좌', '한_우'])
                 palace_keys_to_check = list(set(palace_keys_to_check))


        for key in palace_keys_to_check:
            if key not in self.palaces: continue
            y1, x1, y2, x2 = self.palaces[key]
            if y1 <= y <= y2 and x1 <= x <= x2: return True
        return False

    def is_valid_palace_diagonal_move(self, r1, c1, r2, c2, team):
        current_pos, new_pos = (r1, c1), (r2, c2)
        
        all_palace_keys = ['초', '한', '초_좌', '초_우', '한_좌', '한_우']
        
        for key in all_palace_keys:
            # Check if both current_pos and new_pos are in THIS specific palace
            y1, x1, y2, x2 = self.palaces[key]
            current_in = y1 <= current_pos[0] <= y2 and x1 <= current_pos[1] <= x2
            new_in = y1 <= new_pos[0] <= y2 and x1 <= new_pos[1] <= x2

            if not (current_in and new_in):
                continue 

            valid_segments = self.palace_diagonal_paths[key]
            if (current_pos, new_pos) in valid_segments: return True
        return False

    def is_square_under_attack(self, square, attacking_team, board_state):
        for r in range(self.BOARD_HEIGHT_CELLS):
            for c in range(self.BOARD_WIDTH_CELLS):
                piece = board_state[r][c]
                if piece and piece.team == attacking_team:
                    # Temporarily set selected_pos for context-dependent moves (like Cha in palace)
                    original_selected_pos = self.selected_pos
                    self.selected_pos = (r, c)
                    
                    attack_moves = []
                    if piece.name in ['Su', 'Jang']: attack_moves = piece._get_base_moves(board_state, self)
                    elif piece.name == 'Bok': attack_moves = piece._get_attack_range(board_state)
                    else: attack_moves = piece.get_valid_moves(board_state, self)
                    
                    self.selected_pos = original_selected_pos # Restore
                    
                    if square in attack_moves: return True
        return False

    def find_su_position(self, team, board_state):
        for r in range(self.BOARD_HEIGHT_CELLS):
            for c in range(self.BOARD_WIDTH_CELLS):
                piece = board_state[r][c]
                if piece and piece.name == 'Su' and piece.team == team: return (r, c)
        return None

    def is_su_in_check(self, team, board_state):
        su_pos = self.find_su_position(team, board_state)
        if not su_pos: return False, None
        attacking_team = '한' if team == '초' else '초'
        if self.is_square_under_attack(su_pos, attacking_team, board_state): return True, su_pos
        return False, None

    def move_piece(self, from_pos, to_pos):
        from_y, from_x = from_pos
        to_y, to_x = to_pos
        fen_before = self.generate_fen()
        piece_to_move = self.board_state[from_y][from_x]
        captured_piece = self.board_state[to_y][to_x]
        if captured_piece and captured_piece.name == 'Su':
            self.game_over = True
            self.winner = piece_to_move.team
        if captured_piece and captured_piece.name == 'Jang':
            group_key = f"{captured_piece.team}_{captured_piece.general_group}"
            self.deactivated_groups[group_key] = True
            piece_to_move.captured_general_group = group_key
        if captured_piece and captured_piece.captured_general_group:
            self.deactivated_groups[captured_piece.captured_general_group] = False
        self.board_state[to_y][to_x] = piece_to_move
        self.board_state[from_y][from_x] = None
        piece_to_move.position = to_pos
        piece_to_move.has_moved = True
        
        fen_after = self.generate_fen()
        deactivated_groups_after = self.deactivated_groups.copy()
        from_alg = f"{chr(ord('a') + from_x)}{self.BOARD_HEIGHT_CELLS - from_y}"
        to_alg = f"{chr(ord('a') + to_x)}{self.BOARD_HEIGHT_CELLS - to_y}"
        notation = f"{from_alg}{to_alg}"
        move_data = {
            'team': piece_to_move.team, 'piece_korean_name': piece_to_move.korean_name,
            'from_pos': from_pos, 'to_pos': to_pos, 'notation': notation,
            'fen_before': fen_before, 'fen_after': fen_after,
            'captured_piece_name': captured_piece.korean_name if captured_piece else None,
            'deactivated_groups_after': deactivated_groups_after
        }
        self.move_history.append(move_data)
        
        # Clear selection state after move
        self.selected_pos = None
        self.valid_moves = []
        self.in_check_team = None
        self.checked_su_pos = None

        if not self.game_over:
            self.current_turn = '한' if self.current_turn == '초' else '초'
            in_check, checked_su_pos = self.is_su_in_check(self.current_turn, self.board_state)
            if in_check:
                self.in_check_team = self.current_turn
                self.checked_su_pos = checked_su_pos