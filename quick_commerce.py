from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta, time
from decimal import Decimal
from dataclasses import dataclass
import uuid
import random


# ==================== Enums ====================

class ProductCategory(Enum):
    """Product categories"""
    FRESH_PRODUCE = "fresh_produce"
    DAIRY = "dairy"
    SNACKS = "snacks"
    BEVERAGES = "beverages"
    FROZEN = "frozen"
    BAKERY = "bakery"
    PERSONAL_CARE = "personal_care"
    HOUSEHOLD = "household"
    BABY_CARE = "baby_care"
    HEALTH = "health"
    ELECTRONICS = "electronics"
    STATIONERY = "stationery"


class OrderStatus(Enum):
    """Order lifecycle status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PICKING = "picking"
    PACKED = "packed"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentMethod(Enum):
    """Payment methods"""
    CASH_ON_DELIVERY = "cash_on_delivery"
    CARD = "card"
    UPI = "upi"
    WALLET = "wallet"
    NET_BANKING = "net_banking"


class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class DarkStoreStatus(Enum):
    """Dark store operational status"""
    ACTIVE = "active"
    BUSY = "busy"  # High order volume
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class DeliveryPartnerStatus(Enum):
    """Delivery partner availability"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_BREAK = "on_break"


class VehicleType(Enum):
    """Delivery vehicle types"""
    BIKE = "bike"
    SCOOTER = "scooter"
    BICYCLE = "bicycle"
    ELECTRIC_SCOOTER = "electric_scooter"


# ==================== Models ====================

class Location:
    """Geographic location"""
    
    def __init__(self, latitude: float, longitude: float, address: str,
                 city: str, pincode: str, landmark: Optional[str] = None):
        self._latitude = latitude
        self._longitude = longitude
        self._address = address
        self._city = city
        self._pincode = pincode
        self._landmark = landmark
    
    def get_coordinates(self) -> Tuple[float, float]:
        return (self._latitude, self._longitude)
    
    def get_address(self) -> str:
        return self._address
    
    def get_full_address(self) -> str:
        parts = [self._address, self._city, self._pincode]
        if self._landmark:
            parts.insert(1, f"Near {self._landmark}")
        return ", ".join(parts)
    
    def calculate_distance(self, other: 'Location') -> float:
        """Calculate distance in km (simplified Haversine)"""
        lat_diff = abs(self._latitude - other._latitude)
        lon_diff = abs(self._longitude - other._longitude)
        # Very simplified - in production use proper Haversine
        return ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111  # km
    
    def to_dict(self) -> Dict:
        return {
            'address': self._address,
            'city': self._city,
            'pincode': self._pincode,
            'landmark': self._landmark,
            'coordinates': f"{self._latitude}, {self._longitude}"
        }


class Customer:
    """Customer using the service"""
    
    def __init__(self, customer_id: str, name: str, phone: str, email: str):
        self._customer_id = customer_id
        self._name = name
        self._phone = phone
        self._email = email
        self._saved_addresses: List[Location] = []
        self._created_at = datetime.now()
        self._total_orders = 0
        self._is_premium = False
    
    def get_id(self) -> str:
        return self._customer_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_phone(self) -> str:
        return self._phone
    
    def add_address(self, address: Location) -> None:
        self._saved_addresses.append(address)
    
    def get_addresses(self) -> List[Location]:
        return self._saved_addresses
    
    def increment_orders(self) -> None:
        self._total_orders += 1
    
    def to_dict(self) -> Dict:
        return {
            'customer_id': self._customer_id,
            'name': self._name,
            'phone': self._phone,
            'email': self._email,
            'total_orders': self._total_orders,
            'is_premium': self._is_premium
        }


class Product:
    """Product available in dark stores"""
    
    def __init__(self, product_id: str, name: str, category: ProductCategory,
                 brand: str, mrp: Decimal, selling_price: Decimal,
                 weight: str, barcode: str):
        self._product_id = product_id
        self._name = name
        self._category = category
        self._brand = brand
        self._mrp = mrp
        self._selling_price = selling_price
        self._weight = weight  # e.g., "500g", "1L"
        self._barcode = barcode
        self._image_url: Optional[str] = None
        self._is_active = True
        
        # Attributes
        self._requires_cold_storage = category in [
            ProductCategory.DAIRY, ProductCategory.FROZEN, ProductCategory.FRESH_PRODUCE
        ]
        self._is_fragile = category in [ProductCategory.BEVERAGES, ProductCategory.ELECTRONICS]
    
    def get_id(self) -> str:
        return self._product_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_category(self) -> ProductCategory:
        return self._category
    
    def get_selling_price(self) -> Decimal:
        return self._selling_price
    
    def get_discount_percentage(self) -> Decimal:
        if self._mrp == 0:
            return Decimal(0)
        return ((self._mrp - self._selling_price) / self._mrp) * 100
    
    def requires_cold_storage(self) -> bool:
        return self._requires_cold_storage
    
    def to_dict(self) -> Dict:
        return {
            'product_id': self._product_id,
            'name': self._name,
            'category': self._category.value,
            'brand': self._brand,
            'mrp': float(self._mrp),
            'selling_price': float(self._selling_price),
            'discount': f"{self.get_discount_percentage():.0f}%",
            'weight': self._weight,
            'barcode': self._barcode
        }


class InventoryItem:
    """Inventory tracking for a product in a dark store"""
    
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = quantity
        self._reserved_quantity = 0  # Reserved for ongoing orders
        self._min_threshold = 10  # Reorder when below this
        self._last_restocked = datetime.now()
    
    def get_product(self) -> Product:
        return self._product
    
    def get_available_quantity(self) -> int:
        """Available quantity = Total - Reserved"""
        return max(0, self._quantity - self._reserved_quantity)
    
    def get_total_quantity(self) -> int:
        return self._quantity
    
    def is_available(self, requested_qty: int = 1) -> bool:
        return self.get_available_quantity() >= requested_qty
    
    def reserve(self, quantity: int) -> bool:
        """Reserve quantity for an order"""
        if self.get_available_quantity() >= quantity:
            self._reserved_quantity += quantity
            return True
        return False
    
    def release_reservation(self, quantity: int) -> None:
        """Release reserved quantity (order cancelled)"""
        self._reserved_quantity = max(0, self._reserved_quantity - quantity)
    
    def fulfill(self, quantity: int) -> bool:
        """Fulfill order - reduce actual quantity"""
        if self._quantity >= quantity and self._reserved_quantity >= quantity:
            self._quantity -= quantity
            self._reserved_quantity -= quantity
            return True
        return False
    
    def restock(self, quantity: int) -> None:
        """Add stock"""
        self._quantity += quantity
        self._last_restocked = datetime.now()
    
    def needs_reorder(self) -> bool:
        """Check if stock needs replenishment"""
        return self._quantity <= self._min_threshold
    
    def to_dict(self) -> Dict:
        return {
            'product': self._product.get_name(),
            'total_quantity': self._quantity,
            'reserved': self._reserved_quantity,
            'available': self.get_available_quantity(),
            'needs_reorder': self.needs_reorder()
        }


