from stockfish import Stockfish
from dotenv import load_dotenv
import os

load_dotenv()
stockfish_path = os.getenv("SF_PATH")
stockfish = Stockfish(stockfish_path)

def analyze_position(fen: str, depth: int = 20) -> dict:
    stockfish.set_fen_position(fen)
    stockfish.set_depth(depth)
    stockfish.set_skill_level(20)
    if not stockfish.is_fen_valid():
        return {"error": "Invalid FEN"}

    return {
        "evaluation": stockfish.get_evaluation(),
        "top_moves": stockfish.get_top_moves(3)
    }
