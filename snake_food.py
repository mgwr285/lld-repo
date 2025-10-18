from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Set, Deque
from collections import deque
from random import randint
import time


# ==================== Enums ====================

class Direction(Enum):
    """Represents movement directions"""
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)
    
    def get_opposite(self) -> 'Direction':
        """Get the opposite direction"""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        return opposites[self]
    
    def is_opposite(self, other: 'Direction') -> bool:
        """Check if this direction is opposite to another"""
        return self.get_opposite() == other


class GameStatus(Enum):
    """Represents the current state of the game"""
    IN_PROGRESS = "IN_PROGRESS"
    GAME_OVER = "GAME_OVER"
    WON = "WON"


# ==================== Core Models ====================

class Position:
    """Represents a position on the board"""
    
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Position):
            return False
        return self.row == other.row and self.col == other.col
    
    def __hash__(self) -> int:
        return hash((self.row, self.col))
    
    def __repr__(self) -> str:
        return f"({self.row}, {self.col})"
    
    def move(self, direction: Direction) -> 'Position':
        """Get a new position by moving in a direction"""
        d_row, d_col = direction.value
        return Position(self.row + d_row, self.col + d_col)


class Snake:
    """Represents the snake using a deque for efficient head/tail operations"""
    
    def __init__(self, starting_positions: List[Position]):
        if not starting_positions:
            raise ValueError("Snake must have at least one position")
        
        # Deque for O(1) append/pop operations
        self._body: Deque[Position] = deque(starting_positions)
        self._direction: Direction = Direction.RIGHT
        self._grow_pending = 0  # Number of segments to grow
    
    def get_head(self) -> Position:
        """Get the head position (front of deque)"""
        return self._body[0]
    
    def get_body(self) -> List[Position]:
        """Get all body positions"""
        return list(self._body)
    
    def get_body_set(self) -> Set[Position]:
        """Get body positions as a set for O(1) collision detection"""
        return set(self._body)
    
    def get_length(self) -> int:
        """Get the snake's length"""
        return len(self._body)
    
    def get_direction(self) -> Direction:
        """Get current direction"""
        return self._direction
    
    def set_direction(self, direction: Direction) -> None:
        """Set direction (with validation to prevent 180-degree turns)"""
        if not direction.is_opposite(self._direction):
            self._direction = direction
    
    def move(self, new_head: Position) -> Optional[Position]:
        """
        Move the snake by adding new head and removing tail.
        Returns the removed tail position, or None if snake is growing.
        """
        self._body.appendleft(new_head)  # Add new head at front
        
        if self._grow_pending > 0:
            self._grow_pending -= 1
            return None  # Don't remove tail when growing
        else:
            return self._body.pop()  # Remove tail from back
    
    def grow(self, segments: int = 1) -> None:
        """Schedule growth for the next N moves"""
        self._grow_pending += segments


class Food:
    """Represents food on the board"""
    
    def __init__(self, position: Position, points: int = 1, growth: int = 1):
        self._position = position
        self._points = points
        self._growth = growth
    
    def get_position(self) -> Position:
        return self._position
    
    def get_points(self) -> int:
        return self._points
    
    def get_growth(self) -> int:
        return self._growth


class Board:
    """Represents the game board"""
    
    def __init__(self, width: int, height: int):
        if width < 5 or height < 5:
            raise ValueError("Board must be at least 5x5")
        
        self._width = width
        self._height = height
    
    def get_width(self) -> int:
        return self._width
    
    def get_height(self) -> int:
        return self._height
    
    def is_valid_position(self, position: Position) -> bool:
        """Check if position is within board boundaries"""
        return 0 <= position.row < self._height and 0 <= position.col < self._width
    
    def get_empty_positions(self, occupied: Set[Position]) -> List[Position]:
        """Get all empty positions not in the occupied set"""
        empty = []
        for row in range(self._height):
            for col in range(self._width):
                pos = Position(row, col)
                if pos not in occupied:
                    empty.append(pos)
        return empty
    
    def display(self, snake: Snake, food: Optional[Food]) -> None:
        """Display the board with snake and food"""
        snake_body = snake.get_body_set()
        snake_head = snake.get_head()
        food_pos = food.get_position() if food else None
        
        # Top border
        print("\n" + "+" + "-" * (self._width * 2) + "+")
        
        for row in range(self._height):
            print("|", end="")
            for col in range(self._width):
                pos = Position(row, col)
                
                if pos == snake_head:
                    print("H ", end="")
                elif pos in snake_body:
                    print("S ", end="")
                elif pos == food_pos:
                    print("F ", end="")
                else:
                    print(". ", end="")
            print("|")
        
        # Bottom border
        print("+" + "-" * (self._width * 2) + "+\n")


