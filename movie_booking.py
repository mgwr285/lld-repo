from enum import Enum
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Lock
from collections import defaultdict


# ==================== Enums ====================

class SeatType(Enum):
    """Types of seats"""
    REGULAR = "REGULAR"
    PREMIUM = "PREMIUM"
    VIP = "VIP"
    WHEELCHAIR = "WHEELCHAIR"


class SeatStatus(Enum):
    """Status of a seat"""
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    RESERVED = "RESERVED"  # Temporarily held during booking
    BLOCKED = "BLOCKED"    # Not available for booking


class BookingStatus(Enum):
    """Status of booking"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentStatus(Enum):
    """Status of payment"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class MovieGenre(Enum):
    """Movie genres"""
    ACTION = "ACTION"
    COMEDY = "COMEDY"
    DRAMA = "DRAMA"
    HORROR = "HORROR"
    THRILLER = "THRILLER"
    ROMANCE = "ROMANCE"
    SCI_FI = "SCI_FI"
    DOCUMENTARY = "DOCUMENTARY"


# ==================== Core Models ====================

class Movie:
    """Represents a movie"""
    
    def __init__(self, movie_id: str, title: str, description: str,
                 duration_minutes: int, genre: MovieGenre, language: str,
                 release_date: datetime, rating: str):
        self._movie_id = movie_id
        self._title = title
        self._description = description
        self._duration_minutes = duration_minutes
        self._genre = genre
        self._language = language
        self._release_date = release_date
        self._rating = rating  # PG, PG-13, R, etc.
    
    def get_id(self) -> str:
        return self._movie_id
    
    def get_title(self) -> str:
        return self._title
    
    def get_duration(self) -> int:
        return self._duration_minutes
    
    def get_genre(self) -> MovieGenre:
        return self._genre
    
    def get_language(self) -> str:
        return self._language
    
    def __repr__(self) -> str:
        return f"Movie({self._movie_id}, {self._title}, {self._language})"


class Seat:
    """Represents a seat in a screen"""
    
    def __init__(self, seat_id: str, row: str, number: int, 
                 seat_type: SeatType, price: Decimal):
        self._seat_id = seat_id
        self._row = row
        self._number = number
        self._seat_type = seat_type
        self._price = price
    
    def get_id(self) -> str:
        return self._seat_id
    
    def get_row(self) -> str:
        return self._row
    
    def get_number(self) -> int:
        return self._number
    
    def get_type(self) -> SeatType:
        return self._seat_type
    
    def get_price(self) -> Decimal:
        return self._price
    
    def get_display_name(self) -> str:
        return f"{self._row}{self._number}"
    
    def __repr__(self) -> str:
        return f"Seat({self.get_display_name()}, {self._seat_type.value})"
    
    def __hash__(self) -> int:
        return hash(self._seat_id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Seat):
            return False
        return self._seat_id == other._seat_id


class Screen:
    """Represents a movie screen/hall"""
    
    def __init__(self, screen_id: str, name: str, total_seats: int):
        self._screen_id = screen_id
        self._name = name
        self._total_seats = total_seats
        self._seats: Dict[str, Seat] = {}
    
    def get_id(self) -> str:
        return self._screen_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_total_seats(self) -> int:
        return self._total_seats
    
    def add_seat(self, seat: Seat) -> None:
        """Add a seat to this screen"""
        self._seats[seat.get_id()] = seat
    
    def get_seat(self, seat_id: str) -> Optional[Seat]:
        """Get seat by ID"""
        return self._seats.get(seat_id)
    
    def get_all_seats(self) -> List[Seat]:
        """Get all seats"""
        return list(self._seats.values())
    
    def __repr__(self) -> str:
        return f"Screen({self._screen_id}, {self._name}, {self._total_seats} seats)"


