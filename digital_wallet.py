from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock
from collections import defaultdict
import uuid


# ==================== Enums ====================

class Currency(Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    JPY = "JPY"
    CAD = "CAD"


class PaymentMethodType(Enum):
    """Types of payment methods"""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    UPI = "UPI"


class TransactionType(Enum):
    """Types of transactions"""
    CREDIT = "CREDIT"  # Money received
    DEBIT = "DEBIT"    # Money sent
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    REFUND = "REFUND"
    PAYMENT = "PAYMENT"
    WITHDRAWAL = "WITHDRAWAL"
    DEPOSIT = "DEPOSIT"
    CURRENCY_EXCHANGE = "CURRENCY_EXCHANGE"


class TransactionStatus(Enum):
    """Status of a transaction"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REVERSED = "REVERSED"


class KYCStatus(Enum):
    """KYC verification status"""
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


# ==================== Payment Method (Strategy Pattern) ====================

class PaymentMethod(ABC):
    """Abstract base class for payment methods"""
    
    def __init__(self, method_id: str, method_type: PaymentMethodType, is_primary: bool = False):
        self._method_id = method_id
        self._method_type = method_type
        self._is_primary = is_primary
        self._is_active = True
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._method_id
    
    def get_type(self) -> PaymentMethodType:
        return self._method_type
    
    def is_primary(self) -> bool:
        return self._is_primary
    
    def set_primary(self, primary: bool) -> None:
        self._is_primary = primary
    
    def is_active(self) -> bool:
        return self._is_active
    
    def deactivate(self) -> None:
        self._is_active = False
    
    @abstractmethod
    def get_display_info(self) -> str:
        """Get display information for the payment method"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate the payment method"""
        pass


class CreditCard(PaymentMethod):
    """Credit card payment method"""
    
    def __init__(self, method_id: str, card_number: str, cardholder_name: str,
                 expiry_month: int, expiry_year: int, cvv: str, is_primary: bool = False):
        super().__init__(method_id, PaymentMethodType.CREDIT_CARD, is_primary)
        self._card_number = card_number  # In production, should be encrypted/tokenized
        self._cardholder_name = cardholder_name
        self._expiry_month = expiry_month
        self._expiry_year = expiry_year
        self._cvv = cvv  # Should never be stored in production
    
    def get_display_info(self) -> str:
        """Return masked card number"""
        masked = "**** **** **** " + self._card_number[-4:]
        return f"Credit Card ({masked})"
    
    def validate(self) -> bool:
        """Validate card details"""
        # Check expiry
        now = datetime.now()
        if self._expiry_year < now.year:
            return False
        if self._expiry_year == now.year and self._expiry_month < now.month:
            return False
        
        # Basic Luhn algorithm check
        return self._luhn_check(self._card_number)
    
    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Luhn algorithm for card validation"""
        digits = [int(d) for d in card_number if d.isdigit()]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0
    
    def __repr__(self) -> str:
        return f"CreditCard(id={self._method_id}, {self.get_display_info()})"


class DebitCard(PaymentMethod):
    """Debit card payment method"""
    
    def __init__(self, method_id: str, card_number: str, cardholder_name: str,
                 expiry_month: int, expiry_year: int, cvv: str, is_primary: bool = False):
        super().__init__(method_id, PaymentMethodType.DEBIT_CARD, is_primary)
        self._card_number = card_number
        self._cardholder_name = cardholder_name
        self._expiry_month = expiry_month
        self._expiry_year = expiry_year
        self._cvv = cvv
    
    def get_display_info(self) -> str:
        masked = "**** **** **** " + self._card_number[-4:]
        return f"Debit Card ({masked})"
    
    def validate(self) -> bool:
        now = datetime.now()
        if self._expiry_year < now.year:
            return False
        if self._expiry_year == now.year and self._expiry_month < now.month:
            return False
        return CreditCard._luhn_check(self._card_number)
    
    def __repr__(self) -> str:
        return f"DebitCard(id={self._method_id}, {self.get_display_info()})"


class BankAccount(PaymentMethod):
    """Bank account payment method"""
    
    def __init__(self, method_id: str, account_number: str, routing_number: str,
                 account_holder_name: str, bank_name: str, is_primary: bool = False):
        super().__init__(method_id, PaymentMethodType.BANK_ACCOUNT, is_primary)
        self._account_number = account_number
        self._routing_number = routing_number
        self._account_holder_name = account_holder_name
        self._bank_name = bank_name
    
    def get_display_info(self) -> str:
        masked = "****" + self._account_number[-4:]
        return f"{self._bank_name} Account ({masked})"
    
    def validate(self) -> bool:
        # Basic validation
        return len(self._account_number) >= 8 and len(self._routing_number) == 9
    
    def __repr__(self) -> str:
        return f"BankAccount(id={self._method_id}, {self._bank_name})"


class UPI(PaymentMethod):
    """UPI payment method"""
    
    def __init__(self, method_id: str, upi_id: str, is_primary: bool = False):
        super().__init__(method_id, PaymentMethodType.UPI, is_primary)
        self._upi_id = upi_id
    
    def get_display_info(self) -> str:
        return f"UPI ({self._upi_id})"
    
    def validate(self) -> bool:
        # UPI ID format: user@bank
        return '@' in self._upi_id and len(self._upi_id.split('@')) == 2
    
    def __repr__(self) -> str:
        return f"UPI(id={self._method_id}, {self._upi_id})"


# ==================== Transaction Models ====================

@dataclass
class Transaction:
    """Represents a transaction"""
    transaction_id: str
    wallet_id: str
    transaction_type: TransactionType
    amount: Decimal
    currency: Currency
    status: TransactionStatus
    timestamp: datetime
    description: str
    reference_id: Optional[str] = None
    from_wallet_id: Optional[str] = None
    to_wallet_id: Optional[str] = None
    payment_method_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (f"Transaction(id={self.transaction_id[:8]}..., type={self.transaction_type.value}, "
                f"amount={self.amount} {self.currency.value}, status={self.status.value})")


@dataclass
class TransactionFilter:
    """Filter criteria for transaction history"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transaction_types: Optional[List[TransactionType]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    status: Optional[TransactionStatus] = None
    currency: Optional[Currency] = None


# ==================== Balance Management ====================

class Balance:
    """Manages balance for a specific currency"""
    
    def __init__(self, currency: Currency, initial_amount: Decimal = Decimal('0')):
        self._currency = currency
        self._amount = initial_amount
        self._lock = RLock()
    
    def get_currency(self) -> Currency:
        return self._currency
    
    def get_amount(self) -> Decimal:
        with self._lock:
            return self._amount
    
    def credit(self, amount: Decimal) -> None:
        """Add funds"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Credit amount must be positive")
            self._amount += amount
    
    def debit(self, amount: Decimal) -> bool:
        """Deduct funds"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Debit amount must be positive")
            
            if self._amount < amount:
                return False  # Insufficient balance
            
            self._amount -= amount
            return True
    
    def has_sufficient_balance(self, amount: Decimal) -> bool:
        """Check if sufficient balance exists"""
        with self._lock:
            return self._amount >= amount
    
    def __repr__(self) -> str:
        return f"Balance({self._currency.value}: {self._amount})"


