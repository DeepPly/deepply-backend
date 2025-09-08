from concurrent.futures import ProcessPoolExecutor
import copy
import chess.pgn
from chess import IllegalMoveError, Move
import io
from .analyze import analyze_position_worker

def validate_pgn(pgn: str) -> tuple[bool, str]:
    """
    Validate the provided PGN string.
    
    Args:
        pgn (str): The PGN string to validate.

    Returns:
        tuple[bool, str]: A tuple containing a boolean indicating validity and an error message if invalid.
    """
    try:
        pgn_io = io.StringIO(pgn)
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            return False, "Invalid PGN format"

        
        if game.errors == []:
            # Check if the game has a valid result
            if game.headers.get("Result") not in ["1-0", "0-1", "1/2-1/2", "*"]:
                return False, "Invalid game result"
            return True, "PGN is valid"
        else:
            for error in game.errors:
                if isinstance(error, IllegalMoveError):
                    return False, "Illegal moves found in PGN"
                else:
                    return False, str(error)
    except Exception as e:
        print(f"PGN validation error: {e}")
        return False, str(e)

def game_analysis(pgn: str) -> dict:
    pgn_io = io.StringIO(pgn)
    game = chess.pgn.read_game(pgn_io)
    if game is None or game.errors != []:
        return {"error": "Invalid PGN"}
    
    board = game.board()
    
    evals = []
    fens = []
    moves = []
    moves_san = []
    for move in game.mainline_moves():
        moves.append(move)
        moves_san.append(board.san(move))
        board.push(move)
        fens.append(board.fen())

    with ProcessPoolExecutor() as executor:
        evals = list(executor.map(analyze_position_worker, [(fen, 15) for fen in fens]))
    
    mistakes = []
    blunders = []
    great_moves = []
    for i in range(1, len(evals)):
        diff = None
        if evals[i]['evaluation']['type'] == 'mate':
            if evals[i - 1]['evaluation']['type'] == 'cp':
                mistakes.append((i, evals[i], evals[i - 1]))
        elif evals[i]['evaluation']['type'] == 'cp' and evals[i - 1]['evaluation']['type'] == 'cp':
            diff = abs(evals[i]['evaluation']['value'] - evals[i - 1]['evaluation']['value'])

        if diff: 
            if 100 > diff > 50:
                mistakes.append((i % 2, evals[i - 1], evals[i], moves_san[i]))
            elif diff >= 100:
                blunders.append((i % 2, evals[i], evals[i - 1], moves_san[i]))

        if i == 0: continue
        is_top_move = False
        second_best = None
        if isinstance(evals[i], dict) and 'top_moves' in evals[i]:
            move_san = moves[i]
            top_moves = [m['Move'] for m in evals[i - 1]['top_moves']]
            if move_san == top_moves[0]:
                is_top_move = True
                second_best = evals[i]['top_moves'][1] if len(top_moves) > 1 else None


        if is_top_move:
            if second_best is not None:
                if second_best['Mate'] is not None:
                    if evals[i] - second_best['evaluation'] >= abs(evals[i]):
                        great_moves.append((i % 2, evals[i], moves_san[i]))


    eval_copy = copy.deepcopy(evals)
    for i in range(len(evals)):
        eval_copy[i]['move_made'] = moves_san[i]

    return {
        "evaluations": eval_copy, 
        "mistakes": mistakes, 
        "blunders": blunders, 
        "great_moves": great_moves
    }
