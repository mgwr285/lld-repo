from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from dataclasses import dataclass
import uuid


# ==================== Enums ====================

class LoyaltyTier(Enum):
    """Loyalty tier levels"""
    SILVER = 1
    GOLD = 2
    PLATINUM = 3
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


class TransactionType(Enum):
    """Transaction types in points wallet"""
    EARN = "earn"
    REDEEM = "redeem"
    BONUS = "bonus"
    REFUND = "refund"
    EXPIRY = "expiry"
    ADJUSTMENT = "adjustment"


class RewardType(Enum):
    """Types of rewards"""
    DISCOUNT_VOUCHER = "discount_voucher"
    FREE_DELIVERY = "free_delivery"
    CASHBACK = "cashback"
    PRODUCT_VOUCHER = "product_voucher"
    TIER_UPGRADE = "tier_upgrade"


class BenefitType(Enum):
    """Types of tier benefits"""
    POINTS_MULTIPLIER = "points_multiplier"
    FREE_DELIVERIES = "free_deliveries"
    EXCLUSIVE_DEALS = "exclusive_deals"
    PRIORITY_SUPPORT = "priority_support"
    BIRTHDAY_BONUS = "birthday_bonus"
    EXTENDED_RETURN = "extended_return"


class ItemCategory(Enum):
    """Product categories"""
    FRESH_PRODUCE = "fresh_produce"
    DAIRY = "dairy"
    MEAT_SEAFOOD = "meat_seafood"
    BAKERY = "bakery"
    PANTRY = "pantry"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    HOUSEHOLD = "household"


# ==================== Models ====================

@dataclass
class PurchaseItem:
    """Item in a purchase"""
    product_id: str
    name: str
    category: ItemCategory
    price: Decimal
    quantity: int
    
    def get_total(self) -> Decimal:
        return self.price * self.quantity


class Purchase:
    """Customer purchase"""
    
    def __init__(self, purchase_id: str, customer_id: str, items: List[PurchaseItem],
                 purchase_date: datetime):
        self._purchase_id = purchase_id
        self._customer_id = customer_id
        self._items = items
        self._purchase_date = purchase_date
        self._total_amount = sum(item.get_total() for item in items)
    
    def get_id(self) -> str:
        return self._purchase_id
    
    def get_customer_id(self) -> str:
        return self._customer_id
    
    def get_items(self) -> List[PurchaseItem]:
        return self._items
    
    def get_total_amount(self) -> Decimal:
        return self._total_amount
    
    def get_purchase_date(self) -> datetime:
        return self._purchase_date
    
    def get_items_by_category(self, category: ItemCategory) -> List[PurchaseItem]:
        return [item for item in self._items if item.category == category]


class PointsTransaction:
    """Transaction in points wallet"""
    
    def __init__(self, transaction_id: str, customer_id: str, 
                 transaction_type: TransactionType, points: int,
                 description: str, reference_id: Optional[str] = None):
        self._transaction_id = transaction_id
        self._customer_id = customer_id
        self._transaction_type = transaction_type
        self._points = points
        self._description = description
        self._reference_id = reference_id  # Purchase ID, Redemption ID, etc.
        self._timestamp = datetime.now()
        self._expiry_date: Optional[datetime] = None
    
    def get_id(self) -> str:
        return self._transaction_id
    
    def get_type(self) -> TransactionType:
        return self._transaction_type
    
    def get_points(self) -> int:
        return self._points
    
    def get_timestamp(self) -> datetime:
        return self._timestamp
    
    def get_description(self) -> str:
        return self._description
    
    def set_expiry_date(self, expiry_date: datetime) -> None:
        self._expiry_date = expiry_date
    
    def get_expiry_date(self) -> Optional[datetime]:
        return self._expiry_date
    
    def is_expired(self) -> bool:
        if self._expiry_date:
            return datetime.now() > self._expiry_date
        return False
    
    def to_dict(self) -> Dict:
        return {
            'transaction_id': self._transaction_id,
            'type': self._transaction_type.value,
            'points': self._points,
            'description': self._description,
            'timestamp': self._timestamp.isoformat(),
            'expiry_date': self._expiry_date.isoformat() if self._expiry_date else None
        }


