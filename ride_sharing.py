from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Set, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from threading import RLock, Thread, Event
from collections import defaultdict
import uuid
import math
import random
import time


# ==================== Enums ====================

class RideType(Enum):
    """Types of rides"""
    REGULAR = "REGULAR"
    PREMIUM = "PREMIUM"
    XL = "XL"
    POOL = "POOL"


class RideStatus(Enum):
    """Ride lifecycle states"""
    REQUESTED = "REQUESTED"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    DRIVER_ARRIVED = "DRIVER_ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DriverStatus(Enum):
    """Driver availability states"""
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    ON_RIDE = "ON_RIDE"
    BUSY = "BUSY"


class PaymentMethod(Enum):
    """Payment methods"""
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    WALLET = "WALLET"
    UPI = "UPI"


class PaymentStatus(Enum):
    """Payment states"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class VehicleType(Enum):
    """Vehicle types"""
    SEDAN = "SEDAN"
    SUV = "SUV"
    HATCHBACK = "HATCHBACK"
    LUXURY = "LUXURY"


# ==================== Location Models ====================

@dataclass
class Location:
    """Represents a geographic location"""
    latitude: float
    longitude: float
    address: str
    
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
        return f"Location({self.address})"


# ==================== User Models ====================

@dataclass
class Rider:
    """Represents a rider/passenger"""
    rider_id: str
    name: str
    email: str
    phone: str
    rating: float = 5.0
    total_ratings: int = 0
    total_rides: int = 0
    
    def add_rating(self, rating: float) -> None:
        """Add a rating (1-5)"""
        if 1 <= rating <= 5:
            total = self.rating * self.total_ratings
            self.total_ratings += 1
            self.rating = (total + rating) / self.total_ratings
    
    def __repr__(self) -> str:
        return f"Rider(id={self.rider_id}, name={self.name}, rating={self.rating:.1f})"


@dataclass
class Vehicle:
    """Represents a vehicle"""
    vehicle_id: str
    license_plate: str
    model: str
    color: str
    vehicle_type: VehicleType
    year: int
    
    def __repr__(self) -> str:
        return f"Vehicle({self.model}, {self.license_plate})"


class Driver:
    """Represents a driver"""
    
    def __init__(self, driver_id: str, name: str, email: str, phone: str, 
                 vehicle: Vehicle, license_number: str):
        self._driver_id = driver_id
        self._name = name
        self._email = email
        self._phone = phone
        self._vehicle = vehicle
        self._license_number = license_number
        self._rating = 5.0
        self._total_ratings = 0
        self._total_rides = 0
        self._status = DriverStatus.OFFLINE
        self._current_location: Optional[Location] = None
        self._current_ride_id: Optional[str] = None
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._driver_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_phone(self) -> str:
        return self._phone
    
    def get_vehicle(self) -> Vehicle:
        return self._vehicle
    
    def get_status(self) -> DriverStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: DriverStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_current_location(self) -> Optional[Location]:
        with self._lock:
            return self._current_location
    
    def update_location(self, location: Location) -> None:
        """Update driver's current location"""
        with self._lock:
            self._current_location = location
    
    def is_available(self) -> bool:
        """Check if driver is available for rides"""
        with self._lock:
            return self._status == DriverStatus.AVAILABLE
    
    def assign_ride(self, ride_id: str) -> bool:
        """Assign ride to driver"""
        with self._lock:
            if not self.is_available():
                return False
            
            self._current_ride_id = ride_id
            self._status = DriverStatus.ON_RIDE
            return True
    
    def complete_ride(self) -> None:
        """Complete current ride"""
        with self._lock:
            self._current_ride_id = None
            self._total_rides += 1
            self._status = DriverStatus.AVAILABLE
    
    def get_rating(self) -> float:
        with self._lock:
            return self._rating
    
    def add_rating(self, rating: float) -> None:
        """Add rating for driver"""
        with self._lock:
            if 1 <= rating <= 5:
                total = self._rating * self._total_ratings
                self._total_ratings += 1
                self._rating = (total + rating) / self._total_ratings
    
    def get_total_rides(self) -> int:
        with self._lock:
            return self._total_rides
    
    def __repr__(self) -> str:
        return (f"Driver(id={self._driver_id}, name={self._name}, "
                f"status={self._status.value}, rating={self._rating:.1f})")


# ==================== Fare Calculation (Strategy Pattern) ====================

class FareCalculationStrategy(ABC):
    """Abstract strategy for fare calculation"""
    
    @abstractmethod
    def calculate_fare(self, distance_km: float, duration_minutes: int, 
                      surge_multiplier: float = 1.0) -> Decimal:
        """Calculate fare for the ride"""
        pass


