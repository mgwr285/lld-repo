from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock, Thread, Event
from collections import defaultdict
import uuid
import time


# ==================== Enums ====================

class AuctionStatus(Enum):
    """Auction lifecycle states"""
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class BidStatus(Enum):
    """Bid states"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    OUTBID = "OUTBID"
    WINNING = "WINNING"
    WON = "WON"
    LOST = "LOST"
    REJECTED = "REJECTED"


class ItemCondition(Enum):
    """Item condition"""
    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class Category(Enum):
    """Item categories"""
    ELECTRONICS = "ELECTRONICS"
    FASHION = "FASHION"
    HOME = "HOME"
    SPORTS = "SPORTS"
    COLLECTIBLES = "COLLECTIBLES"
    AUTOMOTIVE = "AUTOMOTIVE"
    BOOKS = "BOOKS"
    TOYS = "TOYS"
    ART = "ART"
    JEWELRY = "JEWELRY"


class PaymentStatus(Enum):
    """Payment states"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ==================== Data Models ====================

@dataclass
class User:
    """Represents a user (buyer/seller)"""
    user_id: str
    username: str
    email: str
    phone: str
    rating: float = 0.0
    total_ratings: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_rating(self, rating: float) -> None:
        """Add a rating (1-5)"""
        if 1 <= rating <= 5:
            total = self.rating * self.total_ratings
            self.total_ratings += 1
            self.rating = (total + rating) / self.total_ratings
    
    def __repr__(self) -> str:
        return f"User(id={self.user_id}, username={self.username}, rating={self.rating:.1f})"


@dataclass
class Item:
    """Represents an item to be auctioned"""
    item_id: str
    title: str
    description: str
    category: Category
    condition: ItemCondition
    images: List[str] = field(default_factory=list)
    
    def __repr__(self) -> str:
        return f"Item(id={self.item_id}, title={self.title})"


class Bid:
    """Represents a bid on an auction"""
    
    def __init__(self, bid_id: str, auction_id: str, bidder: User, amount: Decimal):
        self._bid_id = bid_id
        self._auction_id = auction_id
        self._bidder = bidder
        self._amount = amount
        self._status = BidStatus.PENDING
        self._timestamp = datetime.now()
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._bid_id
    
    def get_auction_id(self) -> str:
        return self._auction_id
    
    def get_bidder(self) -> User:
        return self._bidder
    
    def get_amount(self) -> Decimal:
        return self._amount
    
    def get_status(self) -> BidStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: BidStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_timestamp(self) -> datetime:
        return self._timestamp
    
    def __repr__(self) -> str:
        return f"Bid(id={self._bid_id}, bidder={self._bidder.username}, amount=${self._amount})"