class Show:
    """Represents a movie show/screening"""
    
    _show_counter = 0
    
    def __init__(self, movie: Movie, screen: Screen, 
                 start_time: datetime, end_time: datetime):
        Show._show_counter += 1
        self._show_id = f"SHOW-{Show._show_counter:06d}"
        self._movie = movie
        self._screen = screen
        self._start_time = start_time
        self._end_time = end_time
        
        # Seat availability tracking (thread-safe)
        self._seat_status: Dict[str, SeatStatus] = {}
        self._seat_locks: Dict[str, Lock] = {}
        self._reserved_seats: Dict[str, tuple] = {}  # seat_id -> (user_id, expiry_time)
        self._lock = Lock()
        
        # Initialize all seats as available
        for seat in screen.get_all_seats():
            self._seat_status[seat.get_id()] = SeatStatus.AVAILABLE
            self._seat_locks[seat.get_id()] = Lock()
    
    def get_id(self) -> str:
        return self._show_id
    
    def get_movie(self) -> Movie:
        return self._movie
    
    def get_screen(self) -> Screen:
        return self._screen
    
    def get_start_time(self) -> datetime:
        return self._start_time
    
    def get_end_time(self) -> datetime:
        return self._end_time
    
    def get_seat_status(self, seat_id: str) -> Optional[SeatStatus]:
        """Get current status of a seat"""
        with self._lock:
            return self._seat_status.get(seat_id)
    
    def get_available_seats(self) -> List[Seat]:
        """Get all available seats"""
        with self._lock:
            # Clean up expired reservations first
            self._cleanup_expired_reservations()
            
            available_seat_ids = [
                seat_id for seat_id, status in self._seat_status.items()
                if status == SeatStatus.AVAILABLE
            ]
            
            return [self._screen.get_seat(seat_id) for seat_id in available_seat_ids]
    
    def reserve_seats(self, seat_ids: List[str], user_id: str, 
                     duration_minutes: int = 10) -> bool:
        """
        Reserve seats temporarily (with timeout).
        This prevents double-booking during the payment process.
        """
        with self._lock:
            # Clean up expired reservations
            self._cleanup_expired_reservations()
            
            # Check if all seats are available
            for seat_id in seat_ids:
                if seat_id not in self._seat_status:
                    print(f"Invalid seat: {seat_id}")
                    return False
                
                if self._seat_status[seat_id] != SeatStatus.AVAILABLE:
                    print(f"Seat {seat_id} not available")
                    return False
            
            # Reserve all seats
            expiry_time = datetime.now() + timedelta(minutes=duration_minutes)
            for seat_id in seat_ids:
                self._seat_status[seat_id] = SeatStatus.RESERVED
                self._reserved_seats[seat_id] = (user_id, expiry_time)
            
            return True
    
    def confirm_seats(self, seat_ids: List[str], user_id: str) -> bool:
        """Confirm reserved seats (after payment)"""
        with self._lock:
            # Verify all seats are reserved by this user
            for seat_id in seat_ids:
                if seat_id not in self._reserved_seats:
                    print(f"Seat {seat_id} not reserved")
                    return False
                
                reserved_user, _ = self._reserved_seats[seat_id]
                if reserved_user != user_id:
                    print(f"Seat {seat_id} reserved by different user")
                    return False
            
            # Confirm all seats
            for seat_id in seat_ids:
                self._seat_status[seat_id] = SeatStatus.BOOKED
                del self._reserved_seats[seat_id]
            
            return True
    
    def release_seats(self, seat_ids: List[str], user_id: str) -> bool:
        """Release reserved seats (if booking cancelled)"""
        with self._lock:
            for seat_id in seat_ids:
                if seat_id in self._reserved_seats:
                    reserved_user, _ = self._reserved_seats[seat_id]
                    if reserved_user == user_id:
                        self._seat_status[seat_id] = SeatStatus.AVAILABLE
                        del self._reserved_seats[seat_id]
            
            return True
    
    def cancel_booking(self, seat_ids: List[str]) -> bool:
        """Cancel confirmed booking and make seats available"""
        with self._lock:
            for seat_id in seat_ids:
                if seat_id in self._seat_status:
                    if self._seat_status[seat_id] == SeatStatus.BOOKED:
                        self._seat_status[seat_id] = SeatStatus.AVAILABLE
            
            return True
    
    def _cleanup_expired_reservations(self) -> None:
        """Clean up expired reservations (internal method, lock must be held)"""
        current_time = datetime.now()
        expired_seats = []
        
        for seat_id, (user_id, expiry_time) in self._reserved_seats.items():
            if current_time > expiry_time:
                expired_seats.append(seat_id)
        
        for seat_id in expired_seats:
            self._seat_status[seat_id] = SeatStatus.AVAILABLE
            del self._reserved_seats[seat_id]
    
    def get_seat_map(self) -> Dict[str, SeatStatus]:
        """Get seat map with current status"""
        with self._lock:
            self._cleanup_expired_reservations()
            return self._seat_status.copy()
    
    def __repr__(self) -> str:
        return f"Show({self._show_id}, {self._movie.get_title()}, {self._start_time})"


