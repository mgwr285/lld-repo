from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional


# ==================== Enums ====================

class PlayerSymbol(Enum):
    """Represents player symbols"""
    X = "X"
    O = "O"
    
    def __str__(self):
        return self.value


class GameStatus(Enum):
    """Represents the current state of the game"""
    IN_PROGRESS = "IN_PROGRESS"
    X_WINS = "X_WINS"
    O_WINS = "O_WINS"
    DRAW = "DRAW"


# ==================== Core Models ====================


class Board:
    """Represents the game board"""
    
    def __init__(self, size: int = 3):
        if size < 3:
            raise ValueError("Board size must be at least 3")
        self._size = size
        self._grid: List[List[Optional[PlayerSymbol]]] = [[None for _ in range(size)] for _ in range(size)]
    
    def get_size(self) -> int:
        return self._size
    
    def is_valid_position(self, row: int, col: int) -> bool:
        return 0 <= row < self._size and 0 <= col < self._size
    
    def is_cell_empty(self, row: int, col: int) -> bool:
        if not self.is_valid_position(row, col):
            return False
        return self._grid[row][col] is None
    
    def mark_cell(self, row: int, col: int, symbol: PlayerSymbol) -> None:
        if not self.is_valid_position(row, col):
            raise ValueError(f"Invalid position: ({row}, {col})")
        if not self.is_cell_empty(row, col):
            raise ValueError("Cell is already occupied")
        self._grid[row][col] = symbol
    
    def get_symbol(self, row: int, col: int) -> Optional[PlayerSymbol]:
        if not self.is_valid_position(row, col):
            raise ValueError(f"Invalid position: ({row}, {col})")
        return self._grid[row][col]
    
    def is_full(self) -> bool:
        return all(cell is not None for row in self._grid for cell in row)
    
    def reset(self) -> None:
        self._grid = [[None for _ in range(self._size)] for _ in range(self._size)]
    
    def display(self) -> None:
        print("\n" + "  " + " ".join(str(i) for i in range(self._size)))
        for i, row in enumerate(self._grid):
            print(f"{i} " + "|".join(cell.value if cell else " " for cell in row))
            if i < self._size - 1:
                print("  " + "-" * (self._size * 2 - 1))
        print()


class Player:
    """Represents a player in the game"""
    
    def __init__(self, name: str, symbol: PlayerSymbol):
        self._name = name
        self._symbol = symbol
    
    def get_name(self) -> str:
        return self._name
    
    def get_symbol(self) -> PlayerSymbol:
        return self._symbol
    
    def __str__(self) -> str:
        return f"{self._name} ({self._symbol.value})"


# ==================== Win Detection ====================

class WinDetector:
    """Detects win conditions by checking rows, columns, and diagonals"""
    
    @staticmethod
    def check_win(board: Board, symbol: PlayerSymbol) -> bool:
        """Check if the given symbol has won the game"""
        return (WinDetector._check_rows(board, symbol) or
                WinDetector._check_columns(board, symbol) or
                WinDetector._check_diagonals(board, symbol))
    
    @staticmethod
    def _check_rows(board: Board, symbol: PlayerSymbol) -> bool:
        """Check for a win in any row"""
        size = board.get_size()
        for row in range(size):
            if all(board.get_symbol(row, col) == symbol for col in range(size)):
                return True
        return False
    
    @staticmethod
    def _check_columns(board: Board, symbol: PlayerSymbol) -> bool:
        """Check for a win in any column"""
        size = board.get_size()
        for col in range(size):
            if all(board.get_symbol(row, col) == symbol for row in range(size)):
                return True
        return False
    
    @staticmethod
    def _check_diagonals(board: Board, symbol: PlayerSymbol) -> bool:
        """Check for a win in either diagonal"""
        size = board.get_size()
        
        # Check main diagonal (top-left to bottom-right)
        if all(board.get_symbol(i, i) == symbol for i in range(size)):
            return True
        
        # Check anti-diagonal (top-right to bottom-left)
        if all(board.get_symbol(i, size - 1 - i) == symbol for i in range(size)):
            return True
        
        return False


# ==================== Move Validator ====================

