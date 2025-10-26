from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass
import random


# ==================== Enums ====================

class Suit(Enum):
    """Card suits"""
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"
    
    def is_red(self) -> bool:
        return self in [Suit.HEARTS, Suit.DIAMONDS]
    
    def is_black(self) -> bool:
        return not self.is_red()


class Rank(Enum):
    """Card ranks"""
    ACE = (1, "A")
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "10")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    
    def __init__(self, value: int, display: str):
        self._value = value
        self._display = display
    
    @property
    def value(self) -> int:
        return self._value
    
    @property
    def display(self) -> str:
        return self._display


class GameStatus(Enum):
    """Represents the current state of the game"""
    IN_PROGRESS = "IN_PROGRESS"
    WON = "WON"
    STUCK = "STUCK"


# ==================== Card ====================

@dataclass
class Card:
    """Represents a playing card"""
    suit: Suit
    rank: Rank
    face_up: bool = False
    
    def flip(self) -> None:
        """Flip the card"""
        self.face_up = not self.face_up
    
    def is_opposite_color(self, other: 'Card') -> bool:
        """Check if card is opposite color"""
        return (self.suit.is_red() and other.suit.is_black()) or \
               (self.suit.is_black() and other.suit.is_red())
    
    def is_one_rank_lower(self, other: 'Card') -> bool:
        """Check if this card is one rank lower than other"""
        return self.rank.value == other.rank.value - 1
    
    def __repr__(self) -> str:
        if not self.face_up:
            return "[??]"
        return f"[{self.rank.display}{self.suit.value}]"


# ==================== Piles ====================

class Pile:
    """Base class for card piles"""
    
    def __init__(self):
        self._cards: List[Card] = []
    
    def add_card(self, card: Card) -> None:
        """Add a card to the pile"""
        self._cards.append(card)
    
    def remove_card(self) -> Optional[Card]:
        """Remove and return top card"""
        if self._cards:
            return self._cards.pop()
        return None
    
    def peek(self) -> Optional[Card]:
        """View top card without removing"""
        if self._cards:
            return self._cards[-1]
        return None
    
    def get_cards(self) -> List[Card]:
        """Get all cards"""
        return self._cards.copy()
    
    def is_empty(self) -> bool:
        """Check if pile is empty"""
        return len(self._cards) == 0
    
    def size(self) -> int:
        """Get number of cards"""
        return len(self._cards)


class StockPile(Pile):
    """Stock pile (draw pile)"""
    
    def __init__(self, cards: List[Card]):
        super().__init__()
        self._cards = cards
        for card in self._cards:
            card.face_up = False
    
    def draw(self) -> Optional[Card]:
        """Draw a card from stock"""
        card = self.remove_card()
        if card:
            card.flip()
        return card


class WastePile(Pile):
    """Waste pile (discard pile from stock)"""
    
    def can_take_card(self) -> bool:
        """Check if card can be taken from waste"""
        return not self.is_empty()


class FoundationPile(Pile):
    """Foundation pile (goal piles, one per suit)"""
    
    def __init__(self, suit: Suit):
        super().__init__()
        self._suit = suit
    
    def can_add_card(self, card: Card) -> bool:
        """Check if card can be added to foundation"""
        if not card.face_up:
            return False
        
        if card.suit != self._suit:
            return False
        
        if self.is_empty():
            return card.rank == Rank.ACE
        
        top_card = self.peek()
        return card.rank.value == top_card.rank.value + 1


class TableauPile(Pile):
    """Tableau pile (main playing area)"""
    
    def can_add_card(self, card: Card) -> bool:
        """Check if card can be added to tableau"""
        if not card.face_up:
            return False
        
        if self.is_empty():
            return card.rank == Rank.KING
        
        top_card = self.peek()
        return (card.is_opposite_color(top_card) and 
                card.is_one_rank_lower(top_card))
    
    def can_move_cards(self, num_cards: int) -> bool:
        """Check if we can move multiple cards"""
        if num_cards > self.size():
            return False
        
        cards_to_move = self._cards[-num_cards:]
        return all(card.face_up for card in cards_to_move)
    
    def remove_cards(self, num_cards: int) -> List[Card]:
        """Remove multiple cards from top"""
        if not self.can_move_cards(num_cards):
            return []
        
        cards = []
        for _ in range(num_cards):
            cards.insert(0, self._cards.pop())
        return cards
    
    def add_cards(self, cards: List[Card]) -> None:
        """Add multiple cards"""
        self._cards.extend(cards)
    
    def flip_top_card(self) -> None:
        """Flip top card face up if needed"""
        if not self.is_empty():
            top = self.peek()
            if not top.face_up:
                top.flip()


