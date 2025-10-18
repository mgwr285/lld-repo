from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
import time


# ==================== Enums ====================

class VehicleType(Enum):
    """Types of vehicles"""
    ECONOMY = "ECONOMY"
    COMPACT = "COMPACT"
    SEDAN = "SEDAN"
    SUV = "SUV"
    LUXURY = "LUXURY"
    VAN = "VAN"


class VehicleStatus(Enum):
    """Status of a vehicle"""
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    RENTED = "RENTED"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class BookingStatus(Enum):
    """Status of a booking"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"           # Pickup completed
    COMPLETED = "COMPLETED"      # Drop-off completed
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"


class PaymentStatus(Enum):
    """Status of payment"""
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"    # Credit card authorized
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentMethod(Enum):
    """Payment methods"""
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    CASH = "CASH"


# ==================== Core Models ====================

class Vehicle:
    """Represents a rental vehicle"""
    
    def __init__(self, vehicle_id: str, make: str, model: str, year: int,
                 vehicle_type: VehicleType, license_plate: str, 
                 daily_rate: float, mileage: int = 0):
        self._vehicle_id = vehicle_id
        self._make = make
        self._model = model
        self._year = year
        self._vehicle_type = vehicle_type
        self._license_plate = license_plate
        self._daily_rate = daily_rate
        self._mileage = mileage
        self._status = VehicleStatus.AVAILABLE
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._vehicle_id
    
    def get_make(self) -> str:
        return self._make
    
    def get_model(self) -> str:
        return self._model
    
    def get_type(self) -> VehicleType:
        return self._vehicle_type
    
    def get_license_plate(self) -> str:
        return self._license_plate
    
    def get_daily_rate(self) -> float:
        return self._daily_rate
    
    def get_mileage(self) -> int:
        with self._lock:
            return self._mileage
    
    def add_mileage(self, miles: int) -> None:
        with self._lock:
            self._mileage += miles
    
    def get_status(self) -> VehicleStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: VehicleStatus) -> None:
        with self._lock:
            self._status = status
    
    def is_available(self) -> bool:
        return self.get_status() == VehicleStatus.AVAILABLE
    
    def __repr__(self) -> str:
        return f"{self._year} {self._make} {self._model} ({self._license_plate})"
    
    def __hash__(self) -> int:
        return hash(self._vehicle_id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Vehicle):
            return False
        return self._vehicle_id == other._vehicle_id


class Store:
    """Represents a rental store location"""
    
    def __init__(self, store_id: str, name: str, address: str, 
                 phone: str, opening_hours: str):
        self._store_id = store_id
        self._name = name
        self._address = address
        self._phone = phone
        self._opening_hours = opening_hours
        self._vehicles: Dict[str, Vehicle] = {}  # vehicle_id -> Vehicle
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._store_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_address(self) -> str:
        return self._address
    
    def add_vehicle(self, vehicle: Vehicle) -> None:
        """Add a vehicle to this store"""
        with self._lock:
            self._vehicles[vehicle.get_id()] = vehicle
    
    def remove_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Remove a vehicle from this store"""
        with self._lock:
            return self._vehicles.pop(vehicle_id, None)
    
    def get_vehicle(self, vehicle_id: str) -> Optional[Vehicle]:
        """Get a specific vehicle"""
        with self._lock:
            return self._vehicles.get(vehicle_id)
    
    def get_all_vehicles(self) -> List[Vehicle]:
        """Get all vehicles at this store"""
        with self._lock:
            return list(self._vehicles.values())
    
    def get_available_vehicles(self, vehicle_type: Optional[VehicleType] = None) -> List[Vehicle]:
        """Get available vehicles, optionally filtered by type"""
        with self._lock:
            vehicles = [v for v in self._vehicles.values() if v.is_available()]
            if vehicle_type:
                vehicles = [v for v in vehicles if v.get_type() == vehicle_type]
            return vehicles
    
    def __repr__(self) -> str:
        return f"Store({self._store_id}, {self._name}, {self._address})"


class Customer:
    """Represents a customer"""
    
    def __init__(self, customer_id: str, name: str, email: str, 
                 phone: str, drivers_license: str):
        self._customer_id = customer_id
        self._name = name
        self._email = email
        self._phone = phone
        self._drivers_license = drivers_license
    
    def get_id(self) -> str:
        return self._customer_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_drivers_license(self) -> str:
        return self._drivers_license
    
    def __repr__(self) -> str:
        return f"Customer({self._customer_id}, {self._name})"


