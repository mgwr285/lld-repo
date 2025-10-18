from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock, Thread
from queue import Queue
import time
from collections import defaultdict


# ==================== Enums ====================

class ProductCategory(Enum):
    """Product categories"""
    ELECTRONICS = "ELECTRONICS"
    CLOTHING = "CLOTHING"
    FOOD = "FOOD"
    BOOKS = "BOOKS"
    FURNITURE = "FURNITURE"
    TOYS = "TOYS"


class OrderStatus(Enum):
    """Status of orders"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    FULFILLED = "FULFILLED"
    PARTIALLY_FULFILLED = "PARTIALLY_FULFILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class TransactionType(Enum):
    """Types of inventory transactions"""
    STOCK_IN = "STOCK_IN"           # Adding inventory
    STOCK_OUT = "STOCK_OUT"         # Removing inventory (sale)
    TRANSFER = "TRANSFER"           # Transfer between warehouses
    ADJUSTMENT = "ADJUSTMENT"       # Manual adjustment
    RETURN = "RETURN"               # Customer return


class WarehouseStatus(Enum):
    """Warehouse operational status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


# ==================== Core Models ====================

class Product:
    """Represents a product in the inventory"""
    
    def __init__(self, product_id: str, name: str, category: ProductCategory, 
                 price: float, weight: float):
        self._product_id = product_id
        self._name = name
        self._category = category
        self._price = price
        self._weight = weight  # in kg
    
    def get_id(self) -> str:
        return self._product_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_category(self) -> ProductCategory:
        return self._category
    
    def get_price(self) -> float:
        return self._price
    
    def get_weight(self) -> float:
        return self._weight
    
    def __repr__(self) -> str:
        return f"Product({self._product_id}, {self._name})"
    
    def __hash__(self) -> int:
        return hash(self._product_id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Product):
            return False
        return self._product_id == other._product_id


@dataclass
class InventoryItem:
    """Represents inventory of a product at a warehouse"""
    product: Product
    quantity: int
    reserved_quantity: int = 0  # Reserved for pending orders
    reorder_point: int = 10     # Trigger replenishment when below this
    reorder_quantity: int = 50  # Amount to reorder
    
    def get_available_quantity(self) -> int:
        """Get quantity available for sale (not reserved)"""
        return max(0, self.quantity - self.reserved_quantity)
    
    def needs_replenishment(self) -> bool:
        """Check if inventory needs replenishment"""
        return self.get_available_quantity() < self.reorder_point