class MoveValidator:
    """Validates moves and detects game end conditions"""
    
    @staticmethod
    def is_valid_move(board: Board, row: int, col: int) -> tuple[bool, str]:
        """
        Validate if a move is legal.
        Returns (is_valid, error_message)
        """
        if not board.is_valid_position(row, col):
            return False, "Position out of bounds"
        
        if not board.is_cell_empty(row, col):
            return False, "Cell already occupied"
        
        return True, ""
    
    @staticmethod
    def has_winner(board: Board, symbol: PlayerSymbol) -> bool:
        """Check if the given player has won"""
        return WinDetector.check_win(board, symbol)
    
    @staticmethod
    def is_draw(board: Board) -> bool:
        """Check if the game is a draw (board full, no winner)"""
        return board.is_full()


# ==================== Observer Pattern: Game Event Listeners ====================

class GameEventListener(ABC):
    """Abstract base class for game event observers"""
    
    @abstractmethod
    def on_move_made(self, player: Player, row: int, col: int) -> None:
        pass
    
    @abstractmethod
    def on_game_over(self, status: GameStatus, winner: Optional[Player]) -> None:
        pass
    
    @abstractmethod
    def on_invalid_move(self, player: Player, row: int, col: int, reason: str) -> None:
        pass


class ConsoleLogger(GameEventListener):
    """Logs game events to the console"""
    
    def on_move_made(self, player: Player, row: int, col: int) -> None:
        print(f"[LOG] {player} made a move at ({row}, {col})")
    
    def on_game_over(self, status: GameStatus, winner: Optional[Player]) -> None:
        if winner:
            print(f"[LOG] Game Over! {winner} wins!")
        else:
            print(f"[LOG] Game Over! It's a draw!")
    
    def on_invalid_move(self, player: Player, row: int, col: int, reason: str) -> None:
        print(f"[LOG] Invalid move by {player} at ({row}, {col}): {reason}")


class GameStatistics(GameEventListener):
    """Tracks game statistics"""
    
    def __init__(self):
        self._total_moves = 0
        self._invalid_moves = 0
    
    def on_move_made(self, player: Player, row: int, col: int) -> None:
        self._total_moves += 1
    
    def on_game_over(self, status: GameStatus, winner: Optional[Player]) -> None:
        print(f"[STATS] Total moves: {self._total_moves}, Invalid moves: {self._invalid_moves}")
    
    def on_invalid_move(self, player: Player, row: int, col: int, reason: str) -> None:
        self._invalid_moves += 1
    
    def get_total_moves(self) -> int:
        return self._total_moves


# ==================== State Pattern: Game States ====================

class GameState(ABC):
    """Abstract base class for game states"""
    
    @abstractmethod
    def make_move(self, game: 'TicTacToeGame', row: int, col: int) -> None:
        pass
    
    @abstractmethod
    def get_status(self) -> GameStatus:
        pass


class InProgressState(GameState):
    """State when the game is in progress"""
    
    def make_move(self, game: 'TicTacToeGame', row: int, col: int) -> None:
        current_player = game.get_current_player()
        board = game.get_board()
        
        # Validate move using MoveValidator
        is_valid, error_message = MoveValidator.is_valid_move(board, row, col)
        if not is_valid:
            game.notify_invalid_move(current_player, row, col, error_message)
            return
        
        # Make the move
        board.mark_cell(row, col, current_player.get_symbol())
        game.notify_move_made(current_player, row, col)
        
        # Check for win or draw using MoveValidator
        if MoveValidator.has_winner(board, current_player.get_symbol()):
            new_state = WonState(current_player)
            game.set_state(new_state)
            game.notify_game_over(new_state.get_status(), current_player)
        elif MoveValidator.is_draw(board):
            new_state = DrawState()
            game.set_state(new_state)
            game.notify_game_over(new_state.get_status(), None)
        else:
            # Switch to next player
            game.switch_player()
    
    def get_status(self) -> GameStatus:
        return GameStatus.IN_PROGRESS


class WonState(GameState):
    """State when a player has won"""
    
    def __init__(self, winner: Player):
        self._winner = winner
    
    def make_move(self, game: 'TicTacToeGame', row: int, col: int) -> None:
        print("Game is already over. Please start a new game.")
    
    def get_status(self) -> GameStatus:
        if self._winner.get_symbol() == PlayerSymbol.X:
            return GameStatus.X_WINS
        return GameStatus.O_WINS
    
    def get_winner(self) -> Player:
        return self._winner


class DrawState(GameState):
    """State when the game ends in a draw"""
    
    def make_move(self, game: 'TicTacToeGame', row: int, col: int) -> None:
        print("Game is already over. Please start a new game.")
    
    def get_status(self) -> GameStatus:
        return GameStatus.DRAW


# ==================== Main Game Class ====================

