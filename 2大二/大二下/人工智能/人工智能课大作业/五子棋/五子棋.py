import tkinter as tk
from tkinter import ttk, messagebox
import math
import random
import copy
import threading
from functools import lru_cache


class MCTSNode:
    PATTERN_SCORES = {
        'five': 1000000,
        'live_four': 200000,
        'double_live_three': 150000,
        'dead_four': 30000,
        'live_three': 25000,
        'dead_three': 3000,
        'live_two': 500,
        'dead_two': 100
    }

    def __init__(self, board, player, depth=0, move=None, parent=None):
        self.board = [row[:] for row in board]
        self.player = player
        self.depth = depth
        self.move = move
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0.0
        self.untried_moves = self.get_legal_moves()

    def generate_candidates(self, board):
        candidates = set()
        for i in range(15):
            for j in range(15):
                if board[i][j] != 0:
                    for dx in (-2, -1, 0, 1, 2):
                        for dy in (-2, -1, 0, 1, 2):
                            if 0 <= i + dx < 15 and 0 <= j + dy < 15:
                                if board[i + dx][j + dy] == 0:
                                    candidates.add((i + dx, j + dy))
        if not candidates and sum(sum(row) for row in board) == 0:
            return {(7, 7)}
        return candidates

    def get_legal_moves(self):
        candidates = self.generate_candidates(self.board)
        if not candidates:
            return self.find_nearest_valid()
        sorted_moves = sorted(candidates, key=lambda m: self.evaluate_move(m), reverse=True)
        return sorted_moves[:30]

    def find_nearest_valid(self):
        occupied = [(i, j) for i in range(15) for j in range(15) if self.board[i][j] != 0]
        two_step = set()
        for o in occupied:
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    if 0 <= o[0] + dx < 15 and 0 <= o[1] + dy < 15:
                        if self.board[o[0] + dx][o[1] + dy] == 0:
                            two_step.add((o[0] + dx, o[1] + dy))
        return list(two_step) if two_step else [(i, j) for i in range(15) for j in range(15) if self.board[i][j] == 0]

    def detect_urgent_threats(self, opponent):
        urgent_points = set()
        candidates = self.generate_candidates(self.board)

        for (i, j) in candidates:
            temp_board = [row[:] for row in self.board]
            temp_board[i][j] = opponent

            if self._detect_pattern(temp_board, i, j, opponent, '11110') or \
                    self._detect_pattern(temp_board, i, j, opponent, '01111') or \
                    self._detect_pattern(temp_board, i, j, opponent, '01110'):
                urgent_points.add((i, j))

        secondary_threats = set()
        for (i, j) in candidates:
            temp_board = [row[:] for row in self.board]
            temp_board[i][j] = opponent

            if self._detect_double_live_three(temp_board, opponent) or \
                    self._detect_next_live_four(temp_board, opponent):
                secondary_threats.add((i, j))

        return list(urgent_points.union(secondary_threats))

    def _detect_double_live_three(self, board, player):
        live_three_count = 0
        for i in range(15):
            for j in range(15):
                if board[i][j] == 0:
                    temp_board = [row[:] for row in board]
                    temp_board[i][j] = player
                    if self._detect_pattern(temp_board, i, j, player, '01110'):
                        live_three_count += 1
                        if live_three_count >= 2:
                            return True
        return False

    def _detect_next_live_four(self, board, player):
        for i in range(15):
            for j in range(15):
                if board[i][j] == 0:
                    temp_board = [row[:] for row in board]
                    temp_board[i][j] = player
                    if self._detect_pattern(temp_board, i, j, player, '11110') or \
                            self._detect_pattern(temp_board, i, j, player, '01111'):
                        return True
        return False

    def _detect_pattern(self, board, r, c, player, pattern):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = []
            for k in range(-4, 5):
                x, y = r + dr * k, c + dc * k
                if 0 <= x < 15 and 0 <= y < 15:
                    line.append('1' if board[x][y] == player else '0' if board[x][y] == 0 else 'x')
                else:
                    line.append('x')
            current_line = ''.join(line)
            if pattern in current_line:
                return True
        return False

    @lru_cache(maxsize=65536)
    def evaluate_move(self, move):
        r, c = move
        attack = self._evaluate_point(r, c, self.player)
        defense = self._evaluate_point(r, c, 3 - self.player)
        return attack * 1.8 + defense * 1.2

    def _evaluate_point(self, r, c, player):
        score = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = []
            for i in range(1, 6):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < 15 and 0 <= nc < 15:
                    line.append(self.board[nr][nc])
                else:
                    line.append(-1)
            reverse_line = []
            for i in range(1, 6):
                nr, nc = r - dr * i, c - dc * i
                if 0 <= nr < 15 and 0 <= nc < 15:
                    reverse_line.append(self.board[nr][nc])
                else:
                    reverse_line.append(-1)
            full_line = reverse_line[::-1] + [player] + line
            score += self._score_pattern(full_line, player)
        return score

    def _score_pattern(self, line, player):
        str_line = ''.join(['1' if x == player else '0' if x == 0 else 'x' for x in line])
        if '11111' in str_line:
            return self.PATTERN_SCORES['five']
        if '011110' in str_line:
            return self.PATTERN_SCORES['live_four']
        if '011112' in str_line or '211110' in str_line:
            return self.PATTERN_SCORES['dead_four']
        if '01110' in str_line or '010110' in str_line:
            return self.PATTERN_SCORES['live_three']
        if '001100' in str_line or '010100' in str_line:
            return self.PATTERN_SCORES['live_two']
        return 0

    def uct_select_child(self):
        if self.parent.visits == 0:
            return random.choice(self.children)
        log_parent_visits = math.log(self.parent.visits)
        return max(self.children, key=lambda c: (c.wins / c.visits) + math.sqrt(2 * log_parent_visits / c.visits))

    def expand(self):
        move = self.untried_moves.pop()
        new_board = [row[:] for row in self.board]
        new_board[move[0]][move[1]] = self.player
        child = MCTSNode(new_board, 3 - self.player, self.depth + 1, move, self)
        self.children.append(child)
        return child

    def simulate(self):
        current_board = [row[:] for row in self.board]
        current_player = self.player
        for _ in range(20):
            legal_moves = self._get_simulate_moves(current_board)
            if not legal_moves:
                return 0.5
            move = random.choice(legal_moves)
            current_board[move[0]][move[1]] = current_player
            if self.check_win_simulate(current_board, move[0], move[1]):
                return 1.0 if current_player == self.player else 0.0
            current_player = 3 - current_player
        return 0.5

    def _get_simulate_moves(self, board):
        candidates = set()
        for i in range(15):
            for j in range(15):
                if board[i][j] != 0:
                    for dx in (-2, -1, 0, 1, 2):
                        for dy in (-2, -1, 0, 1, 2):
                            if 0 <= i + dx < 15 and 0 <= j + dy < 15:
                                if board[i + dx][j + dy] == 0:
                                    candidates.add((i + dx, j + dy))
        return list(candidates) if candidates else [(i, j) for i in range(15) for j in range(15) if board[i][j] == 0]

    def check_win_simulate(self, board, row, col):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        player = board[row][col]
        for dx, dy in directions:
            count = 1
            x, y = row + dx, col + dy
            while 0 <= x < 15 and 0 <= y < 15 and board[x][y] == player:
                count += 1
                x += dx
                y += dy
            x, y = row - dx, col - dy
            while 0 <= x < 15 and 0 <= y < 15 and board[x][y] == player:
                count += 1
                x -= dx
                y -= dy
            if count >= 5:
                return True
        return False