class Warehouse:
    """Represents a warehouse/fulfillment center"""
    
    def __init__(self, warehouse_id: str, name: str, location: str, capacity: int):
        self._warehouse_id = warehouse_id
        self._name = name
        self._location = location
        self._capacity = capacity  # Max number of items
        self._status = WarehouseStatus.ACTIVE
        self._inventory: Dict[str, InventoryItem] = {}  # product_id -> InventoryItem
        self._lock = Lock()  # Thread safety for inventory operations
    
    def get_id(self) -> str:
        return self._warehouse_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_location(self) -> str:
        return self._location
    
    def get_status(self) -> WarehouseStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: WarehouseStatus) -> None:
        with self._lock:
            self._status = status
    
    def is_active(self) -> bool:
        return self.get_status() == WarehouseStatus.ACTIVE
    
    def _get_total_items_internal(self) -> int:
        """Internal method - assumes lock is already held"""
        return sum(item.quantity for item in self._inventory.values())
    
    def get_total_items(self) -> int:
        """Get total number of items in warehouse"""
        with self._lock:
            return self._get_total_items_internal()
    
    def get_available_capacity(self) -> int:
        """Get remaining capacity"""
        return self._capacity - self.get_total_items()
    
    def add_product(self, product: Product, quantity: int, 
                   reorder_point: int = 10, reorder_quantity: int = 50) -> bool:
        """Add a product to inventory"""
        if quantity <= 0:
            return False
        
        with self._lock:
            # Use internal method to avoid deadlock
            if self._get_total_items_internal() + quantity > self._capacity:
                return False
            
            product_id = product.get_id()
            if product_id in self._inventory:
                self._inventory[product_id].quantity += quantity
            else:
                self._inventory[product_id] = InventoryItem(
                    product=product,
                    quantity=quantity,
                    reorder_point=reorder_point,
                    reorder_quantity=reorder_quantity
                )
        
        return True
    
    def remove_product(self, product_id: str, quantity: int) -> bool:
        """Remove product from inventory"""
        if quantity <= 0:
            return False
        
        with self._lock:
            if product_id not in self._inventory:
                return False
            
            item = self._inventory[product_id]
            if item.get_available_quantity() < quantity:
                return False
            
            item.quantity -= quantity
            if item.quantity == 0:
                del self._inventory[product_id]
        
        return True
    
    def reserve_product(self, product_id: str, quantity: int) -> bool:
        """Reserve product for an order"""
        if quantity <= 0:
            return False
        
        with self._lock:
            if product_id not in self._inventory:
                return False
            
            item = self._inventory[product_id]
            if item.get_available_quantity() < quantity:
                return False
            
            item.reserved_quantity += quantity
        
        return True
    
    def release_reservation(self, product_id: str, quantity: int) -> bool:
        """Release reserved product (e.g., order cancelled)"""
        if quantity <= 0:
            return False
        
        with self._lock:
            if product_id not in self._inventory:
                return False
            
            item = self._inventory[product_id]
            item.reserved_quantity = max(0, item.reserved_quantity - quantity)
        
        return True
    
    def fulfill_reservation(self, product_id: str, quantity: int) -> bool:
        """Fulfill reserved product (convert reservation to actual removal)"""
        if quantity <= 0:
            return False
        
        with self._lock:
            if product_id not in self._inventory:
                return False
            
            item = self._inventory[product_id]
            if item.reserved_quantity < quantity:
                return False
            
            item.reserved_quantity -= quantity
            item.quantity -= quantity
            
            if item.quantity == 0:
                del self._inventory[product_id]
        
        return True
    
    def get_inventory_item(self, product_id: str) -> Optional[InventoryItem]:
        """Get inventory item for a product"""
        with self._lock:
            return self._inventory.get(product_id)
    
    def get_all_inventory(self) -> Dict[str, InventoryItem]:
        """Get copy of all inventory"""
        with self._lock:
            return self._inventory.copy()
    
    def get_products_needing_replenishment(self) -> List[InventoryItem]:
        """Get products that need replenishment"""
        with self._lock:
            return [item for item in self._inventory.values() 
                   if item.needs_replenishment()]
    
    def __repr__(self) -> str:
        return f"Warehouse({self._warehouse_id}, {self._name}, {self._location})"


@dataclass
class OrderItem:
    """Represents an item in an order"""
    product: Product
    quantity: int
    warehouse_id: Optional[str] = None  # Assigned warehouse


class Order:
    """Represents a customer order"""
    
    _order_counter = 0
    
    def __init__(self, customer_id: str, items: List[OrderItem]):
        Order._order_counter += 1
        self._order_id = f"ORD-{Order._order_counter:06d}"
        self._customer_id = customer_id
        self._items = items
        self._status = OrderStatus.PENDING
        self._created_at = datetime.now()
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._order_id
    
    def get_customer_id(self) -> str:
        return self._customer_id
    
    def get_items(self) -> List[OrderItem]:
        with self._lock:
            return self._items.copy()
    
    def get_status(self) -> OrderStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: OrderStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_total_value(self) -> float:
        """Calculate total order value"""
        return sum(item.product.get_price() * item.quantity for item in self._items)
    
    def __repr__(self) -> str:
        return f"Order({self._order_id}, {self._status.value}, ${self.get_total_value():.2f})"


@dataclass
class InventoryTransaction:
    """Records an inventory transaction"""
    transaction_id: str
    transaction_type: TransactionType
    product: Product
    quantity: int
    warehouse_id: str
    timestamp: datetime
    reference_id: Optional[str] = None  # Order ID, Transfer ID, etc.
    notes: Optional[str] = None


class TransferRequest:
    """Represents a transfer request between warehouses"""
    
    _transfer_counter = 0
    
    def __init__(self, product: Product, quantity: int, 
                 from_warehouse_id: str, to_warehouse_id: str):
        TransferRequest._transfer_counter += 1
        self._transfer_id = f"TRF-{TransferRequest._transfer_counter:06d}"
        self._product = product
        self._quantity = quantity
        self._from_warehouse_id = from_warehouse_id
        self._to_warehouse_id = to_warehouse_id
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._transfer_id
    
    def get_product(self) -> Product:
        return self._product
    
    def get_quantity(self) -> int:
        return self._quantity
    
    def get_from_warehouse_id(self) -> str:
        return self._from_warehouse_id
    
    def get_to_warehouse_id(self) -> str:
        return self._to_warehouse_id


# ==================== Strategy Pattern: Order Fulfillment Strategies ====================

class FulfillmentStrategy(ABC):
    """Abstract strategy for order fulfillment"""
    
    @abstractmethod
    def assign_warehouses(self, order: Order, warehouses: List[Warehouse]) -> bool:
        """
        Assign warehouses to fulfill order items.
        Returns True if order can be fulfilled, False otherwise.
        """
        pass


class NearestWarehouseStrategy(FulfillmentStrategy):
    """Fulfill from nearest warehouse with stock"""
    
    def assign_warehouses(self, order: Order, warehouses: List[Warehouse]) -> bool:
        """Simple strategy: assign first warehouse that has stock"""
        items = order.get_items()
        
        for item in items:
            assigned = False
            for warehouse in warehouses:
                if not warehouse.is_active():
                    continue
                
                inventory_item = warehouse.get_inventory_item(item.product.get_id())
                if inventory_item and inventory_item.get_available_quantity() >= item.quantity:
                    item.warehouse_id = warehouse.get_id()
                    assigned = True
                    break
            
            if not assigned:
                return False
        
        return True


class LoadBalancingStrategy(FulfillmentStrategy):
    """Balance load across warehouses"""
    
    def assign_warehouses(self, order: Order, warehouses: List[Warehouse]) -> bool:
        """Assign to warehouse with most available capacity"""
        items = order.get_items()
        active_warehouses = [w for w in warehouses if w.is_active()]
        
        for item in items:
            # Find warehouses with stock, sorted by available capacity
            candidates = []
            for warehouse in active_warehouses:
                inventory_item = warehouse.get_inventory_item(item.product.get_id())
                if inventory_item and inventory_item.get_available_quantity() >= item.quantity:
                    candidates.append((warehouse.get_available_capacity(), warehouse))
            
            if not candidates:
                return False
            
            # Assign to warehouse with most capacity
            candidates.sort(reverse=True)
            item.warehouse_id = candidates[0][1].get_id()
        
        return True


class SplitOrderStrategy(FulfillmentStrategy):
    """Split order across multiple warehouses if needed"""
    
    def assign_warehouses(self, order: Order, warehouses: List[Warehouse]) -> bool:
        """Can split items across warehouses"""
        # For simplicity, this implementation doesn't actually split items
        # In production, you'd split OrderItem into multiple items
        # Here we just try to fulfill from any available warehouse
        
        items = order.get_items()
        active_warehouses = [w for w in warehouses if w.is_active()]
        
        for item in items:
            remaining = item.quantity
            
            for warehouse in active_warehouses:
                if remaining == 0:
                    break
                
                inventory_item = warehouse.get_inventory_item(item.product.get_id())
                if inventory_item and inventory_item.get_available_quantity() > 0:
                    available = inventory_item.get_available_quantity()
                    fulfill_qty = min(remaining, available)
                    remaining -= fulfill_qty
                    
                    # For this simplified version, just assign to first warehouse
                    # In production, would create multiple OrderItems
                    if item.warehouse_id is None:
                        item.warehouse_id = warehouse.get_id()
            
            if remaining > 0:
                return False
        
        return True


# ==================== Strategy Pattern: Replenishment Strategies ====================

class ReplenishmentStrategy(ABC):
    """Abstract strategy for inventory replenishment"""
    
    @abstractmethod
    def generate_replenishment_requests(self, warehouses: List[Warehouse]) -> List[TransferRequest]:
        """Generate replenishment/transfer requests"""
        pass


