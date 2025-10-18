from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any, Callable
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import uuid
import json
from threading import RLock
from decimal import Decimal


# ==================== Enums ====================

class CouponStatus(Enum):
    """Coupon status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    EXHAUSTED = "exhausted"  # All uses consumed


class VoucherStatus(Enum):
    """Voucher status"""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VoucherType(Enum):
    """Type of voucher"""
    UNASSIGNED = "unassigned"  # Anyone can use, single use
    PRE_ASSIGNED = "pre_assigned"  # Attached to specific user


class DiscountType(Enum):
    """Type of discount"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SHIPPING = "free_shipping"
    BUY_X_GET_Y = "buy_x_get_y"


class RuleType(Enum):
    """Type of eligibility rule"""
    MIN_CART_VALUE = "min_cart_value"
    MIN_AGE = "min_age"
    MAX_AGE = "max_age"
    SPECIFIC_CATEGORY = "specific_category"
    SPECIFIC_PRODUCT = "specific_product"
    FIRST_ORDER = "first_order"
    USER_LOCATION = "user_location"
    PAYMENT_METHOD = "payment_method"


class UsageLogStatus(Enum):
    """Status of usage attempt"""
    SUCCESS = "success"
    FAILED = "failed"


# ==================== Rule System ====================

class Rule(ABC):
    """Abstract base class for eligibility rules"""
    
    def __init__(self, rule_type: RuleType):
        self._rule_type = rule_type
    
    def get_type(self) -> RuleType:
        return self._rule_type
    
    @abstractmethod
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if rule is satisfied"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        pass


class MinCartValueRule(Rule):
    """Minimum cart value rule"""
    
    def __init__(self, min_value: Decimal):
        super().__init__(RuleType.MIN_CART_VALUE)
        self._min_value = min_value
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        cart_value = context.get('cart_value', Decimal(0))
        return cart_value >= self._min_value
    
    def get_description(self) -> str:
        return f"Minimum cart value: ${self._min_value}"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._rule_type.value,
            'min_value': str(self._min_value)
        }


class AgeRule(Rule):
    """Age-based rule"""
    
    def __init__(self, min_age: Optional[int] = None, max_age: Optional[int] = None):
        rule_type = RuleType.MIN_AGE if min_age else RuleType.MAX_AGE
        super().__init__(rule_type)
        self._min_age = min_age
        self._max_age = max_age
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        user_age = context.get('user_age')
        if user_age is None:
            return False
        
        if self._min_age and user_age < self._min_age:
            return False
        if self._max_age and user_age > self._max_age:
            return False
        
        return True
    
    def get_description(self) -> str:
        if self._min_age and self._max_age:
            return f"Age between {self._min_age} and {self._max_age}"
        elif self._min_age:
            return f"Minimum age: {self._min_age}"
        else:
            return f"Maximum age: {self._max_age}"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._rule_type.value,
            'min_age': self._min_age,
            'max_age': self._max_age
        }


class CategoryRule(Rule):
    """Specific category rule"""
    
    def __init__(self, categories: Set[str]):
        super().__init__(RuleType.SPECIFIC_CATEGORY)
        self._categories = categories
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        cart_categories = set(context.get('categories', []))
        return bool(cart_categories.intersection(self._categories))
    
    def get_description(self) -> str:
        return f"Valid for categories: {', '.join(self._categories)}"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._rule_type.value,
            'categories': list(self._categories)
        }


class ProductRule(Rule):
    """Specific product rule"""
    
    def __init__(self, product_ids: Set[str]):
        super().__init__(RuleType.SPECIFIC_PRODUCT)
        self._product_ids = product_ids
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        cart_products = set(context.get('product_ids', []))
        return bool(cart_products.intersection(self._product_ids))
    
    def get_description(self) -> str:
        return f"Valid for specific products (count: {len(self._product_ids)})"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._rule_type.value,
            'product_ids': list(self._product_ids)
        }


class FirstOrderRule(Rule):
    """First order rule"""
    
    def __init__(self):
        super().__init__(RuleType.FIRST_ORDER)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        return context.get('is_first_order', False)
    
    def get_description(self) -> str:
        return "Valid for first order only"
    
    def to_dict(self) -> Dict:
        return {'type': self._rule_type.value}


class LocationRule(Rule):
    """User location rule"""
    
    def __init__(self, locations: Set[str]):
        super().__init__(RuleType.USER_LOCATION)
        self._locations = locations
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        user_location = context.get('user_location')
        return user_location in self._locations
    
    def get_description(self) -> str:
        return f"Valid for locations: {', '.join(self._locations)}"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._rule_type.value,
            'locations': list(self._locations)
        }


# ==================== Discount Models ====================