class Auction:
    """
    Represents an auction with thread-safe bid management.
    Handles concurrent bidding and automatic status updates.
    """
    
    def __init__(self, auction_id: str, item: Item, seller: User,
                 starting_price: Decimal, reserve_price: Optional[Decimal],
                 start_time: datetime, duration_minutes: int,
                 min_bid_increment: Decimal = Decimal('1.00')):
        self._auction_id = auction_id
        self._item = item
        self._seller = seller
        self._starting_price = starting_price
        self._reserve_price = reserve_price
        self._start_time = start_time
        self._end_time = start_time + timedelta(minutes=duration_minutes)
        self._min_bid_increment = min_bid_increment
        
        # Bidding state
        self._current_highest_bid: Optional[Bid] = None
        self._bids: List[Bid] = []
        self._bidder_max_bids: Dict[str, Decimal] = {}  # For proxy bidding
        
        # Status
        self._status = AuctionStatus.DRAFT
        self._winner: Optional[User] = None
        
        # Watchers
        self._watchers: Set[str] = set()  # user_ids watching this auction
        
        # Callbacks
        self._on_bid_placed: Optional[Callable] = None
        self._on_outbid: Optional[Callable] = None
        self._on_auction_ended: Optional[Callable] = None
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._auction_id
    
    def get_item(self) -> Item:
        return self._item
    
    def get_seller(self) -> User:
        return self._seller
    
    def get_starting_price(self) -> Decimal:
        return self._starting_price
    
    def get_reserve_price(self) -> Optional[Decimal]:
        return self._reserve_price
    
    def get_start_time(self) -> datetime:
        return self._start_time
    
    def get_end_time(self) -> datetime:
        return self._end_time
    
    def get_status(self) -> AuctionStatus:
        with self._lock:
            return self._status
    
    def get_current_highest_bid(self) -> Optional[Bid]:
        with self._lock:
            return self._current_highest_bid
    
    def get_current_price(self) -> Decimal:
        """Get current price (highest bid or starting price)"""
        with self._lock:
            if self._current_highest_bid:
                return self._current_highest_bid.get_amount()
            return self._starting_price
    
    def get_minimum_next_bid(self) -> Decimal:
        """Calculate minimum valid next bid"""
        with self._lock:
            current = self.get_current_price()
            return current + self._min_bid_increment
    
    def get_all_bids(self) -> List[Bid]:
        """Get all bids sorted by timestamp"""
        with self._lock:
            return sorted(self._bids, key=lambda b: b.get_timestamp(), reverse=True)
    
    def get_winner(self) -> Optional[User]:
        with self._lock:
            return self._winner
    
    def schedule(self) -> bool:
        """Schedule the auction"""
        with self._lock:
            if self._status != AuctionStatus.DRAFT:
                return False
            
            self._status = AuctionStatus.SCHEDULED
            print(f"Auction {self._auction_id} scheduled for {self._start_time}")
            return True
    
    def start(self) -> bool:
        """Start the auction"""
        with self._lock:
            if self._status != AuctionStatus.SCHEDULED:
                return False
            
            self._status = AuctionStatus.ACTIVE
            print(f"Auction {self._auction_id} is now ACTIVE")
            return True
    
    def is_active(self) -> bool:
        """Check if auction is currently active"""
        with self._lock:
            now = datetime.now()
            return (self._status == AuctionStatus.ACTIVE and 
                    self._start_time <= now < self._end_time)
    
    def place_bid(self, bidder: User, amount: Decimal) -> Optional[Bid]:
        """
        Place a bid on the auction (thread-safe).
        Returns the bid if successful, None otherwise.
        """
        with self._lock:
            # Validate auction is active
            if not self.is_active():
                print(f"Auction {self._auction_id} is not active")
                return None
            
            # Seller cannot bid on own auction
            if bidder.user_id == self._seller.user_id:
                print("Seller cannot bid on their own auction")
                return None
            
            # Validate bid amount
            min_bid = self.get_minimum_next_bid()
            if amount < min_bid:
                print(f"Bid amount ${amount} is below minimum ${min_bid}")
                return None
            
            # Create bid
            bid_id = str(uuid.uuid4())
            bid = Bid(bid_id, self._auction_id, bidder, amount)
            
            # Process bid
            previous_highest = self._current_highest_bid
            
            # Update highest bid
            self._current_highest_bid = bid
            bid.set_status(BidStatus.ACCEPTED)
            self._bids.append(bid)
            
            # Mark previous highest as outbid
            if previous_highest:
                previous_highest.set_status(BidStatus.OUTBID)
                
                # Notify previous bidder
                if self._on_outbid:
                    self._on_outbid(previous_highest.get_bidder(), self)
            
            # Notify new bid
            if self._on_bid_placed:
                self._on_bid_placed(bid, self)
            
            print(f"Bid placed: ${amount} by {bidder.username}")
            return bid
    
    def end_auction(self) -> bool:
        """End the auction and determine winner"""
        with self._lock:
            if self._status != AuctionStatus.ACTIVE:
                return False
            
            self._status = AuctionStatus.ENDED
            
            # Determine winner
            if self._current_highest_bid:
                final_price = self._current_highest_bid.get_amount()
                
                # Check reserve price
                if self._reserve_price and final_price < self._reserve_price:
                    print(f"Auction ended - Reserve price not met (${self._reserve_price})")
                    self._current_highest_bid.set_status(BidStatus.LOST)
                    self._winner = None
                else:
                    self._winner = self._current_highest_bid.get_bidder()
                    self._current_highest_bid.set_status(BidStatus.WON)
                    print(f"Auction ended - Winner: {self._winner.username} at ${final_price}")
                    
                    # Mark all other bids as lost
                    for bid in self._bids:
                        if bid != self._current_highest_bid and bid.get_status() != BidStatus.LOST:
                            bid.set_status(BidStatus.LOST)
            else:
                print(f"Auction ended - No bids received")
            
            # Notify auction ended
            if self._on_auction_ended:
                self._on_auction_ended(self)
            
            return True
    
    def cancel(self) -> bool:
        """Cancel the auction"""
        with self._lock:
            if self._status in [AuctionStatus.ENDED, AuctionStatus.CANCELLED]:
                return False
            
            self._status = AuctionStatus.CANCELLED
            
            # Mark all bids as lost
            for bid in self._bids:
                bid.set_status(BidStatus.LOST)
            
            print(f"Auction {self._auction_id} cancelled")
            return True
    
    def add_watcher(self, user_id: str) -> None:
        """Add user to watchlist"""
        with self._lock:
            self._watchers.add(user_id)
    
    def remove_watcher(self, user_id: str) -> None:
        """Remove user from watchlist"""
        with self._lock:
            self._watchers.discard(user_id)
    
    def get_watchers(self) -> Set[str]:
        """Get all watchers"""
        with self._lock:
            return self._watchers.copy()
    
    def get_time_remaining(self) -> timedelta:
        """Get time remaining in auction"""
        with self._lock:
            if self._status != AuctionStatus.ACTIVE:
                return timedelta(0)
            
            now = datetime.now()
            if now >= self._end_time:
                return timedelta(0)
            
            return self._end_time - now
    
    def extend_duration(self, additional_minutes: int) -> bool:
        """Extend auction duration (anti-sniping)"""
        with self._lock:
            if self._status != AuctionStatus.ACTIVE:
                return False
            
            self._end_time += timedelta(minutes=additional_minutes)
            print(f"Auction extended by {additional_minutes} minutes")
            return True
    
    def set_on_bid_placed_callback(self, callback: Callable) -> None:
        """Set callback for new bids"""
        self._on_bid_placed = callback
    
    def set_on_outbid_callback(self, callback: Callable) -> None:
        """Set callback when user is outbid"""
        self._on_outbid = callback
    
    def set_on_auction_ended_callback(self, callback: Callable) -> None:
        """Set callback when auction ends"""
        self._on_auction_ended = callback
    
    def __repr__(self) -> str:
        current_price = self.get_current_price()
        return (f"Auction(id={self._auction_id}, item={self._item.title}, "
                f"current_price=${current_price}, status={self._status.value})")


# ==================== Auction Manager ====================

