# utils/batch_engine_stockfishlike.py
import os, asyncio, math
import chess
import chess.engine

ENGINE_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
SF_THREADS  = int(os.getenv("SF_THREADS", "4"))
SF_HASH_MB  = int(os.getenv("SF_HASH", "256"))
# choose ONE budget: time per pos OR nodes per pos
PER_POS_MS  = int(os.getenv("REVIEW_MS_PER_POS", "50"))
NODES_STR   = os.getenv("REVIEW_NODES_PER_POS")  # e.g. "80000"

def _score_to_eval(score: chess.engine.PovScore) -> dict:
    # same semantics as python-stockfish: type/value
    if score.is_mate():
        return {"type": "mate", "value": score.mate()}
    # centipawns; mimic stockfish where positive favors side-to-move POV
    return {"type": "cp", "value": score.score(mate_score=32000)}

def _variant_to_topmove(board: chess.Board, info: dict) -> dict:
    # Build a single entry like python-stockfish get_top_moves()[0]
    # Fields may be missing depending on limit; default sanely.
    score = info.get("score", chess.engine.PovScore(chess.engine.Cp(0), board.turn))
    depth = int(info.get("depth", 0) or 0)
    sel   = int(info.get("seldepth", 0) or 0)
    nodes = int(info.get("nodes", 0) or 0)
    nps   = int(info.get("nps", 0) or 0)
    t_sec = float(info.get("time", 0.0) or 0.0)
    t_ms  = int(round(t_sec * 1000))

    pv_moves = info.get("pv", []) or []
    pv_uci   = [m.uci() for m in pv_moves]
    first_uci = pv_uci[0] if pv_uci else None

    # stockfish-style dual fields: Centipawn or Mate, one is None
    if score.is_mate():
        mate_val = score.mate()
        cp_val   = None
    else:
        mate_val = None
        cp_val   = score.score(mate_score=32000)

    return {
        "Move": first_uci,
        "Centipawn": cp_val,
        "Mate": mate_val,
        "Depth": depth,
        "Seldepth": sel,
        "Time": t_ms,
        "Nodes": nodes,
        "Nps": nps,
        "Pv": " ".join(pv_uci),
    }

async def analyse_batch_stockfishlike(fens: list[str], multipv: int = 1) -> list[dict]:
    """
    Returns a list (aligned to input FENs) of:
      { "evaluation": {"type": "cp"|"mate", "value": int},
        "top_moves": [ {Move, Centipawn, Mate, Depth, Seldepth, Time, Nodes, Nps, Pv}, ... ] }
    """
    limits = (
        chess.engine.Limit(time=PER_POS_MS / 1000.0)
        if not NODES_STR else chess.engine.Limit(nodes=int(NODES_STR))
    )
    out = []
    async with await chess.engine.popen_uci(ENGINE_PATH) as eng:
        await eng.configure({"Threads": SF_THREADS, "Hash": SF_HASH_MB, "MultiPV": multipv})
        for fen in fens:
            board = chess.Board(fen)
            info = await eng.analyse(board, limits, multipv=multipv)
            infos = info if isinstance(info, list) else [info]

            pov = infos[0].get("score") if infos else chess.engine.PovScore(chess.engine.Cp(0), board.turn)
            eval_obj = _score_to_eval(pov.pov(board.turn) if hasattr(pov, "pov") else pov)

            top_moves = [_variant_to_topmove(board, v) for v in infos]
            out.append({"evaluation": eval_obj, "top_moves": top_moves})
    return out
