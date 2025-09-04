from concurrent.futures import ProcessPoolExecutor
from stockfish import Stockfish
from dotenv import load_dotenv
import os

load_dotenv()
stockfish_path = os.getenv("SF_PATH")
stockfish = Stockfish(stockfish_path)

def analyze_position_worker(args):
    fen, depth = args
    stockfish = Stockfish(stockfish_path)
    stockfish.set_fen_position(fen)
    stockfish.set_depth(depth)
    stockfish.set_skill_level(20)
    if not stockfish.is_fen_valid(fen):
        return {"error": "Invalid FEN"}
    evaluation = stockfish.get_evaluation()
    top_moves = stockfish.get_top_moves(3)
    return {
        "evaluation": evaluation,
        "top_moves": top_moves
    }