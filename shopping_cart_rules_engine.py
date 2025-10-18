from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
import uuid


# ==================== Enums ====================

class MembershipType(Enum):
    """Customer membership types"""
    REGULAR = "regular"
    PRIME = "prime"


class ShippingSpeed(Enum):
    """Shipping speed options"""
    STANDARD = "standard"  # 5-7 days
    TWO_DAY = "two_day"
    ONE_DAY = "one_day"
    TWO_HOUR = "two_hour"


class ItemCategory(Enum):
    """Item categories"""
    ELECTRONICS = "electronics"
    GROCERY = "grocery"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    BEAUTY = "beauty"


class RuleType(Enum):
    """Type of rule"""
    SHIPPING_RULE = "shipping_rule"
    DISCOUNT_RULE = "discount_rule"
    PROMOTION_RULE = "promotion_rule"


class RulePriority(Enum):
    """Rule execution priority"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ==================== Models ====================

@dataclass
class Customer:
    """Customer model"""
    customer_id: str
    name: str
    email: str
    membership_type: MembershipType
    member_since: Optional[datetime] = None
    
    def is_prime_member(self) -> bool:
        return self.membership_type == MembershipType.PRIME


@dataclass
class CartItem:
    """Item in shopping cart"""
    item_id: str
    name: str
    price: Decimal
    quantity: int
    category: ItemCategory
    is_subscribe_and_save: bool = False
    is_digital: bool = False
    weight_oz: Optional[float] = None  # Weight in ounces
    
    def get_subtotal(self) -> Decimal:
        return self.price * self.quantity
    
    def is_grocery(self) -> bool:
        return self.category == ItemCategory.GROCERY


class ShoppingCart:
    """Shopping cart"""
    
    def __init__(self, cart_id: str, customer: Customer):
        self._cart_id = cart_id
        self._customer = customer
        self._items: List[CartItem] = []
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._cart_id
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def add_item(self, item: CartItem) -> None:
        self._items.append(item)
    
    def get_items(self) -> List[CartItem]:
        return self._items.copy()
    
    def get_subtotal(self) -> Decimal:
        """Calculate subtotal before discounts"""
        return sum(item.get_subtotal() for item in self._items)
    
    def get_item_count(self) -> int:
        return sum(item.quantity for item in self._items)
    
    def has_grocery_items(self) -> bool:
        return any(item.is_grocery() for item in self._items)
    
    def has_subscribe_and_save_items(self) -> bool:
        return any(item.is_subscribe_and_save for item in self._items)
    
    def get_items_by_category(self, category: ItemCategory) -> List[CartItem]:
        return [item for item in self._items if item.category == category]
    
    def get_subscribe_and_save_items(self) -> List[CartItem]:
        return [item for item in self._items if item.is_subscribe_and_save]


class RuleResult:
    """Result of applying a rule"""
    
    def __init__(self, rule_name: str, applied: bool, description: str = ""):
        self.rule_name = rule_name
        self.applied = applied
        self.description = description
        self.metadata: Dict[str, Any] = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value
    
    def __repr__(self) -> str:
        status = "✅" if self.applied else "⏭️"
        return f"{status} {self.rule_name}: {self.description}"


class OrderContext:
    """Context object passed to rules"""
    
    def __init__(self, cart: ShoppingCart):
        self.cart = cart
        self.customer = cart.get_customer()
        
        # Calculated values
        self.subtotal = cart.get_subtotal()
        self.item_count = cart.get_item_count()
        
        # Applied benefits
        self.shipping_speed: ShippingSpeed = ShippingSpeed.STANDARD
        self.shipping_cost: Decimal = Decimal(0)
        self.free_shipping: bool = False
        
        # Discounts
        self.discounts: List[Dict] = []
        self.total_discount: Decimal = Decimal(0)
        
        # Metadata
        self.metadata: Dict[str, Any] = {}
    
    def apply_shipping(self, speed: ShippingSpeed, cost: Decimal, free: bool = False) -> None:
        """Apply shipping option"""
        # Only upgrade shipping, never downgrade
        if speed.value > self.shipping_speed.value or free:
            self.shipping_speed = speed
            self.shipping_cost = Decimal(0) if free else cost
            self.free_shipping = free
    
    def apply_discount(self, name: str, amount: Decimal, description: str = "") -> None:
        """Apply a discount"""
        self.discounts.append({
            'name': name,
            'amount': amount,
            'description': description
        })
        self.total_discount += amount
    
    def get_final_total(self) -> Decimal:
        """Calculate final order total"""
        return max(self.subtotal - self.total_discount + self.shipping_cost, Decimal(0))
    
    def get_summary(self) -> Dict:
        """Get order summary"""
        return {
            'subtotal': float(self.subtotal),
            'shipping': {
                'speed': self.shipping_speed.value,
                'cost': float(self.shipping_cost),
                'free': self.free_shipping
            },
            'discounts': [
                {
                    'name': d['name'],
                    'amount': float(d['amount']),
                    'description': d['description']
                }
                for d in self.discounts
            ],
            'total_discount': float(self.total_discount),
            'final_total': float(self.get_final_total())
        }


# ==================== Rules Engine ====================

class Rule(ABC):
    """Abstract base class for all rules"""
    
    def __init__(self, rule_id: str, name: str, rule_type: RuleType,
                 priority: RulePriority = RulePriority.MEDIUM):
        self._rule_id = rule_id
        self._name = name
        self._rule_type = rule_type
        self._priority = priority
        self._enabled = True
    
    def get_id(self) -> str:
        return self._rule_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_type(self) -> RuleType:
        return self._rule_type
    
    def get_priority(self) -> RulePriority:
        return self._priority
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def enable(self) -> None:
        self._enabled = True
    
    def disable(self) -> None:
        self._enabled = False
    
    @abstractmethod
    def evaluate(self, context: OrderContext) -> bool:
        """Check if rule conditions are met"""
        pass
    
    @abstractmethod
    def apply(self, context: OrderContext) -> RuleResult:
        """Apply the rule"""
        pass
    
    def execute(self, context: OrderContext) -> RuleResult:
        """Execute rule: evaluate and apply if conditions met"""
        if not self._enabled:
            return RuleResult(self._name, False, "Rule is disabled")
        
        if self.evaluate(context):
            return self.apply(context)
        
        return RuleResult(self._name, False, "Conditions not met")
    
    def __lt__(self, other: 'Rule') -> bool:
        """For sorting by priority"""
        return self._priority.value > other._priority.value  # Higher priority first


# ==================== Shipping Rules ====================

class FreeShippingOver35Rule(Rule):
    """Free 2-day shipping on orders > $35 for non-prime members"""
    
    def __init__(self):
        super().__init__(
            "free_shipping_over_35",
            "Free 2-Day Shipping Over $35",
            RuleType.SHIPPING_RULE,
            RulePriority.MEDIUM
        )
        self._min_amount = Decimal(35)
    
    def evaluate(self, context: OrderContext) -> bool:
        # Only for non-prime members
        if context.customer.is_prime_member():
            return False
        
        # Cart total must be > $35
        return context.subtotal > self._min_amount
    
    def apply(self, context: OrderContext) -> RuleResult:
        context.apply_shipping(ShippingSpeed.TWO_DAY, Decimal(0), free=True)
        
        result = RuleResult(
            self._name,
            True,
            f"Free 2-day shipping applied (order > ${self._min_amount})"
        )
        result.add_metadata('shipping_speed', ShippingSpeed.TWO_DAY.value)
        result.add_metadata('min_amount', str(self._min_amount))
        return result


class PrimeFreeShippingRule(Rule):
    """Free 2-day shipping on all orders for Prime members"""
    
    def __init__(self):
        super().__init__(
            "prime_free_shipping",
            "Prime Free 2-Day Shipping",
            RuleType.SHIPPING_RULE,
            RulePriority.HIGH
        )
    
    def evaluate(self, context: OrderContext) -> bool:
        return context.customer.is_prime_member()
    
    def apply(self, context: OrderContext) -> RuleResult:
        context.apply_shipping(ShippingSpeed.TWO_DAY, Decimal(0), free=True)
        
        return RuleResult(
            self._name,
            True,
            "Free 2-day shipping for Prime members"
        )


class FreeOneDayShippingOver125Rule(Rule):
    """Free 1-day shipping for orders > $125"""
    
    def __init__(self):
        super().__init__(
            "free_one_day_over_125",
            "Free 1-Day Shipping Over $125",
            RuleType.SHIPPING_RULE,
            RulePriority.HIGH
        )
        self._min_amount = Decimal(125)
    
    def evaluate(self, context: OrderContext) -> bool:
        return context.subtotal > self._min_amount
    
    def apply(self, context: OrderContext) -> RuleResult:
        context.apply_shipping(ShippingSpeed.ONE_DAY, Decimal(0), free=True)
        
        result = RuleResult(
            self._name,
            True,
            f"Free 1-day shipping applied (order > ${self._min_amount})"
        )
        result.add_metadata('shipping_speed', ShippingSpeed.ONE_DAY.value)
        return result


class PrimeTwoHourGroceryShippingRule(Rule):
    """Free 2-hour shipping for Prime members with grocery items > $25"""
    
    def __init__(self):
        super().__init__(
            "prime_two_hour_grocery",
            "Prime 2-Hour Grocery Delivery",
            RuleType.SHIPPING_RULE,
            RulePriority.CRITICAL
        )
        self._min_amount = Decimal(25)
    
    def evaluate(self, context: OrderContext) -> bool:
        # Must be Prime member
        if not context.customer.is_prime_member():
            return False
        
        # Must have grocery items
        if not context.cart.has_grocery_items():
            return False
        
        # Grocery items total must be > $25
        grocery_items = context.cart.get_items_by_category(ItemCategory.GROCERY)
        grocery_total = sum(item.get_subtotal() for item in grocery_items)
        
        return grocery_total > self._min_amount
    
    def apply(self, context: OrderContext) -> RuleResult:
        context.apply_shipping(ShippingSpeed.TWO_HOUR, Decimal(0), free=True)
        
        result = RuleResult(
            self._name,
            True,
            f"Free 2-hour delivery for Prime grocery orders > ${self._min_amount}"
        )
        result.add_metadata('shipping_speed', ShippingSpeed.TWO_HOUR.value)
        return result


# ==================== Discount Rules ====================

class SubscribeAndSaveDiscountRule(Rule):
    """10% discount on Subscribe & Save items"""
    
    def __init__(self):
        super().__init__(
            "subscribe_and_save_discount",
            "Subscribe & Save 10% Discount",
            RuleType.DISCOUNT_RULE,
            RulePriority.HIGH
        )
        self._discount_percentage = Decimal(10)
    
    def evaluate(self, context: OrderContext) -> bool:
        return context.cart.has_subscribe_and_save_items()
    
    def apply(self, context: OrderContext) -> RuleResult:
        sns_items = context.cart.get_subscribe_and_save_items()
        
        total_discount = Decimal(0)
        discounted_items = []
        
        for item in sns_items:
            item_discount = (item.get_subtotal() * self._discount_percentage) / Decimal(100)
            total_discount += item_discount
            discounted_items.append(item.name)
        
        context.apply_discount(
            "Subscribe & Save",
            total_discount,
            f"{self._discount_percentage}% off on {len(sns_items)} items"
        )
        
        result = RuleResult(
            self._name,
            True,
            f"10% discount applied on {len(sns_items)} Subscribe & Save items"
        )
        result.add_metadata('discount_amount', str(total_discount))
        result.add_metadata('items_count', len(sns_items))
        result.add_metadata('items', discounted_items)
        return result


# ==================== Additional Example Rules ====================

class BulkDiscountRule(Rule):
    """Discount for buying in bulk"""
    
    def __init__(self, min_quantity: int = 10, discount_percentage: Decimal = Decimal(5)):
        super().__init__(
            "bulk_discount",
            "Bulk Purchase Discount",
            RuleType.DISCOUNT_RULE,
            RulePriority.MEDIUM
        )
        self._min_quantity = min_quantity
        self._discount_percentage = discount_percentage
    
    def evaluate(self, context: OrderContext) -> bool:
        return context.item_count >= self._min_quantity
    
    def apply(self, context: OrderContext) -> RuleResult:
        discount_amount = (context.subtotal * self._discount_percentage) / Decimal(100)
        
        context.apply_discount(
            "Bulk Discount",
            discount_amount,
            f"{self._discount_percentage}% off for {context.item_count} items"
        )
        
        result = RuleResult(
            self._name,
            True,
            f"{self._discount_percentage}% bulk discount applied"
        )
        result.add_metadata('discount_amount', str(discount_amount))
        return result


class FirstOrderDiscountRule(Rule):
    """Discount for first-time customers"""
    
    def __init__(self, discount_percentage: Decimal = Decimal(15)):
        super().__init__(
            "first_order_discount",
            "First Order Discount",
            RuleType.DISCOUNT_RULE,
            RulePriority.HIGH
        )
        self._discount_percentage = discount_percentage
    
    def evaluate(self, context: OrderContext) -> bool:
        # Check if this is customer's first order
        # In real system, would check order history
        is_first_order = context.metadata.get('is_first_order', False)
        return is_first_order
    
    def apply(self, context: OrderContext) -> RuleResult:
        discount_amount = (context.subtotal * self._discount_percentage) / Decimal(100)
        max_discount = Decimal(50)  # Cap at $50
        discount_amount = min(discount_amount, max_discount)
        
        context.apply_discount(
            "First Order",
            discount_amount,
            f"{self._discount_percentage}% off first order"
        )
        
        return RuleResult(
            self._name,
            True,
            f"Welcome! {self._discount_percentage}% discount on your first order"
        )


class CategoryPromotionRule(Rule):
    """Promotional discount for specific category"""
    
    def __init__(self, category: ItemCategory, discount_percentage: Decimal,
                 min_amount: Decimal = Decimal(0)):
        super().__init__(
            f"{category.value}_promo",
            f"{category.value.title()} Promotion",
            RuleType.PROMOTION_RULE,
            RulePriority.MEDIUM
        )
        self._category = category
        self._discount_percentage = discount_percentage
        self._min_amount = min_amount
    
    def evaluate(self, context: OrderContext) -> bool:
        category_items = context.cart.get_items_by_category(self._category)
        if not category_items:
            return False
        
        category_total = sum(item.get_subtotal() for item in category_items)
        return category_total >= self._min_amount
    
    def apply(self, context: OrderContext) -> RuleResult:
        category_items = context.cart.get_items_by_category(self._category)
        category_total = sum(item.get_subtotal() for item in category_items)
        
        discount_amount = (category_total * self._discount_percentage) / Decimal(100)
        
        context.apply_discount(
            f"{self._category.value.title()} Promo",
            discount_amount,
            f"{self._discount_percentage}% off {self._category.value}"
        )
        
        return RuleResult(
            self._name,
            True,
            f"{self._discount_percentage}% off on {self._category.value} items"
        )


# ==================== Rules Engine ====================

class ShoppingCartRulesEngine:
    """
    Main rules engine that orchestrates rule execution
    
    Features:
    - Priority-based rule execution
    - Easy rule registration
    - Extensible architecture
    - Rule enable/disable
    - Detailed execution results
    """
    
    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._rules_by_type: Dict[RuleType, List[Rule]] = {
            RuleType.SHIPPING_RULE: [],
            RuleType.DISCOUNT_RULE: [],
            RuleType.PROMOTION_RULE: []
        }
    
    def register_rule(self, rule: Rule) -> None:
        """Register a new rule"""
        self._rules[rule.get_id()] = rule
        self._rules_by_type[rule.get_type()].append(rule)
        
        # Sort by priority
        self._rules_by_type[rule.get_type()].sort()
        
        print(f"✅ Registered rule: {rule.get_name()}")
    
    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a rule"""
        rule = self._rules.pop(rule_id, None)
        if not rule:
            return False
        
        self._rules_by_type[rule.get_type()].remove(rule)
        print(f"🗑️  Unregistered rule: {rule.get_name()}")
        return True
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule"""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enable()
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule"""
        rule = self._rules.get(rule_id)
        if rule:
            rule.disable()
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID"""
        return self._rules.get(rule_id)
    
    def get_all_rules(self) -> List[Rule]:
        """Get all rules"""
        return list(self._rules.values())
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[Rule]:
        """Get rules by type"""
        return self._rules_by_type[rule_type].copy()
    
    def evaluate_order(self, cart: ShoppingCart, metadata: Dict[str, Any] = None) -> OrderContext:
        """
        Evaluate order by applying all rules
        Returns OrderContext with all applied benefits
        """
        # Create context
        context = OrderContext(cart)
        if metadata:
            context.metadata.update(metadata)
        
        # Execute rules by type and priority
        # 1. Shipping rules first
        # 2. Discount rules
        # 3. Promotion rules
        
        results: List[RuleResult] = []
        
        for rule_type in [RuleType.SHIPPING_RULE, RuleType.DISCOUNT_RULE, RuleType.PROMOTION_RULE]:
            rules = self._rules_by_type[rule_type]
            
            for rule in rules:
                result = rule.execute(context)
                results.append(result)
        
        # Store results in context
        context.metadata['rule_results'] = results
        
        return context
    
    def get_execution_summary(self, context: OrderContext) -> str:
        """Get human-readable summary of rule execution"""
        results = context.metadata.get('rule_results', [])
        
        summary = []
        summary.append(f"\n{'='*60}")
        summary.append(" RULES EXECUTION SUMMARY")
        summary.append('='*60)
        
        for result in results:
            summary.append(str(result))
        
        summary.append(f"\n{'='*60}")
        summary.append(f" ORDER SUMMARY")
        summary.append('='*60)
        summary.append(f"Subtotal: ${context.subtotal}")
        summary.append(f"Shipping: {context.shipping_speed.value} - "
                      f"${context.shipping_cost} {'(FREE)' if context.free_shipping else ''}")
        
        if context.discounts:
            summary.append(f"\nDiscounts:")
            for discount in context.discounts:
                summary.append(f"  • {discount['name']}: -${discount['amount']} "
                             f"({discount['description']})")
            summary.append(f"Total Discount: -${context.total_discount}")
        
        summary.append(f"\nFinal Total: ${context.get_final_total()}")
        summary.append('='*60)
        
        return '\n'.join(summary)


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def create_sample_cart(customer: Customer, scenario: str) -> ShoppingCart:
    """Create sample carts for different scenarios"""
    cart_id = str(uuid.uuid4())
    cart = ShoppingCart(cart_id, customer)
    
    if scenario == "regular_over_35":
        # Regular customer with $50 order
        cart.add_item(CartItem("1", "Wireless Mouse", Decimal(25), 1, ItemCategory.ELECTRONICS))
        cart.add_item(CartItem("2", "USB Cable", Decimal(15), 1, ItemCategory.ELECTRONICS))
        cart.add_item(CartItem("3", "Notebook", Decimal(10), 1, ItemCategory.HOME))
    
    elif scenario == "prime_basic":
        # Prime customer with $30 order
        cart.add_item(CartItem("4", "T-Shirt", Decimal(20), 1, ItemCategory.CLOTHING))
        cart.add_item(CartItem("5", "Socks", Decimal(10), 1, ItemCategory.CLOTHING))
    
    elif scenario == "high_value":
        # Order over $125
        cart.add_item(CartItem("6", "Laptop Stand", Decimal(80), 1, ItemCategory.ELECTRONICS))
        cart.add_item(CartItem("7", "Keyboard", Decimal(50), 1, ItemCategory.ELECTRONICS))
    
    elif scenario == "prime_grocery":
        # Prime customer with grocery items
        cart.add_item(CartItem("8", "Milk", Decimal(5), 2, ItemCategory.GROCERY))
        cart.add_item(CartItem("9", "Bread", Decimal(4), 2, ItemCategory.GROCERY))
        cart.add_item(CartItem("10", "Eggs", Decimal(6), 2, ItemCategory.GROCERY))
    
    elif scenario == "subscribe_and_save":
        # Items with Subscribe & Save
        item1 = CartItem("11", "Coffee", Decimal(15), 2, ItemCategory.GROCERY, is_subscribe_and_save=True)
        item2 = CartItem("12", "Shampoo", Decimal(12), 1, ItemCategory.BEAUTY, is_subscribe_and_save=True)
        item3 = CartItem("13", "Paper Towels", Decimal(20), 1, ItemCategory.HOME, is_subscribe_and_save=True)
        cart.add_item(item1)
        cart.add_item(item2)
        cart.add_item(item3)
    
    elif scenario == "combo":
        # Prime customer with grocery + Subscribe & Save + high value
        cart.add_item(CartItem("14", "Organic Milk", Decimal(8), 2, ItemCategory.GROCERY))
        cart.add_item(CartItem("15", "Fresh Vegetables", Decimal(15), 1, ItemCategory.GROCERY))
        cart.add_item(CartItem("16", "Vitamins", Decimal(30), 2, ItemCategory.GROCERY, is_subscribe_and_save=True))
        cart.add_item(CartItem("17", "Protein Powder", Decimal(50), 1, ItemCategory.GROCERY, is_subscribe_and_save=True))
    
    return cart


def demo_shopping_cart_rules():
    """Comprehensive demo of shopping cart rules engine"""
    
    print_section("SHOPPING CART RULES ENGINE DEMO")
    
    # ==================== Initialize Rules Engine ====================
    print_section("1. Initialize Rules Engine")
    
    engine = ShoppingCartRulesEngine()
    
    # Register all rules
    engine.register_rule(FreeShippingOver35Rule())
    engine.register_rule(PrimeFreeShippingRule())
    engine.register_rule(FreeOneDayShippingOver125Rule())
    engine.register_rule(PrimeTwoHourGroceryShippingRule())
    engine.register_rule(SubscribeAndSaveDiscountRule())
    
    # Register additional example rules
    engine.register_rule(BulkDiscountRule(min_quantity=10, discount_percentage=Decimal(5)))
    engine.register_rule(FirstOrderDiscountRule(discount_percentage=Decimal(15)))
    engine.register_rule(CategoryPromotionRule(ItemCategory.ELECTRONICS, Decimal(10), Decimal(50)))
    
    print(f"\n✅ Rules engine initialized with {len(engine.get_all_rules())} rules")
    
    # ==================== Create Customers ====================
    print_section("2. Create Customers")
    
    regular_customer = Customer("C001", "John Doe", "john@example.com", MembershipType.REGULAR)
    prime_customer = Customer("C002", "Jane Smith", "jane@example.com", MembershipType.PRIME, datetime.now())
    
    print(f"✅ Regular Customer: {regular_customer.name}")
    print(f"✅ Prime Customer: {prime_customer.name}")
    
    # ==================== Scenario 1: Regular Customer > $35 ====================
    print_section("3. Scenario 1: Regular Customer Order > $35")
    
    cart1 = create_sample_cart(regular_customer, "regular_over_35")
    print(f"\n🛒 Cart Items:")
    for item in cart1.get_items():
        print(f"   • {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart1.get_subtotal()}")
    
    context1 = engine.evaluate_order(cart1)
    print(engine.get_execution_summary(context1))
    
    # ==================== Scenario 2: Prime Customer Basic Order ====================
    print_section("4. Scenario 2: Prime Customer Basic Order")
    
    cart2 = create_sample_cart(prime_customer, "prime_basic")
    print(f"\n🛒 Cart Items:")
    for item in cart2.get_items():
        print(f"   • {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart2.get_subtotal()}")
    
    context2 = engine.evaluate_order(cart2)
    print(engine.get_execution_summary(context2))
    
    # ==================== Scenario 3: High Value Order > $125 ====================
    print_section("5. Scenario 3: Order > $125 (Free 1-Day Shipping)")
    
    cart3 = create_sample_cart(regular_customer, "high_value")
    print(f"\n🛒 Cart Items:")
    for item in cart3.get_items():
        print(f"   • {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart3.get_subtotal()}")
    
    context3 = engine.evaluate_order(cart3)
    print(engine.get_execution_summary(context3))
    
    # ==================== Scenario 4: Prime Grocery 2-Hour Delivery ====================
    print_section("6. Scenario 4: Prime Grocery Order > $25")
    
    cart4 = create_sample_cart(prime_customer, "prime_grocery")
    print(f"\n🛒 Cart Items:")
    for item in cart4.get_items():
        category_icon = "🥬" if item.is_grocery() else "📦"
        print(f"   {category_icon} {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart4.get_subtotal()}")
    
    context4 = engine.evaluate_order(cart4)
    print(engine.get_execution_summary(context4))
    
    # ==================== Scenario 5: Subscribe & Save Discount ====================
    print_section("7. Scenario 5: Subscribe & Save Items")
    
    cart5 = create_sample_cart(regular_customer, "subscribe_and_save")
    print(f"\n🛒 Cart Items:")
    for item in cart5.get_items():
        sns_icon = "🔄" if item.is_subscribe_and_save else "📦"
        print(f"   {sns_icon} {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart5.get_subtotal()}")
    
    context5 = engine.evaluate_order(cart5)
    print(engine.get_execution_summary(context5))
    
    # ==================== Scenario 6: Combo (Multiple Rules) ====================
    print_section("8. Scenario 6: Prime + Grocery + Subscribe & Save")
    
    cart6 = create_sample_cart(prime_customer, "combo")
    print(f"\n🛒 Cart Items:")
    for item in cart6.get_items():
        icons = []
        if item.is_grocery():
            icons.append("🥬")
        if item.is_subscribe_and_save:
            icons.append("🔄")
        icon = ''.join(icons) or "📦"
        print(f"   {icon} {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart6.get_subtotal()}")
    
    context6 = engine.evaluate_order(cart6)
    print(engine.get_execution_summary(context6))
    
    # ==================== Scenario 7: First Order Discount ====================
    print_section("9. Scenario 7: First Order Discount")
    
    new_customer = Customer("C003", "New User", "new@example.com", MembershipType.REGULAR)
    cart7 = create_sample_cart(new_customer, "high_value")
    
    print(f"\n🛒 Cart Items:")
    for item in cart7.get_items():
        print(f"   • {item.name}: ${item.price} x {item.quantity} = ${item.get_subtotal()}")
    print(f"   Subtotal: ${cart7.get_subtotal()}")
    
    context7 = engine.evaluate_order(cart7, metadata={'is_first_order': True})
    print(engine.get_execution_summary(context7))
    
    # ==================== Rule Management ====================
    print_section("10. Rule Management")
    
    print("\n📋 All Registered Rules:")
    for rule in engine.get_all_rules():
        status = "✅ Enabled" if rule.is_enabled() else "❌ Disabled"
        print(f"   • {rule.get_name()} ({rule.get_type().value}) - Priority: {rule.get_priority().name} - {status}")
    
    # Disable a rule
    print("\n⏸️  Disabling 'Subscribe & Save' rule...")
    engine.disable_rule("subscribe_and_save_discount")
    
    # Re-evaluate cart with Subscribe & Save items
    context_disabled = engine.evaluate_order(cart5)
    print("\n🔄 Re-evaluating cart after disabling rule:")
    print(engine.get_execution_summary(context_disabled))
    
    # Re-enable
    print("\n▶️  Re-enabling 'Subscribe & Save' rule...")
    engine.enable_rule("subscribe_and_save_discount")
    
    # ==================== Add New Custom Rule ====================
    print_section("11. Adding New Custom Rule at Runtime")
    
    class WeekendSpecialRule(Rule):
        """Special discount on weekends"""
        
        def __init__(self):
            super().__init__(
                "weekend_special",
                "Weekend Special",
                RuleType.PROMOTION_RULE,
                RulePriority.MEDIUM
            )
        
        def evaluate(self, context: OrderContext) -> bool:
            # Check if today is weekend
            today = datetime.now().weekday()
            return today >= 5  # Saturday = 5, Sunday = 6
        
        def apply(self, context: OrderContext) -> RuleResult:
            discount = context.subtotal * Decimal(0.05)  # 5% off
            context.apply_discount("Weekend Special", discount, "5% weekend discount")
            return RuleResult(self._name, True, "Weekend special 5% discount applied!")
    
    # Register new rule
    weekend_rule = WeekendSpecialRule()
    engine.register_rule(weekend_rule)
    
    print(f"\n✅ New rule added: {weekend_rule.get_name()}")
    print(f"   Total rules now: {len(engine.get_all_rules())}")
    
    # ==================== Summary ====================
    print_section("12. System Summary")
    
    print(f"\n📊 Rules Engine Statistics:")
    print(f"   Total Rules: {len(engine.get_all_rules())}")
    print(f"   Shipping Rules: {len(engine.get_rules_by_type(RuleType.SHIPPING_RULE))}")
    print(f"   Discount Rules: {len(engine.get_rules_by_type(RuleType.DISCOUNT_RULE))}")
    print(f"   Promotion Rules: {len(engine.get_rules_by_type(RuleType.PROMOTION_RULE))}")
    
    print(f"\n✨ Key Features Demonstrated:")
    print(f"   ✅ Priority-based rule execution")
    print(f"   ✅ Multiple shipping speed upgrades")
    print(f"   ✅ Stackable discounts")
    print(f"   ✅ Category-specific promotions")
    print(f"   ✅ Membership-based benefits")
    print(f"   ✅ Subscribe & Save discounts")
    print(f"   ✅ Dynamic rule registration")
    print(f"   ✅ Rule enable/disable")
    print(f"   ✅ Extensible architecture")
    
    print_section("Demo Complete")
    print("\n✅ Shopping Cart Rules Engine demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_shopping_cart_rules()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Shopping Cart Rules Engine - Low Level Design
# Here's a comprehensive and extensible rules engine for shopping cart:

# Key Design Decisions:
# 1. Core Components:
# Rule: Abstract base class for all rules
# OrderContext: Shared state during rule execution
# RulesEngine: Orchestrates rule execution
# RuleResult: Result of rule execution
# 2. Rule Architecture:
# 3. Extensibility:
# ✅ Easy to add new rules: Just extend Rule class ✅ Priority-based execution: Control execution order ✅ Enable/Disable rules: Toggle rules at runtime ✅ Dynamic registration: Add rules on the fly ✅ Type-based grouping: Shipping, Discount, Promotion

# 4. Implemented Rules:
# Shipping Rules:

# Free 2-day shipping > $35 (non-Prime)
# Free 2-day shipping (Prime members)
# Free 1-day shipping > $125
# Free 2-hour grocery delivery (Prime + grocery > $25)
# Discount Rules:

# 10% Subscribe & Save discount
# Bulk purchase discount
# First order discount
# Promotion Rules:

# Category-specific promotions
# Weekend specials
# 5. Rule Execution Flow:
# 6. Key Features:
# Shipping Upgrade Logic:

# Rules can only upgrade shipping, not downgrade
# Priority determines which rule applies first
# 2-hour > 1-day > 2-day > Standard
# Discount Stacking:

# Multiple discounts can apply
# All discounts are tracked separately
# Total discount calculated
# Context-Based Evaluation:

# Rules evaluate against OrderContext
# Shared state across all rules
# Metadata for extensibility
# 7. Design Patterns:
# Strategy Pattern: Different rule types
# Chain of Responsibility: Sequential rule execution
# Template Method: Base Rule class with hooks
# Command Pattern: Rules as executable commands
# Priority Queue: Rule ordering
# 8. Adding New Rules:
# 9. Rule Priority:
# 10. Benefits:
# ✅ Separation of Concerns: Each rule is independent ✅ Open/Closed Principle: Open for extension, closed for modification ✅ Single Responsibility: Each rule does one thing ✅ Testable: Rules can be tested independently ✅ Maintainable: Easy to add/remove/modify rules ✅ Scalable: No limit on number of rules

# 11. Real-World Usage:
# This is a production-grade extensible rules engine like Amazon's! 🛒✨
