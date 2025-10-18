from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple, Dict


# ==================== Enums ====================

class PieceColor(Enum):
    """Represents piece colors"""
    WHITE = "WHITE"
    BLACK = "BLACK"
    
    def opposite(self) -> 'PieceColor':
        return PieceColor.BLACK if self == PieceColor.WHITE else PieceColor.WHITE


class PieceType(Enum):
    """Represents different chess piece types"""
    KING = "K"
    QUEEN = "Q"
    ROOK = "R"
    BISHOP = "B"
    KNIGHT = "N"
    PAWN = "P"


class GameStatus(Enum):
    """Represents the current state of the game"""
    IN_PROGRESS = "IN_PROGRESS"
    WHITE_WINS = "WHITE_WINS"
    BLACK_WINS = "BLACK_WINS"
    STALEMATE = "STALEMATE"
    DRAW = "DRAW"


# ==================== Core Models ====================

class Position:
    """Represents a position on the chess board"""
    
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    
    def is_valid(self) -> bool:
        return 0 <= self.row < 8 and 0 <= self.col < 8
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Position):
            return False
        return self.row == other.row and self.col == other.col
    
    def __hash__(self) -> int:
        return hash((self.row, self.col))
    
    def __repr__(self) -> str:
        return f"({self.row}, {self.col})"
    
    def to_chess_notation(self) -> str:
        """Convert to standard chess notation (e.g., 'e4')"""
        return f"{chr(ord('a') + self.col)}{8 - self.row}"
    
    @staticmethod
    def from_chess_notation(notation: str) -> 'Position':
        """Create Position from chess notation (e.g., 'e4')"""
        col = ord(notation[0].lower()) - ord('a')
        row = 8 - int(notation[1])
        return Position(row, col)


class Move:
    """Represents a chess move"""
    
    def __init__(self, start: Position, end: Position, 
                 piece: 'Piece', captured_piece: Optional['Piece'] = None):
        self.start = start
        self.end = end
        self.piece = piece
        self.captured_piece = captured_piece
        self.is_castling = False
        self.is_en_passant = False
        self.promotion_type: Optional[PieceType] = None
    
    def __repr__(self) -> str:
        return f"{self.piece.get_type().value}: {self.start.to_chess_notation()} -> {self.end.to_chess_notation()}"


# ==================== Strategy Pattern: Move Strategies ====================

class MoveStrategy(ABC):
    """Abstract base class for piece movement strategies"""
    
    @abstractmethod
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        """Get all possible moves for a piece at the given position"""
        pass
    
    def _get_linear_moves(self, board: 'Board', position: Position, 
                         directions: List[Tuple[int, int]]) -> List[Position]:
        """Helper method for pieces that move in straight lines"""
        moves = []
        piece = board.get_piece(position)
        
        for d_row, d_col in directions:
            current_row, current_col = position.row, position.col
            
            while True:
                current_row += d_row
                current_col += d_col
                new_pos = Position(current_row, current_col)
                
                if not new_pos.is_valid():
                    break
                
                target_piece = board.get_piece(new_pos)
                
                if target_piece is None:
                    moves.append(new_pos)
                elif target_piece.get_color() != piece.get_color():
                    moves.append(new_pos)
                    break
                else:
                    break
        
        return moves


class KingMoveStrategy(MoveStrategy):
    """Movement strategy for King"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        moves = []
        piece = board.get_piece(position)
        
        # King moves one square in any direction
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), 
                     (0, 1), (1, -1), (1, 0), (1, 1)]
        
        for d_row, d_col in directions:
            new_pos = Position(position.row + d_row, position.col + d_col)
            
            if not new_pos.is_valid():
                continue
            
            target_piece = board.get_piece(new_pos)
            if target_piece is None or target_piece.get_color() != piece.get_color():
                moves.append(new_pos)
        
        # TODO: Add castling logic in a complete implementation
        
        return moves


class QueenMoveStrategy(MoveStrategy):
    """Movement strategy for Queen"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        # Queen moves like both rook and bishop
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1),  # Rook directions
                     (-1, -1), (-1, 1), (1, -1), (1, 1)]  # Bishop directions
        return self._get_linear_moves(board, position, directions)


class RookMoveStrategy(MoveStrategy):
    """Movement strategy for Rook"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Vertical and horizontal
        return self._get_linear_moves(board, position, directions)


class BishopMoveStrategy(MoveStrategy):
    """Movement strategy for Bishop"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]  # Diagonals
        return self._get_linear_moves(board, position, directions)