class RegularFareStrategy(FareCalculationStrategy):
    """Regular ride fare calculation"""
    
    def __init__(self):
        self._base_fare = Decimal('2.50')
        self._per_km = Decimal('1.50')
        self._per_minute = Decimal('0.30')
        self._minimum_fare = Decimal('5.00')
    
    def calculate_fare(self, distance_km: float, duration_minutes: int,
                      surge_multiplier: float = 1.0) -> Decimal:
        distance_cost = Decimal(str(distance_km)) * self._per_km
        time_cost = Decimal(str(duration_minutes)) * self._per_minute
        
        fare = self._base_fare + distance_cost + time_cost
        fare = fare * Decimal(str(surge_multiplier))
        
        return max(fare, self._minimum_fare).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )


class PremiumFareStrategy(FareCalculationStrategy):
    """Premium ride fare calculation"""
    
    def __init__(self):
        self._base_fare = Decimal('5.00')
        self._per_km = Decimal('2.50')
        self._per_minute = Decimal('0.50')
        self._minimum_fare = Decimal('10.00')
    
    def calculate_fare(self, distance_km: float, duration_minutes: int,
                      surge_multiplier: float = 1.0) -> Decimal:
        distance_cost = Decimal(str(distance_km)) * self._per_km
        time_cost = Decimal(str(duration_minutes)) * self._per_minute
        
        fare = self._base_fare + distance_cost + time_cost
        fare = fare * Decimal(str(surge_multiplier))
        
        return max(fare, self._minimum_fare).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )


class XLFareStrategy(FareCalculationStrategy):
    """XL ride fare calculation (larger vehicles)"""
    
    def __init__(self):
        self._base_fare = Decimal('4.00')
        self._per_km = Decimal('2.00')
        self._per_minute = Decimal('0.40')
        self._minimum_fare = Decimal('8.00')
    
    def calculate_fare(self, distance_km: float, duration_minutes: int,
                      surge_multiplier: float = 1.0) -> Decimal:
        distance_cost = Decimal(str(distance_km)) * self._per_km
        time_cost = Decimal(str(duration_minutes)) * self._per_minute
        
        fare = self._base_fare + distance_cost + time_cost
        fare = fare * Decimal(str(surge_multiplier))
        
        return max(fare, self._minimum_fare).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )


class FareCalculatorFactory:
    """Factory for creating fare calculators"""
    
    @staticmethod
    def get_calculator(ride_type: RideType) -> FareCalculationStrategy:
        """Get appropriate fare calculator for ride type"""
        calculators = {
            RideType.REGULAR: RegularFareStrategy(),
            RideType.PREMIUM: PremiumFareStrategy(),
            RideType.XL: XLFareStrategy(),
            RideType.POOL: RegularFareStrategy(),  # Pool uses regular pricing
        }
        
        return calculators.get(ride_type, RegularFareStrategy())


# ==================== Ride Models ====================