# ==================== Currency Converter ====================

class CurrencyConverter:
    """
    Handles currency conversion with exchange rates.
    In production, would integrate with real-time exchange rate APIs.
    """
    
    def __init__(self):
        # Simplified exchange rates (1 USD = X units of other currency)
        self._rates: Dict[tuple, Decimal] = {
            (Currency.USD, Currency.EUR): Decimal('0.92'),
            (Currency.USD, Currency.GBP): Decimal('0.79'),
            (Currency.USD, Currency.INR): Decimal('83.12'),
            (Currency.USD, Currency.JPY): Decimal('149.50'),
            (Currency.USD, Currency.CAD): Decimal('1.36'),
            # Reverse rates
            (Currency.EUR, Currency.USD): Decimal('1.09'),
            (Currency.GBP, Currency.USD): Decimal('1.27'),
            (Currency.INR, Currency.USD): Decimal('0.012'),
            (Currency.JPY, Currency.USD): Decimal('0.0067'),
            (Currency.CAD, Currency.USD): Decimal('0.74'),
        }
        self._lock = RLock()
        self._last_updated = datetime.now()
    
    def convert(self, amount: Decimal, from_currency: Currency, to_currency: Currency) -> Decimal:
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        with self._lock:
            # Direct conversion
            rate_key = (from_currency, to_currency)
            if rate_key in self._rates:
                converted = amount * self._rates[rate_key]
                return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Try conversion through USD
            if from_currency != Currency.USD and to_currency != Currency.USD:
                usd_amount = self.convert(amount, from_currency, Currency.USD)
                return self.convert(usd_amount, Currency.USD, to_currency)
            
            raise ValueError(f"No exchange rate available for {from_currency.value} to {to_currency.value}")
    
    def get_exchange_rate(self, from_currency: Currency, to_currency: Currency) -> Decimal:
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return Decimal('1')
        
        with self._lock:
            rate_key = (from_currency, to_currency)
            if rate_key in self._rates:
                return self._rates[rate_key]
            
            # Calculate through USD
            if from_currency != Currency.USD and to_currency != Currency.USD:
                to_usd = self.get_exchange_rate(from_currency, Currency.USD)
                from_usd = self.get_exchange_rate(Currency.USD, to_currency)
                return to_usd * from_usd
            
            raise ValueError(f"No exchange rate available for {from_currency.value} to {to_currency.value}")
    
    def update_rate(self, from_currency: Currency, to_currency: Currency, rate: Decimal) -> None:
        """Update exchange rate (admin function)"""
        with self._lock:
            self._rates[(from_currency, to_currency)] = rate
            self._last_updated = datetime.now()


# ==================== User and KYC ====================

@dataclass
class User:
    """Represents a user"""
    user_id: str
    email: str
    phone: str
    full_name: str
    kyc_status: KYCStatus
    created_at: datetime
    
    def __repr__(self) -> str:
        return f"User(id={self.user_id}, name={self.full_name}, kyc={self.kyc_status.value})"


# ==================== Wallet ====================

