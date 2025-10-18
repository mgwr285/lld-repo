from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
import uuid
import random
import string


# ==================== Enums ====================

class LockerSize(Enum):
    """Locker compartment sizes"""
    EXTRA_SMALL = "extra_small"  # < 12x10x8 inches
    SMALL = "small"              # < 16x12x10 inches
    MEDIUM = "medium"            # < 20x16x12 inches
    LARGE = "large"              # < 24x18x16 inches
    EXTRA_LARGE = "extra_large"  # < 30x20x18 inches


class LockerStatus(Enum):
    """Status of individual locker"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    OUT_OF_SERVICE = "out_of_service"


class PackageStatus(Enum):
    """Package delivery status"""
    IN_TRANSIT = "in_transit"
    DELIVERED_TO_LOCKER = "delivered_to_locker"
    PICKED_UP = "picked_up"
    RETURNED_TO_SENDER = "returned_to_sender"
    EXPIRED = "expired"


class LocationStatus(Enum):
    """Locker location operational status"""
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class NotificationType(Enum):
    """Notification types"""
    DELIVERY = "delivery"
    PICKUP_REMINDER = "pickup_reminder"
    EXPIRY_WARNING = "expiry_warning"
    RETURN_NOTICE = "return_notice"


# ==================== Models ====================

class Location:
    """Geographic location with address"""
    
    def __init__(self, latitude: float, longitude: float, address: str,
                 city: str, state: str, zip_code: str):
        self._latitude = latitude
        self._longitude = longitude
        self._address = address
        self._city = city
        self._state = state
        self._zip_code = zip_code
    
    def get_address(self) -> str:
        return self._address
    
    def get_city(self) -> str:
        return self._city
    
    def get_coordinates(self) -> tuple[float, float]:
        return (self._latitude, self._longitude)
    
    def calculate_distance(self, other: 'Location') -> float:
        """Calculate distance in miles (simplified)"""
        # Simplified distance calculation (should use Haversine formula)
        lat_diff = abs(self._latitude - other._latitude)
        lon_diff = abs(self._longitude - other._longitude)
        return ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 69  # Approx miles
    
    def to_dict(self) -> Dict:
        return {
            'address': self._address,
            'city': self._city,
            'state': self._state,
            'zip_code': self._zip_code,
            'coordinates': f"{self._latitude}, {self._longitude}"
        }


class Customer:
    """Customer using locker service"""
    
    def __init__(self, customer_id: str, name: str, email: str, phone: str):
        self._customer_id = customer_id
        self._name = name
        self._email = email
        self._phone = phone
        self._verified = True
    
    def get_id(self) -> str:
        return self._customer_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_phone(self) -> str:
        return self._phone
    
    def to_dict(self) -> Dict:
        return {
            'customer_id': self._customer_id,
            'name': self._name,
            'email': self._email,
            'phone': self._phone
        }


class Package:
    """Package to be delivered"""
    
    def __init__(self, package_id: str, tracking_number: str,
                 customer: Customer, size: LockerSize):
        self._package_id = package_id
        self._tracking_number = tracking_number
        self._customer = customer
        self._size = size
        self._status = PackageStatus.IN_TRANSIT
        
        # Delivery details
        self._locker_location_id: Optional[str] = None
        self._locker_id: Optional[str] = None
        self._pickup_code: Optional[str] = None
        
        # Timestamps
        self._created_at = datetime.now()
        self._delivered_at: Optional[datetime] = None
        self._pickup_deadline: Optional[datetime] = None
        self._picked_up_at: Optional[datetime] = None
        
        # Metadata
        self._delivery_attempts = 0
        self._notes: List[str] = []
    
    def get_id(self) -> str:
        return self._package_id
    
    def get_tracking_number(self) -> str:
        return self._tracking_number
    
    def get_customer(self) -> Customer:
        return self._customer
    
    def get_size(self) -> LockerSize:
        return self._size
    
    def get_status(self) -> PackageStatus:
        return self._status
    
    def get_pickup_code(self) -> Optional[str]:
        return self._pickup_code
    
    def get_locker_location_id(self) -> Optional[str]:
        return self._locker_location_id
    
    def get_locker_id(self) -> Optional[str]:
        return self._locker_id
    
    def set_delivered(self, locker_location_id: str, locker_id: str,
                     pickup_code: str, pickup_hours: int = 72) -> None:
        """Mark package as delivered to locker"""
        self._status = PackageStatus.DELIVERED_TO_LOCKER
        self._locker_location_id = locker_location_id
        self._locker_id = locker_id
        self._pickup_code = pickup_code
        self._delivered_at = datetime.now()
        self._pickup_deadline = datetime.now() + timedelta(hours=pickup_hours)
    
    def set_picked_up(self) -> None:
        """Mark package as picked up"""
        self._status = PackageStatus.PICKED_UP
        self._picked_up_at = datetime.now()
    
    def set_returned(self) -> None:
        """Mark package as returned to sender"""
        self._status = PackageStatus.RETURNED_TO_SENDER
    
    def is_expired(self) -> bool:
        """Check if pickup deadline has passed"""
        if self._pickup_deadline:
            return datetime.now() > self._pickup_deadline
        return False
    
    def get_time_remaining(self) -> Optional[timedelta]:
        """Get time remaining until deadline"""
        if self._pickup_deadline and not self.is_expired():
            return self._pickup_deadline - datetime.now()
        return None
    
    def add_note(self, note: str) -> None:
        self._notes.append(f"{datetime.now().isoformat()}: {note}")
    
    def increment_delivery_attempt(self) -> None:
        self._delivery_attempts += 1
    
    def to_dict(self) -> Dict:
        return {
            'package_id': self._package_id,
            'tracking_number': self._tracking_number,
            'customer': self._customer.get_name(),
            'size': self._size.value,
            'status': self._status.value,
            'pickup_code': self._pickup_code,
            'delivered_at': self._delivered_at.isoformat() if self._delivered_at else None,
            'pickup_deadline': self._pickup_deadline.isoformat() if self._pickup_deadline else None,
            'time_remaining': str(self.get_time_remaining()) if self.get_time_remaining() else None,
            'is_expired': self.is_expired(),
            'delivery_attempts': self._delivery_attempts
        }


class Locker:
    """Individual locker compartment"""
    
    def __init__(self, locker_id: str, size: LockerSize):
        self._locker_id = locker_id
        self._size = size
        self._status = LockerStatus.AVAILABLE
        self._package: Optional[Package] = None
        self._last_opened: Optional[datetime] = None
    
    def get_id(self) -> str:
        return self._locker_id
    
    def get_size(self) -> LockerSize:
        return self._size
    
    def get_status(self) -> LockerStatus:
        return self._status
    
    def is_available(self) -> bool:
        return self._status == LockerStatus.AVAILABLE
    
    def can_fit(self, package_size: LockerSize) -> bool:
        """Check if locker can fit package"""
        # Compare enum values (smaller value = smaller size)
        size_order = {
            LockerSize.EXTRA_SMALL: 1,
            LockerSize.SMALL: 2,
            LockerSize.MEDIUM: 3,
            LockerSize.LARGE: 4,
            LockerSize.EXTRA_LARGE: 5
        }
        return size_order[self._size] >= size_order[package_size]
    
    def assign_package(self, package: Package) -> bool:
        """Assign package to locker"""
        if not self.is_available():
            return False
        
        if not self.can_fit(package.get_size()):
            return False
        
        self._package = package
        self._status = LockerStatus.OCCUPIED
        return True
    
    def release_package(self) -> Optional[Package]:
        """Release package from locker"""
        if self._status != LockerStatus.OCCUPIED:
            return None
        
        package = self._package
        self._package = None
        self._status = LockerStatus.AVAILABLE
        self._last_opened = datetime.now()
        
        return package
    
    def get_package(self) -> Optional[Package]:
        return self._package
    
    def set_out_of_service(self) -> None:
        self._status = LockerStatus.OUT_OF_SERVICE
    
    def set_available(self) -> None:
        if self._package is None:
            self._status = LockerStatus.AVAILABLE
    
    def to_dict(self) -> Dict:
        return {
            'locker_id': self._locker_id,
            'size': self._size.value,
            'status': self._status.value,
            'has_package': self._package is not None,
            'package_id': self._package.get_id() if self._package else None
        }


class LockerLocation:
    """Physical location with multiple lockers"""
    
    def __init__(self, location_id: str, name: str, location: Location):
        self._location_id = location_id
        self._name = name
        self._location = location
        self._status = LocationStatus.ACTIVE
        
        # Lockers organized by size
        self._lockers: Dict[str, Locker] = {}
        self._lockers_by_size: Dict[LockerSize, List[Locker]] = {
            size: [] for size in LockerSize
        }
        
        # Operating hours (simplified - 24/7 for demo)
        self._operating_hours = "24/7"
        
        # Capacity tracking
        self._total_capacity = 0
        self._occupied_count = 0
        
        # Metadata
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._location_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_location(self) -> Location:
        return self._location
    
    def get_status(self) -> LocationStatus:
        return self._status
    
    def is_operational(self) -> bool:
        return self._status == LocationStatus.ACTIVE
    
    def add_locker(self, locker: Locker) -> None:
        """Add a locker to this location"""
        self._lockers[locker.get_id()] = locker
        self._lockers_by_size[locker.get_size()].append(locker)
        self._total_capacity += 1
    
    def get_locker(self, locker_id: str) -> Optional[Locker]:
        return self._lockers.get(locker_id)
    
    def find_available_locker(self, package_size: LockerSize) -> Optional[Locker]:
        """Find available locker that can fit the package"""
        # Try exact size first
        for locker in self._lockers_by_size[package_size]:
            if locker.is_available():
                return locker
        
        # Try larger sizes
        size_order = [
            LockerSize.EXTRA_SMALL,
            LockerSize.SMALL,
            LockerSize.MEDIUM,
            LockerSize.LARGE,
            LockerSize.EXTRA_LARGE
        ]
        
        package_index = size_order.index(package_size)
        for size in size_order[package_index + 1:]:
            for locker in self._lockers_by_size[size]:
                if locker.is_available():
                    return locker
        
        return None
    
    def get_occupancy_rate(self) -> float:
        """Get percentage of occupied lockers"""
        if self._total_capacity == 0:
            return 0.0
        
        occupied = sum(1 for locker in self._lockers.values() 
                      if locker.get_status() == LockerStatus.OCCUPIED)
        return (occupied / self._total_capacity) * 100
    
    def get_available_count(self, size: Optional[LockerSize] = None) -> int:
        """Get count of available lockers"""
        if size:
            return sum(1 for locker in self._lockers_by_size[size] 
                      if locker.is_available())
        
        return sum(1 for locker in self._lockers.values() 
                  if locker.is_available())
    
    def has_capacity(self, package_size: LockerSize) -> bool:
        """Check if location has capacity for package"""
        return self.find_available_locker(package_size) is not None
    
    def set_status(self, status: LocationStatus) -> None:
        self._status = status
    
    def get_size_distribution(self) -> Dict[str, int]:
        """Get distribution of locker sizes"""
        distribution = {}
        for size in LockerSize:
            distribution[size.value] = len(self._lockers_by_size[size])
        return distribution
    
    def to_dict(self) -> Dict:
        return {
            'location_id': self._location_id,
            'name': self._name,
            'location': self._location.to_dict(),
            'status': self._status.value,
            'total_lockers': self._total_capacity,
            'available_lockers': self.get_available_count(),
            'occupancy_rate': f"{self.get_occupancy_rate():.1f}%",
            'size_distribution': self.get_size_distribution(),
            'operating_hours': self._operating_hours
        }


class Notification:
    """Notification sent to customer"""
    
    def __init__(self, notification_id: str, customer: Customer,
                 notification_type: NotificationType, message: str,
                 package: Optional[Package] = None):
        self._notification_id = notification_id
        self._customer = customer
        self._notification_type = notification_type
        self._message = message
        self._package = package
        self._sent_at = datetime.now()
        self._read = False
    
    def get_id(self) -> str:
        return self._notification_id
    
    def mark_read(self) -> None:
        self._read = True
    
    def to_dict(self) -> Dict:
        return {
            'notification_id': self._notification_id,
            'type': self._notification_type.value,
            'message': self._message,
            'sent_at': self._sent_at.isoformat(),
            'read': self._read
        }


# ==================== Amazon Locker Service ====================

class AmazonLockerService:
    """
    Main Amazon Locker Service
    
    Features:
    - Find nearby locker locations
    - Allocate lockers for packages
    - Deliver packages to lockers
    - Generate pickup codes
    - Handle package pickup
    - Manage expired packages
    - Send notifications
    - Track locker utilization
    """
    
    def __init__(self):
        # Storage
        self._customers: Dict[str, Customer] = {}
        self._locations: Dict[str, LockerLocation] = {}
        self._packages: Dict[str, Package] = {}
        self._notifications: List[Notification] = []
        
        # Indexes
        self._packages_by_tracking: Dict[str, str] = {}  # tracking -> package_id
        self._packages_by_customer: Dict[str, Set[str]] = {}  # customer_id -> package_ids
        self._packages_at_location: Dict[str, Set[str]] = {}  # location_id -> package_ids
        
        # Configuration
        self._pickup_window_hours = 72  # Default pickup window
        self._max_delivery_attempts = 3
    
    # ==================== Customer Management ====================
    
    def register_customer(self, name: str, email: str, phone: str) -> Customer:
        """Register a new customer"""
        customer_id = str(uuid.uuid4())
        customer = Customer(customer_id, name, email, phone)
        
        self._customers[customer_id] = customer
        self._packages_by_customer[customer_id] = set()
        
        print(f"✅ Customer registered: {name}")
        return customer
    
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self._customers.get(customer_id)
    
    # ==================== Location Management ====================
    
    def add_locker_location(self, name: str, location: Location,
                           locker_config: Dict[LockerSize, int]) -> LockerLocation:
        """Add a new locker location with specified locker sizes"""
        location_id = str(uuid.uuid4())
        locker_location = LockerLocation(location_id, name, location)
        
        # Add lockers based on configuration
        for size, count in locker_config.items():
            for i in range(count):
                locker_id = f"{location_id[:8]}-{size.value[:2].upper()}{i+1:03d}"
                locker = Locker(locker_id, size)
                locker_location.add_locker(locker)
        
        self._locations[location_id] = locker_location
        self._packages_at_location[location_id] = set()
        
        print(f"✅ Locker location added: {name} with {locker_location._total_capacity} lockers")
        return locker_location
    
    def get_location(self, location_id: str) -> Optional[LockerLocation]:
        return self._locations.get(location_id)
    
    def find_nearby_locations(self, customer_location: Location,
                             radius_miles: float = 5.0,
                             package_size: Optional[LockerSize] = None) -> List[LockerLocation]:
        """Find locker locations within radius"""
        nearby = []
        
        for location in self._locations.values():
            if not location.is_operational():
                continue
            
            distance = customer_location.calculate_distance(location.get_location())
            
            if distance <= radius_miles:
                # Check capacity if package size specified
                if package_size is None or location.has_capacity(package_size):
                    nearby.append((location, distance))
        
        # Sort by distance
        nearby.sort(key=lambda x: x[1])
        
        return [loc for loc, _ in nearby]
    
    # ==================== Package Management ====================
    
    def create_package(self, tracking_number: str, customer: Customer,
                      size: LockerSize) -> Package:
        """Create a new package for delivery"""
        package_id = str(uuid.uuid4())
        package = Package(package_id, tracking_number, customer, size)
        
        self._packages[package_id] = package
        self._packages_by_tracking[tracking_number] = package_id
        self._packages_by_customer[customer.get_id()].add(package_id)
        
        print(f"📦 Package created: {tracking_number} for {customer.get_name()}")
        return package
    
    def get_package(self, package_id: str) -> Optional[Package]:
        return self._packages.get(package_id)
    
    def get_package_by_tracking(self, tracking_number: str) -> Optional[Package]:
        package_id = self._packages_by_tracking.get(tracking_number)
        if package_id:
            return self._packages.get(package_id)
        return None
    
    # ==================== Delivery ====================
    
    def allocate_locker(self, package: Package, preferred_location_id: Optional[str] = None) -> Optional[tuple[LockerLocation, Locker]]:
        """Allocate a locker for package delivery"""
        
        # Try preferred location first
        if preferred_location_id:
            location = self._locations.get(preferred_location_id)
            if location and location.is_operational():
                locker = location.find_available_locker(package.get_size())
                if locker:
                    return (location, locker)
        
        # Try all locations
        for location in self._locations.values():
            if not location.is_operational():
                continue
            
            locker = location.find_available_locker(package.get_size())
            if locker:
                return (location, locker)
        
        return None
    
    def _generate_pickup_code(self, length: int = 6) -> str:
        """Generate random pickup code"""
        return ''.join(random.choices(string.digits, k=length))
    
    def deliver_package(self, package_id: str,
                       preferred_location_id: Optional[str] = None) -> bool:
        """Deliver package to locker"""
        package = self._packages.get(package_id)
        if not package:
            print(f"❌ Package not found: {package_id}")
            return False
        
        if package.get_status() != PackageStatus.IN_TRANSIT:
            print(f"❌ Package not in transit: {package.get_status().value}")
            return False
        
        # Allocate locker
        allocation = self.allocate_locker(package, preferred_location_id)
        if not allocation:
            print(f"❌ No available locker for package size: {package.get_size().value}")
            package.increment_delivery_attempt()
            return False
        
        location, locker = allocation
        
        # Assign package to locker
        if not locker.assign_package(package):
            print(f"❌ Failed to assign package to locker")
            return False
        
        # Generate pickup code
        pickup_code = self._generate_pickup_code()
        
        # Update package
        package.set_delivered(
            location.get_id(),
            locker.get_id(),
            pickup_code,
            self._pickup_window_hours
        )
        
        # Track package at location
        self._packages_at_location[location.get_id()].add(package_id)
        
        # Send delivery notification
        self._send_notification(
            package.get_customer(),
            NotificationType.DELIVERY,
            f"Your package has been delivered to {location.get_name()}. "
            f"Pickup code: {pickup_code}. Must pick up by {package._pickup_deadline.strftime('%Y-%m-%d %H:%M')}",
            package
        )
        
        print(f"✅ Package delivered to {location.get_name()}, Locker {locker.get_id()}")
        print(f"   Pickup code: {pickup_code}")
        
        return True
    
    # ==================== Pickup ====================
    
    def pickup_package(self, tracking_number: str, pickup_code: str) -> Optional[Package]:
        """Customer picks up package using code"""
        package = self.get_package_by_tracking(tracking_number)
        
        if not package:
            print(f"❌ Package not found: {tracking_number}")
            return None
        
        if package.get_status() != PackageStatus.DELIVERED_TO_LOCKER:
            print(f"❌ Package not available for pickup: {package.get_status().value}")
            return None
        
        # Verify pickup code
        if package.get_pickup_code() != pickup_code:
            print(f"❌ Invalid pickup code")
            return None
        
        # Check if expired
        if package.is_expired():
            print(f"❌ Package pickup window has expired")
            return None
        
        # Get locker
        location = self._locations.get(package.get_locker_location_id())
        if not location:
            print(f"❌ Locker location not found")
            return None
        
        locker = location.get_locker(package.get_locker_id())
        if not locker:
            print(f"❌ Locker not found")
            return None
        
        # Release package from locker
        released_package = locker.release_package()
        if not released_package:
            print(f"❌ Failed to release package from locker")
            return None
        
        # Update package status
        package.set_picked_up()
        
        # Remove from location tracking
        self._packages_at_location[location.get_id()].discard(package.get_id())
        
        print(f"✅ Package picked up successfully!")
        print(f"   Location: {location.get_name()}")
        print(f"   Locker: {locker.get_id()}")
        
        return package
    
    # ==================== Expired Packages ====================
    
    def check_expired_packages(self) -> List[Package]:
        """Check and process expired packages"""
        expired_packages = []
        
        for package in self._packages.values():
            if (package.get_status() == PackageStatus.DELIVERED_TO_LOCKER and
                package.is_expired()):
                
                expired_packages.append(package)
                
                # Get locker and release package
                location = self._locations.get(package.get_locker_location_id())
                if location:
                    locker = location.get_locker(package.get_locker_id())
                    if locker:
                        locker.release_package()
                    
                    self._packages_at_location[location.get_id()].discard(package.get_id())
                
                # Mark as returned
                package.set_returned()
                package.add_note("Package not picked up within deadline - returned to sender")
                
                # Send notification
                self._send_notification(
                    package.get_customer(),
                    NotificationType.RETURN_NOTICE,
                    f"Your package {package.get_tracking_number()} was not picked up and has been returned to sender.",
                    package
                )
        
        if expired_packages:
            print(f"🔄 Processed {len(expired_packages)} expired packages")
        
        return expired_packages
    
    def send_expiry_warnings(self, hours_before: int = 24) -> int:
        """Send warnings for packages expiring soon"""
        warning_count = 0
        cutoff_time = datetime.now() + timedelta(hours=hours_before)
        
        for package in self._packages.values():
            if (package.get_status() == PackageStatus.DELIVERED_TO_LOCKER and
                package._pickup_deadline and
                package._pickup_deadline <= cutoff_time and
                not package.is_expired()):
                
                time_remaining = package.get_time_remaining()
                
                self._send_notification(
                    package.get_customer(),
                    NotificationType.EXPIRY_WARNING,
                    f"Reminder: Your package at {self._locations.get(package.get_locker_location_id()).get_name()} "
                    f"must be picked up within {time_remaining}. Pickup code: {package.get_pickup_code()}",
                    package
                )
                
                warning_count += 1
        
        if warning_count:
            print(f"⚠️  Sent {warning_count} expiry warnings")
        
        return warning_count
    
    # ==================== Notifications ====================
    
    def _send_notification(self, customer: Customer, notification_type: NotificationType,
                          message: str, package: Optional[Package] = None) -> None:
        """Send notification to customer"""
        notification_id = str(uuid.uuid4())
        notification = Notification(
            notification_id,
            customer,
            notification_type,
            message,
            package
        )
        
        self._notifications.append(notification)
        
        # In real system, would send email/SMS
        print(f"📧 Notification sent to {customer.get_email()}: {message[:50]}...")
    
    def get_customer_notifications(self, customer_id: str,
                                   unread_only: bool = False) -> List[Notification]:
        """Get notifications for customer"""
        notifications = [
            n for n in self._notifications
            if n._customer.get_id() == customer_id
        ]
        
        if unread_only:
            notifications = [n for n in notifications if not n._read]
        
        return sorted(notifications, key=lambda n: n._sent_at, reverse=True)
    
    # ==================== Customer Queries ====================
    
    def get_customer_packages(self, customer_id: str,
                             status: Optional[PackageStatus] = None) -> List[Package]:
        """Get packages for customer"""
        package_ids = self._packages_by_customer.get(customer_id, set())
        packages = [self._packages[pid] for pid in package_ids]
        
        if status:
            packages = [p for p in packages if p.get_status() == status]
        
        return packages
    
    def get_active_deliveries(self, customer_id: str) -> List[Package]:
        """Get customer's packages currently in lockers"""
        return self.get_customer_packages(customer_id, PackageStatus.DELIVERED_TO_LOCKER)
    
    # ==================== Location Queries ====================
    
    def get_location_packages(self, location_id: str) -> List[Package]:
        """Get all packages at a location"""
        package_ids = self._packages_at_location.get(location_id, set())
        return [self._packages[pid] for pid in package_ids]
    
    def get_location_statistics(self, location_id: str) -> Optional[Dict]:
        """Get statistics for a location"""
        location = self._locations.get(location_id)
        if not location:
            return None
        
        packages = self.get_location_packages(location_id)
        
        return {
            'location': location.to_dict(),
            'current_packages': len(packages),
            'packages_expiring_soon': len([
                p for p in packages
                if p.get_time_remaining() and p.get_time_remaining() < timedelta(hours=24)
            ]),
            'available_by_size': {
                size.value: location.get_available_count(size)
                for size in LockerSize
            }
        }
    
    # ==================== System Statistics ====================
    
    def get_system_statistics(self) -> Dict:
        """Get overall system statistics"""
        total_lockers = sum(loc._total_capacity for loc in self._locations.values())
        occupied_lockers = sum(
            1 for loc in self._locations.values()
            for locker in loc._lockers.values()
            if locker.get_status() == LockerStatus.OCCUPIED
        )
        
        packages_by_status = {}
        for status in PackageStatus:
            packages_by_status[status.value] = len([
                p for p in self._packages.values()
                if p.get_status() == status
            ])
        
        return {
            'total_locations': len(self._locations),
            'active_locations': len([
                loc for loc in self._locations.values()
                if loc.is_operational()
            ]),
            'total_lockers': total_lockers,
            'occupied_lockers': occupied_lockers,
            'utilization_rate': f"{(occupied_lockers/total_lockers*100):.1f}%" if total_lockers > 0 else "0%",
            'total_customers': len(self._customers),
            'total_packages': len(self._packages),
            'packages_by_status': packages_by_status,
            'total_notifications': len(self._notifications)
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_amazon_locker_service():
    """Comprehensive demo of Amazon Locker service"""
    
    print_section("AMAZON LOCKER SERVICE DEMO")
    
    service = AmazonLockerService()
    
    # ==================== Register Customers ====================
    print_section("1. Register Customers")
    
    alice = service.register_customer("Alice Johnson", "alice@email.com", "+1-555-0101")
    bob = service.register_customer("Bob Smith", "bob@email.com", "+1-555-0102")
    charlie = service.register_customer("Charlie Brown", "charlie@email.com", "+1-555-0103")
    
    # ==================== Add Locker Locations ====================
    print_section("2. Add Locker Locations")
    
    # Location 1: Downtown
    downtown_loc = Location(
        40.7589, -73.9851,
        "123 Main St, Times Square",
        "New York", "NY", "10036"
    )
    
    downtown = service.add_locker_location(
        "Times Square Hub",
        downtown_loc,
        {
            LockerSize.EXTRA_SMALL: 20,
            LockerSize.SMALL: 30,
            LockerSize.MEDIUM: 25,
            LockerSize.LARGE: 15,
            LockerSize.EXTRA_LARGE: 10
        }
    )
    
    # Location 2: Midtown
    midtown_loc = Location(
        40.7549, -73.9840,
        "456 Park Ave",
        "New York", "NY", "10022"
    )
    
    midtown = service.add_locker_location(
        "Park Avenue Station",
        midtown_loc,
        {
            LockerSize.EXTRA_SMALL: 15,
            LockerSize.SMALL: 25,
            LockerSize.MEDIUM: 20,
            LockerSize.LARGE: 10,
            LockerSize.EXTRA_LARGE: 5
        }
    )
    
    # Location 3: Uptown
    uptown_loc = Location(
        40.7829, -73.9654,
        "789 Central Park West",
        "New York", "NY", "10024"
    )
    
    uptown = service.add_locker_location(
        "Central Park Locker",
        uptown_loc,
        {
            LockerSize.EXTRA_SMALL: 10,
            LockerSize.SMALL: 20,
            LockerSize.MEDIUM: 15,
            LockerSize.LARGE: 10,
            LockerSize.EXTRA_LARGE: 5
        }
    )
    
    print(f"\n📍 Added {len(service._locations)} locker locations")
    
    # ==================== Find Nearby Locations ====================
    print_section("3. Find Nearby Locker Locations")
    
    customer_loc = Location(40.7580, -73.9855, "Customer Address", "New York", "NY", "10036")
    
    nearby = service.find_nearby_locations(customer_loc, radius_miles=2.0)
    
    print(f"\n🔍 Locations within 2 miles:")
    for location in nearby:
        distance = customer_loc.calculate_distance(location.get_location())
        print(f"   • {location.get_name()}: {distance:.2f} miles")
        print(f"     {location.get_location().get_address()}")
        print(f"     Available lockers: {location.get_available_count()}/{location._total_capacity}")
        print(f"     Occupancy: {location.get_occupancy_rate():.1f}%")
    
    # ==================== Create Packages ====================
    print_section("4. Create Packages")
    
    # Alice's packages
    package1 = service.create_package("TRK001", alice, LockerSize.SMALL)
    package2 = service.create_package("TRK002", alice, LockerSize.MEDIUM)
    
    # Bob's packages
    package3 = service.create_package("TRK003", bob, LockerSize.LARGE)
    package4 = service.create_package("TRK004", bob, LockerSize.EXTRA_SMALL)
    
    # Charlie's package
    package5 = service.create_package("TRK005", charlie, LockerSize.MEDIUM)
    
    print(f"\n📦 Created {len(service._packages)} packages")
    
    # ==================== Deliver Packages ====================
    print_section("5. Deliver Packages to Lockers")
    
    # Deliver to preferred location
    print(f"\n📍 Delivering to preferred location (Downtown):")
    service.deliver_package(package1.get_id(), downtown.get_id())
    
    # Deliver without preference (auto-allocate)
    print(f"\n📍 Delivering with auto-allocation:")
    service.deliver_package(package2.get_id())
    service.deliver_package(package3.get_id())
    service.deliver_package(package4.get_id())
    service.deliver_package(package5.get_id())
    
    # ==================== Check Locker Status ====================
    print_section("6. Check Locker Status")
    
    print(f"\n🏢 {downtown.get_name()} Status:")
    downtown_stats = service.get_location_statistics(downtown.get_id())
    print(f"   Occupancy: {downtown_stats['location']['occupancy_rate']}")
    print(f"   Current Packages: {downtown_stats['current_packages']}")
    print(f"   Available by size:")
    for size, count in downtown_stats['available_by_size'].items():
        if count > 0:
            print(f"      • {size}: {count}")
    
    # ==================== View Customer Packages ====================
    print_section("7. View Customer Packages")
    
    print(f"\n👤 Alice's Packages:")
    alice_packages = service.get_customer_packages(alice.get_id())
    for pkg in alice_packages:
        print(f"   📦 {pkg.get_tracking_number()}")
        print(f"      Status: {pkg.get_status().value}")
        if pkg.get_status() == PackageStatus.DELIVERED_TO_LOCKER:
            location = service.get_location(pkg.get_locker_location_id())
            print(f"      Location: {location.get_name()}")
            print(f"      Pickup Code: {pkg.get_pickup_code()}")
            print(f"      Time Remaining: {pkg.get_time_remaining()}")
    
    print(f"\n👤 Bob's Active Deliveries:")
    bob_active = service.get_active_deliveries(bob.get_id())
    for pkg in bob_active:
        print(f"   📦 {pkg.get_tracking_number()} - Code: {pkg.get_pickup_code()}")
    
    # ==================== Pickup Package ====================
    print_section("8. Customer Picks Up Package")
    
    # Alice picks up package 1
    print(f"\n👤 Alice picking up package TRK001:")
    pickup_code = package1.get_pickup_code()
    picked_up = service.pickup_package("TRK001", pickup_code)
    
    if picked_up:
        print(f"   ✅ Successfully picked up!")
        print(f"   Package: {picked_up.get_tracking_number()}")
    
    # Try wrong code
    print(f"\n👤 Bob trying wrong pickup code:")
    service.pickup_package("TRK003", "999999")
    
    # Bob picks up with correct code
    print(f"\n👤 Bob picking up package TRK003:")
    bob_code = package3.get_pickup_code()
    service.pickup_package("TRK003", bob_code)
    
    # ==================== View Notifications ====================
    print_section("9. View Customer Notifications")
    
    print(f"\n📧 Alice's Notifications:")
    alice_notifications = service.get_customer_notifications(alice.get_id())
    for notif in alice_notifications[:5]:  # Show last 5
        print(f"   • [{notif._notification_type.value}] {notif._message[:80]}...")
        print(f"     Sent: {notif._sent_at.strftime('%Y-%m-%d %H:%M')}")
    
    # ==================== Simulate Expiring Package ====================
    print_section("10. Handle Expiring Packages")
    
    # Manually set package to expire soon
    package2._pickup_deadline = datetime.now() + timedelta(hours=12)
    
    print(f"\n⚠️  Checking for packages expiring soon...")
    service.send_expiry_warnings(hours_before=24)
    
    # ==================== Simulate Expired Package ====================
    print_section("11. Process Expired Packages")
    
    # Manually expire a package
    package4._pickup_deadline = datetime.now() - timedelta(hours=1)
    
    print(f"\n🔄 Checking for expired packages...")
    expired = service.check_expired_packages()
    
    print(f"\n   Expired packages processed: {len(expired)}")
    for pkg in expired:
        print(f"   📦 {pkg.get_tracking_number()} - Returned to sender")
    
    # ==================== Find Location with Capacity ====================
    print_section("12. Find Locations with Capacity")
    
    print(f"\n🔍 Finding locations with capacity for LARGE package:")
    nearby_with_capacity = service.find_nearby_locations(
        customer_loc,
        radius_miles=5.0,
        package_size=LockerSize.LARGE
    )
    
    for location in nearby_with_capacity:
        available = location.get_available_count(LockerSize.LARGE)
        print(f"   • {location.get_name()}: {available} LARGE lockers available")
    
    # ==================== Deliver More Packages ====================
    print_section("13. Bulk Package Delivery")
    
    print(f"\n📦 Creating and delivering multiple packages...")
    
    for i in range(10):
        customer = random.choice([alice, bob, charlie])
        size = random.choice(list(LockerSize))
        tracking = f"BULK{i+1:03d}"
        
        pkg = service.create_package(tracking, customer, size)
        service.deliver_package(pkg.get_id())
    
    # ==================== Location Statistics ====================
    print_section("14. Location Statistics")
    
    for location in service._locations.values():
        stats = service.get_location_statistics(location.get_id())
        
        print(f"\n📊 {stats['location']['name']}:")
        print(f"   Total Lockers: {stats['location']['total_lockers']}")
        print(f"   Available: {stats['location']['available_lockers']}")
        print(f"   Occupancy: {stats['location']['occupancy_rate']}")
        print(f"   Current Packages: {stats['current_packages']}")
        print(f"   Expiring Soon: {stats['packages_expiring_soon']}")
        
        print(f"   Size Distribution:")
        for size, count in stats['location']['size_distribution'].items():
            print(f"      • {size}: {count} lockers")
    
    # ==================== System Statistics ====================
    print_section("15. System-Wide Statistics")
    
    system_stats = service.get_system_statistics()
    
    print(f"\n📊 Amazon Locker Service Statistics:")
    print(f"   Locations: {system_stats['total_locations']} "
          f"({system_stats['active_locations']} active)")
    print(f"   Total Lockers: {system_stats['total_lockers']}")
    print(f"   Occupied: {system_stats['occupied_lockers']}")
    print(f"   Utilization: {system_stats['utilization_rate']}")
    
    print(f"\n   Customers: {system_stats['total_customers']}")
    print(f"   Total Packages: {system_stats['total_packages']}")
    
    print(f"\n   Packages by Status:")
    for status, count in system_stats['packages_by_status'].items():
        if count > 0:
            print(f"      • {status}: {count}")
    
    print(f"\n   Total Notifications Sent: {system_stats['total_notifications']}")
    
    # ==================== Package Tracking ====================
    print_section("16. Track Package Journey")
    
    print(f"\n📦 Package TRK002 Journey:")
    pkg2 = service.get_package_by_tracking("TRK002")
    pkg2_dict = pkg2.to_dict()
    
    print(f"   Tracking: {pkg2_dict['tracking_number']}")
    print(f"   Customer: {pkg2_dict['customer']}")
    print(f"   Size: {pkg2_dict['size']}")
    print(f"   Status: {pkg2_dict['status']}")
    print(f"   Delivered: {pkg2_dict['delivered_at'][:19] if pkg2_dict['delivered_at'] else 'N/A'}")
    print(f"   Pickup Code: {pkg2_dict['pickup_code']}")
    print(f"   Deadline: {pkg2_dict['pickup_deadline'][:19] if pkg2_dict['pickup_deadline'] else 'N/A'}")
    print(f"   Time Remaining: {pkg2_dict['time_remaining']}")
    print(f"   Delivery Attempts: {pkg2_dict['delivery_attempts']}")
    
    # ==================== Locker Details ====================
    print_section("17. Individual Locker Details")
    
    print(f"\n🔐 Sample Lockers at {downtown.get_name()}:")
    sample_lockers = list(downtown._lockers.values())[:5]
    
    for locker in sample_lockers:
        locker_dict = locker.to_dict()
        print(f"   • Locker {locker_dict['locker_id']}:")
        print(f"     Size: {locker_dict['size']}")
        print(f"     Status: {locker_dict['status']}")
        if locker_dict['has_package']:
            print(f"     Package: {locker_dict['package_id']}")
    
    print_section("Demo Complete")
    print("\n✅ Amazon Locker Service demo completed!")
    print("\n🎯 Key Features Demonstrated:")
    print("   ✅ Multiple locker locations")
    print("   ✅ Various locker sizes (XS to XL)")
    print("   ✅ Find nearby locations by distance")
    print("   ✅ Intelligent locker allocation")
    print("   ✅ Package delivery with pickup codes")
    print("   ✅ Secure package pickup")
    print("   ✅ Expiry management and warnings")
    print("   ✅ Automatic return of expired packages")
    print("   ✅ Customer notifications")
    print("   ✅ Real-time capacity tracking")
    print("   ✅ Location and system statistics")
    print("   ✅ Package tracking")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_amazon_locker_service()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Amazon Locker Service - Low Level Design
# Here's a comprehensive Amazon Locker service system for package pickup:

# Key Design Decisions:
# 1. Core Components:
# LockerLocation: Physical location with multiple lockers
# Locker: Individual compartment
# Package: Item to be delivered
# Customer: User of service
# Location: Geographic coordinates
# 2. Locker Sizes:
# 3. Key Features:
# Smart Allocation:

# Tries exact size first
# Falls back to larger sizes
# Handles capacity constraints
# Location preference support
# Pickup Process:

# Package delivered → Generate 6-digit code
# Customer receives notification
# Customer enters code at locker
# Locker opens and releases package
# Locker becomes available again
# Expiry Management:

# 72-hour default pickup window
# Warnings 24 hours before expiry
# Auto-return expired packages
# Frees up locker space
# 4. Location Finding:
# 5. Security:
# ✅ Pickup Code: Random 6-digit code ✅ Code Verification: Must match to open ✅ Time Limits: 72-hour pickup window ✅ Tracking: Full audit trail

# 6. Notification System:
# DELIVERY: Package arrived
# PICKUP_REMINDER: Time to pick up
# EXPIRY_WARNING: 24 hours left
# RETURN_NOTICE: Package returned
# 7. Capacity Management:
# 8. Design Patterns:
# Strategy Pattern: Different locker sizes
# State Pattern: Locker status transitions
# Observer Pattern: Notifications
# Factory Pattern: Package/Location creation
# Repository Pattern: Storage management
# 9. Workflow:
# Delivery Flow:

# Pickup Flow:

# Expiry Flow:

# 10. Statistics Tracked:
# Location: Occupancy, capacity by size
# System: Total packages, utilization
# Customer: Active deliveries, history
# Package: Delivery attempts, timing
# 11. Real-World Considerations:
# Implemented: ✅ Multiple locker sizes ✅ Location-based search ✅ Capacity management ✅ Expiry handling ✅ Notifications ✅ Pickup codes

# Production Additions:

# Payment integration
# Temperature-controlled lockers
# Video surveillance
# Access control systems
# Mobile app integration
# QR code scanning
# Real-time monitoring
# 12. Scalability:
# This is a production-grade Amazon Locker system! 📦🔐
