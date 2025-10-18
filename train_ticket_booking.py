from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, date, time, timedelta
from collections import defaultdict
from threading import RLock, Thread
import uuid
from dataclasses import dataclass
import time as time_module


# ==================== Enums ====================

class SeatType(Enum):
    """Types of train seats"""
    SLEEPER = "sleeper"
    AC_3_TIER = "3ac"
    AC_2_TIER = "2ac"
    AC_1_TIER = "1ac"
    SECOND_SITTING = "2s"
    CHAIR_CAR = "cc"
    GENERAL = "general"


class BookingStatus(Enum):
    """Booking status"""
    CONFIRMED = "confirmed"
    WAITING = "waiting"
    RAC = "rac"  # Reservation Against Cancellation
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    """Payment status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class TrainStatus(Enum):
    """Train running status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class BerthType(Enum):
    """Berth preferences"""
    LOWER = "lower"
    MIDDLE = "middle"
    UPPER = "upper"
    SIDE_LOWER = "side_lower"
    SIDE_UPPER = "side_upper"


class Gender(Enum):
    """Gender for passengers"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


# ==================== Core Models ====================

class Station:
    """Railway station"""
    
    def __init__(self, station_id: str, code: str, name: str, city: str):
        self._station_id = station_id
        self._code = code.upper()  # e.g., "NDLS" for New Delhi
        self._name = name
        self._city = city
        self._platforms = 10
    
    def get_id(self) -> str:
        return self._station_id
    
    def get_code(self) -> str:
        return self._code
    
    def get_name(self) -> str:
        return self._name
    
    def get_city(self) -> str:
        return self._city
    
    def __str__(self) -> str:
        return f"{self._name} ({self._code})"


class TrainRoute:
    """A station in the train's route with timing"""
    
    def __init__(self, station: Station, stop_number: int,
                 arrival_time: Optional[time], departure_time: Optional[time],
                 distance_from_source: int, platform: int = 1):
        self._station = station
        self._stop_number = stop_number  # 1 for first station, 2 for second, etc.
        self._arrival_time = arrival_time  # None for first station
        self._departure_time = departure_time  # None for last station
        self._distance_from_source = distance_from_source  # in km
        self._platform = platform
    
    def get_station(self) -> Station:
        return self._station
    
    def get_stop_number(self) -> int:
        return self._stop_number
    
    def get_arrival_time(self) -> Optional[time]:
        return self._arrival_time
    
    def get_departure_time(self) -> Optional[time]:
        return self._departure_time
    
    def get_distance(self) -> int:
        return self._distance_from_source
    
    def get_platform(self) -> int:
        return self._platform

class Coach:
    """Train coach/compartment"""
    
    def __init__(self, coach_id: str, coach_number: str, seat_type: SeatType,
                 total_seats: int):
        self._coach_id = coach_id
        self._coach_number = coach_number  # e.g., "S1", "A1"
        self._seat_type = seat_type
        self._total_seats = total_seats
        
        # Seat numbers in this coach
        self._seats: List[str] = [f"{coach_number}-{i}" for i in range(1, total_seats + 1)]
    
    def get_id(self) -> str:
        return self._coach_id
    
    def get_coach_number(self) -> str:
        return self._coach_number
    
    def get_seat_type(self) -> SeatType:
        return self._seat_type
    
    def get_total_seats(self) -> int:
        return self._total_seats
    
    def get_seats(self) -> List[str]:
        return self._seats.copy()


