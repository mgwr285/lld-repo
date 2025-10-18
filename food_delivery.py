from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock
import uuid
import math


# ==================== Enums ====================

class OrderStatus(Enum):
    """Order lifecycle states"""
    CART = "CART"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentStatus(Enum):
    """Payment states"""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(Enum):
    """Payment methods"""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    UPI = "UPI"
    WALLET = "WALLET"
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"


class DeliveryAgentStatus(Enum):
    """Delivery agent availability"""
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    ON_BREAK = "ON_BREAK"


class CuisineType(Enum):
    """Types of cuisines"""
    INDIAN = "INDIAN"
    CHINESE = "CHINESE"
    ITALIAN = "ITALIAN"
    MEXICAN = "MEXICAN"
    AMERICAN = "AMERICAN"
    JAPANESE = "JAPANESE"
    THAI = "THAI"
    MEDITERRANEAN = "MEDITERRANEAN"


class FoodCategory(Enum):
    """Food categories"""
    APPETIZER = "APPETIZER"
    MAIN_COURSE = "MAIN_COURSE"
    DESSERT = "DESSERT"
    BEVERAGE = "BEVERAGE"
    SNACK = "SNACK"


class DietaryType(Enum):
    """Dietary classifications"""
    VEG = "VEG"
    NON_VEG = "NON_VEG"
    VEGAN = "VEGAN"
    GLUTEN_FREE = "GLUTEN_FREE"


# ==================== Location Models ====================

@dataclass
class Location:
    """Represents a geographic location"""
    latitude: float
    longitude: float
    address: str
    city: str
    zipcode: str
    
    def distance_to(self, other: 'Location') -> float:
        """Calculate distance in kilometers using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(self.latitude)
        lat2_rad = math.radians(other.latitude)
        delta_lat = math.radians(other.latitude - self.latitude)
        delta_lon = math.radians(other.longitude - self.longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def __repr__(self) -> str:
        return f"Location({self.address}, {self.city})"


# ==================== Menu Models ====================

@dataclass
class MenuItem:
    """Represents a menu item"""
    item_id: str
    name: str
    description: str
    price: Decimal
    category: FoodCategory
    dietary_type: DietaryType
    is_available: bool = True
    preparation_time_minutes: int = 15
    image_url: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"MenuItem(id={self.item_id}, name={self.name}, price=${self.price})"


class Menu:
    """Restaurant menu with items"""
    
    def __init__(self, restaurant_id: str):
        self._restaurant_id = restaurant_id
        self._items: Dict[str, MenuItem] = {}
        self._lock = RLock()
    
    def add_item(self, item: MenuItem) -> None:
        """Add item to menu"""
        with self._lock:
            self._items[item.item_id] = item
            print(f"Added menu item: {item.name}")
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from menu"""
        with self._lock:
            if item_id in self._items:
                item = self._items.pop(item_id)
                print(f"Removed menu item: {item.name}")
                return True
            return False
    
    def update_item_price(self, item_id: str, new_price: Decimal) -> bool:
        """Update item price"""
        with self._lock:
            if item_id in self._items:
                old_price = self._items[item_id].price
                self._items[item_id].price = new_price
                print(f"Updated {self._items[item_id].name} price: ${old_price} -> ${new_price}")
                return True
            return False
    
    def update_item_availability(self, item_id: str, is_available: bool) -> bool:
        """Update item availability"""
        with self._lock:
            if item_id in self._items:
                self._items[item_id].is_available = is_available
                status = "available" if is_available else "unavailable"
                print(f"Set {self._items[item_id].name} as {status}")
                return True
            return False
    
    def get_item(self, item_id: str) -> Optional[MenuItem]:
        """Get menu item by ID"""
        with self._lock:
            return self._items.get(item_id)
    
    def get_all_items(self) -> List[MenuItem]:
        """Get all menu items"""
        with self._lock:
            return list(self._items.values())
    
    def get_available_items(self) -> List[MenuItem]:
        """Get only available items"""
        with self._lock:
            return [item for item in self._items.values() if item.is_available]
    
    def search_items(self, query: str = None, category: FoodCategory = None,
                    dietary_type: DietaryType = None) -> List[MenuItem]:
        """Search menu items with filters"""
        with self._lock:
            items = self.get_available_items()
            
            if query:
                query_lower = query.lower()
                items = [item for item in items 
                        if query_lower in item.name.lower() or 
                        query_lower in item.description.lower()]
            
            if category:
                items = [item for item in items if item.category == category]
            
            if dietary_type:
                items = [item for item in items if item.dietary_type == dietary_type]
            
            return items
    
    def __repr__(self) -> str:
        return f"Menu(restaurant={self._restaurant_id}, items={len(self._items)})"


# ==================== Restaurant Models ====================

@dataclass
class RestaurantRating:
    """Restaurant rating information"""
    average_rating: float = 0.0
    total_ratings: int = 0
    
    def add_rating(self, rating: float) -> None:
        """Add a new rating"""
        total = self.average_rating * self.total_ratings
        self.total_ratings += 1
        self.average_rating = (total + rating) / self.total_ratings


class Restaurant:
    """Represents a restaurant"""
    
    def __init__(self, restaurant_id: str, name: str, location: Location,
                 cuisine_types: List[CuisineType], owner_id: str):
        self._restaurant_id = restaurant_id
        self._name = name
        self._location = location
        self._cuisine_types = cuisine_types
        self._owner_id = owner_id
        self._menu = Menu(restaurant_id)
        self._is_open = False
        self._rating = RestaurantRating()
        self._lock = RLock()
        
        # Operating hours (simplified - hour of day)
        self._opening_time = 9  # 9 AM
        self._closing_time = 22  # 10 PM
        
        # Delivery settings
        self._accepts_orders = True
        self._min_order_amount = Decimal('0')
        self._delivery_fee = Decimal('2.99')
        self._avg_preparation_time = 30  # minutes
    
    def get_id(self) -> str:
        return self._restaurant_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_location(self) -> Location:
        return self._location
    
    def get_cuisine_types(self) -> List[CuisineType]:
        return self._cuisine_types.copy()
    
    def get_menu(self) -> Menu:
        return self._menu
    
    def is_open(self) -> bool:
        """Check if restaurant is currently open"""
        with self._lock:
            current_hour = datetime.now().hour
            return (self._is_open and 
                    self._opening_time <= current_hour < self._closing_time and
                    self._accepts_orders)
    
    def set_open_status(self, is_open: bool) -> None:
        """Manually set open/closed status"""
        with self._lock:
            self._is_open = is_open
            status = "opened" if is_open else "closed"
            print(f"Restaurant {self._name} {status}")
    
    def get_rating(self) -> RestaurantRating:
        with self._lock:
            return self._rating
    
    def add_rating(self, rating: float) -> None:
        """Add customer rating"""
        with self._lock:
            if 1 <= rating <= 5:
                self._rating.add_rating(rating)
    
    def get_delivery_fee(self) -> Decimal:
        return self._delivery_fee
    
    def set_delivery_fee(self, fee: Decimal) -> None:
        with self._lock:
            self._delivery_fee = fee
    
    def get_min_order_amount(self) -> Decimal:
        return self._min_order_amount
    
    def set_min_order_amount(self, amount: Decimal) -> None:
        with self._lock:
            self._min_order_amount = amount
    
    def __repr__(self) -> str:
        cuisines = ', '.join([c.value for c in self._cuisine_types])
        return f"Restaurant(id={self._restaurant_id}, name={self._name}, cuisines=[{cuisines}])"