class DarkStore:
    """Micro-fulfillment center / Dark store"""
    
    def __init__(self, store_id: str, name: str, location: Location):
        self._store_id = store_id
        self._name = name
        self._location = location
        self._status = DarkStoreStatus.ACTIVE
        
        # Inventory management
        self._inventory: Dict[str, InventoryItem] = {}  # product_id -> InventoryItem
        
        # Operational details
        self._service_radius_km = 3.0  # 3km delivery radius
        self._max_concurrent_orders = 20
        self._current_order_count = 0
        
        # Operating hours
        self._opening_time = time(6, 0)  # 6 AM
        self._closing_time = time(23, 0)  # 11 PM
        
        # Performance metrics
        self._total_orders_fulfilled = 0
        self._average_picking_time_minutes = 3.0
        
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._store_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_location(self) -> Location:
        return self._location
    
    def get_status(self) -> DarkStoreStatus:
        return self._status
    
    def is_operational(self) -> bool:
        """Check if store is currently operational"""
        if self._status != DarkStoreStatus.ACTIVE:
            return False
        
        # Check operating hours
        current_time = datetime.now().time()
        if not (self._opening_time <= current_time <= self._closing_time):
            return False
        
        return True
    
    def can_serve_location(self, customer_location: Location) -> bool:
        """Check if customer location is within service radius"""
        distance = self._location.calculate_distance(customer_location)
        return distance <= self._service_radius_km
    
    def can_accept_order(self) -> bool:
        """Check if store can accept new orders"""
        if not self.is_operational():
            return False
        
        if self._current_order_count >= self._max_concurrent_orders:
            return False
        
        return True
    
    def add_product(self, product: Product, quantity: int) -> None:
        """Add product to inventory"""
        if product.get_id() in self._inventory:
            self._inventory[product.get_id()].restock(quantity)
        else:
            self._inventory[product.get_id()] = InventoryItem(product, quantity)
    
    def get_inventory_item(self, product_id: str) -> Optional[InventoryItem]:
        return self._inventory.get(product_id)
    
    def check_availability(self, product_id: str, quantity: int = 1) -> bool:
        """Check if product is available in required quantity"""
        item = self._inventory.get(product_id)
        if not item:
            return False
        return item.is_available(quantity)
    
    def get_available_products(self) -> List[Product]:
        """Get all products currently in stock"""
        available = []
        for item in self._inventory.values():
            if item.is_available():
                available.append(item.get_product())
        return available
    
    def search_products(self, query: str, category: Optional[ProductCategory] = None) -> List[Product]:
        """Search products by name or category"""
        results = []
        query_lower = query.lower()
        
        for item in self._inventory.values():
            if not item.is_available():
                continue
            
            product = item.get_product()
            
            # Category filter
            if category and product.get_category() != category:
                continue
            
            # Name match
            if query_lower in product.get_name().lower():
                results.append(product)
        
        return results
    
    def get_low_stock_items(self) -> List[InventoryItem]:
        """Get items that need restocking"""
        return [item for item in self._inventory.values() if item.needs_reorder()]
    
    def increment_order_count(self) -> None:
        self._current_order_count += 1
        if self._current_order_count >= self._max_concurrent_orders * 0.8:
            self._status = DarkStoreStatus.BUSY
    
    def decrement_order_count(self) -> None:
        self._current_order_count = max(0, self._current_order_count - 1)
        if self._current_order_count < self._max_concurrent_orders * 0.8:
            if self._status == DarkStoreStatus.BUSY:
                self._status = DarkStoreStatus.ACTIVE
    
    def to_dict(self) -> Dict:
        return {
            'store_id': self._store_id,
            'name': self._name,
            'location': self._location.to_dict(),
            'status': self._status.value,
            'service_radius_km': self._service_radius_km,
            'current_orders': self._current_order_count,
            'max_capacity': self._max_concurrent_orders,
            'total_products': len(self._inventory),
            'low_stock_items': len(self.get_low_stock_items()),
            'operating_hours': f"{self._opening_time.strftime('%H:%M')} - {self._closing_time.strftime('%H:%M')}"
        }


class OrderItem:
    """Item in an order"""
    
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = quantity
        self._price_at_order = product.get_selling_price()
    
    def get_product(self) -> Product:
        return self._product
    
    def get_quantity(self) -> int:
        return self._quantity
    
    def get_subtotal(self) -> Decimal:
        return self._price_at_order * self._quantity
    
    def to_dict(self) -> Dict:
        return {
            'product': self._product.get_name(),
            'quantity': self._quantity,
            'price': float(self._price_at_order),
            'subtotal': float(self.get_subtotal())
        }


class DeliveryPartner:
    """Delivery executive"""
    
    def __init__(self, partner_id: str, name: str, phone: str,
                 vehicle_type: VehicleType):
        self._partner_id = partner_id
        self._name = name
        self._phone = phone
        self._vehicle_type = vehicle_type
        self._status = DeliveryPartnerStatus.AVAILABLE
        self._current_location: Optional[Location] = None
        self._assigned_dark_store_id: Optional[str] = None
        
        # Performance metrics
        self._total_deliveries = 0
        self._average_delivery_time_minutes = 0.0
        self._rating = Decimal(0)
        self._rating_count = 0
        
        self._joined_at = datetime.now()
    
    def get_id(self) -> str:
        return self._partner_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_status(self) -> DeliveryPartnerStatus:
        return self._status
    
    def is_available(self) -> bool:
        return self._status == DeliveryPartnerStatus.AVAILABLE
    
    def assign_to_store(self, store_id: str) -> None:
        self._assigned_dark_store_id = store_id
    
    def get_assigned_store(self) -> Optional[str]:
        return self._assigned_dark_store_id
    
    def set_status(self, status: DeliveryPartnerStatus) -> None:
        self._status = status
    
    def update_location(self, location: Location) -> None:
        self._current_location = location
    
    def complete_delivery(self, delivery_time_minutes: float) -> None:
        """Update metrics after delivery"""
        self._total_deliveries += 1
        
        # Update average delivery time
        total_time = self._average_delivery_time_minutes * (self._total_deliveries - 1)
        self._average_delivery_time_minutes = (total_time + delivery_time_minutes) / self._total_deliveries
    
    def add_rating(self, rating: int) -> None:
        """Add customer rating (1-5)"""
        total_rating = float(self._rating) * self._rating_count
        self._rating_count += 1
        self._rating = Decimal((total_rating + rating) / self._rating_count)
    
    def to_dict(self) -> Dict:
        return {
            'partner_id': self._partner_id,
            'name': self._name,
            'phone': self._phone,
            'vehicle': self._vehicle_type.value,
            'status': self._status.value,
            'total_deliveries': self._total_deliveries,
            'avg_delivery_time': f"{self._average_delivery_time_minutes:.1f} min",
            'rating': f"{self._rating:.1f}/5.0" if self._rating_count > 0 else "No ratings"
        }