class AIPlayer:
    def __init__(self, iterations):
        self.iterations = iterations

    def get_move(self, board, player):
        root = MCTSNode(board, player)
        opponent = 3 - player

        urgent_moves = root.detect_urgent_threats(opponent)
        if urgent_moves:
            scored = sorted(urgent_moves, key=lambda m: root.evaluate_move(m), reverse=True)
            if len(scored) > 0:
                return scored[0]

        for _ in range(self.iterations):
            node = root
            while node.untried_moves == [] and node.children != []:
                node = node.uct_select_child()
            if node.untried_moves != [] and node.depth < 5:
                node = node.expand()
            result = node.simulate()
            while node is not None:
                node.visits += 1
                node.wins += result if node.player == player else (1 - result)
                node = node.parent

        if root.children:
            best = max(root.children, key=lambda c: c.visits)
            return best.move
        else:
            return random.choice([(i, j) for i in range(15) for j in range(15) if board[i][j] == 0])


# 原有AIPlayer类保持不变（请确保此处包含之前完整的AIPlayer类代码）

class Gobang:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("五子棋专业版")
        self.root.geometry("800x720")  # 设置初始窗口尺寸
        self.root.minsize(850, 600)  # 设置最小窗口尺寸

        # 调整棋盘参数
        self.cell_size = 36  # 增大单元格尺寸
        self.board_size = 15
        self.chess_radius = 14

        # 主容器布局优化
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 棋盘区域
        board_frame = ttk.Frame(main_frame)
        board_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 棋盘画布
        canvas_width = self.cell_size * (self.board_size + 2)
        canvas_height = self.cell_size * (self.board_size + 2)
        self.canvas = tk.Canvas(board_frame,
                                width=canvas_width,
                                height=canvas_height,
                                bg="#CDBA96",
                                highlightthickness=1,
                                highlightbackground="#666")
        self.canvas.pack(pady=(0, 10))

        # 控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        # 模式选择
        mode_frame = ttk.LabelFrame(control_frame, text="游戏模式")
        mode_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.mode_var = tk.StringVar(value="PvP")
        modes = [
            ("人人对战", "PvP"),
            ("人机对战", "PvC"),
            ("AI对战", "CvC")
        ]
        for text, mode in modes:
            rb = ttk.Radiobutton(mode_frame, text=text, value=mode,
                                 variable=self.mode_var, command=self.reset)
            rb.pack(side=tk.LEFT, padx=5)

        # 操作按钮区
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.LEFT, padx=10)

        self.undo_btn = ttk.Button(btn_frame, text="悔棋", command=self.undo)
        self.undo_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="重新开始", command=self.reset).pack(side=tk.LEFT, padx=2)

        # AI设置区
        ai_frame = ttk.LabelFrame(control_frame, text="AI设置")
        ai_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(ai_frame, text="强度:").pack(side=tk.LEFT)
        self.iter_var = tk.StringVar(value="800")
        iter_menu = ttk.Combobox(ai_frame, textvariable=self.iter_var,
                                 values=("500", "800", "1500"), width=6)
        iter_menu.pack(side=tk.LEFT, padx=2)

        # 游戏状态初始化
        self.board = [[0] * 15 for _ in range(15)]
        self.current_player = 1
        self.game_over = False
        self.ai_thinking = False
        self.history = []

        # 绘制棋盘
        self._draw_board_lines()
        self.canvas.bind("<Button-1>", self.click_handler)

        self.root.mainloop()

    def _draw_board_lines(self):
        """优化棋盘线绘制"""
        line_color = "#404040"

        # 绘制16条水平线和垂直线
        for i in range(16):
            # 水平线（从左到右贯穿整个画布）
            y = self.cell_size * (i + 1)
            self.canvas.create_line(
                self.cell_size, y,
                self.cell_size * 16, y,
                fill=line_color
            )
            # 垂直线（从上到下贯穿整个画布）
            x = self.cell_size * (i + 1)
            self.canvas.create_line(
                x, self.cell_size,
                x, self.cell_size * 16,
                fill=line_color
            )

        # 星位标记（保持原有位置不变）
        star_pos = [(3, 3), (3, 11), (11, 3), (11, 11), (7, 7)]
        for x, y in star_pos:
            cx = self.cell_size * (x + 1)
            cy = self.cell_size * (y + 1)
            self.canvas.create_oval(
                cx - 3, cy - 3,
                cx + 3, cy + 3,
                fill=line_color
            )

    # 保持其他方法完全不变（包括以下所有方法）
    def click_handler(self, event):
        if self.game_over or self.ai_thinking:
            return
        if self.mode_var.get() == "CvC":
            return
        if self.mode_var.get() == "PvC" and self.current_player == 2:
            return

        col = round((event.x - self.cell_size) / self.cell_size)
        row = round((event.y - self.cell_size) / self.cell_size)
        if 0 <= row < 15 and 0 <= col < 15 and self.board[row][col] == 0:
            self._record_state()
            self.place_chess(row, col)
            if self.mode_var.get() == "PvC" and not self.game_over:
                self.ai_thinking = True
                threading.Thread(target=self.ai_move).start()

    def _record_state(self):
        self.history.append({
            'board': copy.deepcopy(self.board),
            'player': self.current_player,
            'game_over': self.game_over
        })
        self.undo_btn['state'] = 'normal'

    def undo(self):
        if len(self.history) < 1:
            return
        last_state = self.history.pop(-1)
        self.board = last_state['board']
        self.current_player = last_state['player']
        self.game_over = last_state['game_over']
        self.redraw_board()
        self.undo_btn['state'] = 'normal' if len(self.history) >= 1 else 'disabled'

    def redraw_board(self):
        self.canvas.delete("chess")
        for i in range(15):
            for j in range(15):
                if self.board[i][j] != 0:
                    self._draw_chess(i, j, self.board[i][j])

    def _draw_chess(self, row, col, player):
        x = self.cell_size * (col + 1)
        y = self.cell_size * (row + 1)
        color = "black" if player == 1 else "white"
        self.canvas.create_oval(x - self.chess_radius,
                                y - self.chess_radius,
                                x + self.chess_radius,
                                y + self.chess_radius,
                                fill=color,
                                outline="black",
                                tags="chess")

    def place_chess(self, row, col):
        self.board[row][col] = self.current_player
        self._draw_chess(row, col, self.current_player)
        if self.check_win(row, col):
            self.game_over = True
            winner = "黑棋" if self.current_player == 1 else "白棋"
            messagebox.showinfo("游戏结束", f"{winner}获胜！")
            if self.mode_var.get() == "CvC":
                self.auto_play = False
        else:
            self.current_player = 3 - self.current_player
            if self.mode_var.get() == "CvC" and not self.game_over:
                self.root.after(500, self.ai_move_step)

    def check_win(self, row, col):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        player = self.board[row][col]
        for dx, dy in directions:
            count = 1
            x, y = row + dx, col + dy
            while 0 <= x < 15 and 0 <= y < 15 and self.board[x][y] == player:
                count += 1
                x += dx
                y += dy
            x, y = row - dx, col - dy
            while 0 <= x < 15 and 0 <= y < 15 and self.board[x][y] == player:
                count += 1
                x -= dx
                y -= dy
            if count >= 5:
                return True
        return False

    def ai_move(self):
        ai = AIPlayer(int(self.iter_var.get()))
        board_copy = copy.deepcopy(self.board)
        try:
            move = ai.get_move(board_copy, self.current_player)
        except Exception as e:
            legal_moves = [(i, j) for i in range(15) for j in range(15) if board_copy[i][j] == 0]
            move = random.choice(legal_moves) if legal_moves else (7, 7)
        self.root.after(0, self.finish_ai_move, move)

    def ai_move_step(self):
        if not self.game_over and self.mode_var.get() == "CvC":
            self.ai_thinking = True
            threading.Thread(target=self.ai_move).start()

    def finish_ai_move(self, move):
        self._record_state()
        self.place_chess(*move)
        self.ai_thinking = False

    def reset(self):
        self.canvas.delete("chess")
        self.board = [[0] * 15 for _ in range(15)]
        self.current_player = 1
        self.game_over = False
        self.ai_thinking = False
        self.history = []
        self.undo_btn['state'] = 'disabled'
        self._draw_board_lines()
        if self.mode_var.get() == "CvC":
            self.auto_play = True
            self.ai_move_step()


if __name__ == "__main__":
    Gobang()