from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from dataclasses import dataclass


# ==================== Enums ====================

class VehicleType(Enum):
    """Types of vehicles"""
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    TRUCK = "TRUCK"
    VAN = "VAN"


class SpotType(Enum):
    """Types of parking spots"""
    COMPACT = "COMPACT"      # Motorcycles, small cars
    REGULAR = "REGULAR"      # Cars, small vans
    LARGE = "LARGE"          # Trucks, large vans
    HANDICAPPED = "HANDICAPPED"  # Any vehicle with permit
    
    def can_fit(self, vehicle_type: VehicleType) -> bool:
        """Check if this spot type can accommodate the vehicle type"""
        fit_mapping = {
            SpotType.COMPACT: [VehicleType.MOTORCYCLE, VehicleType.CAR],
            SpotType.REGULAR: [VehicleType.MOTORCYCLE, VehicleType.CAR, VehicleType.VAN],
            SpotType.LARGE: [VehicleType.MOTORCYCLE, VehicleType.CAR, VehicleType.VAN, VehicleType.TRUCK],
            SpotType.HANDICAPPED: [VehicleType.MOTORCYCLE, VehicleType.CAR, VehicleType.VAN, VehicleType.TRUCK]
        }
        return vehicle_type in fit_mapping[self]


class ParkingTicketStatus(Enum):
    """Status of parking ticket"""
    ACTIVE = "ACTIVE"
    PAID = "PAID"
    LOST = "LOST"