class KnightMoveStrategy(MoveStrategy):
    """Movement strategy for Knight"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        moves = []
        piece = board.get_piece(position)
        
        # Knight moves in L-shape
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                       (1, -2), (1, 2), (2, -1), (2, 1)]
        
        for d_row, d_col in knight_moves:
            new_pos = Position(position.row + d_row, position.col + d_col)
            
            if not new_pos.is_valid():
                continue
            
            target_piece = board.get_piece(new_pos)
            if target_piece is None or target_piece.get_color() != piece.get_color():
                moves.append(new_pos)
        
        return moves


class PawnMoveStrategy(MoveStrategy):
    """Movement strategy for Pawn"""
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        moves = []
        piece = board.get_piece(position)
        direction = -1 if piece.get_color() == PieceColor.WHITE else 1
        start_row = 6 if piece.get_color() == PieceColor.WHITE else 1
        
        # Move forward one square
        forward_one = Position(position.row + direction, position.col)
        if forward_one.is_valid() and board.get_piece(forward_one) is None:
            moves.append(forward_one)
            
            # Move forward two squares from starting position
            if position.row == start_row:
                forward_two = Position(position.row + 2 * direction, position.col)
                if board.get_piece(forward_two) is None:
                    moves.append(forward_two)
        
        # Capture diagonally
        for d_col in [-1, 1]:
            capture_pos = Position(position.row + direction, position.col + d_col)
            if capture_pos.is_valid():
                target_piece = board.get_piece(capture_pos)
                if target_piece and target_piece.get_color() != piece.get_color():
                    moves.append(capture_pos)
        
        # TODO: Add en passant logic in a complete implementation
        
        return moves


# ==================== Piece Classes ====================

class Piece:
    """Represents a chess piece"""
    
    def __init__(self, piece_type: PieceType, color: PieceColor, 
                 move_strategy: MoveStrategy):
        self._type = piece_type
        self._color = color
        self._move_strategy = move_strategy
        self._has_moved = False
    
    def get_type(self) -> PieceType:
        return self._type
    
    def get_color(self) -> PieceColor:
        return self._color
    
    def has_moved(self) -> bool:
        return self._has_moved
    
    def mark_as_moved(self) -> None:
        self._has_moved = True
    
    def get_possible_moves(self, board: 'Board', position: Position) -> List[Position]:
        return self._move_strategy.get_possible_moves(board, position)
    
    def __repr__(self) -> str:
        color_prefix = 'W' if self._color == PieceColor.WHITE else 'B'
        return f"{color_prefix}{self._type.value}"


# ==================== Board ====================

class Board:
    """Represents the chess board"""
    
    def __init__(self):
        self._grid: List[List[Optional[Piece]]] = [[None for _ in range(8)] for _ in range(8)]
        self._piece_positions: Dict[PieceColor, Dict[Position, Piece]] = {
            PieceColor.WHITE: {},
            PieceColor.BLACK: {}
        }
    
    def get_piece(self, position: Position) -> Optional[Piece]:
        if not position.is_valid():
            return None
        return self._grid[position.row][position.col]
    
    def set_piece(self, position: Position, piece: Optional[Piece]) -> None:
        if not position.is_valid():
            raise ValueError(f"Invalid position: {position}")
        
        # Remove from old position tracking
        old_piece = self._grid[position.row][position.col]
        if old_piece:
            if position in self._piece_positions[old_piece.get_color()]:
                del self._piece_positions[old_piece.get_color()][position]
        
        # Update grid
        self._grid[position.row][position.col] = piece
        
        # Add to new position tracking
        if piece:
            self._piece_positions[piece.get_color()][position] = piece
    
    def move_piece(self, start: Position, end: Position) -> Optional[Piece]:
        """Move a piece and return any captured piece"""
        piece = self.get_piece(start)
        if not piece:
            return None
        
        captured_piece = self.get_piece(end)
        
        self.set_piece(end, piece)
        self.set_piece(start, None)
        piece.mark_as_moved()
        
        return captured_piece
    
    def get_king_position(self, color: PieceColor) -> Optional[Position]:
        """Find the king's position for the given color"""
        for position, piece in self._piece_positions[color].items():
            if piece.get_type() == PieceType.KING:
                return position
        return None
    
    def get_all_pieces(self, color: PieceColor) -> Dict[Position, Piece]:
        """Get all pieces for a given color"""
        return self._piece_positions[color].copy()
    
    def display(self) -> None:
        """Display the board"""
        print("\n  a b c d e f g h")
        for i in range(8):
            print(f"{8-i} ", end="")
            for j in range(8):
                piece = self._grid[i][j]
                if piece:
                    print(f"{piece} ", end="")
                else:
                    print(".  ", end="")
            print(f"{8-i}")
        print("  a b c d e f g h\n")