# ==================== Order Models ====================

@dataclass
class OrderItem:
    """Item in an order"""
    menu_item: MenuItem
    quantity: int
    special_instructions: Optional[str] = None
    
    def get_subtotal(self) -> Decimal:
        """Calculate subtotal for this item"""
        return self.menu_item.price * self.quantity
    
    def __repr__(self) -> str:
        return f"OrderItem({self.menu_item.name} x{self.quantity})"


class Order:
    """Represents a customer order"""
    
    def __init__(self, order_id: str, customer_id: str, restaurant: Restaurant,
                 delivery_location: Location):
        self._order_id = order_id
        self._customer_id = customer_id
        self._restaurant = restaurant
        self._delivery_location = delivery_location
        self._items: List[OrderItem] = []
        self._status = OrderStatus.CART
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        
        # Pricing
        self._subtotal = Decimal('0')
        self._delivery_fee = restaurant.get_delivery_fee()
        self._tax = Decimal('0')
        self._discount = Decimal('0')
        self._total = Decimal('0')
        
        # Payment
        self._payment_method: Optional[PaymentMethod] = None
        self._payment_status = PaymentStatus.PENDING
        
        # Delivery
        self._delivery_agent_id: Optional[str] = None
        self._estimated_delivery_time: Optional[datetime] = None
        self._actual_delivery_time: Optional[datetime] = None
        
        # Status tracking
        self._status_history: List[Tuple[OrderStatus, datetime]] = []
        self._status_history.append((OrderStatus.CART, self._created_at))
        
        # Lock
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._order_id
    
    def get_customer_id(self) -> str:
        return self._customer_id
    
    def get_restaurant(self) -> Restaurant:
        return self._restaurant
    
    def get_status(self) -> OrderStatus:
        with self._lock:
            return self._status
    
    def add_item(self, menu_item: MenuItem, quantity: int = 1,
                special_instructions: str = None) -> bool:
        """Add item to order"""
        with self._lock:
            if self._status != OrderStatus.CART:
                print("Cannot modify order after placement")
                return False
            
            if not menu_item.is_available:
                print(f"{menu_item.name} is not available")
                return False
            
            # Check if item already exists, update quantity
            for order_item in self._items:
                if order_item.menu_item.item_id == menu_item.item_id:
                    order_item.quantity += quantity
                    self._calculate_totals()
                    return True
            
            # Add new item
            order_item = OrderItem(menu_item, quantity, special_instructions)
            self._items.append(order_item)
            self._calculate_totals()
            print(f"Added {quantity}x {menu_item.name} to order")
            return True
    
    def remove_item(self, item_id: str) -> bool:
        """Remove item from order"""
        with self._lock:
            if self._status != OrderStatus.CART:
                print("Cannot modify order after placement")
                return False
            
            for i, order_item in enumerate(self._items):
                if order_item.menu_item.item_id == item_id:
                    removed = self._items.pop(i)
                    self._calculate_totals()
                    print(f"Removed {removed.menu_item.name} from order")
                    return True
            return False
    
    def update_item_quantity(self, item_id: str, quantity: int) -> bool:
        """Update item quantity"""
        with self._lock:
            if self._status != OrderStatus.CART:
                return False
            
            if quantity <= 0:
                return self.remove_item(item_id)
            
            for order_item in self._items:
                if order_item.menu_item.item_id == item_id:
                    order_item.quantity = quantity
                    self._calculate_totals()
                    return True
            return False
    
    def get_items(self) -> List[OrderItem]:
        """Get all order items"""
        with self._lock:
            return self._items.copy()
    
    def _calculate_totals(self) -> None:
        """Calculate order totals (internal, lock must be held)"""
        self._subtotal = sum(item.get_subtotal() for item in self._items)
        self._tax = (self._subtotal * Decimal('0.08')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        self._total = self._subtotal + self._delivery_fee + self._tax - self._discount
    
    def get_subtotal(self) -> Decimal:
        with self._lock:
            return self._subtotal
    
    def get_delivery_fee(self) -> Decimal:
        return self._delivery_fee
    
    def get_tax(self) -> Decimal:
        with self._lock:
            return self._tax
    
    def get_total(self) -> Decimal:
        with self._lock:
            return self._total
    
    def apply_discount(self, discount: Decimal) -> None:
        """Apply discount to order"""
        with self._lock:
            self._discount = discount
            self._calculate_totals()
    
    def set_payment_method(self, method: PaymentMethod) -> None:
        """Set payment method"""
        with self._lock:
            self._payment_method = method
    
    def place_order(self) -> bool:
        """Place the order"""
        with self._lock:
            if self._status != OrderStatus.CART:
                print("Order already placed")
                return False
            
            if not self._items:
                print("Cannot place empty order")
                return False
            
            if not self._restaurant.is_open():
                print("Restaurant is closed")
                return False
            
            if self._subtotal < self._restaurant.get_min_order_amount():
                print(f"Minimum order amount is ${self._restaurant.get_min_order_amount()}")
                return False
            
            if not self._payment_method:
                print("Payment method not set")
                return False
            
            self._update_status(OrderStatus.PLACED)
            
            # Calculate estimated delivery time
            prep_time = self._restaurant._avg_preparation_time
            delivery_time = 20  # Simplified
            self._estimated_delivery_time = datetime.now() + timedelta(
                minutes=prep_time + delivery_time
            )
            
            return True
    
    def confirm_order(self) -> bool:
        """Restaurant confirms the order"""
        with self._lock:
            if self._status != OrderStatus.PLACED:
                return False
            self._update_status(OrderStatus.CONFIRMED)
            return True
    
    def start_preparation(self) -> bool:
        """Start preparing the order"""
        with self._lock:
            if self._status != OrderStatus.CONFIRMED:
                return False
            self._update_status(OrderStatus.PREPARING)
            return True
    
    def mark_ready_for_pickup(self) -> bool:
        """Mark order as ready for pickup"""
        with self._lock:
            if self._status != OrderStatus.PREPARING:
                return False
            self._update_status(OrderStatus.READY_FOR_PICKUP)
            return True
    
    def assign_delivery_agent(self, agent_id: str) -> bool:
        """Assign delivery agent"""
        with self._lock:
            if self._status not in [OrderStatus.READY_FOR_PICKUP, OrderStatus.CONFIRMED]:
                return False
            self._delivery_agent_id = agent_id
            return True
    
    def mark_picked_up(self) -> bool:
        """Mark order as picked up by delivery agent"""
        with self._lock:
            if self._status != OrderStatus.READY_FOR_PICKUP:
                return False
            if not self._delivery_agent_id:
                return False
            self._update_status(OrderStatus.PICKED_UP)
            self._update_status(OrderStatus.OUT_FOR_DELIVERY)
            return True
    
    def mark_delivered(self) -> bool:
        """Mark order as delivered"""
        with self._lock:
            if self._status != OrderStatus.OUT_FOR_DELIVERY:
                return False
            self._update_status(OrderStatus.DELIVERED)
            self._actual_delivery_time = datetime.now()
            self._payment_status = PaymentStatus.CAPTURED
            return True
    
    def cancel_order(self, reason: str = None) -> bool:
        """Cancel the order"""
        with self._lock:
            if self._status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
                return False
            
            # Can only cancel before pickup
            if self._status in [OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY]:
                print("Cannot cancel order after pickup")
                return False
            
            self._update_status(OrderStatus.CANCELLED)
            if self._payment_status == PaymentStatus.CAPTURED:
                self._payment_status = PaymentStatus.REFUNDED
            return True
    
    def _update_status(self, new_status: OrderStatus) -> None:
        """Update order status (internal, lock must be held)"""
        self._status = new_status
        self._updated_at = datetime.now()
        self._status_history.append((new_status, self._updated_at))
        print(f"Order {self._order_id} status updated to {new_status.value}")
    
    def get_status_history(self) -> List[Tuple[OrderStatus, datetime]]:
        """Get order status history"""
        with self._lock:
            return self._status_history.copy()
    
    def get_estimated_delivery_time(self) -> Optional[datetime]:
        with self._lock:
            return self._estimated_delivery_time
    
    def get_delivery_agent_id(self) -> Optional[str]:
        with self._lock:
            return self._delivery_agent_id
    
    def __repr__(self) -> str:
        return (f"Order(id={self._order_id}, restaurant={self._restaurant.get_name()}, "
                f"status={self._status.value}, total=${self._total})")


# ==================== User Models ====================

@dataclass
class Customer:
    """Represents a customer"""
    customer_id: str
    name: str
    email: str
    phone: str
    addresses: List[Location] = field(default_factory=list)
    
    def add_address(self, location: Location) -> None:
        """Add delivery address"""
        self.addresses.append(location)
    
    def __repr__(self) -> str:
        return f"Customer(id={self.customer_id}, name={self.name})"


class DeliveryAgent:
    """Represents a delivery agent"""
    
    def __init__(self, agent_id: str, name: str, phone: str, vehicle_type: str):
        self._agent_id = agent_id
        self._name = name
        self._phone = phone
        self._vehicle_type = vehicle_type
        self._status = DeliveryAgentStatus.OFFLINE
        self._current_location: Optional[Location] = None
        self._current_order_id: Optional[str] = None
        self._completed_deliveries = 0
        self._rating = 0.0
        self._total_ratings = 0
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._agent_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_status(self) -> DeliveryAgentStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: DeliveryAgentStatus) -> None:
        """Update agent status"""
        with self._lock:
            self._status = status
            print(f"Delivery agent {self._name} status: {status.value}")
    
    def get_current_location(self) -> Optional[Location]:
        with self._lock:
            return self._current_location
    
    def update_location(self, location: Location) -> None:
        """Update agent's current location"""
        with self._lock:
            self._current_location = location
    
    def is_available(self) -> bool:
        """Check if agent is available for delivery"""
        with self._lock:
            return self._status == DeliveryAgentStatus.AVAILABLE
    
    def assign_order(self, order_id: str) -> bool:
        """Assign order to agent"""
        with self._lock:
            if not self.is_available():
                return False
            self._current_order_id = order_id
            self._status = DeliveryAgentStatus.BUSY
            return True
    
    def complete_delivery(self) -> None:
        """Mark current delivery as complete"""
        with self._lock:
            self._current_order_id = None
            self._completed_deliveries += 1
            self._status = DeliveryAgentStatus.AVAILABLE
    
    def add_rating(self, rating: float) -> None:
        """Add rating for agent"""
        with self._lock:
            if 1 <= rating <= 5:
                total = self._rating * self._total_ratings
                self._total_ratings += 1
                self._rating = (total + rating) / self._total_ratings
    
    def get_rating(self) -> float:
        with self._lock:
            return self._rating
    
    def get_completed_deliveries(self) -> int:
        with self._lock:
            return self._completed_deliveries
    
    def __repr__(self) -> str:
        return (f"DeliveryAgent(id={self._agent_id}, name={self._name}, "
                f"status={self._status.value}, rating={self._rating:.1f})")