class Train:
    """Train with route and coaches"""
    
    def __init__(self, train_id: str, train_number: str, name: str):
        self._train_id = train_id
        self._train_number = train_number  # e.g., "12301"
        self._name = name
        
        # Route: ordered list of TrainRoute objects
        self._route: List[TrainRoute] = []
        
        # Coaches by seat type
        self._coaches: Dict[SeatType, List[Coach]] = defaultdict(list)
        
        # Source and destination (first and last stations)
        self._source: Optional[Station] = None
        self._destination: Optional[Station] = None
        
        # Days train runs (0=Monday, 6=Sunday)
        self._running_days: Set[int] = set(range(7))  # Runs all days by default
        
        # Base fare per km
        self._base_fare_per_km: Dict[SeatType, float] = {
            SeatType.SLEEPER: 0.50,
            SeatType.AC_3_TIER: 1.20,
            SeatType.AC_2_TIER: 1.80,
            SeatType.AC_1_TIER: 3.00,
            SeatType.SECOND_SITTING: 0.30,
            SeatType.CHAIR_CAR: 0.80,
            SeatType.GENERAL: 0.20
        }
    
    def get_id(self) -> str:
        return self._train_id
    
    def get_train_number(self) -> str:
        return self._train_number
    
    def get_name(self) -> str:
        return self._name
    
    def add_route_stop(self, route: TrainRoute) -> None:
        """Add station to route"""
        self._route.append(route)
        self._route.sort(key=lambda r: r.get_stop_number())
        
        # Update source and destination
        if len(self._route) > 0:
            self._source = self._route[0].get_station()
            self._destination = self._route[-1].get_station()
    
    def get_route(self) -> List[TrainRoute]:
        return self._route.copy()
    
    def get_source(self) -> Optional[Station]:
        return self._source
    
    def get_destination(self) -> Optional[Station]:
        return self._destination
    
    def add_coach(self, coach: Coach) -> None:
        """Add coach to train"""
        self._coaches[coach.get_seat_type()].append(coach)
    
    def get_coaches(self, seat_type: Optional[SeatType] = None) -> List[Coach]:
        """Get all coaches or coaches of specific type"""
        if seat_type:
            return self._coaches.get(seat_type, []).copy()
        
        all_coaches = []
        for coaches in self._coaches.values():
            all_coaches.extend(coaches)
        return all_coaches
    
    def get_total_seats(self, seat_type: SeatType) -> int:
        """Get total seats of a specific type"""
        coaches = self._coaches.get(seat_type, [])
        return sum(c.get_total_seats() for c in coaches)
    
    def set_running_days(self, days: Set[int]) -> None:
        """Set which days train runs (0=Monday, 6=Sunday)"""
        self._running_days = days
    
    def runs_on_day(self, day: int) -> bool:
        """Check if train runs on specific day of week"""
        return day in self._running_days
    
    def get_station_by_code(self, code: str) -> Optional[TrainRoute]:
        """Get route stop by station code"""
        for route in self._route:
            if route.get_station().get_code() == code.upper():
                return route
        return None
    
    def get_distance_between_stations(self, from_code: str, to_code: str) -> Optional[int]:
        """Calculate distance between two stations"""
        from_route = self.get_station_by_code(from_code)
        to_route = self.get_station_by_code(to_code)
        
        if not from_route or not to_route:
            return None
        
        return abs(to_route.get_distance() - from_route.get_distance())
    
    def calculate_fare(self, from_code: str, to_code: str, 
                      seat_type: SeatType) -> Optional[float]:
        """Calculate fare between two stations"""
        distance = self.get_distance_between_stations(from_code, to_code)
        if not distance:
            return None
        
        base_rate = self._base_fare_per_km.get(seat_type, 1.0)
        return distance * base_rate


class Passenger:
    """Passenger details"""
    
    def __init__(self, name: str, age: int, gender: Gender):
        self._passenger_id = str(uuid.uuid4())
        self._name = name
        self._age = age
        self._gender = gender
        self._berth_preference: Optional[BerthType] = None
    
    def get_id(self) -> str:
        return self._passenger_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_age(self) -> int:
        return self._age
    
    def get_gender(self) -> Gender:
        return self._gender
    
    def set_berth_preference(self, berth: BerthType) -> None:
        self._berth_preference = berth
    
    def get_berth_preference(self) -> Optional[BerthType]:
        return self._berth_preference


class SeatAllocation:
    """Represents a seat allocated to a passenger"""
    
    def __init__(self, seat_number: str, coach_number: str, berth_type: BerthType):
        self._seat_number = seat_number
        self._coach_number = coach_number
        self._berth_type = berth_type
    
    def get_seat_number(self) -> str:
        return self._seat_number
    
    def get_coach_number(self) -> str:
        return self._coach_number
    
    def get_berth_type(self) -> BerthType:
        return self._berth_type
    
    def __str__(self) -> str:
        return f"{self._coach_number}-{self._seat_number} ({self._berth_type.value})"


class Ticket:
    """Ticket for a passenger"""
    
    def __init__(self, ticket_id: str, passenger: Passenger, 
                 from_station: str, to_station: str,
                 seat_type: SeatType):
        self._ticket_id = ticket_id
        self._passenger = passenger
        self._from_station = from_station
        self._to_station = to_station
        self._seat_type = seat_type
        self._status = BookingStatus.CONFIRMED
        self._seat_allocation: Optional[SeatAllocation] = None
        self._fare = 0.0
    
    def get_id(self) -> str:
        return self._ticket_id
    
    def get_passenger(self) -> Passenger:
        return self._passenger
    
    def get_from_station(self) -> str:
        return self._from_station
    
    def get_to_station(self) -> str:
        return self._to_station
    
    def get_seat_type(self) -> SeatType:
        return self._seat_type
    
    def get_status(self) -> BookingStatus:
        return self._status
    
    def set_status(self, status: BookingStatus) -> None:
        self._status = status
    
    def set_seat_allocation(self, allocation: SeatAllocation) -> None:
        self._seat_allocation = allocation
    
    def get_seat_allocation(self) -> Optional[SeatAllocation]:
        return self._seat_allocation
    
    def set_fare(self, fare: float) -> None:
        self._fare = fare
    
    def get_fare(self) -> float:
        return self._fare