# ==================== Factory Pattern: Piece Factory ====================

class PieceFactory:
    """Factory for creating chess pieces"""
    
    _strategies = {
        PieceType.KING: KingMoveStrategy(),
        PieceType.QUEEN: QueenMoveStrategy(),
        PieceType.ROOK: RookMoveStrategy(),
        PieceType.BISHOP: BishopMoveStrategy(),
        PieceType.KNIGHT: KnightMoveStrategy(),
        PieceType.PAWN: PawnMoveStrategy()
    }
    
    @staticmethod
    def create_piece(piece_type: PieceType, color: PieceColor) -> Piece:
        """Create a piece with the appropriate movement strategy"""
        strategy = PieceFactory._strategies[piece_type]
        return Piece(piece_type, color, strategy)


class BoardFactory:
    """Factory for creating and initializing chess boards"""
    
    @staticmethod
    def create_standard_board() -> Board:
        """Create a standard chess board with initial setup"""
        board = Board()
        
        # Set up pawns
        for col in range(8):
            board.set_piece(Position(6, col), 
                          PieceFactory.create_piece(PieceType.PAWN, PieceColor.WHITE))
            board.set_piece(Position(1, col), 
                          PieceFactory.create_piece(PieceType.PAWN, PieceColor.BLACK))
        
        # Set up other pieces
        piece_order = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, 
                      PieceType.QUEEN, PieceType.KING, PieceType.BISHOP, 
                      PieceType.KNIGHT, PieceType.ROOK]
        
        for col, piece_type in enumerate(piece_order):
            board.set_piece(Position(7, col), 
                          PieceFactory.create_piece(piece_type, PieceColor.WHITE))
            board.set_piece(Position(0, col), 
                          PieceFactory.create_piece(piece_type, PieceColor.BLACK))
        
        return board
    
    @staticmethod
    def create_empty_board() -> Board:
        """Create an empty chess board"""
        return Board()


# ==================== Move Validator ====================

class MoveValidator:
    """Validates chess moves"""
    
    @staticmethod
    def is_valid_move(board: Board, move: Move, current_color: PieceColor) -> Tuple[bool, str]:
        """
        Validate if a move is legal.
        Returns (is_valid, error_message)
        """
        # Check if piece exists
        piece = board.get_piece(move.start)
        if not piece:
            return False, "No piece at starting position"
        
        # Check if it's the right player's turn
        if piece.get_color() != current_color:
            return False, "Not your piece"
        
        # Check if move is in possible moves
        possible_moves = piece.get_possible_moves(board, move.start)
        if move.end not in possible_moves:
            return False, "Invalid move for this piece"
        
        # Check if move would leave king in check (simulate move)
        if MoveValidator._would_be_in_check_after_move(board, move, current_color):
            return False, "Move would leave king in check"
        
        return True, ""
    
    @staticmethod
    def _would_be_in_check_after_move(board: Board, move: Move, color: PieceColor) -> bool:
        """Check if making this move would leave the king in check"""
        # Create a temporary board state
        temp_board = MoveValidator._simulate_move(board, move)
        return MoveValidator.is_in_check(temp_board, color)
    
    @staticmethod
    def _simulate_move(board: Board, move: Move) -> Board:
        """Create a board copy with the move applied"""
        # Simple deep copy simulation
        temp_board = Board()
        for row in range(8):
            for col in range(8):
                pos = Position(row, col)
                piece = board.get_piece(pos)
                if piece:
                    new_piece = PieceFactory.create_piece(piece.get_type(), piece.get_color())
                    temp_board.set_piece(pos, new_piece)
        
        temp_board.move_piece(move.start, move.end)
        return temp_board
    
    @staticmethod
    def is_in_check(board: Board, color: PieceColor) -> bool:
        """Check if the king of the given color is in check"""
        king_position = board.get_king_position(color)
        if not king_position:
            return False
        
        # Check if any opponent piece can attack the king
        opponent_color = color.opposite()
        opponent_pieces = board.get_all_pieces(opponent_color)
        
        for position, piece in opponent_pieces.items():
            possible_moves = piece.get_possible_moves(board, position)
            if king_position in possible_moves:
                return True
        
        return False
    
    @staticmethod
    def is_checkmate(board: Board, color: PieceColor) -> bool:
        """Check if the given color is in checkmate"""
        if not MoveValidator.is_in_check(board, color):
            return False
        
        # Check if any legal move can get out of check
        return not MoveValidator._has_legal_moves(board, color)
    
    @staticmethod
    def is_stalemate(board: Board, color: PieceColor) -> bool:
        """Check if the given color is in stalemate"""
        if MoveValidator.is_in_check(board, color):
            return False
        
        # No legal moves but not in check
        return not MoveValidator._has_legal_moves(board, color)
    
    @staticmethod
    def _has_legal_moves(board: Board, color: PieceColor) -> bool:
        """Check if the player has any legal moves"""
        pieces = board.get_all_pieces(color)
        
        for position, piece in pieces.items():
            possible_moves = piece.get_possible_moves(board, position)
            for end_pos in possible_moves:
                move = Move(position, end_pos, piece)
                if not MoveValidator._would_be_in_check_after_move(board, move, color):
                    return True
        
        return False


