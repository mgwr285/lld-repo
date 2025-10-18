from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
import uuid
from collections import defaultdict
import json


# ==================== Enums ====================

class BillingCycle(Enum):
    """Billing cycle types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    ONE_TIME = "one_time"
    USAGE_BASED = "usage_based"


class InvoiceStatus(Enum):
    """Invoice status"""
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentMethod(Enum):
    """Payment methods"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    WALLET = "wallet"
    CASH = "cash"
    CHECK = "check"


class TaxType(Enum):
    """Tax types"""
    SALES_TAX = "sales_tax"
    VAT = "vat"
    GST = "gst"
    SERVICE_TAX = "service_tax"
    CUSTOM_TAX = "custom_tax"


class DiscountType(Enum):
    """Discount types"""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"


class SubscriptionStatus(Enum):
    """Subscription status"""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"


class RefundStatus(Enum):
    """Refund status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSED = "processed"


# ==================== Core Models ====================

class Money:
    """Money value object with currency"""
    
    def __init__(self, amount: Decimal, currency: str = "USD"):
        self._amount = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self._currency = currency.upper()
    
    def get_amount(self) -> Decimal:
        return self._amount
    
    def get_currency(self) -> str:
        return self._currency
    
    def add(self, other: 'Money') -> 'Money':
        """Add two money values"""
        if self._currency != other._currency:
            raise ValueError(f"Cannot add different currencies: {self._currency} and {other._currency}")
        return Money(self._amount + other._amount, self._currency)
    
    def subtract(self, other: 'Money') -> 'Money':
        """Subtract two money values"""
        if self._currency != other._currency:
            raise ValueError(f"Cannot subtract different currencies: {self._currency} and {other._currency}")
        return Money(self._amount - other._amount, self._currency)
    
    def multiply(self, multiplier: Decimal) -> 'Money':
        """Multiply money by a value"""
        return Money(self._amount * Decimal(str(multiplier)), self._currency)
    
    def is_zero(self) -> bool:
        return self._amount == Decimal('0')
    
    def is_positive(self) -> bool:
        return self._amount > Decimal('0')
    
    def is_negative(self) -> bool:
        return self._amount < Decimal('0')
    
    def __str__(self) -> str:
        return f"{self._currency} {self._amount:.2f}"
    
    def __repr__(self) -> str:
        return f"Money({self._amount}, '{self._currency}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency
    
    def __lt__(self, other: 'Money') -> bool:
        if self._currency != other._currency:
            raise ValueError("Cannot compare different currencies")
        return self._amount < other._amount
    
    def __le__(self, other: 'Money') -> bool:
        if self._currency != other._currency:
            raise ValueError("Cannot compare different currencies")
        return self._amount <= other._amount


class Address:
    """Address information"""
    
    def __init__(self, street: str, city: str, state: str, 
                 country: str, postal_code: str):
        self._street = street
        self._city = city
        self._state = state
        self._country = country
        self._postal_code = postal_code
    
    def get_street(self) -> str:
        return self._street
    
    def get_city(self) -> str:
        return self._city
    
    def get_state(self) -> str:
        return self._state
    
    def get_country(self) -> str:
        return self._country
    
    def get_postal_code(self) -> str:
        return self._postal_code
    
    def get_formatted(self) -> str:
        return f"{self._street}, {self._city}, {self._state} {self._postal_code}, {self._country}"


class Customer:
    """Customer entity"""
    
    def __init__(self, customer_id: str, name: str, email: str, phone: str):
        self._customer_id = customer_id
        self._name = name
        self._email = email
        self._phone = phone
        self._billing_address: Optional[Address] = None
        self._shipping_address: Optional[Address] = None
        self._tax_id: Optional[str] = None  # Tax ID / GST number
        self._created_at = datetime.now()
        self._metadata: Dict[str, Any] = {}
    
    def get_id(self) -> str:
        return self._customer_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_phone(self) -> str:
        return self._phone
    
    def set_billing_address(self, address: Address) -> None:
        self._billing_address = address
    
    def get_billing_address(self) -> Optional[Address]:
        return self._billing_address
    
    def set_shipping_address(self, address: Address) -> None:
        self._shipping_address = address
    
    def get_shipping_address(self) -> Optional[Address]:
        return self._shipping_address
    
    def set_tax_id(self, tax_id: str) -> None:
        self._tax_id = tax_id
    
    def get_tax_id(self) -> Optional[str]:
        return self._tax_id
    
    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        return self._metadata.get(key)


class Product:
    """Product or service being billed"""
    
    def __init__(self, product_id: str, name: str, description: str,
                 unit_price: Money, sku: Optional[str] = None):
        self._product_id = product_id
        self._name = name
        self._description = description
        self._unit_price = unit_price
        self._sku = sku or product_id
        self._is_taxable = True
        self._metadata: Dict[str, Any] = {}
    
    def get_id(self) -> str:
        return self._product_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_description(self) -> str:
        return self._description
    
    def get_unit_price(self) -> Money:
        return self._unit_price
    
    def set_unit_price(self, price: Money) -> None:
        self._unit_price = price
    
    def get_sku(self) -> str:
        return self._sku
    
    def is_taxable(self) -> bool:
        return self._is_taxable
    
    def set_taxable(self, taxable: bool) -> None:
        self._is_taxable = taxable


class Tax:
    """Tax configuration"""
    
    def __init__(self, tax_id: str, name: str, tax_type: TaxType, rate: Decimal):
        self._tax_id = tax_id
        self._name = name
        self._tax_type = tax_type
        self._rate = Decimal(str(rate))  # Percentage (e.g., 18.0 for 18%)
        self._is_compound = False  # Applied after other taxes
    
    def get_id(self) -> str:
        return self._tax_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_type(self) -> TaxType:
        return self._tax_type
    
    def get_rate(self) -> Decimal:
        return self._rate
    
    def set_rate(self, rate: Decimal) -> None:
        self._rate = Decimal(str(rate))
    
    def calculate_tax_amount(self, base_amount: Money) -> Money:
        """Calculate tax amount on base amount"""
        tax_amount = base_amount.get_amount() * (self._rate / Decimal('100'))
        return Money(tax_amount, base_amount.get_currency())
    
    def is_compound(self) -> bool:
        return self._is_compound
    
    def set_compound(self, compound: bool) -> None:
        self._is_compound = compound


class Discount:
    """Discount configuration"""
    
    def __init__(self, discount_id: str, name: str, discount_type: DiscountType,
                 value: Decimal, code: Optional[str] = None):
        self._discount_id = discount_id
        self._name = name
        self._discount_type = discount_type
        self._value = Decimal(str(value))
        self._code = code
        self._min_amount: Optional[Money] = None
        self._max_amount: Optional[Money] = None
        self._valid_from: Optional[datetime] = None
        self._valid_until: Optional[datetime] = None
        self._usage_limit: Optional[int] = None
        self._times_used = 0
    
    def get_id(self) -> str:
        return self._discount_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_code(self) -> Optional[str]:
        return self._code
    
    def get_type(self) -> DiscountType:
        return self._discount_type
    
    def set_validity_period(self, valid_from: datetime, valid_until: datetime) -> None:
        self._valid_from = valid_from
        self._valid_until = valid_until
    
    def is_valid(self) -> bool:
        """Check if discount is currently valid"""
        now = datetime.now()
        
        if self._valid_from and now < self._valid_from:
            return False
        
        if self._valid_until and now > self._valid_until:
            return False
        
        if self._usage_limit and self._times_used >= self._usage_limit:
            return False
        
        return True
    
    def calculate_discount_amount(self, amount: Money) -> Money:
        """Calculate discount amount"""
        if not self.is_valid():
            return Money(Decimal('0'), amount.get_currency())
        
        if self._discount_type == DiscountType.PERCENTAGE:
            discount_amount = amount.get_amount() * (self._value / Decimal('100'))
            return Money(discount_amount, amount.get_currency())
        
        elif self._discount_type == DiscountType.FIXED_AMOUNT:
            return Money(min(self._value, amount.get_amount()), amount.get_currency())
        
        return Money(Decimal('0'), amount.get_currency())
    
    def increment_usage(self) -> None:
        self._times_used += 1


class InvoiceLineItem:
    """Line item in an invoice"""
    
    def __init__(self, product: Product, quantity: Decimal, 
                 unit_price: Optional[Money] = None):
        self._item_id = str(uuid.uuid4())
        self._product = product
        self._quantity = Decimal(str(quantity))
        self._unit_price = unit_price or product.get_unit_price()
        self._discount: Optional[Discount] = None
        self._taxes: List[Tax] = []
        self._description_override: Optional[str] = None
    
    def get_id(self) -> str:
        return self._item_id
    
    def get_product(self) -> Product:
        return self._product
    
    def get_quantity(self) -> Decimal:
        return self._quantity
    
    def set_quantity(self, quantity: Decimal) -> None:
        self._quantity = Decimal(str(quantity))
    
    def get_unit_price(self) -> Money:
        return self._unit_price
    
    def set_unit_price(self, price: Money) -> None:
        self._unit_price = price
    
    def get_subtotal(self) -> Money:
        """Calculate subtotal (quantity × unit price)"""
        return self._unit_price.multiply(self._quantity)
    
    def apply_discount(self, discount: Discount) -> None:
        self._discount = discount
    
    def get_discount_amount(self) -> Money:
        """Calculate discount amount"""
        if not self._discount:
            return Money(Decimal('0'), self._unit_price.get_currency())
        
        subtotal = self.get_subtotal()
        return self._discount.calculate_discount_amount(subtotal)
    
    def add_tax(self, tax: Tax) -> None:
        self._taxes.append(tax)
    
    def get_taxes(self) -> List[Tax]:
        return self._taxes.copy()
    
    def calculate_tax_amount(self) -> Money:
        """Calculate total tax amount"""
        if not self._product.is_taxable():
            return Money(Decimal('0'), self._unit_price.get_currency())
        
        subtotal = self.get_subtotal()
        discount_amount = self.get_discount_amount()
        taxable_amount = subtotal.subtract(discount_amount)
        
        total_tax = Money(Decimal('0'), self._unit_price.get_currency())
        
        # Calculate simple taxes first
        for tax in self._taxes:
            if not tax.is_compound():
                tax_amount = tax.calculate_tax_amount(taxable_amount)
                total_tax = total_tax.add(tax_amount)
        
        # Then compound taxes (applied on amount + simple taxes)
        amount_with_simple_tax = taxable_amount.add(total_tax)
        for tax in self._taxes:
            if tax.is_compound():
                tax_amount = tax.calculate_tax_amount(amount_with_simple_tax)
                total_tax = total_tax.add(tax_amount)
        
        return total_tax
    
    def get_total(self) -> Money:
        """Calculate total (subtotal - discount + tax)"""
        subtotal = self.get_subtotal()
        discount = self.get_discount_amount()
        tax = self.calculate_tax_amount()
        
        return subtotal.subtract(discount).add(tax)
    
    def set_description_override(self, description: str) -> None:
        self._description_override = description
    
    def get_description(self) -> str:
        return self._description_override or self._product.get_description()


class Invoice:
    """Invoice for billing"""
    
    def __init__(self, invoice_id: str, customer: Customer, invoice_number: str):
        self._invoice_id = invoice_id
        self._customer = customer
        self._invoice_number = invoice_number
        self._status = InvoiceStatus.DRAFT
        
        # Line items
        self._line_items: List[InvoiceLineItem] = []
        
        # Dates
        self._created_at = datetime.now()
        self._issued_at: Optional[datetime] = None
        self._due_at: Optional[datetime] = None
        self._paid_at: Optional[datetime] = None
        
        # Invoice-level discount
        self._invoice_discount: Optional[Discount] = None
        
        # Notes and terms
        self._notes: Optional[str] = None
        self._terms: Optional[str] = None
        
        # Payments
        self._payments: List['Payment'] = []
        
        # Currency
        self._currency = "USD"
        
        # Metadata
        self._metadata: Dict[str, Any] = {}
    
    def get_id(self) -> str:
        return self._invoice_id
    
    def get_invoice_number(self) -> str:
        return self._invoice_number
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def get_status(self) -> InvoiceStatus:
        return self._status
    
    def set_status(self, status: InvoiceStatus) -> None:
        self._status = status
        
        if status == InvoiceStatus.SENT and not self._issued_at:
            self._issued_at = datetime.now()
        elif status == InvoiceStatus.PAID and not self._paid_at:
            self._paid_at = datetime.now()
    
    def add_line_item(self, line_item: InvoiceLineItem) -> None:
        self._line_items.append(line_item)
    
    def get_line_items(self) -> List[InvoiceLineItem]:
        return self._line_items.copy()
    
    def remove_line_item(self, item_id: str) -> bool:
        for i, item in enumerate(self._line_items):
            if item.get_id() == item_id:
                self._line_items.pop(i)
                return True
        return False
    
    def set_due_date(self, due_date: datetime) -> None:
        self._due_at = due_date
    
    def get_due_date(self) -> Optional[datetime]:
        return self._due_at
    
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        if not self._due_at:
            return False
        
        if self._status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.REFUNDED]:
            return False
        
        return datetime.now() > self._due_at
    
    def apply_invoice_discount(self, discount: Discount) -> None:
        """Apply discount to entire invoice"""
        self._invoice_discount = discount
    
    def get_subtotal(self) -> Money:
        """Calculate subtotal of all line items"""
        if not self._line_items:
            return Money(Decimal('0'), self._currency)
        
        subtotal = Money(Decimal('0'), self._currency)
        for item in self._line_items:
            subtotal = subtotal.add(item.get_subtotal())
        
        return subtotal
    
    def get_total_discount(self) -> Money:
        """Calculate total discount amount"""
        total = Money(Decimal('0'), self._currency)
        
        # Line item discounts
        for item in self._line_items:
            total = total.add(item.get_discount_amount())
        
        # Invoice-level discount
        if self._invoice_discount:
            subtotal = self.get_subtotal()
            invoice_discount = self._invoice_discount.calculate_discount_amount(subtotal)
            total = total.add(invoice_discount)
        
        return total
    
    def get_total_tax(self) -> Money:
        """Calculate total tax amount"""
        total = Money(Decimal('0'), self._currency)
        
        for item in self._line_items:
            total = total.add(item.calculate_tax_amount())
        
        return total
    
    def get_total(self) -> Money:
        """Calculate invoice total"""
        if not self._line_items:
            return Money(Decimal('0'), self._currency)
        
        total = Money(Decimal('0'), self._currency)
        
        for item in self._line_items:
            total = total.add(item.get_total())
        
        # Apply invoice-level discount
        if self._invoice_discount:
            subtotal = self.get_subtotal()
            invoice_discount = self._invoice_discount.calculate_discount_amount(subtotal)
            total = total.subtract(invoice_discount)
        
        return total
    
    def get_amount_paid(self) -> Money:
        """Calculate total amount paid"""
        total = Money(Decimal('0'), self._currency)
        
        for payment in self._payments:
            if payment.get_status() == PaymentStatus.COMPLETED:
                total = total.add(payment.get_amount())
        
        return total
    
    def get_amount_due(self) -> Money:
        """Calculate remaining amount due"""
        return self.get_total().subtract(self.get_amount_paid())
    
    def add_payment(self, payment: 'Payment') -> None:
        self._payments.append(payment)
        
        # Update status based on payment
        if payment.get_status() == PaymentStatus.COMPLETED:
            amount_due = self.get_amount_due()
            
            if amount_due.is_zero():
                self.set_status(InvoiceStatus.PAID)
            elif amount_due.is_positive():
                self.set_status(InvoiceStatus.PARTIALLY_PAID)
    
    def get_payments(self) -> List['Payment']:
        return self._payments.copy()
    
    def set_notes(self, notes: str) -> None:
        self._notes = notes
    
    def set_terms(self, terms: str) -> None:
        self._terms = terms
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def get_issued_at(self) -> Optional[datetime]:
        return self._issued_at
    
    def finalize(self) -> None:
        """Finalize draft invoice"""
        if self._status == InvoiceStatus.DRAFT:
            self.set_status(InvoiceStatus.PENDING)


class Payment:
    """Payment record"""
    
    def __init__(self, payment_id: str, invoice: Invoice, amount: Money,
                 payment_method: PaymentMethod):
        self._payment_id = payment_id
        self._invoice = invoice
        self._amount = amount
        self._payment_method = payment_method
        self._status = PaymentStatus.PENDING
        
        self._created_at = datetime.now()
        self._processed_at: Optional[datetime] = None
        
        self._transaction_id: Optional[str] = None
        self._reference_number: Optional[str] = None
        
        self._notes: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
    
    def get_id(self) -> str:
        return self._payment_id
    
    def get_invoice(self) -> Invoice:
        return self._invoice
    
    def get_amount(self) -> Money:
        return self._amount
    
    def get_payment_method(self) -> PaymentMethod:
        return self._payment_method
    
    def get_status(self) -> PaymentStatus:
        return self._status
    
    def set_status(self, status: PaymentStatus) -> None:
        self._status = status
        
        if status == PaymentStatus.COMPLETED:
            self._processed_at = datetime.now()
    
    def set_transaction_id(self, transaction_id: str) -> None:
        self._transaction_id = transaction_id
    
    def get_transaction_id(self) -> Optional[str]:
        return self._transaction_id
    
    def set_reference_number(self, reference: str) -> None:
        self._reference_number = reference
    
    def set_notes(self, notes: str) -> None:
        self._notes = notes
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def process(self) -> bool:
        """Process the payment"""
        if self._status != PaymentStatus.PENDING:
            return False
        
        self.set_status(PaymentStatus.PROCESSING)
        
        # Simulate payment processing
        # In real system, integrate with payment gateway
        
        self.set_status(PaymentStatus.COMPLETED)
        return True


class Refund:
    """Refund record"""
    
    def __init__(self, refund_id: str, payment: Payment, amount: Money, reason: str):
        self._refund_id = refund_id
        self._payment = payment
        self._amount = amount
        self._reason = reason
        self._status = RefundStatus.PENDING
        
        self._created_at = datetime.now()
        self._processed_at: Optional[datetime] = None
        
        self._notes: Optional[str] = None
    
    def get_id(self) -> str:
        return self._refund_id
    
    def get_payment(self) -> Payment:
        return self._payment
    
    def get_amount(self) -> Money:
        return self._amount
    
    def get_reason(self) -> str:
        return self._reason
    
    def get_status(self) -> RefundStatus:
        return self._status
    
    def approve(self) -> None:
        if self._status == RefundStatus.PENDING:
            self._status = RefundStatus.APPROVED
    
    def reject(self) -> None:
        if self._status == RefundStatus.PENDING:
            self._status = RefundStatus.REJECTED
    
    def process(self) -> bool:
        """Process the refund"""
        if self._status != RefundStatus.APPROVED:
            return False
        
        self._status = RefundStatus.PROCESSED
        self._processed_at = datetime.now()
        
        # Update payment status
        if self._amount == self._payment.get_amount():
            self._payment.set_status(PaymentStatus.REFUNDED)
        else:
            self._payment.set_status(PaymentStatus.PARTIALLY_REFUNDED)
        
        return True


class Subscription:
    """Subscription for recurring billing"""
    
    def __init__(self, subscription_id: str, customer: Customer,
                 product: Product, billing_cycle: BillingCycle):
        self._subscription_id = subscription_id
        self._customer = customer
        self._product = product
        self._billing_cycle = billing_cycle
        self._status = SubscriptionStatus.ACTIVE
        
        self._start_date = datetime.now()
        self._end_date: Optional[datetime] = None
        self._next_billing_date = self._calculate_next_billing_date(self._start_date)
        
        self._trial_end_date: Optional[datetime] = None
        
        self._invoices: List[Invoice] = []
        
        # Pricing
        self._quantity = Decimal('1')
        self._unit_price = product.get_unit_price()
    
    def get_id(self) -> str:
        return self._subscription_id
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def get_product(self) -> Product:
        return self._product
    
    def get_billing_cycle(self) -> BillingCycle:
        return self._billing_cycle
    
    def get_status(self) -> SubscriptionStatus:
        return self._status
    
    def set_status(self, status: SubscriptionStatus) -> None:
        self._status = status
    
    def get_next_billing_date(self) -> datetime:
        return self._next_billing_date
    
    def set_trial_period(self, days: int) -> None:
        """Set trial period in days"""
        self._trial_end_date = self._start_date + timedelta(days=days)
        self._status = SubscriptionStatus.TRIAL
    
    def is_in_trial(self) -> bool:
        if not self._trial_end_date:
            return False
        return datetime.now() < self._trial_end_date
    
    def _calculate_next_billing_date(self, from_date: datetime) -> datetime:
        """Calculate next billing date"""
        if self._billing_cycle == BillingCycle.MONTHLY:
            # Add 1 month
            next_month = from_date.month + 1
            next_year = from_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            return from_date.replace(year=next_year, month=next_month)
        
        elif self._billing_cycle == BillingCycle.QUARTERLY:
            return from_date + timedelta(days=90)
        
        elif self._billing_cycle == BillingCycle.SEMI_ANNUAL:
            return from_date + timedelta(days=180)
        
        elif self._billing_cycle == BillingCycle.ANNUAL:
            return from_date.replace(year=from_date.year + 1)
        
        return from_date
    
    def generate_invoice(self, billing_system: 'BillingSystem') -> Optional[Invoice]:
        """Generate invoice for current billing period"""
        if self._status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            return None
        
        # Don't charge during trial
        if self.is_in_trial():
            return None
        
        invoice = billing_system.create_invoice(self._customer)
        
        # Add subscription item
        line_item = InvoiceLineItem(self._product, self._quantity, self._unit_price)
        invoice.add_line_item(line_item)
        
        # Set due date (e.g., 7 days from now)
        invoice.set_due_date(datetime.now() + timedelta(days=7))
        
        # Finalize and send
        invoice.finalize()
        invoice.set_status(InvoiceStatus.SENT)
        
        self._invoices.append(invoice)
        
        # Update next billing date
        self._next_billing_date = self._calculate_next_billing_date(self._next_billing_date)
        
        return invoice
    
    def cancel(self, immediate: bool = False) -> None:
        """Cancel subscription"""
        if immediate:
            self._status = SubscriptionStatus.CANCELLED
            self._end_date = datetime.now()
        else:
            # Cancel at end of billing period
            self._end_date = self._next_billing_date
    
    def pause(self) -> None:
        """Pause subscription"""
        if self._status == SubscriptionStatus.ACTIVE:
            self._status = SubscriptionStatus.PAUSED
    
    def resume(self) -> None:
        """Resume paused subscription"""
        if self._status == SubscriptionStatus.PAUSED:
            self._status = SubscriptionStatus.ACTIVE


# ==================== Billing System ====================

class BillingSystem:
    """
    Main billing system
    Features:
    - Invoice generation and management
    - Payment processing
    - Subscription management
    - Tax calculations
    - Discount management
    - Refund processing
    """
    
    def __init__(self):
        # Storage
        self._customers: Dict[str, Customer] = {}
        self._products: Dict[str, Product] = {}
        self._invoices: Dict[str, Invoice] = {}
        self._payments: Dict[str, Payment] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._taxes: Dict[str, Tax] = {}
        self._discounts: Dict[str, Discount] = {}
        self._refunds: Dict[str, Refund] = {}
        
        # Indexes
        self._customer_invoices: Dict[str, List[str]] = defaultdict(list)
        self._invoice_payments: Dict[str, List[str]] = defaultdict(list)
        
        # Invoice numbering
        self._invoice_counter = 1000
        
        # Statistics
        self._total_revenue = Money(Decimal('0'), "USD")
        self._total_refunds = Money(Decimal('0'), "USD")
    
    # ==================== Customer Management ====================
    
    def create_customer(self, name: str, email: str, phone: str) -> Customer:
        """Create a new customer"""
        customer_id = str(uuid.uuid4())
        customer = Customer(customer_id, name, email, phone)
        self._customers[customer_id] = customer
        print(f"✅ Customer created: {name} ({email})")
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)
    
    # ==================== Product Management ====================
    
    def create_product(self, name: str, description: str, 
                      unit_price: Money, sku: Optional[str] = None) -> Product:
        """Create a new product"""
        product_id = str(uuid.uuid4())
        product = Product(product_id, name, description, unit_price, sku)
        self._products[product_id] = product
        print(f"✅ Product created: {name} - {unit_price}")
        return product
    
    def get_product(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)
    
    # ==================== Tax Management ====================
    
    def create_tax(self, name: str, tax_type: TaxType, rate: Decimal) -> Tax:
        """Create a tax"""
        tax_id = str(uuid.uuid4())
        tax = Tax(tax_id, name, tax_type, rate)
        self._taxes[tax_id] = tax
        print(f"✅ Tax created: {name} ({rate}%)")
        return tax
    
    def get_tax(self, tax_id: str) -> Optional[Tax]:
        return self._taxes.get(tax_id)
    
    # ==================== Discount Management ====================
    
    def create_discount(self, name: str, discount_type: DiscountType,
                       value: Decimal, code: Optional[str] = None) -> Discount:
        """Create a discount"""
        discount_id = str(uuid.uuid4())
        discount = Discount(discount_id, name, discount_type, value, code)
        self._discounts[discount_id] = discount
        print(f"✅ Discount created: {name} ({value}{'%' if discount_type == DiscountType.PERCENTAGE else ''})")
        return discount
    
    def get_discount(self, discount_id: str) -> Optional[Discount]:
        return self._discounts.get(discount_id)
    
    def get_discount_by_code(self, code: str) -> Optional[Discount]:
        """Get discount by code"""
        for discount in self._discounts.values():
            if discount.get_code() == code:
                return discount
        return None
    
    # ==================== Invoice Management ====================
    
    def create_invoice(self, customer: Customer) -> Invoice:
        """Create a new invoice"""
        invoice_id = str(uuid.uuid4())
        invoice_number = f"INV-{self._invoice_counter:06d}"
        self._invoice_counter += 1
        
        invoice = Invoice(invoice_id, customer, invoice_number)
        self._invoices[invoice_id] = invoice
        self._customer_invoices[customer.get_id()].append(invoice_id)
        
        print(f"✅ Invoice created: {invoice_number} for {customer.get_name()}")
        return invoice
    
    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)
    
    def get_customer_invoices(self, customer_id: str) -> List[Invoice]:
        """Get all invoices for a customer"""
        invoice_ids = self._customer_invoices.get(customer_id, [])
        return [self._invoices[iid] for iid in invoice_ids if iid in self._invoices]
    
    def send_invoice(self, invoice_id: str) -> bool:
        """Send invoice to customer"""
        invoice = self._invoices.get(invoice_id)
        if not invoice:
            return False
        
        if invoice.get_status() != InvoiceStatus.PENDING:
            return False
        
        invoice.set_status(InvoiceStatus.SENT)
        print(f"📧 Invoice sent: {invoice.get_invoice_number()} to {invoice.get_customer().get_email()}")
        return True
    
    def check_overdue_invoices(self) -> List[Invoice]:
        """Find overdue invoices"""
        overdue = []
        
        for invoice in self._invoices.values():
            if invoice.is_overdue():
                if invoice.get_status() != InvoiceStatus.OVERDUE:
                    invoice.set_status(InvoiceStatus.OVERDUE)
                    print(f"⚠️  Invoice overdue: {invoice.get_invoice_number()}")
                overdue.append(invoice)
        
        return overdue
    
    # ==================== Payment Management ====================
    
    def create_payment(self, invoice: Invoice, amount: Money,
                      payment_method: PaymentMethod) -> Payment:
        """Create a payment"""
        payment_id = str(uuid.uuid4())
        payment = Payment(payment_id, invoice, amount, payment_method)
        
        self._payments[payment_id] = payment
        self._invoice_payments[invoice.get_id()].append(payment_id)
        
        print(f"💳 Payment created: {amount} for invoice {invoice.get_invoice_number()}")
        return payment
    
    def process_payment(self, payment_id: str) -> bool:
        """Process a payment"""
        payment = self._payments.get(payment_id)
        if not payment:
            return False
        
        success = payment.process()
        
        if success:
            # Add payment to invoice
            payment.get_invoice().add_payment(payment)
            
            # Update revenue
            self._total_revenue = self._total_revenue.add(payment.get_amount())
            
            print(f"✅ Payment processed: {payment.get_amount()}")
        else:
            print(f"❌ Payment failed")
        
        return success
    
    def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)
    
    # ==================== Refund Management ====================
    
    def create_refund(self, payment: Payment, amount: Money, reason: str) -> Refund:
        """Create a refund request"""
        refund_id = str(uuid.uuid4())
        refund = Refund(refund_id, payment, amount, reason)
        
        self._refunds[refund_id] = refund
        
        print(f"🔄 Refund requested: {amount} for payment {payment.get_id()}")
        print(f"   Reason: {reason}")
        return refund
    
    def approve_refund(self, refund_id: str) -> bool:
        """Approve a refund"""
        refund = self._refunds.get(refund_id)
        if not refund:
            return False
        
        refund.approve()
        print(f"✅ Refund approved: {refund.get_amount()}")
        return True
    
    def process_refund(self, refund_id: str) -> bool:
        """Process an approved refund"""
        refund = self._refunds.get(refund_id)
        if not refund:
            return False
        
        success = refund.process()
        
        if success:
            self._total_refunds = self._total_refunds.add(refund.get_amount())
            print(f"✅ Refund processed: {refund.get_amount()}")
        
        return success
    
    # ==================== Subscription Management ====================
    
    def create_subscription(self, customer: Customer, product: Product,
                           billing_cycle: BillingCycle) -> Subscription:
        """Create a new subscription"""
        subscription_id = str(uuid.uuid4())
        subscription = Subscription(subscription_id, customer, product, billing_cycle)
        
        self._subscriptions[subscription_id] = subscription
        
        print(f"✅ Subscription created: {product.get_name()} for {customer.get_name()}")
        print(f"   Billing cycle: {billing_cycle.value}")
        print(f"   Next billing: {subscription.get_next_billing_date()}")
        return subscription
    
    def get_subscription(self, subscription_id: str) -> Optional[Subscription]:
        return self._subscriptions.get(subscription_id)
    
    def process_subscriptions(self) -> List[Invoice]:
        """Process due subscriptions and generate invoices"""
        invoices = []
        now = datetime.now()
        
        for subscription in self._subscriptions.values():
            if subscription.get_status() not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
                continue
            
            # Check if billing is due
            if now >= subscription.get_next_billing_date():
                invoice = subscription.generate_invoice(self)
                if invoice:
                    invoices.append(invoice)
                    print(f"📄 Subscription invoice generated: {invoice.get_invoice_number()}")
        
        return invoices
    
    # ==================== Reports and Analytics ====================
    
    def get_revenue_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get revenue report for date range"""
        total_revenue = Money(Decimal('0'), "USD")
        total_invoices = 0
        paid_invoices = 0
        
        for invoice in self._invoices.values():
            created = invoice.get_created_at()
            if start_date <= created <= end_date:
                total_invoices += 1
                
                if invoice.get_status() == InvoiceStatus.PAID:
                    paid_invoices += 1
                    total_revenue = total_revenue.add(invoice.get_total())
        
        return {
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_revenue': str(total_revenue),
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoices,
            'payment_rate': f"{(paid_invoices/total_invoices*100) if total_invoices > 0 else 0:.1f}%"
        }
    
    def get_customer_report(self, customer_id: str) -> Dict:
        """Get customer billing report"""
        customer = self._customers.get(customer_id)
        if not customer:
            return {}
        
        invoices = self.get_customer_invoices(customer_id)
        
        total_billed = Money(Decimal('0'), "USD")
        total_paid = Money(Decimal('0'), "USD")
        total_outstanding = Money(Decimal('0'), "USD")
        
        for invoice in invoices:
            total_billed = total_billed.add(invoice.get_total())
            total_paid = total_paid.add(invoice.get_amount_paid())
            
            if invoice.get_status() in [InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]:
                total_outstanding = total_outstanding.add(invoice.get_amount_due())
        
        return {
            'customer_name': customer.get_name(),
            'customer_email': customer.get_email(),
            'total_invoices': len(invoices),
            'total_billed': str(total_billed),
            'total_paid': str(total_paid),
            'total_outstanding': str(total_outstanding)
        }
    
    def get_statistics(self) -> Dict:
        """Get overall system statistics"""
        total_customers = len(self._customers)
        total_products = len(self._products)
        total_invoices = len(self._invoices)
        
        paid_invoices = sum(1 for inv in self._invoices.values() 
                          if inv.get_status() == InvoiceStatus.PAID)
        
        overdue_invoices = sum(1 for inv in self._invoices.values() 
                             if inv.get_status() == InvoiceStatus.OVERDUE)
        
        active_subscriptions = sum(1 for sub in self._subscriptions.values() 
                                  if sub.get_status() == SubscriptionStatus.ACTIVE)
        
        return {
            'total_customers': total_customers,
            'total_products': total_products,
            'total_invoices': total_invoices,
            'paid_invoices': paid_invoices,
            'overdue_invoices': overdue_invoices,
            'active_subscriptions': active_subscriptions,
            'total_revenue': str(self._total_revenue),
            'total_refunds': str(self._total_refunds),
            'net_revenue': str(self._total_revenue.subtract(self._total_refunds))
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_invoice(invoice: Invoice) -> None:
    """Print invoice details"""
    print(f"\n📄 INVOICE: {invoice.get_invoice_number()}")
    print(f"   Status: {invoice.get_status().value}")
    print(f"   Customer: {invoice.get_customer().get_name()}")
    print(f"   Date: {invoice.get_created_at().strftime('%Y-%m-%d')}")
    if invoice.get_due_date():
        print(f"   Due Date: {invoice.get_due_date().strftime('%Y-%m-%d')}")
    
    print(f"\n   Line Items:")
    for item in invoice.get_line_items():
        print(f"      • {item.get_product().get_name()}")
        print(f"        Qty: {item.get_quantity()}, "
              f"Unit Price: {item.get_unit_price()}, "
              f"Total: {item.get_total()}")
        
        if item.get_discount_amount().is_positive():
            print(f"        Discount: -{item.get_discount_amount()}")
        
        if item.calculate_tax_amount().is_positive():
            print(f"        Tax: {item.calculate_tax_amount()}")
    
    print(f"\n   Subtotal: {invoice.get_subtotal()}")
    
    if invoice.get_total_discount().is_positive():
        print(f"   Total Discount: -{invoice.get_total_discount()}")
    
    if invoice.get_total_tax().is_positive():
        print(f"   Total Tax: {invoice.get_total_tax()}")
    
    print(f"   TOTAL: {invoice.get_total()}")
    
    if invoice.get_amount_paid().is_positive():
        print(f"   Amount Paid: {invoice.get_amount_paid()}")
        print(f"   Amount Due: {invoice.get_amount_due()}")


def demo_billing_system():
    """Comprehensive demo of the billing system"""
    
    print_section("BILLING SYSTEM DEMO")
    
    system = BillingSystem()
    
    # ==================== Setup ====================
    print_section("1. Setup - Create Customers and Products")
    
    # Create customers
    alice = system.create_customer("Alice Johnson", "alice@example.com", "+1-555-0101")
    bob = system.create_customer("Bob Smith", "bob@example.com", "+1-555-0102")
    charlie = system.create_customer("Charlie Brown", "charlie@example.com", "+1-555-0103")
    
    # Set addresses
    alice.set_billing_address(Address(
        "123 Main St", "New York", "NY", "USA", "10001"
    ))
    
    # Create products
    basic_plan = system.create_product(
        "Basic Cloud Plan",
        "Basic cloud hosting with 10GB storage",
        Money(Decimal('29.99'), "USD"),
        "PLAN-BASIC"
    )
    
    pro_plan = system.create_product(
        "Pro Cloud Plan",
        "Professional cloud hosting with 100GB storage",
        Money(Decimal('99.99'), "USD"),
        "PLAN-PRO"
    )
    
    consulting = system.create_product(
        "Consulting Services",
        "Technical consulting per hour",
        Money(Decimal('150.00'), "USD"),
        "CONSULT-HR"
    )
    
    # Create taxes
    sales_tax = system.create_tax("Sales Tax", TaxType.SALES_TAX, Decimal('8.5'))
    gst = system.create_tax("GST", TaxType.GST, Decimal('18.0'))
    
    # Create discounts
    welcome_discount = system.create_discount(
        "Welcome Discount",
        DiscountType.PERCENTAGE,
        Decimal('10.0'),
        "WELCOME10"
    )
    
    flat_discount = system.create_discount(
        "Flat $20 Off",
        DiscountType.FIXED_AMOUNT,
        Decimal('20.0'),
        "SAVE20"
    )
    
    # ==================== Simple Invoice ====================
    print_section("2. Create Simple Invoice")
    
    invoice1 = system.create_invoice(alice)
    
    # Add line items
    item1 = InvoiceLineItem(pro_plan, Decimal('1'))
    item1.add_tax(sales_tax)
    invoice1.add_line_item(item1)
    
    # Set due date (30 days from now)
    invoice1.set_due_date(datetime.now() + timedelta(days=30))
    
    # Finalize and send
    invoice1.finalize()
    system.send_invoice(invoice1.get_id())
    
    print_invoice(invoice1)
    
    # ==================== Invoice with Discount ====================
    print_section("3. Invoice with Discount")
    
    invoice2 = system.create_invoice(bob)
    
    # Add consulting hours
    item2 = InvoiceLineItem(consulting, Decimal('5'))  # 5 hours
    item2.add_tax(sales_tax)
    item2.apply_discount(welcome_discount)
    invoice2.add_line_item(item2)
    
    invoice2.set_due_date(datetime.now() + timedelta(days=15))
    invoice2.finalize()
    system.send_invoice(invoice2.get_id())
    
    print_invoice(invoice2)
    
    # ==================== Invoice with Multiple Items ====================
    print_section("4. Invoice with Multiple Items and Taxes")
    
    invoice3 = system.create_invoice(charlie)
    
    # Add multiple items
    item3a = InvoiceLineItem(basic_plan, Decimal('2'))  # 2 basic plans
    item3a.add_tax(gst)
    invoice3.add_line_item(item3a)
    
    item3b = InvoiceLineItem(consulting, Decimal('3'))  # 3 hours
    item3b.add_tax(gst)
    invoice3.add_line_item(item3b)
    
    # Apply invoice-level discount
    invoice3.apply_invoice_discount(flat_discount)
    
    invoice3.set_due_date(datetime.now() + timedelta(days=7))
    invoice3.finalize()
    system.send_invoice(invoice3.get_id())
    
    print_invoice(invoice3)
    
    # ==================== Payment Processing ====================
    print_section("5. Process Payments")
    
    # Full payment for invoice1
    payment1 = system.create_payment(
        invoice1,
        invoice1.get_total(),
        PaymentMethod.CREDIT_CARD
    )
    payment1.set_transaction_id("TXN-12345")
    system.process_payment(payment1.get_id())
    
    print(f"\n✅ Payment processed for {invoice1.get_invoice_number()}")
    print(f"   Amount: {payment1.get_amount()}")
    print(f"   Method: {payment1.get_payment_method().value}")
    print(f"   Status: {invoice1.get_status().value}")
    
    # Partial payment for invoice2
    partial_amount = invoice2.get_total().multiply(Decimal('0.5'))
    payment2 = system.create_payment(
        invoice2,
        partial_amount,
        PaymentMethod.BANK_TRANSFER
    )
    system.process_payment(payment2.get_id())
    
    print(f"\n💳 Partial payment for {invoice2.get_invoice_number()}")
    print(f"   Paid: {invoice2.get_amount_paid()}")
    print(f"   Due: {invoice2.get_amount_due()}")
    print(f"   Status: {invoice2.get_status().value}")
    
    # ==================== Subscriptions ====================
    print_section("6. Create Subscriptions")
    
    # Monthly subscription
    sub1 = system.create_subscription(alice, pro_plan, BillingCycle.MONTHLY)
    sub1.set_trial_period(14)  # 14-day trial
    
    print(f"\n   Trial period: {sub1.is_in_trial()}")
    print(f"   Status: {sub1.get_status().value}")
    
    # Annual subscription
    sub2 = system.create_subscription(bob, basic_plan, BillingCycle.ANNUAL)
    
    # Simulate subscription billing
    print(f"\n   Simulating subscription billing...")
    
    # Force next billing date to now for demo
    sub2._next_billing_date = datetime.now()
    
    subscription_invoices = system.process_subscriptions()
    
    if subscription_invoices:
        print(f"   Generated {len(subscription_invoices)} subscription invoice(s)")
        for inv in subscription_invoices:
            print_invoice(inv)
    
    # ==================== Refund Processing ====================
    print_section("7. Process Refund")
    
    # Request refund for payment1
    refund = system.create_refund(
        payment1,
        Money(Decimal('50.00'), "USD"),
        "Customer requested partial refund"
    )
    
    # Approve and process
    system.approve_refund(refund.get_id())
    system.process_refund(refund.get_id())
    
    print(f"   Refund status: {refund.get_status().value}")
    print(f"   Payment status: {payment1.get_status().value}")
    
    # ==================== Overdue Invoices ====================
    print_section("8. Check Overdue Invoices")
    
    # Manually set invoice as overdue for demo
    invoice3._due_at = datetime.now() - timedelta(days=1)
    
    overdue = system.check_overdue_invoices()
    
    print(f"\n   Found {len(overdue)} overdue invoice(s):")
    for inv in overdue:
        print(f"      • {inv.get_invoice_number()}: "
              f"{inv.get_customer().get_name()}, "
              f"Due: {inv.get_due_date().strftime('%Y-%m-%d')}, "
              f"Amount: {inv.get_amount_due()}")
    
    # ==================== Customer Report ====================
    print_section("9. Customer Billing Report")
    
    alice_report = system.get_customer_report(alice.get_id())
    
    print(f"\n📊 Customer Report: {alice_report['customer_name']}")
    print(f"   Email: {alice_report['customer_email']}")
    print(f"   Total Invoices: {alice_report['total_invoices']}")
    print(f"   Total Billed: {alice_report['total_billed']}")
    print(f"   Total Paid: {alice_report['total_paid']}")
    print(f"   Outstanding: {alice_report['total_outstanding']}")
    
    # ==================== Revenue Report ====================
    print_section("10. Revenue Report")
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    revenue_report = system.get_revenue_report(start_date, end_date)
    
    print(f"\n💰 Revenue Report")
    print(f"   Period: {revenue_report['period']}")
    print(f"   Total Revenue: {revenue_report['total_revenue']}")
    print(f"   Total Invoices: {revenue_report['total_invoices']}")
    print(f"   Paid Invoices: {revenue_report['paid_invoices']}")
    print(f"   Payment Rate: {revenue_report['payment_rate']}")
    
    # ==================== System Statistics ====================
    print_section("11. System Statistics")
    
    stats = system.get_statistics()
    
    print(f"\n📈 System Statistics:")
    print(f"   Total Customers: {stats['total_customers']}")
    print(f"   Total Products: {stats['total_products']}")
    print(f"   Total Invoices: {stats['total_invoices']}")
    print(f"   Paid Invoices: {stats['paid_invoices']}")
    print(f"   Overdue Invoices: {stats['overdue_invoices']}")
    print(f"   Active Subscriptions: {stats['active_subscriptions']}")
    print(f"   Total Revenue: {stats['total_revenue']}")
    print(f"   Total Refunds: {stats['total_refunds']}")
    print(f"   Net Revenue: {stats['net_revenue']}")
    
    # ==================== Invoice Operations ====================
    print_section("12. Advanced Invoice Operations")
    
    # Create complex invoice
    complex_invoice = system.create_invoice(alice)
    
    # Multiple items with different taxes
    item_a = InvoiceLineItem(pro_plan, Decimal('1'))
    item_a.add_tax(sales_tax)
    item_a.apply_discount(welcome_discount)
    complex_invoice.add_line_item(item_a)
    
    item_b = InvoiceLineItem(consulting, Decimal('2'))
    item_b.add_tax(gst)
    complex_invoice.add_line_item(item_b)
    
    item_c = InvoiceLineItem(basic_plan, Decimal('3'))
    item_c.add_tax(sales_tax)
    complex_invoice.add_line_item(item_c)
    
    # Add notes and terms
    complex_invoice.set_notes("Thank you for your business!")
    complex_invoice.set_terms("Payment due within 30 days. Late payments subject to 1.5% monthly interest.")
    
    complex_invoice.finalize()
    
    print_invoice(complex_invoice)
    
    print_section("Demo Complete")
    print("\n✅ Billing system demo completed successfully!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_billing_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Billing System - Low Level Design
# Here's a comprehensive billing and invoicing system design:

# Key Design Decisions:
# 1. Core Components:
# Money: Value object with currency (prevents currency mixing)
# Customer: Customer entity with billing/shipping addresses
# Product: Products/services being billed
# Invoice: Main billing document
# InvoiceLineItem: Individual items in invoice
# Payment: Payment records
# Subscription: Recurring billing
# Tax & Discount: Flexible tax and discount system
# Refund: Refund processing
# 2. Key Features:
# ✅ Invoice generation (draft, finalize, send) ✅ Line item management (quantity, pricing, descriptions) ✅ Tax calculations (multiple taxes, compound taxes) ✅ Discount system (percentage, fixed amount, coupon codes) ✅ Payment processing (multiple payment methods) ✅ Partial payments (track amount paid/due) ✅ Refund management (full/partial refunds) ✅ Subscription billing (recurring invoices) ✅ Overdue tracking (automatic status updates) ✅ Reports & analytics (revenue, customer reports)

# 3. Money Handling:
# Uses Decimal for precision (no floating point errors)
# Currency-aware operations
# Prevents mixing different currencies
# Automatic rounding (2 decimal places)
# 4. Tax Calculation:
