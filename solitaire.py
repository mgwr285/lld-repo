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
        # All cards face down in stock
        for card in self._cards:
            card.face_up = False
    
    def draw(self) -> Optional[Card]:
        """Draw a card from stock"""
        card = self.remove_card()
        if card:
            card.flip()  # Flip face up when drawn
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
        
        # Must be correct suit
        if card.suit != self._suit:
            return False
        
        # If empty, must be Ace
        if self.is_empty():
            return card.rank == Rank.ACE
        
        # Otherwise, must be one rank higher
        top_card = self.peek()
        return card.rank.value == top_card.rank.value + 1


class TableauPile(Pile):
    """Tableau pile (main playing area)"""
    
    def can_add_card(self, card: Card) -> bool:
        """Check if card can be added to tableau"""
        if not card.face_up:
            return False
        
        # If empty, only King can be placed
        if self.is_empty():
            return card.rank == Rank.KING
        
        top_card = self.peek()
        
        # Must be opposite color and one rank lower
        return (card.is_opposite_color(top_card) and 
                card.is_one_rank_lower(top_card))
    
    def can_move_cards(self, num_cards: int) -> bool:
        """Check if we can move multiple cards"""
        if num_cards > self.size():
            return False
        
        # Can only move if all cards are face up
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


# ==================== Main Game ====================

class SolitaireGame:
    """
    Klondike Solitaire game implementation
    """
    
    def __init__(self):
        # Create and shuffle deck
        self._deck = self._create_deck()
        random.shuffle(self._deck)
        
        # Initialize piles
        self._stock = StockPile([])
        self._waste = WastePile()
        self._foundations = {
            suit: FoundationPile(suit) for suit in Suit
        }
        self._tableau = [TableauPile() for _ in range(7)]
        
        # Deal cards
        self._deal()
        
        # Game state
        self._moves = 0
        self._score = 0
    
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
        
        # Deal to tableau piles
        for pile_num in range(7):
            for card_num in range(pile_num + 1):
                card = self._deck[card_index]
                # Only top card is face up
                if card_num == pile_num:
                    card.face_up = True
                self._tableau[pile_num].add_card(card)
                card_index += 1
        
        # Remaining cards go to stock
        for i in range(card_index, len(self._deck)):
            self._stock.add_card(self._deck[i])
    
    # ==================== Game Actions ====================
    
    def draw_from_stock(self) -> bool:
        """Draw a card from stock to waste"""
        if self._stock.is_empty():
            # Recycle waste back to stock
            if self._waste.is_empty():
                return False
            
            while not self._waste.is_empty():
                card = self._waste.remove_card()
                card.face_up = False
                self._stock.add_card(card)
            
            print("Recycled waste pile back to stock")
            return True
        
        card = self._stock.draw()
        if card:
            self._waste.add_card(card)
            self._moves += 1
            print(f"Drew {card} from stock")
            return True
        
        return False
    
    def move_waste_to_foundation(self, suit: Suit) -> bool:
        """Move top card from waste to foundation"""
        if self._waste.is_empty():
            print("Waste pile is empty")
            return False
        
        card = self._waste.peek()
        foundation = self._foundations[suit]
        
        if foundation.can_add_card(card):
            self._waste.remove_card()
            foundation.add_card(card)
            self._moves += 1
            self._score += 10
            print(f"Moved {card} to {suit.value} foundation")
            return True
        
        print(f"Cannot move {card} to {suit.value} foundation")
        return False
    
    def move_waste_to_tableau(self, tableau_index: int) -> bool:
        """Move top card from waste to tableau"""
        if not 0 <= tableau_index < 7:
            print("Invalid tableau index")
            return False
        
        if self._waste.is_empty():
            print("Waste pile is empty")
            return False
        
        card = self._waste.peek()
        tableau = self._tableau[tableau_index]
        
        if tableau.can_add_card(card):
            self._waste.remove_card()
            tableau.add_card(card)
            self._moves += 1
            self._score += 5
            print(f"Moved {card} to tableau {tableau_index + 1}")
            return True
        
        print(f"Cannot move {card} to tableau {tableau_index + 1}")
        return False
    
    def move_tableau_to_foundation(self, tableau_index: int, suit: Suit) -> bool:
        """Move top card from tableau to foundation"""
        if not 0 <= tableau_index < 7:
            print("Invalid tableau index")
            return False
        
        tableau = self._tableau[tableau_index]
        if tableau.is_empty():
            print(f"Tableau {tableau_index + 1} is empty")
            return False
        
        card = tableau.peek()
        foundation = self._foundations[suit]
        
        if foundation.can_add_card(card):
            tableau.remove_card()
            foundation.add_card(card)
            tableau.flip_top_card()
            self._moves += 1
            self._score += 10
            print(f"Moved {card} to {suit.value} foundation")
            return True
        
        print(f"Cannot move {card} to {suit.value} foundation")
        return False
    
    def move_tableau_to_tableau(self, from_index: int, to_index: int, 
                                num_cards: int = 1) -> bool:
        """Move cards between tableau piles"""
        if not (0 <= from_index < 7 and 0 <= to_index < 7):
            print("Invalid tableau index")
            return False
        
        if from_index == to_index:
            print("Cannot move to same pile")
            return False
        
        from_tableau = self._tableau[from_index]
        to_tableau = self._tableau[to_index]
        
        if from_tableau.size() < num_cards:
            print(f"Not enough cards in tableau {from_index + 1}")
            return False
        
        # Get cards to move
        cards = from_tableau.get_cards()[-num_cards:]
        
        # Check if move is valid
        if not all(card.face_up for card in cards):
            print("Cannot move face-down cards")
            return False
        
        if not to_tableau.can_add_card(cards[0]):
            print(f"Cannot move to tableau {to_index + 1}")
            return False
        
        # Perform move
        moved_cards = from_tableau.remove_cards(num_cards)
        to_tableau.add_cards(moved_cards)
        from_tableau.flip_top_card()
        
        self._moves += 1
        self._score += 5
        print(f"Moved {num_cards} card(s) from tableau {from_index + 1} "
              f"to tableau {to_index + 1}")
        return True
    
    def auto_move_to_foundation(self) -> int:
        """Automatically move available cards to foundations"""
        moves_made = 0
        
        # Try waste pile
        if not self._waste.is_empty():
            card = self._waste.peek()
            if self._foundations[card.suit].can_add_card(card):
                self.move_waste_to_foundation(card.suit)
                moves_made += 1
        
        # Try each tableau pile
        for i in range(7):
            if not self._tableau[i].is_empty():
                card = self._tableau[i].peek()
                if self._foundations[card.suit].can_add_card(card):
                    self.move_tableau_to_foundation(i, card.suit)
                    moves_made += 1
        
        if moves_made > 0:
            print(f"Auto-moved {moves_made} card(s) to foundations")
        
        return moves_made
    
    # ==================== Game State ====================
    
    def is_won(self) -> bool:
        """Check if game is won"""
        return all(foundation.size() == 13 for foundation in self._foundations.values())
    
    def get_score(self) -> int:
        """Get current score"""
        return self._score
    
    def get_moves(self) -> int:
        """Get number of moves"""
        return self._moves
    
    def display(self) -> None:
        """Display current game state"""
        print("\n" + "="*70)
        print("KLONDIKE SOLITAIRE")
        print("="*70)
        
        # Stock and Waste
        stock_display = f"[{self._stock.size()}]" if not self._stock.is_empty() else "[ ]"
        waste_display = str(self._waste.peek()) if not self._waste.is_empty() else "[ ]"
        print(f"\nStock: {stock_display}  Waste: {waste_display}")
        
        # Foundations
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
        
        # Tableau
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
        
        # Stats
        print(f"\nMoves: {self._moves}  Score: {self._score}")
        print("="*70)