# ==================== Observer Pattern: Game Event Listeners ====================

class GameEventListener(ABC):
    """Abstract base class for game event observers"""
    
    @abstractmethod
    def on_move_made(self, move_description: str, points: int) -> None:
        pass
    
    @abstractmethod
    def on_game_won(self, total_moves: int, final_score: int) -> None:
        pass
    
    @abstractmethod
    def on_invalid_move(self, reason: str) -> None:
        pass
    
    @abstractmethod
    def on_cards_recycled(self) -> None:
        pass


class ConsoleLogger(GameEventListener):
    """Logs game events to the console"""
    
    def on_move_made(self, move_description: str, points: int) -> None:
        print(f"[LOG] {move_description} (+{points} points)")
    
    def on_game_won(self, total_moves: int, final_score: int) -> None:
        print(f"[LOG] 🎉 Game Won! Moves: {total_moves}, Score: {final_score}")
    
    def on_invalid_move(self, reason: str) -> None:
        print(f"[LOG] Invalid move: {reason}")
    
    def on_cards_recycled(self) -> None:
        print("[LOG] Recycled waste pile back to stock")


class GameStatistics(GameEventListener):
    """Tracks game statistics"""
    
    def __init__(self):
        self._total_moves = 0
        self._invalid_moves = 0
        self._recycle_count = 0
    
    def on_move_made(self, move_description: str, points: int) -> None:
        self._total_moves += 1
    
    def on_game_won(self, total_moves: int, final_score: int) -> None:
        print(f"[STATS] Total moves: {self._total_moves}, "
              f"Invalid moves: {self._invalid_moves}, "
              f"Recycles: {self._recycle_count}")
    
    def on_invalid_move(self, reason: str) -> None:
        self._invalid_moves += 1
    
    def on_cards_recycled(self) -> None:
        self._recycle_count += 1
    
    def get_total_moves(self) -> int:
        return self._total_moves


# ==================== State Pattern: Game States ====================

class GameState(ABC):
    """Abstract base class for game states"""
    
    @abstractmethod
    def draw_from_stock(self, game: 'SolitaireGame') -> bool:
        pass
    
    @abstractmethod
    def move_waste_to_foundation(self, game: 'SolitaireGame', suit: Suit) -> bool:
        pass
    
    @abstractmethod
    def move_waste_to_tableau(self, game: 'SolitaireGame', tableau_index: int) -> bool:
        pass
    
    @abstractmethod
    def move_tableau_to_foundation(self, game: 'SolitaireGame', 
                                   tableau_index: int, suit: Suit) -> bool:
        pass
    
    @abstractmethod
    def move_tableau_to_tableau(self, game: 'SolitaireGame', 
                               from_index: int, to_index: int, num_cards: int) -> bool:
        pass
    
    @abstractmethod
    def get_status(self) -> GameStatus:
        pass