class Order:
    """Customer order"""
    
    def __init__(self, order_id: str, customer: Customer,
                 delivery_address: Location, dark_store: DarkStore):
        self._order_id = order_id
        self._customer = customer
        self._delivery_address = delivery_address
        self._dark_store = dark_store
        
        # Order details
        self._items: List[OrderItem] = []
        self._status = OrderStatus.PENDING
        
        # Pricing
        self._item_total = Decimal(0)
        self._delivery_fee = Decimal(0)
        self._platform_fee = Decimal(5)  # Fixed platform fee
        self._discount = Decimal(0)
        self._total_amount = Decimal(0)
        
        # Payment
        self._payment_method: Optional[PaymentMethod] = None
        self._payment_status = PaymentStatus.PENDING
        
        # Delivery
        self._delivery_partner: Optional[DeliveryPartner] = None
        self._estimated_delivery_time: Optional[datetime] = None
        self._actual_delivery_time: Optional[datetime] = None
        
        # Timestamps
        self._created_at = datetime.now()
        self._confirmed_at: Optional[datetime] = None
        self._picking_started_at: Optional[datetime] = None
        self._packed_at: Optional[datetime] = None
        self._dispatched_at: Optional[datetime] = None
        self._delivered_at: Optional[datetime] = None
        
        # Delivery promise
        self._delivery_promise_minutes = 15  # 15 minute delivery
        
        # Notes
        self._delivery_instructions: Optional[str] = None
        self._cancellation_reason: Optional[str] = None
    
    def get_id(self) -> str:
        return self._order_id
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def get_dark_store(self) -> DarkStore:
        return self._dark_store
    
    def get_status(self) -> OrderStatus:
        return self._status
    
    def add_item(self, product: Product, quantity: int) -> bool:
        """Add item to order"""
        # Check inventory availability
        if not self._dark_store.check_availability(product.get_id(), quantity):
            return False
        
        self._items.append(OrderItem(product, quantity))
        self._calculate_totals()
        return True
    
    def get_items(self) -> List[OrderItem]:
        return self._items
    
    def _calculate_totals(self) -> None:
        """Calculate order totals"""
        self._item_total = sum(item.get_subtotal() for item in self._items)
        
        # Calculate delivery fee (free for orders above certain amount)
        if self._item_total >= 99:
            self._delivery_fee = Decimal(0)
        else:
            self._delivery_fee = Decimal(25)
        
        self._total_amount = (
            self._item_total + 
            self._delivery_fee + 
            self._platform_fee - 
            self._discount
        )
    
    def apply_discount(self, discount: Decimal) -> None:
        self._discount = discount
        self._calculate_totals()
    
    def get_total_amount(self) -> Decimal:
        return self._total_amount
    
    def set_payment_method(self, method: PaymentMethod) -> None:
        self._payment_method = method
    
    def set_delivery_instructions(self, instructions: str) -> None:
        self._delivery_instructions = instructions
    
    def confirm_order(self) -> bool:
        """Confirm order and reserve inventory"""
        if self._status != OrderStatus.PENDING:
            return False
        
        # Reserve inventory for all items
        for item in self._items:
            inventory_item = self._dark_store.get_inventory_item(item.get_product().get_id())
            if not inventory_item or not inventory_item.reserve(item.get_quantity()):
                # Rollback reservations
                for prev_item in self._items:
                    if prev_item == item:
                        break
                    prev_inv = self._dark_store.get_inventory_item(prev_item.get_product().get_id())
                    if prev_inv:
                        prev_inv.release_reservation(prev_item.get_quantity())
                return False
        
        self._status = OrderStatus.CONFIRMED
        self._confirmed_at = datetime.now()
        self._estimated_delivery_time = datetime.now() + timedelta(minutes=self._delivery_promise_minutes)
        
        self._dark_store.increment_order_count()
        self._customer.increment_orders()
        
        return True
    
    def start_picking(self) -> None:
        if self._status == OrderStatus.CONFIRMED:
            self._status = OrderStatus.PICKING
            self._picking_started_at = datetime.now()
    
    def mark_packed(self) -> None:
        """Mark order as packed"""
        if self._status == OrderStatus.PICKING:
            self._status = OrderStatus.PACKED
            self._packed_at = datetime.now()
            
            # Fulfill inventory (reduce actual stock)
            for item in self._items:
                inventory_item = self._dark_store.get_inventory_item(item.get_product().get_id())
                if inventory_item:
                    inventory_item.fulfill(item.get_quantity())
    
    def assign_delivery_partner(self, partner: DeliveryPartner) -> bool:
        """Assign delivery partner"""
        if self._status != OrderStatus.PACKED:
            return False
        
        if not partner.is_available():
            return False
        
        self._delivery_partner = partner
        partner.set_status(DeliveryPartnerStatus.BUSY)
        return True
    
    def dispatch(self) -> bool:
        """Dispatch order for delivery"""
        if self._status != OrderStatus.PACKED or not self._delivery_partner:
            return False
        
        self._status = OrderStatus.OUT_FOR_DELIVERY
        self._dispatched_at = datetime.now()
        return True
    
    def mark_delivered(self) -> bool:
        """Mark order as delivered"""
        if self._status != OrderStatus.OUT_FOR_DELIVERY:
            return False
        
        self._status = OrderStatus.DELIVERED
        self._delivered_at = datetime.now()
        self._payment_status = PaymentStatus.COMPLETED
        
        # Update delivery partner
        if self._delivery_partner:
            delivery_time = (self._delivered_at - self._dispatched_at).total_seconds() / 60
            self._delivery_partner.complete_delivery(delivery_time)
            self._delivery_partner.set_status(DeliveryPartnerStatus.AVAILABLE)
        
        # Update dark store
        self._dark_store.decrement_order_count()
        
        return True
    
    def cancel(self, reason: str) -> bool:
        """Cancel order"""
        if self._status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            return False
        
        # Release inventory reservations
        if self._status in [OrderStatus.CONFIRMED, OrderStatus.PICKING]:
            for item in self._items:
                inventory_item = self._dark_store.get_inventory_item(item.get_product().get_id())
                if inventory_item:
                    inventory_item.release_reservation(item.get_quantity())
        
        # Restock if already fulfilled
        if self._status in [OrderStatus.PACKED, OrderStatus.OUT_FOR_DELIVERY]:
            for item in self._items:
                inventory_item = self._dark_store.get_inventory_item(item.get_product().get_id())
                if inventory_item:
                    inventory_item.restock(item.get_quantity())
        
        self._status = OrderStatus.CANCELLED
        self._cancellation_reason = reason
        self._dark_store.decrement_order_count()
        
        # Release delivery partner
        if self._delivery_partner:
            self._delivery_partner.set_status(DeliveryPartnerStatus.AVAILABLE)
        
        return True
    
    def get_delivery_time_minutes(self) -> Optional[float]:
        """Get actual delivery time"""
        if self._delivered_at and self._created_at:
            return (self._delivered_at - self._created_at).total_seconds() / 60
        return None
    
    def is_delayed(self) -> bool:
        """Check if delivery is delayed"""
        if self._estimated_delivery_time and not self._delivered_at:
            return datetime.now() > self._estimated_delivery_time
        return False
    
    def to_dict(self) -> Dict:
        return {
            'order_id': self._order_id,
            'customer': self._customer.get_name(),
            'dark_store': self._dark_store.get_name(),
            'status': self._status.value,
            'items': [item.to_dict() for item in self._items],
            'pricing': {
                'item_total': float(self._item_total),
                'delivery_fee': float(self._delivery_fee),
                'platform_fee': float(self._platform_fee),
                'discount': float(self._discount),
                'total': float(self._total_amount)
            },
            'payment_method': self._payment_method.value if self._payment_method else None,
            'payment_status': self._payment_status.value,
            'delivery_partner': self._delivery_partner.get_name() if self._delivery_partner else None,
            'estimated_delivery': self._estimated_delivery_time.strftime('%H:%M') if self._estimated_delivery_time else None,
            'created_at': self._created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'delivery_time': f"{self.get_delivery_time_minutes():.1f} min" if self.get_delivery_time_minutes() else None,
            'is_delayed': self.is_delayed()
        }