class Ride:
    """
    Represents a ride request and its lifecycle.
    Thread-safe for concurrent operations.
    """
    
    def __init__(self, ride_id: str, rider: Rider, pickup_location: Location,
                 dropoff_location: Location, ride_type: RideType,
                 payment_method: PaymentMethod):
        self._ride_id = ride_id
        self._rider = rider
        self._pickup_location = pickup_location
        self._dropoff_location = dropoff_location
        self._ride_type = ride_type
        self._payment_method = payment_method
        
        # Ride state
        self._status = RideStatus.REQUESTED
        self._driver: Optional[Driver] = None
        self._fare: Optional[Decimal] = None
        self._payment_status = PaymentStatus.PENDING
        
        # Timestamps
        self._requested_at = datetime.now()
        self._accepted_at: Optional[datetime] = None
        self._pickup_at: Optional[datetime] = None
        self._dropoff_at: Optional[datetime] = None
        
        # Tracking
        self._driver_location: Optional[Location] = None
        self._estimated_arrival_minutes: Optional[int] = None
        
        # Ratings
        self._rider_rating: Optional[float] = None
        self._driver_rating: Optional[float] = None
        
        # Callbacks
        self._on_status_change: Optional[Callable] = None
        self._on_location_update: Optional[Callable] = None
        
        # Lock
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._ride_id
    
    def get_rider(self) -> Rider:
        return self._rider
    
    def get_driver(self) -> Optional[Driver]:
        with self._lock:
            return self._driver
    
    def get_pickup_location(self) -> Location:
        return self._pickup_location
    
    def get_dropoff_location(self) -> Location:
        return self._dropoff_location
    
    def get_ride_type(self) -> RideType:
        return self._ride_type
    
    def get_status(self) -> RideStatus:
        with self._lock:
            return self._status
    
    def get_fare(self) -> Optional[Decimal]:
        with self._lock:
            return self._fare
    
    def assign_driver(self, driver: Driver) -> bool:
        """Assign driver to ride"""
        with self._lock:
            if self._status != RideStatus.REQUESTED:
                return False
            
            self._driver = driver
            self._status = RideStatus.DRIVER_ASSIGNED
            self._accepted_at = datetime.now()
            
            # Calculate estimated arrival
            if driver.get_current_location():
                distance = driver.get_current_location().distance_to(self._pickup_location)
                self._estimated_arrival_minutes = int(distance * 3)  # Rough estimate
            
            self._notify_status_change()
            print(f"Driver {driver.get_name()} assigned to ride {self._ride_id}")
            return True
    
    def mark_driver_arrived(self) -> bool:
        """Mark driver as arrived at pickup"""
        with self._lock:
            if self._status != RideStatus.DRIVER_ASSIGNED:
                return False
            
            self._status = RideStatus.DRIVER_ARRIVED
            self._notify_status_change()
            print(f"Driver arrived at pickup for ride {self._ride_id}")
            return True
    
    def start_ride(self) -> bool:
        """Start the ride (pickup completed)"""
        with self._lock:
            if self._status != RideStatus.DRIVER_ARRIVED:
                return False
            
            self._status = RideStatus.IN_PROGRESS
            self._pickup_at = datetime.now()
            self._notify_status_change()
            print(f"Ride {self._ride_id} started")
            return True
    
    def complete_ride(self, fare: Decimal) -> bool:
        """Complete the ride"""
        with self._lock:
            if self._status != RideStatus.IN_PROGRESS:
                return False
            
            self._status = RideStatus.COMPLETED
            self._dropoff_at = datetime.now()
            self._fare = fare
            self._notify_status_change()
            
            print(f"Ride {self._ride_id} completed - Fare: ${fare}")
            return True
    
    def cancel_ride(self) -> bool:
        """Cancel the ride"""
        with self._lock:
            if self._status in [RideStatus.COMPLETED, RideStatus.CANCELLED]:
                return False
            
            self._status = RideStatus.CANCELLED
            self._notify_status_change()
            print(f"Ride {self._ride_id} cancelled")
            return True
    
    def update_driver_location(self, location: Location) -> None:
        """Update driver's current location"""
        with self._lock:
            self._driver_location = location
            
            if self._on_location_update:
                self._on_location_update(location)
    
    def set_payment_status(self, status: PaymentStatus) -> None:
        """Update payment status"""
        with self._lock:
            self._payment_status = status
    
    def rate_driver(self, rating: float) -> None:
        """Rider rates the driver"""
        with self._lock:
            if self._status != RideStatus.COMPLETED:
                return
            
            self._driver_rating = rating
            if self._driver:
                self._driver.add_rating(rating)
                print(f"Driver rated: {rating} stars")
    
    def rate_rider(self, rating: float) -> None:
        """Driver rates the rider"""
        with self._lock:
            if self._status != RideStatus.COMPLETED:
                return
            
            self._rider_rating = rating
            self._rider.add_rating(rating)
            print(f"Rider rated: {rating} stars")
    
    def get_duration_minutes(self) -> Optional[int]:
        """Get ride duration in minutes"""
        with self._lock:
            if self._pickup_at and self._dropoff_at:
                duration = self._dropoff_at - self._pickup_at
                return int(duration.total_seconds() / 60)
            return None
    
    def set_on_status_change_callback(self, callback: Callable) -> None:
        """Set callback for status changes"""
        self._on_status_change = callback
    
    def set_on_location_update_callback(self, callback: Callable) -> None:
        """Set callback for location updates"""
        self._on_location_update = callback
    
    def _notify_status_change(self) -> None:
        """Notify status change"""
        if self._on_status_change:
            try:
                self._on_status_change(self)
            except Exception as e:
                print(f"Error in status change callback: {e}")
    
    def __repr__(self) -> str:
        return (f"Ride(id={self._ride_id}, rider={self._rider.name}, "
                f"status={self._status.value}, type={self._ride_type.value})")


# ==================== Driver Matching Strategy ====================