class InProgressState(GameState):
    """State when the game is in progress"""
    
    def draw_from_stock(self, game: 'SolitaireGame') -> bool:
        stock = game.get_stock()
        waste = game.get_waste()
        
        if stock.is_empty():
            if waste.is_empty():
                game.notify_invalid_move("No cards to draw")
                return False
            
            # Recycle waste back to stock
            while not waste.is_empty():
                card = waste.remove_card()
                card.face_up = False
                stock.add_card(card)
            
            game.notify_cards_recycled()
            return True
        
        card = stock.draw()
        if card:
            waste.add_card(card)
            game.increment_moves()
            game.notify_move_made(f"Drew {card} from stock", 0)
            self._check_win_condition(game)
            return True
        
        return False
    
    def move_waste_to_foundation(self, game: 'SolitaireGame', suit: Suit) -> bool:
        waste = game.get_waste()
        
        if waste.is_empty():
            game.notify_invalid_move("Waste pile is empty")
            return False
        
        card = waste.peek()
        foundation = game.get_foundation(suit)
        
        if foundation.can_add_card(card):
            waste.remove_card()
            foundation.add_card(card)
            game.increment_moves()
            game.add_score(10)
            game.notify_move_made(f"Moved {card} to {suit.value} foundation", 10)
            self._check_win_condition(game)
            return True
        
        game.notify_invalid_move(f"Cannot move {card} to {suit.value} foundation")
        return False
    
    def move_waste_to_tableau(self, game: 'SolitaireGame', tableau_index: int) -> bool:
        if not 0 <= tableau_index < 7:
            game.notify_invalid_move("Invalid tableau index")
            return False
        
        waste = game.get_waste()
        if waste.is_empty():
            game.notify_invalid_move("Waste pile is empty")
            return False
        
        card = waste.peek()
        tableau = game.get_tableau(tableau_index)
        
        if tableau.can_add_card(card):
            waste.remove_card()
            tableau.add_card(card)
            game.increment_moves()
            game.add_score(5)
            game.notify_move_made(f"Moved {card} to tableau {tableau_index + 1}", 5)
            self._check_win_condition(game)
            return True
        
        game.notify_invalid_move(f"Cannot move {card} to tableau {tableau_index + 1}")
        return False
    
    def move_tableau_to_foundation(self, game: 'SolitaireGame', 
                                   tableau_index: int, suit: Suit) -> bool:
        if not 0 <= tableau_index < 7:
            game.notify_invalid_move("Invalid tableau index")
            return False
        
        tableau = game.get_tableau(tableau_index)
        if tableau.is_empty():
            game.notify_invalid_move(f"Tableau {tableau_index + 1} is empty")
            return False
        
        card = tableau.peek()
        foundation = game.get_foundation(suit)
        
        if foundation.can_add_card(card):
            tableau.remove_card()
            foundation.add_card(card)
            tableau.flip_top_card()
            game.increment_moves()
            game.add_score(10)
            game.notify_move_made(f"Moved {card} to {suit.value} foundation", 10)
            self._check_win_condition(game)
            return True
        
        game.notify_invalid_move(f"Cannot move {card} to {suit.value} foundation")
        return False
    
    def move_tableau_to_tableau(self, game: 'SolitaireGame', 
                               from_index: int, to_index: int, num_cards: int) -> bool:
        if not (0 <= from_index < 7 and 0 <= to_index < 7):
            game.notify_invalid_move("Invalid tableau index")
            return False
        
        if from_index == to_index:
            game.notify_invalid_move("Cannot move to same pile")
            return False
        
        from_tableau = game.get_tableau(from_index)
        to_tableau = game.get_tableau(to_index)
        
        if from_tableau.size() < num_cards:
            game.notify_invalid_move(f"Not enough cards in tableau {from_index + 1}")
            return False
        
        cards = from_tableau.get_cards()[-num_cards:]
        
        if not all(card.face_up for card in cards):
            game.notify_invalid_move("Cannot move face-down cards")
            return False
        
        if not to_tableau.can_add_card(cards[0]):
            game.notify_invalid_move(f"Cannot move to tableau {to_index + 1}")
            return False
        
        moved_cards = from_tableau.remove_cards(num_cards)
        to_tableau.add_cards(moved_cards)
        from_tableau.flip_top_card()
        
        game.increment_moves()
        game.add_score(5)
        game.notify_move_made(
            f"Moved {num_cards} card(s) from tableau {from_index + 1} to tableau {to_index + 1}", 
            5
        )
        self._check_win_condition(game)
        return True
    
    def _check_win_condition(self, game: 'SolitaireGame') -> None:
        """Check if the game has been won"""
        if all(game.get_foundation(suit).size() == 13 for suit in Suit):
            new_state = WonState()
            game.set_state(new_state)
            game.notify_game_won()
    
    def get_status(self) -> GameStatus:
        return GameStatus.IN_PROGRESS


class WonState(GameState):
    """State when the game has been won"""
    
    def draw_from_stock(self, game: 'SolitaireGame') -> bool:
        print("Game is already won! Start a new game.")
        return False
    
    def move_waste_to_foundation(self, game: 'SolitaireGame', suit: Suit) -> bool:
        print("Game is already won! Start a new game.")
        return False
    
    def move_waste_to_tableau(self, game: 'SolitaireGame', tableau_index: int) -> bool:
        print("Game is already won! Start a new game.")
        return False
    
    def move_tableau_to_foundation(self, game: 'SolitaireGame', 
                                   tableau_index: int, suit: Suit) -> bool:
        print("Game is already won! Start a new game.")
        return False
    
    def move_tableau_to_tableau(self, game: 'SolitaireGame', 
                               from_index: int, to_index: int, num_cards: int) -> bool:
        print("Game is already won! Start a new game.")
        return False
    
    def get_status(self) -> GameStatus:
        return GameStatus.WON