class PointsWallet:
    """Customer's points wallet"""
    
    def __init__(self, customer_id: str):
        self._customer_id = customer_id
        self._balance = 0
        self._lifetime_points_earned = 0
        self._lifetime_points_redeemed = 0
        self._transactions: List[PointsTransaction] = []
        self._pending_expiry: List[PointsTransaction] = []  # Points about to expire
    
    def get_balance(self) -> int:
        return self._balance
    
    def get_lifetime_earned(self) -> int:
        return self._lifetime_points_earned
    
    def get_lifetime_redeemed(self) -> int:
        return self._lifetime_points_redeemed
    
    def add_points(self, points: int, description: str, 
                   reference_id: Optional[str] = None,
                   expiry_days: Optional[int] = None) -> PointsTransaction:
        """Add points to wallet"""
        transaction = PointsTransaction(
            str(uuid.uuid4()),
            self._customer_id,
            TransactionType.EARN,
            points,
            description,
            reference_id
        )
        
        # Set expiry if specified
        if expiry_days:
            expiry_date = datetime.now() + timedelta(days=expiry_days)
            transaction.set_expiry_date(expiry_date)
            self._pending_expiry.append(transaction)
        
        self._balance += points
        self._lifetime_points_earned += points
        self._transactions.append(transaction)
        
        return transaction
    
    def redeem_points(self, points: int, description: str,
                     reference_id: Optional[str] = None) -> Optional[PointsTransaction]:
        """Redeem points from wallet"""
        if points > self._balance:
            return None
        
        transaction = PointsTransaction(
            str(uuid.uuid4()),
            self._customer_id,
            TransactionType.REDEEM,
            -points,  # Negative for redemption
            description,
            reference_id
        )
        
        self._balance -= points
        self._lifetime_points_redeemed += points
        self._transactions.append(transaction)
        
        return transaction
    
    def add_bonus(self, points: int, description: str) -> PointsTransaction:
        """Add bonus points"""
        transaction = PointsTransaction(
            str(uuid.uuid4()),
            self._customer_id,
            TransactionType.BONUS,
            points,
            description
        )
        
        self._balance += points
        self._lifetime_points_earned += points
        self._transactions.append(transaction)
        
        return transaction
    
    def expire_points(self) -> int:
        """Expire old points and return count of expired points"""
        now = datetime.now()
        expired_points = 0
        
        expired_transactions = [t for t in self._pending_expiry if t.is_expired()]
        
        for transaction in expired_transactions:
            points = transaction.get_points()
            
            # Create expiry transaction
            expiry_transaction = PointsTransaction(
                str(uuid.uuid4()),
                self._customer_id,
                TransactionType.EXPIRY,
                -points,
                f"Points expired from {transaction.get_description()}",
                transaction.get_id()
            )
            
            self._balance -= points
            expired_points += points
            self._transactions.append(expiry_transaction)
            
            # Remove from pending
            self._pending_expiry.remove(transaction)
        
        return expired_points
    
    def get_expiring_soon(self, days: int = 30) -> List[PointsTransaction]:
        """Get points expiring within specified days"""
        cutoff_date = datetime.now() + timedelta(days=days)
        
        return [
            t for t in self._pending_expiry 
            if t.get_expiry_date() and t.get_expiry_date() <= cutoff_date
        ]
    
    def get_transaction_history(self, limit: Optional[int] = None) -> List[PointsTransaction]:
        """Get transaction history"""
        transactions = sorted(self._transactions, 
                            key=lambda t: t.get_timestamp(), 
                            reverse=True)
        
        if limit:
            return transactions[:limit]
        return transactions
    
    def get_summary(self) -> Dict:
        """Get wallet summary"""
        return {
            'balance': self._balance,
            'lifetime_earned': self._lifetime_points_earned,
            'lifetime_redeemed': self._lifetime_points_redeemed,
            'pending_expiry': sum(t.get_points() for t in self._pending_expiry),
            'total_transactions': len(self._transactions)
        }


# ==================== Tier Benefits ====================

class TierBenefit:
    """Benefit associated with a tier"""
    
    def __init__(self, benefit_type: BenefitType, value: Any, description: str):
        self._benefit_type = benefit_type
        self._value = value
        self._description = description
    
    def get_type(self) -> BenefitType:
        return self._benefit_type
    
    def get_value(self) -> Any:
        return self._value
    
    def get_description(self) -> str:
        return self._description
    
    def to_dict(self) -> Dict:
        return {
            'type': self._benefit_type.value,
            'value': self._value,
            'description': self._description
        }


class TierConfiguration:
    """Configuration for a loyalty tier"""
    
    def __init__(self, tier: LoyaltyTier, min_points: int, 
                 points_multiplier: Decimal = Decimal(1)):
        self._tier = tier
        self._min_points = min_points  # Minimum points to qualify
        self._points_multiplier = points_multiplier  # Earn rate multiplier
        self._benefits: List[TierBenefit] = []
        self._free_deliveries_per_month = 0
    
    def get_tier(self) -> LoyaltyTier:
        return self._tier
    
    def get_min_points(self) -> int:
        return self._min_points
    
    def get_points_multiplier(self) -> Decimal:
        return self._points_multiplier
    
    def add_benefit(self, benefit: TierBenefit) -> None:
        self._benefits.append(benefit)
    
    def get_benefits(self) -> List[TierBenefit]:
        return self._benefits
    
    def set_free_deliveries(self, count: int) -> None:
        self._free_deliveries_per_month = count
    
    def get_free_deliveries(self) -> int:
        return self._free_deliveries_per_month
    
    def to_dict(self) -> Dict:
        return {
            'tier': self._tier.name,
            'min_points': self._min_points,
            'points_multiplier': float(self._points_multiplier),
            'benefits': [b.to_dict() for b in self._benefits],
            'free_deliveries_per_month': self._free_deliveries_per_month
        }


# ==================== Rewards ====================

