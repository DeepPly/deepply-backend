# utils/batchsf.py
import os, asyncio
import chess
import chess.engine

ENGINE_PATH = os.getenv("STOCKFISH_PATH", "/usr/games/stockfish")
SF_THREADS  = int(os.getenv("SF_THREADS", "4"))
SF_HASH_MB  = int(os.getenv("SF_HASH", "256"))
PER_POS_MS  = int(os.getenv("REVIEW_MS_PER_POS", "50"))
NODES_STR   = os.getenv("REVIEW_NODES_PER_POS")  # e.g. "80000"

def _score_obj(povscore: chess.engine.PovScore, turn) -> dict:
    s = povscore.pov(turn)
    return {"type": "mate", "value": s.mate()} if s.is_mate() \
           else {"type": "cp", "value": s.score(mate_score=32000)}

def _topmove(board: chess.Board, info: dict) -> dict:
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

async def analyse_batch_stockfishlike(fens: list[str], multipv: int = 1) -> list[dict]:
    limits = (chess.engine.Limit(time=PER_POS_MS / 1000.0)
              if not NODES_STR else chess.engine.Limit(nodes=int(NODES_STR)))

    out: list[dict] = []

    # Support both APIs:
    ctx = chess.engine.popen_uci(ENGINE_PATH)
    if asyncio.iscoroutine(ctx):  # old API: await -> (transport, engine)
        transport, eng = await ctx
        try:
            await eng.configure({"Threads": SF_THREADS, "Hash": SF_HASH_MB, "MultiPV": multipv})
            for fen in fens:
                board = chess.Board(fen)
                info = await eng.analyse(board, limits, multipv=multipv)
                infos = info if isinstance(info, list) else [info]
                eval_obj = _score_obj(infos[0]["score"], board.turn) if infos and "score" in infos[0] \
                           else {"type": "cp", "value": 0}
                out.append({"evaluation": eval_obj,
                            "top_moves": [_topmove(board, v) for v in infos]})
        finally:
            await eng.quit()
            transport.close()
    else:
        # newer API: ctx is an async context manager yielding engine
        async with ctx as eng:
            await eng.configure({"Threads": SF_THREADS, "Hash": SF_HASH_MB, "MultiPV": multipv})
            for fen in fens:
                board = chess.Board(fen)
                info = await eng.analyse(board, limits, multipv=multipv)
                infos = info if isinstance(info, list) else [info]
                eval_obj = _score_obj(infos[0]["score"], board.turn) if infos and "score" in infos[0] \
                           else {"type": "cp", "value": 0}
                out.append({"evaluation": eval_obj,
                            "top_moves": [_topmove(board, v) for v in infos]})

    return out