# ==================== Strategy Pattern: Food Placement Strategies ====================

class FoodPlacementStrategy(ABC):
    """Abstract strategy for placing food on the board"""
    
    @abstractmethod
    def place_food(self, board: Board, occupied_positions: Set[Position]) -> Optional[Position]:
        """Place food on the board, return position or None if no space"""
        pass


class RandomPlacementStrategy(FoodPlacementStrategy):
    """Place food randomly on empty cells"""
    
    def place_food(self, board: Board, occupied_positions: Set[Position]) -> Optional[Position]:
        empty_positions = board.get_empty_positions(occupied_positions)
        
        if not empty_positions:
            return None
        
        # Random selection
        index = randint(0, len(empty_positions) - 1)
        return empty_positions[index]


# ==================== State Pattern: Game States ====================

class GameState(ABC):
    """Abstract base class for game states"""
    
    @abstractmethod
    def update(self, game: 'SnakeGame') -> None:
        """Update game state"""
        pass
    
    @abstractmethod
    def handle_direction_change(self, game: 'SnakeGame', direction: Direction) -> None:
        """Handle direction change input"""
        pass
    
    @abstractmethod
    def get_status(self) -> GameStatus:
        """Get current game status"""
        pass


class PlayingState(GameState):
    """State when game is actively being played"""
    
    def update(self, game: 'SnakeGame') -> None:
        snake = game.get_snake()
        board = game.get_board()
        
        # Calculate new head position
        current_head = snake.get_head()
        new_head = current_head.move(snake.get_direction())
        
        # Check wall collision
        if not board.is_valid_position(new_head):
            game.set_state(GameOverState("Hit the wall!"))
            return
        
        # Check self collision (before moving)
        if new_head in snake.get_body_set():
            game.set_state(GameOverState("Hit yourself!"))
            return
        
        # Move snake
        snake.move(new_head)
        
        # Check food collision
        food = game.get_food()
        if food and new_head == food.get_position():
            # Eat food
            snake.grow(food.get_growth())
            game.add_score(food.get_points())
            game.spawn_food()
            
            # Check win condition (filled entire board)
            if snake.get_length() >= board.get_width() * board.get_height():
                game.set_state(WonState())
    
    def handle_direction_change(self, game: 'SnakeGame', direction: Direction) -> None:
        game.get_snake().set_direction(direction)
    
    def get_status(self) -> GameStatus:
        return GameStatus.IN_PROGRESS


class GameOverState(GameState):
    """State when game is over"""
    
    def __init__(self, reason: str = "Game Over"):
        self._reason = reason
    
    def update(self, game: 'SnakeGame') -> None:
        # No updates when game over
        pass
    
    def handle_direction_change(self, game: 'SnakeGame', direction: Direction) -> None:
        # Can't change direction when game over
        pass
    
    def get_status(self) -> GameStatus:
        return GameStatus.GAME_OVER
    
    def get_reason(self) -> str:
        return self._reason


class WonState(GameState):
    """State when player wins (fills entire board)"""
    
    def update(self, game: 'SnakeGame') -> None:
        pass
    
    def handle_direction_change(self, game: 'SnakeGame', direction: Direction) -> None:
        pass
    
    def get_status(self) -> GameStatus:
        return GameStatus.WON


# ==================== Main Game Class ====================

class SnakeGame:
    """Main game controller"""
    
    def __init__(self, board: Board, snake: Snake, 
                 food_strategy: FoodPlacementStrategy):
        self._board = board
        self._snake = snake
        self._food: Optional[Food] = None
        self._food_strategy = food_strategy
        self._state: GameState = PlayingState()
        self._score = 0
        self._moves_count = 0
        
        # Spawn initial food
        self.spawn_food()
    
    def get_board(self) -> Board:
        return self._board
    
    def get_snake(self) -> Snake:
        return self._snake
    
    def get_food(self) -> Optional[Food]:
        return self._food
    
    def get_score(self) -> int:
        return self._score
    
    def add_score(self, points: int) -> None:
        self._score += points
    
    def get_moves_count(self) -> int:
        return self._moves_count
    
    def set_state(self, state: GameState) -> None:
        self._state = state
    
    def get_status(self) -> GameStatus:
        return self._state.get_status()
    
    def spawn_food(self) -> None:
        """Spawn food using the placement strategy"""
        occupied = self._snake.get_body_set()
        position = self._food_strategy.place_food(self._board, occupied)
        
        if position:
            self._food = Food(position, points=10, growth=1)
        else:
            self._food = None
    
    def change_direction(self, direction: Direction) -> None:
        """Change snake direction"""
        self._state.handle_direction_change(self, direction)
    
    def update(self) -> None:
        """Update game state (one game tick)"""
        self._state.update(self)
        self._moves_count += 1
    
    def is_game_over(self) -> bool:
        """Check if game is over"""
        status = self.get_status()
        return status == GameStatus.GAME_OVER or status == GameStatus.WON
    
    def display(self) -> None:
        """Display the game state"""
        self._board.display(self._snake, self._food)
        print(f"Score: {self._score} | Length: {self._snake.get_length()} | Moves: {self._moves_count}")
        print(f"Status: {self.get_status().value}")
        
        if isinstance(self._state, GameOverState):
            print(f"Reason: {self._state.get_reason()}")


