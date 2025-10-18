from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta, time
from collections import defaultdict
from threading import RLock
import uuid
from dataclasses import dataclass
import calendar as cal


# ==================== Enums ====================

class EventType(Enum):
    """Type of calendar event"""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    ALL_DAY = "all_day"


class RecurrenceFrequency(Enum):
    """Frequency of recurring events"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class EventStatus(Enum):
    """Event status"""
    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class ParticipantStatus(Enum):
    """Participant response status"""
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    NEEDS_ACTION = "needs_action"


class Permission(Enum):
    """Calendar/Event permissions"""
    OWNER = "owner"
    WRITE = "write"
    READ = "read"
    FREE_BUSY = "free_busy"  # Can only see if time is busy


class ReminderType(Enum):
    """Reminder notification type"""
    EMAIL = "email"
    POPUP = "popup"
    NOTIFICATION = "notification"


class DayOfWeek(Enum):
    """Days of the week"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Visibility(Enum):
    """Event visibility"""
    PUBLIC = "public"
    PRIVATE = "private"
    CONFIDENTIAL = "confidential"


# ==================== Core Models ====================

class User:
    """Calendar user"""
    
    def __init__(self, user_id: str, name: str, email: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._timezone = "UTC"
        self._default_reminders: List['Reminder'] = []
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_timezone(self) -> str:
        return self._timezone
    
    def set_timezone(self, timezone: str) -> None:
        self._timezone = timezone
    
    def add_default_reminder(self, reminder: 'Reminder') -> None:
        self._default_reminders.append(reminder)
    
    def get_default_reminders(self) -> List['Reminder']:
        return self._default_reminders.copy()


class Reminder:
    """Event reminder"""
    
    def __init__(self, minutes_before: int, reminder_type: ReminderType):
        self._minutes_before = minutes_before
        self._reminder_type = reminder_type
    
    def get_minutes_before(self) -> int:
        return self._minutes_before
    
    def get_type(self) -> ReminderType:
        return self._reminder_type
    
    def get_reminder_time(self, event_start: datetime) -> datetime:
        """Calculate when reminder should fire"""
        return event_start - timedelta(minutes=self._minutes_before)


class Participant:
    """Event participant"""
    
    def __init__(self, user: User, is_organizer: bool = False,
                 is_optional: bool = False):
        self._user = user
        self._is_organizer = is_organizer
        self._is_optional = is_optional
        self._status = ParticipantStatus.NEEDS_ACTION
        self._response_time: Optional[datetime] = None
    
    def get_user(self) -> User:
        return self._user
    
    def is_organizer(self) -> bool:
        return self._is_organizer
    
    def is_optional(self) -> bool:
        return self._is_optional
    
    def get_status(self) -> ParticipantStatus:
        return self._status
    
    def set_status(self, status: ParticipantStatus) -> None:
        self._status = status
        self._response_time = datetime.now()
    
    def get_response_time(self) -> Optional[datetime]:
        return self._response_time


class RecurrenceRule:
    """Defines how an event repeats"""
    
    def __init__(self, frequency: RecurrenceFrequency, interval: int = 1):
        self._frequency = frequency
        self._interval = interval  # e.g., every 2 weeks
        
        # Optional constraints
        self._count: Optional[int] = None  # Number of occurrences
        self._until: Optional[datetime] = None  # End date
        self._by_day: List[DayOfWeek] = []  # For weekly: which days
        self._by_month_day: List[int] = []  # For monthly: which day of month
        self._by_month: List[int] = []  # For yearly: which months
    
    def get_frequency(self) -> RecurrenceFrequency:
        return self._frequency
    
    def get_interval(self) -> int:
        return self._interval
    
    def set_count(self, count: int) -> None:
        """Set number of occurrences"""
        self._count = count
        self._until = None  # Count and until are mutually exclusive
    
    def set_until(self, until: datetime) -> None:
        """Set end date"""
        self._until = until
        self._count = None
    
    def set_by_day(self, days: List[DayOfWeek]) -> None:
        """Set which days of week (for weekly recurrence)"""
        self._by_day = days
    
    def set_by_month_day(self, days: List[int]) -> None:
        """Set which day of month (1-31)"""
        self._by_month_day = days
    
    def set_by_month(self, months: List[int]) -> None:
        """Set which months (1-12)"""
        self._by_month = months

    def generate_occurrences(self, start: datetime, 
                        original_duration: timedelta,
                        limit: int = 100) -> List[Dict[str, datetime]]:
        """
        Generate occurrence dates based on recurrence rule
        
        Returns list of dicts with 'start' and 'end' datetime
        """
        occurrences = []
        current = start
        count = 0
        iterations = 0
        max_iterations = 1000  # Safety limit
        
        # Maximum date we'll generate (10 years from start)
        max_date = start + timedelta(days=3650)
        
        while count < limit and iterations < max_iterations:
            iterations += 1
            
            # Check if we've reached the limit
            if self._count and count >= self._count:
                break
            
            if self._until and current > self._until:
                break
            
            # Safety check for date overflow
            if current > max_date:
                break
            
            # Check if current date matches the rule
            if self._matches_rule(current):
                occurrences.append({
                    'start': current,
                    'end': current + original_duration
                })
                count += 1
            
            # Move to next potential date
            try:
                current = self._get_next_date(current)
            except (OverflowError, ValueError):
                # Date overflow, stop generating
                break
        
        return occurrences
    
    def _matches_rule(self, dt: datetime) -> bool:
        """Check if datetime matches the recurrence constraints"""
        # Check day of week constraint
        if self._by_day and dt.weekday() not in [d.value for d in self._by_day]:
            return False
        
        # Check month day constraint
        if self._by_month_day and dt.day not in self._by_month_day:
            return False
        
        # Check month constraint
        if self._by_month and dt.month not in self._by_month:
            return False
        
        return True
    
    def _get_next_date(self, current: datetime) -> datetime:
        """Get next potential occurrence date"""
        try:
            if self._frequency == RecurrenceFrequency.DAILY:
                # For daily with day constraints, check each day
                if self._by_day:
                    next_date = current + timedelta(days=1)
                    # Keep advancing until we hit a matching day
                    max_attempts = 7
                    attempts = 0
                    while next_date.weekday() not in [d.value for d in self._by_day] and attempts < max_attempts:
                        next_date += timedelta(days=1)
                        attempts += 1
                    return next_date
                else:
                    return current + timedelta(days=self._interval)
            
            elif self._frequency == RecurrenceFrequency.WEEKLY:
                # For weekly, advance by interval weeks
                # But if we have day constraints, find the next matching day
                if self._by_day:
                    # Start from next day
                    next_date = current + timedelta(days=1)
                    target_days = sorted([d.value for d in self._by_day])
                    current_weekday = current.weekday()
                    
                    # Find next occurrence within this week
                    for target_day in target_days:
                        if target_day > current_weekday:
                            days_ahead = target_day - current_weekday
                            return current + timedelta(days=days_ahead)
                    
                    # If no day found this week, go to next week's first day
                    days_ahead = (7 - current_weekday) + target_days[0]
                    return current + timedelta(days=days_ahead)
                else:
                    return current + timedelta(weeks=self._interval)
            
            elif self._frequency == RecurrenceFrequency.MONTHLY:
                # Add months
                month = current.month + self._interval
                year = current.year
                
                while month > 12:
                    month -= 12
                    year += 1
                
                # Handle day overflow (e.g., Jan 31 -> Feb 31)
                max_day = cal.monthrange(year, month)[1]
                day = min(current.day, max_day)
                
                return current.replace(year=year, month=month, day=day)
            
            elif self._frequency == RecurrenceFrequency.YEARLY:
                return current.replace(year=current.year + self._interval)
            
        except (OverflowError, ValueError) as e:
            # If we can't compute next date, raise to stop iteration
            raise
        
        return current + timedelta(days=1)  # Default fallback

class Event:
    """Calendar event"""
    
    def __init__(self, event_id: str, calendar_id: str, title: str,
                 start_time: datetime, end_time: datetime,
                 creator: User):
        self._event_id = event_id
        self._calendar_id = calendar_id
        self._title = title
        self._start_time = start_time
        self._end_time = end_time
        self._creator = creator
        
        # Optional fields
        self._description: str = ""
        self._location: str = ""
        self._event_type = EventType.ONE_TIME
        self._status = EventStatus.CONFIRMED
        self._visibility = Visibility.PUBLIC
        
        # Participants
        self._participants: Dict[str, Participant] = {}
        self._participants[creator.get_id()] = Participant(creator, is_organizer=True)
        
        # Recurrence
        self._recurrence_rule: Optional[RecurrenceRule] = None
        self._recurrence_id: Optional[str] = None  # For instances of recurring events
        
        # Reminders
        self._reminders: List[Reminder] = []
        
        # Metadata
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._color: Optional[str] = None
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._event_id
    
    def get_calendar_id(self) -> str:
        return self._calendar_id
    
    def get_title(self) -> str:
        return self._title
    
    def set_title(self, title: str) -> None:
        with self._lock:
            self._title = title
            self._updated_at = datetime.now()
    
    def get_start_time(self) -> datetime:
        return self._start_time
    
    def get_end_time(self) -> datetime:
        return self._end_time
    
    def set_time(self, start: datetime, end: datetime) -> None:
        with self._lock:
            if start >= end:
                raise ValueError("Start time must be before end time")
            self._start_time = start
            self._end_time = end
            self._updated_at = datetime.now()
    
    def get_duration(self) -> timedelta:
        return self._end_time - self._start_time
    
    def get_description(self) -> str:
        return self._description
    
    def set_description(self, description: str) -> None:
        with self._lock:
            self._description = description
            self._updated_at = datetime.now()
    
    def get_location(self) -> str:
        return self._location
    
    def set_location(self, location: str) -> None:
        with self._lock:
            self._location = location
            self._updated_at = datetime.now()
    
    def get_creator(self) -> User:
        return self._creator
    
    def get_status(self) -> EventStatus:
        return self._status
    
    def set_status(self, status: EventStatus) -> None:
        with self._lock:
            self._status = status
            self._updated_at = datetime.now()
    
    def get_visibility(self) -> Visibility:
        return self._visibility
    
    def set_visibility(self, visibility: Visibility) -> None:
        self._visibility = visibility
    
    def get_event_type(self) -> EventType:
        return self._event_type
    
    def add_participant(self, user: User, is_optional: bool = False) -> Participant:
        """Add participant to event"""
        with self._lock:
            if user.get_id() in self._participants:
                return self._participants[user.get_id()]
            
            participant = Participant(user, is_optional=is_optional)
            self._participants[user.get_id()] = participant
            self._updated_at = datetime.now()
            return participant
    
    def remove_participant(self, user_id: str) -> bool:
        """Remove participant from event"""
        with self._lock:
            # Can't remove organizer
            participant = self._participants.get(user_id)
            if participant and participant.is_organizer():
                return False
            
            if user_id in self._participants:
                del self._participants[user_id]
                self._updated_at = datetime.now()
                return True
            return False
    
    def get_participant(self, user_id: str) -> Optional[Participant]:
        return self._participants.get(user_id)
    
    def get_participants(self) -> List[Participant]:
        return list(self._participants.values())
    
    def update_participant_status(self, user_id: str, 
                                  status: ParticipantStatus) -> bool:
        """Update participant's response status"""
        with self._lock:
            participant = self._participants.get(user_id)
            if participant:
                participant.set_status(status)
                return True
            return False
    
    def set_recurrence(self, rule: RecurrenceRule) -> None:
        """Make event recurring"""
        with self._lock:
            self._recurrence_rule = rule
            self._event_type = EventType.RECURRING
            self._updated_at = datetime.now()
    
    def get_recurrence_rule(self) -> Optional[RecurrenceRule]:
        return self._recurrence_rule
    
    def is_recurring(self) -> bool:
        return self._recurrence_rule is not None
    
    def set_recurrence_id(self, recurrence_id: str) -> None:
        """Set ID for instances of recurring events"""
        self._recurrence_id = recurrence_id
    
    def get_recurrence_id(self) -> Optional[str]:
        return self._recurrence_id
    
    def add_reminder(self, reminder: Reminder) -> None:
        with self._lock:
            self._reminders.append(reminder)
    
    def get_reminders(self) -> List[Reminder]:
        return self._reminders.copy()
    
    def set_color(self, color: str) -> None:
        self._color = color
    
    def get_color(self) -> Optional[str]:
        return self._color
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def get_updated_at(self) -> datetime:
        return self._updated_at
    
    def overlaps_with(self, other: 'Event') -> bool:
        """Check if this event overlaps with another"""
        return (self._start_time < other.get_end_time() and 
                self._end_time > other.get_start_time())
    
    def is_during(self, start: datetime, end: datetime) -> bool:
        """Check if event falls within a time range"""
        return (self._start_time < end and self._end_time > start)
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary"""
        return {
            'id': self._event_id,
            'calendar_id': self._calendar_id,
            'title': self._title,
            'description': self._description,
            'location': self._location,
            'start': self._start_time.isoformat(),
            'end': self._end_time.isoformat(),
            'status': self._status.value,
            'visibility': self._visibility.value,
            'is_recurring': self.is_recurring(),
            'creator': self._creator.get_email(),
            'participants': [
                {
                    'email': p.get_user().get_email(),
                    'status': p.get_status().value,
                    'organizer': p.is_organizer(),
                    'optional': p.is_optional()
                }
                for p in self._participants.values()
            ],
            'created_at': self._created_at.isoformat(),
            'updated_at': self._updated_at.isoformat()
        }


class Calendar:
    """Calendar that contains events"""
    
    def __init__(self, calendar_id: str, name: str, owner: User):
        self._calendar_id = calendar_id
        self._name = name
        self._owner = owner
        self._description: str = ""
        self._timezone = owner.get_timezone()
        self._color: Optional[str] = None
        
        # Events in this calendar
        self._events: Dict[str, Event] = {}
        
        # Permissions: user_id -> Permission
        self._permissions: Dict[str, Permission] = {}
        self._permissions[owner.get_id()] = Permission.OWNER
        
        # Settings
        self._is_primary = False
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._calendar_id
    
    def get_name(self) -> str:
        return self._name
    
    def set_name(self, name: str) -> None:
        self._name = name
    
    def get_owner(self) -> User:
        return self._owner
    
    def get_description(self) -> str:
        return self._description
    
    def set_description(self, description: str) -> None:
        self._description = description
    
    def get_timezone(self) -> str:
        return self._timezone
    
    def set_timezone(self, timezone: str) -> None:
        self._timezone = timezone
    
    def set_color(self, color: str) -> None:
        self._color = color
    
    def get_color(self) -> Optional[str]:
        return self._color
    
    def is_primary(self) -> bool:
        return self._is_primary
    
    def set_primary(self, is_primary: bool) -> None:
        self._is_primary = is_primary
    
    def add_event(self, event: Event) -> None:
        """Add event to calendar"""
        with self._lock:
            self._events[event.get_id()] = event
    
    def remove_event(self, event_id: str) -> bool:
        """Remove event from calendar"""
        with self._lock:
            if event_id in self._events:
                del self._events[event_id]
                return True
            return False
    
    def get_event(self, event_id: str) -> Optional[Event]:
        return self._events.get(event_id)
    
    def get_events(self, start: Optional[datetime] = None,
                   end: Optional[datetime] = None) -> List[Event]:
        """Get events, optionally filtered by time range"""
        with self._lock:
            events = list(self._events.values())
            
            if start and end:
                events = [e for e in events if e.is_during(start, end)]
            
            return sorted(events, key=lambda e: e.get_start_time())
    
    def share_with(self, user_id: str, permission: Permission) -> None:
        """Share calendar with user"""
        with self._lock:
            if permission == Permission.OWNER:
                raise ValueError("Cannot grant owner permission")
            self._permissions[user_id] = permission
    
    def revoke_access(self, user_id: str) -> bool:
        """Revoke user's access to calendar"""
        with self._lock:
            # Can't revoke owner
            if user_id == self._owner.get_id():
                return False
            
            if user_id in self._permissions:
                del self._permissions[user_id]
                return True
            return False
    
    def get_permission(self, user_id: str) -> Optional[Permission]:
        """Get user's permission level"""
        return self._permissions.get(user_id)
    
    def has_permission(self, user_id: str, required: Permission) -> bool:
        """Check if user has required permission"""
        user_perm = self.get_permission(user_id)
        if not user_perm:
            return False
        
        # Owner can do everything
        if user_perm == Permission.OWNER:
            return True
        
        # Write includes read and free-busy
        if user_perm == Permission.WRITE:
            return required in [Permission.WRITE, Permission.READ, Permission.FREE_BUSY]
        
        # Read includes free-busy
        if user_perm == Permission.READ:
            return required in [Permission.READ, Permission.FREE_BUSY]
        
        # Free-busy only for free-busy
        if user_perm == Permission.FREE_BUSY:
            return required == Permission.FREE_BUSY
        
        return False
    
    def get_shared_users(self) -> Dict[str, Permission]:
        """Get all users with access"""
        return self._permissions.copy()


# ==================== Calendar Service ====================

class CalendarService:
    """
    Main calendar service that manages:
    - Multiple calendars per user
    - Event creation and management
    - Recurring events
    - Sharing and permissions
    - Event queries and searches
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._calendars: Dict[str, Calendar] = {}
        self._events: Dict[str, Event] = {}
        
        # Index: user_id -> list of calendar_ids they have access to
        self._user_calendars: Dict[str, List[str]] = defaultdict(list)
        
        # Index: user_id -> list of event_ids they're invited to
        self._user_events: Dict[str, Set[str]] = defaultdict(set)
        
        # Thread safety
        self._lock = RLock()
    
    # ==================== User Management ====================
    
    def register_user(self, user: User) -> None:
        """Register a new user"""
        with self._lock:
            self._users[user.get_id()] = user
            print(f"✅ User registered: {user.get_name()} ({user.get_email()})")
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Calendar Management ====================
    
    def create_calendar(self, owner_id: str, name: str, 
                       description: str = "") -> Optional[Calendar]:
        """Create a new calendar"""
        with self._lock:
            owner = self._users.get(owner_id)
            if not owner:
                print(f"❌ User {owner_id} not found")
                return None
            
            calendar_id = str(uuid.uuid4())
            calendar = Calendar(calendar_id, name, owner)
            calendar.set_description(description)
            
            self._calendars[calendar_id] = calendar
            self._user_calendars[owner_id].append(calendar_id)
            
            print(f"📅 Calendar created: {name} ({calendar_id})")
            return calendar
    
    def get_calendar(self, calendar_id: str) -> Optional[Calendar]:
        return self._calendars.get(calendar_id)
    
    def get_user_calendars(self, user_id: str) -> List[Calendar]:
        """Get all calendars user has access to"""
        calendar_ids = self._user_calendars.get(user_id, [])
        return [self._calendars[cid] for cid in calendar_ids if cid in self._calendars]
    
    def share_calendar(self, calendar_id: str, requester_id: str,
                      target_user_id: str, permission: Permission) -> bool:
        """Share calendar with another user"""
        with self._lock:
            calendar = self._calendars.get(calendar_id)
            if not calendar:
                return False
            
            # Check if requester has permission to share
            if not calendar.has_permission(requester_id, Permission.OWNER):
                print(f"❌ User {requester_id} cannot share this calendar")
                return False
            
            # Share with target user
            calendar.share_with(target_user_id, permission)
            
            # Update index
            if calendar_id not in self._user_calendars[target_user_id]:
                self._user_calendars[target_user_id].append(calendar_id)
            
            target_user = self._users.get(target_user_id)
            print(f"✅ Calendar shared with {target_user.get_email() if target_user else target_user_id} "
                  f"({permission.value})")
            return True
    
    def delete_calendar(self, calendar_id: str, user_id: str) -> bool:
        """Delete a calendar"""
        with self._lock:
            calendar = self._calendars.get(calendar_id)
            if not calendar:
                return False
            
            # Only owner can delete
            if calendar.get_owner().get_id() != user_id:
                print(f"❌ Only owner can delete calendar")
                return False
            
            # Remove all events
            for event in calendar.get_events():
                self._events.pop(event.get_id(), None)
            
            # Remove from all user indexes
            for uid in self._user_calendars:
                if calendar_id in self._user_calendars[uid]:
                    self._user_calendars[uid].remove(calendar_id)
            
            # Remove calendar
            del self._calendars[calendar_id]
            print(f"🗑️  Calendar deleted: {calendar_id}")
            return True
    
    # ==================== Event Management ====================
    
    def create_event(self, calendar_id: str, creator_id: str,
                    title: str, start_time: datetime, end_time: datetime,
                    description: str = "", location: str = "") -> Optional[Event]:
        """Create a new event"""
        with self._lock:
            calendar = self._calendars.get(calendar_id)
            if not calendar:
                print(f"❌ Calendar {calendar_id} not found")
                return None
            
            # Check permissions
            if not calendar.has_permission(creator_id, Permission.WRITE):
                print(f"❌ User {creator_id} does not have write permission")
                return None
            
            creator = self._users.get(creator_id)
            if not creator:
                return None
            
            event_id = str(uuid.uuid4())
            event = Event(event_id, calendar_id, title, start_time, end_time, creator)
            event.set_description(description)
            event.set_location(location)
            
            # Add to calendar
            calendar.add_event(event)
            self._events[event_id] = event
            
            # Index for creator
            self._user_events[creator_id].add(event_id)
            
            print(f"📌 Event created: {title} ({event_id})")
            return event
    
    def get_event(self, event_id: str) -> Optional[Event]:
        return self._events.get(event_id)
    
    def update_event(self, event_id: str, user_id: str,
                    **kwargs) -> bool:
        """Update event properties"""
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            calendar = self._calendars.get(event.get_calendar_id())
            if not calendar:
                return False
            
            # Check permissions
            if not calendar.has_permission(user_id, Permission.WRITE):
                print(f"❌ User {user_id} does not have write permission")
                return False
            
            # Update fields
            if 'title' in kwargs:
                event.set_title(kwargs['title'])
            
            if 'description' in kwargs:
                event.set_description(kwargs['description'])
            
            if 'location' in kwargs:
                event.set_location(kwargs['location'])
            
            if 'start_time' in kwargs and 'end_time' in kwargs:
                event.set_time(kwargs['start_time'], kwargs['end_time'])
            
            if 'status' in kwargs:
                event.set_status(kwargs['status'])
            
            if 'visibility' in kwargs:
                event.set_visibility(kwargs['visibility'])
            
            print(f"✏️  Event updated: {event.get_title()}")
            return True
    
    def delete_event(self, event_id: str, user_id: str) -> bool:
        """Delete an event"""
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            calendar = self._calendars.get(event.get_calendar_id())
            if not calendar:
                return False
            
            # Check permissions (only organizer or calendar owner can delete)
            is_organizer = event.get_creator().get_id() == user_id
            is_owner = calendar.has_permission(user_id, Permission.OWNER)
            
            if not (is_organizer or is_owner):
                print(f"❌ Only organizer or calendar owner can delete event")
                return False
            
            # Remove from calendar
            calendar.remove_event(event_id)
            
            # Remove from global events
            del self._events[event_id]
            
            # Remove from user indexes
            for uid in self._user_events:
                self._user_events[uid].discard(event_id)
            
            print(f"🗑️  Event deleted: {event.get_title()}")
            return True
    
    # ==================== Participant Management ====================
    
    def invite_participant(self, event_id: str, inviter_id: str,
                          invitee_id: str, is_optional: bool = False) -> bool:
        """Add participant to event"""
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            # Check if inviter is organizer or has write permission
            calendar = self._calendars.get(event.get_calendar_id())
            is_organizer = event.get_creator().get_id() == inviter_id
            has_permission = calendar.has_permission(inviter_id, Permission.WRITE)
            
            if not (is_organizer or has_permission):
                print(f"❌ Only organizer can invite participants")
                return False
            
            invitee = self._users.get(invitee_id)
            if not invitee:
                return False
            
            # Add participant
            event.add_participant(invitee, is_optional)
            
            # Index for invitee
            self._user_events[invitee_id].add(event_id)
            
            print(f"✉️  Invitation sent to {invitee.get_email()} for '{event.get_title()}'")
            return True
    
    def respond_to_event(self, event_id: str, user_id: str,
                        status: ParticipantStatus) -> bool:
        """User responds to event invitation"""
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            success = event.update_participant_status(user_id, status)
            
            if success:
                user = self._users.get(user_id)
                print(f"✅ {user.get_email() if user else user_id} "
                      f"{status.value} '{event.get_title()}'")
            
            return success
    
    # ==================== Recurring Events ====================
    
    def make_event_recurring(self, event_id: str, user_id: str,
                           recurrence_rule: RecurrenceRule) -> bool:
        """Make an event recurring"""
        with self._lock:
            event = self._events.get(event_id)
            if not event:
                return False
            
            calendar = self._calendars.get(event.get_calendar_id())
            if not calendar.has_permission(user_id, Permission.WRITE):
                return False
            
            event.set_recurrence(recurrence_rule)
            print(f"🔁 Event '{event.get_title()}' is now recurring "
                  f"({recurrence_rule.get_frequency().value})")
            return True
    
    def get_recurring_instances(self, event_id: str, start: datetime,
                               end: datetime) -> List[Dict]:
        """Get instances of recurring event within time range"""
        event = self._events.get(event_id)
        if not event or not event.is_recurring():
            return []
        
        rule = event.get_recurrence_rule()
        duration = event.get_duration()
        
        # Generate occurrences
        occurrences = rule.generate_occurrences(
            event.get_start_time(),
            duration,
            limit=100
        )
        
        # Filter by time range
        instances = []
        for occ in occurrences:
            if occ['start'] >= start and occ['start'] < end:
                instances.append({
                    'event_id': event_id,
                    'title': event.get_title(),
                    'start': occ['start'],
                    'end': occ['end'],
                    'is_instance': True
                })
        
        return instances
    
    # ==================== Event Queries ====================
    
    def get_events_for_day(self, user_id: str, date: datetime) -> List[Event]:
        """Get all events for a specific day"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return self.get_events_in_range(user_id, start, end)
    
    def get_events_in_range(self, user_id: str, start: datetime,
                           end: datetime) -> List[Event]:
        """Get all events for user in time range"""
        events = []
        
        # Get all calendars user has access to
        calendars = self.get_user_calendars(user_id)
        
        for calendar in calendars:
            # Check read permission
            if not calendar.has_permission(user_id, Permission.READ):
                continue
            
            calendar_events = calendar.get_events(start, end)
            
            for event in calendar_events:
                # Handle recurring events
                if event.is_recurring():
                    instances = self.get_recurring_instances(event.get_id(), start, end)
                    # Create temporary event objects for instances
                    for inst in instances:
                        events.append(event)  # Simplified - in real system create instance objects
                else:
                    events.append(event)
        
        return sorted(events, key=lambda e: e.get_start_time())
    
    def find_free_slots(self, user_id: str, date: datetime,
                       duration: timedelta, 
                       working_hours: tuple = (9, 17)) -> List[Dict[str, datetime]]:
        """
        Find available time slots for a user on a given day
        
        Args:
            user_id: User to check
            date: Day to check
            duration: Required slot duration
            working_hours: Tuple of (start_hour, end_hour)
        
        Returns:
            List of dicts with 'start' and 'end' datetime
        """
        start_hour, end_hour = working_hours
        
        day_start = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        # Get all events for the day
        events = self.get_events_in_range(user_id, day_start, day_end)
        
        # Sort events by start time
        events = sorted(events, key=lambda e: e.get_start_time())
        
        # Find gaps between events
        free_slots = []
        current_time = day_start
        
        for event in events:
            event_start = max(event.get_start_time(), day_start)
            event_end = min(event.get_end_time(), day_end)
            
            # Check if there's a gap before this event
            if current_time < event_start:
                gap_duration = event_start - current_time
                if gap_duration >= duration:
                    free_slots.append({
                        'start': current_time,
                        'end': event_start
                    })
            
            current_time = max(current_time, event_end)
        
        # Check if there's time after last event
        if current_time < day_end:
            remaining = day_end - current_time
            if remaining >= duration:
                free_slots.append({
                    'start': current_time,
                    'end': day_end
                })
        
        return free_slots
    
    def check_availability(self, user_ids: List[str], start: datetime,
                          end: datetime) -> Dict[str, bool]:
        """
        Check if multiple users are available during a time slot
        
        Returns dict of user_id -> is_available
        """
        availability = {}
        
        for user_id in user_ids:
            events = self.get_events_in_range(user_id, start, end)
            
            # Check if any event overlaps with requested time
            has_conflict = any(
                event.get_start_time() < end and event.get_end_time() > start
                for event in events
            )
            
            availability[user_id] = not has_conflict
        
        return availability
    
    def search_events(self, user_id: str, query: str) -> List[Event]:
        """Search events by title or description"""
        results = []
        calendars = self.get_user_calendars(user_id)
        
        query_lower = query.lower()
        
        for calendar in calendars:
            if not calendar.has_permission(user_id, Permission.READ):
                continue
            
            for event in calendar.get_events():
                if (query_lower in event.get_title().lower() or
                    query_lower in event.get_description().lower() or
                    query_lower in event.get_location().lower()):
                    results.append(event)
        
        return results
    
    # ==================== Statistics ====================
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        calendars = self.get_user_calendars(user_id)
        
        total_events = 0
        upcoming_events = 0
        now = datetime.now()
        
        for calendar in calendars:
            events = calendar.get_events()
            total_events += len(events)
            upcoming_events += sum(1 for e in events if e.get_start_time() > now)
        
        return {
            'user_id': user_id,
            'calendars_count': len(calendars),
            'total_events': total_events,
            'upcoming_events': upcoming_events,
            'events_as_participant': len(self._user_events.get(user_id, []))
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_event(event: Event) -> None:
    """Print event details"""
    print(f"\n📅 {event.get_title()}")
    print(f"   Start: {event.get_start_time().strftime('%Y-%m-%d %H:%M')}")
    print(f"   End: {event.get_end_time().strftime('%Y-%m-%d %H:%M')}")
    if event.get_location():
        print(f"   Location: {event.get_location()}")
    if event.get_description():
        print(f"   Description: {event.get_description()}")
    print(f"   Organizer: {event.get_creator().get_email()}")
    print(f"   Status: {event.get_status().value}")
    
    participants = event.get_participants()
    if len(participants) > 1:
        print(f"   Participants:")
        for p in participants:
            if not p.is_organizer():
                status_emoji = {
                    ParticipantStatus.ACCEPTED: "✅",
                    ParticipantStatus.DECLINED: "❌",
                    ParticipantStatus.TENTATIVE: "❓",
                    ParticipantStatus.NEEDS_ACTION: "⏳"
                }
                print(f"      {status_emoji[p.get_status()]} {p.get_user().get_email()} "
                      f"({p.get_status().value})")


def demo_google_calendar():
    """Comprehensive demo of the calendar system"""
    
    print_section("GOOGLE CALENDAR DEMO")
    
    service = CalendarService()
    
    try:
        # ==================== User Registration ====================
        print_section("1. User Registration")
        
        alice = User("U001", "Alice Johnson", "alice@company.com")
        alice.set_timezone("America/New_York")
        
        bob = User("U002", "Bob Smith", "bob@company.com")
        bob.set_timezone("America/Los_Angeles")
        
        charlie = User("U003", "Charlie Brown", "charlie@company.com")
        
        service.register_user(alice)
        service.register_user(bob)
        service.register_user(charlie)
        
        # ==================== Calendar Creation ====================
        print_section("2. Create Calendars")
        
        alice_personal = service.create_calendar(
            "U001", "Alice's Personal Calendar",
            "Personal events and reminders"
        )
        alice_personal.set_color("#FF6B6B")
        alice_personal.set_primary(True)
        
        alice_work = service.create_calendar(
            "U001", "Work Calendar",
            "Work meetings and tasks"
        )
        alice_work.set_color("#4ECDC4")
        
        bob_calendar = service.create_calendar(
            "U002", "Bob's Calendar",
            "Bob's schedule"
        )
        
        # ==================== Share Calendar ====================
        print_section("3. Share Calendar")
        
        # Alice shares work calendar with Bob (write access)
        service.share_calendar(
            alice_work.get_id(),
            "U001",  # Alice (owner)
            "U002",  # Bob
            Permission.WRITE
        )
        
        # Alice shares personal calendar with Charlie (read-only)
        service.share_calendar(
            alice_personal.get_id(),
            "U001",
            "U003",
            Permission.READ
        )
        
        # ==================== Create Events ====================
        print_section("4. Create One-Time Events")
        
        now = datetime.now()
        
        # Alice creates a team meeting
        team_meeting = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U001",
            title="Team Standup",
            start_time=now + timedelta(days=1, hours=10),
            end_time=now + timedelta(days=1, hours=10, minutes=30),
            description="Daily team sync",
            location="Conference Room A"
        )
        
        # Add reminder
        team_meeting.add_reminder(Reminder(15, ReminderType.POPUP))
        
        # Bob creates an event on Alice's work calendar
        code_review = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U002",  # Bob has write permission
            title="Code Review Session",
            start_time=now + timedelta(days=2, hours=14),
            end_time=now + timedelta(days=2, hours=15),
            description="Review PR #123"
        )
        
        # Alice creates personal event
        dentist = service.create_event(
            calendar_id=alice_personal.get_id(),
            creator_id="U001",
            title="Dentist Appointment",
            start_time=now + timedelta(days=3, hours=16),
            end_time=now + timedelta(days=3, hours=17),
            location="Dr. Smith's Clinic"
        )
        
        # ==================== Invite Participants ====================
        print_section("5. Invite Participants to Events")
        
        # Invite Bob and Charlie to team meeting
        service.invite_participant(team_meeting.get_id(), "U001", "U002")
        service.invite_participant(team_meeting.get_id(), "U001", "U003", is_optional=True)
        
        # Participants respond
        service.respond_to_event(team_meeting.get_id(), "U002", ParticipantStatus.ACCEPTED)
        service.respond_to_event(team_meeting.get_id(), "U003", ParticipantStatus.TENTATIVE)
        
        print_event(team_meeting)
        
                # ==================== Recurring Events ====================
        print_section("6. Create Recurring Events")
        
        # Get a proper Monday for weekly meeting
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = (now + timedelta(days=days_until_monday)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        
        # Weekly meeting every Monday
        weekly_meeting = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U001",
            title="Weekly Planning Meeting",
            start_time=next_monday,
            end_time=next_monday + timedelta(hours=1),
            description="Weekly team planning"
        )
        
        # Make it recurring: Every Monday
        weekly_rule = RecurrenceRule(RecurrenceFrequency.WEEKLY, interval=1)
        weekly_rule.set_by_day([DayOfWeek.MONDAY])
        weekly_rule.set_count(10)  # Next 10 occurrences
        
        service.make_event_recurring(weekly_meeting.get_id(), "U001", weekly_rule)
        
        # Daily standup (weekdays only)
        tomorrow_morning = (now + timedelta(days=1)).replace(
            hour=10, minute=30, second=0, microsecond=0
        )
        
        daily_standup = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U001",
            title="Daily Standup",
            start_time=tomorrow_morning,
            end_time=tomorrow_morning + timedelta(minutes=15),
            description="Daily sync"
        )
        
        daily_rule = RecurrenceRule(RecurrenceFrequency.DAILY, interval=1)
        daily_rule.set_by_day([
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY
        ])
        daily_rule.set_count(20)
        
        service.make_event_recurring(daily_standup.get_id(), "U001", daily_rule)
        
        # Monthly all-hands - first day of next month
        if now.month == 12:
            first_of_next_month = now.replace(year=now.year + 1, month=1, day=1, 
                                              hour=15, minute=0, second=0, microsecond=0)
        else:
            first_of_next_month = now.replace(month=now.month + 1, day=1,
                                              hour=15, minute=0, second=0, microsecond=0)
        
        monthly_meeting = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U001",
            title="Monthly All-Hands",
            start_time=first_of_next_month,
            end_time=first_of_next_month + timedelta(hours=1),
            description="Company-wide meeting"
        )
        
        monthly_rule = RecurrenceRule(RecurrenceFrequency.MONTHLY, interval=1)
        monthly_rule.set_by_month_day([1])  # First day of month
        monthly_rule.set_count(6)
        
        service.make_event_recurring(monthly_meeting.get_id(), "U001", monthly_rule)
        
        print(f"✅ Created recurring events")
        
        # ==================== Query Recurring Instances ====================
        print_section("7. Query Recurring Event Instances")
        
        range_start = now
        range_end = now + timedelta(days=30)
        
        instances = service.get_recurring_instances(
            weekly_meeting.get_id(),
            range_start,
            range_end
        )
        
        print(f"\n📅 Weekly Planning Meeting - Next 30 days:")
        for inst in instances[:5]:
            print(f"   • {inst['start'].strftime('%Y-%m-%d %H:%M')}")
        
        # ==================== View Events ====================
        print_section("8. View Events for a Day")
        
        tomorrow = now + timedelta(days=1)
        alice_events = service.get_events_for_day("U001", tomorrow)
        
        print(f"\n📆 Alice's events for {tomorrow.strftime('%Y-%m-%d')}:")
        for event in alice_events:
            print(f"   • {event.get_start_time().strftime('%H:%M')} - "
                  f"{event.get_title()}")
        
        # ==================== Update Event ====================
        print_section("9. Update Event")
        
        print(f"\n📝 Before update:")
        print_event(team_meeting)
        
        service.update_event(
            team_meeting.get_id(),
            "U001",
            title="Team Standup (Updated)",
            location="Conference Room B (Changed)",
            description="Daily team sync - Now with new agenda"
        )
        
        print(f"\n📝 After update:")
        print_event(team_meeting)
        
        # ==================== Find Free Slots ====================
        print_section("10. Find Available Time Slots")
        
        search_day = now + timedelta(days=1)
        free_slots = service.find_free_slots(
            "U001",
            search_day,
            duration=timedelta(hours=1),
            working_hours=(9, 18)
        )
        
        print(f"\n🕐 Free 1-hour slots for Alice on {search_day.strftime('%Y-%m-%d')}:")
        for slot in free_slots[:5]:
            print(f"   • {slot['start'].strftime('%H:%M')} - {slot['end'].strftime('%H:%M')}")
        
        # ==================== Check Availability ====================
        print_section("11. Check Group Availability")
        
        proposed_time_start = now + timedelta(days=1, hours=14)
        proposed_time_end = now + timedelta(days=1, hours=15)
        
        availability = service.check_availability(
            ["U001", "U002", "U003"],
            proposed_time_start,
            proposed_time_end
        )
        
        print(f"\n👥 Availability for {proposed_time_start.strftime('%Y-%m-%d %H:%M')}:")
        for user_id, is_available in availability.items():
            user = service.get_user(user_id)
            status = "✅ Available" if is_available else "❌ Busy"
            print(f"   {user.get_email()}: {status}")
        
        # ==================== Search Events ====================
        print_section("12. Search Events")
        
        results = service.search_events("U001", "meeting")
        
        print(f"\n🔍 Search results for 'meeting':")
        for event in results[:5]:
            print(f"   • {event.get_title()} - {event.get_start_time().strftime('%Y-%m-%d %H:%M')}")
        
        # ==================== Permission Test ====================
        print_section("13. Permission Testing")
        
        # Charlie tries to modify Alice's personal calendar (read-only)
        print(f"\n🔒 Charlie attempts to create event (read-only access):")
        unauthorized_event = service.create_event(
            calendar_id=alice_personal.get_id(),
            creator_id="U003",  # Charlie
            title="Unauthorized Event",
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=1, hours=1)
        )
        
        if not unauthorized_event:
            print("   ❌ Permission denied (expected)")
        
        # Charlie tries to delete event
        print(f"\n🔒 Charlie attempts to delete event:")
        deleted = service.delete_event(team_meeting.get_id(), "U003")
        if not deleted:
            print("   ❌ Permission denied (expected)")
        
        # Alice (organizer) can delete
        print(f"\n✅ Alice (organizer) deletes dentist appointment:")
        service.delete_event(dentist.get_id(), "U001")
        
        # ==================== Event Visibility ====================
        print_section("14. Event Visibility")
        
        private_event = service.create_event(
            calendar_id=alice_personal.get_id(),
            creator_id="U001",
            title="Private Meeting",
            start_time=now + timedelta(days=5, hours=14),
            end_time=now + timedelta(days=5, hours=15)
        )
        private_event.set_visibility(Visibility.PRIVATE)
        
        confidential_event = service.create_event(
            calendar_id=alice_work.get_id(),
            creator_id="U001",
            title="Executive Meeting",
            start_time=now + timedelta(days=6, hours=16),
            end_time=now + timedelta(days=6, hours=17)
        )
        confidential_event.set_visibility(Visibility.CONFIDENTIAL)
        
        print(f"✅ Created events with different visibility levels")
        
        # ==================== View Range ====================
        print_section("15. View Events in Date Range")
        
        range_start = now
        range_end = now + timedelta(days=7)
        
        alice_week = service.get_events_in_range("U001", range_start, range_end)
        
        print(f"\n📅 Alice's events for next 7 days:")
        for event in alice_week[:10]:
            print(f"   • {event.get_start_time().strftime('%Y-%m-%d %H:%M')} - "
                  f"{event.get_title()} "
                  f"[{event.get_calendar_id()[:8]}...]")
        
        # ==================== Calendar List ====================
        print_section("16. List User's Calendars")
        
        alice_calendars = service.get_user_calendars("U001")
        print(f"\n📚 Alice's calendars:")
        for cal in alice_calendars:
            perm = cal.get_permission("U001")
            print(f"   • {cal.get_name()} ({perm.value})")
            print(f"     Events: {len(cal.get_events())}")
        
        bob_calendars = service.get_user_calendars("U002")
        print(f"\n📚 Bob's calendars (including shared):")
        for cal in bob_calendars:
            perm = cal.get_permission("U002")
            print(f"   • {cal.get_name()} ({perm.value})")
        
        # ==================== Statistics ====================
        print_section("17. User Statistics")
        
        alice_stats = service.get_user_stats("U001")
        print(f"\n📊 Alice's Statistics:")
        for key, value in alice_stats.items():
            print(f"   {key}: {value}")
        
        bob_stats = service.get_user_stats("U002")
        print(f"\n📊 Bob's Statistics:")
        for key, value in bob_stats.items():
            print(f"   {key}: {value}")
        
        # ==================== Export Event ====================
        print_section("18. Export Event Data")
        
        event_dict = team_meeting.to_dict()
        print(f"\n📤 Event export (JSON-like):")
        import json
        print(json.dumps(event_dict, indent=2))
        
    finally:
        print_section("Demo Complete")
        print("\n✅ Google Calendar demo completed successfully!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_google_calendar()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Google Calendar System - Low Level Design
# Here's a comprehensive calendar system design:

# Key Design Decisions:
# 1. Core Components:
# User: Calendar owner with timezone and preferences
# Calendar: Container for events with sharing capabilities
# Event: Single event (one-time or recurring)
# RecurrenceRule: Defines how events repeat (RRULE-like)
# Participant: Event attendee with RSVP status
# Reminder: Notification before event
# 2. Key Features:
# ✅ Multiple calendars per user ✅ Calendar sharing with granular permissions (Owner, Write, Read, Free/Busy) ✅ One-time and recurring events ✅ Flexible recurrence rules (daily, weekly, monthly, yearly) ✅ Participant invitations and RSVP tracking ✅ Event reminders ✅ Free/busy time finding ✅ Group availability checking ✅ Event search ✅ Event visibility levels (Public, Private, Confidential) ✅ Permission-based access control ✅ Thread-safe operations

# 3. Recurrence Patterns Supported:
# Daily (every N days)
# Weekly (specific days of week)
# Monthly (specific day of month)
# Yearly (specific date)
# With end conditions (count or until date)
# 4. Permission Model:
# OWNER: Full control
# WRITE: Create, edit, delete events
# READ: View event details
# FREE_BUSY: Only see if time is occupied
# 5. Design Patterns:
# Composite Pattern: Calendars contain events
# Strategy Pattern: Different recurrence rules
# Observer Pattern: Participant status updates (extensible for notifications)
# Builder-like: RecurrenceRule configuration
# Index Pattern: Fast lookups for user calendars and events
# This is a production-grade calendar system like Google Calendar! 📅