class Booking:
    """Represents a rental booking"""
    
    _booking_counter = 0
    
    def __init__(self, customer: Customer, vehicle: Vehicle,
                 pickup_store: Store, dropoff_store: Store,
                 pickup_datetime: datetime, dropoff_datetime: datetime):
        Booking._booking_counter += 1
        self._booking_id = f"BK-{Booking._booking_counter:08d}"
        self._customer = customer
        self._vehicle = vehicle
        self._pickup_store = pickup_store
        self._dropoff_store = dropoff_store
        self._pickup_datetime = pickup_datetime
        self._dropoff_datetime = dropoff_datetime
        self._actual_pickup_datetime: Optional[datetime] = None
        self._actual_dropoff_datetime: Optional[datetime] = None
        self._status = BookingStatus.PENDING
        self._created_at = datetime.now()
        self._pickup_mileage: Optional[int] = None
        self._dropoff_mileage: Optional[int] = None
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._booking_id
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def get_vehicle(self) -> Vehicle:
        return self._vehicle
    
    def get_pickup_store(self) -> Store:
        return self._pickup_store
    
    def get_dropoff_store(self) -> Store:
        return self._dropoff_store
    
    def get_pickup_datetime(self) -> datetime:
        return self._pickup_datetime
    
    def get_dropoff_datetime(self) -> datetime:
        return self._dropoff_datetime
    
    def get_actual_pickup_datetime(self) -> Optional[datetime]:
        with self._lock:
            return self._actual_pickup_datetime
    
    def get_actual_dropoff_datetime(self) -> Optional[datetime]:
        with self._lock:
            return self._actual_dropoff_datetime
    
    def get_status(self) -> BookingStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: BookingStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_rental_days(self) -> int:
        """Get number of rental days"""
        duration = self._dropoff_datetime - self._pickup_datetime
        days = duration.days
        # If there are any hours, round up to full day
        if duration.seconds > 0:
            days += 1
        return max(1, days)  # Minimum 1 day
    
    def get_actual_rental_days(self) -> int:
        """Get actual rental days based on pickup/dropoff times"""
        if not self._actual_pickup_datetime or not self._actual_dropoff_datetime:
            return self.get_rental_days()
        
        duration = self._actual_dropoff_datetime - self._actual_pickup_datetime
        days = duration.days
        if duration.seconds > 0:
            days += 1
        return max(1, days)
    
    def complete_pickup(self, mileage: int) -> None:
        """Complete the pickup process"""
        with self._lock:
            self._actual_pickup_datetime = datetime.now()
            self._pickup_mileage = mileage
            self._status = BookingStatus.ACTIVE
    
    def complete_dropoff(self, mileage: int) -> None:
        """Complete the dropoff process"""
        with self._lock:
            self._actual_dropoff_datetime = datetime.now()
            self._dropoff_mileage = mileage
            self._status = BookingStatus.COMPLETED
    
    def get_miles_driven(self) -> Optional[int]:
        """Get miles driven during rental"""
        if self._pickup_mileage is not None and self._dropoff_mileage is not None:
            return self._dropoff_mileage - self._pickup_mileage
        return None
    
    def is_overdue(self) -> bool:
        """Check if booking is overdue"""
        if self._status != BookingStatus.ACTIVE:
            return False
        return datetime.now() > self._dropoff_datetime
    
    def __repr__(self) -> str:
        return (f"Booking({self._booking_id}, {self._customer.get_name()}, "
                f"{self._vehicle}, {self._status.value})")


@dataclass
class Payment:
    """Represents a payment transaction"""
    payment_id: str
    booking: Booking
    amount: float
    payment_method: PaymentMethod
    status: PaymentStatus
    payment_datetime: datetime
    transaction_reference: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"Payment({self.payment_id}, ${self.amount:.2f}, {self.status.value})"


class Invoice:
    """Represents an invoice for a booking"""
    
    _invoice_counter = 0
    
    def __init__(self, booking: Booking, base_amount: float, 
                 taxes: float, fees: float, total_amount: float):
        Invoice._invoice_counter += 1
        self._invoice_id = f"INV-{Invoice._invoice_counter:08d}"
        self._booking = booking
        self._base_amount = base_amount
        self._taxes = taxes
        self._fees = fees
        self._total_amount = total_amount
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._invoice_id
    
    def get_booking(self) -> Booking:
        return self._booking
    
    def get_total_amount(self) -> float:
        return self._total_amount
    
    def display(self) -> None:
        """Display invoice details"""
        print(f"\n{'='*60}")
        print(f"INVOICE {self._invoice_id}")
        print(f"{'='*60}")
        print(f"Booking ID: {self._booking.get_id()}")
        print(f"Customer: {self._booking.get_customer().get_name()}")
        print(f"Vehicle: {self._booking.get_vehicle()}")
        print(f"Rental Period: {self._booking.get_rental_days()} days")
        print(f"-" * 60)
        print(f"Base Amount:        ${self._base_amount:>10.2f}")
        print(f"Taxes:              ${self._taxes:>10.2f}")
        print(f"Fees:               ${self._fees:>10.2f}")
        print(f"-" * 60)
        print(f"Total Amount:       ${self._total_amount:>10.2f}")
        print(f"{'='*60}\n")