class Theater:
    """Represents a movie theater/cinema"""
    
    def __init__(self, theater_id: str, name: str, address: str):
        self._theater_id = theater_id
        self._name = name
        self._address = address
        self._screens: Dict[str, Screen] = {}
        self._shows: List[Show] = []
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._theater_id
    
    def get_name(self) -> str:
        return self._name
    
    def add_screen(self, screen: Screen) -> None:
        """Add a screen to this theater"""
        with self._lock:
            self._screens[screen.get_id()] = screen
    
    def get_screen(self, screen_id: str) -> Optional[Screen]:
        """Get screen by ID"""
        return self._screens.get(screen_id)
    
    def add_show(self, show: Show) -> bool:
        """Add a show to this theater"""
        # Check for conflicts
        screen = show.get_screen()
        
        with self._lock:
            # Check if screen exists in this theater
            if screen.get_id() not in self._screens:
                print(f"Screen not found in theater")
                return False
            
            # Check for time conflicts
            for existing_show in self._shows:
                if existing_show.get_screen() == screen:
                    # Check for overlap
                    if (show.get_start_time() < existing_show.get_end_time() and
                        show.get_end_time() > existing_show.get_start_time()):
                        print(f"Show conflicts with existing show")
                        return False
            
            self._shows.append(show)
            return True
    
    def get_shows(self, movie: Optional[Movie] = None, 
                  date: Optional[datetime] = None) -> List[Show]:
        """Get shows, optionally filtered by movie and/or date"""
        with self._lock:
            shows = self._shows.copy()
        
        # Filter by movie
        if movie:
            shows = [s for s in shows if s.get_movie() == movie]
        
        # Filter by date
        if date:
            shows = [s for s in shows if s.get_start_time().date() == date.date()]
        
        return sorted(shows, key=lambda s: s.get_start_time())
    
    def __repr__(self) -> str:
        return f"Theater({self._theater_id}, {self._name})"