class Wallet:
    """
    Digital wallet with multi-currency support, payment methods, and transaction history.
    """
    
    def __init__(self, wallet_id: str, user: User, primary_currency: Currency = Currency.USD):
        self._wallet_id = wallet_id
        self._user = user
        self._primary_currency = primary_currency
        
        # Multi-currency balances
        self._balances: Dict[Currency, Balance] = {
            primary_currency: Balance(primary_currency)
        }
        
        # Payment methods
        self._payment_methods: Dict[str, PaymentMethod] = {}
        self._primary_payment_method: Optional[str] = None
        
        # Transaction history
        self._transactions: List[Transaction] = []
        
        # Limits (based on KYC)
        self._daily_limit = self._get_daily_limit()
        self._daily_spent = Decimal('0')
        self._last_reset_date = datetime.now().date()
        
        # Lock for thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._wallet_id
    
    def get_user(self) -> User:
        return self._user
    
    def get_primary_currency(self) -> Currency:
        return self._primary_currency
    
    def _get_daily_limit(self) -> Decimal:
        """Get daily transaction limit based on KYC status"""
        limits = {
            KYCStatus.NOT_SUBMITTED: Decimal('100'),
            KYCStatus.PENDING: Decimal('500'),
            KYCStatus.VERIFIED: Decimal('10000'),
            KYCStatus.REJECTED: Decimal('0')
        }
        return limits.get(self._user.kyc_status, Decimal('0'))
    
    def _reset_daily_limit_if_needed(self) -> None:
        """Reset daily spending if new day"""
        today = datetime.now().date()
        if today > self._last_reset_date:
            self._daily_spent = Decimal('0')
            self._last_reset_date = today
    
    def _check_daily_limit(self, amount: Decimal) -> bool:
        """Check if transaction is within daily limit"""
        self._reset_daily_limit_if_needed()
        return (self._daily_spent + amount) <= self._daily_limit
    
    # ==================== Balance Operations ====================
    
    def get_balance(self, currency: Currency = None) -> Decimal:
        """Get balance in specified currency (or primary currency)"""
        with self._lock:
            currency = currency or self._primary_currency
            if currency not in self._balances:
                self._balances[currency] = Balance(currency)
            return self._balances[currency].get_amount()
    
    def get_all_balances(self) -> Dict[Currency, Decimal]:
        """Get all currency balances"""
        with self._lock:
            return {currency: balance.get_amount() 
                    for currency, balance in self._balances.items()}
    
    def add_funds(self, amount: Decimal, currency: Currency, 
                  payment_method_id: Optional[str] = None,
                  description: str = "Add funds") -> Transaction:
        """Add funds to wallet"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Ensure balance exists for currency
            if currency not in self._balances:
                self._balances[currency] = Balance(currency)
            
            # Create transaction
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                wallet_id=self._wallet_id,
                transaction_type=TransactionType.DEPOSIT,
                amount=amount,
                currency=currency,
                status=TransactionStatus.PENDING,
                timestamp=datetime.now(),
                description=description,
                payment_method_id=payment_method_id
            )
            
            # Simulate payment processing
            try:
                self._balances[currency].credit(amount)
                transaction.status = TransactionStatus.COMPLETED
            except Exception as e:
                transaction.status = TransactionStatus.FAILED
                transaction.metadata['error'] = str(e)
            
            self._transactions.append(transaction)
            return transaction
    
    def withdraw_funds(self, amount: Decimal, currency: Currency,
                      payment_method_id: Optional[str] = None,
                      description: str = "Withdraw funds") -> Transaction:
        """Withdraw funds from wallet"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if currency not in self._balances:
                raise ValueError(f"No balance in {currency.value}")
            
            # Check daily limit
            if not self._check_daily_limit(amount):
                raise ValueError("Daily transaction limit exceeded")
            
            # Create transaction
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                wallet_id=self._wallet_id,
                transaction_type=TransactionType.WITHDRAWAL,
                amount=amount,
                currency=currency,
                status=TransactionStatus.PENDING,
                timestamp=datetime.now(),
                description=description,
                payment_method_id=payment_method_id
            )
            
            # Process withdrawal
            if self._balances[currency].debit(amount):
                transaction.status = TransactionStatus.COMPLETED
                self._daily_spent += amount
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.metadata['error'] = "Insufficient balance"
            
            self._transactions.append(transaction)
            return transaction
    
    # ==================== Payment Methods ====================
    
    def add_payment_method(self, payment_method: PaymentMethod) -> bool:
        """Add a payment method"""
        with self._lock:
            if not payment_method.validate():
                print("Payment method validation failed")
                return False
            
            self._payment_methods[payment_method.get_id()] = payment_method
            
            # Set as primary if it's the first one or marked as primary
            if not self._primary_payment_method or payment_method.is_primary():
                self._set_primary_payment_method(payment_method.get_id())
            
            print(f"Added payment method: {payment_method}")
            return True
    
    def remove_payment_method(self, method_id: str) -> bool:
        """Remove a payment method"""
        with self._lock:
            if method_id not in self._payment_methods:
                return False
            
            # Don't allow removing primary method if there are others
            if method_id == self._primary_payment_method and len(self._payment_methods) > 1:
                print("Cannot remove primary payment method. Set another as primary first.")
                return False
            
            del self._payment_methods[method_id]
            
            if method_id == self._primary_payment_method:
                self._primary_payment_method = None
                # Set another as primary if available
                if self._payment_methods:
                    self._primary_payment_method = next(iter(self._payment_methods.keys()))
            
            print(f"Removed payment method: {method_id}")
            return True
    
    def _set_primary_payment_method(self, method_id: str) -> bool:
        """Set primary payment method"""
        if method_id not in self._payment_methods:
            return False
        
        # Update all methods
        for mid, method in self._payment_methods.items():
            method.set_primary(mid == method_id)
        
        self._primary_payment_method = method_id
        return True
    
    def get_payment_methods(self) -> List[PaymentMethod]:
        """Get all payment methods"""
        with self._lock:
            return list(self._payment_methods.values())
    
    def get_primary_payment_method(self) -> Optional[PaymentMethod]:
        """Get primary payment method"""
        with self._lock:
            if self._primary_payment_method:
                return self._payment_methods.get(self._primary_payment_method)
            return None
    
    # ==================== Fund Transfer ====================
    
    def transfer_to_wallet(self, recipient_wallet: 'Wallet', amount: Decimal,
                          currency: Currency, description: str = "Fund transfer") -> Transaction:
        """Transfer funds to another wallet"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if currency not in self._balances:
                raise ValueError(f"No balance in {currency.value}")
            
            # Check daily limit
            if not self._check_daily_limit(amount):
                raise ValueError("Daily transaction limit exceeded")
            
            # Create transaction
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                wallet_id=self._wallet_id,
                transaction_type=TransactionType.TRANSFER_OUT,
                amount=amount,
                currency=currency,
                status=TransactionStatus.PENDING,
                timestamp=datetime.now(),
                description=description,
                to_wallet_id=recipient_wallet.get_id()
            )
            
            # Process transfer
            if self._balances[currency].debit(amount):
                # Credit recipient
                recipient_wallet._receive_transfer(self._wallet_id, amount, currency, description, transaction.transaction_id)
                transaction.status = TransactionStatus.COMPLETED
                self._daily_spent += amount
            else:
                transaction.status = TransactionStatus.FAILED
                transaction.metadata['error'] = "Insufficient balance"
            
            self._transactions.append(transaction)
            return transaction
    
    def _receive_transfer(self, from_wallet_id: str, amount: Decimal, 
                         currency: Currency, description: str, reference_id: str) -> None:
        """Internal method to receive transfer"""
        with self._lock:
            # Ensure balance exists
            if currency not in self._balances:
                self._balances[currency] = Balance(currency)
            
            # Credit amount
            self._balances[currency].credit(amount)
            
            # Create transaction record
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                wallet_id=self._wallet_id,
                transaction_type=TransactionType.TRANSFER_IN,
                amount=amount,
                currency=currency,
                status=TransactionStatus.COMPLETED,
                timestamp=datetime.now(),
                description=description,
                from_wallet_id=from_wallet_id,
                reference_id=reference_id
            )
            
            self._transactions.append(transaction)
    
    # ==================== Currency Exchange ====================
    
    def exchange_currency(self, from_currency: Currency, to_currency: Currency,
                         amount: Decimal, converter: CurrencyConverter) -> Transaction:
        """Exchange one currency for another"""
        with self._lock:
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            if from_currency not in self._balances:
                raise ValueError(f"No balance in {from_currency.value}")
            
            if from_currency == to_currency:
                raise ValueError("Cannot exchange same currency")
            
            # Create transaction
            transaction = Transaction(
                transaction_id=str(uuid.uuid4()),
                wallet_id=self._wallet_id,
                transaction_type=TransactionType.CURRENCY_EXCHANGE,
                amount=amount,
                currency=from_currency,
                status=TransactionStatus.PENDING,
                timestamp=datetime.now(),
                description=f"Exchange {from_currency.value} to {to_currency.value}"
            )
            
            try:
                # Calculate converted amount
                converted_amount = converter.convert(amount, from_currency, to_currency)
                exchange_rate = converter.get_exchange_rate(from_currency, to_currency)
                
                # Debit from source currency
                if not self._balances[from_currency].debit(amount):
                    transaction.status = TransactionStatus.FAILED
                    transaction.metadata['error'] = "Insufficient balance"
                else:
                    # Credit to target currency
                    if to_currency not in self._balances:
                        self._balances[to_currency] = Balance(to_currency)
                    
                    self._balances[to_currency].credit(converted_amount)
                    transaction.status = TransactionStatus.COMPLETED
                    transaction.metadata['to_currency'] = to_currency.value
                    transaction.metadata['converted_amount'] = str(converted_amount)
                    transaction.metadata['exchange_rate'] = str(exchange_rate)
            
            except Exception as e:
                transaction.status = TransactionStatus.FAILED
                transaction.metadata['error'] = str(e)
            
            self._transactions.append(transaction)
            return transaction
    
    # ==================== Transaction History ====================
    
    def get_transaction_history(self, filter_criteria: Optional[TransactionFilter] = None,
                               limit: int = 100) -> List[Transaction]:
        """Get transaction history with optional filters"""
        with self._lock:
            transactions = self._transactions.copy()
            
            if filter_criteria:
                # Apply filters
                if filter_criteria.start_date:
                    transactions = [t for t in transactions if t.timestamp >= filter_criteria.start_date]
                
                if filter_criteria.end_date:
                    transactions = [t for t in transactions if t.timestamp <= filter_criteria.end_date]
                
                if filter_criteria.transaction_types:
                    transactions = [t for t in transactions if t.transaction_type in filter_criteria.transaction_types]
                
                if filter_criteria.min_amount:
                    transactions = [t for t in transactions if t.amount >= filter_criteria.min_amount]
                
                if filter_criteria.max_amount:
                    transactions = [t for t in transactions if t.amount <= filter_criteria.max_amount]
                
                if filter_criteria.status:
                    transactions = [t for t in transactions if t.status == filter_criteria.status]
                
                if filter_criteria.currency:
                    transactions = [t for t in transactions if t.currency == filter_criteria.currency]
            
            # Sort by timestamp (most recent first) and apply limit
            transactions.sort(key=lambda t: t.timestamp, reverse=True)
            return transactions[:limit]
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Get specific transaction by ID"""
        with self._lock:
            for transaction in self._transactions:
                if transaction.transaction_id == transaction_id:
                    return transaction
            return None
    
    def get_spending_summary(self, days: int = 30) -> Dict[Currency, Decimal]:
        """Get spending summary for the last N days"""
        with self._lock:
            cutoff_date = datetime.now() - timedelta(days=days)
            spending: Dict[Currency, Decimal] = defaultdict(lambda: Decimal('0'))
            
            for transaction in self._transactions:
                if (transaction.timestamp >= cutoff_date and 
                    transaction.transaction_type in [TransactionType.DEBIT, TransactionType.TRANSFER_OUT, 
                                                     TransactionType.WITHDRAWAL, TransactionType.PAYMENT] and
                    transaction.status == TransactionStatus.COMPLETED):
                    spending[transaction.currency] += transaction.amount
            
            return dict(spending)
    
    def __repr__(self) -> str:
        balances_str = ', '.join([f"{curr.value}: {amt}" for curr, amt in self.get_all_balances().items()])
        return f"Wallet(id={self._wallet_id}, user={self._user.full_name}, balances=[{balances_str}])"