class StuckState(GameState):
    """State when the player is stuck (no valid moves)"""
    
    def draw_from_stock(self, game: 'SolitaireGame') -> bool:
        print("Game is stuck! Start a new game.")
        return False
    
    def move_waste_to_foundation(self, game: 'SolitaireGame', suit: Suit) -> bool:
        print("Game is stuck! Start a new game.")
        return False
    
    def move_waste_to_tableau(self, game: 'SolitaireGame', tableau_index: int) -> bool:
        print("Game is stuck! Start a new game.")
        return False
    
    def move_tableau_to_foundation(self, game: 'SolitaireGame', 
                                   tableau_index: int, suit: Suit) -> bool:
        print("Game is stuck! Start a new game.")
        return False
    
    def move_tableau_to_tableau(self, game: 'SolitaireGame', 
                               from_index: int, to_index: int, num_cards: int) -> bool:
        print("Game is stuck! Start a new game.")
        return False
    
    def get_status(self) -> GameStatus:
        return GameStatus.STUCK


# ==================== Main Game Class ====================

class SolitaireGame:
    """
    Klondike Solitaire game implementation with State pattern
    """
    
    def __init__(self):
        # Create and shuffle deck
        self._deck = self._create_deck()
        random.shuffle(self._deck)
        
        # Initialize piles
        self._stock = StockPile([])
        self._waste = WastePile()
        self._foundations = {suit: FoundationPile(suit) for suit in Suit}
        self._tableau = [TableauPile() for _ in range(7)]
        
        # Game state
        self._state: GameState = InProgressState()
        self._moves = 0
        self._score = 0
        self._listeners: List[GameEventListener] = []
        
        # Deal cards
        self._deal()
    
    def _create_deck(self) -> List[Card]:
        """Create a standard 52-card deck"""
        deck = []
        for suit in Suit:
            for rank in Rank:
                deck.append(Card(suit, rank))
        return deck
    
    def _deal(self) -> None:
        """Deal cards to tableau"""
        card_index = 0
        
        for pile_num in range(7):
            for card_num in range(pile_num + 1):
                card = self._deck[card_index]
                if card_num == pile_num:
                    card.face_up = True
                self._tableau[pile_num].add_card(card)
                card_index += 1
        
        for i in range(card_index, len(self._deck)):
            self._stock.add_card(self._deck[i])
    
    # ==================== Observer Methods ====================
    
    def add_listener(self, listener: GameEventListener) -> None:
        self._listeners.append(listener)
    
    def remove_listener(self, listener: GameEventListener) -> None:
        self._listeners.remove(listener)
    
    def notify_move_made(self, move_description: str, points: int) -> None:
        for listener in self._listeners:
            listener.on_move_made(move_description, points)
    
    def notify_game_won(self) -> None:
        for listener in self._listeners:
            listener.on_game_won(self._moves, self._score)
    
    def notify_invalid_move(self, reason: str) -> None:
        for listener in self._listeners:
            listener.on_invalid_move(reason)
    
    def notify_cards_recycled(self) -> None:
        for listener in self._listeners:
            listener.on_cards_recycled()
    
    # ==================== State Management ====================
    
    def set_state(self, state: GameState) -> None:
        self._state = state
    
    def get_status(self) -> GameStatus:
        return self._state.get_status()
    
    def is_game_over(self) -> bool:
        return self.get_status() != GameStatus.IN_PROGRESS
    
    # ==================== Accessors ====================
    
    def get_stock(self) -> StockPile:
        return self._stock
    
    def get_waste(self) -> WastePile:
        return self._waste
    
    def get_foundation(self, suit: Suit) -> FoundationPile:
        return self._foundations[suit]
    
    def get_tableau(self, index: int) -> TableauPile:
        return self._tableau[index]
    
    def increment_moves(self) -> None:
        self._moves += 1
    
    def add_score(self, points: int) -> None:
        self._score += points
    
    def get_score(self) -> int:
        return self._score
    
    def get_moves(self) -> int:
        return self._moves
    
    # ==================== Game Actions (Delegated to State) ====================
    
    def draw_from_stock(self) -> bool:
        """Draw a card from stock to waste"""
        return self._state.draw_from_stock(self)
    
    def move_waste_to_foundation(self, suit: Suit) -> bool:
        """Move top card from waste to foundation"""
        return self._state.move_waste_to_foundation(self, suit)
    
    def move_waste_to_tableau(self, tableau_index: int) -> bool:
        """Move top card from waste to tableau"""
        return self._state.move_waste_to_tableau(self, tableau_index)
    
    def move_tableau_to_foundation(self, tableau_index: int, suit: Suit) -> bool:
        """Move top card from tableau to foundation"""
        return self._state.move_tableau_to_foundation(self, tableau_index, suit)
    
    def move_tableau_to_tableau(self, from_index: int, to_index: int, 
                                num_cards: int = 1) -> bool:
        """Move cards between tableau piles"""
        return self._state.move_tableau_to_tableau(self, from_index, to_index, num_cards)
    
    def auto_move_to_foundation(self) -> int:
        """Automatically move available cards to foundations"""
        moves_made = 0
        
        if not self._waste.is_empty():
            card = self._waste.peek()
            if self._foundations[card.suit].can_add_card(card):
                if self.move_waste_to_foundation(card.suit):
                    moves_made += 1
        
        for i in range(7):
            if not self._tableau[i].is_empty():
                card = self._tableau[i].peek()
                if self._foundations[card.suit].can_add_card(card):
                    if self.move_tableau_to_foundation(i, card.suit):
                        moves_made += 1
        
        return moves_made
    
    # ==================== Display ====================
    
    def display(self) -> None:
        """Display current game state"""
        print("\n" + "="*70)
        print("KLONDIKE SOLITAIRE")
        print("="*70)
        
        stock_display = f"[{self._stock.size()}]" if not self._stock.is_empty() else "[ ]"
        waste_display = str(self._waste.peek()) if not self._waste.is_empty() else "[ ]"
        print(f"\nStock: {stock_display}  Waste: {waste_display}")
        
        print("\nFoundations:")
        for suit in Suit:
            foundation = self._foundations[suit]
            if foundation.is_empty():
                display = f"{suit.value}: [ ]"
            else:
                top = foundation.peek()
                display = f"{suit.value}: {top}"
            print(f"  {display}", end="")
        print()
        
        print("\nTableau:")
        max_height = max(pile.size() for pile in self._tableau)
        
        for row in range(max_height):
            print("  ", end="")
            for pile_num in range(7):
                pile = self._tableau[pile_num]
                if row < pile.size():
                    card = pile.get_cards()[row]
                    print(f"{str(card):6}", end="")
                else:
                    print("      ", end="")
            print()
        
        print(f"\nStatus: {self.get_status().value}")
        print(f"Moves: {self._moves}  Score: {self._score}")
        print("="*70)
    
    def reset(self) -> None:
        """Reset the game to start a new round"""
        self._deck = self._create_deck()
        random.shuffle(self._deck)
        
        self._stock = StockPile([])
        self._waste = WastePile()
        self._foundations = {suit: FoundationPile(suit) for suit in Suit}
        self._tableau = [TableauPile() for _ in range(7)]
        
        self._state = InProgressState()
        self._moves = 0
        self._score = 0
        
        self._deal()
        print("Game has been reset!")