class Reward:
    """Redeemable reward"""
    
    def __init__(self, reward_id: str, name: str, reward_type: RewardType,
                 points_cost: int, value: Decimal, description: str = ""):
        self._reward_id = reward_id
        self._name = name
        self._reward_type = reward_type
        self._points_cost = points_cost
        self._value = value  # Monetary value
        self._description = description
        self._min_tier: Optional[LoyaltyTier] = None
        self._available = True
        self._stock: Optional[int] = None  # None = unlimited
        self._valid_until: Optional[datetime] = None
    
    def get_id(self) -> str:
        return self._reward_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_type(self) -> RewardType:
        return self._reward_type
    
    def get_points_cost(self) -> int:
        return self._points_cost
    
    def get_value(self) -> Decimal:
        return self._value
    
    def set_min_tier(self, tier: LoyaltyTier) -> None:
        self._min_tier = tier
    
    def get_min_tier(self) -> Optional[LoyaltyTier]:
        return self._min_tier
    
    def is_available(self) -> bool:
        if not self._available:
            return False
        
        if self._stock is not None and self._stock <= 0:
            return False
        
        if self._valid_until and datetime.now() > self._valid_until:
            return False
        
        return True
    
    def set_stock(self, stock: int) -> None:
        self._stock = stock
    
    def decrement_stock(self) -> bool:
        """Decrement stock, return False if out of stock"""
        if self._stock is None:
            return True
        
        if self._stock > 0:
            self._stock -= 1
            return True
        
        return False
    
    def can_redeem(self, customer_tier: LoyaltyTier, points_available: int) -> tuple[bool, Optional[str]]:
        """Check if customer can redeem this reward"""
        if not self.is_available():
            return False, "Reward not available"
        
        if self._min_tier and customer_tier < self._min_tier:
            return False, f"Requires {self._min_tier.name} tier or higher"
        
        if points_available < self._points_cost:
            return False, f"Insufficient points (need {self._points_cost})"
        
        return True, None
    
    def to_dict(self) -> Dict:
        return {
            'reward_id': self._reward_id,
            'name': self._name,
            'type': self._reward_type.value,
            'points_cost': self._points_cost,
            'value': float(self._value),
            'description': self._description,
            'min_tier': self._min_tier.name if self._min_tier else None,
            'available': self.is_available(),
            'stock': self._stock
        }


class Redemption:
    """Record of reward redemption"""
    
    def __init__(self, redemption_id: str, customer_id: str, reward: Reward):
        self._redemption_id = redemption_id
        self._customer_id = customer_id
        self._reward = reward
        self._redeemed_at = datetime.now()
        self._used = False
        self._used_at: Optional[datetime] = None
        self._expires_at: Optional[datetime] = None
        
        # Set default expiry (30 days)
        self._expires_at = datetime.now() + timedelta(days=30)
    
    def get_id(self) -> str:
        return self._redemption_id
    
    def get_reward(self) -> Reward:
        return self._reward
    
    def is_used(self) -> bool:
        return self._used
    
    def is_expired(self) -> bool:
        if self._expires_at:
            return datetime.now() > self._expires_at
        return False
    
    def use(self) -> bool:
        """Mark redemption as used"""
        if self._used or self.is_expired():
            return False
        
        self._used = True
        self._used_at = datetime.now()
        return True
    
    def to_dict(self) -> Dict:
        return {
            'redemption_id': self._redemption_id,
            'reward': self._reward.to_dict(),
            'redeemed_at': self._redeemed_at.isoformat(),
            'used': self._used,
            'used_at': self._used_at.isoformat() if self._used_at else None,
            'expires_at': self._expires_at.isoformat() if self._expires_at else None,
            'expired': self.is_expired()
        }


# ==================== Customer ====================

class LoyaltyCustomer:
    """Customer in loyalty program"""
    
    def __init__(self, customer_id: str, name: str, email: str,
                 phone: str, date_of_birth: Optional[date] = None):
        self._customer_id = customer_id
        self._name = name
        self._email = email
        self._phone = phone
        self._date_of_birth = date_of_birth
        
        # Loyalty details
        self._current_tier = LoyaltyTier.SILVER
        self._enrollment_date = datetime.now()
        self._wallet = PointsWallet(customer_id)
        
        # Tier tracking
        self._tier_history: List[Dict] = []
        self._last_tier_evaluation: Optional[datetime] = None
        
        # Usage tracking
        self._free_deliveries_used_this_month = 0
        self._last_delivery_reset: Optional[datetime] = None
        
        # Redemptions
        self._redemptions: List[Redemption] = []
    
    def get_id(self) -> str:
        return self._customer_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_current_tier(self) -> LoyaltyTier:
        return self._current_tier
    
    def upgrade_tier(self, new_tier: LoyaltyTier, reason: str = "") -> None:
        """Upgrade customer tier"""
        if new_tier > self._current_tier:
            self._tier_history.append({
                'from_tier': self._current_tier.name,
                'to_tier': new_tier.name,
                'timestamp': datetime.now().isoformat(),
                'reason': reason
            })
            self._current_tier = new_tier
            self._last_tier_evaluation = datetime.now()
    
    def get_wallet(self) -> PointsWallet:
        return self._wallet
    
    def get_date_of_birth(self) -> Optional[date]:
        return self._date_of_birth
    
    def is_birthday_month(self) -> bool:
        """Check if current month is customer's birthday month"""
        if self._date_of_birth:
            today = date.today()
            return today.month == self._date_of_birth.month
        return False
    
    def use_free_delivery(self) -> bool:
        """Use a free delivery"""
        # Reset counter if new month
        today = datetime.now()
        if (not self._last_delivery_reset or 
            self._last_delivery_reset.month != today.month):
            self._free_deliveries_used_this_month = 0
            self._last_delivery_reset = today
        
        self._free_deliveries_used_this_month += 1
        return True
    
    def get_free_deliveries_remaining(self, tier_config: TierConfiguration) -> int:
        """Get remaining free deliveries for this month"""
        today = datetime.now()
        if (not self._last_delivery_reset or 
            self._last_delivery_reset.month != today.month):
            return tier_config.get_free_deliveries()
        
        return max(0, tier_config.get_free_deliveries() - self._free_deliveries_used_this_month)
    
    def add_redemption(self, redemption: Redemption) -> None:
        self._redemptions.append(redemption)
    
    def get_redemptions(self, active_only: bool = False) -> List[Redemption]:
        """Get redemptions"""
        if active_only:
            return [r for r in self._redemptions if not r.is_used() and not r.is_expired()]
        return self._redemptions
    
    def get_summary(self) -> Dict:
        """Get customer summary"""
        return {
            'customer_id': self._customer_id,
            'name': self._name,
            'email': self._email,
            'tier': self._current_tier.name,
            'enrollment_date': self._enrollment_date.isoformat(),
            'wallet': self._wallet.get_summary(),
            'tier_upgrades': len(self._tier_history),
            'total_redemptions': len(self._redemptions),
            'active_redemptions': len(self.get_redemptions(active_only=True))
        }