# ==================== Factory Pattern ====================

class SnakeGameFactory:
    """Factory for creating different game configurations"""
    
    @staticmethod
    def create_standard_game(width: int = 20, height: int = 15) -> SnakeGame:
        """Create a standard snake game"""
        board = Board(width, height)
        
        # Start snake in the middle-left
        start_row = height // 2
        start_col = width // 4
        starting_positions = [
            Position(start_row, start_col),
            Position(start_row, start_col - 1),
            Position(start_row, start_col - 2)
        ]
        snake = Snake(starting_positions)
        
        food_strategy = RandomPlacementStrategy()
        
        return SnakeGame(board, snake, food_strategy)
    
    @staticmethod
    def create_small_game() -> SnakeGame:
        """Create a small game for testing"""
        board = Board(10, 8)
        
        starting_positions = [
            Position(4, 3),
            Position(4, 2),
            Position(4, 1)
        ]
        snake = Snake(starting_positions)
        
        food_strategy = RandomPlacementStrategy()
        
        return SnakeGame(board, snake, food_strategy)


# ==================== Demo Usage ====================

def main():
    """Demo the snake game"""
    print("=== Snake Game ===\n")
    
    # Create a standard game
    game = SnakeGameFactory.create_standard_game(width=15, height=10)
    
    # Show initial state
    print("Initial Game State:")
    game.display()
    
    # Simulate some moves
    print("\nSimulating moves...\n")
    
    moves = [
        Direction.RIGHT,
        Direction.RIGHT,
        Direction.RIGHT,
        Direction.DOWN,
        Direction.DOWN,
        Direction.LEFT,
        Direction.LEFT,
        Direction.LEFT,
        Direction.DOWN,
        Direction.RIGHT,
        Direction.RIGHT,
        Direction.DOWN,
        Direction.RIGHT,
        Direction.RIGHT,
        Direction.UP,
        Direction.UP,
    ]
    
    for direction in moves:
        if game.is_game_over():
            break
        
        game.change_direction(direction)
        game.update()
        game.display()
        time.sleep(0.3)
    
    print(f"\n=== Final Stats ===")
    print(f"Score: {game.get_score()}")
    print(f"Snake Length: {game.get_snake().get_length()}")
    print(f"Total Moves: {game.get_moves_count()}")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Core Data Structure:

# Snake as Deque - Perfect for O(1) operations:

# appendleft() - add new head
# pop() - remove tail
# This is the critical insight you had!



# Design Patterns Used:

# Strategy Pattern - Two uses:

# Food Placement Strategies: Random vs Corner placement (extensible for difficulty levels)
# Collision Handlers: Standard vs Wrap-around walls


# State Pattern - Game flow:

# PlayingState, PausedState, GameOverState, WonState
# Clean separation of behavior in different states


# Factory Pattern - Game creation:

# Standard game, game with obstacles, small test game
# Easy to create different configurations



# Additional Design Choices:

# Position Value Object: Immutable position with movement logic
# Direction Enum: Built-in opposite direction validation (prevents 180° turns)
# Separation of Concerns: Board manages space, Snake manages body, Game orchestrates
# Growth Queue: Snake doesn't grow immediately - it schedules growth for next N moves

# Extensions You Could Add:

# Different food types (power-ups, speed boost, etc.)
# Multiple snakes (multiplayer)
# AI opponent using pathfinding
# Speed increase as score grows
# Undo/replay using command pattern with move history

# Key Simplifications Made:

# Removed Paused State - Only PlayingState, GameOverState, and WonState
# Removed Obstacles - No obstacle tracking or collision detection
# Removed Collision Handlers - Walls always end the game (no wrap-around)
# Simplified Board - No obstacle methods

# What Remains:
# ✅ Snake as Deque - The core insight with O(1) operations
# ✅ Strategy Pattern - Food placement (easily extensible)
# ✅ State Pattern - Clean game state management
# ✅ Factory Pattern - Easy game creation
# ✅ Clean separation - Board, Snake, Game responsibilities are clear
# This is much cleaner and focused on the essentials for an interview. The deque-based snake implementation is the star of the show, and the design patterns support it without overcomplicating things!