# ==================== State Pattern: Game States ====================

class GameState(ABC):
    """Abstract base class for game states"""
    
    @abstractmethod
    def make_move(self, game: 'ChessGame', start: Position, end: Position) -> bool:
        pass
    
    @abstractmethod
    def get_status(self) -> GameStatus:
        pass


class InProgressState(GameState):
    """State when the game is in progress"""
    
    def make_move(self, game: 'ChessGame', start: Position, end: Position) -> bool:
        board = game.get_board()
        current_color = game.get_current_player_color()
        
        piece = board.get_piece(start)
        if not piece:
            print("No piece at starting position")
            return False
        
        captured_piece = board.get_piece(end)
        move = Move(start, end, piece, captured_piece)
        
        # Validate move
        is_valid, error_msg = MoveValidator.is_valid_move(board, move, current_color)
        if not is_valid:
            print(f"Invalid move: {error_msg}")
            return False
        
        # Execute move
        board.move_piece(start, end)
        game.add_move_to_history(move)
        
        # Check game end conditions
        opponent_color = current_color.opposite()
        
        if MoveValidator.is_checkmate(board, opponent_color):
            winner_state = CheckmateState(current_color)
            game.set_state(winner_state)
            print(f"Checkmate! {current_color.value} wins!")
            return True
        
        if MoveValidator.is_stalemate(board, opponent_color):
            game.set_state(StalemateState())
            print("Stalemate!")
            return True
        
        if MoveValidator.is_in_check(board, opponent_color):
            print(f"{opponent_color.value} is in check!")
        
        # Switch players
        game.switch_player()
        return True
    
    def get_status(self) -> GameStatus:
        return GameStatus.IN_PROGRESS


class CheckmateState(GameState):
    """State when a player is checkmated"""
    
    def __init__(self, winner_color: PieceColor):
        self._winner_color = winner_color
    
    def make_move(self, game: 'ChessGame', start: Position, end: Position) -> bool:
        print("Game is over. Please start a new game.")
        return False
    
    def get_status(self) -> GameStatus:
        return GameStatus.WHITE_WINS if self._winner_color == PieceColor.WHITE else GameStatus.BLACK_WINS
    
    def get_winner(self) -> PieceColor:
        return self._winner_color


class StalemateState(GameState):
    """State when the game is a stalemate"""
    
    def make_move(self, game: 'ChessGame', start: Position, end: Position) -> bool:
        print("Game is over. Please start a new game.")
        return False
    
    def get_status(self) -> GameStatus:
        return GameStatus.STALEMATE


class DrawState(GameState):
    """State when the game is a draw (by agreement or other rules)"""
    
    def make_move(self, game: 'ChessGame', start: Position, end: Position) -> bool:
        print("Game is over. Please start a new game.")
        return False
    
    def get_status(self) -> GameStatus:
        return GameStatus.DRAW


# ==================== Player ====================