class Discount:
    """Discount configuration"""
    
    def __init__(self, discount_type: DiscountType, value: Decimal,
                 max_discount: Optional[Decimal] = None):
        self._discount_type = discount_type
        self._value = value
        self._max_discount = max_discount  # Cap for percentage discounts
    
    def get_type(self) -> DiscountType:
        return self._discount_type
    
    def calculate_discount(self, cart_value: Decimal) -> Decimal:
        """Calculate discount amount"""
        if self._discount_type == DiscountType.PERCENTAGE:
            discount = (cart_value * self._value) / Decimal(100)
            if self._max_discount:
                discount = min(discount, self._max_discount)
            return discount
        
        elif self._discount_type == DiscountType.FIXED_AMOUNT:
            return min(self._value, cart_value)
        
        elif self._discount_type == DiscountType.FREE_SHIPPING:
            # Would need shipping cost from context
            return Decimal(0)
        
        return Decimal(0)
    
    def get_description(self) -> str:
        if self._discount_type == DiscountType.PERCENTAGE:
            desc = f"{self._value}% off"
            if self._max_discount:
                desc += f" (max ${self._max_discount})"
            return desc
        elif self._discount_type == DiscountType.FIXED_AMOUNT:
            return f"${self._value} off"
        elif self._discount_type == DiscountType.FREE_SHIPPING:
            return "Free shipping"
        return "Discount"
    
    def to_dict(self) -> Dict:
        return {
            'type': self._discount_type.value,
            'value': str(self._value),
            'max_discount': str(self._max_discount) if self._max_discount else None
        }


# ==================== Coupon Model ====================

class Coupon:
    """Coupon with rules and usage limits"""
    
    def __init__(self, coupon_id: str, code: str, name: str,
                 discount: Discount, creator_id: str):
        self._coupon_id = coupon_id
        self._code = code.upper()  # Always uppercase
        self._name = name
        self._discount = discount
        self._creator_id = creator_id
        
        # Status
        self._status = CouponStatus.ACTIVE
        
        # Validity period
        self._start_date: Optional[datetime] = None
        self._end_date: Optional[datetime] = None
        
        # Usage limits
        self._overall_usage_limit: Optional[int] = None  # Total uses
        self._per_user_limit: Optional[int] = None  # Per user limit
        self._overall_usage_count = 0
        self._user_usage_count: Dict[str, int] = {}  # user_id -> count
        
        # Eligibility rules
        self._rules: List[Rule] = []
        
        # Metadata
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._description: Optional[str] = None
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._coupon_id
    
    def get_code(self) -> str:
        return self._code
    
    def get_name(self) -> str:
        return self._name
    
    def get_discount(self) -> Discount:
        return self._discount
    
    def get_status(self) -> CouponStatus:
        return self._status
    
    def set_status(self, status: CouponStatus) -> None:
        with self._lock:
            self._status = status
            self._updated_at = datetime.now()
    
    def activate(self) -> None:
        """Activate coupon"""
        self.set_status(CouponStatus.ACTIVE)
    
    def deactivate(self) -> None:
        """Deactivate coupon"""
        self.set_status(CouponStatus.INACTIVE)
    
    def set_validity_period(self, start_date: datetime, end_date: datetime) -> None:
        """Set validity period"""
        self._start_date = start_date
        self._end_date = end_date
    
    def get_start_date(self) -> Optional[datetime]:
        return self._start_date
    
    def get_end_date(self) -> Optional[datetime]:
        return self._end_date
    
    def is_valid_date(self) -> bool:
        """Check if coupon is valid based on date"""
        now = datetime.now()
        
        if self._start_date and now < self._start_date:
            return False
        
        if self._end_date and now > self._end_date:
            return False
        
        return True
    
    def set_overall_usage_limit(self, limit: int) -> None:
        """Set overall usage limit"""
        self._overall_usage_limit = limit
    
    def set_per_user_limit(self, limit: int) -> None:
        """Set per-user usage limit"""
        self._per_user_limit = limit
    
    def get_overall_usage_count(self) -> int:
        return self._overall_usage_count
    
    def get_user_usage_count(self, user_id: str) -> int:
        return self._user_usage_count.get(user_id, 0)
    
    def can_use(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if user can use this coupon"""
        with self._lock:
            # Check status
            if self._status != CouponStatus.ACTIVE:
                return False, f"Coupon is {self._status.value}"
            
            # Check date validity
            if not self.is_valid_date():
                return False, "Coupon is not valid at this time"
            
            # Check overall usage limit
            if self._overall_usage_limit and self._overall_usage_count >= self._overall_usage_limit:
                return False, "Coupon usage limit exhausted"
            
            # Check per-user limit
            if self._per_user_limit:
                user_count = self._user_usage_count.get(user_id, 0)
                if user_count >= self._per_user_limit:
                    return False, f"You have already used this coupon {user_count} times"
            
            return True, None
    
    def add_rule(self, rule: Rule) -> None:
        """Add eligibility rule"""
        self._rules.append(rule)
    
    def get_rules(self) -> List[Rule]:
        return self._rules.copy()
    
    def check_eligibility(self, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Check if user is eligible based on rules"""
        for rule in self._rules:
            if not rule.evaluate(context):
                return False, f"Rule not satisfied: {rule.get_description()}"
        
        return True, None
    
    def apply(self, user_id: str, context: Dict[str, Any]) -> tuple[bool, Optional[Decimal], Optional[str]]:
        """
        Apply coupon and return (success, discount_amount, error_message)
        """
        with self._lock:
            # Check if can use
            can_use, error = self.can_use(user_id)
            if not can_use:
                return False, None, error
            
            # Check eligibility rules
            eligible, error = self.check_eligibility(context)
            if not eligible:
                return False, None, error
            
            # Calculate discount
            cart_value = context.get('cart_value', Decimal(0))
            discount_amount = self._discount.calculate_discount(cart_value)
            
            # Update usage counts
            self._overall_usage_count += 1
            self._user_usage_count[user_id] = self._user_usage_count.get(user_id, 0) + 1
            
            # Check if exhausted
            if self._overall_usage_limit and self._overall_usage_count >= self._overall_usage_limit:
                self._status = CouponStatus.EXHAUSTED
            
            return True, discount_amount, None
    
    def set_description(self, description: str) -> None:
        self._description = description
    
    def get_description(self) -> Optional[str]:
        return self._description
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'coupon_id': self._coupon_id,
            'code': self._code,
            'name': self._name,
            'status': self._status.value,
            'discount': self._discount.to_dict(),
            'description': self._description,
            'start_date': self._start_date.isoformat() if self._start_date else None,
            'end_date': self._end_date.isoformat() if self._end_date else None,
            'overall_usage_limit': self._overall_usage_limit,
            'overall_usage_count': self._overall_usage_count,
            'per_user_limit': self._per_user_limit,
            'rules': [rule.to_dict() for rule in self._rules],
            'created_at': self._created_at.isoformat(),
            'updated_at': self._updated_at.isoformat()
        }