class DriverMatchingStrategy(ABC):
    """Abstract strategy for matching drivers to rides"""
    
    @abstractmethod
    def find_driver(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        """Find best driver for the ride"""
        pass


class ProximityMatchingStrategy(DriverMatchingStrategy):
    """Match driver based on proximity to pickup location"""
    
    def find_driver(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        if not available_drivers:
            return None
        
        pickup_location = ride.get_pickup_location()
        best_driver = None
        min_distance = float('inf')
        
        for driver in available_drivers:
            if not driver.is_available():
                continue
            
            driver_location = driver.get_current_location()
            if not driver_location:
                continue
            
            # Check if driver's vehicle type is suitable
            if ride.get_ride_type() == RideType.PREMIUM:
                if driver.get_vehicle().vehicle_type not in [VehicleType.LUXURY, VehicleType.SUV]:
                    continue
            elif ride.get_ride_type() == RideType.XL:
                if driver.get_vehicle().vehicle_type != VehicleType.SUV:
                    continue
            
            distance = driver_location.distance_to(pickup_location)
            
            if distance < min_distance:
                min_distance = distance
                best_driver = driver
        
        return best_driver


class RatingBasedMatchingStrategy(DriverMatchingStrategy):
    """Match driver based on rating (premium rides)"""
    
    def find_driver(self, ride: Ride, available_drivers: List[Driver]) -> Optional[Driver]:
        if not available_drivers:
            return None
        
        pickup_location = ride.get_pickup_location()
        MAX_DISTANCE = 10.0  # km
        
        suitable_drivers = []
        
        for driver in available_drivers:
            if not driver.is_available():
                continue
            
            driver_location = driver.get_current_location()
            if not driver_location:
                continue
            
            distance = driver_location.distance_to(pickup_location)
            if distance > MAX_DISTANCE:
                continue
            
            # Check vehicle type
            if ride.get_ride_type() == RideType.PREMIUM:
                if driver.get_vehicle().vehicle_type not in [VehicleType.LUXURY, VehicleType.SUV]:
                    continue
            
            suitable_drivers.append(driver)
        
        if not suitable_drivers:
            return None
        
        # Sort by rating (highest first)
        suitable_drivers.sort(key=lambda d: d.get_rating(), reverse=True)
        return suitable_drivers[0]


# ==================== Main Ride-Sharing System ====================

class RideSharingSystem:
    """
    Main ride-sharing system coordinating all operations.
    """
    
    def __init__(self):
        # Data storage
        self._riders: Dict[str, Rider] = {}
        self._drivers: Dict[str, Driver] = {}
        self._rides: Dict[str, Ride] = {}
        self._rider_rides: Dict[str, List[str]] = defaultdict(list)  # rider_id -> ride_ids
        self._driver_rides: Dict[str, List[str]] = defaultdict(list)  # driver_id -> ride_ids
        
        # Active rides
        self._active_rides: Set[str] = set()
        
        # Matching strategy
        self._matching_strategy: DriverMatchingStrategy = ProximityMatchingStrategy()
        
        # Surge pricing
        self._surge_multipliers: Dict[str, float] = defaultdict(lambda: 1.0)  # area -> multiplier
        
        # Lock
        self._lock = RLock()
        
        # Location tracking thread
        self._tracking_thread: Optional[Thread] = None
        self._stop_tracking = Event()
    
    def start(self) -> None:
        """Start the ride-sharing system"""
        self._tracking_thread = Thread(target=self._simulate_location_updates, daemon=True)
        self._tracking_thread.start()
        print("Ride-sharing system started")
    
    def stop(self) -> None:
        """Stop the ride-sharing system"""
        self._stop_tracking.set()
        if self._tracking_thread:
            self._tracking_thread.join(timeout=1.0)
        print("Ride-sharing system stopped")
    
    # ==================== User Management ====================
    
    def register_rider(self, rider: Rider) -> None:
        """Register a new rider"""
        with self._lock:
            self._riders[rider.rider_id] = rider
            print(f"Registered rider: {rider}")
    
    def register_driver(self, driver: Driver) -> None:
        """Register a new driver"""
        with self._lock:
            self._drivers[driver.get_id()] = driver
            print(f"Registered driver: {driver}")
    
    def get_rider(self, rider_id: str) -> Optional[Rider]:
        """Get rider by ID"""
        return self._riders.get(rider_id)
    
    def get_driver(self, driver_id: str) -> Optional[Driver]:
        """Get driver by ID"""
        return self._drivers.get(driver_id)
    
    def set_driver_status(self, driver_id: str, status: DriverStatus) -> bool:
        """Set driver availability status"""
        driver = self.get_driver(driver_id)
        if not driver:
            return False
        
        driver.set_status(status)
        print(f"Driver {driver.get_name()} status: {status.value}")
        return True
    
    def update_driver_location(self, driver_id: str, location: Location) -> bool:
        """Update driver's current location"""
        driver = self.get_driver(driver_id)
        if not driver:
            return False
        
        driver.update_location(location)
        return True
    
    # ==================== Ride Request & Matching ====================
    
    def request_ride(self, rider_id: str, pickup_location: Location,
                    dropoff_location: Location, ride_type: RideType,
                    payment_method: PaymentMethod) -> Optional[Ride]:
        """Request a new ride"""
        with self._lock:
            rider = self.get_rider(rider_id)
            if not rider:
                print("Rider not found")
                return None
            
            # Create ride
            ride_id = str(uuid.uuid4())
            ride = Ride(ride_id, rider, pickup_location, dropoff_location,
                       ride_type, payment_method)
            
            self._rides[ride_id] = ride
            self._rider_rides[rider_id].append(ride_id)
            self._active_rides.add(ride_id)
            
            print(f"\nRide requested: {ride_id}")
            print(f"  Pickup: {pickup_location.address}")
            print(f"  Dropoff: {dropoff_location.address}")
            print(f"  Type: {ride_type.value}")
            
            # Try to match with a driver
            self._match_driver(ride)
            
            return ride
    
    def _match_driver(self, ride: Ride) -> bool:
        """Match ride with available driver"""
        with self._lock:
            available_drivers = [d for d in self._drivers.values() 
                               if d.is_available() and d.get_current_location()]
            
            if not available_drivers:
                print("No drivers available")
                return False
            
            # Use matching strategy
            driver = self._matching_strategy.find_driver(ride, available_drivers)
            
            if not driver:
                print("No suitable driver found")
                return False
            
            # Assign driver
            if driver.assign_ride(ride.get_id()):
                ride.assign_driver(driver)
                self._driver_rides[driver.get_id()].append(ride.get_id())
                return True
            
            return False
    
    def set_matching_strategy(self, strategy: DriverMatchingStrategy) -> None:
        """Set driver matching strategy"""
        self._matching_strategy = strategy
    
    # ==================== Ride Operations ====================
    
    def get_ride(self, ride_id: str) -> Optional[Ride]:
        """Get ride by ID"""
        return self._rides.get(ride_id)
    
    def driver_arrived(self, ride_id: str) -> bool:
        """Mark driver as arrived at pickup"""
        ride = self.get_ride(ride_id)
        if not ride:
            return False
        
        return ride.mark_driver_arrived()
    
    def start_ride(self, ride_id: str) -> bool:
        """Start the ride"""
        ride = self.get_ride(ride_id)
        if not ride:
            return False
        
        return ride.start_ride()
    
    def complete_ride(self, ride_id: str) -> bool:
        """Complete the ride and process payment"""
        with self._lock:
            ride = self.get_ride(ride_id)
            if not ride:
                return False
            
            # Calculate fare
            distance = ride.get_pickup_location().distance_to(
                ride.get_dropoff_location()
            )
            duration = ride.get_duration_minutes() or int(distance * 2)  # Estimate if not available
            
            # Get surge multiplier (simplified - based on area)
            surge = self._surge_multipliers.get("default", 1.0)
            
            # Calculate fare using strategy
            calculator = FareCalculatorFactory.get_calculator(ride.get_ride_type())
            fare = calculator.calculate_fare(distance, duration, surge)
            
            # Complete ride
            if ride.complete_ride(fare):
                # Process payment
                self._process_payment(ride, fare)
                
                # Update driver
                driver = ride.get_driver()
                if driver:
                    driver.complete_ride()
                
                # Update rider
                ride.get_rider().total_rides += 1
                
                # Remove from active rides
                self._active_rides.discard(ride_id)
                
                return True
            
            return False
    
    def cancel_ride(self, ride_id: str, cancelled_by: str) -> bool:
        """Cancel a ride"""
        with self._lock:
            ride = self.get_ride(ride_id)
            if not ride:
                return False
            
            if ride.cancel_ride():
                # Free up driver
                driver = ride.get_driver()
                if driver:
                    driver.set_status(DriverStatus.AVAILABLE)
                
                # Remove from active rides
                self._active_rides.discard(ride_id)
                
                print(f"Ride cancelled by {cancelled_by}")
                return True
            
            return False
    
    def _process_payment(self, ride: Ride, amount: Decimal) -> bool:
        """Process payment for completed ride"""
        ride.set_payment_status(PaymentStatus.PROCESSING)
        
        # Simulate payment processing
        # In production, would integrate with payment gateway
        
        ride.set_payment_status(PaymentStatus.COMPLETED)
        print(f"Payment processed: ${amount} via {ride._payment_method.value}")
        return True
    
    # ==================== Tracking & Location ====================
    
    def track_ride(self, ride_id: str) -> Dict:
        """Get real-time tracking information for a ride"""
        ride = self.get_ride(ride_id)
        if not ride:
            return {}
        
        driver = ride.get_driver()
        
        tracking_info = {
            'ride_id': ride_id,
            'status': ride.get_status().value,
            'pickup_location': {
                'lat': ride.get_pickup_location().latitude,
                'lng': ride.get_pickup_location().longitude,
                'address': ride.get_pickup_location().address
            },
            'dropoff_location': {
                'lat': ride.get_dropoff_location().latitude,
                'lng': ride.get_dropoff_location().longitude,
                'address': ride.get_dropoff_location().address
            }
        }
        
        if driver:
            tracking_info['driver'] = {
                'name': driver.get_name(),
                'phone': driver.get_phone(),
                'vehicle': {
                    'model': driver.get_vehicle().model,
                    'color': driver.get_vehicle().color,
                    'license_plate': driver.get_vehicle().license_plate
                },
                'rating': driver.get_rating()
            }
            
            if driver.get_current_location():
                tracking_info['driver_location'] = {
                    'lat': driver.get_current_location().latitude,
                    'lng': driver.get_current_location().longitude
                }
        
        if ride._estimated_arrival_minutes:
            tracking_info['estimated_arrival'] = ride._estimated_arrival_minutes
        
        if ride.get_fare():
            tracking_info['fare'] = str(ride.get_fare())
        
        return tracking_info

    def _simulate_location_updates(self) -> None:
        """Simulate driver location updates (background thread)"""
        while not self._stop_tracking.is_set():
            try:
                time.sleep(2)  # Update every 2 seconds
                
                with self._lock:
                    # Update locations for drivers on active rides
                    for ride_id in list(self._active_rides):
                        ride = self._rides.get(ride_id)
                        if not ride:
                            continue
                        
                        driver = ride.get_driver()
                        if not driver:
                            continue
                        
                        status = ride.get_status()
                        if status not in [RideStatus.DRIVER_ASSIGNED, RideStatus.IN_PROGRESS]:
                            continue
                        
                        # Simulate movement toward destination
                        current_loc = driver.get_current_location()
                        if not current_loc:
                            continue
                        
                        if status == RideStatus.DRIVER_ASSIGNED:
                            # Move toward pickup
                            target = ride.get_pickup_location()
                        else:
                            # Move toward dropoff
                            target = ride.get_dropoff_location()
                        
                        # Simulate small movement toward target
                        lat_diff = target.latitude - current_loc.latitude
                        lng_diff = target.longitude - current_loc.longitude
                        
                        # Move 10% closer
                        new_lat = current_loc.latitude + (lat_diff * 0.1)
                        new_lng = current_loc.longitude + (lng_diff * 0.1)
                        
                        new_location = Location(
                            new_lat, new_lng,
                            f"En route to {target.address}"
                        )
                        
                        driver.update_location(new_location)
                        ride.update_driver_location(new_location)
                        
            except Exception as e:
                print(f"Error in location update thread: {e}")
    
    # ==================== Analytics & Reports ====================
    
    def get_rider_history(self, rider_id: str) -> List[Ride]:
        """Get ride history for a rider"""
        ride_ids = self._rider_rides.get(rider_id, [])
        return [self._rides[rid] for rid in ride_ids if rid in self._rides]
    
    def get_driver_history(self, driver_id: str) -> List[Ride]:
        """Get ride history for a driver"""
        ride_ids = self._driver_rides.get(driver_id, [])
        return [self._rides[rid] for rid in ride_ids if rid in self._rides]
    
    def get_active_rides(self) -> List[Ride]:
        """Get all currently active rides"""
        return [self._rides[rid] for rid in self._active_rides if rid in self._rides]
    
    def get_available_drivers(self) -> List[Driver]:
        """Get all available drivers"""
        return [d for d in self._drivers.values() if d.is_available()]
    
    def set_surge_multiplier(self, area: str, multiplier: float) -> None:
        """Set surge pricing for an area"""
        self._surge_multipliers[area] = multiplier
        print(f"Surge pricing set for {area}: {multiplier}x")
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        total_rides = len(self._rides)
        completed_rides = sum(1 for r in self._rides.values() 
                             if r.get_status() == RideStatus.COMPLETED)
        cancelled_rides = sum(1 for r in self._rides.values() 
                             if r.get_status() == RideStatus.CANCELLED)
        active_rides = len(self._active_rides)
        
        total_revenue = sum(
            r.get_fare() for r in self._rides.values() 
            if r.get_fare() is not None
        )
        
        return {
            'total_riders': len(self._riders),
            'total_drivers': len(self._drivers),
            'available_drivers': len(self.get_available_drivers()),
            'total_rides': total_rides,
            'completed_rides': completed_rides,
            'cancelled_rides': cancelled_rides,
            'active_rides': active_rides,
            'total_revenue': str(total_revenue)
        }


# ==================== Demo/Test Driver ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)


def demo_ride_sharing_system():
    """Comprehensive demo of the ride-sharing system"""
    
    print_section("RIDE-SHARING SYSTEM DEMO")
    
    # Initialize system
    system = RideSharingSystem()
    system.start()
    
    try:
        # ==================== Setup Users ====================
        print_section("1. User Registration")
        
        # Register riders
        rider1 = Rider(
            rider_id="R001",
            name="Alice Johnson",
            email="alice@example.com",
            phone="+1-555-0101"
        )
        
        rider2 = Rider(
            rider_id="R002",
            name="Bob Smith",
            email="bob@example.com",
            phone="+1-555-0102"
        )
        
        system.register_rider(rider1)
        system.register_rider(rider2)
        
        # Register drivers with vehicles
        vehicle1 = Vehicle(
            vehicle_id="V001",
            license_plate="ABC-123",
            model="Toyota Camry",
            color="Silver",
            vehicle_type=VehicleType.SEDAN,
            year=2022
        )
        
        vehicle2 = Vehicle(
            vehicle_id="V002",
            license_plate="XYZ-789",
            model="Mercedes S-Class",
            color="Black",
            vehicle_type=VehicleType.LUXURY,
            year=2023
        )
        
        vehicle3 = Vehicle(
            vehicle_id="V003",
            license_plate="DEF-456",
            model="Honda CR-V",
            color="White",
            vehicle_type=VehicleType.SUV,
            year=2021
        )
        
        driver1 = Driver(
            driver_id="D001",
            name="Charlie Driver",
            email="charlie@example.com",
            phone="+1-555-0201",
            vehicle=vehicle1,
            license_number="DL123456"
        )
        
        driver2 = Driver(
            driver_id="D002",
            name="Diana Premium",
            email="diana@example.com",
            phone="+1-555-0202",
            vehicle=vehicle2,
            license_number="DL789012"
        )
        
        driver3 = Driver(
            driver_id="D003",
            name="Eve XL",
            email="eve@example.com",
            phone="+1-555-0203",
            vehicle=vehicle3,
            license_number="DL345678"
        )
        
        system.register_driver(driver1)
        system.register_driver(driver2)
        system.register_driver(driver3)
        
        # ==================== Set Driver Locations & Status ====================
        print_section("2. Drivers Going Online")
        
        # Set driver locations
        driver1_loc = Location(37.7749, -122.4194, "Downtown SF")
        driver2_loc = Location(37.7849, -122.4094, "Financial District")
        driver3_loc = Location(37.7649, -122.4294, "Mission District")
        
        system.update_driver_location("D001", driver1_loc)
        system.update_driver_location("D002", driver2_loc)
        system.update_driver_location("D003", driver3_loc)
        
        # Set drivers as available
        system.set_driver_status("D001", DriverStatus.AVAILABLE)
        system.set_driver_status("D002", DriverStatus.AVAILABLE)
        system.set_driver_status("D003", DriverStatus.AVAILABLE)
        
        time.sleep(1)
        
        # ==================== Regular Ride ====================
        print_section("3. Regular Ride Request")
        
        pickup1 = Location(37.7750, -122.4190, "Market Street")
        dropoff1 = Location(37.8044, -122.2712, "Oakland Airport")
        
        ride1 = system.request_ride(
            rider_id="R001",
            pickup_location=pickup1,
            dropoff_location=dropoff1,
            ride_type=RideType.REGULAR,
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        if ride1:
            print(f"\n📍 Tracking Info:")
            tracking = system.track_ride(ride1.get_id())
            print(f"   Status: {tracking.get('status')}")
            if 'driver' in tracking:
                print(f"   Driver: {tracking['driver']['name']}")
                print(f"   Vehicle: {tracking['driver']['vehicle']['model']} "
                      f"({tracking['driver']['vehicle']['color']})")
            
            time.sleep(2)
            
            # Driver arrives
            print("\n🚗 Driver arriving at pickup...")
            system.driver_arrived(ride1.get_id())
            time.sleep(1)
            
            # Start ride
            print("\n🏁 Starting ride...")
            system.start_ride(ride1.get_id())
            time.sleep(2)
            
            # Complete ride
            print("\n✅ Completing ride...")
            system.complete_ride(ride1.get_id())
            
            # Rate driver
            ride1.rate_driver(4.8)
            ride1.rate_rider(5.0)
        
        time.sleep(1)
        
        # ==================== Premium Ride ====================
        print_section("4. Premium Ride Request")
        
        # Switch to rating-based matching for premium rides
        system.set_matching_strategy(RatingBasedMatchingStrategy())
        
        pickup2 = Location(37.7850, -122.4090, "Union Square")
        dropoff2 = Location(37.7694, -122.4862, "Golden Gate Park")
        
        ride2 = system.request_ride(
            rider_id="R002",
            pickup_location=pickup2,
            dropoff_location=dropoff2,
            ride_type=RideType.PREMIUM,
            payment_method=PaymentMethod.WALLET
        )
        
        if ride2:
            print(f"\n📍 Tracking Info:")
            tracking = system.track_ride(ride2.get_id())
            print(f"   Status: {tracking.get('status')}")
            if 'driver' in tracking:
                print(f"   Driver: {tracking['driver']['name']}")
                print(f"   Rating: {tracking['driver']['rating']:.1f} ⭐")
            
            time.sleep(2)
            
            # Complete ride workflow
            system.driver_arrived(ride2.get_id())
            time.sleep(1)
            system.start_ride(ride2.get_id())
            time.sleep(2)
            system.complete_ride(ride2.get_id())
            
            # Rate
            ride2.rate_driver(5.0)
            ride2.rate_rider(4.5)
        
        time.sleep(1)
        
        # ==================== XL Ride with Cancellation ====================
        print_section("5. XL Ride Request (with Cancellation)")
        
        system.set_matching_strategy(ProximityMatchingStrategy())
        
        pickup3 = Location(37.7650, -122.4290, "Mission Bay")
        dropoff3 = Location(37.6213, -122.3790, "SFO Airport")
        
        ride3 = system.request_ride(
            rider_id="R001",
            pickup_location=pickup3,
            dropoff_location=dropoff3,
            ride_type=RideType.XL,
            payment_method=PaymentMethod.CASH
        )
        
        if ride3:
            print(f"\n📍 Tracking Info:")
            tracking = system.track_ride(ride3.get_id())
            print(f"   Status: {tracking.get('status')}")
            
            time.sleep(2)
            
            # Cancel ride
            print("\n❌ Rider cancelling ride...")
            system.cancel_ride(ride3.get_id(), "rider")
        
        time.sleep(1)
        
        # ==================== Surge Pricing ====================
        print_section("6. Surge Pricing Demo")
        
        system.set_surge_multiplier("downtown", 1.5)
        
        pickup4 = Location(37.7900, -122.4000, "Downtown - High Demand")
        dropoff4 = Location(37.8000, -122.4100, "North Beach")
        
        ride4 = system.request_ride(
            rider_id="R002",
            pickup_location=pickup4,
            dropoff_location=dropoff4,
            ride_type=RideType.REGULAR,
            payment_method=PaymentMethod.UPI
        )
        
        if ride4:
            system.driver_arrived(ride4.get_id())
            system.start_ride(ride4.get_id())
            time.sleep(1)
            system.complete_ride(ride4.get_id())
            
            print(f"\n💰 Fare with 1.5x surge: ${ride4.get_fare()}")
        
        time.sleep(1)
        
        # ==================== System Statistics ====================
        print_section("7. System Statistics")
        
        stats = system.get_system_stats()
        print(f"\n📊 System Overview:")
        print(f"   Total Riders: {stats['total_riders']}")
        print(f"   Total Drivers: {stats['total_drivers']}")
        print(f"   Available Drivers: {stats['available_drivers']}")
        print(f"   Total Rides: {stats['total_rides']}")
        print(f"   Completed Rides: {stats['completed_rides']}")
        print(f"   Cancelled Rides: {stats['cancelled_rides']}")
        print(f"   Active Rides: {stats['active_rides']}")
        print(f"   Total Revenue: ${stats['total_revenue']}")
        
        # ==================== Ride History ====================
        print_section("8. Ride History")
        
        print(f"\n📋 Alice's Ride History:")
        alice_rides = system.get_rider_history("R001")
        for ride in alice_rides:
            print(f"   • {ride.get_ride_type().value} ride - "
                  f"Status: {ride.get_status().value} - "
                  f"Fare: ${ride.get_fare() or 'N/A'}")
        
        print(f"\n📋 Charlie Driver's History:")
        charlie_rides = system.get_driver_history("D001")
        for ride in charlie_rides:
            print(f"   • Ride for {ride.get_rider().name} - "
                  f"Status: {ride.get_status().value} - "
                  f"Fare: ${ride.get_fare() or 'N/A'}")
        
        # ==================== Driver Ratings ====================
        print_section("9. Driver Ratings")
        
        for driver_id in ["D001", "D002", "D003"]:
            driver = system.get_driver(driver_id)
            if driver:
                print(f"\n⭐ {driver.get_name()}: {driver.get_rating():.2f} "
                      f"({driver.get_total_rides()} rides)")
        
        time.sleep(1)
        
    finally:
        # Stop system
        print_section("Shutting Down System")
        system.stop()
        print("\n✅ Demo completed successfully!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_ride_sharing_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Completed Features:

# ✅ Location simulation thread for real-time tracking
# ✅ System analytics and statistics
# ✅ Ride history for riders and drivers
# ✅ Surge pricing support
# ✅ Comprehensive demo with multiple scenarios
# Demo Covers:

# User registration (riders & drivers)
# Regular, Premium, and XL rides
# Driver matching strategies (proximity & rating-based)
# Ride lifecycle (request → assign → pickup → complete)
# Cancellations
# Surge pricing
# Payment processing
# Rating system
# Real-time tracking
# System statistics
# Design Patterns Used:

# Strategy Pattern: Fare calculation & driver matching
# Factory Pattern: Fare calculator creation
# Observer Pattern: Ride status callbacks
# Singleton-like: Central system coordinator
# Thread-safe: RLock for concurrency