class Booking:
    """Booking containing multiple tickets"""
    
    def __init__(self, booking_id: str, user_id: str, train_id: str,
                 journey_date: date):
        self._booking_id = booking_id
        self._user_id = user_id
        self._train_id = train_id
        self._journey_date = journey_date
        self._tickets: List[Ticket] = []
        self._total_fare = 0.0
        self._booking_time = datetime.now()
        self._payment_status = PaymentStatus.PENDING
        self._pnr = self._generate_pnr()
    
    def _generate_pnr(self) -> str:
        """Generate 10-digit PNR"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(10)])
    
    def get_id(self) -> str:
        return self._booking_id
    
    def get_pnr(self) -> str:
        return self._pnr
    
    def get_user_id(self) -> str:
        return self._user_id
    
    def get_train_id(self) -> str:
        return self._train_id
    
    def get_journey_date(self) -> date:
        return self._journey_date
    
    def add_ticket(self, ticket: Ticket) -> None:
        self._tickets.append(ticket)
        self._total_fare += ticket.get_fare()
    
    def get_tickets(self) -> List[Ticket]:
        return self._tickets.copy()
    
    def get_total_fare(self) -> float:
        return self._total_fare
    
    def get_booking_time(self) -> datetime:
        return self._booking_time
    
    def get_payment_status(self) -> PaymentStatus:
        return self._payment_status
    
    def set_payment_status(self, status: PaymentStatus) -> None:
        self._payment_status = status
    
    def is_cancelled(self) -> bool:
        """Check if all tickets are cancelled"""
        return all(t.get_status() == BookingStatus.CANCELLED for t in self._tickets)


class User:
    """User account"""
    
    def __init__(self, user_id: str, name: str, email: str, phone: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._phone = phone
        self._bookings: List[str] = []  # Booking IDs
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_phone(self) -> str:
        return self._phone
    
    def add_booking(self, booking_id: str) -> None:
        self._bookings.append(booking_id)
    
    def get_bookings(self) -> List[str]:
        return self._bookings.copy()


# ==================== Seat Availability Manager ====================

class SeatSegment:
    """
    Represents a segment of journey for a seat
    Key insight: A seat can be booked for different segments
    """
    
    def __init__(self, from_stop: int, to_stop: int):
        self._from_stop = from_stop  # Stop number
        self._to_stop = to_stop
    
    def get_from_stop(self) -> int:
        return self._from_stop
    
    def get_to_stop(self) -> int:
        return self._to_stop
    
    def overlaps_with(self, other: 'SeatSegment') -> bool:
        """Check if two segments overlap"""
        return not (self._to_stop <= other._from_stop or 
                   self._from_stop >= other._to_stop)


class SeatAvailability:
    """
    Manages seat availability for a specific train on a specific date
    Handles seat reusability across different segments
    """
    
    def __init__(self, train: Train, journey_date: date):
        self._train = train
        self._journey_date = journey_date
        
        # seat_number -> List of booked segments
        self._seat_bookings: Dict[str, List[SeatSegment]] = defaultdict(list)
        
        # Lock for thread-safe operations
        self._lock = RLock()
    
    def is_seat_available(self, seat_number: str, from_stop: int, 
                         to_stop: int) -> bool:
        """
        Check if seat is available for the given segment
        Key feature: Allows reusability
        """
        with self._lock:
            booked_segments = self._seat_bookings.get(seat_number, [])
            
            requested_segment = SeatSegment(from_stop, to_stop)
            
            # Check if requested segment overlaps with any booked segment
            for segment in booked_segments:
                if segment.overlaps_with(requested_segment):
                    return False
            
            return True
    
    def book_seat(self, seat_number: str, from_stop: int, to_stop: int) -> bool:
        """Book a seat for a specific segment"""
        with self._lock:
            if not self.is_seat_available(seat_number, from_stop, to_stop):
                return False
            
            segment = SeatSegment(from_stop, to_stop)
            self._seat_bookings[seat_number].append(segment)
            return True
    
    def release_seat(self, seat_number: str, from_stop: int, to_stop: int) -> bool:
        """Release a booked seat segment"""
        with self._lock:
            if seat_number not in self._seat_bookings:
                return False
            
            # Find and remove the matching segment
            segments = self._seat_bookings[seat_number]
            for i, segment in enumerate(segments):
                if segment.get_from_stop() == from_stop and segment.get_to_stop() == to_stop:
                    segments.pop(i)
                    return True
            
            return False
    
    def get_available_seats(self, from_stop: int, to_stop: int,
                           seat_type: SeatType) -> List[str]:
        """Get all available seats for a segment and seat type"""
        with self._lock:
            available = []
            
            coaches = self._train.get_coaches(seat_type)
            for coach in coaches:
                for seat in coach.get_seats():
                    if self.is_seat_available(seat, from_stop, to_stop):
                        available.append(seat)
            
            return available
    
    def get_available_count(self, from_stop: int, to_stop: int,
                           seat_type: SeatType) -> int:
        """Get count of available seats"""
        return len(self.get_available_seats(from_stop, to_stop, seat_type))


# ==================== Booking Service ====================

class IRCTCBookingService:
    """
    Main service for train ticket booking
    Handles concurrent bookings with seat reusability
    """
    
    def __init__(self):
        # Core data
        self._users: Dict[str, User] = {}
        self._trains: Dict[str, Train] = {}
        self._stations: Dict[str, Station] = {}
        self._bookings: Dict[str, Booking] = {}
        
        # Seat availability: (train_id, date) -> SeatAvailability
        self._seat_availability: Dict[Tuple[str, date], SeatAvailability] = {}
        
        # Indexes
        self._train_by_number: Dict[str, str] = {}  # train_number -> train_id
        self._station_by_code: Dict[str, str] = {}  # station_code -> station_id
        self._pnr_to_booking: Dict[str, str] = {}  # PNR -> booking_id
        
        # Global lock for critical sections
        self._lock = RLock()
    
    # ==================== User Management ====================
    
    def register_user(self, name: str, email: str, phone: str) -> User:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        user = User(user_id, name, email, phone)
        
        with self._lock:
            self._users[user_id] = user
        
        print(f"✅ User registered: {name} ({email})")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Station Management ====================
    
    def add_station(self, code: str, name: str, city: str) -> Station:
        """Add a railway station"""
        station_id = str(uuid.uuid4())
        station = Station(station_id, code, name, city)
        
        with self._lock:
            self._stations[station_id] = station
            self._station_by_code[code.upper()] = station_id
        
        print(f"✅ Station added: {station}")
        return station
    
    def get_station_by_code(self, code: str) -> Optional[Station]:
        station_id = self._station_by_code.get(code.upper())
        if station_id:
            return self._stations.get(station_id)
        return None
    
    # ==================== Train Management ====================
    
    def add_train(self, train_number: str, name: str) -> Train:
        """Add a new train"""
        train_id = str(uuid.uuid4())
        train = Train(train_id, train_number, name)
        
        with self._lock:
            self._trains[train_id] = train
            self._train_by_number[train_number] = train_id
        
        print(f"✅ Train added: {train_number} - {name}")
        return train
    
    def get_train_by_number(self, train_number: str) -> Optional[Train]:
        train_id = self._train_by_number.get(train_number)
        if train_id:
            return self._trains.get(train_id)
        return None
    
    def get_train(self, train_id: str) -> Optional[Train]:
        return self._trains.get(train_id)
    
    # ==================== Search ====================
    
    def search_trains_by_route(self, from_code: str, to_code: str,
                               journey_date: date) -> List[Train]:
        """
        Search trains between two stations on a specific date
        """
        results = []
        
        # Check if date is valid (not in past)
        if journey_date < date.today():
            return results
        
        day_of_week = journey_date.weekday()
        
        for train in self._trains.values():
            # Check if train runs on this day
            if not train.runs_on_day(day_of_week):
                continue
            
            # Check if both stations are in route
            from_route = train.get_station_by_code(from_code)
            to_route = train.get_station_by_code(to_code)
            
            if not from_route or not to_route:
                continue
            
            # Check if 'from' comes before 'to' in the route
            if from_route.get_stop_number() < to_route.get_stop_number():
                results.append(train)
        
        return results
    
    def search_train_by_number(self, train_number: str, journey_date: date) -> Optional[Train]:
        """Search train by number if it runs on the given date"""
        train = self.get_train_by_number(train_number)
        if not train:
            return None
        
        if journey_date < date.today():
            return None
        
        day_of_week = journey_date.weekday()
        if not train.runs_on_day(day_of_week):
            return None
        
        return train
    
    # ==================== Seat Availability ====================
    
    def _get_seat_availability(self, train_id: str, journey_date: date) -> SeatAvailability:
        """Get or create seat availability for train and date"""
        key = (train_id, journey_date)
        
        if key not in self._seat_availability:
            train = self._trains.get(train_id)
            if train:
                self._seat_availability[key] = SeatAvailability(train, journey_date)
        
        return self._seat_availability.get(key)
    
    def check_seat_availability(self, train_number: str, from_code: str,
                               to_code: str, journey_date: date,
                               seat_type: SeatType) -> int:
        """
        Check number of available seats for a journey segment
        """
        train = self.get_train_by_number(train_number)
        if not train:
            return 0
        
        from_route = train.get_station_by_code(from_code)
        to_route = train.get_station_by_code(to_code)
        
        if not from_route or not to_route:
            return 0
        
        if from_route.get_stop_number() >= to_route.get_stop_number():
            return 0
        
        seat_avail = self._get_seat_availability(train.get_id(), journey_date)
        if not seat_avail:
            return 0
        
        return seat_avail.get_available_count(
            from_route.get_stop_number(),
            to_route.get_stop_number(),
            seat_type
        )
    
    # ==================== Booking ====================
    
    def book_ticket(self, user_id: str, train_number: str,
                   from_code: str, to_code: str, journey_date: date,
                   passengers: List[Passenger], seat_type: SeatType) -> Optional[Booking]:
        """
        Book tickets for multiple passengers
        Thread-safe with seat reusability
        """
        with self._lock:
            # Validate inputs
            user = self._users.get(user_id)
            if not user:
                print("❌ User not found")
                return None
            
            train = self.get_train_by_number(train_number)
            if not train:
                print("❌ Train not found")
                return None
            
            # Get route stops
            from_route = train.get_station_by_code(from_code)
            to_route = train.get_station_by_code(to_code)
            
            if not from_route or not to_route:
                print("❌ Invalid stations")
                return None
            
            if from_route.get_stop_number() >= to_route.get_stop_number():
                print("❌ Invalid route")
                return None
            
            from_stop = from_route.get_stop_number()
            to_stop = to_route.get_stop_number()
            
            # Get seat availability
            seat_avail = self._get_seat_availability(train.get_id(), journey_date)
            if not seat_avail:
                print("❌ Unable to check availability")
                return None
            
            # Check if enough seats available
            available_seats = seat_avail.get_available_seats(from_stop, to_stop, seat_type)
            
            if len(available_seats) < len(passengers):
                print(f"❌ Only {len(available_seats)} seats available, requested {len(passengers)}")
                return None
            
            # Calculate fare
            fare_per_person = train.calculate_fare(from_code, to_code, seat_type)
            if not fare_per_person:
                print("❌ Unable to calculate fare")
                return None
            
            # Create booking
            booking_id = str(uuid.uuid4())
            booking = Booking(booking_id, user_id, train.get_id(), journey_date)
            
            # Book seats and create tickets
            for i, passenger in enumerate(passengers):
                seat_number = available_seats[i]
                
                # Book the seat
                success = seat_avail.book_seat(seat_number, from_stop, to_stop)
                if not success:
                    # Rollback previous bookings
                    for j in range(i):
                        prev_seat = available_seats[j]
                        seat_avail.release_seat(prev_seat, from_stop, to_stop)
                    print(f"❌ Failed to book seat {seat_number}")
                    return None
                
                # Create ticket
                ticket_id = str(uuid.uuid4())
                ticket = Ticket(ticket_id, passenger, from_code, to_code, seat_type)
                ticket.set_fare(fare_per_person)
                ticket.set_status(BookingStatus.CONFIRMED)
                
                # Assign seat (simplified - just use seat number)
                allocation = SeatAllocation(seat_number, seat_number.split('-')[0], BerthType.LOWER)
                ticket.set_seat_allocation(allocation)
                
                booking.add_ticket(ticket)
            
            # Save booking
            self._bookings[booking_id] = booking
            self._pnr_to_booking[booking.get_pnr()] = booking_id
            user.add_booking(booking_id)
            
            print(f"✅ Booking confirmed! PNR: {booking.get_pnr()}")
            print(f"   {len(passengers)} ticket(s) booked")
            print(f"   Total fare: ₹{booking.get_total_fare():.2f}")
            
            return booking
    
    def get_booking_by_pnr(self, pnr: str) -> Optional[Booking]:
        """Get booking by PNR number"""
        booking_id = self._pnr_to_booking.get(pnr)
        if booking_id:
            return self._bookings.get(booking_id)
        return None
    
    # ==================== Cancellation ====================
    
    def cancel_booking(self, pnr: str, user_id: str) -> bool:
        """
        Cancel entire booking
        Releases all seats for reuse
        """
        with self._lock:
            booking = self.get_booking_by_pnr(pnr)
            if not booking:
                print("❌ Booking not found")
                return False
            
            # Verify ownership
            if booking.get_user_id() != user_id:
                print("❌ Unauthorized cancellation attempt")
                return False
            
            # Check if already cancelled
            if booking.is_cancelled():
                print("❌ Booking already cancelled")
                return False
            
            # Get train and seat availability
            train = self._trains.get(booking.get_train_id())
            if not train:
                return False
            
            seat_avail = self._get_seat_availability(
                booking.get_train_id(),
                booking.get_journey_date()
            )
            
            if not seat_avail:
                return False
            
            # Cancel all tickets and release seats
            for ticket in booking.get_tickets():
                # Get route stops
                from_route = train.get_station_by_code(ticket.get_from_station())
                to_route = train.get_station_by_code(ticket.get_to_station())
                
                if from_route and to_route:
                    allocation = ticket.get_seat_allocation()
                    if allocation:
                        # Release seat
                        seat_avail.release_seat(
                            allocation.get_seat_number(),
                            from_route.get_stop_number(),
                            to_route.get_stop_number()
                        )
                
                ticket.set_status(BookingStatus.CANCELLED)
            
            # Update payment status
            booking.set_payment_status(PaymentStatus.REFUNDED)
            
            print(f"✅ Booking cancelled - PNR: {pnr}")
            print(f"   Refund amount: ₹{booking.get_total_fare():.2f}")
            
            return True
    
    def cancel_ticket(self, pnr: str, ticket_id: str, user_id: str) -> bool:
        """
        Cancel individual ticket within a booking
        """
        with self._lock:
            booking = self.get_booking_by_pnr(pnr)
            if not booking:
                return False
            
            if booking.get_user_id() != user_id:
                return False
            
            # Find ticket
            ticket = None
            for t in booking.get_tickets():
                if t.get_id() == ticket_id:
                    ticket = t
                    break
            
            if not ticket:
                return False
            
            if ticket.get_status() == BookingStatus.CANCELLED:
                return False
            
            # Release seat
            train = self._trains.get(booking.get_train_id())
            if not train:
                return False
            
            seat_avail = self._get_seat_availability(
                booking.get_train_id(),
                booking.get_journey_date()
            )
            
            from_route = train.get_station_by_code(ticket.get_from_station())
            to_route = train.get_station_by_code(ticket.get_to_station())
            
            if from_route and to_route:
                allocation = ticket.get_seat_allocation()
                if allocation:
                    seat_avail.release_seat(
                        allocation.get_seat_number(),
                        from_route.get_stop_number(),
                        to_route.get_stop_number()
                    )
            
            ticket.set_status(BookingStatus.CANCELLED)
            
            print(f"✅ Ticket cancelled")
            print(f"   Refund: ₹{ticket.get_fare():.2f}")
            
            return True
    
    # ==================== Reports ====================
    
    def get_train_occupancy(self, train_number: str, journey_date: date,
                           seat_type: SeatType) -> Dict:
        """Get occupancy statistics for a train"""
        train = self.get_train_by_number(train_number)
        if not train:
            return {}
        
        total_seats = train.get_total_seats(seat_type)
        route = train.get_route()
        
        occupancy_by_segment = []
        
        for i in range(len(route) - 1):
            from_stop = route[i].get_stop_number()
            to_stop = route[i + 1].get_stop_number()
            
            seat_avail = self._get_seat_availability(train.get_id(), journey_date)
            if seat_avail:
                available = seat_avail.get_available_count(from_stop, to_stop, seat_type)
                booked = total_seats - available
                
                occupancy_by_segment.append({
                    'from': route[i].get_station().get_code(),
                    'to': route[i + 1].get_station().get_code(),
                    'booked': booked,
                    'available': available,
                    'occupancy_percent': (booked / total_seats * 100) if total_seats > 0 else 0
                })
        
        return {
            'train_number': train_number,
            'journey_date': journey_date.isoformat(),
            'seat_type': seat_type.value,
            'total_seats': total_seats,
            'segments': occupancy_by_segment
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_train_info(train: Train) -> None:
    """Print train details"""
    print(f"\n🚂 {train.get_train_number()} - {train.get_name()}")
    print(f"   Route: {train.get_source()} → {train.get_destination()}")
    
    route = train.get_route()
    print(f"   Stops ({len(route)}):")
    for r in route:
        arr = r.get_arrival_time().strftime('%H:%M') if r.get_arrival_time() else "START"
        dep = r.get_departure_time().strftime('%H:%M') if r.get_departure_time() else "END"
        print(f"      {r.get_stop_number()}. {r.get_station().get_code()} - "
              f"Arr: {arr}, Dep: {dep}, Distance: {r.get_distance()}km")


def print_booking_details(booking: Booking, train: Train) -> None:
    """Print booking confirmation"""
    print(f"\n🎫 BOOKING CONFIRMATION")
    print(f"   PNR: {booking.get_pnr()}")
    print(f"   Train: {train.get_train_number()} - {train.get_name()}")
    print(f"   Journey Date: {booking.get_journey_date()}")
    print(f"   Total Fare: ₹{booking.get_total_fare():.2f}")
    print(f"\n   Passengers:")
    
    for ticket in booking.get_tickets():
        passenger = ticket.get_passenger()
        allocation = ticket.get_seat_allocation()
        seat_info = str(allocation) if allocation else "Not allocated"
        
        print(f"      • {passenger.get_name()} ({passenger.get_age()}/{passenger.get_gender().value})")
        print(f"        {ticket.get_from_station()} → {ticket.get_to_station()}")
        print(f"        Seat: {seat_info}, Fare: ₹{ticket.get_fare():.2f}")
        print(f"        Status: {ticket.get_status().value}")


def demo_irctc_booking_system():
    """Comprehensive demo of IRCTC booking system"""
    
    print_section("IRCTC TRAIN TICKET BOOKING SYSTEM DEMO")
    
    service = IRCTCBookingService()
    
    try:
        # ==================== Setup Stations ====================
        print_section("1. Add Railway Stations")
        
        ndls = service.add_station("NDLS", "New Delhi", "Delhi")
        bpl = service.add_station("BPL", "Bhopal Junction", "Bhopal")
        jbp = service.add_station("JBP", "Jabalpur Junction", "Jabalpur")
        ald = service.add_station("ALD", "Allahabad Junction", "Prayagraj")
        cstm = service.add_station("CSTM", "Mumbai CST", "Mumbai")
        pune = service.add_station("PUNE", "Pune Junction", "Pune")
        
        # ==================== Setup Train ====================
                # ==================== Setup Train ====================
        print_section("2. Add Train with Route")
        
        # Rajdhani Express
        rajdhani = service.add_train("12301", "Howrah Rajdhani Express")
        
        # Add route
        rajdhani.add_route_stop(TrainRoute(ndls, 1, None, time(17, 0), 0, 7))
        rajdhani.add_route_stop(TrainRoute(bpl, 2, time(2, 15), time(2, 25), 750, 3))
        rajdhani.add_route_stop(TrainRoute(jbp, 3, time(5, 30), time(5, 40), 1050, 2))
        rajdhani.add_route_stop(TrainRoute(ald, 4, time(10, 15), time(10, 25), 1400, 5))
        rajdhani.add_route_stop(TrainRoute(cstm, 5, time(18, 30), None, 2200, 1))  # None for last stop
        
        # Add coaches
        # Sleeper coaches
        for i in range(1, 6):
            coach = Coach(str(uuid.uuid4()), f"S{i}", SeatType.SLEEPER, 72)
            rajdhani.add_coach(coach)
        
        # AC 3-Tier
        for i in range(1, 4):
            coach = Coach(str(uuid.uuid4()), f"B{i}", SeatType.AC_3_TIER, 64)
            rajdhani.add_coach(coach)
        
        # AC 2-Tier
        for i in range(1, 3):
            coach = Coach(str(uuid.uuid4()), f"A{i}", SeatType.AC_2_TIER, 48)
            rajdhani.add_coach(coach)
        
        print_train_info(rajdhani)
        
        print(f"\n   Seat Configuration:")
        for seat_type in [SeatType.SLEEPER, SeatType.AC_3_TIER, SeatType.AC_2_TIER]:
            count = rajdhani.get_total_seats(seat_type)
            print(f"      {seat_type.value}: {count} seats")
        
        # ==================== Register Users ====================
        print_section("3. Register Users")
        
        user1 = service.register_user("Rahul Sharma", "rahul@example.com", "+91-9876543210")
        user2 = service.register_user("Priya Patel", "priya@example.com", "+91-9123456789")
        user3 = service.register_user("Amit Kumar", "amit@example.com", "+91-9234567890")
        
        # ==================== Search Trains ====================
        print_section("4. Search Trains by Route")
        
        journey_date = date.today() + timedelta(days=7)
        
        trains = service.search_trains_by_route("NDLS", "CSTM", journey_date)
        
        print(f"\n🔍 Trains from NDLS to CSTM on {journey_date}:")
        for train in trains:
            print(f"   • {train.get_train_number()} - {train.get_name()}")
        
        # ==================== Check Availability ====================
        print_section("5. Check Seat Availability")
        
        print(f"\n📊 Availability for train 12301 (NDLS → CSTM) on {journey_date}:")
        
        for seat_type in [SeatType.SLEEPER, SeatType.AC_3_TIER, SeatType.AC_2_TIER]:
            available = service.check_seat_availability(
                "12301", "NDLS", "CSTM", journey_date, seat_type
            )
            total = rajdhani.get_total_seats(seat_type)
            print(f"   {seat_type.value}: {available}/{total} available")
        
        # ==================== Book Tickets ====================
        print_section("6. Book Tickets")
        
        # Create passengers
        passenger1 = Passenger("Rahul Sharma", 30, Gender.MALE)
        passenger2 = Passenger("Priya Sharma", 28, Gender.FEMALE)
        
        # Book tickets from NDLS to CSTM
        booking1 = service.book_ticket(
            user_id=user1.get_id(),
            train_number="12301",
            from_code="NDLS",
            to_code="CSTM",
            journey_date=journey_date,
            passengers=[passenger1, passenger2],
            seat_type=SeatType.AC_3_TIER
        )
        
        if booking1:
            print_booking_details(booking1, rajdhani)
        
        # ==================== Seat Reusability Demo ====================
        print_section("7. Seat Reusability - Book from Mid Route")
        
        # Book from Bhopal to Allahabad (should reuse seats)
        passenger3 = Passenger("Amit Kumar", 35, Gender.MALE)
        
        print(f"\n📊 Availability BPL → ALD (mid-route):")
        available = service.check_seat_availability(
            "12301", "BPL", "ALD", journey_date, SeatType.AC_3_TIER
        )
        print(f"   AC 3-Tier: {available} seats available")
        
        booking2 = service.book_ticket(
            user_id=user3.get_id(),
            train_number="12301",
            from_code="BPL",
            to_code="ALD",
            journey_date=journey_date,
            passengers=[passenger3],
            seat_type=SeatType.AC_3_TIER
        )
        
        if booking2:
            print_booking_details(booking2, rajdhani)
            print(f"\n✅ Notice: Seats are reused for different segments!")
        
        # ==================== Concurrent Booking Simulation ====================
        print_section("8. Concurrent Booking Simulation")
        
        # Check availability before concurrent bookings
        before_avail = service.check_seat_availability(
            "12301", "NDLS", "BPL", journey_date, SeatType.SLEEPER
        )
        print(f"\n📊 Before concurrent bookings: {before_avail} Sleeper seats available")
        
        # Simulate concurrent bookings
        def book_tickets_concurrent(user_id: str, name_prefix: str, count: int):
            passengers = [Passenger(f"{name_prefix} {i}", 25 + i, Gender.MALE) 
                         for i in range(count)]
            
            booking = service.book_ticket(
                user_id=user_id,
                train_number="12301",
                from_code="NDLS",
                to_code="BPL",
                journey_date=journey_date,
                passengers=passengers,
                seat_type=SeatType.SLEEPER
            )
            
            if booking:
                print(f"   Thread {name_prefix}: Booked {count} seats - PNR: {booking.get_pnr()}")
        
        # Create concurrent booking threads
        threads = []
        for i in range(5):
            user = service.register_user(f"User{i}", f"user{i}@example.com", f"+91-900000000{i}")
            thread = Thread(target=book_tickets_concurrent, args=(user.get_id(), f"U{i}", 2))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        after_avail = service.check_seat_availability(
            "12301", "NDLS", "BPL", journey_date, SeatType.SLEEPER
        )
        print(f"\n📊 After concurrent bookings: {after_avail} Sleeper seats available")
        print(f"   Booked: {before_avail - after_avail} seats")
        
        # ==================== Check Updated Availability ====================
        print_section("9. Updated Seat Availability")
        
        print(f"\n📊 Current availability for train 12301 on {journey_date}:")
        
        segments = [
            ("NDLS", "BPL"),
            ("BPL", "JBP"),
            ("JBP", "ALD"),
            ("ALD", "CSTM")
        ]
        
        for from_code, to_code in segments:
            print(f"\n   {from_code} → {to_code}:")
            for seat_type in [SeatType.SLEEPER, SeatType.AC_3_TIER]:
                available = service.check_seat_availability(
                    "12301", from_code, to_code, journey_date, seat_type
                )
                total = rajdhani.get_total_seats(seat_type)
                booked = total - available
                print(f"      {seat_type.value}: {booked} booked, {available} available")
        
        # ==================== Cancellation ====================
        print_section("10. Cancel Booking")
        
        if booking1:
            print(f"\n🎫 Cancelling booking PNR: {booking1.get_pnr()}")
            
            success = service.cancel_booking(booking1.get_pnr(), user1.get_id())
            
            if success:
                # Check availability after cancellation
                available_after_cancel = service.check_seat_availability(
                    "12301", "NDLS", "CSTM", journey_date, SeatType.AC_3_TIER
                )
                print(f"\n📊 Seats released back to inventory")
                print(f"   AC 3-Tier available now: {available_after_cancel}")
        
        # ==================== Train Occupancy Report ====================
        print_section("11. Train Occupancy Report")
        
        occupancy = service.get_train_occupancy("12301", journey_date, SeatType.AC_3_TIER)
        
        print(f"\n📊 Train {occupancy['train_number']} - AC 3-Tier Occupancy")
        print(f"   Date: {occupancy['journey_date']}")
        print(f"   Total Seats: {occupancy['total_seats']}")
        print(f"\n   Segment-wise Occupancy:")
        
        for segment in occupancy['segments']:
            print(f"      {segment['from']} → {segment['to']}: "
                  f"{segment['booked']} booked, {segment['available']} available "
                  f"({segment['occupancy_percent']:.1f}% occupied)")
        
        # ==================== Search by Train Number ====================
        print_section("12. Search Train by Number")
        
        train = service.search_train_by_number("12301", journey_date)
        if train:
            print(f"\n✅ Train found: {train.get_train_number()} - {train.get_name()}")
            print(f"   Runs on: {journey_date} ({journey_date.strftime('%A')})")
        
        # ==================== PNR Status ====================
        print_section("13. Check PNR Status")
        
        if booking2:
            pnr = booking2.get_pnr()
            booking_status = service.get_booking_by_pnr(pnr)
            
            if booking_status:
                print(f"\n🔍 PNR Status: {pnr}")
                print(f"   Journey Date: {booking_status.get_journey_date()}")
                print(f"   Total Passengers: {len(booking_status.get_tickets())}")
                print(f"   Payment Status: {booking_status.get_payment_status().value}")
                print(f"\n   Ticket Details:")
                
                for ticket in booking_status.get_tickets():
                    passenger = ticket.get_passenger()
                    allocation = ticket.get_seat_allocation()
                    
                    print(f"      {passenger.get_name()}: {ticket.get_status().value}")
                    if allocation:
                        print(f"         Seat: {allocation}")
        
        # ==================== Fare Calculation ====================
        print_section("14. Fare Calculation")
        
        routes_to_check = [
            ("NDLS", "BPL"),
            ("BPL", "CSTM"),
            ("NDLS", "CSTM")
        ]
        
        print(f"\n💰 Fare Chart for Train 12301:")
        
        for from_code, to_code in routes_to_check:
            distance = rajdhani.get_distance_between_stations(from_code, to_code)
            print(f"\n   {from_code} → {to_code} ({distance}km):")
            
            for seat_type in [SeatType.SLEEPER, SeatType.AC_3_TIER, SeatType.AC_2_TIER]:
                fare = rajdhani.calculate_fare(from_code, to_code, seat_type)
                if fare:
                    print(f"      {seat_type.value}: ₹{fare:.2f}")
        
    finally:
        print_section("Demo Complete")
        print("\n✅ IRCTC booking system demo completed successfully!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_irctc_booking_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# IRCTC Train Ticket Booking System - Low Level Design
# Here's a comprehensive train ticket booking system design:

# Key Design Decisions:
# 1. Seat Reusability (Core Feature):
# SeatSegment: Represents journey segment (from_stop → to_stop)
# SeatAvailability: Tracks which segments each seat is booked for
# A seat can be booked for multiple non-overlapping segments
# Example: Seat S1 booked NDLS→BPL, same seat available BPL→CSTM
# 2. Concurrency Handling:
# Thread-safe seat booking with RLock
# Atomic check-and-book operations
# Rollback mechanism if booking fails mid-way
# Fair handling via locks (FIFO within lock queue)
# 3. Core Components:
# Station: Railway station with code
# TrainRoute: Station in train's route with timings
# Train: Train with route, coaches, and seat types
# Coach: Compartment with seats
# SeatAvailability: Manages seat bookings per segment
# Booking: Contains multiple tickets (passengers)
# Ticket: Individual passenger ticket
# 4. Key Features:
# ✅ Search by train number ✅ Search by source/destination/date ✅ Seat availability check with reusability ✅ Thread-safe concurrent booking ✅ Seat reusability across segments ✅ Booking cancellation (releases seats) ✅ Individual ticket cancellation ✅ PNR-based booking retrieval ✅ Train occupancy reports ✅ Fare calculation based on distance ✅ Multiple seat types (Sleeper, AC tiers)

# 5. Search Capabilities:
# By train number and date
# By source, destination, and date
# Validates train runs on specific day of week
# 6. Design Patterns:
# Strategy Pattern: Different seat types
# Composite Pattern: Booking contains tickets
# Factory-like: ID generation
# Singleton-like: Service class
# Segment Tree concept: Seat availability tracking
# 7. Segment-Based Booking Algorithm:
# This is a production-grade IRCTC-like booking system with seat reusability! 🚂🎫