# ==================== Loyalty Program ====================

class AmazonFreshLoyaltyProgram:
    """
    Main loyalty program system
    
    Features:
    - Tier-based benefits (Silver, Gold, Platinum)
    - Points wallet with expiry
    - Purchase-based point earning
    - Reward redemption system
    - Automatic tier upgrades
    - Birthday bonuses
    - Category multipliers
    """
    
    def __init__(self, program_name: str = "Amazon Fresh Rewards"):
        self._program_name = program_name
        
        # Customers
        self._customers: Dict[str, LoyaltyCustomer] = {}
        
        # Tier configurations
        self._tier_configs: Dict[LoyaltyTier, TierConfiguration] = {}
        
        # Rewards catalog
        self._rewards: Dict[str, Reward] = {}
        
        # Points earning rules
        self._base_points_per_dollar = Decimal(1)  # 1 point per $1
        self._category_multipliers: Dict[ItemCategory, Decimal] = {}
        self._points_expiry_days = 365  # Points expire after 1 year
        
        # Initialize default tier configurations
        self._initialize_tiers()
    
    def _initialize_tiers(self) -> None:
        """Initialize default tier configurations"""
        # Silver Tier (Entry level)
        silver = TierConfiguration(LoyaltyTier.SILVER, 0, Decimal(1))
        silver.add_benefit(TierBenefit(
            BenefitType.POINTS_MULTIPLIER, 
            "1x", 
            "Earn 1 point per dollar"
        ))
        silver.set_free_deliveries(2)
        self._tier_configs[LoyaltyTier.SILVER] = silver
        
        # Gold Tier
        gold = TierConfiguration(LoyaltyTier.GOLD, 5000, Decimal(1.5))
        gold.add_benefit(TierBenefit(
            BenefitType.POINTS_MULTIPLIER, 
            "1.5x", 
            "Earn 1.5 points per dollar"
        ))
        gold.add_benefit(TierBenefit(
            BenefitType.BIRTHDAY_BONUS,
            500,
            "500 bonus points on birthday month"
        ))
        gold.set_free_deliveries(5)
        self._tier_configs[LoyaltyTier.GOLD] = gold
        
        # Platinum Tier
        platinum = TierConfiguration(LoyaltyTier.PLATINUM, 15000, Decimal(2))
        platinum.add_benefit(TierBenefit(
            BenefitType.POINTS_MULTIPLIER, 
            "2x", 
            "Earn 2 points per dollar"
        ))
        platinum.add_benefit(TierBenefit(
            BenefitType.BIRTHDAY_BONUS,
            1000,
            "1000 bonus points on birthday month"
        ))
        platinum.add_benefit(TierBenefit(
            BenefitType.EXTENDED_RETURN,
            60,
            "60 days return window"
        ))
        platinum.add_benefit(TierBenefit(
            BenefitType.PRIORITY_SUPPORT,
            True,
            "Priority customer support"
        ))
        platinum.set_free_deliveries(10)
        self._tier_configs[LoyaltyTier.PLATINUM] = platinum
    
    def enroll_customer(self, name: str, email: str, phone: str,
                       date_of_birth: Optional[date] = None) -> LoyaltyCustomer:
        """Enroll a new customer"""
        customer_id = str(uuid.uuid4())
        customer = LoyaltyCustomer(customer_id, name, email, phone, date_of_birth)
        
        self._customers[customer_id] = customer
        
        # Welcome bonus
        customer.get_wallet().add_bonus(100, "Welcome bonus")
        
        print(f"✅ Customer enrolled: {name} - Welcome bonus: 100 points")
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[LoyaltyCustomer]:
        return self._customers.get(customer_id)
    
    def set_category_multiplier(self, category: ItemCategory, multiplier: Decimal) -> None:
        """Set points multiplier for specific category"""
        self._category_multipliers[category] = multiplier
    
    def calculate_points(self, purchase: Purchase, customer: LoyaltyCustomer) -> int:
        """Calculate points earned from purchase"""
        tier_config = self._tier_configs[customer.get_current_tier()]
        tier_multiplier = tier_config.get_points_multiplier()
        
        total_points = 0
        
        for item in purchase.get_items():
            # Base points
            item_total = item.get_total()
            base_points = int(item_total * self._base_points_per_dollar)
            
            # Apply tier multiplier
            points = int(base_points * tier_multiplier)
            
            # Apply category multiplier if exists
            if item.category in self._category_multipliers:
                category_mult = self._category_multipliers[item.category]
                points = int(points * category_mult)
            
            total_points += points
        
        return total_points
    
    def process_purchase(self, customer_id: str, purchase: Purchase) -> Optional[int]:
        """Process a purchase and award points"""
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        
        # Calculate points
        points_earned = self.calculate_points(purchase, customer)
        
        # Add to wallet
        transaction = customer.get_wallet().add_points(
            points_earned,
            f"Purchase #{purchase.get_id()}",
            purchase.get_id(),
            self._points_expiry_days
        )
        
        print(f"💰 {customer.get_name()} earned {points_earned} points "
              f"from ${purchase.get_total_amount()} purchase")
        
        # Check for tier upgrade
        self._evaluate_tier_upgrade(customer)
        
        # Check for birthday bonus
        self._check_birthday_bonus(customer)
        
        return points_earned
    
    def _evaluate_tier_upgrade(self, customer: LoyaltyCustomer) -> None:
        """Evaluate if customer qualifies for tier upgrade"""
        lifetime_points = customer.get_wallet().get_lifetime_earned()
        current_tier = customer.get_current_tier()
        
        # Check each tier in descending order
        for tier in [LoyaltyTier.PLATINUM, LoyaltyTier.GOLD]:
            tier_config = self._tier_configs[tier]
            
            if lifetime_points >= tier_config.get_min_points() and tier > current_tier:
                customer.upgrade_tier(
                    tier,
                    f"Reached {tier_config.get_min_points()} lifetime points"
                )
                print(f"🎉 {customer.get_name()} upgraded to {tier.name} tier!")
                
                # Award tier upgrade bonus
                bonus_points = 500 if tier == LoyaltyTier.GOLD else 1000
                customer.get_wallet().add_bonus(
                    bonus_points,
                    f"{tier.name} tier upgrade bonus"
                )
                break
    
    def _check_birthday_bonus(self, customer: LoyaltyCustomer) -> None:
        """Check and award birthday bonus"""
        if not customer.is_birthday_month():
            return
        
        # Check if already awarded this month
        current_month = datetime.now().strftime("%Y-%m")
        recent_transactions = customer.get_wallet().get_transaction_history(limit=50)
        
        for transaction in recent_transactions:
            if (transaction.get_type() == TransactionType.BONUS and
                "birthday" in transaction.get_description().lower() and
                transaction.get_timestamp().strftime("%Y-%m") == current_month):
                return  # Already awarded
        
        # Award birthday bonus based on tier
        tier_config = self._tier_configs[customer.get_current_tier()]
        birthday_benefit = next(
            (b for b in tier_config.get_benefits() 
             if b.get_type() == BenefitType.BIRTHDAY_BONUS),
            None
        )
        
        if birthday_benefit:
            bonus_points = birthday_benefit.get_value()
            customer.get_wallet().add_bonus(
                bonus_points,
                "Happy Birthday bonus!"
            )
            print(f"🎂 Birthday bonus: {bonus_points} points for {customer.get_name()}")
    
    def add_reward(self, reward: Reward) -> None:
        """Add reward to catalog"""
        self._rewards[reward.get_id()] = reward
        print(f"✅ Reward added: {reward.get_name()} - {reward.get_points_cost()} points")
    
    def get_available_rewards(self, customer_id: str) -> List[Reward]:
        """Get rewards available to customer"""
        customer = self._customers.get(customer_id)
        if not customer:
            return []
        
        customer_tier = customer.get_current_tier()
        points_available = customer.get_wallet().get_balance()
        
        available = []
        for reward in self._rewards.values():
            can_redeem, _ = reward.can_redeem(customer_tier, points_available)
            if can_redeem:
                available.append(reward)
        
        return available
    
    def redeem_reward(self, customer_id: str, reward_id: str) -> Optional[Redemption]:
        """Redeem a reward"""
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        
        reward = self._rewards.get(reward_id)
        if not reward:
            return None
        
        # Check if can redeem
        can_redeem, error = reward.can_redeem(
            customer.get_current_tier(),
            customer.get_wallet().get_balance()
        )
        
        if not can_redeem:
            print(f"❌ Cannot redeem: {error}")
            return None
        
        # Deduct points
        transaction = customer.get_wallet().redeem_points(
            reward.get_points_cost(),
            f"Redeemed: {reward.get_name()}",
            reward_id
        )
        
        if not transaction:
            return None
        
        # Decrement stock
        if not reward.decrement_stock():
            print(f"❌ Reward out of stock")
            return None
        
        # Create redemption
        redemption = Redemption(str(uuid.uuid4()), customer_id, reward)
        customer.add_redemption(redemption)
        
        print(f"🎁 {customer.get_name()} redeemed {reward.get_name()} "
              f"for {reward.get_points_cost()} points")
        
        return redemption
    
    def get_tier_benefits(self, tier: LoyaltyTier) -> TierConfiguration:
        """Get benefits for a tier"""
        return self._tier_configs[tier]
    
    def get_customer_summary(self, customer_id: str) -> Optional[Dict]:
        """Get comprehensive customer summary"""
        customer = self._customers.get(customer_id)
        if not customer:
            return None
        
        tier_config = self._tier_configs[customer.get_current_tier()]
        wallet = customer.get_wallet()
        
        return {
            'customer': customer.get_summary(),
            'tier_benefits': tier_config.to_dict(),
            'free_deliveries_remaining': customer.get_free_deliveries_remaining(tier_config),
            'points_expiring_soon': [
                t.to_dict() for t in wallet.get_expiring_soon(30)
            ],
            'recent_transactions': [
                t.to_dict() for t in wallet.get_transaction_history(10)
            ],
            'active_rewards': [
                r.to_dict() for r in customer.get_redemptions(active_only=True)
            ]
        }
    
    def run_monthly_maintenance(self) -> Dict:
        """Run monthly maintenance tasks"""
        stats = {
            'customers_processed': 0,
            'points_expired': 0,
            'tier_upgrades': 0
        }
        
        for customer in self._customers.values():
            stats['customers_processed'] += 1
            
            # Expire old points
            expired = customer.get_wallet().expire_points()
            stats['points_expired'] += expired
            
            # Re-evaluate tiers
            old_tier = customer.get_current_tier()
            self._evaluate_tier_upgrade(customer)
            if customer.get_current_tier() != old_tier:
                stats['tier_upgrades'] += 1
        
        return stats


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_loyalty_program():
    """Comprehensive demo of loyalty program"""
    
    print_section("AMAZON FRESH LOYALTY PROGRAM DEMO")
    
    program = AmazonFreshLoyaltyProgram()
    
    # ==================== Setup Category Multipliers ====================
    print_section("1. Setup Category Multipliers")
    
    program.set_category_multiplier(ItemCategory.FRESH_PRODUCE, Decimal(1.5))
    program.set_category_multiplier(ItemCategory.DAIRY, Decimal(1.2))
    
    print("✅ Category multipliers configured:")
    print("   • Fresh Produce: 1.5x points")
    print("   • Dairy: 1.2x points")
    
    # ==================== Enroll Customers ====================
    print_section("2. Enroll Customers")
    
    alice = program.enroll_customer(
        "Alice Johnson",
        "alice@example.com",
        "+1-555-0101",
        date(1990, 3, 15)
    )
    
    bob = program.enroll_customer(
        "Bob Smith",
        "bob@example.com",
        "+1-555-0102",
        date(1985, 7, 22)
    )
    
    charlie = program.enroll_customer(
        "Charlie Brown",
        "charlie@example.com",
        "+1-555-0103"
    )
    
    # ==================== Add Rewards ====================
    print_section("3. Add Rewards to Catalog")
    
    rewards = [
        Reward("R001", "$5 Off Next Order", RewardType.DISCOUNT_VOUCHER, 
               500, Decimal(5), "Discount voucher for next purchase"),
        Reward("R002", "$10 Off Next Order", RewardType.DISCOUNT_VOUCHER, 
               1000, Decimal(10), "Discount voucher for next purchase"),
        Reward("R003", "Free Delivery", RewardType.FREE_DELIVERY, 
               200, Decimal(3.99), "Free delivery on next order"),
        Reward("R004", "$25 Cashback", RewardType.CASHBACK, 
               2500, Decimal(25), "Cashback to wallet"),
        Reward("R005", "$50 Off (Gold+)", RewardType.DISCOUNT_VOUCHER, 
               4000, Decimal(50), "Exclusive for Gold tier and above"),
    ]
    
    # Set tier requirements
    rewards[4].set_min_tier(LoyaltyTier.GOLD)
    
    for reward in rewards:
        program.add_reward(reward)
    
    # ==================== Process Purchases ====================
    print_section("4. Process Customer Purchases")
    
    # Alice's first purchase
    purchase1_items = [
        PurchaseItem("P001", "Organic Apples", ItemCategory.FRESH_PRODUCE, 
                     Decimal(4.99), 2),
        PurchaseItem("P002", "Whole Milk", ItemCategory.DAIRY, 
                     Decimal(3.99), 1),
        PurchaseItem("P003", "Fresh Bread", ItemCategory.BAKERY, 
                     Decimal(2.99), 1),
    ]
    purchase1 = Purchase("PUR001", alice.get_id(), purchase1_items, datetime.now())
    
    print(f"\n🛒 Alice's Purchase:")
    for item in purchase1.get_items():
        print(f"   • {item.name} ({item.category.value}): "
              f"${item.price} x {item.quantity} = ${item.get_total()}")
    print(f"   Total: ${purchase1.get_total_amount()}")
    
    points = program.process_purchase(alice.get_id(), purchase1)
    
    # Bob's large purchase
    purchase2_items = [
        PurchaseItem("P004", "Salmon Fillet", ItemCategory.MEAT_SEAFOOD, 
                     Decimal(15.99), 2),
        PurchaseItem("P005", "Greek Yogurt", ItemCategory.DAIRY, 
                     Decimal(5.99), 3),
        PurchaseItem("P006", "Mixed Salad", ItemCategory.FRESH_PRODUCE, 
                     Decimal(3.99), 2),
        PurchaseItem("P007", "Chicken Breast", ItemCategory.MEAT_SEAFOOD, 
                     Decimal(12.99), 2),
    ]
    purchase2 = Purchase("PUR002", bob.get_id(), purchase2_items, datetime.now())
    
    print(f"\n🛒 Bob's Purchase:")
    print(f"   Total: ${purchase2.get_total_amount()}")
    points = program.process_purchase(bob.get_id(), purchase2)
    
    # ==================== Simulate Multiple Purchases for Tier Upgrade ====================
    print_section("5. Simulate Purchases for Tier Upgrades")
    
    # Give Alice multiple large purchases
    for i in range(8):
        large_purchase_items = [
            PurchaseItem(f"P{100+i}", "Groceries", ItemCategory.PANTRY, 
                        Decimal(75), 1),
            PurchaseItem(f"P{200+i}", "Fresh Items", ItemCategory.FRESH_PRODUCE, 
                        Decimal(25), 1),
        ]
        purchase_date = datetime.now() - timedelta(days=30-i*3)
        large_purchase = Purchase(f"PUR{100+i}", alice.get_id(), 
                                 large_purchase_items, purchase_date)
        program.process_purchase(alice.get_id(), large_purchase)
    
    # Give Bob even more for Platinum
    for i in range(25):
        mega_purchase_items = [
            PurchaseItem(f"P{300+i}", "Weekly Shop", ItemCategory.PANTRY, 
                        Decimal(80), 1),
        ]
        purchase_date = datetime.now() - timedelta(days=60-i*2)
        mega_purchase = Purchase(f"PUR{200+i}", bob.get_id(), 
                               mega_purchase_items, purchase_date)
        program.process_purchase(bob.get_id(), mega_purchase)
    
    # ==================== Check Tier Status ====================
    print_section("6. Check Customer Tiers")
    
    for customer_id, name in [(alice.get_id(), "Alice"), 
                               (bob.get_id(), "Bob"), 
                               (charlie.get_id(), "Charlie")]:
        customer = program.get_customer(customer_id)
        wallet = customer.get_wallet()
        tier_config = program.get_tier_benefits(customer.get_current_tier())
        
        print(f"\n👤 {name}:")
        print(f"   Tier: {customer.get_current_tier().name}")
        print(f"   Points Balance: {wallet.get_balance()}")
        print(f"   Lifetime Earned: {wallet.get_lifetime_earned()}")
        print(f"   Points Multiplier: {tier_config.get_points_multiplier()}x")
        print(f"   Free Deliveries/Month: {tier_config.get_free_deliveries()}")
    
    # ==================== View Tier Benefits ====================
    print_section("7. Tier Benefits Details")
    
    for tier in [LoyaltyTier.SILVER, LoyaltyTier.GOLD, LoyaltyTier.PLATINUM]:
        config = program.get_tier_benefits(tier)
        print(f"\n🏆 {tier.name} Tier:")
        print(f"   Min Points Required: {config.get_min_points()}")
        print(f"   Points Multiplier: {config.get_points_multiplier()}x")
        print(f"   Free Deliveries: {config.get_free_deliveries()}/month")
        print(f"   Benefits:")
        for benefit in config.get_benefits():
            print(f"      • {benefit.get_description()}")
    
    # ==================== View Available Rewards ====================
    print_section("8. Available Rewards")
    
    print(f"\n🎁 Alice's Available Rewards ({alice.get_current_tier().name} tier, "
          f"{alice.get_wallet().get_balance()} points):")
    alice_rewards = program.get_available_rewards(alice.get_id())
    for reward in alice_rewards:
        print(f"   • {reward.get_name()}: {reward.get_points_cost()} points "
              f"(${reward.get_value()} value)")
    
    print(f"\n🎁 Bob's Available Rewards ({bob.get_current_tier().name} tier, "
          f"{bob.get_wallet().get_balance()} points):")
    bob_rewards = program.get_available_rewards(bob.get_id())
    for reward in bob_rewards:
        tier_req = f"({reward.get_min_tier().name}+)" if reward.get_min_tier() else ""
        print(f"   • {reward.get_name()}: {reward.get_points_cost()} points "
              f"(${reward.get_value()} value) {tier_req}")
    
    # ==================== Redeem Rewards ====================
    print_section("9. Redeem Rewards")
    
    # Alice redeems $5 off
    redemption1 = program.redeem_reward(alice.get_id(), "R001")
    
    # Bob redeems $50 off (Gold tier reward)
    redemption2 = program.redeem_reward(bob.get_id(), "R005")
    
    # Charlie tries to redeem Gold tier reward (should fail)
    print(f"\n🔴 Charlie (Silver tier) tries Gold tier reward:")
    redemption3 = program.redeem_reward(charlie.get_id(), "R005")
    
    # ==================== View Transaction History ====================
    print_section("10. Transaction History")
    
    print(f"\n📋 Alice's Recent Transactions:")
    alice_transactions = alice.get_wallet().get_transaction_history(10)
    for tx in alice_transactions[:5]:
        points_str = f"+{tx.get_points()}" if tx.get_points() > 0 else str(tx.get_points())
        print(f"   {tx.get_timestamp().strftime('%Y-%m-%d %H:%M')} | "
              f"{tx.get_type().value:12} | {points_str:6} pts | "
              f"{tx.get_description()}")
    
    # ==================== Check Points Expiry ====================
    print_section("11. Points Expiring Soon")
    
    expiring = alice.get_wallet().get_expiring_soon(30)
    if expiring:
        print(f"\n⚠️  Alice has {len(expiring)} point transactions expiring in 30 days:")
        for tx in expiring:
            print(f"   • {tx.get_points()} points expiring on "
                  f"{tx.get_expiry_date().strftime('%Y-%m-%d')}")
    else:
        print(f"\n✅ No points expiring soon for Alice")
    
    # ==================== Active Redemptions ====================
    print_section("12. Active Redemptions")
    
    print(f"\n🎟️  Alice's Active Redemptions:")
    alice_redemptions = alice.get_redemptions(active_only=True)
    for redemption in alice_redemptions:
        reward = redemption.get_reward()
        print(f"   • {reward.get_name()}: Expires {redemption._expires_at.strftime('%Y-%m-%d')}")
    
    print(f"\n🎟️  Bob's Active Redemptions:")
    bob_redemptions = bob.get_redemptions(active_only=True)
    for redemption in bob_redemptions:
        reward = redemption.get_reward()
        print(f"   • {reward.get_name()}: Expires {redemption._expires_at.strftime('%Y-%m-%d')}")
    
    # ==================== Comprehensive Customer Summary ====================
    print_section("13. Comprehensive Customer Summary")
    
    alice_summary = program.get_customer_summary(alice.get_id())
    
    print(f"\n👤 {alice.get_name()} - Complete Profile")
    print(f"\n📊 Loyalty Status:")
    print(f"   Current Tier: {alice_summary['customer']['tier']}")
    print(f"   Member Since: {alice_summary['customer']['enrollment_date'][:10]}")
    print(f"   Tier Upgrades: {alice_summary['customer']['tier_upgrades']}")
    
    print(f"\n💰 Points Wallet:")
    wallet_summary = alice_summary['customer']['wallet']
    print(f"   Balance: {wallet_summary['balance']} points")
    print(f"   Lifetime Earned: {wallet_summary['lifetime_earned']} points")
    print(f"   Lifetime Redeemed: {wallet_summary['lifetime_redeemed']} points")
    print(f"   Pending Expiry: {wallet_summary['pending_expiry']} points")
    
    print(f"\n🎁 Benefits & Redemptions:")
    print(f"   Free Deliveries Remaining: {alice_summary['free_deliveries_remaining']}")
    print(f"   Total Redemptions: {alice_summary['customer']['total_redemptions']}")
    print(f"   Active Rewards: {alice_summary['customer']['active_redemptions']}")
    
    # ==================== Monthly Maintenance ====================
    print_section("14. Monthly Maintenance")
    
    print("\n🔧 Running monthly maintenance...")
    stats = program.run_monthly_maintenance()
    
    print(f"\n📊 Maintenance Results:")
    print(f"   Customers Processed: {stats['customers_processed']}")
    print(f"   Points Expired: {stats['points_expired']}")
    print(f"   Tier Upgrades: {stats['tier_upgrades']}")
    
    # ==================== Program Statistics ====================
    print_section("15. Program Statistics")
    
    total_customers = len(program._customers)
    silver_count = sum(1 for c in program._customers.values() 
                      if c.get_current_tier() == LoyaltyTier.SILVER)
    gold_count = sum(1 for c in program._customers.values() 
                    if c.get_current_tier() == LoyaltyTier.GOLD)
    platinum_count = sum(1 for c in program._customers.values() 
                        if c.get_current_tier() == LoyaltyTier.PLATINUM)
    
    total_points_issued = sum(c.get_wallet().get_lifetime_earned() 
                             for c in program._customers.values())
    total_points_redeemed = sum(c.get_wallet().get_lifetime_redeemed() 
                               for c in program._customers.values())
    
    print(f"\n📊 Amazon Fresh Loyalty Program Statistics:")
    print(f"   Total Members: {total_customers}")
    print(f"   Tier Distribution:")
    print(f"      • Silver: {silver_count} ({silver_count/total_customers*100:.1f}%)")
    print(f"      • Gold: {gold_count} ({gold_count/total_customers*100:.1f}%)")
    print(f"      • Platinum: {platinum_count} ({platinum_count/total_customers*100:.1f}%)")
    print(f"\n   Points Economy:")
    print(f"      • Total Points Issued: {total_points_issued:,}")
    print(f"      • Total Points Redeemed: {total_points_redeemed:,}")
    print(f"      • Points Outstanding: {total_points_issued - total_points_redeemed:,}")
    print(f"      • Redemption Rate: {(total_points_redeemed/total_points_issued*100):.1f}%")
    
    print(f"\n   Rewards Catalog: {len(program._rewards)} rewards")
    
    print_section("Demo Complete")
    print("\n✅ Amazon Fresh Loyalty Program demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_loyalty_program()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Key Design Decisions:
# 1. Core Components:
# LoyaltyCustomer: Customer with tier and wallet
# PointsWallet: Manages points with expiry
# TierConfiguration: Benefits for each tier
# Reward: Redeemable items
# Purchase: Shopping transaction
# 2. Three-Tier System:
# Silver (Entry):

# 0 points minimum
# 1x points multiplier
# 2 free deliveries/month
# Gold:

# 5,000 points minimum
# 1.5x points multiplier
# 5 free deliveries/month
# 500 birthday bonus
# Platinum:

# 15,000 points minimum
# 2x points multiplier
# 10 free deliveries/month
# 1,000 birthday bonus
# Priority support
# Extended returns (60 days)
# 3. Points System:
# ✅ Earning: Base 1 point per $1 + tier multiplier ✅ Category Multipliers: Extra points for specific categories ✅ Expiry: Points expire after 365 days ✅ Tracking: Complete transaction history ✅ Wallet: Balance, lifetime earned, lifetime redeemed

# 4. Key Features:
# Automatic Tier Upgrades:

# Based on lifetime points earned
# Bonus points on upgrade
# Tier history tracking
# Birthday Bonuses:

# Automatic detection
# Tier-based bonus amount
# Once per year
# Reward Redemption:

# Tier restrictions
# Stock management
# Expiry dates
# Active redemptions tracking
# Points Expiry:

# Time-based expiration
# Expiring soon notifications
# Automatic cleanup
# 5. Design Patterns:
# Strategy Pattern: Different tier benefits
# Wallet Pattern: Points management
# Observer Pattern: Purchase triggers point award
# Factory Pattern: Creating rewards/customers
# State Pattern: Customer tier transitions
# 6. Extensibility:
# 7. Transaction Types:
# EARN: Purchase points
# REDEEM: Reward redemption
# BONUS: Welcome/birthday/upgrade bonuses
# REFUND: Returned purchases
# EXPIRY: Expired points
# ADJUSTMENT: Manual corrections
# 8. Benefits of Design:
# ✅ Scalable: Easy to add tiers/rewards ✅ Maintainable: Clear separation of concerns ✅ Testable: Independent components ✅ Flexible: Configurable rules ✅ Auditable: Complete transaction history

# This is a production-grade loyalty program like Starbucks Rewards or Amazon Prime! 🌟💳