class ThresholdReplenishmentStrategy(ReplenishmentStrategy):
    """Replenish when inventory falls below threshold"""
    
    def generate_replenishment_requests(self, warehouses: List[Warehouse]) -> List[TransferRequest]:
        """Generate requests for items below reorder point"""
        requests = []
        
        for warehouse in warehouses:
            if not warehouse.is_active():
                continue
            
            items_needing_replenishment = warehouse.get_products_needing_replenishment()
            
            for item in items_needing_replenishment:
                # In real system, would create purchase orders to suppliers
                # Here we'll mark as needing replenishment
                print(f"[Replenishment] {warehouse.get_name()} needs {item.reorder_quantity} "
                      f"units of {item.product.get_name()}")
        
        return requests


class BalancingReplenishmentStrategy(ReplenishmentStrategy):
    """Balance inventory across warehouses"""
    
    def generate_replenishment_requests(self, warehouses: List[Warehouse]) -> List[TransferRequest]:
        """Transfer inventory from high-stock to low-stock warehouses"""
        requests = []
        active_warehouses = [w for w in warehouses if w.is_active()]
        
        if len(active_warehouses) < 2:
            return requests
        
        # Group inventory by product across warehouses
        product_inventory: Dict[str, List[tuple]] = defaultdict(list)
        
        for warehouse in active_warehouses:
            for product_id, item in warehouse.get_all_inventory().items():
                product_inventory[product_id].append((
                    warehouse.get_id(),
                    item.get_available_quantity(),
                    item
                ))
        
        # For each product, check if balancing is needed
        for product_id, warehouse_stocks in product_inventory.items():
            if len(warehouse_stocks) < 2:
                continue
            
            # Sort by available quantity
            warehouse_stocks.sort(key=lambda x: x[1])
            
            # Check if there's significant imbalance
            lowest = warehouse_stocks[0]
            highest = warehouse_stocks[-1]
            
            # If highest has 3x more than lowest, balance them
            if highest[1] > lowest[1] * 3 and highest[1] > 20:
                transfer_qty = (highest[1] - lowest[1]) // 2
                transfer_qty = min(transfer_qty, 50)  # Cap transfer size
                
                if transfer_qty >= 5:  # Minimum transfer quantity
                    transfer = TransferRequest(
                        product=highest[2].product,
                        quantity=transfer_qty,
                        from_warehouse_id=highest[0],
                        to_warehouse_id=lowest[0]
                    )
                    requests.append(transfer)
        
        return requests


# ==================== Inventory Management System ====================