# ==================== Wallet Service ====================

class WalletService:
    """
    Central service managing all wallets and facilitating operations.
    """
    
    def __init__(self):
        self._wallets: Dict[str, Wallet] = {}
        self._user_wallets: Dict[str, str] = {}  # user_id -> wallet_id
        self._currency_converter = CurrencyConverter()
        self._lock = RLock()
    
    def create_wallet(self, user: User, primary_currency: Currency = Currency.USD) -> Wallet:
        """Create a new wallet for a user"""
        with self._lock:
            if user.user_id in self._user_wallets:
                raise ValueError(f"Wallet already exists for user {user.user_id}")
            
            wallet_id = str(uuid.uuid4())
            wallet = Wallet(wallet_id, user, primary_currency)
            
            self._wallets[wallet_id] = wallet
            self._user_wallets[user.user_id] = wallet_id
            
            print(f"Created wallet: {wallet}")
            return wallet
    
    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID"""
        return self._wallets.get(wallet_id)
    
    def get_wallet_by_user(self, user_id: str) -> Optional[Wallet]:
        """Get wallet by user ID"""
        wallet_id = self._user_wallets.get(user_id)
        if wallet_id:
            return self._wallets.get(wallet_id)
        return None
    
    def transfer_funds(self, from_wallet_id: str, to_wallet_id: str, 
                      amount: Decimal, currency: Currency,
                      description: str = "Fund transfer") -> Optional[Transaction]:
        """Transfer funds between wallets"""
        with self._lock:
            from_wallet = self.get_wallet(from_wallet_id)
            to_wallet = self.get_wallet(to_wallet_id)
            
            if not from_wallet or not to_wallet:
                print("Invalid wallet ID(s)")
                return None
            
            if from_wallet_id == to_wallet_id:
                print("Cannot transfer to same wallet")
                return None
            
            try:
                transaction = from_wallet.transfer_to_wallet(to_wallet, amount, currency, description)
                return transaction
            except Exception as e:
                print(f"Transfer failed: {e}")
                return None
    
    def get_currency_converter(self) -> CurrencyConverter:
        """Get currency converter instance"""
        return self._currency_converter
    
    def get_all_wallets(self) -> List[Wallet]:
        """Get all wallets"""
        with self._lock:
            return list(self._wallets.values())
    
    def get_system_stats(self) -> Dict:
        """Get system-wide statistics"""
        with self._lock:
            total_wallets = len(self._wallets)
            total_users = len(self._user_wallets)
            
            # Calculate total balances by currency
            total_balances: Dict[Currency, Decimal] = defaultdict(lambda: Decimal('0'))
            for wallet in self._wallets.values():
                for currency, amount in wallet.get_all_balances().items():
                    total_balances[currency] += amount
            
            # Count transactions
            total_transactions = sum(len(w._transactions) for w in self._wallets.values())
            
            return {
                'total_wallets': total_wallets,
                'total_users': total_users,
                'total_transactions': total_transactions,
                'total_balances': {curr.value: str(amt) for curr, amt in total_balances.items()}
            }


# ==================== Payment Method Factory ====================

class PaymentMethodFactory:
    """Factory for creating payment methods"""
    
    @staticmethod
    def create_credit_card(card_number: str, cardholder_name: str,
                          expiry_month: int, expiry_year: int, cvv: str,
                          is_primary: bool = False) -> CreditCard:
        """Create a credit card payment method"""
        method_id = str(uuid.uuid4())
        return CreditCard(method_id, card_number, cardholder_name, 
                         expiry_month, expiry_year, cvv, is_primary)
    
    @staticmethod
    def create_debit_card(card_number: str, cardholder_name: str,
                         expiry_month: int, expiry_year: int, cvv: str,
                         is_primary: bool = False) -> DebitCard:
        """Create a debit card payment method"""
        method_id = str(uuid.uuid4())
        return DebitCard(method_id, card_number, cardholder_name,
                        expiry_month, expiry_year, cvv, is_primary)
    
    @staticmethod
    def create_bank_account(account_number: str, routing_number: str,
                           account_holder_name: str, bank_name: str,
                           is_primary: bool = False) -> BankAccount:
        """Create a bank account payment method"""
        method_id = str(uuid.uuid4())
        return BankAccount(method_id, account_number, routing_number,
                          account_holder_name, bank_name, is_primary)
    
    @staticmethod
    def create_upi(upi_id: str, is_primary: bool = False) -> UPI:
        """Create a UPI payment method"""
        method_id = str(uuid.uuid4())
        return UPI(method_id, upi_id, is_primary)


# ==================== Demo Usage ====================

def print_separator(title: str):
    """Print formatted separator"""
    print("\n" + "="*70)
    print(f"TEST CASE: {title}")
    print("="*70)


def main():
    """Demo the digital wallet system"""
    print("=== Digital Wallet System Demo ===\n")
    
    # Initialize service
    wallet_service = WalletService()
    
    # Test Case 1: Create Users and Wallets
    print_separator("Create Users and Wallets")
    
    user1 = User(
        user_id="user-001",
        email="alice@example.com",
        phone="+1-555-0001",
        full_name="Alice Johnson",
        kyc_status=KYCStatus.VERIFIED,
        created_at=datetime.now()
    )
    
    user2 = User(
        user_id="user-002",
        email="bob@example.com",
        phone="+1-555-0002",
        full_name="Bob Smith",
        kyc_status=KYCStatus.VERIFIED,
        created_at=datetime.now()
    )
    
    user3 = User(
        user_id="user-003",
        email="charlie@example.com",
        phone="+91-9876543210",
        full_name="Charlie Patel",
        kyc_status=KYCStatus.PENDING,
        created_at=datetime.now()
    )
    
    wallet1 = wallet_service.create_wallet(user1, Currency.USD)
    wallet2 = wallet_service.create_wallet(user2, Currency.USD)
    wallet3 = wallet_service.create_wallet(user3, Currency.INR)
    
    print(f"\n{user1}")
    print(f"{wallet1}")
    print(f"\n{user2}")
    print(f"{wallet2}")
    print(f"\n{user3}")
    print(f"{wallet3}")
    
    # Test Case 2: Add Payment Methods
    print_separator("Add Payment Methods")
    
    factory = PaymentMethodFactory()
    
    # Alice adds multiple payment methods
    print(f"\nAlice adding payment methods:")
    credit_card = factory.create_credit_card(
        "4532015112830366",
        "Alice Johnson",
        12, 2026,
        "123",
        is_primary=True
    )
    wallet1.add_payment_method(credit_card)
    
    bank_account = factory.create_bank_account(
        "123456789",
        "021000021",
        "Alice Johnson",
        "Chase Bank"
    )
    wallet1.add_payment_method(bank_account)
    
    # Bob adds payment methods
    print(f"\nBob adding payment methods:")
    debit_card = factory.create_debit_card(
        "5425233430109903",
        "Bob Smith",
        8, 2025,
        "456",
        is_primary=True
    )
    wallet2.add_payment_method(debit_card)
    
    # Charlie adds UPI
    print(f"\nCharlie adding UPI:")
    upi = factory.create_upi("charlie@paytm", is_primary=True)
    wallet3.add_payment_method(upi)
    
    print(f"\nAlice's payment methods:")
    for method in wallet1.get_payment_methods():
        primary = " (PRIMARY)" if method.is_primary() else ""
        print(f"  - {method.get_display_info()}{primary}")
    
    # Test Case 3: Add Funds
    print_separator("Add Funds to Wallets")
    
    print(f"\nAlice adds $1000 USD:")
    txn1 = wallet1.add_funds(
        Decimal('1000'),
        Currency.USD,
        credit_card.get_id(),
        "Initial deposit"
    )
    print(f"Transaction: {txn1}")
    print(f"Alice's balance: ${wallet1.get_balance(Currency.USD)}")
    
    print(f"\nBob adds $500 USD:")
    txn2 = wallet2.add_funds(
        Decimal('500'),
        Currency.USD,
        debit_card.get_id(),
        "Initial deposit"
    )
    print(f"Transaction: {txn2}")
    print(f"Bob's balance: ${wallet2.get_balance(Currency.USD)}")
    
    print(f"\nCharlie adds ₹10000 INR:")
    txn3 = wallet3.add_funds(
        Decimal('10000'),
        Currency.INR,
        upi.get_id(),
        "Initial deposit"
    )
    print(f"Transaction: {txn3}")
    print(f"Charlie's balance: ₹{wallet3.get_balance(Currency.INR)}")
    
    # Test Case 4: Fund Transfer
    print_separator("Fund Transfer Between Wallets")
    
    print(f"\nAlice transfers $100 to Bob:")
    print(f"Alice's balance before: ${wallet1.get_balance(Currency.USD)}")
    print(f"Bob's balance before: ${wallet2.get_balance(Currency.USD)}")
    
    transfer_txn = wallet_service.transfer_funds(
        wallet1.get_id(),
        wallet2.get_id(),
        Decimal('100'),
        Currency.USD,
        "Payment for dinner"
    )
    
    print(f"Transfer transaction: {transfer_txn}")
    print(f"Alice's balance after: ${wallet1.get_balance(Currency.USD)}")
    print(f"Bob's balance after: ${wallet2.get_balance(Currency.USD)}")
    
    # Test Case 5: Multi-Currency Operations
    print_separator("Multi-Currency Operations")
    
    print(f"\nAlice adds €500 EUR:")
    wallet1.add_funds(Decimal('500'), Currency.EUR, description="EUR deposit")
    
    print(f"\nAlice adds £300 GBP:")
    wallet1.add_funds(Decimal('300'), Currency.GBP, description="GBP deposit")
    
    print(f"\nAlice's multi-currency balances:")
    for currency, amount in wallet1.get_all_balances().items():
        print(f"  {currency.value}: {amount}")
    
    # Test Case 6: Currency Conversion
    print_separator("Currency Conversion")
    
    converter = wallet_service.get_currency_converter()
    
    print(f"\nExchange rates:")
    print(f"1 USD = {converter.get_exchange_rate(Currency.USD, Currency.EUR)} EUR")
    print(f"1 USD = {converter.get_exchange_rate(Currency.USD, Currency.GBP)} GBP")
    print(f"1 USD = {converter.get_exchange_rate(Currency.USD, Currency.INR)} INR")
    
    print(f"\nAlice exchanges $200 USD to EUR:")
    print(f"USD balance before: ${wallet1.get_balance(Currency.USD)}")
    print(f"EUR balance before: €{wallet1.get_balance(Currency.EUR)}")
    
    exchange_txn = wallet1.exchange_currency(
        Currency.USD,
        Currency.EUR,
        Decimal('200'),
        converter
    )
    
    print(f"Exchange transaction: {exchange_txn}")
    print(f"Exchange rate: {exchange_txn.metadata.get('exchange_rate')}")
    print(f"Converted amount: €{exchange_txn.metadata.get('converted_amount')}")
    print(f"USD balance after: ${wallet1.get_balance(Currency.USD)}")
    print(f"EUR balance after: €{wallet1.get_balance(Currency.EUR)}")
    
    # Test Case 7: Transaction History
    print_separator("Transaction History")
    
    print(f"\nAlice's complete transaction history:")
    transactions = wallet1.get_transaction_history()
    for txn in transactions:
        print(f"  {txn.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - "
              f"{txn.transaction_type.value}: {txn.amount} {txn.currency.value} - "
              f"{txn.status.value}")
        if txn.description:
            print(f"    Description: {txn.description}")
    
    # Test Case 8: Filtered Transaction History
    print_separator("Filtered Transaction History")
    
    print(f"\nAlice's DEPOSIT transactions only:")
    filter_deposits = TransactionFilter(
        transaction_types=[TransactionType.DEPOSIT]
    )
    deposits = wallet1.get_transaction_history(filter_deposits)
    for txn in deposits:
        print(f"  {txn.timestamp.strftime('%Y-%m-%d')} - {txn.amount} {txn.currency.value}")
    
    print(f"\nAlice's transactions > $50:")
    filter_amount = TransactionFilter(
        min_amount=Decimal('50')
    )
    large_txns = wallet1.get_transaction_history(filter_amount)
    for txn in large_txns:
        print(f"  {txn.transaction_type.value}: {txn.amount} {txn.currency.value}")
    
    print(f"\nAlice's USD transactions only:")
    filter_currency = TransactionFilter(
        currency=Currency.USD
    )
    usd_txns = wallet1.get_transaction_history(filter_currency)
    for txn in usd_txns:
        print(f"  {txn.transaction_type.value}: {txn.amount} {txn.currency.value}")
    
    # Test Case 9: Spending Summary
    print_separator("Spending Summary")
    
    print(f"\nAlice's spending in last 30 days:")
    spending = wallet1.get_spending_summary(days=30)
    for currency, amount in spending.items():
        print(f"  {currency.value}: {amount}")
    
    # Test Case 10: Withdrawal
    print_separator("Withdrawal")
    
    print(f"\nBob withdraws $100:")
    print(f"Bob's balance before: ${wallet2.get_balance(Currency.USD)}")
    
    withdrawal_txn = wallet2.withdraw_funds(
        Decimal('100'),
        Currency.USD,
        debit_card.get_id(),
        "ATM withdrawal"
    )
    
    print(f"Withdrawal transaction: {withdrawal_txn}")
    print(f"Bob's balance after: ${wallet2.get_balance(Currency.USD)}")
    
    # Test Case 11: Remove Payment Method
    print_separator("Remove Payment Method")
    
    print(f"\nAlice's payment methods before removal:")
    for method in wallet1.get_payment_methods():
        print(f"  - {method.get_display_info()}")
    
    print(f"\nRemoving bank account...")
    wallet1.remove_payment_method(bank_account.get_id())
    
    print(f"\nAlice's payment methods after removal:")
    for method in wallet1.get_payment_methods():
        print(f"  - {method.get_display_info()}")
    
    # Test Case 12: Daily Limit (KYC-based)
    print_separator("Daily Transaction Limits (KYC-based)")
    
    print(f"\nUser KYC statuses and limits:")
    print(f"Alice (VERIFIED): ${wallet1._daily_limit} per day")
    print(f"Bob (VERIFIED): ${wallet2._daily_limit} per day")
    print(f"Charlie (PENDING): ₹{wallet3._daily_limit} per day")
    
    print(f"\nCharlie (PENDING KYC) tries to transfer ₹1000:")
    try:
        charlie_transfer = wallet_service.transfer_funds(
            wallet3.get_id(),
            wallet1.get_id(),
            Decimal('1000'),
            Currency.INR,
            "Payment"
        )
        if charlie_transfer and charlie_transfer.status == TransactionStatus.COMPLETED:
            print("Transfer successful")
        else:
            print("Transfer failed")
    except Exception as e:
        print(f"Transfer blocked: {e}")
    
    # Test Case 13: Insufficient Balance
    print_separator("Insufficient Balance Handling")
    
    print(f"\nBob tries to transfer $10000 (insufficient balance):")
    print(f"Bob's current balance: ${wallet2.get_balance(Currency.USD)}")
    
    try:
        failed_transfer = wallet_service.transfer_funds(
            wallet2.get_id(),
            wallet1.get_id(),
            Decimal('10000'),
            Currency.USD,
            "Large payment"
        )
        if failed_transfer:
            print(f"Transaction status: {failed_transfer.status.value}")
            if failed_transfer.status == TransactionStatus.FAILED:
                print(f"Reason: {failed_transfer.metadata.get('error')}")
    except Exception as e:
        print(f"Transfer failed: {e}")
    
    # Test Case 14: Cross-Currency Transfer (with conversion)
    print_separator("Cross-Currency Transfer")
    
    print(f"\nAlice has EUR, Bob needs USD:")
    print(f"Alice's EUR balance: €{wallet1.get_balance(Currency.EUR)}")
    print(f"Bob's USD balance: ${wallet2.get_balance(Currency.USD)}")
    
    print(f"\nOption 1: Alice converts EUR to USD, then transfers")
    print("Alice exchanges €100 to USD:")
    wallet1.exchange_currency(Currency.EUR, Currency.USD, Decimal('100'), converter)
    print(f"Alice's USD balance: ${wallet1.get_balance(Currency.USD)}")
    
    print("\nAlice transfers $109 to Bob:")
    wallet_service.transfer_funds(
        wallet1.get_id(),
        wallet2.get_id(),
        Decimal('109'),
        Currency.USD,
        "Cross-currency payment"
    )
    print(f"Bob's USD balance: ${wallet2.get_balance(Currency.USD)}")
    
    # Test Case 15: Transaction Search by ID
    print_separator("Transaction Search by ID")
    
    print(f"\nSearching for specific transaction:")
    if transfer_txn:
        found_txn = wallet1.get_transaction_by_id(transfer_txn.transaction_id)
        if found_txn:
            print(f"Found: {found_txn}")
            print(f"  Type: {found_txn.transaction_type.value}")
            print(f"  Amount: {found_txn.amount} {found_txn.currency.value}")
            print(f"  Status: {found_txn.status.value}")
            print(f"  To Wallet: {found_txn.to_wallet_id}")
    
    # Test Case 16: Primary Payment Method
    print_separator("Primary Payment Method Management")
    
    print(f"\nAlice's primary payment method:")
    primary = wallet1.get_primary_payment_method()
    if primary:
        print(f"  {primary.get_display_info()}")
    
    # Test Case 17: Multiple Deposits
    print_separator("Multiple Deposits (Batch Operations)")
    
    print(f"\nAlice makes multiple deposits:")
    deposit_amounts = [Decimal('50'), Decimal('75'), Decimal('100')]
    
    for amount in deposit_amounts:
        txn = wallet1.add_funds(amount, Currency.USD, description=f"Deposit ${amount}")
        print(f"  Deposited ${amount} - Status: {txn.status.value}")
    
    print(f"\nAlice's new USD balance: ${wallet1.get_balance(Currency.USD)}")
    
    # Test Case 18: System Statistics
    print_separator("System-Wide Statistics")
    
    stats = wallet_service.get_system_stats()
    print(f"\nSystem Statistics:")
    print(f"  Total Wallets: {stats['total_wallets']}")
    print(f"  Total Users: {stats['total_users']}")
    print(f"  Total Transactions: {stats['total_transactions']}")
    print(f"\n  Total Balances:")
    for currency, amount in stats['total_balances'].items():
        print(f"    {currency}: {amount}")
    
    # Test Case 19: Payment Method Validation
    print_separator("Payment Method Validation")
    
    print(f"\nTrying to add invalid credit card:")
    invalid_card = factory.create_credit_card(
        "1234567890123456",  # Invalid Luhn check
        "Test User",
        12, 2025,
        "123"
    )
    
    success = wallet1.add_payment_method(invalid_card)
    print(f"Add payment method result: {'Success' if success else 'Failed (validation error)'}")
    
    print(f"\nTrying to add expired card:")
    expired_card = factory.create_credit_card(
        "4532015112830366",
        "Test User",
        12, 2020,  # Expired
        "123"
    )
    
    success = wallet1.add_payment_method(expired_card)
    print(f"Add payment method result: {'Success' if success else 'Failed (expired)'}")
    
    # Test Case 20: Transaction History Date Range
    print_separator("Transaction History - Date Range Filter")
    
    # Get transactions from the last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    filter_recent = TransactionFilter(
        start_date=one_hour_ago
    )
    
    print(f"\nAlice's transactions in the last hour:")
    recent_txns = wallet1.get_transaction_history(filter_recent)
    print(f"Total transactions: {len(recent_txns)}")
    for txn in recent_txns[:5]:  # Show first 5
        print(f"  {txn.timestamp.strftime('%H:%M:%S')} - "
              f"{txn.transaction_type.value}: "
              f"{txn.amount} {txn.currency.value}")
    
    # Final Summary
    print_separator("Final Wallet Summary")
    
    print(f"\nAlice's Wallet:")
    print(f"  User: {wallet1.get_user().full_name}")
    print(f"  KYC Status: {wallet1.get_user().kyc_status.value}")
    print(f"  Primary Currency: {wallet1.get_primary_currency().value}")
    print(f"  Balances:")
    for currency, amount in wallet1.get_all_balances().items():
        print(f"    {currency.value}: {amount}")
    print(f"  Payment Methods: {len(wallet1.get_payment_methods())}")
    print(f"  Total Transactions: {len(wallet1._transactions)}")
    
    print(f"\nBob's Wallet:")
    print(f"  User: {wallet2.get_user().full_name}")
    print(f"  Balances:")
    for currency, amount in wallet2.get_all_balances().items():
        print(f"    {currency.value}: {amount}")
    print(f"  Total Transactions: {len(wallet2._transactions)}")
    
    print(f"\nCharlie's Wallet:")
    print(f"  User: {wallet3.get_user().full_name}")
    print(f"  Balances:")
    for currency, amount in wallet3.get_all_balances().items():
        print(f"    {currency.value}: {amount}")
    print(f"  Total Transactions: {len(wallet3._transactions)}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# Strategy Pattern - Different payment methods (CreditCard, DebitCard, BankAccount, UPI) implement the PaymentMethod interface with different validation strategies
# Factory Pattern - PaymentMethodFactory creates different types of payment methods
# Service Layer Pattern - WalletService acts as a central coordinator for wallet operations

# Key Features Implemented:

# Add/Remove Payment Methods:

# Multiple payment method types (credit card, debit card, bank account, UPI)
# Primary payment method designation
# Payment method validation (Luhn algorithm for cards, format validation)
# Safe removal with primary method protection


# Fund Transfer:

# Wallet-to-wallet transfers
# Transaction atomicity (debit + credit)
# Reference tracking between sender and receiver
# Transfer history with bidirectional records


# Transaction History:

# Comprehensive transaction recording
# Advanced filtering (date range, type, amount, status, currency)
# Transaction search by ID
# Spending summaries
# Chronological ordering


# Currency Conversion:

# Multi-currency wallet support
# Real-time exchange rate lookup
# Currency exchange transactions
# Conversion through intermediate currency (USD) when direct rate unavailable
# Exchange rate metadata in transactions


# Additional Features:

# KYC-based limits: Transaction limits based on verification status
# Daily spending limits: Reset automatically per day
# Multi-currency balances: Each wallet can hold multiple currencies
# Thread safety: RLock for concurrent operations
# Transaction status tracking: Pending, completed, failed states
# Payment method validation: Card validation (Luhn), expiry checks
# System statistics: Aggregate metrics across all wallets
# Insufficient balance handling: Proper error handling
# Transaction metadata: Extensible metadata storage



# Architecture Decisions:

# Balance per Currency: Each currency has its own Balance object for cleaner management
# Transaction Immutability: Transactions are created with final state (with dataclass)
# Decimal for Money: Using Decimal for precise financial calculations
# Thread Safety: RLock throughout for concurrent access
# Validation Layer: Payment methods validate themselves before being added
# Service Coordinator: Central WalletService manages cross-wallet operations
# Transaction Linking: Reference IDs link related transactions (transfers)

# This design provides a production-ready foundation for a digital wallet system with robust financial operations!