# ==================== Payment Processing ====================

class PaymentProcessor:
    """Handles payment processing"""
    
    def __init__(self):
        self._transactions: Dict[str, Dict] = {}
        self._lock = RLock()
    
    def process_payment(self, order: Order) -> bool:
        """Process payment for an order"""
        with self._lock:
            transaction_id = str(uuid.uuid4())
            
            print(f"\nProcessing payment for order {order.get_id()}")
            print(f"  Amount: ${order.get_total()}")
            print(f"  Method: {order._payment_method.value if order._payment_method else 'Not set'}")
            
            # Simulate payment processing
            if order._payment_method == PaymentMethod.CASH_ON_DELIVERY:
                # No immediate payment needed
                order._payment_status = PaymentStatus.PENDING
                success = True
            else:
                # Simulate card/UPI/wallet payment
                success = True  # In real system, would integrate with payment gateway
                if success:
                    order._payment_status = PaymentStatus.AUTHORIZED
            
            # Record transaction
            self._transactions[transaction_id] = {
                'order_id': order.get_id(),
                'amount': order.get_total(),
                'method': order._payment_method,
                'status': order._payment_status,
                'timestamp': datetime.now()
            }
            
            if success:
                print(f"  Payment successful (Transaction ID: {transaction_id[:8]}...)")
            else:
                print(f"  Payment failed")
                order._payment_status = PaymentStatus.FAILED
            
            return success
    
    def capture_payment(self, order: Order) -> bool:
        """Capture payment after delivery (for COD or authorized payments)"""
        with self._lock:
            if order._payment_status == PaymentStatus.PENDING:
                # COD payment captured on delivery
                order._payment_status = PaymentStatus.CAPTURED
                return True
            elif order._payment_status == PaymentStatus.AUTHORIZED:
                # Capture previously authorized payment
                order._payment_status = PaymentStatus.CAPTURED
                return True
            return False
    
    def refund_payment(self, order: Order) -> bool:
        """Process refund for cancelled order"""
        with self._lock:
            if order._payment_status in [PaymentStatus.AUTHORIZED, PaymentStatus.CAPTURED]:
                order._payment_status = PaymentStatus.REFUNDED
                print(f"Refund processed for order {order.get_id()}")
                return True
            return False