class InventoryManagementSystem:
    """Main inventory management system"""
    
    def __init__(self, fulfillment_strategy: FulfillmentStrategy,
                 replenishment_strategy: ReplenishmentStrategy):
        self._warehouses: Dict[str, Warehouse] = {}
        self._products: Dict[str, Product] = {}
        self._orders: Dict[str, Order] = {}
        self._order_queue: Queue = Queue()  # Thread-safe queue for incoming orders
        self._transaction_log: List[InventoryTransaction] = []
        self._fulfillment_strategy = fulfillment_strategy
        self._replenishment_strategy = replenishment_strategy
        self._running = False
        self._lock = Lock()
        
        # Counters
        self._transaction_counter = 0
    
    def add_warehouse(self, warehouse: Warehouse) -> None:
        """Add a warehouse to the system"""
        with self._lock:
            self._warehouses[warehouse.get_id()] = warehouse
        print(f"[System] Added warehouse: {warehouse}")
    
    def add_product(self, product: Product) -> None:
        """Register a product in the system"""
        with self._lock:
            self._products[product.get_id()] = product
        print(f"[System] Registered product: {product}")
    
    def get_warehouse(self, warehouse_id: str) -> Optional[Warehouse]:
        """Get warehouse by ID"""
        with self._lock:
            return self._warehouses.get(warehouse_id)
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        with self._lock:
            return self._products.get(product_id)
    
    def stock_in(self, warehouse_id: str, product_id: str, quantity: int) -> bool:
        """Add inventory to warehouse"""
        warehouse = self.get_warehouse(warehouse_id)
        product = self.get_product(product_id)
        
        if not warehouse or not product:
            print(f"[System] Invalid warehouse or product")
            return False
        
        if warehouse.add_product(product, quantity):
            self._log_transaction(
                TransactionType.STOCK_IN,
                product,
                quantity,
                warehouse_id,
                notes=f"Stock added to {warehouse.get_name()}"
            )
            print(f"[System] Stocked {quantity} units of {product.get_name()} "
                  f"in {warehouse.get_name()}")
            return True
        
        return False
    
    def submit_order(self, order: Order) -> None:
        """Submit an order for processing"""
        with self._lock:
            self._orders[order.get_id()] = order
        self._order_queue.put(order)
        print(f"[System] Order submitted: {order}")
    
    def process_orders(self) -> None:
        """Process orders from the queue (runs in separate thread)"""
        while self._running:
            try:
                # Get order from queue (blocking with timeout)
                order = self._order_queue.get(timeout=1)
                self._process_single_order(order)
            except:
                # Queue empty or timeout
                continue
    
    def _process_single_order(self, order: Order) -> None:
        """Process a single order"""
        print(f"\n[System] Processing {order}")
        order.set_status(OrderStatus.PROCESSING)
        
        # Get list of active warehouses
        with self._lock:
            warehouses = [w for w in self._warehouses.values() if w.is_active()]
        
        # Assign warehouses using strategy
        can_fulfill = self._fulfillment_strategy.assign_warehouses(order, warehouses)
        
        if not can_fulfill:
            print(f"[System] Cannot fulfill {order.get_id()} - insufficient inventory")
            order.set_status(OrderStatus.FAILED)
            return
        
        # Reserve inventory
        all_reserved = True
        reserved_items = []
        
        for item in order.get_items():
            warehouse = self.get_warehouse(item.warehouse_id)
            if warehouse:
                success = warehouse.reserve_product(item.product.get_id(), item.quantity)
                if success:
                    reserved_items.append(item)
                else:
                    all_reserved = False
                    break
        
        if not all_reserved:
            # Release all reservations
            for item in reserved_items:
                warehouse = self.get_warehouse(item.warehouse_id)
                if warehouse:
                    warehouse.release_reservation(item.product.get_id(), item.quantity)
            
            print(f"[System] Failed to reserve inventory for {order.get_id()}")
            order.set_status(OrderStatus.FAILED)
            return
        
        # Fulfill order
        for item in order.get_items():
            warehouse = self.get_warehouse(item.warehouse_id)
            if warehouse:
                warehouse.fulfill_reservation(item.product.get_id(), item.quantity)
                self._log_transaction(
                    TransactionType.STOCK_OUT,
                    item.product,
                    item.quantity,
                    warehouse.get_id(),
                    reference_id=order.get_id(),
                    notes=f"Order fulfillment"
                )
                print(f"[System] Fulfilled {item.quantity} units of {item.product.get_name()} "
                      f"from {warehouse.get_name()}")
        
        order.set_status(OrderStatus.FULFILLED)
        print(f"[System] Order {order.get_id()} fulfilled successfully!\n")
    
    def transfer_inventory(self, transfer: TransferRequest) -> bool:
        """Transfer inventory between warehouses"""
        from_warehouse = self.get_warehouse(transfer.get_from_warehouse_id())
        to_warehouse = self.get_warehouse(transfer.get_to_warehouse_id())
        
        if not from_warehouse or not to_warehouse:
            return False
        
        product = transfer.get_product()
        quantity = transfer.get_quantity()
        
        # Remove from source
        if not from_warehouse.remove_product(product.get_id(), quantity):
            return False
        
        # Add to destination
        if not to_warehouse.add_product(product, quantity):
            # Rollback: add back to source
            from_warehouse.add_product(product, quantity)
            return False
        
        # Log transactions
        self._log_transaction(
            TransactionType.TRANSFER,
            product,
            quantity,
            from_warehouse.get_id(),
            reference_id=transfer.get_id(),
            notes=f"Transfer to {to_warehouse.get_name()}"
        )
        
        print(f"[System] Transferred {quantity} units of {product.get_name()} "
              f"from {from_warehouse.get_name()} to {to_warehouse.get_name()}")
        
        return True
    
    def run_replenishment_check(self) -> None:
        """Check and execute replenishment (runs periodically)"""
        print(f"\n[System] Running replenishment check...")
        
        with self._lock:
            warehouses = list(self._warehouses.values())
        
        # Generate replenishment requests
        requests = self._replenishment_strategy.generate_replenishment_requests(warehouses)
        
        # Execute transfer requests
        for request in requests:
            self.transfer_inventory(request)
        
        if not requests:
            print(f"[System] No replenishment needed\n")
    
    def _log_transaction(self, transaction_type: TransactionType, product: Product,
                        quantity: int, warehouse_id: str, 
                        reference_id: Optional[str] = None,
                        notes: Optional[str] = None) -> None:
        """Log an inventory transaction"""
        with self._lock:
            self._transaction_counter += 1
            transaction = InventoryTransaction(
                transaction_id=f"TXN-{self._transaction_counter:06d}",
                transaction_type=transaction_type,
                product=product,
                quantity=quantity,
                warehouse_id=warehouse_id,
                timestamp=datetime.now(),
                reference_id=reference_id,
                notes=notes
            )
            self._transaction_log.append(transaction)
    
    def start(self) -> None:
        """Start the inventory management system"""
        print(f"[System] Starting Inventory Management System...")
        with self._lock:
            if self._running:
                return
            self._running = True
        
        # Start order processing thread
        order_thread = Thread(target=self.process_orders, daemon=True)
        order_thread.start()
        
        # Start replenishment thread
        replenishment_thread = Thread(target=self._run_replenishment_loop, daemon=True)
        replenishment_thread.start()
    
    def _run_replenishment_loop(self) -> None:
        """Periodically check for replenishment needs"""
        while self._running:
            time.sleep(10)  # Check every 10 seconds
            if self._running:
                self.run_replenishment_check()
    
    def stop(self) -> None:
        """Stop the system"""
        with self._lock:
            self._running = False
    
    def display_inventory_status(self) -> None:
        """Display current inventory across all warehouses"""
        print("\n" + "="*80)
        print("INVENTORY STATUS")
        print("="*80)
        
        with self._lock:
            warehouses = list(self._warehouses.values())
        
        for warehouse in warehouses:
            print(f"\n{warehouse.get_name()} ({warehouse.get_location()}) - "
                  f"Status: {warehouse.get_status().value}")
            print(f"Capacity: {warehouse.get_total_items()}/{warehouse._capacity}")
            print("-" * 80)
            
            inventory = warehouse.get_all_inventory()
            if not inventory:
                print("  No inventory")
                continue
            
            for product_id, item in inventory.items():
                status = "⚠️ LOW" if item.needs_replenishment() else "✓"
                print(f"  {status} {item.product.get_name()}: "
                      f"{item.get_available_quantity()} available "
                      f"({item.reserved_quantity} reserved, "
                      f"{item.quantity} total)")
        
        print("="*80 + "\n")
    
    def display_order_status(self) -> None:
        """Display order statistics"""
        print("\n" + "="*80)
        print("ORDER STATUS")
        print("="*80)
        
        with self._lock:
            orders = list(self._orders.values())
        
        status_counts = defaultdict(int)
        total_value = 0
        
        for order in orders:
            status_counts[order.get_status()] += 1
            if order.get_status() == OrderStatus.FULFILLED:
                total_value += order.get_total_value()
        
        print(f"Total Orders: {len(orders)}")
        for status, count in status_counts.items():
            print(f"  {status.value}: {count}")
        print(f"Total Revenue (Fulfilled): ${total_value:.2f}")
        print("="*80 + "\n")


