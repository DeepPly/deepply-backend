# utils/batchsf.py
from __future__ import annotations
import os, asyncio, inspect
from typing import List, Dict, Any
import chess
import chess.engine

ENGINE_PATH    = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
SF_THREADS     = int(os.getenv("SF_THREADS", "4"))
SF_HASH_MB     = int(os.getenv("SF_HASH", "256"))
PER_POS_MS     = os.getenv("REVIEW_MS_PER_POS", 100)

def _limits() -> chess.engine.Limit:
    return chess.engine.Limit(time=int(PER_POS_MS) / 1000.0)

def _pov_to_eval(ps: chess.engine.PovScore, turn: chess.Color) -> Dict[str, Any]:
    """Return {"type": "cp"|"mate", "value": int} from a PovScore, POV = side to move."""
    # Convert to a white-relative Score, then flip sign if it's black to move.
    s_white = ps.white()
    if s_white.is_mate():
        val = s_white.mate()
        if turn is chess.BLACK:
            val = -val
        return {"type": "mate", "value": val}
    cp = s_white.score(mate_score=32000)
    if turn is chess.BLACK:
        cp = -cp
    return {"type": "cp", "value": cp}

def _topmove(board: chess.Board, info: Dict[str, Any]) -> Dict[str, Any]:
    """Match python-stockfish get_top_moves() keys."""
    ps = info.get("score")
    depth = int(info.get("depth", 0) or 0)
    sel   = int(info.get("seldepth", 0) or 0)
    nodes = int(info.get("nodes", 0) or 0)
    nps   = int(info.get("nps", 0) or 0)
    t_sec = float(info.get("time", 0.0) or 0.0)
    t_ms  = int(round(t_sec * 1000))

    pv_moves = info.get("pv", []) or []
    pv_uci   = [m.uci() for m in pv_moves]
    first_uci = pv_uci[0] if pv_uci else None

    centi = None
    mate  = None
    if isinstance(ps, chess.engine.PovScore):
        # Convert to white-relative then flip to side-to-move like above
        s_white = ps.white()
        if s_white.is_mate():
            mate = s_white.mate()
            if board.turn is chess.BLACK:
                mate = -mate
        else:
            centi = s_white.score(mate_score=32000)
            if board.turn is chess.BLACK:
                centi = -centi

    return {
        "Move": first_uci,
        "Centipawn": centi,
        "Mate": mate,
        "Depth": depth,
        "Seldepth": sel,
        "Time": t_ms,
        "Nodes": nodes,
        "Nps": nps,
        "Pv": " ".join(pv_uci),
    }

async def _analyse_with_engine(eng: chess.engine.AsyncEngine, fens: List[str], multipv: int) -> List[Dict[str, Any]]:
    # Do NOT set MultiPV here; python-chess manages it when you pass multipv=
    await eng.configure({"Threads": SF_THREADS, "Hash": SF_HASH_MB})
    lim = _limits()
    out: List[Dict[str, Any]] = []
    for fen in fens:
        board = chess.Board(fen)
        try:
            info = await asyncio.wait_for(eng.analyse(board, lim, multipv=multipv), timeout=5.0)
        except asyncio.TimeoutError:
            out.append({"evaluation": {"type": "cp", "value": 0}, "top_moves": []})
            continue
        infos = info if isinstance(info, list) else [info]
        if infos and "score" in infos[0]:
            eval_obj = _pov_to_eval(infos[0]["score"], board.turn)
        else:
            eval_obj = {"type": "cp", "value": 0}
        out.append({"evaluation": eval_obj, "top_moves": [_topmove(board, v) for v in infos]})
    return out

async def analyse_batch_stockfishlike(fens: List[str], multipv: int = 1) -> List[Dict[str, Any]]:
    if not ENGINE_PATH or not os.path.exists(ENGINE_PATH):
        raise FileNotFoundError(f"Stockfish not found at STOCKFISH_PATH='{ENGINE_PATH}'")
    try:
        multipv = max(1, min(int(multipv), 50))
    except Exception:
        multipv = 1

    ctx = chess.engine.popen_uci(ENGINE_PATH)
    if inspect.iscoroutine(ctx):                           # old API: await -> (transport, engine)
        transport, eng = await ctx
        try:
            return await _analyse_with_engine(eng, fens, multipv)
        finally:
            try:
                await eng.quit()
            finally:
                transport.close()
    else:                                                  # new API: async context manager
        async with ctx as eng:
            return await _analyse_with_engine(eng, fens, multipv)