# ==================== Voucher Model ====================

class Voucher:
    """Voucher (single-use coupon)"""
    
    def __init__(self, voucher_id: str, code: str, voucher_type: VoucherType,
                 discount: Discount, creator_id: str):
        self._voucher_id = voucher_id
        self._code = code.upper()
        self._voucher_type = voucher_type
        self._discount = discount
        self._creator_id = creator_id
        
        # Status
        self._status = VoucherStatus.ACTIVE
        
        # Assignment
        self._assigned_user_id: Optional[str] = None
        
        # Usage
        self._used_by: Optional[str] = None
        self._used_at: Optional[datetime] = None
        self._order_id: Optional[str] = None
        
        # Validity
        self._expiry_date: Optional[datetime] = None
        
        # Metadata
        self._created_at = datetime.now()
        self._description: Optional[str] = None
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._voucher_id
    
    def get_code(self) -> str:
        return self._code
    
    def get_type(self) -> VoucherType:
        return self._voucher_type
    
    def get_discount(self) -> Discount:
        return self._discount
    
    def get_status(self) -> VoucherStatus:
        return self._status
    
    def set_status(self, status: VoucherStatus) -> None:
        with self._lock:
            self._status = status
    
    def assign_to_user(self, user_id: str) -> bool:
        """Assign voucher to user (for PRE_ASSIGNED type)"""
        with self._lock:
            if self._voucher_type != VoucherType.PRE_ASSIGNED:
                return False
            
            if self._assigned_user_id:
                return False
            
            self._assigned_user_id = user_id
            return True
    
    def get_assigned_user(self) -> Optional[str]:
        return self._assigned_user_id
    
    def set_expiry_date(self, expiry_date: datetime) -> None:
        self._expiry_date = expiry_date
    
    def get_expiry_date(self) -> Optional[datetime]:
        return self._expiry_date
    
    def is_expired(self) -> bool:
        """Check if voucher is expired"""
        if self._expiry_date and datetime.now() > self._expiry_date:
            return True
        return False
    
    def can_use(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if user can use this voucher"""
        with self._lock:
            # Check status
            if self._status != VoucherStatus.ACTIVE:
                return False, f"Voucher is {self._status.value}"
            
            # Check expiry
            if self.is_expired():
                self._status = VoucherStatus.EXPIRED
                return False, "Voucher has expired"
            
            # Check assignment for PRE_ASSIGNED type
            if self._voucher_type == VoucherType.PRE_ASSIGNED:
                if self._assigned_user_id != user_id:
                    return False, "This voucher is not assigned to you"
            
            # Check if already used
            if self._used_by:
                return False, "Voucher already used"
            
            return True, None
    
    def use(self, user_id: str, cart_value: Decimal, order_id: str) -> tuple[bool, Optional[Decimal], Optional[str]]:
        """
        Use the voucher
        Returns (success, discount_amount, error_message)
        """
        with self._lock:
            # Check if can use
            can_use, error = self.can_use(user_id)
            if not can_use:
                return False, None, error
            
            # Calculate discount
            discount_amount = self._discount.calculate_discount(cart_value)
            
            # Mark as used
            self._used_by = user_id
            self._used_at = datetime.now()
            self._order_id = order_id
            self._status = VoucherStatus.USED
            
            return True, discount_amount, None
    
    def cancel(self) -> bool:
        """Cancel voucher"""
        with self._lock:
            if self._status == VoucherStatus.USED:
                return False
            
            self._status = VoucherStatus.CANCELLED
            return True
    
    def set_description(self, description: str) -> None:
        self._description = description
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'voucher_id': self._voucher_id,
            'code': self._code,
            'type': self._voucher_type.value,
            'status': self._status.value,
            'discount': self._discount.to_dict(),
            'description': self._description,
            'assigned_to': self._assigned_user_id,
            'used_by': self._used_by,
            'used_at': self._used_at.isoformat() if self._used_at else None,
            'order_id': self._order_id,
            'expiry_date': self._expiry_date.isoformat() if self._expiry_date else None,
            'created_at': self._created_at.isoformat()
        }


# ==================== Usage Log ====================

class UsageLog:
    """Log of coupon/voucher usage attempts"""
    
    def __init__(self, log_id: str, user_id: str, code: str,
                 status: UsageLogStatus, discount_amount: Optional[Decimal] = None,
                 error_message: Optional[str] = None, order_id: Optional[str] = None):
        self._log_id = log_id
        self._user_id = user_id
        self._code = code
        self._status = status
        self._discount_amount = discount_amount
        self._error_message = error_message
        self._order_id = order_id
        self._timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'log_id': self._log_id,
            'user_id': self._user_id,
            'code': self._code,
            'status': self._status.value,
            'discount_amount': str(self._discount_amount) if self._discount_amount else None,
            'error_message': self._error_message,
            'order_id': self._order_id,
            'timestamp': self._timestamp.isoformat()
        }


# ==================== User Model ====================

class User:
    """User model"""
    
    def __init__(self, user_id: str, name: str, email: str, age: int, location: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._age = age
        self._location = location
        self._is_first_order = True
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_age(self) -> int:
        return self._age
    
    def get_location(self) -> str:
        return self._location
    
    def is_first_order(self) -> bool:
        return self._is_first_order
    
    def mark_order_placed(self) -> None:
        self._is_first_order = False


# ==================== Voucher Management Service ====================

class VoucherManagementService:
    """
    Main service for managing coupons and vouchers
    Provides APIs for admin and users
    """
    
    def __init__(self):
        # Storage
        self._coupons: Dict[str, Coupon] = {}
        self._vouchers: Dict[str, Voucher] = {}
        self._users: Dict[str, User] = {}
        self._usage_logs: List[UsageLog] = []
        
        # Indexes
        self._coupon_by_code: Dict[str, str] = {}  # code -> coupon_id
        self._voucher_by_code: Dict[str, str] = {}  # code -> voucher_id
        self._user_vouchers: Dict[str, Set[str]] = {}  # user_id -> voucher_ids
        
        # Thread safety
        self._lock = RLock()
    
    # ==================== User Management ====================
    
    def register_user(self, name: str, email: str, age: int, location: str) -> User:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        user = User(user_id, name, email, age, location)
        
        with self._lock:
            self._users[user_id] = user
            self._user_vouchers[user_id] = set()
        
        print(f"✅ User registered: {name}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Admin: Coupon Management ====================
    
    def create_coupon(self, admin_id: str, code: str, name: str,
                     discount: Discount, rules: List[Rule] = None) -> Coupon:
        """Admin: Create a new coupon"""
        coupon_id = str(uuid.uuid4())
        coupon = Coupon(coupon_id, code, name, discount, admin_id)
        
        # Add rules
        if rules:
            for rule in rules:
                coupon.add_rule(rule)
        
        with self._lock:
            self._coupons[coupon_id] = coupon
            self._coupon_by_code[code.upper()] = coupon_id
        
        print(f"✅ Coupon created: {code} - {name}")
        return coupon
    
    def update_coupon(self, admin_id: str, coupon_id: str, **kwargs) -> bool:
        """Admin: Update coupon"""
        coupon = self._coupons.get(coupon_id)
        if not coupon:
            return False
        
        with self._lock:
            if 'name' in kwargs:
                coupon._name = kwargs['name']
            
            if 'description' in kwargs:
                coupon.set_description(kwargs['description'])
            
            if 'overall_usage_limit' in kwargs:
                coupon.set_overall_usage_limit(kwargs['overall_usage_limit'])
            
            if 'per_user_limit' in kwargs:
                coupon.set_per_user_limit(kwargs['per_user_limit'])
            
            coupon._updated_at = datetime.now()
        
        print(f"✅ Coupon updated: {coupon.get_code()}")
        return True
    
    def activate_coupon(self, admin_id: str, coupon_id: str) -> bool:
        """Admin: Activate coupon"""
        coupon = self._coupons.get(coupon_id)
        if not coupon:
            return False
        
        coupon.activate()
        print(f"✅ Coupon activated: {coupon.get_code()}")
        return True
    
    def deactivate_coupon(self, admin_id: str, coupon_id: str) -> bool:
        """Admin: Deactivate coupon"""
        coupon = self._coupons.get(coupon_id)
        if not coupon:
            return False
        
        coupon.deactivate()
        print(f"⏸️  Coupon deactivated: {coupon.get_code()}")
        return True
    
    def delete_coupon(self, admin_id: str, coupon_id: str) -> bool:
        """Admin: Delete coupon"""
        with self._lock:
            coupon = self._coupons.get(coupon_id)
            if not coupon:
                return False
            
            # Remove from indexes
            self._coupon_by_code.pop(coupon.get_code(), None)
            
            # Remove coupon
            del self._coupons[coupon_id]
        
        print(f"🗑️  Coupon deleted: {coupon.get_code()}")
        return True
    
    # ==================== Admin: Voucher Management ====================
    
    def create_voucher(self, admin_id: str, code: str, voucher_type: VoucherType,
                      discount: Discount, assigned_user_id: Optional[str] = None) -> Voucher:
        """Admin: Create a new voucher"""
        voucher_id = str(uuid.uuid4())
        voucher = Voucher(voucher_id, code, voucher_type, discount, admin_id)
        
        # Assign to user if PRE_ASSIGNED
        if voucher_type == VoucherType.PRE_ASSIGNED and assigned_user_id:
            voucher.assign_to_user(assigned_user_id)
            self._user_vouchers[assigned_user_id].add(voucher_id)
        
        with self._lock:
            self._vouchers[voucher_id] = voucher
            self._voucher_by_code[code.upper()] = voucher_id
        
        print(f"✅ Voucher created: {code} ({voucher_type.value})")
        return voucher
    
    def create_bulk_vouchers(self, admin_id: str, count: int,
                           voucher_type: VoucherType, discount: Discount,
                           prefix: str = "VOUCHER") -> List[Voucher]:
        """Admin: Create multiple vouchers"""
        vouchers = []
        
        for i in range(count):
            code = f"{prefix}{i+1:05d}"
            voucher = self.create_voucher(admin_id, code, voucher_type, discount)
            vouchers.append(voucher)
        
        print(f"✅ Created {count} vouchers")
        return vouchers
    
    def assign_voucher_to_user(self, admin_id: str, voucher_id: str, user_id: str) -> bool:
        """Admin: Assign voucher to user"""
        voucher = self._vouchers.get(voucher_id)
        if not voucher:
            return False
        
        if voucher.assign_to_user(user_id):
            self._user_vouchers[user_id].add(voucher_id)
            print(f"✅ Voucher {voucher.get_code()} assigned to user {user_id}")
            return True
        
        return False
    
    def cancel_voucher(self, admin_id: str, voucher_id: str) -> bool:
        """Admin: Cancel voucher"""
        voucher = self._vouchers.get(voucher_id)
        if not voucher:
            return False
        
        if voucher.cancel():
            print(f"🚫 Voucher cancelled: {voucher.get_code()}")
            return True
        
        return False
    
    # ==================== User: View Available Coupons/Vouchers ====================
    
    def get_available_coupons(self, user_id: str) -> List[Dict]:
        """User: Get list of available coupons"""
        user = self._users.get(user_id)
        if not user:
            return []
        
        available = []
        
        for coupon in self._coupons.values():
            # Check if user can use
            can_use, _ = coupon.can_use(user_id)
            
            if can_use and coupon.get_status() == CouponStatus.ACTIVE:
                available.append(coupon.to_dict())
        
        return available
    
    def get_user_vouchers(self, user_id: str) -> List[Dict]:
        """User: Get vouchers assigned to user"""
        voucher_ids = self._user_vouchers.get(user_id, set())
        vouchers = []
        
        for voucher_id in voucher_ids:
            voucher = self._vouchers.get(voucher_id)
            if voucher and voucher.get_status() == VoucherStatus.ACTIVE:
                vouchers.append(voucher.to_dict())
        
        return vouchers
    
    def get_all_unassigned_vouchers(self, user_id: str) -> List[Dict]:
        """User: Get all unassigned vouchers"""
        vouchers = []
        
        for voucher in self._vouchers.values():
            if (voucher.get_type() == VoucherType.UNASSIGNED and
                voucher.get_status() == VoucherStatus.ACTIVE):
                vouchers.append(voucher.to_dict())
        
        return vouchers
    
    # ==================== User: Apply Coupon/Voucher ====================
    
    def apply_coupon(self, user_id: str, code: str, context: Dict[str, Any],
                    order_id: str) -> tuple[bool, Optional[Decimal], Optional[str]]:
        """User: Apply a coupon"""
        coupon_id = self._coupon_by_code.get(code.upper())
        if not coupon_id:
            return False, None, "Invalid coupon code"
        
        coupon = self._coupons.get(coupon_id)
        if not coupon:
            return False, None, "Coupon not found"
        
        # Add user info to context
        user = self._users.get(user_id)
        if user:
            context['user_age'] = user.get_age()
            context['user_location'] = user.get_location()
            context['is_first_order'] = user.is_first_order()
        
        # Apply coupon
        success, discount, error = coupon.apply(user_id, context)
        
        # Log usage
        status = UsageLogStatus.SUCCESS if success else UsageLogStatus.FAILED
        log = UsageLog(
            str(uuid.uuid4()), user_id, code, status,
            discount, error, order_id if success else None
        )
        self._usage_logs.append(log)
        
        if success:
            print(f"✅ Coupon applied: {code} - Discount: ${discount}")
        else:
            print(f"❌ Coupon application failed: {error}")
        
        return success, discount, error
    
    def apply_voucher(self, user_id: str, code: str, cart_value: Decimal,
                     order_id: str) -> tuple[bool, Optional[Decimal], Optional[str]]:
        """User: Apply a voucher"""
        voucher_id = self._voucher_by_code.get(code.upper())
        if not voucher_id:
            return False, None, "Invalid voucher code"
        
        voucher = self._vouchers.get(voucher_id)
        if not voucher:
            return False, None, "Voucher not found"
        
        # Use voucher
        success, discount, error = voucher.use(user_id, cart_value, order_id)
        
        # Log usage
        status = UsageLogStatus.SUCCESS if success else UsageLogStatus.FAILED
        log = UsageLog(
            str(uuid.uuid4()), user_id, code, status,
            discount, error, order_id if success else None
        )
        self._usage_logs.append(log)
        
        if success:
            print(f"✅ Voucher applied: {code} - Discount: ${discount}")
        else:
            print(f"❌ Voucher application failed: {error}")
        
        return success, discount, error
    
    # ==================== Analytics ====================
    
    def get_coupon_statistics(self, coupon_id: str) -> Optional[Dict]:
        """Get coupon usage statistics"""
        coupon = self._coupons.get(coupon_id)
        if not coupon:
            return None
        
        return {
            'coupon_id': coupon_id,
            'code': coupon.get_code(),
            'status': coupon.get_status().value,
            'overall_usage': coupon.get_overall_usage_count(),
            'overall_limit': coupon._overall_usage_limit,
            'unique_users': len(coupon._user_usage_count),
            'per_user_limit': coupon._per_user_limit,
            'created_at': coupon._created_at.isoformat()
        }
    
    def get_usage_logs(self, user_id: Optional[str] = None,
                      code: Optional[str] = None) -> List[Dict]:
        """Get usage logs with optional filters"""
        logs = self._usage_logs
        
        if user_id:
            logs = [log for log in logs if log._user_id == user_id]
        
        if code:
            logs = [log for log in logs if log._code.upper() == code.upper()]
        
        return [log.to_dict() for log in logs]


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_voucher_system():
    """Comprehensive demo of voucher management system"""
    
    print_section("VOUCHER MANAGEMENT SYSTEM DEMO")
    
    service = VoucherManagementService()
    
    # ==================== Setup Users ====================
    print_section("1. Register Users")
    
    alice = service.register_user("Alice Johnson", "alice@example.com", 25, "NY")
    bob = service.register_user("Bob Smith", "bob@example.com", 17, "CA")
    charlie = service.register_user("Charlie Brown", "charlie@example.com", 35, "TX")
    
    admin_id = "admin_001"
    
    # ==================== Create Coupons with Rules ====================
    print_section("2. Admin: Create Coupons with Rules")
    
    # Coupon 1: 20% off, min cart value $100
    discount1 = Discount(DiscountType.PERCENTAGE, Decimal(20), max_discount=Decimal(50))
    rules1 = [MinCartValueRule(Decimal(100))]
    
    coupon1 = service.create_coupon(
        admin_id, "SAVE20", "Save 20%", discount1, rules1
    )
    coupon1.set_description("Get 20% off on orders above $100")
    coupon1.set_overall_usage_limit(100)
    coupon1.set_per_user_limit(2)
    coupon1.set_validity_period(
        datetime.now(),
        datetime.now() + timedelta(days=30)
    )
    
    # Coupon 2: $25 off, age > 18, specific category
    discount2 = Discount(DiscountType.FIXED_AMOUNT, Decimal(25))
    rules2 = [
        AgeRule(min_age=18),
        CategoryRule({"electronics", "gadgets"})
    ]
    
    coupon2 = service.create_coupon(
        admin_id, "ADULT25", "Adult Discount", discount2, rules2
    )
    coupon2.set_description("$25 off for adults on electronics")
    coupon2.set_per_user_limit(1)
    
    # Coupon 3: First order discount
    discount3 = Discount(DiscountType.PERCENTAGE, Decimal(15))
    rules3 = [FirstOrderRule(), MinCartValueRule(Decimal(50))]
    
    coupon3 = service.create_coupon(
        admin_id, "FIRST15", "First Order", discount3, rules3
    )
    coupon3.set_description("15% off on your first order")
    
    # Coupon 4: Location-based
    discount4 = Discount(DiscountType.FIXED_AMOUNT, Decimal(10))
    rules4 = [LocationRule({"NY", "CA"})]
    
    coupon4 = service.create_coupon(
        admin_id, "LOCAL10", "Local Discount", discount4, rules4
    )
    coupon4.set_description("$10 off for NY and CA residents")
    
    print(f"\n✅ Created {len(service._coupons)} coupons")
    
    # ==================== Create Vouchers ====================
    print_section("3. Admin: Create Vouchers")
    
    # Unassigned vouchers
    voucher_discount = Discount(DiscountType.FIXED_AMOUNT, Decimal(30))
    unassigned_vouchers = service.create_bulk_vouchers(
        admin_id, 5, VoucherType.UNASSIGNED, voucher_discount, "GIFT"
    )
    
    for voucher in unassigned_vouchers:
        voucher.set_expiry_date(datetime.now() + timedelta(days=60))
        voucher.set_description("$30 gift voucher")
    
    # Pre-assigned vouchers
    special_discount = Discount(DiscountType.PERCENTAGE, Decimal(30))
    alice_voucher = service.create_voucher(
        admin_id, "ALICE30", VoucherType.PRE_ASSIGNED,
        special_discount, alice.get_id()
    )
    alice_voucher.set_description("Special 30% off voucher for Alice")
    alice_voucher.set_expiry_date(datetime.now() + timedelta(days=90))
    
    print(f"✅ Total vouchers created: {len(service._vouchers)}")
    
    # ==================== User: View Available Coupons ====================
    print_section("4. User: View Available Coupons")
    
    print(f"\n🔍 Alice's available coupons:")
    alice_coupons = service.get_available_coupons(alice.get_id())
    for coupon_data in alice_coupons:
        print(f"   • {coupon_data['code']}: {coupon_data['name']}")
        print(f"     {coupon_data['description']}")
        print(f"     Discount: {coupon_data['discount']['type']} - {coupon_data['discount']['value']}")
    
    print(f"\n🔍 Bob's available coupons:")
    bob_coupons = service.get_available_coupons(bob.get_id())
    for coupon_data in bob_coupons:
        print(f"   • {coupon_data['code']}: {coupon_data['name']}")
    
    # ==================== User: View Vouchers ====================
    print_section("5. User: View Vouchers")
    
    print(f"\n🎫 Alice's assigned vouchers:")
    alice_vouchers = service.get_user_vouchers(alice.get_id())
    for voucher_data in alice_vouchers:
        print(f"   • {voucher_data['code']}: {voucher_data['description']}")
    
    print(f"\n🎫 Available unassigned vouchers:")
    unassigned = service.get_all_unassigned_vouchers(alice.get_id())
    for voucher_data in unassigned[:3]:  # Show first 3
        print(f"   • {voucher_data['code']}: {voucher_data['description']}")
    
    # ==================== Apply Coupons ====================
    print_section("6. User: Apply Coupons")
    
    # Alice applies SAVE20 (should work)
    context = {
        'cart_value': Decimal(150),
        'categories': ['electronics'],
        'product_ids': ['P1', 'P2']
    }
    
    success, discount, error = service.apply_coupon(
        alice.get_id(), "SAVE20", context, "ORDER001"
    )
    
    if success:
        final_amount = context['cart_value'] - discount
        print(f"   Cart: ${context['cart_value']}, Discount: ${discount}, Final: ${final_amount}")
    
    # Bob applies ADULT25 (should fail - age < 18)
    context2 = {
        'cart_value': Decimal(200),
        'categories': ['electronics']
    }
    
    success, discount, error = service.apply_coupon(
        bob.get_id(), "ADULT25", context2, "ORDER002"
    )
    
    if not success:
        print(f"   Bob's attempt failed: {error}")
    
    # Alice applies ADULT25 (should work)
    success, discount, error = service.apply_coupon(
        alice.get_id(), "ADULT25", context2, "ORDER003"
    )
    
    # Charlie applies FIRST15 (first order)
    context3 = {
        'cart_value': Decimal(100),
        'categories': ['fashion']
    }
    
    success, discount, error = service.apply_coupon(
        charlie.get_id(), "FIRST15", context3, "ORDER004"
    )
    
    if success:
        charlie.mark_order_placed()
        print(f"   Charlie's first order discount: ${discount}")
    
    # ==================== Apply Vouchers ====================
    print_section("7. User: Apply Vouchers")
    
    # Alice uses her pre-assigned voucher
    success, discount, error = service.apply_voucher(
        alice.get_id(), "ALICE30", Decimal(200), "ORDER005"
    )
    
    if success:
        print(f"   Alice used voucher: ${discount} off")
    
    # Bob tries unassigned voucher
    success, discount, error = service.apply_voucher(
        bob.get_id(), "GIFT00001", Decimal(100), "ORDER006"
    )
    
    if success:
        print(f"   Bob used unassigned voucher: ${discount} off")
    
    # Charlie tries same voucher (should fail - already used)
    success, discount, error = service.apply_voucher(
        charlie.get_id(), "GIFT00001", Decimal(150), "ORDER007"
    )
    
    if not success:
        print(f"   Charlie's attempt failed: {error}")
    
    # ==================== Per-User Limit Test ====================
    print_section("8. Per-User Limit Test")
    
    # Alice already used SAVE20 once, can use one more time
    context4 = {
        'cart_value': Decimal(120),
        'categories': ['books']
    }
    
    success, discount, error = service.apply_coupon(
        alice.get_id(), "SAVE20", context4, "ORDER008"
    )
    
    if success:
        print(f"   Alice's 2nd use of SAVE20: ${discount} off")
    
    # Try 3rd time (should fail)
    success, discount, error = service.apply_coupon(
        alice.get_id(), "SAVE20", context4, "ORDER009"
    )
    
    if not success:
        print(f"   Alice's 3rd attempt failed: {error}")
    
    # ==================== Admin: Deactivate Coupon ====================
    print_section("9. Admin: Deactivate Coupon")
    
    service.deactivate_coupon(admin_id, coupon4.get_id())
    
    # Try to use deactivated coupon
    context5 = {'cart_value': Decimal(50)}
    success, discount, error = service.apply_coupon(
        alice.get_id(), "LOCAL10", context5, "ORDER010"
    )
    
    if not success:
        print(f"   ❌ {error}")
    
    # Reactivate
    service.activate_coupon(admin_id, coupon4.get_id())
    print(f"   ✅ Coupon reactivated")
    
    # ==================== Admin: Cancel Voucher ====================
    print_section("10. Admin: Cancel Voucher")
    
    service.cancel_voucher(admin_id, unassigned_vouchers[1].get_id())
    
    # ==================== Statistics ====================
    print_section("11. Coupon Statistics")
    
    stats = service.get_coupon_statistics(coupon1.get_id())
    if stats:
        print(f"\n📊 Coupon: {stats['code']}")
        print(f"   Status: {stats['status']}")
        print(f"   Usage: {stats['overall_usage']}/{stats['overall_limit']}")
        print(f"   Unique Users: {stats['unique_users']}")
        print(f"   Per User Limit: {stats['per_user_limit']}")
    
    # ==================== Usage Logs ====================
    print_section("12. Usage Logs")
    
    print(f"\n📋 Alice's usage history:")
    alice_logs = service.get_usage_logs(user_id=alice.get_id())
    for log in alice_logs:
        print(f"   • {log['code']}: {log['status']} - "
              f"Discount: ${log['discount_amount'] or 'N/A'}")
        if log['error_message']:
            print(f"     Error: {log['error_message']}")
    
    print(f"\n📋 SAVE20 usage logs:")
    save20_logs = service.get_usage_logs(code="SAVE20")
    for log in save20_logs:
        print(f"   • User: {log['user_id']}, Status: {log['status']}, "
              f"Discount: ${log['discount_amount'] or 'N/A'}")
    
    # ==================== Summary ====================
    print_section("13. System Summary")
    
    print(f"\n📈 System Statistics:")
    print(f"   Total Coupons: {len(service._coupons)}")
    print(f"   Active Coupons: {sum(1 for c in service._coupons.values() if c.get_status() == CouponStatus.ACTIVE)}")
    print(f"   Total Vouchers: {len(service._vouchers)}")
    print(f"   Used Vouchers: {sum(1 for v in service._vouchers.values() if v.get_status() == VoucherStatus.USED)}")
    print(f"   Total Users: {len(service._users)}")
    print(f"   Total Usage Logs: {len(service._usage_logs)}")
    
    print(f"\n📋 Coupon Details:")
    for coupon in service._coupons.values():
        print(f"   • {coupon.get_code()}: {coupon.get_status().value}")
        print(f"     Rules: {len(coupon.get_rules())}")
        for rule in coupon.get_rules():
            print(f"       - {rule.get_description()}")
    
    print_section("Demo Complete")
    print("\n✅ Voucher Management System demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_voucher_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Voucher & Coupon Management System - Low Level Design
# Here's a comprehensive voucher and coupon management system:

# Key Design Decisions:
# 1. Core Components:
# Coupon: Reusable discount with rules and limits
# Voucher: Single-use or pre-assigned discount
# Rule System: Flexible eligibility rules
# Discount: Different discount types
# UsageLog: Audit trail
# 2. Coupon Features:
# ✅ Status: Active, Inactive, Expired, Exhausted ✅ Usage Limits: Overall limit + Per-user limit ✅ Validity Period: Start date and end date ✅ Eligibility Rules: Age, cart value, category, location, etc. ✅ Discount Types: Percentage, Fixed amount, Free shipping

# 3. Voucher Features:
# ✅ Types: Unassigned (anyone, single use) & Pre-assigned (specific user) ✅ Single Use: Once used, status changes to USED ✅ Expiry: Date-based expiration ✅ Assignment: Pre-assigned to specific users

# 4. Rule System:
# 5. Admin APIs:
# create_coupon() - Create with rules
# update_coupon() - Update limits, dates
# activate_coupon() / deactivate_coupon() - Control status
# delete_coupon() - Remove coupon
# create_voucher() - Create single voucher
# create_bulk_vouchers() - Create multiple
# assign_voucher_to_user() - Pre-assign
# cancel_voucher() - Cancel voucher
# 6. User APIs:
# get_available_coupons() - List usable coupons
# get_user_vouchers() - Pre-assigned vouchers
# get_all_unassigned_vouchers() - Available unassigned
# apply_coupon() - Apply with validation
# apply_voucher() - Use voucher
# 7. Validation Flow:
# 8. Rule Evaluation:
# Context-based evaluation
# All rules must pass (AND logic)
# Flexible rule composition
# Clear error messages
# 9. Usage Tracking:
# Overall usage count
# Per-user usage count
# Complete audit logs
# Success/failure tracking
# 10. Design Patterns:
# Strategy Pattern: Different discount types
# Rule Pattern: Composable eligibility rules
# Template Method: Base Rule class
# Factory-like: Coupon/Voucher creation
# Singleton-like: Service class
# 11. Key Differences:
# Coupons vs Vouchers:

# 12. Thread Safety:
# RLock for concurrent access
# Atomic operations
# Safe counter updates
# This is a production-grade voucher/coupon system like Amazon, Uber, or Swiggy! 🎫💳