# ==================== Factory Pattern: Game Factory ====================

class GameFactory:
    """Factory for creating different game configurations"""
    
    @staticmethod
    def create_standard_game() -> SolitaireGame:
        """Create a standard Klondike Solitaire game"""
        game = SolitaireGame()
        game.add_listener(ConsoleLogger())
        game.add_listener(GameStatistics())
        return game
    
    @staticmethod
    def create_silent_game() -> SolitaireGame:
        """Create a game without logging"""
        game = SolitaireGame()
        return game


# ==================== Demo ====================

def main():
    """Demo the solitaire game"""
    print("=== Solitaire Game Demo ===\n")
    
    game = GameFactory.create_standard_game()
    
    game.display()
    
    print("\n--- Playing some moves ---\n")
    
    game.draw_from_stock()
    game.display()
    
    game.auto_move_to_foundation()
    game.display()
    
    game.move_tableau_to_tableau(2, 3, 1)
    game.display()
    
    for _ in range(3):
        game.draw_from_stock()
    
    game.display()
    
    game.move_waste_to_tableau(1)
    game.display()
    
    if game.get_status() == GameStatus.WON:
        print("\n🎉 Congratulations! You won!")
    else:
        print(f"\n📊 Game Status: {game.get_status().value}")
        print(f"Score: {game.get_score()}, Moves: {game.get_moves()}")
    
    print("\n--- Testing game over state ---")
    print("Trying to make a move after checking status:")
    game.draw_from_stock()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()