# ==================== Quick Delivery Service ====================

class QuickDeliveryService:
    """
    Main Quick Delivery Service (10-15 minute delivery)
    
    Key Features:
    - Dark store network management
    - Real-time inventory tracking
    - Intelligent store selection based on location
    - 15-minute delivery promise
    - Delivery partner assignment
    - Demand prediction
    - Low stock alerts
    """
    
    def __init__(self, service_name: str = "QuickMart"):
        self._service_name = service_name
        
        # Core entities
        self._customers: Dict[str, Customer] = {}
        self._dark_stores: Dict[str, DarkStore] = {}
        self._products: Dict[str, Product] = {}
        self._delivery_partners: Dict[str, DeliveryPartner] = {}
        self._orders: Dict[str, Order] = {}
        
        # Indexes for fast lookup
        self._orders_by_customer: Dict[str, List[str]] = {}
        self._partners_by_store: Dict[str, List[str]] = {}
        self._active_orders: Set[str] = set()
        
        # Configuration
        self._max_delivery_time_minutes = 15
        self._free_delivery_threshold = Decimal(99)
    
    # ==================== Customer Management ====================
    
    def register_customer(self, name: str, phone: str, email: str) -> Customer:
        """Register new customer"""
        customer_id = str(uuid.uuid4())
        customer = Customer(customer_id, name, phone, email)
        
        self._customers[customer_id] = customer
        self._orders_by_customer[customer_id] = []
        
        print(f"✅ Customer registered: {name}")
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)
    
    # ==================== Dark Store Management ====================
    
    def add_dark_store(self, name: str, location: Location) -> DarkStore:
        """Add new dark store"""
        store_id = str(uuid.uuid4())
        store = DarkStore(store_id, name, location)
        
        self._dark_stores[store_id] = store
        self._partners_by_store[store_id] = []
        
        print(f"✅ Dark store added: {name}")
        return store
    
    def get_dark_store(self, store_id: str) -> Optional[DarkStore]:
        return self._dark_stores.get(store_id)
    
    def find_nearest_dark_store(self, customer_location: Location,
                               required_products: Optional[List[str]] = None) -> Optional[DarkStore]:
        """Find nearest dark store that can serve location and has products"""
        eligible_stores = []
        
        for store in self._dark_stores.values():
            # Check if operational and can serve location
            if not store.is_operational():
                continue
            
            if not store.can_serve_location(customer_location):
                continue
            
            if not store.can_accept_order():
                continue
            
            # Check product availability if specified
            if required_products:
                all_available = all(
                    store.check_availability(pid) for pid in required_products
                )
                if not all_available:
                    continue
            
            distance = store.get_location().calculate_distance(customer_location)
            eligible_stores.append((store, distance))
        
        if not eligible_stores:
            return None
        
        # Sort by distance and return nearest
        eligible_stores.sort(key=lambda x: x[1])
        return eligible_stores[0][0]
    
    # ==================== Product Management ====================
    
    def add_product(self, name: str, category: ProductCategory, brand: str,
                   mrp: Decimal, selling_price: Decimal, weight: str) -> Product:
        """Add product to catalog"""
        product_id = str(uuid.uuid4())
        barcode = f"BAR{random.randint(100000000000, 999999999999)}"
        
        product = Product(product_id, name, category, brand, mrp, selling_price, weight, barcode)
        self._products[product_id] = product
        
        print(f"✅ Product added: {name}")
        return product
    
    def stock_product_in_store(self, product_id: str, store_id: str, quantity: int) -> bool:
        """Add product stock to a dark store"""
        product = self._products.get(product_id)
        store = self._dark_stores.get(store_id)
        
        if not product or not store:
            return False
        
        store.add_product(product, quantity)
        return True
    
    # ==================== Delivery Partner Management ====================
    
    def onboard_delivery_partner(self, name: str, phone: str,
                                 vehicle_type: VehicleType,
                                 assigned_store_id: str) -> Optional[DeliveryPartner]:
        """Onboard new delivery partner"""
        partner_id = str(uuid.uuid4())
        partner = DeliveryPartner(partner_id, name, phone, vehicle_type)
        
        if assigned_store_id not in self._dark_stores:
            return None
        
        partner.assign_to_store(assigned_store_id)
        
        self._delivery_partners[partner_id] = partner
        self._partners_by_store[assigned_store_id].append(partner_id)
        
        print(f"✅ Delivery partner onboarded: {name}")
        return partner
    
    def get_available_partner(self, store_id: str) -> Optional[DeliveryPartner]:
        """Get available delivery partner for a store"""
        partner_ids = self._partners_by_store.get(store_id, [])
        
        for partner_id in partner_ids:
            partner = self._delivery_partners.get(partner_id)
            if partner and partner.is_available():
                return partner
        
        return None
    
    # ==================== Order Management ====================
    
    def create_order(self, customer_id: str, delivery_address: Location) -> Optional[Order]:
        """Create new order"""
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        
        # Find nearest dark store
        dark_store = self.find_nearest_dark_store(delivery_address)
        if not dark_store:
            print("❌ No dark store available in your area")
            return None
        
        order_id = f"ORD{random.randint(100000, 999999)}"
        order = Order(order_id, customer, delivery_address, dark_store)
        
        self._orders[order_id] = order
        self._orders_by_customer[customer_id].append(order_id)
        
        print(f"✅ Order created: {order_id}")
        print(f"   Assigned store: {dark_store.get_name()}")
        
        return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)
    
    def confirm_and_process_order(self, order_id: str, payment_method: PaymentMethod) -> bool:
        """Confirm order and start processing"""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        # Set payment method
        order.set_payment_method(payment_method)
        
        # Confirm order (reserves inventory)
        if not order.confirm_order():
            print("❌ Failed to confirm order - inventory not available")
            return False
        
        self._active_orders.add(order_id)
        
        print(f"✅ Order confirmed: {order_id}")
        print(f"   Estimated delivery: {order._estimated_delivery_time.strftime('%H:%M')}")
        
        # Auto-start picking (in real system, this would be done by store staff)
        self._auto_process_order(order)
        
        return True
    
    def _auto_process_order(self, order: Order) -> None:
        """Auto-process order (simulate picking and packing)"""
        # Start picking
        order.start_picking()
        print(f"📦 Picking started for {order.get_id()}")
        
        # Simulate picking time (1-2 minutes)
        # In real system, this would be done by store staff
        
        # Mark as packed
        order.mark_packed()
        print(f"📦 Order packed: {order.get_id()}")
        
        # Assign delivery partner
        partner = self.get_available_partner(order.get_dark_store().get_id())
        if partner:
            order.assign_delivery_partner(partner)
            print(f"🏍️  Delivery partner assigned: {partner.get_name()}")
            
            # Dispatch
            if order.dispatch():
                print(f"🚚 Order dispatched: {order.get_id()}")
        else:
            print(f"⚠️  No delivery partner available for {order.get_id()}")
    
    def complete_delivery(self, order_id: str, rating: Optional[int] = None) -> bool:
        """Complete order delivery"""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if not order.mark_delivered():
            return False
        
        self._active_orders.discard(order_id)
        
        # Add rating to delivery partner
        if rating and order._delivery_partner:
            order._delivery_partner.add_rating(rating)
        
        delivery_time = order.get_delivery_time_minutes()
        print(f"✅ Order delivered: {order_id}")
        print(f"   Delivery time: {delivery_time:.1f} minutes")
        
        if delivery_time and delivery_time <= 15:
            print(f"   🎯 Delivered within 15-minute promise!")
        
        return True
    
    def cancel_order(self, order_id: str, reason: str) -> bool:
        """Cancel order"""
        order = self._orders.get(order_id)
        if not order:
            return False
        
        if order.cancel(reason):
            self._active_orders.discard(order_id)
            print(f"❌ Order cancelled: {order_id}")
            print(f"   Reason: {reason}")
            return True
        
        return False
    
    # ==================== Search and Browse ====================
    
    def search_products(self, customer_location: Location, query: str,
                       category: Optional[ProductCategory] = None) -> List[Product]:
        """Search products available near customer"""
        # Find nearest store
        store = self.find_nearest_dark_store(customer_location)
        if not store:
            return []
        
        return store.search_products(query, category)
    
    def browse_category(self, customer_location: Location,
                       category: ProductCategory) -> List[Product]:
        """Browse products by category"""
        return self.search_products(customer_location, "", category)
    
    # ==================== Analytics and Monitoring ====================
    
    def get_store_statistics(self, store_id: str) -> Optional[Dict]:
        """Get dark store statistics"""
        store = self._dark_stores.get(store_id)
        if not store:
            return None
        
        store_orders = [
            order for order in self._orders.values()
            if order.get_dark_store().get_id() == store_id
        ]
        
        completed_orders = [
            o for o in store_orders if o.get_status() == OrderStatus.DELIVERED
        ]
        
        avg_delivery_time = 0.0
        if completed_orders:
            delivery_times = [o.get_delivery_time_minutes() for o in completed_orders if o.get_delivery_time_minutes()]
            if delivery_times:
                avg_delivery_time = sum(delivery_times) / len(delivery_times)
        
        return {
            'store': store.to_dict(),
            'total_orders': len(store_orders),
            'completed_orders': len(completed_orders),
            'active_orders': store._current_order_count,
            'avg_delivery_time': f"{avg_delivery_time:.1f} min",
            'low_stock_items': len(store.get_low_stock_items())
        }
    
    def get_system_statistics(self) -> Dict:
        """Get overall system statistics"""
        total_orders = len(self._orders)
        delivered_orders = len([o for o in self._orders.values() if o.get_status() == OrderStatus.DELIVERED])
        active_orders = len(self._active_orders)
        
        # Calculate average delivery time
        delivery_times = [
            o.get_delivery_time_minutes() 
            for o in self._orders.values() 
            if o.get_delivery_time_minutes()
        ]
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # On-time delivery rate
        on_time = len([t for t in delivery_times if t <= 15])
        on_time_rate = (on_time / len(delivery_times) * 100) if delivery_times else 0
        
        return {
            'total_customers': len(self._customers),
            'total_dark_stores': len(self._dark_stores),
            'active_stores': len([s for s in self._dark_stores.values() if s.is_operational()]),
            'total_products': len(self._products),
            'total_delivery_partners': len(self._delivery_partners),
            'available_partners': len([p for p in self._delivery_partners.values() if p.is_available()]),
            'total_orders': total_orders,
            'delivered_orders': delivered_orders,
            'active_orders': active_orders,
            'avg_delivery_time': f"{avg_delivery_time:.1f} min",
            'on_time_delivery_rate': f"{on_time_rate:.1f}%"
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_quick_delivery_service():
    """Comprehensive demo"""
    
    print_section("QUICK DELIVERY SERVICE DEMO (15-Min Delivery)")
    
    service = QuickDeliveryService("QuickMart")
    
    # ==================== Setup Dark Stores ====================
    print_section("1. Setup Dark Store Network")
    
    # Store 1: Downtown
    downtown_location = Location(
        28.6139, 77.2090,
        "Sector 18, Connaught Place",
        "New Delhi", "110001",
        "Near Metro Station"
    )
    downtown_store = service.add_dark_store("CP Dark Store", downtown_location)
    
    # Store 2: South Delhi
    south_location = Location(
        28.5355, 77.2490,
        "Hauz Khas Village",
        "New Delhi", "110016",
        "Near Deer Park"
    )
    south_store = service.add_dark_store("Hauz Khas Dark Store", south_location)
    
    # Store 3: North Delhi
    north_location = Location(
        28.7041, 77.1025,
        "Rohini Sector 10",
        "New Delhi", "110085"
    )
    north_store = service.add_dark_store("Rohini Dark Store", north_location)
    
    # ==================== Add Products ====================
    print_section("2. Add Products to Catalog")
    
    products = []
    
    # Dairy
    products.append(service.add_product("Amul Milk", ProductCategory.DAIRY, "Amul", 
                                       Decimal(60), Decimal(56), "1L"))
    products.append(service.add_product("Mother Dairy Curd", ProductCategory.DAIRY, "Mother Dairy",
                                       Decimal(30), Decimal(28), "400g"))
    
    # Snacks
    products.append(service.add_product("Lays Chips", ProductCategory.SNACKS, "Lays",
                                       Decimal(20), Decimal(18), "50g"))
    products.append(service.add_product("Kurkure", ProductCategory.SNACKS, "Kurkure",
                                       Decimal(10), Decimal(10), "35g"))
    
    # Beverages
    products.append(service.add_product("Coca Cola", ProductCategory.BEVERAGES, "Coca Cola",
                                       Decimal(40), Decimal(35), "750ml"))
    products.append(service.add_product("Real Juice", ProductCategory.BEVERAGES, "Dabur",
                                       Decimal(99), Decimal(89), "1L"))
    
    # Fresh Produce
    products.append(service.add_product("Onions", ProductCategory.FRESH_PRODUCE, "Local",
                                       Decimal(40), Decimal(35), "1kg"))
    products.append(service.add_product("Tomatoes", ProductCategory.FRESH_PRODUCE, "Local",
                                       Decimal(50), Decimal(45), "1kg"))
    
    # Personal Care
    products.append(service.add_product("Colgate Toothpaste", ProductCategory.PERSONAL_CARE, "Colgate",
                                       Decimal(120), Decimal(99), "200g"))
    
    # Household
    products.append(service.add_product("Vim Dishwash", ProductCategory.HOUSEHOLD, "Vim",
                                       Decimal(150), Decimal(129), "500ml"))
    
    print(f"\n✅ Added {len(products)} products to catalog")
    
    # ==================== Stock Dark Stores ====================
    print_section("3. Stock Products in Dark Stores")
    
    # Stock all stores with all products
    for store in [downtown_store, south_store, north_store]:
        for product in products:
            quantity = random.randint(50, 200)
            service.stock_product_in_store(product.get_id(), store.get_id(), quantity)
    
    print(f"✅ Stocked all dark stores")
    
    # ==================== Onboard Delivery Partners ====================
    print_section("4. Onboard Delivery Partners")
    
    # Downtown partners
    service.onboard_delivery_partner("Rajesh Kumar", "+91-9876543210", 
                                    VehicleType.BIKE, downtown_store.get_id())
    service.onboard_delivery_partner("Amit Singh", "+91-9876543211",
                                    VehicleType.SCOOTER, downtown_store.get_id())
    
    # South Delhi partners
    service.onboard_delivery_partner("Sanjay Sharma", "+91-9876543212",
                                    VehicleType.ELECTRIC_SCOOTER, south_store.get_id())
    
    # North Delhi partners
    service.onboard_delivery_partner("Vikram Yadav", "+91-9876543213",
                                    VehicleType.BIKE, north_store.get_id())
    
    # ==================== Register Customers ====================
    print_section("5. Register Customers")
    
    customer1 = service.register_customer("Priya Sharma", "+91-9999999991", "priya@email.com")
    customer2 = service.register_customer("Rahul Verma", "+91-9999999992", "rahul@email.com")
    customer3 = service.register_customer("Neha Gupta", "+91-9999999993", "neha@email.com")
    
    # ==================== Customer Places Order ====================
    print_section("6. Customer Places Order")
    
    # Priya's delivery address (near downtown store)
    priya_address = Location(
        28.6100, 77.2100,
        "Flat 301, Shanti Apartments",
        "New Delhi", "110001",
        "Near Barakhamba Metro"
    )
    
    # Create order
    print(f"\n👤 {customer1.get_name()} creating order...")
    order1 = service.create_order(customer1.get_id(), priya_address)
    
    if order1:
        print(f"\n🛒 Adding items to cart...")
        
        # Add items
        order1.add_item(products[0], 2)  # Milk
        order1.add_item(products[1], 1)  # Curd
        order1.add_item(products[2], 3)  # Chips
        order1.add_item(products[4], 2)  # Coca Cola
        order1.add_item(products[8], 1)  # Toothpaste
        
        print(f"\n📋 Order Summary:")
        order_dict = order1.to_dict()
        print(f"   Order ID: {order_dict['order_id']}")
        print(f"   Items: {len(order_dict['items'])}")
        for item in order_dict['items']:
            print(f"      • {item['product']} x{item['quantity']} = ₹{item['subtotal']}")
        
        print(f"\n💰 Pricing:")
        pricing = order_dict['pricing']
        print(f"   Item Total: ₹{pricing['item_total']}")
        print(f"   Delivery Fee: ₹{pricing['delivery_fee']}")
        print(f"   Platform Fee: ₹{pricing['platform_fee']}")
        print(f"   Total: ₹{pricing['total']}")
        
        # Confirm order
        print(f"\n✅ Confirming order with UPI payment...")
        service.confirm_and_process_order(order1.get_id(), PaymentMethod.UPI)
    else:
        print("❌ Failed to create order 1")
    
    # ==================== Another Order ====================
    print_section("7. Another Customer Order")
    
    rahul_address = Location(
        28.5400, 77.2500,
        "B-23, Green Park",
        "New Delhi", "110016",
        "Near Main Market"
    )
    
    print(f"\n👤 {customer2.get_name()} creating order...")
    order2 = service.create_order(customer2.get_id(), rahul_address)
    
    if order2:
        order2.add_item(products[6], 2)  # Onions
        order2.add_item(products[7], 1)  # Tomatoes
        order2.add_item(products[5], 1)  # Juice
        order2.add_item(products[9], 1)  # Dishwash
        
        print(f"\n💰 Order Total: ₹{order2.get_total_amount()}")
        service.confirm_and_process_order(order2.get_id(), PaymentMethod.CARD)
    else:
        print("❌ Failed to create order 2")
    
    # ==================== Search Products ====================
    print_section("8. Search Products")
    
    print(f"\n🔍 Searching for 'milk' near customer location...")
    search_results = service.search_products(priya_address, "milk")
    
    print(f"   Found {len(search_results)} results:")
    for product in search_results:
        prod_dict = product.to_dict()
        print(f"   • {prod_dict['name']} - ₹{prod_dict['selling_price']} ({prod_dict['discount']} off)")
    
    # ==================== Browse Category ====================
    print_section("9. Browse by Category")
    
    print(f"\n📂 Browsing SNACKS category...")
    snacks = service.browse_category(priya_address, ProductCategory.SNACKS)
    
    for product in snacks:
        print(f"   • {product.get_name()} - ₹{product.get_selling_price()}")
    
    # ==================== Complete Deliveries ====================
    print_section("10. Complete Deliveries")
    
    # Complete order 1
    if order1:
        print(f"\n📦 Completing delivery for Order 1...")
        service.complete_delivery(order1.get_id(), rating=5)
    
    # Complete order 2
    if order2:
        print(f"\n📦 Completing delivery for Order 2...")
        service.complete_delivery(order2.get_id(), rating=4)
    
    # ==================== Check Inventory ====================
    print_section("11. Check Inventory Status")
    
    print(f"\n📊 {downtown_store.get_name()} Inventory:")
    low_stock = downtown_store.get_low_stock_items()
    
    print(f"   Total Products: {len(downtown_store._inventory)}")
    print(f"   Low Stock Items: {len(low_stock)}")
    
    if low_stock:
        print(f"\n   ⚠️  Items needing restock:")
        for item in low_stock[:5]:
            item_dict = item.to_dict()
            print(f"      • {item_dict['product']}: {item_dict['available']} available")
    
    # Sample inventory items
    print(f"\n   Sample Inventory:")
    for item in list(downtown_store._inventory.values())[:5]:
        item_dict = item.to_dict()
        print(f"      • {item_dict['product']}: {item_dict['available']}/{item_dict['total_quantity']} available")
    
    # ==================== Store Statistics ====================
    print_section("12. Dark Store Statistics")
    
    for store in [downtown_store, south_store]:
        stats = service.get_store_statistics(store.get_id())
        if stats:
            print(f"\n📊 {stats['store']['name']}:")
            print(f"   Status: {stats['store']['status']}")
            print(f"   Service Radius: {stats['store']['service_radius_km']} km")
            print(f"   Active Orders: {stats['active_orders']}/{stats['store']['max_capacity']}")
            print(f"   Total Orders Processed: {stats['total_orders']}")
            print(f"   Completed: {stats['completed_orders']}")
            if stats['completed_orders'] > 0:
                print(f"   Avg Delivery Time: {stats['avg_delivery_time']}")
            print(f"   Low Stock Items: {stats['low_stock_items']}")
    
    # ==================== System Statistics ====================
    print_section("13. System-Wide Statistics")
    
    system_stats = service.get_system_statistics()
    
    print(f"\n📊 QuickMart Statistics:")
    print(f"   Total Customers: {system_stats['total_customers']}")
    print(f"   Dark Stores: {system_stats['total_dark_stores']} ({system_stats['active_stores']} active)")
    print(f"   Products in Catalog: {system_stats['total_products']}")
    print(f"   Delivery Partners: {system_stats['total_delivery_partners']} ({system_stats['available_partners']} available)")
    
    print(f"\n   Orders:")
    print(f"   Total: {system_stats['total_orders']}")
    print(f"   Delivered: {system_stats['delivered_orders']}")
    print(f"   Active: {system_stats['active_orders']}")
    
    if system_stats['delivered_orders'] > 0:
        print(f"\n   Performance:")
        print(f"   Avg Delivery Time: {system_stats['avg_delivery_time']}")
        print(f"   On-Time Delivery Rate: {system_stats['on_time_delivery_rate']}")
    
    # ==================== Order Cancellation ====================
    print_section("14. Order Cancellation")
    
    # Create and cancel an order
    cancel_order = service.create_order(customer3.get_id(), priya_address)
    if cancel_order:
        cancel_order.add_item(products[0], 1)
        service.confirm_and_process_order(cancel_order.get_id(), PaymentMethod.CASH_ON_DELIVERY)
        
        print(f"\n❌ Customer cancelling order...")
        service.cancel_order(cancel_order.get_id(), "Changed mind")
    
    # ==================== Bulk Orders for Testing ====================
    print_section("15. Simulate Multiple Orders")
    
    print(f"\n🔄 Creating 5 more orders for realistic stats...")
    
    test_addresses = [
        Location(28.6110, 77.2095, "Test Address 1", "New Delhi", "110001"),
        Location(28.5380, 77.2495, "Test Address 2", "New Delhi", "110016"),
        Location(28.6105, 77.2085, "Test Address 3", "New Delhi", "110001"),
        Location(28.5360, 77.2480, "Test Address 4", "New Delhi", "110016"),
        Location(28.6120, 77.2100, "Test Address 5", "New Delhi", "110001"),
    ]
    
    completed_count = 0
    for i, addr in enumerate(test_addresses):
        test_order = service.create_order(customer1.get_id(), addr)
        if test_order:
            # Add random items
            num_items = random.randint(2, 4)
            for _ in range(num_items):
                prod = random.choice(products)
                test_order.add_item(prod, random.randint(1, 3))
            
            # Confirm and complete
            if service.confirm_and_process_order(test_order.get_id(), PaymentMethod.UPI):
                service.complete_delivery(test_order.get_id(), rating=random.randint(4, 5))
                completed_count += 1
    
    print(f"✅ Completed {completed_count} additional orders")
    
    # ==================== Final Statistics ====================
    print_section("16. Final System Statistics")
    
    final_stats = service.get_system_statistics()
    
    print(f"\n📊 Final QuickMart Statistics:")
    print(f"   Total Orders: {final_stats['total_orders']}")
    print(f"   Delivered Orders: {final_stats['delivered_orders']}")
    print(f"   Active Orders: {final_stats['active_orders']}")
    print(f"   Avg Delivery Time: {final_stats['avg_delivery_time']}")
    print(f"   On-Time Delivery Rate: {final_stats['on_time_delivery_rate']}")
    
    print_section("Demo Complete")
    print("\n✅ Quick Delivery Service demo completed!")
    
    print("\n" + "="*70)
    print(" KEY DIFFERENCES: QUICK COMMERCE vs FOOD DELIVERY")
    print("="*70)
    
    print("\n🏪 INFRASTRUCTURE:")
    print("   Quick Commerce:")
    print("   • Dark Stores (company-owned micro-warehouses)")
    print("   • Small service radius (2-3km)")
    print("   • Optimized for speed and freshness")
    
    print("\n   Food Delivery:")
    print("   • Restaurant Partners (independent businesses)")
    print("   • Larger service radius (5-10km)")
    print("   • Optimized for variety and choice")
    
    print("\n📦 INVENTORY MANAGEMENT:")
    print("   Quick Commerce:")
    print("   • ✅ Real-time inventory tracking")
    print("   • ✅ Inventory reservation system")
    print("   • ✅ Low stock alerts and auto-reorder")
    print("   • ✅ Cold storage requirements")
    print("   • ✅ SKU-level management (barcodes)")
    
    print("\n   Food Delivery:")
    print("   • Restaurant manages their own inventory")
    print("   • Menu availability (binary: available/unavailable)")
    print("   • No direct inventory control")
    
    print("\n⏱️ DELIVERY PROMISE:")
    print("   Quick Commerce:")
    print("   • 10-15 minute delivery")
    print("   • Highly optimized logistics")
    print("   • Pre-picked and ready to dispatch")
    
    print("\n   Food Delivery:")
    print("   • 30-45 minute delivery")
    print("   • Prep time + delivery time")
    print("   • Made-to-order approach")
    
    print("\n🔍 PRODUCT DISCOVERY:")
    print("   Quick Commerce:")
    print("   • ✅ Search by product name")
    print("   • ✅ Browse by category")
    print("   • ✅ Location-based availability")
    print("   • ✅ Real-time stock visibility")
    
    print("\n   Food Delivery:")
    print("   • Search by restaurant or cuisine")
    print("   • Browse by restaurant rating")
    print("   • Filter by delivery time, offers")
    
    print("\n💰 PRICING MODEL:")
    print("   Quick Commerce:")
    print("   • Fixed MRP + discounts")
    print("   • Platform fee")
    print("   • Free delivery above threshold")
    print("   • Lower margins (5-10%)")
    
    print("\n   Food Delivery:")
    print("   • Restaurant pricing + markup")
    print("   • Commission (20-30%)")
    print("   • Delivery fee varies")
    print("   • Higher margins")
    
    print("\n📱 ORDER LIFECYCLE:")
    print("   Quick Commerce:")
    print("   • Pending → Confirmed → Picking → Packed → Out for Delivery → Delivered")
    print("   • Picking phase (1-2 min)")
    print("   • Packing phase (1 min)")
    print("   • Delivery (5-10 min)")
    
    print("\n   Food Delivery:")
    print("   • Placed → Accepted → Preparing → Ready → Out for Delivery → Delivered")
    print("   • Preparation phase (15-20 min)")
    print("   • Delivery (15-20 min)")
    
    print("\n🚚 DELIVERY OPTIMIZATION:")
    print("   Quick Commerce:")
    print("   • ✅ Store-specific delivery partners")
    print("   • ✅ Smaller delivery radius")
    print("   • ✅ Batch picking in store")
    print("   • ✅ Pre-assigned partners")
    
    print("\n   Food Delivery:")
    print("   • Dynamic partner assignment")
    print("   • Multi-restaurant pickups possible")
    print("   • Larger coverage area")
    
    print("\n🔄 INVENTORY RESERVATION:")
    print("   Quick Commerce:")
    print("   • ✅ Reserve items when order confirmed")
    print("   • ✅ Release on cancellation")
    print("   • ✅ Fulfill (reduce stock) when packed")
    print("   • ✅ Prevents overselling")
    
    print("\n   Food Delivery:")
    print("   • No reservation needed")
    print("   • Restaurant makes fresh")
    
    print("\n📊 DEMAND MANAGEMENT:")
    print("   Quick Commerce:")
    print("   • ✅ Predict demand by location/time")
    print("   • ✅ Stock optimization")
    print("   • ✅ Dynamic dark store capacity")
    print("   • ✅ Burst handling (mark store as BUSY)")
    
    print("\n   Food Delivery:")
    print("   • Restaurant capacity management")
    print("   • Peak hours surcharge")
    print("   • Order throttling by restaurant")
    
    print("\n🌡️ SPECIAL REQUIREMENTS:")
    print("   Quick Commerce:")
    print("   • ✅ Cold chain management")
    print("   • ✅ Fragile item handling")
    print("   • ✅ Fresh produce quality checks")
    print("   • ✅ Expiry date tracking")
    
    print("\n   Food Delivery:")
    print("   • Temperature-controlled bags")
    print("   • Spill-proof packaging")
    
    print("\n💡 TECHNOLOGY FOCUS:")
    print("   Quick Commerce:")
    print("   • Inventory management systems")
    print("   • Demand forecasting")
    print("   • Warehouse optimization")
    print("   • Route optimization")
    print("   • Real-time stock sync")
    
    print("\n   Food Delivery:")
    print("   • Restaurant discovery")
    print("   • Menu management")
    print("   • Order aggregation")
    print("   • ETA prediction")
    
    print("\n🎯 BUSINESS MODEL:")
    print("   Quick Commerce:")
    print("   • B2C (direct to consumer)")
    print("   • Own inventory risk")
    print("   • Scale through dark stores")
    print("   • Focus on essentials")
    
    print("\n   Food Delivery:")
    print("   • Marketplace model")
    print("   • No inventory risk")
    print("   • Scale through restaurant network")
    print("   • Focus on variety")
    
    print("\n📈 KEY METRICS:")
    print("   Quick Commerce:")
    print("   • Delivery time (< 15 min)")
    print("   • Inventory turnover")
    print("   • Stock-out rate")
    print("   • Order fulfillment rate")
    print("   • Dark store utilization")
    
    print("\n   Food Delivery:")
    print("   • Delivery time (< 45 min)")
    print("   • Restaurant partner count")
    print("   • Order value")
    print("   • Customer retention")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        demo_quick_delivery_service()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