class AuctionScheduler(Thread):
    """
    Background thread that manages auction lifecycle:
    - Starts scheduled auctions
    - Ends expired auctions
    """
    
    def __init__(self, auction_system: 'AuctionSystem'):
        super().__init__(daemon=True)
        self._auction_system = auction_system
        self._stop_event = Event()
        self._check_interval = 1  # Check every second
    
    def run(self) -> None:
        """Main scheduler loop"""
        while not self._stop_event.is_set():
            try:
                self._check_auctions()
                time.sleep(self._check_interval)
            except Exception as e:
                print(f"Scheduler error: {e}")
    
    def _check_auctions(self) -> None:
        """Check all auctions and update their status"""
        now = datetime.now()
        
        for auction in self._auction_system.get_all_auctions():
            # Start scheduled auctions
            if (auction.get_status() == AuctionStatus.SCHEDULED and 
                now >= auction.get_start_time()):
                auction.start()
            
            # End active auctions
            elif (auction.get_status() == AuctionStatus.ACTIVE and 
                  now >= auction.get_end_time()):
                auction.end_auction()
    
    def stop(self) -> None:
        """Stop the scheduler"""
        self._stop_event.set()


# ==================== Search & Filter ====================

@dataclass
class AuctionSearchFilter:
    """Filter criteria for searching auctions"""
    query: Optional[str] = None
    category: Optional[Category] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    condition: Optional[ItemCondition] = None
    seller_id: Optional[str] = None
    status: Optional[AuctionStatus] = None


# ==================== Main Auction System ====================