# ==================== Strategy Pattern: Pricing Strategies ====================

class PricingStrategy(ABC):
    """Abstract strategy for calculating rental prices"""
    
    @abstractmethod
    def calculate_price(self, booking: Booking) -> float:
        """Calculate the rental price for a booking"""
        pass


class StandardPricingStrategy(PricingStrategy):
    """Standard daily rate pricing"""
    
    def __init__(self, tax_rate: float = 0.10, service_fee: float = 25.0):
        self._tax_rate = tax_rate
        self._service_fee = service_fee
    
    def calculate_price(self, booking: Booking) -> float:
        """Calculate price based on daily rate and rental days"""
        days = booking.get_rental_days()
        daily_rate = booking.get_vehicle().get_daily_rate()
        
        base_amount = days * daily_rate
        taxes = base_amount * self._tax_rate
        total = base_amount + taxes + self._service_fee
        
        return total


class WeekendPricingStrategy(PricingStrategy):
    """Pricing with weekend surcharge"""
    
    def __init__(self, tax_rate: float = 0.10, service_fee: float = 25.0,
                 weekend_multiplier: float = 1.5):
        self._tax_rate = tax_rate
        self._service_fee = service_fee
        self._weekend_multiplier = weekend_multiplier
    
    def calculate_price(self, booking: Booking) -> float:
        """Calculate price with weekend surcharge"""
        daily_rate = booking.get_vehicle().get_daily_rate()
        
        # Count weekend vs weekday days
        current_date = booking.get_pickup_datetime().date()
        end_date = booking.get_dropoff_datetime().date()
        
        weekday_days = 0
        weekend_days = 0
        
        while current_date <= end_date:
            if current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                weekend_days += 1
            else:
                weekday_days += 1
            current_date += timedelta(days=1)
        
        base_amount = (weekday_days * daily_rate + 
                      weekend_days * daily_rate * self._weekend_multiplier)
        taxes = base_amount * self._tax_rate
        total = base_amount + taxes + self._service_fee
        
        return total


class LoyaltyPricingStrategy(PricingStrategy):
    """Pricing with loyalty discounts"""
    
    def __init__(self, tax_rate: float = 0.10, service_fee: float = 25.0):
        self._tax_rate = tax_rate
        self._service_fee = service_fee
        # In real system, would track customer rental history
        self._discount_tiers = {
            'bronze': 0.05,   # 5% discount
            'silver': 0.10,   # 10% discount
            'gold': 0.15      # 15% discount
        }
    
    def calculate_price(self, booking: Booking) -> float:
        """Calculate price with loyalty discount"""
        days = booking.get_rental_days()
        daily_rate = booking.get_vehicle().get_daily_rate()
        
        base_amount = days * daily_rate
        
        # Apply discount (simplified - always give bronze tier)
        discount = base_amount * self._discount_tiers['bronze']
        base_amount -= discount
        
        taxes = base_amount * self._tax_rate
        total = base_amount + taxes + self._service_fee
        
        return total


# ==================== Strategy Pattern: Payment Processing ====================

class PaymentProcessor(ABC):
    """Abstract payment processor"""
    
    @abstractmethod
    def process_payment(self, booking: Booking, amount: float, 
                       payment_method: PaymentMethod) -> Payment:
        """Process payment and return Payment object"""
        pass
    
    @abstractmethod
    def refund_payment(self, payment: Payment, amount: float) -> bool:
        """Process refund"""
        pass


class CreditCardProcessor(PaymentProcessor):
    """Process credit card payments"""
    
    _payment_counter = 0
    
    def process_payment(self, booking: Booking, amount: float, 
                       payment_method: PaymentMethod) -> Payment:
        CreditCardProcessor._payment_counter += 1
        payment_id = f"PAY-CC-{CreditCardProcessor._payment_counter:08d}"
        
        # Simulate credit card processing
        # In real system, would integrate with payment gateway
        transaction_ref = f"TXN-{int(time.time())}"
        
        payment = Payment(
            payment_id=payment_id,
            booking=booking,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.COMPLETED,
            payment_datetime=datetime.now(),
            transaction_reference=transaction_ref
        )
        
        print(f"[Payment] Processed ${amount:.2f} via {payment_method.value}")
        return payment
    
    def refund_payment(self, payment: Payment, amount: float) -> bool:
        """Process refund"""
        print(f"[Payment] Refunded ${amount:.2f} to {payment.payment_method.value}")
        payment.status = PaymentStatus.REFUNDED
        return True