# ==================== Delivery Assignment Strategy ====================

class DeliveryAssignmentStrategy(ABC):
    """Strategy for assigning delivery agents to orders"""
    
    @abstractmethod
    def assign_agent(self, order: Order, available_agents: List[DeliveryAgent]) -> Optional[DeliveryAgent]:
        """Assign best agent for the order"""
        pass


class NearestAgentStrategy(DeliveryAssignmentStrategy):
    """Assign nearest available agent"""
    
    def assign_agent(self, order: Order, available_agents: List[DeliveryAgent]) -> Optional[DeliveryAgent]:
        if not available_agents:
            return None
        
        restaurant_location = order.get_restaurant().get_location()
        
        # Find nearest agent
        nearest_agent = None
        min_distance = float('inf')
        
        for agent in available_agents:
            if agent.is_available() and agent.get_current_location():
                distance = agent.get_current_location().distance_to(restaurant_location)
                if distance < min_distance:
                    min_distance = distance
                    nearest_agent = agent
        
        return nearest_agent


class HighestRatedAgentStrategy(DeliveryAssignmentStrategy):
    """Assign highest rated available agent"""
    
    def assign_agent(self, order: Order, available_agents: List[DeliveryAgent]) -> Optional[DeliveryAgent]:
        available = [agent for agent in available_agents if agent.is_available()]
        
        if not available:
            return None
        
        # Sort by rating (highest first)
        available.sort(key=lambda a: a.get_rating(), reverse=True)
        return available[0]


# ==================== Main Service ====================