class PaymentStatus(Enum):
    """Status of payment"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


# ==================== Core Models ====================

class Vehicle:
    """Represents a vehicle"""
    
    def __init__(self, license_plate: str, vehicle_type: VehicleType):
        self._license_plate = license_plate
        self._vehicle_type = vehicle_type
    
    def get_license_plate(self) -> str:
        return self._license_plate
    
    def get_type(self) -> VehicleType:
        return self._vehicle_type
    
    def __repr__(self) -> str:
        return f"{self._vehicle_type.value}({self._license_plate})"


class ParkingSpot:
    """Represents a single parking spot"""
    
    def __init__(self, spot_id: str, spot_type: SpotType, floor: int):
        self._spot_id = spot_id
        self._spot_type = spot_type
        self._floor = floor
        self._is_occupied = False
        self._vehicle: Optional[Vehicle] = None
    
    def get_id(self) -> str:
        return self._spot_id
    
    def get_type(self) -> SpotType:
        return self._spot_type
    
    def get_floor(self) -> int:
        return self._floor
    
    def is_occupied(self) -> bool:
        return self._is_occupied
    
    def can_fit_vehicle(self, vehicle: Vehicle) -> bool:
        """Check if this spot can fit the given vehicle"""
        return not self._is_occupied and self._spot_type.can_fit(vehicle.get_type())
    
    def park_vehicle(self, vehicle: Vehicle) -> bool:
        """Park a vehicle in this spot"""
        if not self.can_fit_vehicle(vehicle):
            return False
        
        self._vehicle = vehicle
        self._is_occupied = True
        return True
    
    def remove_vehicle(self) -> Optional[Vehicle]:
        """Remove and return the parked vehicle"""
        vehicle = self._vehicle
        self._vehicle = None
        self._is_occupied = False
        return vehicle
    
    def get_vehicle(self) -> Optional[Vehicle]:
        return self._vehicle
    
    def __repr__(self) -> str:
        status = "OCCUPIED" if self._is_occupied else "AVAILABLE"
        return f"Spot({self._spot_id}, {self._spot_type.value}, Floor {self._floor}, {status})"


class ParkingFloor:
    """Represents a floor in the parking lot"""
    
    def __init__(self, floor_number: int):
        self._floor_number = floor_number
        self._spots: Dict[str, ParkingSpot] = {}
        self._spots_by_type: Dict[SpotType, List[ParkingSpot]] = {
            spot_type: [] for spot_type in SpotType
        }
    
    def get_floor_number(self) -> int:
        return self._floor_number
    
    def add_spot(self, spot: ParkingSpot) -> None:
        """Add a parking spot to this floor"""
        self._spots[spot.get_id()] = spot
        self._spots_by_type[spot.get_type()].append(spot)
    
    def get_spot(self, spot_id: str) -> Optional[ParkingSpot]:
        """Get a specific spot by ID"""
        return self._spots.get(spot_id)
    
    def find_available_spot(self, vehicle: Vehicle) -> Optional[ParkingSpot]:
        """Find an available spot for the vehicle"""
        # Try to find exact match first
        for spot_type in SpotType:
            if spot_type.can_fit(vehicle.get_type()):
                for spot in self._spots_by_type[spot_type]:
                    if spot.can_fit_vehicle(vehicle):
                        return spot
        return None
    
    def get_available_spots_count(self, spot_type: SpotType) -> int:
        """Get count of available spots of a specific type"""
        return sum(1 for spot in self._spots_by_type[spot_type] if not spot.is_occupied())
    
    def get_total_spots_count(self, spot_type: SpotType) -> int:
        """Get total count of spots of a specific type"""
        return len(self._spots_by_type[spot_type])
    
    def display_status(self) -> None:
        """Display floor status"""
        print(f"\nFloor {self._floor_number}:")
        for spot_type in SpotType:
            available = self.get_available_spots_count(spot_type)
            total = self.get_total_spots_count(spot_type)
            print(f"  {spot_type.value}: {available}/{total} available")


class ParkingTicket:
    """Represents a parking ticket issued when vehicle enters"""
    
    _ticket_counter = 0
    
    def __init__(self, vehicle: Vehicle, spot: ParkingSpot, entry_time: datetime):
        ParkingTicket._ticket_counter += 1
        self._ticket_id = f"TICKET-{ParkingTicket._ticket_counter:06d}"
        self._vehicle = vehicle
        self._spot = spot
        self._entry_time = entry_time
        self._exit_time: Optional[datetime] = None
        self._status = ParkingTicketStatus.ACTIVE
    
    def get_id(self) -> str:
        return self._ticket_id
    
    def get_vehicle(self) -> Vehicle:
        return self._vehicle
    
    def get_spot(self) -> ParkingSpot:
        return self._spot
    
    def get_entry_time(self) -> datetime:
        return self._entry_time
    
    def get_exit_time(self) -> Optional[datetime]:
        return self._exit_time
    
    def set_exit_time(self, exit_time: datetime) -> None:
        self._exit_time = exit_time
    
    def get_status(self) -> ParkingTicketStatus:
        return self._status
    
    def mark_as_paid(self) -> None:
        self._status = ParkingTicketStatus.PAID
    
    def mark_as_lost(self) -> None:
        self._status = ParkingTicketStatus.LOST
    
    def get_parking_duration(self) -> timedelta:
        """Get parking duration"""
        end_time = self._exit_time if self._exit_time else datetime.now()
        return end_time - self._entry_time
    
    def __repr__(self) -> str:
        return f"Ticket({self._ticket_id}, {self._vehicle}, {self._spot.get_id()})"


@dataclass
class Payment:
    """Represents a payment transaction"""
    payment_id: str
    ticket: ParkingTicket
    amount: float
    payment_time: datetime
    payment_method: str
    status: PaymentStatus
    
    def __repr__(self) -> str:
        return f"Payment({self.payment_id}, ${self.amount:.2f}, {self.status.value})"


# ==================== Strategy Pattern: Pricing Strategies ====================

class PricingStrategy(ABC):
    """Abstract strategy for calculating parking fees"""
    
    @abstractmethod
    def calculate_fee(self, ticket: ParkingTicket, exit_time: datetime) -> float:
        """Calculate parking fee based on ticket and exit time"""
        pass


class HourlyPricingStrategy(PricingStrategy):
    """Standard hourly pricing"""
    
    def __init__(self, hourly_rate: float = 5.0, daily_max: float = 50.0):
        self._hourly_rate = hourly_rate
        self._daily_max = daily_max
    
    def calculate_fee(self, ticket: ParkingTicket, exit_time: datetime) -> float:
        duration = exit_time - ticket.get_entry_time()
        hours = duration.total_seconds() / 3600
        
        # Round up to nearest hour
        hours_rounded = int(hours) + (1 if hours % 1 > 0 else 0)
        
        # Calculate fee
        fee = hours_rounded * self._hourly_rate
        
        # Apply daily maximum
        days = duration.days + 1
        max_fee = days * self._daily_max
        
        return min(fee, max_fee)


class VehicleTypePricingStrategy(PricingStrategy):
    """Pricing based on vehicle type"""
    
    def __init__(self):
        self._rates = {
            VehicleType.MOTORCYCLE: 2.0,
            VehicleType.CAR: 5.0,
            VehicleType.VAN: 7.0,
            VehicleType.TRUCK: 10.0
        }
        self._daily_max = {
            VehicleType.MOTORCYCLE: 20.0,
            VehicleType.CAR: 50.0,
            VehicleType.VAN: 70.0,
            VehicleType.TRUCK: 100.0
        }
    
    def calculate_fee(self, ticket: ParkingTicket, exit_time: datetime) -> float:
        vehicle_type = ticket.get_vehicle().get_type()
        duration = exit_time - ticket.get_entry_time()
        hours = duration.total_seconds() / 3600
        
        # Round up to nearest hour
        hours_rounded = int(hours) + (1 if hours % 1 > 0 else 0)
        
        # Calculate fee
        hourly_rate = self._rates[vehicle_type]
        fee = hours_rounded * hourly_rate
        
        # Apply daily maximum
        days = duration.days + 1
        max_fee = days * self._daily_max[vehicle_type]
        
        return min(fee, max_fee)


class FlatRatePricingStrategy(PricingStrategy):
    """Flat rate pricing regardless of duration"""
    
    def __init__(self, flat_rate: float = 10.0):
        self._flat_rate = flat_rate
    
    def calculate_fee(self, ticket: ParkingTicket, exit_time: datetime) -> float:
        return self._flat_rate


# ==================== Strategy Pattern: Payment Processing ====================

class PaymentProcessor(ABC):
    """Abstract payment processor"""
    
    @abstractmethod
    def process_payment(self, amount: float, payment_method: str) -> Payment:
        """Process payment and return payment object"""
        pass


class CashPaymentProcessor(PaymentProcessor):
    """Process cash payments"""
    
    _payment_counter = 0
    
    def process_payment(self, amount: float, payment_method: str) -> Payment:
        CashPaymentProcessor._payment_counter += 1
        payment_id = f"CASH-{CashPaymentProcessor._payment_counter:06d}"
        
        # Simulate cash payment processing
        return Payment(
            payment_id=payment_id,
            ticket=None,  # Will be set by caller
            amount=amount,
            payment_time=datetime.now(),
            payment_method="CASH",
            status=PaymentStatus.COMPLETED
        )


class CreditCardPaymentProcessor(PaymentProcessor):
    """Process credit card payments"""
    
    _payment_counter = 0
    
    def process_payment(self, amount: float, payment_method: str) -> Payment:
        CreditCardPaymentProcessor._payment_counter += 1
        payment_id = f"CC-{CreditCardPaymentProcessor._payment_counter:06d}"
        
        # Simulate credit card processing
        # In real system, would integrate with payment gateway
        return Payment(
            payment_id=payment_id,
            ticket=None,  # Will be set by caller
            amount=amount,
            payment_time=datetime.now(),
            payment_method="CREDIT_CARD",
            status=PaymentStatus.COMPLETED
        )


class DigitalWalletPaymentProcessor(PaymentProcessor):
    """Process digital wallet payments"""
    
    _payment_counter = 0
    
    def process_payment(self, amount: float, payment_method: str) -> Payment:
        DigitalWalletPaymentProcessor._payment_counter += 1
        payment_id = f"WALLET-{DigitalWalletPaymentProcessor._payment_counter:06d}"
        
        return Payment(
            payment_id=payment_id,
            ticket=None,  # Will be set by caller
            amount=amount,
            payment_time=datetime.now(),
            payment_method="DIGITAL_WALLET",
            status=PaymentStatus.COMPLETED
        )


class PaymentService:
    """Service to handle payment processing"""
    
    def __init__(self):
        self._processors: Dict[str, PaymentProcessor] = {
            "CASH": CashPaymentProcessor(),
            "CREDIT_CARD": CreditCardPaymentProcessor(),
            "DIGITAL_WALLET": DigitalWalletPaymentProcessor()
        }
    
    def process_payment(self, ticket: ParkingTicket, amount: float, 
                       payment_method: str) -> Optional[Payment]:
        """Process payment for a ticket"""
        processor = self._processors.get(payment_method)
        if not processor:
            print(f"Invalid payment method: {payment_method}")
            return None
        
        payment = processor.process_payment(amount, payment_method)
        payment.ticket = ticket
        
        if payment.status == PaymentStatus.COMPLETED:
            ticket.mark_as_paid()
        
        return payment


# ==================== Strategy Pattern: Spot Assignment Strategies ====================

class SpotAssignmentStrategy(ABC):
    """Abstract strategy for assigning parking spots"""
    
    @abstractmethod
    def find_spot(self, parking_lot: 'ParkingLot', vehicle: Vehicle) -> Optional[ParkingSpot]:
        """Find and return an available spot for the vehicle"""
        pass


class NearestSpotStrategy(SpotAssignmentStrategy):
    """Assign nearest available spot (lowest floor first)"""
    
    def find_spot(self, parking_lot: 'ParkingLot', vehicle: Vehicle) -> Optional[ParkingSpot]:
        for floor in parking_lot.get_floors():
            spot = floor.find_available_spot(vehicle)
            if spot:
                return spot
        return None


class OptimalSpotStrategy(SpotAssignmentStrategy):
    """Assign spot optimally - small vehicles to compact spots, large vehicles to large spots"""
    
    def find_spot(self, parking_lot: 'ParkingLot', vehicle: Vehicle) -> Optional[ParkingSpot]:
        # Determine preferred spot types based on vehicle
        vehicle_type = vehicle.get_type()
        
        if vehicle_type == VehicleType.MOTORCYCLE:
            preferred_order = [SpotType.COMPACT, SpotType.REGULAR, SpotType.LARGE]
        elif vehicle_type == VehicleType.CAR:
            preferred_order = [SpotType.COMPACT, SpotType.REGULAR, SpotType.LARGE]
        elif vehicle_type == VehicleType.VAN:
            preferred_order = [SpotType.REGULAR, SpotType.LARGE]
        else:  # TRUCK
            preferred_order = [SpotType.LARGE]
        
        # Try each spot type in order of preference
        for spot_type in preferred_order:
            for floor in parking_lot.get_floors():
                for spot in floor._spots_by_type[spot_type]:
                    if spot.can_fit_vehicle(vehicle):
                        return spot
        
        return None


# ==================== Main Parking Lot Class ====================

class ParkingLot:
    """Main parking lot system"""
    
    def __init__(self, name: str, pricing_strategy: PricingStrategy,
                 spot_assignment_strategy: SpotAssignmentStrategy):
        self._name = name
        self._floors: List[ParkingFloor] = []
        self._active_tickets: Dict[str, ParkingTicket] = {}  # ticket_id -> ticket
        self._vehicle_to_ticket: Dict[str, ParkingTicket] = {}  # license_plate -> ticket
        self._pricing_strategy = pricing_strategy
        self._spot_assignment_strategy = spot_assignment_strategy
        self._payment_service = PaymentService()
        self._payment_history: List[Payment] = []
    
    def get_name(self) -> str:
        return self._name
    
    def add_floor(self, floor: ParkingFloor) -> None:
        """Add a floor to the parking lot"""
        self._floors.append(floor)
    
    def get_floors(self) -> List[ParkingFloor]:
        return self._floors
    
    def park_vehicle(self, vehicle: Vehicle) -> Optional[ParkingTicket]:
        """Park a vehicle and return a ticket"""
        # Check if vehicle is already parked
        if vehicle.get_license_plate() in self._vehicle_to_ticket:
            print(f"Vehicle {vehicle.get_license_plate()} is already parked!")
            return None
        
        # Find available spot
        spot = self._spot_assignment_strategy.find_spot(self, vehicle)
        
        if not spot:
            print(f"No available spot for {vehicle}")
            return None
        
        # Park vehicle
        spot.park_vehicle(vehicle)
        
        # Create ticket
        ticket = ParkingTicket(vehicle, spot, datetime.now())
        self._active_tickets[ticket.get_id()] = ticket
        self._vehicle_to_ticket[vehicle.get_license_plate()] = ticket
        
        print(f"Vehicle parked successfully!")
        print(f"Ticket: {ticket.get_id()}")
        print(f"Spot: {spot.get_id()} (Floor {spot.get_floor()})")
        
        return ticket
    
    def unpark_vehicle(self, ticket_id: str, payment_method: str) -> bool:
        """Unpark vehicle and process payment"""
        ticket = self._active_tickets.get(ticket_id)
        
        if not ticket:
            print(f"Invalid ticket: {ticket_id}")
            return False
        
        # Set exit time
        exit_time = datetime.now()
        ticket.set_exit_time(exit_time)
        
        # Calculate fee
        fee = self._pricing_strategy.calculate_fee(ticket, exit_time)
        
        print(f"\nParking Fee Calculation:")
        print(f"Duration: {ticket.get_parking_duration()}")
        print(f"Amount Due: ${fee:.2f}")
        
        # Process payment
        payment = self._payment_service.process_payment(ticket, fee, payment_method)
        
        if not payment or payment.status != PaymentStatus.COMPLETED:
            print("Payment failed!")
            return False
        
        self._payment_history.append(payment)
        
        # Remove vehicle from spot
        spot = ticket.get_spot()
        vehicle = spot.remove_vehicle()
        
        # Remove from tracking
        del self._active_tickets[ticket_id]
        if vehicle:
            del self._vehicle_to_ticket[vehicle.get_license_plate()]
        
        print(f"Payment processed: {payment}")
        print(f"Vehicle {vehicle} has exited. Thank you!")
        
        return True
    
    def get_ticket_by_vehicle(self, license_plate: str) -> Optional[ParkingTicket]:
        """Get ticket for a vehicle by license plate"""
        return self._vehicle_to_ticket.get(license_plate)
    
    def display_status(self) -> None:
        """Display parking lot status"""
        print(f"\n{'='*50}")
        print(f"{self._name} - Status")
        print(f"{'='*50}")
        
        for floor in self._floors:
            floor.display_status()
        
        print(f"\nActive Tickets: {len(self._active_tickets)}")
        print(f"Total Revenue: ${sum(p.amount for p in self._payment_history):.2f}")


# ==================== Factory Pattern ====================

class ParkingLotFactory:
    """Factory for creating parking lot configurations"""
    
    @staticmethod
    def create_standard_parking_lot(name: str = "Downtown Parking") -> ParkingLot:
        """Create a standard multi-floor parking lot"""
        pricing = VehicleTypePricingStrategy()
        assignment = OptimalSpotStrategy()
        parking_lot = ParkingLot(name, pricing, assignment)
        
        # Create 3 floors
        for floor_num in range(1, 4):
            floor = ParkingFloor(floor_num)
            
            # Add spots to each floor
            # Floor layout: 10 compact, 20 regular, 5 large, 2 handicapped
            for i in range(10):
                spot = ParkingSpot(f"F{floor_num}-C{i+1}", SpotType.COMPACT, floor_num)
                floor.add_spot(spot)
            
            for i in range(20):
                spot = ParkingSpot(f"F{floor_num}-R{i+1}", SpotType.REGULAR, floor_num)
                floor.add_spot(spot)
            
            for i in range(5):
                spot = ParkingSpot(f"F{floor_num}-L{i+1}", SpotType.LARGE, floor_num)
                floor.add_spot(spot)
            
            for i in range(2):
                spot = ParkingSpot(f"F{floor_num}-H{i+1}", SpotType.HANDICAPPED, floor_num)
                floor.add_spot(spot)
            
            parking_lot.add_floor(floor)
        
        return parking_lot
    
    @staticmethod
    def create_small_parking_lot(name: str = "Small Lot") -> ParkingLot:
        """Create a small single-floor parking lot"""
        pricing = HourlyPricingStrategy(hourly_rate=3.0, daily_max=30.0)
        assignment = NearestSpotStrategy()
        parking_lot = ParkingLot(name, pricing, assignment)
        
        # Single floor
        floor = ParkingFloor(1)
        
        # Add 20 spots
        for i in range(5):
            spot = ParkingSpot(f"F1-C{i+1}", SpotType.COMPACT, 1)
            floor.add_spot(spot)
        
        for i in range(10):
            spot = ParkingSpot(f"F1-R{i+1}", SpotType.REGULAR, 1)
            floor.add_spot(spot)
        
        for i in range(5):
            spot = ParkingSpot(f"F1-L{i+1}", SpotType.LARGE, 1)
            floor.add_spot(spot)
        
        parking_lot.add_floor(floor)
        
        return parking_lot


# ==================== Demo Usage ====================

def main():
    """Demo the parking lot system"""
    print("=== Parking Lot Management System ===\n")
    
    # Create parking lot
    parking_lot = ParkingLotFactory.create_standard_parking_lot("City Center Parking")
    
    # Display initial status
    parking_lot.display_status()
    
    # Create some vehicles
    vehicles = [
        Vehicle("ABC-123", VehicleType.CAR),
        Vehicle("XYZ-789", VehicleType.MOTORCYCLE),
        Vehicle("TRK-456", VehicleType.TRUCK),
        Vehicle("VAN-111", VehicleType.VAN),
        Vehicle("CAR-222", VehicleType.CAR),
    ]
    
    # Park vehicles
    print("\n" + "="*50)
    print("Parking Vehicles")
    print("="*50)
    
    tickets = []
    for vehicle in vehicles:
        print(f"\n--- Parking {vehicle} ---")
        ticket = parking_lot.park_vehicle(vehicle)
        if ticket:
            tickets.append(ticket)
    
    # Display status after parking
    parking_lot.display_status()
    
    # Simulate some time passing
    print("\n" + "="*50)
    print("Simulating 3 hours passing...")
    print("="*50)
    
    # Manually adjust entry times for demo
    for ticket in tickets:
        ticket._entry_time = datetime.now() - timedelta(hours=3)
    
    # Unpark some vehicles
    print("\n" + "="*50)
    print("Unparking Vehicles")
    print("="*50)
    
    if len(tickets) >= 2:
        print(f"\n--- Unparking vehicle with ticket {tickets[0].get_id()} ---")
        parking_lot.unpark_vehicle(tickets[0].get_id(), "CREDIT_CARD")
        
        print(f"\n--- Unparking vehicle with ticket {tickets[1].get_id()} ---")
        parking_lot.unpark_vehicle(tickets[1].get_id(), "CASH")
    
    # Final status
    parking_lot.display_status()


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Strategy Pattern - Multiple uses:

# Pricing Strategies: Hourly, vehicle-based, flat rate
# Payment Processing: Cash, credit card, digital wallet
# Spot Assignment: Nearest available, optimal placement


# Factory Pattern:

# Creates different parking lot configurations
# Standard multi-floor vs small single-floor


# Service Layer:

# PaymentService orchestrates payment processing
# Decouples payment logic from main parking lot



# Core Design Elements:

# Multi-floor Support: ParkingFloor manages spots per floor
# Spot Types: Compact, Regular, Large, Handicapped with fit validation
# Vehicle Types: Motorcycle, Car, Van, Truck
# Ticket System: Tracks entry/exit times, vehicle, and spot
# Fee Calculation: Pluggable pricing strategies
# Payment Processing: Multiple payment methods with status tracking

# Key Data Structures:

# Spot Organization: Dictionary by type for efficient lookup
# Ticket Tracking: Maps for O(1) lookup by ticket ID or license plate
# Payment History: List for audit trail

# Real-world Features:
# ✅ Multiple floors
# ✅ Different spot and vehicle types
# ✅ Flexible pricing strategies
# ✅ Multiple payment methods
# ✅ Ticket-based entry/exit
# ✅ Real-time availability tracking
# ✅ Revenue tracking
# This design is extensible for features like reservations, monthly passes, validation stamps, and more!