class Player:
    """Represents a player in the game"""
    
    def __init__(self, name: str, color: PieceColor):
        self._name = name
        self._color = color
    
    def get_name(self) -> str:
        return self._name
    
    def get_color(self) -> PieceColor:
        return self._color
    
    def __repr__(self) -> str:
        return f"{self._name} ({self._color.value})"


# ==================== Main Game Class ====================

class ChessGame:
    """Main chess game controller"""
    
    def __init__(self, player1: Player, player2: Player, board: Optional[Board] = None):
        if player1.get_color() == player2.get_color():
            raise ValueError("Players must have different colors")
        
        # Ensure white goes first
        if player1.get_color() == PieceColor.WHITE:
            self._players = [player1, player2]
        else:
            self._players = [player2, player1]
        
        self._board = board if board else BoardFactory.create_standard_board()
        self._current_player_index = 0
        self._state: GameState = InProgressState()
        self._move_history: List[Move] = []
    
    def get_board(self) -> Board:
        return self._board
    
    def get_current_player(self) -> Player:
        return self._players[self._current_player_index]
    
    def get_current_player_color(self) -> PieceColor:
        return self.get_current_player().get_color()
    
    def switch_player(self) -> None:
        self._current_player_index = 1 - self._current_player_index
    
    def set_state(self, state: GameState) -> None:
        self._state = state
    
    def get_status(self) -> GameStatus:
        return self._state.get_status()
    
    def add_move_to_history(self, move: Move) -> None:
        self._move_history.append(move)
    
    def get_move_history(self) -> List[Move]:
        return self._move_history.copy()
    
    def make_move(self, start: Position, end: Position) -> bool:
        """
        Make a move from start to end position.
        Returns True if the move was successful, False otherwise.
        """
        return self._state.make_move(self, start, end)
    
    def make_move_notation(self, start_notation: str, end_notation: str) -> bool:
        """Make a move using chess notation (e.g., 'e2', 'e4')"""
        start = Position.from_chess_notation(start_notation)
        end = Position.from_chess_notation(end_notation)
        return self.make_move(start, end)
    
    def display_board(self) -> None:
        self._board.display()
    
    def is_game_over(self) -> bool:
        return self.get_status() != GameStatus.IN_PROGRESS
    
    def offer_draw(self) -> None:
        """Allow players to agree to a draw"""
        if not self.is_game_over():
            self.set_state(DrawState())
            print("Game ended in a draw by agreement.")
    
    def resign(self, player: Player) -> None:
        """Allow a player to resign"""
        if not self.is_game_over():
            winner_color = player.get_color().opposite()
            self.set_state(CheckmateState(winner_color))
            print(f"{player} has resigned. {winner_color.value} wins!")


# ==================== Game Factory ====================

class GameFactory:
    """Factory for creating different game configurations"""
    
    @staticmethod
    def create_standard_game(player1_name: str = "Player 1", 
                            player2_name: str = "Player 2") -> ChessGame:
        """Create a standard chess game"""
        player1 = Player(player1_name, PieceColor.WHITE)
        player2 = Player(player2_name, PieceColor.BLACK)
        board = BoardFactory.create_standard_board()
        return ChessGame(player1, player2, board)
    
    @staticmethod
    def create_custom_game(player1_name: str, player1_color: PieceColor,
                          player2_name: str, board: Optional[Board] = None) -> ChessGame:
        """Create a custom chess game"""
        player1 = Player(player1_name, player1_color)
        player2 = Player(player2_name, player1_color.opposite())
        
        if board is None:
            board = BoardFactory.create_standard_board()
        
        return ChessGame(player1, player2, board)


# ==================== Demo Usage ====================

def main():
    """Demo the chess game"""
    print("=== Chess Game ===\n")
    
    # Create a standard game
    game = GameFactory.create_standard_game("Alice", "Bob")
    
    print(f"Current player: {game.get_current_player()}")
    game.display_board()
    
    # Example moves using chess notation
    moves = [
        ("e2", "e4"),   # White pawn
        ("e7", "e5"),   # Black pawn
        ("g1", "f3"),   # White knight
        ("b8", "c6"),   # Black knight
        ("f1", "c4"),   # White bishop
        ("f8", "c5"),   # Black bishop
        ("b2", "b4"),   # White pawn (Evans Gambit)
    ]
    
    for start, end in moves:
        print(f"\n{game.get_current_player()} moves: {start} -> {end}")
        success = game.make_move_notation(start, end)
        
        if success:
            game.display_board()
        
        if game.is_game_over():
            print(f"\nGame Over! Status: {game.get_status().value}")
            break
    
    # Display move history
    print("\n=== Move History ===")
    for i, move in enumerate(game.get_move_history(), 1):
        print(f"{i}. {move}")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Strategy Pattern - For piece movement logic