class FoodDeliveryService:
    """
    Main food delivery service coordinating all operations
    """
    
    def __init__(self):
        # Entities
        self._restaurants: Dict[str, Restaurant] = {}
        self._customers: Dict[str, Customer] = {}
        self._delivery_agents: Dict[str, DeliveryAgent] = {}
        self._orders: Dict[str, Order] = {}
        
        # Services
        self._payment_processor = PaymentProcessor()
        self._delivery_strategy: DeliveryAssignmentStrategy = NearestAgentStrategy()
        
        # Locks
        self._lock = RLock()
    
    # ==================== Restaurant Management ====================
    
    def register_restaurant(self, restaurant: Restaurant) -> None:
        """Register a new restaurant"""
        with self._lock:
            self._restaurants[restaurant.get_id()] = restaurant
            print(f"Registered restaurant: {restaurant}")
    
    def get_restaurant(self, restaurant_id: str) -> Optional[Restaurant]:
        """Get restaurant by ID"""
        return self._restaurants.get(restaurant_id)
    
    def search_restaurants(self, location: Location, max_distance_km: float = 10,
                          cuisine_type: CuisineType = None,
                          min_rating: float = None) -> List[Restaurant]:
        """Search restaurants near location"""
        with self._lock:
            results = []
            
            for restaurant in self._restaurants.values():
                # Check if open
                if not restaurant.is_open():
                    continue
                
                # Check distance
                distance = location.distance_to(restaurant.get_location())
                if distance > max_distance_km:
                    continue
                
                # Check cuisine type
                if cuisine_type and cuisine_type not in restaurant.get_cuisine_types():
                    continue
                
                # Check rating
                if min_rating and restaurant.get_rating().average_rating < min_rating:
                    continue
                
                results.append(restaurant)
            
            # Sort by rating
            results.sort(key=lambda r: r.get_rating().average_rating, reverse=True)
            return results
    
    # ==================== Customer Management ====================
    
    def register_customer(self, customer: Customer) -> None:
        """Register a new customer"""
        with self._lock:
            self._customers[customer.customer_id] = customer
            print(f"Registered customer: {customer}")
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID"""
        return self._customers.get(customer_id)
    
    # ==================== Delivery Agent Management ====================
    
    def register_delivery_agent(self, agent: DeliveryAgent) -> None:
        """Register a new delivery agent"""
        with self._lock:
            self._delivery_agents[agent.get_id()] = agent
            print(f"Registered delivery agent: {agent}")
    
    def get_delivery_agent(self, agent_id: str) -> Optional[DeliveryAgent]:
        """Get delivery agent by ID"""
        return self._delivery_agents.get(agent_id)
    
    def get_available_agents(self) -> List[DeliveryAgent]:
        """Get all available delivery agents"""
        with self._lock:
            return [agent for agent in self._delivery_agents.values() 
                   if agent.is_available()]
    
    def set_delivery_strategy(self, strategy: DeliveryAssignmentStrategy) -> None:
        """Set delivery assignment strategy"""
        self._delivery_strategy = strategy
    
    # ==================== Order Management ====================
    
    def create_order(self, customer_id: str, restaurant_id: str,
                    delivery_location: Location) -> Optional[Order]:
        """Create a new order"""
        with self._lock:
            customer = self.get_customer(customer_id)
            restaurant = self.get_restaurant(restaurant_id)
            
            if not customer or not restaurant:
                print("Invalid customer or restaurant")
                return None
            
            if not restaurant.is_open():
                print(f"Restaurant {restaurant.get_name()} is closed")
                return None
            
            order_id = str(uuid.uuid4())
            order = Order(order_id, customer_id, restaurant, delivery_location)
            self._orders[order_id] = order
            
            print(f"Created order: {order_id}")
            return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self._orders.get(order_id)
    
    def place_order(self, order_id: str) -> bool:
        """Place an order and initiate fulfillment"""
        with self._lock:
            order = self.get_order(order_id)
            if not order:
                return False
            
            # Process payment
            if not self._payment_processor.process_payment(order):
                print("Payment failed")
                return False
            
            # Place order
            if not order.place_order():
                return False
            
            # Auto-confirm order (in real system, restaurant would confirm)
            order.confirm_order()
            
            print(f"\nOrder {order_id} placed successfully!")
            print(f"  Restaurant: {order.get_restaurant().get_name()}")
            print(f"  Items: {len(order.get_items())}")
            print(f"  Total: ${order.get_total()}")
            print(f"  Estimated delivery: {order.get_estimated_delivery_time().strftime('%I:%M %p')}")
            
            return True
    
    def assign_delivery_agent_to_order(self, order_id: str) -> bool:
        """Assign delivery agent to order"""
        with self._lock:
            order = self.get_order(order_id)
            if not order:
                return False
            
            # Get available agents
            available_agents = self.get_available_agents()
            
            if not available_agents:
                print("No delivery agents available")
                return False
            
            # Use strategy to assign agent
            agent = self._delivery_strategy.assign_agent(order, available_agents)
            
            if not agent:
                print("Could not assign delivery agent")
                return False
            
            # Assign order to agent
            if agent.assign_order(order_id):
                order.assign_delivery_agent(agent.get_id())
                print(f"Assigned delivery agent {agent.get_name()} to order {order_id}")
                return True
            
            return False
    
    def complete_order_delivery(self, order_id: str) -> bool:
        """Complete order delivery"""
        with self._lock:
            order = self.get_order(order_id)
            if not order:
                return False
            
            # Mark order as delivered
            if not order.mark_delivered():
                return False
            
            # Capture payment
            self._payment_processor.capture_payment(order)
            
            # Free up delivery agent
            agent_id = order.get_delivery_agent_id()
            if agent_id:
                agent = self.get_delivery_agent(agent_id)
                if agent:
                    agent.complete_delivery()
            
            print(f"Order {order_id} delivered successfully!")
            return True
    
    def cancel_order(self, order_id: str, reason: str = None) -> bool:
        """Cancel an order"""
        with self._lock:
            order = self.get_order(order_id)
            if not order:
                return False
            
            if order.cancel_order(reason):
                # Process refund if payment was made
                self._payment_processor.refund_payment(order)
                
                # Free up delivery agent if assigned
                agent_id = order.get_delivery_agent_id()
                if agent_id:
                    agent = self.get_delivery_agent(agent_id)
                    if agent and agent._current_order_id == order_id:
                        agent.complete_delivery()
                
                print(f"Order {order_id} cancelled")
                return True
            
            return False
    
    def get_customer_orders(self, customer_id: str) -> List[Order]:
        """Get all orders for a customer"""
        with self._lock:
            orders = [order for order in self._orders.values() 
                     if order.get_customer_id() == customer_id]
            orders.sort(key=lambda o: o._created_at, reverse=True)
            return orders
    
    def get_restaurant_orders(self, restaurant_id: str,
                             status: OrderStatus = None) -> List[Order]:
        """Get all orders for a restaurant"""
        with self._lock:
            orders = [order for order in self._orders.values()
                     if order.get_restaurant().get_id() == restaurant_id]
            
            if status:
                orders = [order for order in orders if order.get_status() == status]
            
            orders.sort(key=lambda o: o._created_at, reverse=True)
            return orders
    
    def get_agent_orders(self, agent_id: str) -> List[Order]:
        """Get all orders assigned to a delivery agent"""
        with self._lock:
            orders = [order for order in self._orders.values()
                     if order.get_delivery_agent_id() == agent_id]
            orders.sort(key=lambda o: o._created_at, reverse=True)
            return orders
    
    # ==================== Tracking ====================
    
    def track_order(self, order_id: str) -> Dict:
        """Get detailed tracking information for an order"""
        order = self.get_order(order_id)
        if not order:
            return {}
        
        tracking_info = {
            'order_id': order_id,
            'status': order.get_status().value,
            'restaurant': order.get_restaurant().get_name(),
            'items': len(order.get_items()),
            'total': str(order.get_total()),
            'estimated_delivery': order.get_estimated_delivery_time(),
            'status_history': [
                {
                    'status': status.value,
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                for status, timestamp in order.get_status_history()
            ]
        }
        
        # Add delivery agent info if assigned
        agent_id = order.get_delivery_agent_id()
        if agent_id:
            agent = self.get_delivery_agent(agent_id)
            if agent:
                tracking_info['delivery_agent'] = {
                    'name': agent.get_name(),
                    'phone': agent._phone,
                    'rating': agent.get_rating()
                }
                
                if agent.get_current_location():
                    tracking_info['agent_location'] = {
                        'address': agent.get_current_location().address
                    }
        
        return tracking_info
    
    # ==================== Analytics ====================
    
    def get_system_stats(self) -> Dict:
        """Get system-wide statistics"""
        with self._lock:
            total_orders = len(self._orders)
            active_orders = sum(1 for o in self._orders.values() 
                               if o.get_status() not in [OrderStatus.DELIVERED, OrderStatus.CANCELLED])
            completed_orders = sum(1 for o in self._orders.values() 
                                  if o.get_status() == OrderStatus.DELIVERED)
            
            total_revenue = sum(o.get_total() for o in self._orders.values()
                               if o.get_status() == OrderStatus.DELIVERED)
            
            return {
                'total_restaurants': len(self._restaurants),
                'total_customers': len(self._customers),
                'total_delivery_agents': len(self._delivery_agents),
                'available_agents': len(self.get_available_agents()),
                'total_orders': total_orders,
                'active_orders': active_orders,
                'completed_orders': completed_orders,
                'total_revenue': str(total_revenue)
            }


# ==================== Demo Usage ====================

def print_separator(title: str):
    """Print formatted separator"""
    print("\n" + "="*70)
    print(f"TEST CASE: {title}")
    print("="*70)


def main():
    """Demo the food delivery system"""
    print("=== Food Delivery Service Demo ===\n")
    
    # Initialize service
    service = FoodDeliveryService()
    
    # Test Case 1: Register Restaurants
    print_separator("Register Restaurants")
    
    # Create locations
    restaurant1_location = Location(37.7749, -122.4194, "123 Market St", "San Francisco", "94102")
    restaurant2_location = Location(37.7849, -122.4094, "456 Mission St", "San Francisco", "94103")
    restaurant3_location = Location(37.7649, -122.4294, "789 Howard St", "San Francisco", "94105")
    
    # Create restaurants
    pizza_palace = Restaurant(
        "rest-001",
        "Pizza Palace",
        restaurant1_location,
        [CuisineType.ITALIAN, CuisineType.AMERICAN],
        "owner-001"
    )
    
    spice_heaven = Restaurant(
        "rest-002",
        "Spice Heaven",
        restaurant2_location,
        [CuisineType.INDIAN],
        "owner-002"
    )
    
    sushi_spot = Restaurant(
        "rest-003",
        "Sushi Spot",
        restaurant3_location,
        [CuisineType.JAPANESE],
        "owner-003"
    )
    
    service.register_restaurant(pizza_palace)
    service.register_restaurant(spice_heaven)
    service.register_restaurant(sushi_spot)
    
    # Open restaurants
    pizza_palace.set_open_status(True)
    spice_heaven.set_open_status(True)
    sushi_spot.set_open_status(True)
    
    # Test Case 2: Add Menu Items
    print_separator("Restaurant Menu Management")
    
    print("\nPizza Palace adding menu items:")
    pizza_menu = pizza_palace.get_menu()
    
    margherita = MenuItem(
        "item-001",
        "Margherita Pizza",
        "Classic tomato and mozzarella pizza",
        Decimal('12.99'),
        FoodCategory.MAIN_COURSE,
        DietaryType.VEG,
        True,
        20
    )
    
    pepperoni = MenuItem(
        "item-002",
        "Pepperoni Pizza",
        "Pepperoni with extra cheese",
        Decimal('14.99'),
        FoodCategory.MAIN_COURSE,
        DietaryType.NON_VEG,
        True,
        20
    )
    
    garlic_bread = MenuItem(
        "item-003",
        "Garlic Bread",
        "Freshly baked garlic bread",
        Decimal('5.99'),
        FoodCategory.APPETIZER,
        DietaryType.VEG,
        True,
        10
    )
    
    soda = MenuItem(
        "item-004",
        "Soda",
        "Cold beverage",
        Decimal('1.99'),
        FoodCategory.BEVERAGE,
        DietaryType.VEG,
        True,
        2
    )
    
    pizza_menu.add_item(margherita)
    pizza_menu.add_item(pepperoni)
    pizza_menu.add_item(garlic_bread)
    pizza_menu.add_item(soda)
    
    print("\nSpice Heaven adding menu items:")
    indian_menu = spice_heaven.get_menu()
    
    butter_chicken = MenuItem(
        "item-101",
        "Butter Chicken",
        "Creamy tomato curry with chicken",
        Decimal('13.99'),
        FoodCategory.MAIN_COURSE,
        DietaryType.NON_VEG,
        True,
        25
    )
    
    paneer_tikka = MenuItem(
        "item-102",
        "Paneer Tikka Masala",
        "Indian cottage cheese in spicy gravy",
        Decimal('11.99'),
        FoodCategory.MAIN_COURSE,
        DietaryType.VEG,
        True,
        25
    )
    
    naan = MenuItem(
        "item-103",
        "Garlic Naan",
        "Indian flatbread with garlic",
        Decimal('2.99'),
        FoodCategory.APPETIZER,
        DietaryType.VEG,
        True,
        10
    )
    
    indian_menu.add_item(butter_chicken)
    indian_menu.add_item(paneer_tikka)
    indian_menu.add_item(naan)
    
    # Test Case 3: Update Menu Prices
    print_separator("Update Menu Prices and Availability")
    
    print("\nPizza Palace updates pepperoni price:")
    pizza_menu.update_item_price("item-002", Decimal('15.99'))
    
    print("\nSpice Heaven marks butter chicken as unavailable:")
    indian_menu.update_item_availability("item-101", False)
    
    print("\nAvailable items at Spice Heaven:")
    for item in indian_menu.get_available_items():
        print(f"  - {item.name}: ${item.price}")
    
    # Test Case 4: Register Customers
    print_separator("Register Customers")
    
    customer1_address = Location(37.7750, -122.4184, "100 Main St Apt 5", "San Francisco", "94102")
    customer2_address = Location(37.7850, -122.4084, "200 Oak St #12", "San Francisco", "94103")
    
    alice = Customer("cust-001", "Alice Johnson", "alice@email.com", "+1-555-0001")
    alice.add_address(customer1_address)
    
    bob = Customer("cust-002", "Bob Smith", "bob@email.com", "+1-555-0002")
    bob.add_address(customer2_address)
    
    service.register_customer(alice)
    service.register_customer(bob)
    
    # Test Case 5: Register Delivery Agents
    print_separator("Register Delivery Agents")
    
    agent1_location = Location(37.7760, -122.4190, "Near Market St", "San Francisco", "94102")
    agent2_location = Location(37.7840, -122.4100, "Near Mission St", "San Francisco", "94103")
    
    agent1 = DeliveryAgent("agent-001", "John Doe", "+1-555-1001", "Bike")
    agent1.update_location(agent1_location)
    agent1.set_status(DeliveryAgentStatus.AVAILABLE)
    
    agent2 = DeliveryAgent("agent-002", "Jane Smith", "+1-555-1002", "Scooter")
    agent2.update_location(agent2_location)
    agent2.set_status(DeliveryAgentStatus.AVAILABLE)
    
    service.register_delivery_agent(agent1)
    service.register_delivery_agent(agent2)
    
    # Test Case 6: Browse Restaurants
    print_separator("Browse Restaurants")
    
    print(f"\nAlice searching for restaurants near her location:")
    nearby_restaurants = service.search_restaurants(customer1_address, max_distance_km=5)
    
    print(f"Found {len(nearby_restaurants)} restaurants:")
    for restaurant in nearby_restaurants:
        distance = customer1_address.distance_to(restaurant.get_location())
        cuisines = ', '.join([c.value for c in restaurant.get_cuisine_types()])
        rating = restaurant.get_rating()
        print(f"  - {restaurant.get_name()}")
        print(f"    Cuisines: {cuisines}")
        print(f"    Distance: {distance:.2f} km")
        print(f"    Rating: {rating.average_rating:.1f} ({rating.total_ratings} ratings)")
        print(f"    Delivery Fee: ${restaurant.get_delivery_fee()}")
    
    # Test Case 7: Create and Place Order
    print_separator("Create and Place Order")
    
    print("\nAlice creates an order from Pizza Palace:")
    order1 = service.create_order("cust-001", "rest-001", customer1_address)
    
    if order1:
        print(f"\nAdding items to order:")
        order1.add_item(margherita, 2)
        order1.add_item(garlic_bread, 1)
        order1.add_item(soda, 2)
        
        print(f"\nOrder Summary:")
        print(f"  Items:")
        for item in order1.get_items():
            print(f"    - {item.menu_item.name} x{item.quantity} = ${item.get_subtotal()}")
        print(f"  Subtotal: ${order1.get_subtotal()}")
        print(f"  Delivery Fee: ${order1.get_delivery_fee()}")
        print(f"  Tax: ${order1.get_tax()}")
        print(f"  Total: ${order1.get_total()}")
        
        # Set payment method and place order
        order1.set_payment_method(PaymentMethod.CREDIT_CARD)
        service.place_order(order1.get_id())
    
    # Test Case 8: Restaurant Prepares Order
    print_separator("Restaurant Prepares Order")
    
    print(f"\nRestaurant confirms and prepares order:")
    order1.start_preparation()
    
    print(f"\nOrder ready for pickup:")
    order1.mark_ready_for_pickup()
    
    # Test Case 9: Assign Delivery Agent
    print_separator("Assign Delivery Agent")
    
    print(f"\nAssigning delivery agent to order:")
    service.assign_delivery_agent_to_order(order1.get_id())
    
    # Test Case 10: Track Order
    print_separator("Track Order")
    
    print(f"\nAlice tracks her order:")
    tracking = service.track_order(order1.get_id())
    
    print(f"Order ID: {tracking['order_id']}")
    print(f"Restaurant: {tracking['restaurant']}")
    print(f"Status: {tracking['status']}")
    print(f"Total: ${tracking['total']}")
    print(f"Estimated Delivery: {tracking['estimated_delivery'].strftime('%I:%M %p')}")
    
    if 'delivery_agent' in tracking:
        print(f"\nDelivery Agent:")
        print(f"  Name: {tracking['delivery_agent']['name']}")
        print(f"  Phone: {tracking['delivery_agent']['phone']}")
        print(f"  Rating: {tracking['delivery_agent']['rating']:.1f}")
    
    print(f"\nOrder Status History:")
    for status_entry in tracking['status_history']:
        print(f"  - {status_entry['timestamp']}: {status_entry['status']}")
    
    # Test Case 11: Complete Delivery
    print_separator("Complete Delivery")
    
    print(f"\nDelivery agent picks up order:")
    order1.mark_picked_up()
    
    print(f"\nDelivery agent delivers order:")
    service.complete_order_delivery(order1.get_id())
    
    # Test Case 12: Multiple Orders
    print_separator("Multiple Concurrent Orders")
    
    print("\nBob creates an order from Spice Heaven:")
    order2 = service.create_order("cust-002", "rest-002", customer2_address)
    
    if order2:
        order2.add_item(paneer_tikka, 2)
        order2.add_item(naan, 3)
        
        print(f"Order total: ${order2.get_total()}")
        
        order2.set_payment_method(PaymentMethod.UPI)
        service.place_order(order2.get_id())
    
    print("\nAlice creates another order from Pizza Palace:")
    order3 = service.create_order("cust-001", "rest-001", customer1_address)
    
    if order3:
        order3.add_item(pepperoni, 1)
        order3.add_item(soda, 1)
        
        print(f"Order total: ${order3.get_total()}")
        
        order3.set_payment_method(PaymentMethod.WALLET)
        service.place_order(order3.get_id())
    
    # Test Case 13: Cancel Order
    print_separator("Cancel Order")
    
    print("\nAlice decides to cancel her second order:")
    service.cancel_order(order3.get_id(), "Changed my mind")
    
    # Test Case 14: Customer Order History
    print_separator("Customer Order History")
    
    print("\nAlice's order history:")
    alice_orders = service.get_customer_orders("cust-001")
    for order in alice_orders:
        print(f"  Order {order.get_id()[:8]}...")
        print(f"    Restaurant: {order.get_restaurant().get_name()}")
        print(f"    Status: {order.get_status().value}")
        print(f"    Total: ${order.get_total()}")
        print(f"    Date: {order._created_at.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    # Test Case 15: Restaurant Order Management
    print_separator("Restaurant Order Management")
    
    print("\nPizza Palace viewing active orders:")
    active_orders = service.get_restaurant_orders("rest-001", OrderStatus.PLACED)
    print(f"Active orders: {len(active_orders)}")
    
    print("\nAll orders for Pizza Palace:")
    all_orders = service.get_restaurant_orders("rest-001")
    for order in all_orders:
        print(f"  Order {order.get_id()[:8]}... - {order.get_status().value} - ${order.get_total()}")
    
    # Test Case 16: Search Menu Items
    print_separator("Search Menu Items")
    
    print("\nSearching for vegetarian items at Pizza Palace:")
    veg_items = pizza_menu.search_items(dietary_type=DietaryType.VEG)
    for item in veg_items:
        print(f"  - {item.name}: ${item.price}")
    
    print("\nSearching for 'pizza' at Pizza Palace:")
    pizza_items = pizza_menu.search_items(query="pizza")
    for item in pizza_items:
        print(f"  - {item.name}: ${item.price}")
    
    # Test Case 17: Ratings
    print_separator("Ratings and Reviews")
    
    print("\nAlice rates Pizza Palace and delivery agent:")
    pizza_palace.add_rating(4.5)
    agent1.add_rating(5.0)
    
    print(f"Pizza Palace rating: {pizza_palace.get_rating().average_rating:.1f} "
          f"({pizza_palace.get_rating().total_ratings} ratings)")
    print(f"Agent {agent1.get_name()} rating: {agent1.get_rating():.1f} "
          f"({agent1._total_ratings} ratings)")
    
    # Test Case 18: Delivery Agent Performance
    print_separator("Delivery Agent Performance")
    
    print(f"\nDelivery agent statistics:")
    for agent_id, agent in service._delivery_agents.items():
        print(f"  {agent.get_name()}:")
        print(f"    Status: {agent.get_status().value}")
        print(f"    Completed Deliveries: {agent.get_completed_deliveries()}")
        print(f"    Rating: {agent.get_rating():.1f}")
    
    # Test Case 19: Update Item in Cart
    print_separator("Update Cart Items")
    
    print("\nAlice creates a new order and modifies cart:")
    order4 = service.create_order("cust-001", "rest-001", customer1_address)
    
    if order4:
        print("Adding items:")
        order4.add_item(margherita, 1)
        order4.add_item(pepperoni, 1)
        
        print(f"\nCart items:")
        for item in order4.get_items():
            print(f"  - {item.menu_item.name} x{item.quantity}")
        
        print("\nUpdating pepperoni quantity to 3:")
        order4.update_item_quantity("item-002", 3)
        
        print(f"\nUpdated cart:")
        for item in order4.get_items():
            print(f"  - {item.menu_item.name} x{item.quantity}")
        
        print(f"\nNew total: ${order4.get_total()}")
        
        print("\nRemoving margherita:")
        order4.remove_item("item-001")
        
        print(f"\nFinal cart:")
        for item in order4.get_items():
            print(f"  - {item.menu_item.name} x{item.quantity}")
        print(f"Final total: ${order4.get_total()}")
    
    # Test Case 20: System Statistics
    print_separator("System Statistics")
    
    stats = service.get_system_stats()
    print(f"\nSystem-wide Statistics:")
    print(f"  Total Restaurants: {stats['total_restaurants']}")
    print(f"  Total Customers: {stats['total_customers']}")
    print(f"  Total Delivery Agents: {stats['total_delivery_agents']}")
    print(f"  Available Agents: {stats['available_agents']}")
    print(f"  Total Orders: {stats['total_orders']}")
    print(f"  Active Orders: {stats['active_orders']}")
    print(f"  Completed Orders: {stats['completed_orders']}")
    print(f"  Total Revenue: ${stats['total_revenue']}")
    
    # Test Case 21: Different Delivery Assignment Strategies
    print_separator("Delivery Assignment Strategies")
    
    print("\nSwitching to highest-rated agent strategy:")
    service.set_delivery_strategy(HighestRatedAgentStrategy())
    
    # Add more ratings to differentiate agents
    agent1.add_rating(4.8)
    agent1.add_rating(4.9)
    agent2.add_rating(4.5)
    
    print(f"Agent ratings:")
    print(f"  {agent1.get_name()}: {agent1.get_rating():.2f}")
    print(f"  {agent2.get_name()}: {agent2.get_rating():.2f}")
    
    # Make agent1 available again
    agent1.set_status(DeliveryAgentStatus.AVAILABLE)
    
    order5 = service.create_order("cust-002", "rest-002", customer2_address)
    if order5:
        order5.add_item(paneer_tikka, 1)
        order5.set_payment_method(PaymentMethod.CREDIT_CARD)
        service.place_order(order5.get_id())
        order5.mark_ready_for_pickup()
        
        print(f"\nAssigning agent using highest-rated strategy:")
        service.assign_delivery_agent_to_order(order5.get_id())
    
    # Test Case 22: Cash on Delivery
    print_separator("Cash on Delivery Payment")
    
    print("\nBob places order with COD:")
    order6 = service.create_order("cust-002", "rest-001", customer2_address)
    
    if order6:
        order6.add_item(margherita, 1)
        order6.set_payment_method(PaymentMethod.CASH_ON_DELIVERY)
        
        print(f"Payment method: {order6._payment_method.value}")
        service.place_order(order6.get_id())
        
        print(f"Payment status after placing order: {order6._payment_status.value}")
        
        # Complete delivery
        order6.start_preparation()
        order6.mark_ready_for_pickup()
        
        agent2.set_status(DeliveryAgentStatus.AVAILABLE)
        service.assign_delivery_agent_to_order(order6.get_id())
        order6.mark_picked_up()
        service.complete_order_delivery(order6.get_id())
        
        print(f"Payment status after delivery: {order6._payment_status.value}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# Strategy Pattern - Different delivery assignment strategies (NearestAgentStrategy, HighestRatedAgentStrategy) can be swapped at runtime
# State Pattern - Order progresses through well-defined states with controlled transitions
# Service Layer Pattern - FoodDeliveryService acts as the central coordinator

# Key Features Implemented:

# Browse Restaurants and Place Orders:

# Location-based restaurant search
# Filter by cuisine, distance, rating
# Menu browsing with search and filters
# Shopping cart functionality
# Order placement with validation


# Restaurant Menu Management:

# Add/remove menu items
# Update prices dynamically
# Control item availability
# Categorize items (appetizer, main course, etc.)
# Dietary classifications (veg, non-veg, vegan)


# Delivery Agent Management:

# Agent registration and status tracking
# Location tracking
# Availability management
# Multiple assignment strategies
# Performance metrics (completed deliveries, ratings)


# Order Tracking:

# Real-time status updates
# Complete status history
# Delivery agent information
# Estimated delivery time
# Detailed tracking information


# Payment Processing:

# Multiple payment methods (card, UPI, wallet, COD)
# Payment authorization and capture
# Refund processing
# Transaction tracking



# Additional Features:

# Multi-currency pricing with Decimal for accuracy
# Distance calculation using Haversine formula
# Ratings system for restaurants and agents
# Order modification before placement