# ==================== Demo ====================

def main():
    """Demo the solitaire game"""
    print("=== Solitaire Game Demo ===\n")
    
    game = SolitaireGame()
    
    # Show initial state
    game.display()
    
    # Simulate some moves
    print("\n--- Playing some moves ---\n")
    
    # Draw from stock
    game.draw_from_stock()
    game.display()
    
    # Try auto-move to foundations
    game.auto_move_to_foundation()
    game.display()
    
    # Move between tableau piles
    game.move_tableau_to_tableau(2, 3, 1)
    game.display()
    
    # Draw more cards
    for _ in range(3):
        game.draw_from_stock()
    
    game.display()
    
    # Try moving waste to tableau
    game.move_waste_to_tableau(1)
    game.display()
    
    # Check game state
    if game.is_won():
        print("\n🎉 Congratulations! You won!")
    else:
        print(f"\n📊 Game in progress - Score: {game.get_score()}, Moves: {game.get_moves()}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Key Design Patterns:

# Enum Pattern - Suit and Rank as type-safe enumerations
# Inheritance - Different pile types inherit from base Pile class
# Strategy Pattern - Each pile type has its own validation logic
# Encapsulation - Game rules enforced within pile classes

# Core Features:

# Card Management:

# 52-card deck with suits and ranks
# Face up/down state
# Color and rank comparisons


# Pile Types:

# Stock (draw pile)
# Waste (discarded from stock)
# 4 Foundations (goal piles by suit)
# 7 Tableau piles (main playing area)


# Game Rules:

# Tableau: Alternating colors, descending rank
# Foundation: Same suit, ascending from Ace to King
# Move validation per Klondike rules


# Scoring & State:

# Move counter
# Score tracking
# Win condition detection



# Interview Discussion Points:

# Why inheritance for piles? Different validation rules per pile type
# Immutability: Cards are mutable for face_up state, but suit/rank are immutable
# Validation: Each pile type knows its own rules (Single Responsibility)
# Extensibility: Easy to add new pile types or game variants
# Clear separation: Game logic, display logic, and data are separated

# This is a clean, complete implementation perfect for a 45-minute LLD interview!RetryClaude does not have the ability to run the code it generates yet.Claude can make mistakes. Please double-check responses. Sonnet 4.5
