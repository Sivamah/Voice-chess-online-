import pygame
import asyncio
import chess
import chess.pgn
import chess.engine
import speech_recognition as sr
import os

# ---------------- INIT ----------------

pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 900, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Voice Chess")

SQUARE_SIZE = 75
board = chess.Board()

font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 18)

WHITE = (245, 245, 220)
BROWN = (139, 69, 19)
BLACK = (0, 0, 0)
GREY = (220, 220, 220)
RED = (200, 0, 0)

move_history = []
redo_stack = []

# ---------------- STOCKFISH ----------------

engine = None
if os.path.exists("stockfish.exe"):
    engine = chess.engine.SimpleEngine.popen_uci("stockfish.exe")
elif os.path.exists("stockfish"):
    engine = chess.engine.SimpleEngine.popen_uci("stockfish")

# ---------------- ASSETS ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

PIECES = {
    'P': 'white-pawn.png', 'N': 'white-knight.png', 'B': 'white-bishop.png',
    'R': 'white-rook.png', 'Q': 'white-queen.png', 'K': 'white-king.png',
    'p': 'black-pawn.png', 'n': 'black-knight.png', 'b': 'black-bishop.png',
    'r': 'black-rook.png', 'q': 'black-queen.png', 'k': 'black-king.png'
}

IMAGES = {}

def load_images():
    for k, v in PIECES.items():
        path = os.path.join(ASSETS_DIR, v)
        if os.path.exists(path):
            img = pygame.image.load(path)
            IMAGES[k] = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))
        else:
            print("Missing image:", v)

load_images()

# ---------------- DRAW ----------------

def draw_board():
    for r in range(8):
        for c in range(8):
            color = WHITE if (r + c) % 2 == 0 else BROWN
            pygame.draw.rect(
                screen, color,
                (c * SQUARE_SIZE, r * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            )

def draw_labels():
    files = "abcdefgh"
    for i in range(8):
        screen.blit(small_font.render(files[i], True, BLACK),
                    (i * SQUARE_SIZE + 35, 580))
        screen.blit(small_font.render(str(8 - i), True, BLACK),
                    (5, i * SQUARE_SIZE + 30))

def draw_pieces():
    for sq in chess.SQUARES:
        p = board.piece_at(sq)
        if p and p.symbol() in IMAGES:
            img = IMAGES[p.symbol()]
            x = chess.square_file(sq) * SQUARE_SIZE
            y = (7 - chess.square_rank(sq)) * SQUARE_SIZE
            screen.blit(img, (x, y))

def draw_score():
    pygame.draw.rect(screen, GREY, (600, 0, 300, 600))
    screen.blit(font.render("Score Sheet", True, BLACK), (680, 10))
    y = 40

    # Group moves into turns
    turns = []
    for i in range(0, len(move_history), 2):
        turn_num = (i // 2) + 1
        white = move_history[i]
        black = move_history[i + 1] if i + 1 < len(move_history) else ""
        turns.append((turn_num, white, black))

    # Show last 25 turns
    for t_num, w, b in turns[-25:]:
        # Turn number and White's move
        screen.blit(font.render(f"{t_num}. {w}", True, BLACK), (610, y))
        # Black's move
        if b:
            screen.blit(font.render(f"{b}", True, BLACK), (720, y))
        y += 20

def draw_status():
    y = 450
    if board.is_checkmate():
        screen.blit(font.render("CHECKMATE!", True, RED), (620, y))
    elif board.is_check():
        screen.blit(font.render("CHECK!", True, RED), (620, y))
    elif board.is_stalemate():
        screen.blit(font.render("STALEMATE", True, RED), (620, y))

    if engine:
        try:
            info = engine.analyse(board, chess.engine.Limit(depth=10))
            best = board.san(info["pv"][0])
            screen.blit(font.render(f"Best Move: {best}", True, BLACK), (610, y + 30))
        except:
            pass

# ---------------- SPEECH ----------------

recognizer = sr.Recognizer()

def recognize_speech():
    try:
        with sr.Microphone() as src:
            recognizer.adjust_for_ambient_noise(src, duration=0.3)
            audio = recognizer.listen(src, timeout=2, phrase_time_limit=3)
            return recognizer.recognize_google(audio).lower()
    except:
        return None

def parse_command(cmd):
    if not cmd:
        return None
    cmd = cmd.replace(" ", "")
    if cmd in ["undo", "redo", "playbestmove"]:
        return cmd
    if len(cmd) == 2:
        return cmd
    return cmd[0].upper() + cmd[1:]

# ---------------- GAME LOGIC ----------------

def make_move(move_str):
    try:
        move = None

        try:
            move = board.parse_san(move_str)
        except:
            pass

        if move is None and len(move_str) == 4:
            move = chess.Move.from_uci(move_str)

        if move and move in board.legal_moves:
            san = board.san(move)
            board.push(move)
            move_history.append(san)
            redo_stack.clear()
            save_pgn()
        else:
            print("Illegal move:", move_str)

    except Exception as e:
        print("Move error:", e)

def undo_move():
    if board.move_stack:
        redo_stack.append(board.pop())
        move_history.pop()

def redo_move():
    if redo_stack:
        move = redo_stack.pop()
        san = board.san(move)
        board.push(move)
        move_history.append(san)

def play_best():
    if engine:
        result = engine.play(board, chess.engine.Limit(time=0.5))
        make_move(board.san(result.move))

def save_pgn():
    game = chess.pgn.Game()
    node = game
    for m in board.move_stack:
        node = node.add_variation(m)
    with open("game_log.pgn", "w") as f:
        print(game, file=f)

# ---------------- MAIN LOOP ----------------

async def main():
    clock = pygame.time.Clock()
    running = True

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

        screen.fill(WHITE)
        draw_board()
        draw_labels()
        draw_pieces()
        draw_score()
        draw_status()
        pygame.display.flip()

        cmd = recognize_speech()
        if cmd:
            cmd = parse_command(cmd)
            if cmd == "undo":
                undo_move()
            elif cmd == "redo":
                redo_move()
            elif cmd == "playbestmove":
                play_best()
            else:
                make_move(cmd)

        clock.tick(30)
        await asyncio.sleep(0)

    if engine:
        engine.quit()
    pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
