import chess.pgn
from chess import IllegalMoveError
import io

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

    