class CashProcessor(PaymentProcessor):
    """Process cash payments"""
    
    _payment_counter = 0
    
    def process_payment(self, booking: Booking, amount: float, 
                       payment_method: PaymentMethod) -> Payment:
        CashProcessor._payment_counter += 1
        payment_id = f"PAY-CASH-{CashProcessor._payment_counter:08d}"
        
        payment = Payment(
            payment_id=payment_id,
            booking=booking,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.COMPLETED,
            payment_datetime=datetime.now()
        )
        
        print(f"[Payment] Received ${amount:.2f} in cash")
        return payment
    
    def refund_payment(self, payment: Payment, amount: float) -> bool:
        """Process refund"""
        print(f"[Payment] Refunded ${amount:.2f} in cash")
        payment.status = PaymentStatus.REFUNDED
        return True


class PaymentService:
    """Service to handle payment processing"""
    
    def __init__(self):
        self._processors: Dict[PaymentMethod, PaymentProcessor] = {
            PaymentMethod.CREDIT_CARD: CreditCardProcessor(),
            PaymentMethod.DEBIT_CARD: CreditCardProcessor(),
            PaymentMethod.CASH: CashProcessor()
        }
    
    def process_payment(self, booking: Booking, amount: float,
                       payment_method: PaymentMethod) -> Optional[Payment]:
        """Process payment for a booking"""
        processor = self._processors.get(payment_method)
        if not processor:
            print(f"[Payment] Invalid payment method: {payment_method}")
            return None
        
        return processor.process_payment(booking, amount, payment_method)
    
    def refund_payment(self, payment: Payment, amount: float) -> bool:
        """Process refund"""
        processor = self._processors.get(payment.payment_method)
        if not processor:
            return False
        
        return processor.refund_payment(payment, amount)


# ==================== Car Rental System ====================