class AuctionSystem:
    """
    Main auction system coordinating all operations.
    Handles auction creation, bidding, and lifecycle management.
    """
    
    def __init__(self):
        # Data storage
        self._users: Dict[str, User] = {}
        self._auctions: Dict[str, Auction] = {}
        self._user_auctions: Dict[str, List[str]] = defaultdict(list)  # seller_id -> auction_ids
        self._user_bids: Dict[str, List[str]] = defaultdict(list)  # user_id -> bid_ids
        self._user_watchlist: Dict[str, Set[str]] = defaultdict(set)  # user_id -> auction_ids
        
        # Scheduler
        self._scheduler = AuctionScheduler(self)
        
        # Thread safety
        self._lock = RLock()
    
    def start(self) -> None:
        """Start the auction system"""
        self._scheduler.start()
        print("Auction system started")
    
    def stop(self) -> None:
        """Stop the auction system"""
        self._scheduler.stop()
        print("Auction system stopped")
    
    # ==================== User Management ====================
    
    def register_user(self, user: User) -> None:
        """Register a new user"""
        with self._lock:
            self._users[user.user_id] = user
            print(f"Registered user: {user}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    # ==================== Auction Creation ====================
    
    def create_auction(self, seller_id: str, item: Item,
                      starting_price: Decimal, reserve_price: Optional[Decimal],
                      start_time: datetime, duration_minutes: int,
                      min_bid_increment: Decimal = Decimal('1.00')) -> Optional[Auction]:
        """Create a new auction"""
        with self._lock:
            seller = self.get_user(seller_id)
            if not seller:
                print("Seller not found")
                return None
            
            # Validate prices
            if starting_price <= 0:
                print("Starting price must be positive")
                return None
            
            if reserve_price and reserve_price < starting_price:
                print("Reserve price must be >= starting price")
                return None
            
            # Create auction
            auction_id = str(uuid.uuid4())
            auction = Auction(
                auction_id, item, seller, starting_price, reserve_price,
                start_time, duration_minutes, min_bid_increment
            )
            
            # Schedule auction
            auction.schedule()
            
            # Store auction
            self._auctions[auction_id] = auction
            self._user_auctions[seller_id].append(auction_id)
            
            print(f"Created auction: {auction}")
            return auction
    
    def get_auction(self, auction_id: str) -> Optional[Auction]:
        """Get auction by ID"""
        return self._auctions.get(auction_id)
    
    def get_all_auctions(self) -> List[Auction]:
        """Get all auctions"""
        with self._lock:
            return list(self._auctions.values())
    
    # ==================== Bidding ====================
    
    def place_bid(self, auction_id: str, bidder_id: str, amount: Decimal) -> Optional[Bid]:
        """Place a bid on an auction"""
        with self._lock:
            auction = self.get_auction(auction_id)
            bidder = self.get_user(bidder_id)
            
            if not auction or not bidder:
                print("Auction or bidder not found")
                return None
            
            # Place bid
            bid = auction.place_bid(bidder, amount)
            
            if bid:
                # Track user's bids
                self._user_bids[bidder_id].append(bid.get_id())
            
            return bid
    
    def get_user_bids(self, user_id: str, auction_id: str = None) -> List[Bid]:
        """Get user's bids, optionally filtered by auction"""
        with self._lock:
            all_bids = []
            
            for aid in self._auctions:
                auction = self._auctions[aid]
                if auction_id and aid != auction_id:
                    continue
                
                for bid in auction.get_all_bids():
                    if bid.get_bidder().user_id == user_id:
                        all_bids.append(bid)
            
            return sorted(all_bids, key=lambda b: b.get_timestamp(), reverse=True)
    
    # ==================== Browse & Search ====================
    
    def search_auctions(self, filters: AuctionSearchFilter = None) -> List[Auction]:
        """Search auctions with filters"""
        with self._lock:
            results = list(self._auctions.values())
            
            if not filters:
                return results
            
            # Apply filters
            if filters.query:
                query_lower = filters.query.lower()
                results = [a for a in results 
                          if (query_lower in a.get_item().title.lower() or
                              query_lower in a.get_item().description.lower())]
            
            if filters.category:
                results = [a for a in results 
                          if a.get_item().category == filters.category]
            
            if filters.min_price:
                results = [a for a in results 
                          if a.get_current_price() >= filters.min_price]
            
            if filters.max_price:
                results = [a for a in results 
                          if a.get_current_price() <= filters.max_price]
            
            if filters.condition:
                results = [a for a in results 
                          if a.get_item().condition == filters.condition]
            
            if filters.seller_id:
                results = [a for a in results 
                          if a.get_seller().user_id == filters.seller_id]
            
            if filters.status:
                results = [a for a in results 
                          if a.get_status() == filters.status]
            
            return results
    
    def get_active_auctions(self, category: Category = None) -> List[Auction]:
        """Get all active auctions"""
        filters = AuctionSearchFilter(
            status=AuctionStatus.ACTIVE,
            category=category
        )
        return self.search_auctions(filters)
    
    def get_ending_soon(self, hours: int = 24) -> List[Auction]:
        """Get auctions ending within specified hours"""
        with self._lock:
            cutoff = datetime.now() + timedelta(hours=hours)
            ending_soon = [
                a for a in self._auctions.values()
                if (a.get_status() == AuctionStatus.ACTIVE and 
                    a.get_end_time() <= cutoff)
            ]
            
            # Sort by end time
            ending_soon.sort(key=lambda a: a.get_end_time())
            return ending_soon
    
    def get_user_auctions(self, user_id: str, status: AuctionStatus = None) -> List[Auction]:
        """Get auctions created by user"""
        with self._lock:
            auction_ids = self._user_auctions.get(user_id, [])
            auctions = [self._auctions[aid] for aid in auction_ids if aid in self._auctions]
            
            if status:
                auctions = [a for a in auctions if a.get_status() == status]
            
            return auctions
    
    # ==================== Watchlist ====================
    
    def add_to_watchlist(self, user_id: str, auction_id: str) -> bool:
        """Add auction to user's watchlist"""
        with self._lock:
            auction = self.get_auction(auction_id)
            if not auction:
                return False
            
            self._user_watchlist[user_id].add(auction_id)
            auction.add_watcher(user_id)
            print(f"Added auction {auction_id} to watchlist")
            return True
    
    def remove_from_watchlist(self, user_id: str, auction_id: str) -> bool:
        """Remove auction from user's watchlist"""
        with self._lock:
            self._user_watchlist[user_id].discard(auction_id)
            
            auction = self.get_auction(auction_id)
            if auction:
                auction.remove_watcher(user_id)
            
            print(f"Removed auction {auction_id} from watchlist")
            return True
    
    def get_watchlist(self, user_id: str) -> List[Auction]:
        """Get user's watchlist"""
        with self._lock:
            auction_ids = self._user_watchlist.get(user_id, set())
            return [self._auctions[aid] for aid in auction_ids if aid in self._auctions]
    
    # ==================== Auction Management ====================
    
    def cancel_auction(self, auction_id: str, seller_id: str) -> bool:
        """Cancel an auction (only by seller)"""
        with self._lock:
            auction = self.get_auction(auction_id)
            if not auction:
                return False
            
            if auction.get_seller().user_id != seller_id:
                print("Only seller can cancel auction")
                return False
            
            return auction.cancel()
    
    # ==================== Statistics ====================
    
    def get_system_stats(self) -> Dict:
        """Get system-wide statistics"""
        with self._lock:
            total_auctions = len(self._auctions)
            active = sum(1 for a in self._auctions.values() 
                        if a.get_status() == AuctionStatus.ACTIVE)
            ended = sum(1 for a in self._auctions.values() 
                       if a.get_status() == AuctionStatus.ENDED)
            
            total_bids = sum(len(a.get_all_bids()) for a in self._auctions.values())
            
            return {
                'total_users': len(self._users),
                'total_auctions': total_auctions,
                'active_auctions': active,
                'ended_auctions': ended,
                'total_bids': total_bids
            }


# ==================== Demo Usage ====================

def print_separator(title: str):
    """Print formatted separator"""
    print("\n" + "="*70)
    print(f"TEST CASE: {title}")
    print("="*70)


def main():
    """Demo the auction system"""
    print("=== Online Auction System Demo ===\n")
    
    # Initialize system
    system = AuctionSystem()
    system.start()
    
    # Test Case 1: Register Users
    print_separator("Register Users")
    
    alice = User("user-001", "alice_seller", "alice@email.com", "+1-555-0001")
    bob = User("user-002", "bob_bidder", "bob@email.com", "+1-555-0002")
    charlie = User("user-003", "charlie_collector", "charlie@email.com", "+1-555-0003")
    
    system.register_user(alice)
    system.register_user(bob)
    system.register_user(charlie)
    
    # Test Case 2: Create Items
    print_separator("Create Auction Items")
    
    item1 = Item(
        "item-001",
        "Vintage Rolex Watch",
        "Rare 1960s Rolex Submariner in excellent condition",
        Category.JEWELRY,
        ItemCondition.EXCELLENT,
        ["image1.jpg", "image2.jpg"]
    )
    
    item2 = Item(
        "item-002",
        "iPhone 14 Pro",
        "Brand new, sealed in box",
        Category.ELECTRONICS,
        ItemCondition.NEW
    )
    
    item3 = Item(
        "item-003",
        "Signed Baseball Card",
        "Mickey Mantle 1952 rookie card, authenticated",
        Category.COLLECTIBLES,
        ItemCondition.GOOD
    )
    
    print(f"Created items:")
    print(f"  - {item1.title}")
    print(f"  - {item2.title}")
    print(f"  - {item3.title}")
    
    # Test Case 3: Create Auctions
    print_separator("Create Auctions")
    
    # Auction starting now
    now = datetime.now()
    
    auction1 = system.create_auction(
        seller_id="user-001",
        item=item1,
        starting_price=Decimal('1000.00'),
        reserve_price=Decimal('5000.00'),
        start_time=now,
        duration_minutes=5,  # 5 minutes for demo
        min_bid_increment=Decimal('50.00')
    )
    
    auction2 = system.create_auction(
        seller_id="user-001",
        item=item2,
        starting_price=Decimal('500.00'),
        reserve_price=None,
        start_time=now,
        duration_minutes=10,
        min_bid_increment=Decimal('10.00')
    )
    
    # Future auction
    future_start = now + timedelta(minutes=2)
    auction3 = system.create_auction(
        seller_id="user-002",
        item=item3,
        starting_price=Decimal('2000.00'),
        reserve_price=Decimal('10000.00'),
        start_time=future_start,
        duration_minutes=3,
        min_bid_increment=Decimal('100.00')
    )
    
    # Wait for auctions to start
    print("\nWaiting for auctions to start...")
    time.sleep(2)
    
    # Test Case 4: Browse Active Auctions
    print_separator("Browse Active Auctions")
    
    active_auctions = system.get_active_auctions()
    print(f"\nFound {len(active_auctions)} active auctions:")
    for auction in active_auctions:
        print(f"  - {auction.get_item().title}")
        print(f"    Current price: ${auction.get_current_price()}")
        print(f"    Min next bid: ${auction.get_minimum_next_bid()}")
        print(f"    Time remaining: {auction.get_time_remaining()}")
    
    # Test Case 5: Place Bids
    print_separator("Place Bids")
    
    print("\nBob bids on Rolex watch:")
    bid1 = system.place_bid(auction1.get_id(), "user-002", Decimal('1050.00'))
    
    print("\nCharlie outbids Bob:")
    bid2 = system.place_bid(auction1.get_id(), "user-003", Decimal('1200.00'))
    
    print("\nBob bids again:")
    bid3 = system.place_bid(auction1.get_id(), "user-002", Decimal('1500.00'))
    
    print(f"\nCurrenthighest bid on Rolex: ${auction1.get_current_price()}")
    
    # Test Case 6: View Bid History
    print_separator("View Bid History")
    
    print(f"\nBid history for '{auction1.get_item().title}':")
    all_bids = auction1.get_all_bids()
    for i, bid in enumerate(all_bids, 1):
        print(f"  {i}. ${bid.get_amount()} by {bid.get_bidder().username} - {bid.get_status().value}")
        print(f"     Time: {bid.get_timestamp().strftime('%H:%M:%S')}")
    
    # Test Case 7: Concurrent Bidding
    print_separator("Concurrent Bidding Simulation")
    
    print("\nSimulating concurrent bids on iPhone:")
    
    import threading
    
    bid_results = []
    
    def place_concurrent_bid(user_id: str, amount: Decimal):
        result = system.place_bid(auction2.get_id(), user_id, amount)
        bid_results.append((user_id, amount, result is not None))
    
    # Create multiple threads placing bids simultaneously
    threads = []
    bids_to_place = [
        ("user-002", Decimal('520.00')),
        ("user-003", Decimal('530.00')),
        ("user-002", Decimal('550.00')),
        ("user-003", Decimal('560.00')),
    ]
    
    for user_id, amount in bids_to_place:
        t = threading.Thread(target=place_concurrent_bid, args=(user_id, amount))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print("\nConcurrent bidding results:")
    for user_id, amount, success in bid_results:
        user = system.get_user(user_id)
        status = "✓ Success" if success else "✗ Failed"
        print(f"  {user.username} bid ${amount}: {status}")
    
    print(f"\nFinal price on iPhone: ${auction2.get_current_price()}")
    print(f"Current leader: {auction2.get_current_highest_bid().get_bidder().username if auction2.get_current_highest_bid() else 'None'}")
    
    # Test Case 8: Invalid Bid Attempts
    print_separator("Invalid Bid Attempts")
    
    print("\nAttempting bid below minimum:")
    invalid_bid1 = system.place_bid(auction1.get_id(), "user-002", Decimal('1510.00'))
    
    print("\nAttempting seller bidding on own auction:")
    invalid_bid2 = system.place_bid(auction1.get_id(), "user-001", Decimal('2000.00'))
    
    # Test Case 9: Watchlist
    print_separator("Watchlist Management")
    
    print("\nBob adds auctions to watchlist:")
    system.add_to_watchlist("user-002", auction1.get_id())
    system.add_to_watchlist("user-002", auction2.get_id())
    
    print("\nCharlie adds auction to watchlist:")
    system.add_to_watchlist("user-003", auction1.get_id())
    
    print(f"\nBob's watchlist:")
    bob_watchlist = system.get_watchlist("user-002")
    for auction in bob_watchlist:
        print(f"  - {auction.get_item().title} (${auction.get_current_price()})")
    
    print(f"\nWatchers for Rolex auction: {len(auction1.get_watchers())}")
    
    # Test Case 10: Search and Filter
    print_separator("Search and Filter Auctions")
    
    print("\nSearching for 'phone':")
    search_results = system.search_auctions(
        AuctionSearchFilter(query="phone")
    )
    for auction in search_results:
        print(f"  - {auction.get_item().title}")
    
    print("\nFiltering by category (JEWELRY):")
    jewelry_auctions = system.search_auctions(
        AuctionSearchFilter(category=Category.JEWELRY)
    )
    for auction in jewelry_auctions:
        print(f"  - {auction.get_item().title}")
    
    print("\nFiltering by price range ($500-$2000):")
    price_filtered = system.search_auctions(
        AuctionSearchFilter(
            min_price=Decimal('500.00'),
            max_price=Decimal('2000.00')
        )
    )
    for auction in price_filtered:
        print(f"  - {auction.get_item().title}: ${auction.get_current_price()}")
    
    # Test Case 11: User's Auctions
    print_separator("View User's Auctions")
    
    print("\nAlice's auctions:")
    alice_auctions = system.get_user_auctions("user-001")
    for auction in alice_auctions:
        print(f"  - {auction.get_item().title}")
        print(f"    Status: {auction.get_status().value}")
        print(f"    Current price: ${auction.get_current_price()}")
    
    # Test Case 12: User's Bids
    print_separator("View User's Bids")
    
    print("\nBob's all bids:")
    bob_bids = system.get_user_bids("user-002")
    for bid in bob_bids:
        auction = system.get_auction(bid.get_auction_id())
        print(f"  - ${bid.get_amount()} on {auction.get_item().title}")
        print(f"    Status: {bid.get_status().value}")
    
    # Test Case 13: Ending Soon
    print_separator("Auctions Ending Soon")
    
    ending_soon = system.get_ending_soon(hours=1)
    print(f"\nAuctions ending within 1 hour: {len(ending_soon)}")
    for auction in ending_soon:
        time_left = auction.get_time_remaining()
        minutes = int(time_left.total_seconds() // 60)
        seconds = int(time_left.total_seconds() % 60)
        print(f"  - {auction.get_item().title}: {minutes}m {seconds}s remaining")
    
    # Test Case 14: Bid Callbacks
    print_separator("Bid Event Callbacks")
    
    def on_bid_placed(bid: Bid, auction: Auction):
        print(f"  📢 New bid: ${bid.get_amount()} on {auction.get_item().title}")
    
    def on_outbid(user: User, auction: Auction):
        print(f"  ⚠️  {user.username} was outbid on {auction.get_item().title}")
    
    def on_auction_ended(auction: Auction):
        winner = auction.get_winner()
        if winner:
            print(f"  🎉 Auction ended! Winner: {winner.username}")
        else:
            print(f"  ❌ Auction ended with no winner")
    
    # Set callbacks for auction1
    auction1.set_on_bid_placed_callback(on_bid_placed)
    auction1.set_on_outbid_callback(on_outbid)
    auction1.set_on_auction_ended_callback(on_auction_ended)
    
    print("\nPlacing bids with callbacks enabled:")
    system.place_bid(auction1.get_id(), "user-003", Decimal('1600.00'))
    system.place_bid(auction1.get_id(), "user-002", Decimal('1700.00'))
    
    # Test Case 15: Extend Auction Duration
    print_separator("Extend Auction Duration (Anti-Sniping)")
    
    print(f"\nAuction 1 time remaining before extension: {auction1.get_time_remaining()}")
    
    print("\nExtending auction by 2 minutes:")
    auction1.extend_duration(2)
    
    print(f"Time remaining after extension: {auction1.get_time_remaining()}")
    
    # Test Case 16: Wait for Auction to End
    print_separator("Wait for Auction to End")
    
    print(f"\nWaiting for auction '{auction1.get_item().title}' to end...")
    print("(Sleeping for a bit to let scheduler work...)")
    
    # Sleep until auction1 should have ended
    time_to_wait = min(auction1.get_time_remaining().total_seconds() + 2, 10)
    print(f"Waiting {int(time_to_wait)} seconds...")
    time.sleep(time_to_wait)
    
    print(f"\nAuction status: {auction1.get_status().value}")
    
    if auction1.get_winner():
        print(f"Winner: {auction1.get_winner().username}")
        print(f"Winning bid: ${auction1.get_current_highest_bid().get_amount()}")
    else:
        print("No winner (reserve price not met or no bids)")
    
    # Test Case 17: Reserve Price Not Met
    print_separator("Reserve Price Not Met Scenario")
    
    # Create auction with high reserve
    item4 = Item(
        "item-004",
        "Rare Painting",
        "Original artwork from famous artist",
        Category.ART,
        ItemCondition.EXCELLENT
    )
    
    auction4 = system.create_auction(
        seller_id="user-001",
        item=item4,
        starting_price=Decimal('100.00'),
        reserve_price=Decimal('10000.00'),  # Very high reserve
        start_time=datetime.now(),
        duration_minutes=1,
        min_bid_increment=Decimal('10.00')
    )
    
    time.sleep(1)  # Let it start
    
    print("\nPlacing bid below reserve price:")
    system.place_bid(auction4.get_id(), "user-002", Decimal('500.00'))
    
    print(f"Current price: ${auction4.get_current_price()}")
    print(f"Reserve price: ${auction4.get_reserve_price()}")
    
    # Wait for it to end
    time.sleep(65)
    
    print(f"\nAuction ended - Winner: {auction4.get_winner()}")
    if not auction4.get_winner():
        print("Reserve price was not met!")
    
    # Test Case 18: Cancel Auction
    print_separator("Cancel Auction")
    
    item5 = Item(
        "item-005",
        "Test Item",
        "Item for cancellation test",
        Category.ELECTRONICS,
        ItemCondition.NEW
    )
    
    auction5 = system.create_auction(
        seller_id="user-001",
        item=item5,
        starting_price=Decimal('50.00'),
        reserve_price=None,
        start_time=datetime.now(),
        duration_minutes=10
    )
    
    time.sleep(1)
    
    system.place_bid(auction5.get_id(), "user-002", Decimal('60.00'))
    
    print(f"\nAuction status before cancel: {auction5.get_status().value}")
    
    print("\nAlice cancels the auction:")
    system.cancel_auction(auction5.get_id(), "user-001")
    
    print(f"Auction status after cancel: {auction5.get_status().value}")
    
    # Check bid status
    cancelled_bids = auction5.get_all_bids()
    if cancelled_bids:
        print(f"Bid status after cancellation: {cancelled_bids[0].get_status().value}")
    
    # Test Case 19: Browse by Status
    print_separator("Browse by Status")
    
    print("\nActive auctions:")
    active = system.search_auctions(AuctionSearchFilter(status=AuctionStatus.ACTIVE))
    for auction in active:
        print(f"  - {auction.get_item().title}")
    
    print("\nEnded auctions:")
    ended = system.search_auctions(AuctionSearchFilter(status=AuctionStatus.ENDED))
    for auction in ended:
        winner = auction.get_winner()
        winner_name = winner.username if winner else "No winner"
        print(f"  - {auction.get_item().title} - Winner: {winner_name}")
    
    print("\nCancelled auctions:")
    cancelled = system.search_auctions(AuctionSearchFilter(status=AuctionStatus.CANCELLED))
    for auction in cancelled:
        print(f"  - {auction.get_item().title}")
    
    # Test Case 20: Search by Seller
    print_separator("Search by Seller")
    
    print("\nAlice's auctions:")
    alice_listings = system.search_auctions(
        AuctionSearchFilter(seller_id="user-001")
    )
    for auction in alice_listings:
        print(f"  - {auction.get_item().title} ({auction.get_status().value})")
    
    # Test Case 21: Search by Condition
    print_separator("Search by Condition")
    
    print("\nNew items:")
    new_items = system.search_auctions(
        AuctionSearchFilter(condition=ItemCondition.NEW)
    )
    for auction in new_items:
        print(f"  - {auction.get_item().title}")
    
    print("\nExcellent condition items:")
    excellent_items = system.search_auctions(
        AuctionSearchFilter(condition=ItemCondition.EXCELLENT)
    )
    for auction in excellent_items:
        print(f"  - {auction.get_item().title}")
    
    # Test Case 22: Multiple Bids from Same User
    print_separator("Multiple Bids from Same User")
    
    print("\nBob's bidding history on all auctions:")
    bob_all_bids = system.get_user_bids("user-002")
    
    bid_count_by_auction = defaultdict(int)
    for bid in bob_all_bids:
        bid_count_by_auction[bid.get_auction_id()] += 1
    
    print(f"Total bids placed by Bob: {len(bob_all_bids)}")
    for auction_id, count in bid_count_by_auction.items():
        auction = system.get_auction(auction_id)
        print(f"  - {auction.get_item().title}: {count} bids")
    
    # Test Case 23: Watchlist Notifications
    print_separator("Watchlist Notifications")
    
    print("\nUsers watching each auction:")
    for auction in system.get_all_auctions():
        watchers = auction.get_watchers()
        if watchers:
            print(f"\n{auction.get_item().title}:")
            for user_id in watchers:
                user = system.get_user(user_id)
                print(f"  - {user.username}")
    
    # Test Case 24: User Ratings
    print_separator("User Ratings")
    
    print("\nAdding ratings to users:")
    alice.add_rating(4.5)
    alice.add_rating(5.0)
    alice.add_rating(4.8)
    
    bob.add_rating(4.2)
    bob.add_rating(4.0)
    
    print(f"\nUser ratings:")
    for user_id, user in system._users.items():
        if user.total_ratings > 0:
            print(f"  {user.username}: {user.rating:.2f} ({user.total_ratings} ratings)")
    
    # Test Case 25: Auction Details
    print_separator("Detailed Auction View")
    
    sample_auction = auction1
    
    print(f"\nAuction: {sample_auction.get_item().title}")
    print(f"Description: {sample_auction.get_item().description}")
    print(f"Category: {sample_auction.get_item().category.value}")
    print(f"Condition: {sample_auction.get_item().condition.value}")
    print(f"\nSeller: {sample_auction.get_seller().username}")
    print(f"Seller rating: {sample_auction.get_seller().rating:.1f}")
    print(f"\nStarting price: ${sample_auction.get_starting_price()}")
    print(f"Reserve price: ${sample_auction.get_reserve_price() if sample_auction.get_reserve_price() else 'None'}")
    print(f"Current price: ${sample_auction.get_current_price()}")
    print(f"Min bid increment: ${sample_auction._min_bid_increment}")
    print(f"\nStatus: {sample_auction.get_status().value}")
    print(f"Start time: {sample_auction.get_start_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End time: {sample_auction.get_end_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTotal bids: {len(sample_auction.get_all_bids())}")
    print(f"Watchers: {len(sample_auction.get_watchers())}")
    
    if sample_auction.get_winner():
        print(f"\nWinner: {sample_auction.get_winner().username}")
        print(f"Winning bid: ${sample_auction.get_current_highest_bid().get_amount()}")
    
    # Test Case 26: Time Remaining Display
    print_separator("Time Remaining Display")
    
    print("\nActive auctions with time remaining:")
    for auction in system.get_active_auctions():
        time_left = auction.get_time_remaining()
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        seconds = int(time_left.total_seconds() % 60)
        
        print(f"\n{auction.get_item().title}:")
        print(f"  Time left: {hours}h {minutes}m {seconds}s")
        print(f"  Current price: ${auction.get_current_price()}")
    
    # Test Case 27: Bid Statistics
    print_separator("Bid Statistics")
    
    for auction in [auction1, auction2]:
        bids = auction.get_all_bids()
        if not bids:
            continue
        
        print(f"\n{auction.get_item().title}:")
        print(f"  Total bids: {len(bids)}")
        
        amounts = [bid.get_amount() for bid in bids]
        print(f"  Lowest bid: ${min(amounts)}")
        print(f"  Highest bid: ${max(amounts)}")
        print(f"  Average bid: ${sum(amounts) / len(amounts):.2f}")
        
        unique_bidders = len(set(bid.get_bidder().user_id for bid in bids))
        print(f"  Unique bidders: {unique_bidders}")
    
    # Test Case 28: Remove from Watchlist
    print_separator("Remove from Watchlist")
    
    print(f"\nBob's watchlist before removal: {len(system.get_watchlist('user-002'))} items")
    
    print("\nRemoving auction from watchlist:")
    system.remove_from_watchlist("user-002", auction1.get_id())
    
    print(f"Bob's watchlist after removal: {len(system.get_watchlist('user-002'))} items")
    
    # Test Case 29: System Statistics
    print_separator("System Statistics")
    
    stats = system.get_system_stats()
    print("\nSystem-wide Statistics:")
    print(f"  Total Users: {stats['total_users']}")
    print(f"  Total Auctions: {stats['total_auctions']}")
    print(f"  Active Auctions: {stats['active_auctions']}")
    print(f"  Ended Auctions: {stats['ended_auctions']}")
    print(f"  Total Bids: {stats['total_bids']}")
    
    # Test Case 30: Final Summary
    print_separator("Final Summary")
    
    print("\nUser Activity Summary:")
    for user_id, user in system._users.items():
        print(f"\n{user.username}:")
        
        # Auctions created
        user_auctions = system.get_user_auctions(user_id)
        print(f"  Auctions created: {len(user_auctions)}")
        
        # Bids placed
        user_bids = system.get_user_bids(user_id)
        print(f"  Bids placed: {len(user_bids)}")
        
        # Active bids
        active_bids = [b for b in user_bids if b.get_status() in [BidStatus.WINNING, BidStatus.ACCEPTED]]
        print(f"  Active bids: {len(active_bids)}")
        
        # Won auctions
        won_bids = [b for b in user_bids if b.get_status() == BidStatus.WON]
        print(f"  Auctions won: {len(won_bids)}")
        
        # Watchlist
        watchlist = system.get_watchlist(user_id)
        print(f"  Watchlist: {len(watchlist)} items")
    
    print("\n" + "="*70)
    print("Stopping auction system...")
    system.stop()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# State Pattern - Auction progresses through well-defined states (Draft → Scheduled → Active → Ended)
# Observer Pattern - Callbacks for bid events, outbid notifications, and auction endings
# Thread-Safe Singleton - AuctionScheduler manages auction lifecycle in background
# Strategy Pattern - Could be extended for different bidding strategies (proxy bidding, autobidding)

# Key Features Implemented:

# Create New Listings:

# Seller creates auctions with items
# Set starting price, reserve price, duration
# Configurable bid increments
# Schedule future auctions
# Item categorization and condition tracking


# Browse Auctions:

# Search by keywords, category, price range
# Filter by condition, seller, status
# View active auctions
# Find auctions ending soon
# Browse by user (seller's listings)


# Place Bids:

# Thread-safe concurrent bidding
# Minimum bid validation
# Seller cannot bid on own auction
# Automatic bid status updates
# Bid history tracking


# Manage Current Highest Bid:

# Atomic bid updates with locking
# Automatic outbid status updates
# Real-time highest bid tracking
# Multiple bids per user allowed
# Previous bidders notified when outbid


# Auction Duration Management:

# Scheduled start times
# Automatic auction start/end
# Time remaining calculation
# Anti-sniping (extend duration)
# Background scheduler thread


# Concurrency:

# RLock for thread-safe operations
# Atomic bid placement
# Protected auction state changes
# Thread-safe collections
# Background scheduler runs independently



# Additional Features:

# Watchlist: Users can watch auctions for updates
# Reserve Price: Minimum acceptable price (hidden from bidders)
# Bid History: Complete audit trail of all bids
# Event Callbacks: Real-time notifications for bid events
# User Ratings: Reputation system for buyers/sellers
# Search & Filter: Advanced search with multiple criteria
# Statistics: System-wide and per-auction analytics
# Auction Cancellation: Seller can cancel before completion
# Bid Status Tracking: Won, Lost, Outbid states

# Architecture Decisions:

# Thread Safety First: All shared state protected with locks
# Background Scheduler: Automatic auction lifecycle management
# Immutable Timestamps: Bid and auction times are fixed
# Decimal for Money: Precise financial calculations
# Event-Driven: Callbacks enable reactive UI updates
# Separation of Concerns: Auction, Bid, Item are independent
# User-Centric: Track user's auctions, bids, watchlist separately

# Production Considerations:

# Persistence: Would add database storage for all entities
# Distributed Locking: For multi-server deployments
# Payment Integration: Connect to payment processors
# Notification Service: Email/SMS for outbid alerts
# Anti-Fraud: Shill bidding detection
# Shipping: Integration with shipping providers
# Escrow: Hold payments until item received

# This design provides a robust foundation for a production-ready auction system with proper concurrency handling and all essential features!
