import chess.pgn
from chess import IllegalMoveError
import io
from analyze import analyze_position

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
    for move in game.mainline_moves():
        
        board.push(move)
        eval = analyze_position(board.fen())
        evals.append(eval.get('evaluation'))

    mistakes = []
    blunders = []
    great_moves = []
    for i in range(0, len(evals) - 1):
        if 1 > abs(evals[i] - evals[i + 1]) > 0.5:
            mistakes.append((i, evals[i], evals[i + 1]))
        elif abs(evals[i] - evals[i + 1]) >= 1:
            blunders.append((i, evals[i], evals[i + 1]))

        is_top_move = False
        second_best_eval = None
        if isinstance(evals[i], dict) and 'top_moves' in evals[i]:
            move_san = board.san(game.mainline_moves().__next__())
            top_moves = [m['move'] for m in evals[i]['top_moves']]
            if move_san == top_moves[0]:
                is_top_move = True
                second_best_eval = evals[i]['top_moves'][1]['evaluation'] if len(top_moves) > 1 else None


        if is_top_move:
            if second_best_eval is not None and evals[i] - second_best_eval >= abs(evals[i]):
                great_moves.append((i, evals[i]))


    return {
        "evaluations": evals, 
        "mistakes": mistakes, 
        "blunders": blunders, 
        "great_moves": great_moves
    }
