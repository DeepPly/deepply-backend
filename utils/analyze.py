from concurrent.futures import ProcessPoolExecutor
from stockfish import Stockfish
from dotenv import load_dotenv
import os

load_dotenv()
stockfish_path = os.getenv("SF_PATH", "stockfish")

def make_engine():
    threads = int(os.getenv("SF_THREADS", "2"))
    hash_mb = int(os.getenv("SF_HASH", "256"))
    return Stockfish(stockfish_path, parameters={"Threads": threads, "Hash": hash_mb, "MultiPV": 1})

def analyze_position_worker(args):
    fen, depth = args
    stockfish = Stockfish(stockfish_path)
    stockfish.set_fen_position(fen)
    stockfish.set_depth(depth)
    stockfish.set_skill_level(20)
    if not stockfish.is_fen_valid(fen):
        return {"error": "Invalid FEN"}
    evaluation = stockfish.get_evaluation()
    top_moves = stockfish.get_top_moves(2)
    return {
        "evaluation": evaluation,
        "top_moves": top_moves
    }