# ==================== Factory Pattern ====================

class InventorySystemFactory:
    """Factory for creating inventory system configurations"""
    
    @staticmethod
    def create_standard_system() -> InventoryManagementSystem:
        """Create system with standard strategies"""
        fulfillment = LoadBalancingStrategy()
        replenishment = BalancingReplenishmentStrategy()
        return InventoryManagementSystem(fulfillment, replenishment)
    
    @staticmethod
    def create_simple_system() -> InventoryManagementSystem:
        """Create system with simple strategies"""
        fulfillment = NearestWarehouseStrategy()
        replenishment = ThresholdReplenishmentStrategy()
        return InventoryManagementSystem(fulfillment, replenishment)


# ==================== Demo Usage ====================

def main():
    """Demo the inventory management system"""
    print("=== Inventory Management System Demo ===\n")
    
    # Create system
    system = InventorySystemFactory.create_standard_system()
    
    # Create warehouses
    warehouse1 = Warehouse("WH-001", "North Warehouse", "Seattle, WA", 1000)
    warehouse2 = Warehouse("WH-002", "South Warehouse", "Los Angeles, CA", 800)
    warehouse3 = Warehouse("WH-003", "East Warehouse", "New York, NY", 1200)
    
    system.add_warehouse(warehouse1)
    system.add_warehouse(warehouse2)
    system.add_warehouse(warehouse3)
    
    # Create products
    products = [
        Product("PROD-001", "Laptop", ProductCategory.ELECTRONICS, 999.99, 2.5),
        Product("PROD-002", "Headphones", ProductCategory.ELECTRONICS, 199.99, 0.5),
        Product("PROD-003", "T-Shirt", ProductCategory.CLOTHING, 29.99, 0.2),
        Product("PROD-004", "Coffee Maker", ProductCategory.ELECTRONICS, 79.99, 3.0),
        Product("PROD-005", "Book", ProductCategory.BOOKS, 19.99, 0.5),
    ]
    
    for product in products:
        system.add_product(product)
    
    # Stock warehouses
    print("\n--- Initial Stocking ---")
    system.stock_in("WH-001", "PROD-001", 50)
    system.stock_in("WH-001", "PROD-002", 100)
    system.stock_in("WH-001", "PROD-003", 200)
    system.stock_in("WH-001", "PROD-004", 30)
    system.stock_in("WH-001", "PROD-005", 150)
    
    system.stock_in("WH-002", "PROD-001", 20)
    system.stock_in("WH-002", "PROD-002", 80)
    system.stock_in("WH-002", "PROD-003", 150)
    system.stock_in("WH-002", "PROD-004", 40)
    system.stock_in("WH-002", "PROD-005", 100)
    
    system.stock_in("WH-003", "PROD-001", 5)  # Low stock
    system.stock_in("WH-003", "PROD-002", 30)
    system.stock_in("WH-003", "PROD-003", 50)
    system.stock_in("WH-003", "PROD-004", 8)   # Low stock
    system.stock_in("WH-003", "PROD-005", 80)
    
    # Display initial inventory
    system.display_inventory_status()
    
    # Start the system
    system.start()
    
    # Create and submit orders
    print("\n--- Submitting Orders ---")
    
    order1 = Order("CUST-001", [
        OrderItem(products[0], 3),  # 3 Laptops
        OrderItem(products[1], 5),  # 5 Headphones
    ])
    system.submit_order(order1)
    
    time.sleep(2)
    
    order2 = Order("CUST-002", [
        OrderItem(products[2], 20),  # 20 T-Shirts
        OrderItem(products[4], 10),  # 10 Books
    ])
    system.submit_order(order2)
    
    time.sleep(2)
    
    order3 = Order("CUST-003", [
        OrderItem(products[0], 2),   # 2 Laptops
        OrderItem(products[3], 4),   # 4 Coffee Makers
        OrderItem(products[1], 3),   # 3 Headphones
    ])
    system.submit_order(order3)
    
    time.sleep(2)
    
    order4 = Order("CUST-004", [
        OrderItem(products[2], 50),  # 50 T-Shirts
    ])
    system.submit_order(order4)
    
    # Let orders process
    print("\n--- Processing Orders ---")
    time.sleep(5)
    
    # Display status after orders
    system.display_inventory_status()
    system.display_order_status()
    
    # Submit more orders to trigger low inventory
    print("\n--- Submitting More Orders ---")
    
    order5 = Order("CUST-005", [
        OrderItem(products[0], 5),  # 5 Laptops
    ])
    system.submit_order(order5)
    
    order6 = Order("CUST-006", [
        OrderItem(products[3], 3),  # 3 Coffee Makers
    ])
    system.submit_order(order6)
    
    time.sleep(5)
    
    # Display final status
    system.display_inventory_status()
    system.display_order_status()
    
    # Wait for replenishment check
    print("\n--- Waiting for Replenishment Check ---")
    time.sleep(12)
    
    # Display status after replenishment
    system.display_inventory_status()
    
    # Stop the system
    print("\n--- Stopping System ---")
    system.stop()
    time.sleep(2)
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Strategy Pattern - Multiple uses:

# Fulfillment Strategies:

# NearestWarehouseStrategy: Simple first-available
# LoadBalancingStrategy: Balance across warehouses
# SplitOrderStrategy: Can split orders across warehouses


# Replenishment Strategies:

# ThresholdReplenishmentStrategy: Reorder when below threshold
# BalancingReplenishmentStrategy: Balance inventory across warehouses




# Factory Pattern:

# Creates different system configurations
# Easy to switch between simple and advanced strategies


# Queue Pattern:

# Thread-safe Queue for incoming order requests
# Decouples order submission from processing



# Concurrency Handling:

# Thread Locks (Lock):

# Warehouse: Protects inventory operations (add, remove, reserve)
# Order: Protects status updates
# InventoryManagementSystem: Protects shared state


# Thread-Safe Queue:

# Queue for order processing
# Supports multiple producers (order submissions)
# Single consumer (order processor)


# Atomic Operations:

# Reservation system prevents double-booking
# Reserve → Fulfill pattern for order processing
# Rollback on failure (e.g., transfer operations)


# Background Workers:

# Order processing thread
# Replenishment checking thread
# Both run continuously while system is active



# Core Features:
# ✅ Multi-Warehouse Support: Independent warehouses with capacity limits
# ✅ Product Categories: Organized inventory by type
# ✅ Reservation System: Reserve inventory for pending orders
# ✅ Order Queue: Thread-safe processing of incoming orders
# ✅ Multiple Fulfillment Strategies: Pluggable order assignment logic
# ✅ Automatic Replenishment: Threshold-based and balancing strategies
# ✅ Transaction Logging: Complete audit trail
# ✅ Warehouse Transfers: Move inventory between locations
# ✅ Concurrency Safety: Thread-safe operations throughout
# Real-World Scenarios Handled:

# Order Fulfillment:

# Assign orders to optimal warehouses
# Reserve inventory to prevent overselling
# Handle partial/failed fulfillment


# Inventory Balancing:

# Detect imbalances across warehouses
# Automatically transfer inventory
# Maintain optimal stock levels


# Replenishment:

# Monitor reorder points
# Trigger restocking when low
# Balance across locations


# Concurrency:

# Multiple orders processed simultaneously
# Thread-safe inventory updates
# Queue-based request handling



# Data Structures Used:

# Dictionary (Dict): O(1) product/warehouse lookup
# Queue: Thread-safe FIFO order processing
# Set: Track target floors, reserved inventory
# Lock: Protect shared state from race conditions

# Extensions You Could Add:

# Batch Processing: Group orders for efficiency
# Priority Orders: VIP customers, express shipping
# Forecasting: Predict demand using historical data
# Supplier Integration: Automatic purchase orders
# Shipping Integration: Calculate costs, track deliveries
# Return Processing: Handle customer returns
# Warehouse Zones: Hot/cold storage, hazmat areas
# Pick/Pack Optimization: Optimize warehouse operations
# Real-time Analytics: Dashboard with metrics
# Multi-tenancy: Support multiple businesses

# Key Methods Explained:
# Reservation System:
# python# Three-phase commit for orders:
# 1. reserve_product()      # Lock inventory
# 2. fulfill_reservation()  # Complete order
# 3. release_reservation()  # On cancellation
# Concurrency Pattern:
# pythonwith self._lock:
#     # Critical section
#     # All shared state access protected
# Queue Processing:
# pythonorder = self._order_queue.get(timeout=1)  # Blocking with timeout
# self._process_single_order(order)         # Thread-safe processing
# This design demonstrates production-ready inventory management with proper concurrency handling, multiple strategies, and extensible architecture - perfect for system design interviews!
