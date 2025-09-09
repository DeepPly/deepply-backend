# utils/batchsf.py
from __future__ import annotations
import os
import asyncio
import inspect
from typing import List, Dict, Any

import chess
import chess.engine

# -------- Config via env (safe defaults) --------
ENGINE_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
SF_THREADS  = int(os.getenv("SF_THREADS", "4"))
SF_HASH_MB  = int(os.getenv("SF_HASH", "256"))

# Per-position budget: choose ONE (time or nodes). Time wins if both set.
PER_POS_MS  = os.getenv("REVIEW_MS_PER_POS")      # e.g. "50"
PER_POS_NODES = os.getenv("REVIEW_NODES_PER_POS") # e.g. "80000"

# -------- Helpers to match your old result shape --------
def _score_to_eval(score: chess.engine.PovScore, turn: chess.Color) -> Dict[str, Any]:
    s = score.pov(turn)
    return {"type": "mate", "value": s.mate()} if s.is_mate() \
           else {"type": "cp", "value": s.score(mate_score=32000)}

def _topmove(board: chess.Board, info: Dict[str, Any]) -> Dict[str, Any]:
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

    if score.is_mate():
        mate_val, cp_val = score.mate(), None
    else:
        mate_val, cp_val = None, score.score(mate_score=32000)

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

def _limits() -> chess.engine.Limit:
    if PER_POS_MS and PER_POS_MS.strip():
        return chess.engine.Limit(time=int(PER_POS_MS) / 1000.0)
    if PER_POS_NODES and PER_POS_NODES.strip():
        return chess.engine.Limit(nodes=int(PER_POS_NODES))
    # conservative default
    return chess.engine.Limit(time=0.05)

async def _analyse_with_engine(eng: chess.engine.AsyncEngine, fen_list: List[str], multipv: int) -> List[Dict[str, Any]]:
    # IMPORTANT: do NOT set MultiPV here — python-chess manages it when you pass multipv=
    await eng.configure({"Threads": SF_THREADS, "Hash": SF_HASH_MB})
    lim = _limits()
    out: List[Dict[str, Any]] = []
    for fen in fen_list:
        board = chess.Board(fen)
        # Wrap each analyse in a timeout so a stuck engine can't freeze the request
        try:
            info = await asyncio.wait_for(eng.analyse(board, lim, multipv=multipv), timeout=5.0)
        except asyncio.TimeoutError:
            # Graceful fallback: empty PV, zero eval
            out.append({"evaluation": {"type": "cp", "value": 0}, "top_moves": []})
            continue

        infos = info if isinstance(info, list) else [info]
        if infos and "score" in infos[0]:
            eval_obj = _score_to_eval(infos[0]["score"], board.turn)
        else:
            eval_obj = {"type": "cp", "value": 0}
        out.append({
            "evaluation": eval_obj,
            "top_moves": [_topmove(board, v) for v in infos],
        })
    return out

async def analyse_batch_stockfishlike(fens: List[str], multipv: int = 1) -> List[Dict[str, Any]]:
    """
    Returns a list aligned to `fens`, each item:
      {
        "evaluation": {"type": "cp"|"mate", "value": int},
        "top_moves": [
           {"Move","Centipawn","Mate","Depth","Seldepth","Time","Nodes","Nps","Pv"}, ...
        ]
      }
    """
    if not ENGINE_PATH or not os.path.exists(ENGINE_PATH):
        # Fail fast with a clear message
        raise FileNotFoundError(f"Stockfish not found at STOCKFISH_PATH='{ENGINE_PATH}'")

    # Clamp multipv to sane bounds that Stockfish accepts
    try:
        multipv = max(1, min(int(multipv), 50))
    except Exception:
        multipv = 1

    # Support both python-chess async APIs:
    ctx = chess.engine.popen_uci(ENGINE_PATH)

    # Older API: awaitable returning (transport, engine)
    if inspect.iscoroutine(ctx):
        transport, eng = await ctx
        try:
            return await _analyse_with_engine(eng, fens, multipv)
        finally:
            try:
                await eng.quit()
            finally:
                transport.close()

    # Newer API: async context manager yielding engine
    async with ctx as eng:
        return await _analyse_with_engine(eng, fens, multipv)