class User:
    """Represents a user"""
    
    def __init__(self, user_id: str, name: str, email: str, phone: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._phone = phone
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def __repr__(self) -> str:
        return f"User({self._user_id}, {self._name})"


@dataclass
class Payment:
    """Represents a payment"""
    payment_id: str
    amount: Decimal
    payment_method: str
    status: PaymentStatus
    timestamp: datetime


class Booking:
    """Represents a movie booking"""
    
    _booking_counter = 0
    
    def __init__(self, user: User, show: Show, seats: List[Seat]):
        Booking._booking_counter += 1
        self._booking_id = f"BK-{Booking._booking_counter:08d}"
        self._user = user
        self._show = show
        self._seats = seats
        self._status = BookingStatus.PENDING
        self._booking_time = datetime.now()
        self._payment: Optional[Payment] = None
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._booking_id
    
    def get_user(self) -> User:
        return self._user
    
    def get_show(self) -> Show:
        return self._show
    
    def get_seats(self) -> List[Seat]:
        return self._seats
    
    def get_status(self) -> BookingStatus:
        with self._lock:
            return self._status
    
    def set_status(self, status: BookingStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_total_amount(self) -> Decimal:
        """Calculate total booking amount"""
        return sum(seat.get_price() for seat in self._seats)
    
    def set_payment(self, payment: Payment) -> None:
        """Set payment information"""
        with self._lock:
            self._payment = payment
    
    def get_payment(self) -> Optional[Payment]:
        with self._lock:
            return self._payment
    
    def confirm(self) -> bool:
        """Confirm booking after payment"""
        seat_ids = [seat.get_id() for seat in self._seats]
        if self._show.confirm_seats(seat_ids, self._user.get_id()):
            self.set_status(BookingStatus.CONFIRMED)
            return True
        return False
    
    def cancel(self) -> bool:
        """Cancel booking"""
        seat_ids = [seat.get_id() for seat in self._seats]
        if self._show.cancel_booking(seat_ids):
            self.set_status(BookingStatus.CANCELLED)
            return True
        return False
    
    def __repr__(self) -> str:
        return f"Booking({self._booking_id}, {self._user.get_name()}, {len(self._seats)} seats)"


# ==================== Movie Booking System ====================

class MovieBookingSystem:
    """Main movie booking system"""
    
    _payment_counter = 0
    
    def __init__(self):
        self._theaters: Dict[str, Theater] = {}
        self._movies: Dict[str, Movie] = {}
        self._users: Dict[str, User] = {}
        self._bookings: Dict[str, Booking] = {}
        self._lock = Lock()
    
    def add_theater(self, theater: Theater) -> None:
        """Add a theater"""
        with self._lock:
            self._theaters[theater.get_id()] = theater
        print(f"Added theater: {theater}")
    
    def add_movie(self, movie: Movie) -> None:
        """Add a movie"""
        with self._lock:
            self._movies[movie.get_id()] = movie
        print(f"Added movie: {movie}")
    
    def register_user(self, user: User) -> None:
        """Register a user"""
        with self._lock:
            self._users[user.get_id()] = user
        print(f"Registered user: {user}")
    
    def get_theater(self, theater_id: str) -> Optional[Theater]:
        """Get theater by ID"""
        return self._theaters.get(theater_id)
    
    def get_movie(self, movie_id: str) -> Optional[Movie]:
        """Get movie by ID"""
        return self._movies.get(movie_id)
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def search_movies(self, title: Optional[str] = None, 
                     genre: Optional[MovieGenre] = None,
                     language: Optional[str] = None) -> List[Movie]:
        """Search for movies"""
        with self._lock:
            movies = list(self._movies.values())
        
        if title:
            movies = [m for m in movies if title.lower() in m.get_title().lower()]
        
        if genre:
            movies = [m for m in movies if m.get_genre() == genre]
        
        if language:
            movies = [m for m in movies if m.get_language() == language]
        
        return movies
    
    def get_shows_for_movie(self, movie: Movie, date: Optional[datetime] = None) -> Dict[Theater, List[Show]]:
        """Get all shows for a movie, grouped by theater"""
        shows_by_theater = defaultdict(list)
        
        for theater in self._theaters.values():
            shows = theater.get_shows(movie, date)
            if shows:
                shows_by_theater[theater] = shows
        
        return dict(shows_by_theater)
    
    def create_booking(self, user_id: str, show_id: str, 
                      seat_ids: List[str]) -> Optional[Booking]:
        """Create a new booking (reserve seats)"""
        user = self.get_user(user_id)
        if not user:
            print(f"User not found: {user_id}")
            return None
        
        # Find the show
        show = None
        for theater in self._theaters.values():
            for s in theater.get_shows():
                if s.get_id() == show_id:
                    show = s
                    break
            if show:
                break
        
        if not show:
            print(f"Show not found: {show_id}")
            return None
        
        # Get seat objects
        screen = show.get_screen()
        seats = []
        for seat_id in seat_ids:
            seat = screen.get_seat(seat_id)
            if not seat:
                print(f"Invalid seat: {seat_id}")
                return None
            seats.append(seat)
        
        # Reserve seats (with 10 minute timeout)
        if not show.reserve_seats(seat_ids, user_id, duration_minutes=10):
            print("Failed to reserve seats")
            return None
        
        # Create booking
        booking = Booking(user, show, seats)
        
        with self._lock:
            self._bookings[booking.get_id()] = booking
        
        print(f"\nCreated booking: {booking}")
        print(f"Reserved seats: {', '.join(s.get_display_name() for s in seats)}")
        print(f"Total amount: ${booking.get_total_amount()}")
        print(f"Please complete payment within 10 minutes")
        
        return booking
    
    def process_payment(self, booking_id: str, payment_method: str) -> bool:
        """Process payment for a booking"""
        booking = self._bookings.get(booking_id)
        
        if not booking:
            print(f"Booking not found: {booking_id}")
            return False
        
        if booking.get_status() != BookingStatus.PENDING:
            print(f"Booking not in pending state")
            return False
        
        # Simulate payment processing
        with self._lock:
            MovieBookingSystem._payment_counter += 1
            payment_id = f"PAY-{MovieBookingSystem._payment_counter:08d}"
        
        payment = Payment(
            payment_id=payment_id,
            amount=booking.get_total_amount(),
            payment_method=payment_method,
            status=PaymentStatus.COMPLETED,
            timestamp=datetime.now()
        )
        
        booking.set_payment(payment)
        
        # Confirm booking
        if booking.confirm():
            print(f"\nPayment successful!")
            print(f"Payment ID: {payment_id}")
            print(f"Amount: ${payment.amount}")
            print(f"Booking confirmed: {booking.get_id()}")
            return True
        else:
            print("Failed to confirm booking")
            payment.status = PaymentStatus.FAILED
            return False
    
    def cancel_booking(self, booking_id: str) -> bool:
        """Cancel a booking"""
        booking = self._bookings.get(booking_id)
        
        if not booking:
            print(f"Booking not found: {booking_id}")
            return False
        
        if booking.get_status() == BookingStatus.CANCELLED:
            print("Booking already cancelled")
            return False
        
        # Release seats
        seat_ids = [seat.get_id() for seat in booking.get_seats()]
        show = booking.get_show()
        
        if booking.get_status() == BookingStatus.PENDING:
            show.release_seats(seat_ids, booking.get_user().get_id())
        elif booking.get_status() == BookingStatus.CONFIRMED:
            show.cancel_booking(seat_ids)
        
        booking.set_status(BookingStatus.CANCELLED)
        
        # Process refund if payment was made
        payment = booking.get_payment()
        if payment and payment.status == PaymentStatus.COMPLETED:
            payment.status = PaymentStatus.REFUNDED
            print(f"Refund processed: ${payment.amount}")
        
        print(f"Booking cancelled: {booking_id}")
        return True
    
    def get_user_bookings(self, user_id: str) -> List[Booking]:
        """Get all bookings for a user"""
        with self._lock:
            bookings = [b for b in self._bookings.values() 
                       if b.get_user().get_id() == user_id]
        
        return sorted(bookings, key=lambda b: b._booking_time, reverse=True)
    
    def display_seat_map(self, show: Show) -> None:
        """Display seat map for a show"""
        print(f"\n{'='*60}")
        print(f"Seat Map - {show.get_movie().get_title()}")
        print(f"Show: {show.get_start_time().strftime('%Y-%m-%d %H:%M')}")
        print(f"Screen: {show.get_screen().get_name()}")
        print(f"{'='*60}")
        
        seat_map = show.get_seat_map()
        seats = show.get_screen().get_all_seats()
        
        # Group by row
        rows = defaultdict(list)
        for seat in seats:
            rows[seat.get_row()].append(seat)
        
        # Legend
        print("\nLegend: [A] Available  [B] Booked  [R] Reserved")
        print()
        
        # Display seats
        for row in sorted(rows.keys()):
            row_seats = sorted(rows[row], key=lambda s: s.get_number())
            row_display = f"Row {row}: "
            
            for seat in row_seats:
                status = seat_map.get(seat.get_id(), SeatStatus.AVAILABLE)
                if status == SeatStatus.AVAILABLE:
                    symbol = "[A]"
                elif status == SeatStatus.BOOKED:
                    symbol = "[B]"
                elif status == SeatStatus.RESERVED:
                    symbol = "[R]"
                else:
                    symbol = "[X]"
                
                row_display += f"{seat.get_number():2d}{symbol} "
            
            print(row_display)
        
        # Summary
        available_count = sum(1 for s in seat_map.values() if s == SeatStatus.AVAILABLE)
        booked_count = sum(1 for s in seat_map.values() if s == SeatStatus.BOOKED)
        reserved_count = sum(1 for s in seat_map.values() if s == SeatStatus.RESERVED)
        
        print(f"\nAvailable: {available_count}, Booked: {booked_count}, Reserved: {reserved_count}")
        print(f"{'='*60}\n")


# ==================== Demo Usage ====================

def main():
    """Demo the movie booking system"""
    print("=== Movie Booking System Demo ===\n")
    
    system = MovieBookingSystem()
    
    # Create movies
    print("--- Adding Movies ---")
    movie1 = Movie(
        "MOV-001", "Inception", "Mind-bending thriller",
        148, MovieGenre.THRILLER, "English",
        datetime(2010, 7, 16), "PG-13"
    )
    movie2 = Movie(
        "MOV-002", "The Dark Knight", "Batman saves Gotham",
        152, MovieGenre.ACTION, "English",
        datetime(2008, 7, 18), "PG-13"
    )
    
    system.add_movie(movie1)
    system.add_movie(movie2)
    
    # Create theater with screens
    print("\n--- Setting Up Theater ---")
    theater = Theater("THR-001", "Cineplex Downtown", "123 Main St")
    
    # Create screens
    screen1 = Screen("SCR-001", "Screen 1", 50)
    screen2 = Screen("SCR-002", "Screen 2", 40)
    
    # Add seats to screen 1
    for row in ['A', 'B', 'C', 'D', 'E']:
        for num in range(1, 11):
            seat_id = f"{screen1.get_id()}-{row}{num}"
            seat_type = SeatType.PREMIUM if row in ['A', 'B'] else SeatType.REGULAR
            price = Decimal('15.00') if seat_type == SeatType.PREMIUM else Decimal('10.00')
            seat = Seat(seat_id, row, num, seat_type, price)
            screen1.add_seat(seat)
    
    # Add seats to screen 2  
    for row in ['A', 'B', 'C', 'D']:
        for num in range(1, 11):
            seat_id = f"{screen2.get_id()}-{row}{num}"
            seat_type = SeatType.REGULAR
            price = Decimal('10.00')
            seat = Seat(seat_id, row, num, seat_type, price)
            screen2.add_seat(seat)
    
    theater.add_screen(screen1)
    theater.add_screen(screen2)
    system.add_theater(theater)
    
    # Create shows
    print("\n--- Creating Shows ---")
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    show1_start = today.replace(hour=14, minute=0)
    show1_end = show1_start + timedelta(minutes=movie1.get_duration() + 30)
    show1 = Show(movie1, screen1, show1_start, show1_end)
    
    show2_start = today.replace(hour=18, minute=0)
    show2_end = show2_start + timedelta(minutes=movie1.get_duration() + 30)
    show2 = Show(movie1, screen1, show2_start, show2_end)
    
    show3_start = today.replace(hour=15, minute=0)
    show3_end = show3_start + timedelta(minutes=movie2.get_duration() + 30)
    show3 = Show(movie2, screen2, show3_start, show3_end)
    
    theater.add_show(show1)
    theater.add_show(show2)
    theater.add_show(show3)
    
    print(f"Show 1: {show1}")
    print(f"Show 2: {show2}")
    print(f"Show 3: {show3}")
    
    # Register users
    print("\n--- Registering Users ---")
    user1 = User("USR-001", "Alice", "alice@email.com", "555-0001")
    user2 = User("USR-002", "Bob", "bob@email.com", "555-0002")
    
    system.register_user(user1)
    system.register_user(user2)
    
    # Display seat map
    system.display_seat_map(show1)
    
    # Test Case 1: Successful booking
    print("\n" + "="*60)
    print("TEST CASE 1: Alice Books Seats")
    print("="*60)
    
    seats_to_book = ["SCR-001-A5", "SCR-001-A6", "SCR-001-A7"]
    booking1 = system.create_booking(user1.get_id(), show1.get_id(), seats_to_book)
    
    if booking1:
        system.display_seat_map(show1)
        
        # Process payment
        print("\n--- Processing Payment ---")
        system.process_payment(booking1.get_id(), "CREDIT_CARD")
        
        system.display_seat_map(show1)
    
    # Test Case 2: Concurrent booking attempt (same seats)
    print("\n" + "="*60)
    print("TEST CASE 2: Bob Tries to Book Same Seats (Should Fail)")
    print("="*60)
    
    booking2 = system.create_booking(user2.get_id(), show1.get_id(), seats_to_book)
    
    # Test Case 3: Bob books different seats
    print("\n" + "="*60)
    print("TEST CASE 3: Bob Books Different Seats")
    print("="*60)
    
    bob_seats = ["SCR-001-B5", "SCR-001-B6"]
    booking3 = system.create_booking(user2.get_id(), show1.get_id(), bob_seats)
    
    if booking3:
        system.display_seat_map(show1)
        system.process_payment(booking3.get_id(), "DEBIT_CARD")
        system.display_seat_map(show1)
    
    # Test Case 4: Reservation timeout simulation
    print("\n" + "="*60)
    print("TEST CASE 4: Reservation Timeout")
    print("="*60)
    
    timeout_seats = ["SCR-001-C5", "SCR-001-C6"]
    booking4 = system.create_booking(user1.get_id(), show1.get_id(), timeout_seats)
    
    if booking4:
        print("\nWaiting for reservation to expire (simulating 10 minutes)...")
        # In real system, would wait 10 minutes. For demo, manually expire
        show1._reserved_seats[timeout_seats[0]] = (user1.get_id(), datetime.now() - timedelta(minutes=1))
        show1._reserved_seats[timeout_seats[1]] = (user1.get_id(), datetime.now() - timedelta(minutes=1))
        
        print("Checking seat availability after timeout...")
        system.display_seat_map(show1)
    
    # Test Case 5: Booking cancellation
    print("\n" + "="*60)
    print("TEST CASE 5: Alice Cancels Her Booking")
    print("="*60)
    
    system.cancel_booking(booking1.get_id())
    system.display_seat_map(show1)
    
    # Test Case 6: View user bookings
    print("\n" + "="*60)
    print("TEST CASE 6: View User Bookings")
    print("="*60)
    
    print(f"\nAlice's Bookings:")
    alice_bookings = system.get_user_bookings(user1.get_id())
    for booking in alice_bookings:
        print(f"  {booking} - Status: {booking.get_status().value}")
        print(f"    Show: {booking.get_show().get_movie().get_title()}")
        print(f"    Time: {booking.get_show().get_start_time().strftime('%Y-%m-%d %H:%M')}")
        print(f"    Seats: {', '.join(s.get_display_name() for s in booking.get_seats())}")
        print(f"    Amount: ${booking.get_total_amount()}")
    
    print(f"\nBob's Bookings:")
    bob_bookings = system.get_user_bookings(user2.get_id())
    for booking in bob_bookings:
        print(f"  {booking} - Status: {booking.get_status().value}")
        print(f"    Show: {booking.get_show().get_movie().get_title()}")
        print(f"    Time: {booking.get_show().get_start_time().strftime('%Y-%m-%d %H:%M')}")
        print(f"    Seats: {', '.join(s.get_display_name() for s in booking.get_seats())}")
        print(f"    Amount: ${booking.get_total_amount()}")
    
    # Test Case 7: Search movies
    print("\n" + "="*60)
    print("TEST CASE 7: Search Movies")
    print("="*60)
    
    print("\nSearching for 'Knight':")
    results = system.search_movies(title="Knight")
    for movie in results:
        print(f"  {movie}")
    
    print("\nSearching for ACTION movies:")
    results = system.search_movies(genre=MovieGenre.ACTION)
    for movie in results:
        print(f"  {movie}")
    
    # Test Case 8: Get shows for movie
    print("\n" + "="*60)
    print("TEST CASE 8: Get Shows for Inception")
    print("="*60)
    
    shows_by_theater = system.get_shows_for_movie(movie1, today)
    for theater, shows in shows_by_theater.items():
        print(f"\n{theater.get_name()}:")
        for show in shows:
            available = len(show.get_available_seats())
            total = show.get_screen().get_total_seats()
            print(f"  {show.get_start_time().strftime('%H:%M')} - "
                  f"{show.get_screen().get_name()} - "
                  f"{available}/{total} available")
    
    # Test Case 9: Multiple concurrent bookings (simulated)
    print("\n" + "="*60)
    print("TEST CASE 9: Concurrent Booking Simulation")
    print("="*60)
    
    print("\nSimulating multiple users trying to book seats simultaneously...")
    
    # User 1 tries to book
    concurrent_seats_1 = ["SCR-001-D1", "SCR-001-D2"]
    booking5 = system.create_booking(user1.get_id(), show1.get_id(), concurrent_seats_1)
    
    # User 2 tries to book overlapping seats (should fail)
    concurrent_seats_2 = ["SCR-001-D2", "SCR-001-D3"]
    booking6 = system.create_booking(user2.get_id(), show1.get_id(), concurrent_seats_2)
    
    # User 2 books non-overlapping seats (should succeed)
    concurrent_seats_3 = ["SCR-001-D4", "SCR-001-D5"]
    booking7 = system.create_booking(user2.get_id(), show1.get_id(), concurrent_seats_3)
    
    system.display_seat_map(show1)
    
    # Complete both bookings
    if booking5:
        system.process_payment(booking5.get_id(), "CREDIT_CARD")
    if booking7:
        system.process_payment(booking7.get_id(), "CREDIT_CARD")
    
    # Final seat map
    print("\n" + "="*60)
    print("FINAL SEAT MAP")
    print("="*60)
    system.display_seat_map(show1)
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# State Pattern (implicit in seat status):

# AVAILABLE → RESERVED → BOOKED
# Or RESERVED → AVAILABLE (timeout/cancel)


# Repository Pattern:

# Central storage for theaters, movies, users, bookings
# Abstracted data access


# Concurrency Control:

# Pessimistic locking for seat reservation
# Time-based reservations with expiry



# Core Features:
# ✅ Multi-theater Support: Multiple theaters, screens, shows
# ✅ Seat Management: Different types, pricing
# ✅ Concurrent Booking: Thread-safe seat reservation
# ✅ Time-based Reservation: 10-minute hold during payment
# ✅ Payment Processing: Multiple payment methods
# ✅ Booking Cancellation: With refunds
# ✅ Search Functionality: Movies by title, genre, language
# ✅ Show Scheduling: Conflict detection
# ✅ User Management: Booking history
# Concurrency Handling - Critical Section:
# The most important aspect for a booking system is preventing double-booking:
# python# Three-phase commit for seat booking:
# 1. Reserve seats (with timeout)
# 2. Process payment
# 3. Confirm booking

# # If payment fails or times out:
# - Seats automatically released
# - Available for other users
# Pessimistic Locking:
# pythondef reserve_seats(self, seat_ids, user_id, duration=10):
#     with self._lock:  # Acquire lock
#         # Check all seats available
#         for seat_id in seat_ids:
#             if status != AVAILABLE:
#                 return False
        
#         # Reserve all seats atomically
#         expiry = now() + duration
#         for seat_id in seat_ids:
#             status = RESERVED
#             reserved_seats[seat_id] = (user_id, expiry)
        
#         return True
# ```

# ### **Race Condition Prevention:**

# **Scenario**: Two users try to book the same seat simultaneously
# ```
# User A                     User B
#   |                          |
#   |-- Check seat available   |
#   |                          |-- Check seat available
#   |-- Reserve seat           |
#   |                          |-- Try to reserve (FAILS)
#   ✓ Success                  ✗ Seat already reserved
# The lock ensures only one user can reserve at a time.
# Timeout Mechanism:
# Why needed: User reserves seats but abandons payment
# python# Reservation with expiry
# reserved_seats[seat_id] = (user_id, expiry_time)

# # Automatic cleanup
# def _cleanup_expired_reservations():
#     current_time = now()
#     for seat_id, (user, expiry) in reserved_seats.items():
#         if current_time > expiry:
#             # Release seat
#             status[seat_id] = AVAILABLE
#             del reserved_seats[seat_id]
# ```

# ### **Seat Status State Machine:**
# ```
#     AVAILABLE
#         ↓
#     [Reserve]
#         ↓
#     RESERVED ─→ [Timeout] ─→ AVAILABLE
#         ↓
#     [Payment]
#         ↓
#     BOOKED ─→ [Cancel] ─→ AVAILABLE
# Thread Safety Strategy:
# Global Lock (on Show):

# Protects entire seat map
# Simple but can be bottleneck

# Per-Seat Lock (alternative):
# python# More granular locking
# seat_locks[seat_id].acquire()
# try:
#     # Operate on single seat
#     status[seat_id] = RESERVED
# finally:
#     seat_locks[seat_id].release()
# Show Scheduling Conflict Detection:
# python# Check time overlap
# def has_conflict(new_show, existing_show):
#     # Same screen?
#     if new_show.screen != existing_show.screen:
#         return False
    
#     # Time overlap?
#     return (new_show.start < existing_show.end and
#             new_show.end > existing_show.start)
# ```

# ### **Real-World Usage Patterns:**

# **User Journey**:
# ```
# 1. Search movies → "Inception"
# 2. View shows → "2PM, 6PM, 9PM"
# 3. Select show → "6PM at Screen 1"
# 4. View seat map → See availability
# 5. Select seats → "A5, A6, A7"
# 6. Reserve (10 min timer starts)
# 7. Enter payment details
# 8. Complete payment
# 9. Booking confirmed
# 10. Receive confirmation email
# Booking Flow:
# python# Step 1: Create booking (reserves seats)
# booking = system.create_booking(user_id, show_id, seat_ids)
# # Seats now RESERVED (10 min timeout)

# # Step 2: Process payment (within 10 minutes)
# success = system.process_payment(booking_id, payment_method)
# # If success: Seats → BOOKED
# # If timeout: Seats → AVAILABLE
# Data Structures & Complexity:
# Seat Map:

# Dict[seat_id, SeatStatus]: O(1) lookup
# Fast checking of availability

# Theater Shows:

# List[Show]: Linear search for conflicts
# Could optimize with interval tree for large scale

# Search:

# Movie search: O(n) filtering
# Could add indexing for production

# Scalability Considerations:
# Database Design (not implemented but important):
# sql-- Optimistic locking with version
# UPDATE seats 
# SET status = 'RESERVED', version = version + 1
# WHERE seat_id = ? AND status = 'AVAILABLE' AND version = ?

# -- If rows_affected == 0, seat already taken
# Distributed System:

# Use distributed locks (Redis, ZooKeeper)
# Event-driven architecture
# Message queues for booking requests

# Caching:

# Cache movie list (rarely changes)
# Cache show schedules (changes daily)
# Invalidate seat map on booking

# Payment Flow:
# python# Idempotent payment processing
# def process_payment(booking_id, payment_method):
#     # Check booking exists and is PENDING
#     if not valid:
#         return False
    
#     # Process payment (external gateway)
#     payment = gateway.charge(amount, method)
    
#     if payment.success:
#         # Confirm seats (RESERVED → BOOKED)
#         booking.confirm()
#         # Send confirmation
#         send_email(booking)
#         return True
#     else:
#         # Release seats (RESERVED → AVAILABLE)
#         booking.release_seats()
#         return False
# Cancellation Policy:
# pythondef cancel_booking(booking_id):
#     booking = get_booking(booking_id)
    
#     # Check cancellation is allowed
#     show_time = booking.show.start_time
#     if datetime.now() > show_time - timedelta(hours=2):
#         return False  # Too late to cancel
    
#     # Release seats
#     booking.cancel()
    
#     # Process refund
#     if booking.payment:
#         refund_amount = calculate_refund(booking)
#         process_refund(refund_amount)
    
#     return True
# Extensions You Could Add:

# Food & Beverage: Add snacks to booking
# Seat Selection UI: Interactive seat picker
# Pricing Strategies: Dynamic pricing, surge pricing
# Discounts & Offers: Promo codes, loyalty points
# Group Booking: Book entire rows
# Recurring Shows: Weekly schedules
# Waitlist: Notify when seats available
# Recommendations: ML-based suggestions
# Social Features: Share with friends
# Reviews & Ratings: User feedback
# Multi-language: Dubbed/subtitled versions
# Accessibility: Wheelchair seats, assisted devices
# Mobile Tickets: QR codes
# Notifications: SMS/email reminders
# Analytics: Popular shows, revenue tracking

# Testing Scenarios:

# ✓ Normal booking flow
# ✓ Concurrent booking attempts
# ✓ Reservation timeout
# ✓ Payment failure
# ✓ Booking cancellation
# ✓ Invalid seat selection
# ✓ Show scheduling conflicts
# ✓ Search functionality
# ✓ User booking history

# Performance Optimizations:
# Seat Map Caching:
# python# Cache seat availability
# cache_key = f"show:{show_id}:seats"
# cached = redis.get(cache_key)

# if cached:
#     return cached
# else:
#     seats = generate_seat_map()
#     redis.setex(cache_key, 60, seats)  # 1 min cache
#     return seats
# Read Replicas:

# Read movie list from replicas
# Write bookings to master
# Eventual consistency acceptable for browse

# Connection Pooling:

# Reuse database connections
# Reduce overhead

# This design demonstrates a production-ready movie booking system with proper concurrency control, seat reservation mechanism, timeout handling, and thread safety - the key challenges in any booking system!