# Each piece type has its own MoveStrategy (KingMoveStrategy, QueenMoveStrategy, etc.)
# Easily extensible for variants or new piece types
# Separates movement logic from piece representation


# Factory Pattern - For object creation

# PieceFactory: Creates pieces with appropriate strategies
# BoardFactory: Creates standard or custom board setups
# GameFactory: Creates complete game configurations


# State Pattern - For game flow management

# InProgressState, CheckmateState, StalemateState, DrawState
# Cleanly handles transitions between game states
# Prevents invalid operations after game ends



# Additional Design Choices:

# Position Value Object: Encapsulates board coordinates with chess notation support
# Move Class: Represents moves as first-class objects (useful for move history, undo, etc.)
# MoveValidator: Centralized validation logic including check/checkmate detection
# Separation of Concerns: Board manages piece positions, Validator handles rules, Game orchestrates flow

# What's Simplified (for interview scope):

# Castling, en passant not fully implemented (marked with TODOs)
# No timer/clock system
# No advanced rules (50-move rule, threefold repetition)
# Board cloning is simplified (would use proper deep copy in production)

# This design is extensible, testable, and demonstrates solid OOD principles without forcing unnecessary patterns. Good luck with your interviews!

# Stalemate (specific condition)

# The player whose turn it is has no legal moves
# Their king is NOT in check
# This is an automatic draw

# Example: Your king can't move anywhere without going into check, and you have no other pieces that can move.
# Draw (general category)
# A draw can happen through multiple ways:

# Stalemate (as described above)
# Mutual agreement - Both players agree to draw
# Insufficient material - Neither side has enough pieces to checkmate (e.g., King vs King)
# Threefold repetition - Same position occurs three times
# 50-move rule - 50 moves without pawn movement or capture
# Perpetual check - One side keeps checking, forcing a draw

# In My Code:
# I separated them because they require different handling:
# pythonclass StalemateState(GameState):
#     """Automatic draw - no legal moves, not in check"""
    
# class DrawState(GameState):  
#     """Draw by agreement or other rules"""
# Stalemate is detected automatically by the game engine (checking if player has no legal moves while not in check), while Draw is typically initiated by players (calling game.offer_draw() or through rule violations).
# In a complete implementation, you'd have additional draw detection methods in MoveValidator for insufficient material, repetition, etc., which would also transition to DrawState.


# My Board Coordinate System
# In my implementation, the board uses array indices where:

# Row 0 = top of the board = Black's back rank (where Black starts)
# Row 7 = bottom of the board = White's back rank (where White starts)

# Row 0:  ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜  (Black pieces)
# Row 1:  ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟  (Black pawns)
# ...
# Row 6:  ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙  (White pawns)
# Row 7:  ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖  (White pieces)
# Why the Direction Values?
# White pawns (start at row 6):

# Need to move UP the board (toward row 0)
# So direction = -1 (decreasing row numbers)
# Start row = 6

# Black pawns (start at row 1):

# Need to move DOWN the board (toward row 7)
# So direction = +1 (increasing row numbers)
# Start row = 1

# Example:
# python# White pawn at row 6, col 4 (e2 in chess notation)
# forward_one = Position(6 + (-1), 4)  # = Position(5, 4) ✓ moves up
# forward_two = Position(6 + (-2), 4)  # = Position(4, 4) ✓ moves up 2

# # Black pawn at row 1, col 4 (e7 in chess notation)
# forward_one = Position(1 + (1), 4)   # = Position(2, 4) ✓ moves down
# forward_two = Position(1 + (2), 4)   # = Position(3, 4) ✓ moves down 2
# Chess Notation Mapping
# Notice in the display() method:
# pythonprint(f"{8-i} ", end="")  # Row labels: 8, 7, 6, 5, 4, 3, 2, 1
# This maps:

# Row 0 → displays as "8" (Black's back rank)
# Row 7 → displays as "1" (White's back rank)

# So it matches standard chess notation where White starts on ranks 1-2 and Black on ranks 7-8!