class TicTacToeGame:
    """Main game controller that orchestrates the game flow"""
    
    def __init__(self, player1: Player, player2: Player, board_size: int = 3):
        if player1.get_symbol() == player2.get_symbol():
            raise ValueError("Players must have different symbols")
        
        self._board = Board(board_size)
        self._players = [player1, player2]
        self._current_player_index = 0
        self._state: GameState = InProgressState()
        self._listeners: List[GameEventListener] = []
    
    def add_listener(self, listener: GameEventListener) -> None:
        self._listeners.append(listener)
    
    def remove_listener(self, listener: GameEventListener) -> None:
        self._listeners.remove(listener)
    
    def notify_move_made(self, player: Player, row: int, col: int) -> None:
        for listener in self._listeners:
            listener.on_move_made(player, row, col)
    
    def notify_game_over(self, status: GameStatus, winner: Optional[Player]) -> None:
        for listener in self._listeners:
            listener.on_game_over(status, winner)
    
    def notify_invalid_move(self, player: Player, row: int, col: int, reason: str) -> None:
        for listener in self._listeners:
            listener.on_invalid_move(player, row, col, reason)
    
    def get_board(self) -> Board:
        return self._board
    
    def get_current_player(self) -> Player:
        return self._players[self._current_player_index]
    
    def switch_player(self) -> None:
        self._current_player_index = 1 - self._current_player_index
    
    def set_state(self, state: GameState) -> None:
        self._state = state
    
    def get_status(self) -> GameStatus:
        return self._state.get_status()
    
    def make_move(self, row: int, col: int) -> bool:
        """
        Make a move at the specified position.
        Returns True if the move was successful, False otherwise.
        """
        initial_status = self.get_status()
        self._state.make_move(self, row, col)
        return self.get_status() == GameStatus.IN_PROGRESS or self.get_status() != initial_status
    
    def display_board(self) -> None:
        self._board.display()
    
    def reset(self) -> None:
        """Reset the game to start a new round"""
        self._board.reset()
        self._current_player_index = 0
        self._state = InProgressState()
        print("Game has been reset!")
    
    def is_game_over(self) -> bool:
        return self.get_status() != GameStatus.IN_PROGRESS


# ==================== Factory Pattern: Game Factory ====================

class GameFactory:
    """Factory for creating different game configurations"""
    
    @staticmethod
    def create_standard_game(player1_name: str = "Player 1", 
                            player2_name: str = "Player 2") -> TicTacToeGame:
        """Create a standard 3x3 Tic Tac Toe game"""
        player1 = Player(player1_name, PlayerSymbol.X)
        player2 = Player(player2_name, PlayerSymbol.O)
        game = TicTacToeGame(player1, player2, board_size=3)
        
        # Add default listeners
        game.add_listener(ConsoleLogger())
        game.add_listener(GameStatistics())
        
        return game
    
    @staticmethod
    def create_custom_game(player1_name: str, player2_name: str, 
                          board_size: int, with_logging: bool = True) -> TicTacToeGame:
        """Create a custom Tic Tac Toe game with specified board size"""
        player1 = Player(player1_name, PlayerSymbol.X)
        player2 = Player(player2_name, PlayerSymbol.O)
        game = TicTacToeGame(player1, player2, board_size=board_size)
        
        if with_logging:
            game.add_listener(ConsoleLogger())
            game.add_listener(GameStatistics())
        
        return game


# ==================== Demo Usage ====================

def main():
    """Demo the Tic Tac Toe game"""
    print("=== Tic Tac Toe Game ===\n")
    
    # Create a game using the factory
    game = GameFactory.create_standard_game("Alice", "Bob")
    
    print(f"Current player: {game.get_current_player()}")
    game.display_board()
    
    # Simulate some moves
    moves = [
        (0, 0),  # Alice (X)
        (1, 1),  # Bob (O)
        (0, 1),  # Alice (X)
        (2, 2),  # Bob (O)
        (0, 2),  # Alice (X) - wins!
    ]
    
    for row, col in moves:
        print(f"\n{game.get_current_player()} is making a move at ({row}, {col})")
        game.make_move(row, col)
        game.display_board()
        
        if game.is_game_over():
            print(f"\nFinal Status: {game.get_status().value}")
            break
    
    # Try to make a move after game is over
    print("\nTrying to make a move after game over:")
    game.make_move(1, 0)
    
    # Reset and play again
    print("\n--- Starting a new game ---")
    game.reset()
    game.display_board()


if __name__ == "__main__":
    main()