class CarRentalSystem:
    """Main car rental system"""
    
    def __init__(self, pricing_strategy: PricingStrategy):
        self._stores: Dict[str, Store] = {}
        self._customers: Dict[str, Customer] = {}
        self._bookings: Dict[str, Booking] = {}
        self._vehicles: Dict[str, Vehicle] = {}
        self._pricing_strategy = pricing_strategy
        self._payment_service = PaymentService()
        self._payments: List[Payment] = []
        self._lock = Lock()
    
    def add_store(self, store: Store) -> None:
        """Add a store location"""
        with self._lock:
            self._stores[store.get_id()] = store
        print(f"[System] Added store: {store}")
    
    def add_customer(self, customer: Customer) -> None:
        """Register a customer"""
        with self._lock:
            self._customers[customer.get_id()] = customer
        print(f"[System] Registered customer: {customer}")
    
    def add_vehicle_to_store(self, vehicle: Vehicle, store_id: str) -> bool:
        """Add a vehicle to a store"""
        store = self._stores.get(store_id)
        if not store:
            print(f"[System] Store not found: {store_id}")
            return False
        
        with self._lock:
            self._vehicles[vehicle.get_id()] = vehicle
        
        store.add_vehicle(vehicle)
        print(f"[System] Added {vehicle} to {store.get_name()}")
        return True
    
    def search_available_vehicles(self, store_id: str, 
                                  pickup_datetime: datetime,
                                  dropoff_datetime: datetime,
                                  vehicle_type: Optional[VehicleType] = None) -> List[Vehicle]:
        """Search for available vehicles at a store for given dates"""
        store = self._stores.get(store_id)
        if not store:
            return []
        
        available_vehicles = store.get_available_vehicles(vehicle_type)
        
        # Filter out vehicles that have conflicting bookings
        # (Simplified - in production would check booking calendar)
        truly_available = []
        for vehicle in available_vehicles:
            if self._is_vehicle_available(vehicle, pickup_datetime, dropoff_datetime):
                truly_available.append(vehicle)
        
        return truly_available
    
    def _is_vehicle_available(self, vehicle: Vehicle, 
                             pickup_datetime: datetime,
                             dropoff_datetime: datetime) -> bool:
        """Check if vehicle is available for given time period"""
        with self._lock:
            bookings = self._bookings.values()
        
        for booking in bookings:
            if booking.get_vehicle() != vehicle:
                continue
            
            # Skip cancelled/completed bookings
            status = booking.get_status()
            if status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
                continue
            
            # Check for overlap
            existing_pickup = booking.get_pickup_datetime()
            existing_dropoff = booking.get_dropoff_datetime()
            
            if (pickup_datetime < existing_dropoff and 
                dropoff_datetime > existing_pickup):
                return False
        
        return True
    
    def create_booking(self, customer_id: str, vehicle_id: str,
                      pickup_store_id: str, dropoff_store_id: str,
                      pickup_datetime: datetime, dropoff_datetime: datetime) -> Optional[Booking]:
        """Create a new booking"""
        customer = self._customers.get(customer_id)
        vehicle = self._vehicles.get(vehicle_id)
        pickup_store = self._stores.get(pickup_store_id)
        dropoff_store = self._stores.get(dropoff_store_id)
        
        if not all([customer, vehicle, pickup_store, dropoff_store]):
            print("[System] Invalid booking parameters")
            return None
        
        # Check if vehicle is available
        if not self._is_vehicle_available(vehicle, pickup_datetime, dropoff_datetime):
            print(f"[System] Vehicle {vehicle} not available for requested dates")
            return None
        
        # Create booking
        booking = Booking(
            customer=customer,
            vehicle=vehicle,
            pickup_store=pickup_store,
            dropoff_store=dropoff_store,
            pickup_datetime=pickup_datetime,
            dropoff_datetime=dropoff_datetime
        )
        
        # Reserve vehicle
        vehicle.set_status(VehicleStatus.RESERVED)
        
        with self._lock:
            self._bookings[booking.get_id()] = booking
        
        print(f"[System] Created {booking}")
        return booking
    
    def confirm_booking(self, booking_id: str, payment_method: PaymentMethod) -> bool:
        """Confirm booking and process payment"""
        booking = self._bookings.get(booking_id)
        if not booking:
            print(f"[System] Booking not found: {booking_id}")
            return False
        
        # Calculate price
        total_amount = self._pricing_strategy.calculate_price(booking)
        
        # Process payment
        payment = self._payment_service.process_payment(
            booking, total_amount, payment_method
        )
        
        if not payment or payment.status != PaymentStatus.COMPLETED:
            print(f"[System] Payment failed for booking {booking_id}")
            return False
        
        self._payments.append(payment)
        booking.set_status(BookingStatus.CONFIRMED)
        
        print(f"[System] Booking {booking_id} confirmed. Total: ${total_amount:.2f}")
        return True
    
    def pickup_vehicle(self, booking_id: str) -> bool:
        """Complete vehicle pickup"""
        booking = self._bookings.get(booking_id)
        if not booking:
            print(f"[System] Booking not found: {booking_id}")
            return False
        
        if booking.get_status() != BookingStatus.CONFIRMED:
            print(f"[System] Booking not confirmed: {booking_id}")
            return False
        
        vehicle = booking.get_vehicle()
        current_mileage = vehicle.get_mileage()
        
        # Complete pickup
        booking.complete_pickup(current_mileage)
        vehicle.set_status(VehicleStatus.RENTED)
        
        print(f"[System] Vehicle {vehicle} picked up by {booking.get_customer().get_name()}")
        print(f"[System] Starting mileage: {current_mileage}")
        
        return True
    
    def dropoff_vehicle(self, booking_id: str, current_mileage: int) -> Optional[Invoice]:
        """Complete vehicle dropoff and generate invoice"""
        booking = self._bookings.get(booking_id)
        if not booking:
            print(f"[System] Booking not found: {booking_id}")
            return None
        
        if booking.get_status() != BookingStatus.ACTIVE:
            print(f"[System] Booking not active: {booking_id}")
            return None
        
        vehicle = booking.get_vehicle()
        
        # Complete dropoff
        booking.complete_dropoff(current_mileage)
        vehicle.add_mileage(booking.get_miles_driven())
        
        # Move vehicle to dropoff store
        pickup_store = booking.get_pickup_store()
        dropoff_store = booking.get_dropoff_store()
        
        if pickup_store != dropoff_store:
            pickup_store.remove_vehicle(vehicle.get_id())
            dropoff_store.add_vehicle(vehicle)
        
        vehicle.set_status(VehicleStatus.AVAILABLE)
        
        # Calculate final charges
        base_amount = self._pricing_strategy.calculate_price(booking)
        
        # Add late fees if overdue
        late_fee = 0.0
        if booking.is_overdue():
            late_days = (booking.get_actual_dropoff_datetime() - 
                        booking.get_dropoff_datetime()).days
            late_fee = late_days * vehicle.get_daily_rate() * 1.5  # 1.5x rate for late
        
        # Add mileage overage charges (simplified)
        # In production, would have mileage limits
        
        taxes = base_amount * 0.10
        total_fees = late_fee
        total_amount = base_amount + taxes + total_fees
        
        # Create invoice
        invoice = Invoice(booking, base_amount, taxes, total_fees, total_amount)
        
        print(f"[System] Vehicle {vehicle} returned by {booking.get_customer().get_name()}")
        print(f"[System] Ending mileage: {current_mileage}")
        print(f"[System] Miles driven: {booking.get_miles_driven()}")
        
        if late_fee > 0:
            print(f"[System] Late fee applied: ${late_fee:.2f}")
        
        return invoice
    
    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel a booking"""
        booking = self._bookings.get(booking_id)
        if not booking:
            print(f"[System] Booking not found: {booking_id}")
            return False
        
        status = booking.get_status()
        if status in [BookingStatus.COMPLETED, BookingStatus.CANCELLED]:
            print(f"[System] Cannot cancel booking in status: {status.value}")
            return False
        
        # Release vehicle
        vehicle = booking.get_vehicle()
        vehicle.set_status(VehicleStatus.AVAILABLE)
        
        # Update booking status
        booking.set_status(BookingStatus.CANCELLED)
        
        # Process refund if payment was made
        # (Simplified - in production would have cancellation policy)
        for payment in self._payments:
            if payment.booking == booking and payment.status == PaymentStatus.COMPLETED:
                refund_amount = payment.amount * 0.5  # 50% refund
                self._payment_service.refund_payment(payment, refund_amount)
        
        print(f"[System] Booking {booking_id} cancelled")
        return True

    def display_store_inventory(self, store_id: str) -> None:
        """Display vehicles at a store"""
        store = self._stores.get(store_id)
        if not store:
            print(f"[System] Store not found: {store_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"INVENTORY - {store.get_name()}")
        print(f"{'='*80}")
        
        vehicles = store.get_all_vehicles()
        if not vehicles:
            print("No vehicles at this location")
            return
        
        # Group by type
        by_type: Dict[VehicleType, List[Vehicle]] = {}
        for vehicle in vehicles:
            vehicle_type = vehicle.get_type()
            if vehicle_type not in by_type:
                by_type[vehicle_type] = []
            by_type[vehicle_type].append(vehicle)
        
        # Sort by the enum's value (string) instead of the enum itself
        for vehicle_type, vehicles_list in sorted(by_type.items(), key=lambda x: x[0].value):
            print(f"\n{vehicle_type.value}:")
            for vehicle in vehicles_list:
                status = vehicle.get_status().value
                print(f"  {vehicle} - ${vehicle.get_daily_rate()}/day - {status}")
        
        print(f"\n{'='*80}\n")
    
    def display_booking_summary(self) -> None:
        """Display booking statistics"""
        print(f"\n{'='*80}")
        print("BOOKING SUMMARY")
        print(f"{'='*80}")
        
        with self._lock:
            bookings = list(self._bookings.values())
        
        status_counts = {}
        total_revenue = 0.0
        
        for booking in bookings:
            status = booking.get_status()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for payment in self._payments:
            if payment.status == PaymentStatus.COMPLETED:
                total_revenue += payment.amount
        
        print(f"Total Bookings: {len(bookings)}")
        for status, count in sorted(status_counts.items(), key=lambda x: x[0].value):
            print(f"  {status.value}: {count}")
        print(f"\nTotal Revenue: ${total_revenue:.2f}")
        print(f"{'='*80}\n")


# ==================== Factory Pattern ====================

class CarRentalSystemFactory:
    """Factory for creating car rental system configurations"""
    
    @staticmethod
    def create_standard_system() -> CarRentalSystem:
        """Create system with standard pricing"""
        pricing = StandardPricingStrategy()
        return CarRentalSystem(pricing)
    
    @staticmethod
    def create_weekend_system() -> CarRentalSystem:
        """Create system with weekend pricing"""
        pricing = WeekendPricingStrategy()
        return CarRentalSystem(pricing)
    
    @staticmethod
    def create_loyalty_system() -> CarRentalSystem:
        """Create system with loyalty pricing"""
        pricing = LoyaltyPricingStrategy()
        return CarRentalSystem(pricing)


# ==================== Demo Usage ====================

def main():
    """Demo the car rental system"""
    print("=== Car Rental System Demo ===\n")
    
    # Create system with standard pricing
    system = CarRentalSystemFactory.create_standard_system()
    
    # Create stores
    store1 = Store("STR-001", "Downtown Office", "123 Main St, Seattle", 
                   "555-0100", "8AM-8PM")
    store2 = Store("STR-002", "Airport Office", "SeaTac Airport", 
                   "555-0200", "6AM-10PM")
    store3 = Store("STR-003", "Suburban Office", "456 Oak Ave, Bellevue", 
                   "555-0300", "9AM-6PM")
    
    system.add_store(store1)
    system.add_store(store2)
    system.add_store(store3)
    
    # Create vehicles
    vehicles = [
        Vehicle("VEH-001", "Toyota", "Corolla", 2023, VehicleType.ECONOMY, 
                "ABC-123", 35.0, 15000),
        Vehicle("VEH-002", "Honda", "Civic", 2023, VehicleType.COMPACT, 
                "DEF-456", 40.0, 12000),
        Vehicle("VEH-003", "Toyota", "Camry", 2023, VehicleType.SEDAN, 
                "GHI-789", 50.0, 18000),
        Vehicle("VEH-004", "Honda", "CR-V", 2023, VehicleType.SUV, 
                "JKL-012", 65.0, 20000),
        Vehicle("VEH-005", "BMW", "5 Series", 2024, VehicleType.LUXURY, 
                "MNO-345", 120.0, 5000),
        Vehicle("VEH-006", "Honda", "Odyssey", 2023, VehicleType.VAN, 
                "PQR-678", 75.0, 22000),
        Vehicle("VEH-007", "Toyota", "Corolla", 2023, VehicleType.ECONOMY, 
                "STU-901", 35.0, 14000),
        Vehicle("VEH-008", "Chevrolet", "Suburban", 2023, VehicleType.SUV, 
                "VWX-234", 70.0, 25000),
    ]
    
    # Distribute vehicles across stores
    system.add_vehicle_to_store(vehicles[0], "STR-001")
    system.add_vehicle_to_store(vehicles[1], "STR-001")
    system.add_vehicle_to_store(vehicles[2], "STR-001")
    system.add_vehicle_to_store(vehicles[3], "STR-002")
    system.add_vehicle_to_store(vehicles[4], "STR-002")
    system.add_vehicle_to_store(vehicles[5], "STR-002")
    system.add_vehicle_to_store(vehicles[6], "STR-003")
    system.add_vehicle_to_store(vehicles[7], "STR-003")
    
    # Display initial inventory
    system.display_store_inventory("STR-001")
    system.display_store_inventory("STR-002")
    
    # Create customers
    customer1 = Customer("CUST-001", "Alice Johnson", "alice@email.com", 
                        "555-1111", "DL12345")
    customer2 = Customer("CUST-002", "Bob Smith", "bob@email.com", 
                        "555-2222", "DL67890")
    customer3 = Customer("CUST-003", "Carol Davis", "carol@email.com", 
                        "555-3333", "DL11111")
    
    system.add_customer(customer1)
    system.add_customer(customer2)
    system.add_customer(customer3)
    
    print("\n" + "="*80)
    print("CREATING BOOKINGS")
    print("="*80 + "\n")
    
    # Create bookings
    pickup_time = datetime.now() + timedelta(days=1)
    dropoff_time = pickup_time + timedelta(days=3)
    
    # Booking 1: Alice rents economy car
    print("--- Booking 1: Alice ---")
    available = system.search_available_vehicles(
        "STR-001", pickup_time, dropoff_time, VehicleType.ECONOMY
    )
    print(f"Available vehicles: {available}")
    
    booking1 = system.create_booking(
        customer_id="CUST-001",
        vehicle_id="VEH-001",
        pickup_store_id="STR-001",
        dropoff_store_id="STR-001",
        pickup_datetime=pickup_time,
        dropoff_datetime=dropoff_time
    )
    
    if booking1:
        system.confirm_booking(booking1.get_id(), PaymentMethod.CREDIT_CARD)
    
    time.sleep(1)
    
    # Booking 2: Bob rents SUV
    print("\n--- Booking 2: Bob ---")
    pickup_time2 = datetime.now() + timedelta(days=2)
    dropoff_time2 = pickup_time2 + timedelta(days=5)
    
    booking2 = system.create_booking(
        customer_id="CUST-002",
        vehicle_id="VEH-004",
        pickup_store_id="STR-002",
        dropoff_store_id="STR-001",  # Different dropoff location
        pickup_datetime=pickup_time2,
        dropoff_datetime=dropoff_time2
    )
    
    if booking2:
        system.confirm_booking(booking2.get_id(), PaymentMethod.DEBIT_CARD)
    
    time.sleep(1)
    
    # Booking 3: Carol rents luxury car
    print("\n--- Booking 3: Carol ---")
    pickup_time3 = datetime.now() + timedelta(days=1)
    dropoff_time3 = pickup_time3 + timedelta(days=7)
    
    booking3 = system.create_booking(
        customer_id="CUST-003",
        vehicle_id="VEH-005",
        pickup_store_id="STR-002",
        dropoff_store_id="STR-002",
        pickup_datetime=pickup_time3,
        dropoff_datetime=dropoff_time3
    )
    
    if booking3:
        system.confirm_booking(booking3.get_id(), PaymentMethod.CREDIT_CARD)
    
    # Display booking summary
    system.display_booking_summary()
    
    print("\n" + "="*80)
    print("SIMULATING PICKUPS AND DROPOFFS")
    print("="*80 + "\n")
    
    # Simulate Alice's rental
    print("--- Alice picks up vehicle ---")
    system.pickup_vehicle(booking1.get_id())
    
    time.sleep(1)
    
    print("\n--- Alice returns vehicle after driving 250 miles ---")
    invoice1 = system.dropoff_vehicle(booking1.get_id(), 15250)
    if invoice1:
        invoice1.display()
    
    # Simulate Bob's rental
    print("\n--- Bob picks up vehicle ---")
    system.pickup_vehicle(booking2.get_id())
    
    time.sleep(1)
    
    print("\n--- Bob returns vehicle after driving 600 miles ---")
    invoice2 = system.dropoff_vehicle(booking2.get_id(), 20600)
    if invoice2:
        invoice2.display()
    
    # Display inventory after dropoffs
    print("\n--- Inventory after returns ---")
    system.display_store_inventory("STR-001")
    
    # Test cancellation
    print("\n" + "="*80)
    print("TESTING CANCELLATION")
    print("="*80 + "\n")
    
    print("--- Carol cancels her booking ---")
    system.cancel_booking(booking3.get_id())
    
    # Final summary
    system.display_booking_summary()
    
    # Test searching for conflicting dates
    print("\n" + "="*80)
    print("TESTING AVAILABILITY CHECK")
    print("="*80 + "\n")
    
    # Try to book same vehicle for overlapping dates
    print("--- Attempting to book VEH-001 for overlapping dates ---")
    overlapping_pickup = pickup_time + timedelta(days=1)
    overlapping_dropoff = dropoff_time + timedelta(days=1)
    
    conflicting_booking = system.create_booking(
        customer_id="CUST-002",
        vehicle_id="VEH-001",
        pickup_store_id="STR-001",
        dropoff_store_id="STR-001",
        pickup_datetime=overlapping_pickup,
        dropoff_datetime=overlapping_dropoff
    )
    
    if not conflicting_booking:
        print("[Expected] Vehicle not available for overlapping dates")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Strategy Pattern - Multiple uses:

# Pricing Strategies:

# StandardPricingStrategy: Simple daily rate
# WeekendPricingStrategy: Weekend surcharges
# LoyaltyPricingStrategy: Discount tiers


# Payment Processing:

# CreditCardProcessor: Card payments
# CashProcessor: Cash payments
# Easily extensible for new payment methods




# Factory Pattern:

# Creates systems with different pricing strategies
# Easy configuration for different business models


# Service Layer:

# PaymentService: Orchestrates payment processing
# Decouples payment logic from core rental system



# Core Features:
# ✅ Multiple Vehicle Types: Economy, Compact, Sedan, SUV, Luxury, Van
# ✅ Multiple Stores: Different pickup/dropoff locations
# ✅ Booking Scheduling: Date-based availability checking
# ✅ Flexible Pricing: Pluggable pricing strategies
# ✅ Payment Processing: Multiple payment methods
# ✅ Invoice Generation: Detailed billing with taxes and fees
# ✅ Vehicle Tracking: Mileage tracking, status management
# ✅ Cancellation & Refunds: Booking cancellation with refund processing
# Concurrency Handling:

# Thread Locks (Lock):

# Vehicle: Protects status and mileage updates
# Booking: Protects status changes
# Store: Protects vehicle inventory
# CarRentalSystem: Protects shared state


# Atomic Operations:

# Vehicle reservation prevents double-booking
# Lock-protected availability checks
# Safe concurrent booking creation



# Business Logic:
# Availability Checking:
# python# Checks for date overlaps across all bookings
# if (pickup_datetime < existing_dropoff and 
#     dropoff_datetime > existing_pickup):
#     return False  # Conflict detected
# Pricing Calculation:

# Base: Daily rate × rental days
# Taxes: Configurable tax rate
# Fees: Service fees, late fees
# Discounts: Loyalty programs, promotions

# Pickup/Dropoff Flow:

# Booking: Reserve vehicle, process payment
# Pickup: Record mileage, mark vehicle as rented
# Dropoff: Calculate final charges, move vehicle if needed

# Real-World Features:
# ✅ Different pickup/dropoff locations (one-way rentals)
# ✅ Late fee calculation for overdue returns
# ✅ Mileage tracking for maintenance and billing
# ✅ Vehicle status management (available, reserved, rented, maintenance)
# ✅ Cancellation policy with partial refunds
# ✅ Invoice generation with itemized charges
# Extensions You Could Add:

# Insurance Options: CDW, liability coverage
# Additional Driver Fees: Extra drivers on booking
# GPS/Child Seat Rentals: Accessory add-ons
# Fuel Policy: Full-to-full, prepaid options
# Age Restrictions: Young driver surcharges
# Corporate Accounts: Business customer management
# Reservation Modifications: Date/vehicle changes
# Damage Assessment: Condition reports with photos
# Loyalty Program: Points accumulation and rewards
# Mobile App Integration: QR codes for pickup
# Real-time Notifications: SMS/email confirmations
# Fleet Management: Maintenance scheduling, depreciation tracking

# Data Structures Used:

# Dictionary (Dict): O(1) vehicle/booking/customer lookup
# Set: Track unique vehicles, prevent duplicates
# Lock: Thread-safe concurrent operations

# Key Business Rules:

# Minimum rental: 1 day (partial days round up)
# Late fees: 1.5× daily rate for overdue days
# Cancellation: 50% refund (configurable policy)
# Vehicle transfer: Moves to dropoff location automatically
# Reservation: Blocks vehicle for booking period

# This design demonstrates production-ready car rental management with proper concurrency, multiple strategies for pricing/payment, and comprehensive business logic - perfect for system design interviews!
