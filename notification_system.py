from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
import time
import uuid
from threading import Thread, RLock
import queue


# ==================== Enums ====================

class NotificationType(Enum):
    """Types of notifications"""
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    ALERT = "alert"
    REMINDER = "reminder"
    SYSTEM = "system"


class ChannelType(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(Enum):
    """Status of a notification"""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


class Priority(Enum):
    """Notification priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


# ==================== Core Models ====================

class User:
    """User model with notification preferences"""
    
    def __init__(self, user_id: str, name: str, email: str, 
                 phone: Optional[str] = None):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._phone = phone
        
        # User preferences for each notification type and channel
        self._preferences: Dict[NotificationType, Set[ChannelType]] = {
            NotificationType.PROMOTIONAL: {ChannelType.EMAIL},
            NotificationType.TRANSACTIONAL: {ChannelType.EMAIL, ChannelType.SMS},
            NotificationType.ALERT: {ChannelType.PUSH, ChannelType.SMS},
            NotificationType.REMINDER: {ChannelType.PUSH, ChannelType.EMAIL},
            NotificationType.SYSTEM: {ChannelType.IN_APP}
        }
        
        # Opt-out settings
        self._opted_out_channels: Set[ChannelType] = set()
        self._opted_out_types: Set[NotificationType] = set()
        
        # Push device tokens
        self._device_tokens: List[str] = []
    
    def get_user_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_phone(self) -> Optional[str]:
        return self._phone
    
    def get_device_tokens(self) -> List[str]:
        return self._device_tokens.copy()
    
    def add_device_token(self, token: str) -> None:
        if token not in self._device_tokens:
            self._device_tokens.append(token)
    
    def remove_device_token(self, token: str) -> None:
        if token in self._device_tokens:
            self._device_tokens.remove(token)
    
    def set_preference(self, notification_type: NotificationType, 
                      channels: Set[ChannelType]) -> None:
        """Set preferred channels for a notification type"""
        self._preferences[notification_type] = channels.copy()
    
    def get_preferences(self, notification_type: NotificationType) -> Set[ChannelType]:
        """Get preferred channels for a notification type"""
        return self._preferences.get(notification_type, set()).copy()
    
    def opt_out_channel(self, channel: ChannelType) -> None:
        """Opt out of a specific channel entirely"""
        self._opted_out_channels.add(channel)
    
    def opt_in_channel(self, channel: ChannelType) -> None:
        """Opt back into a channel"""
        self._opted_out_channels.discard(channel)
    
    def opt_out_type(self, notification_type: NotificationType) -> None:
        """Opt out of a notification type"""
        self._opted_out_types.add(notification_type)
    
    def opt_in_type(self, notification_type: NotificationType) -> None:
        """Opt back into a notification type"""
        self._opted_out_types.discard(notification_type)
    
    def can_receive(self, notification_type: NotificationType, 
                    channel: ChannelType) -> bool:
        """Check if user can receive this notification type via this channel"""
        if notification_type in self._opted_out_types:
            return False
        if channel in self._opted_out_channels:
            return False
        return channel in self._preferences.get(notification_type, set())


class Notification:
    """Core notification model"""
    
    def __init__(self, notification_id: str, user_id: str, 
                 notification_type: NotificationType,
                 title: str, message: str,
                 priority: Priority = Priority.MEDIUM,
                 metadata: Optional[Dict] = None):
        self._notification_id = notification_id
        self._user_id = user_id
        self._notification_type = notification_type
        self._title = title
        self._message = message
        self._priority = priority
        self._metadata = metadata or {}
        
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        
        # Track status per channel
        self._channel_status: Dict[ChannelType, NotificationStatus] = {}
        self._delivery_attempts: Dict[ChannelType, int] = defaultdict(int)
        self._sent_at: Dict[ChannelType, Optional[datetime]] = {}
        self._delivered_at: Dict[ChannelType, Optional[datetime]] = {}
        self._error_messages: Dict[ChannelType, Optional[str]] = {}
    
    def get_id(self) -> str:
        return self._notification_id
    
    def get_user_id(self) -> str:
        return self._user_id
    
    def get_type(self) -> NotificationType:
        return self._notification_type
    
    def get_title(self) -> str:
        return self._title
    
    def get_message(self) -> str:
        return self._message
    
    def get_priority(self) -> Priority:
        return self._priority
    
    def get_metadata(self) -> Dict:
        return self._metadata.copy()
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def set_channel_status(self, channel: ChannelType, 
                          status: NotificationStatus) -> None:
        """Update status for a specific channel"""
        self._channel_status[channel] = status
        self._updated_at = datetime.now()
        
        if status == NotificationStatus.SENT:
            self._sent_at[channel] = datetime.now()
        elif status == NotificationStatus.DELIVERED:
            self._delivered_at[channel] = datetime.now()
    
    def get_channel_status(self, channel: ChannelType) -> Optional[NotificationStatus]:
        """Get status for a specific channel"""
        return self._channel_status.get(channel)
    
    def increment_attempts(self, channel: ChannelType) -> None:
        """Increment delivery attempts for a channel"""
        self._delivery_attempts[channel] += 1
    
    def get_attempts(self, channel: ChannelType) -> int:
        """Get delivery attempts for a channel"""
        return self._delivery_attempts[channel]
    
    def set_error(self, channel: ChannelType, error: str) -> None:
        """Set error message for a channel"""
        self._error_messages[channel] = error
    
    def get_error(self, channel: ChannelType) -> Optional[str]:
        """Get error message for a channel"""
        return self._error_messages.get(channel)
    
    def get_all_statuses(self) -> Dict[ChannelType, NotificationStatus]:
        """Get statuses for all channels"""
        return self._channel_status.copy()


# ==================== Channel Implementations ====================

class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    def __init__(self, channel_type: ChannelType):
        self._channel_type = channel_type
        self._rate_limit_per_second = 10  # Default rate limit
        self._max_retries = 3
    
    @abstractmethod
    def send(self, user: User, notification: Notification) -> bool:
        """Send notification through this channel"""
        pass
    
    def get_channel_type(self) -> ChannelType:
        return self._channel_type
    
    def can_send(self, user: User, notification: Notification) -> bool:
        """Check if notification can be sent to user via this channel"""
        return user.can_receive(notification.get_type(), self._channel_type)
    
    def _simulate_send(self, delay: float = 0.1) -> bool:
        """Simulate sending with some failure rate"""
        time.sleep(delay)
        import random
        return random.random() > 0.1  # 90% success rate


class EmailChannel(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self):
        super().__init__(ChannelType.EMAIL)
        self._rate_limit_per_second = 100
    
    def send(self, user: User, notification: Notification) -> bool:
        """Send email notification"""
        email = user.get_email()
        if not email:
            return False
        
        print(f"📧 Sending EMAIL to {user.get_name()} ({email})")
        print(f"   Subject: {notification.get_title()}")
        print(f"   Message: {notification.get_message()[:50]}...")
        
        # Simulate actual email sending
        success = self._simulate_send(0.2)
        
        if success:
            print(f"   ✅ Email sent successfully")
        else:
            print(f"   ❌ Email failed to send")
        
        return success


class SMSChannel(NotificationChannel):
    """SMS notification channel"""
    
    def __init__(self):
        super().__init__(ChannelType.SMS)
        self._rate_limit_per_second = 50
    
    def send(self, user: User, notification: Notification) -> bool:
        """Send SMS notification"""
        phone = user.get_phone()
        if not phone:
            return False
        
        print(f"📱 Sending SMS to {user.get_name()} ({phone})")
        print(f"   Message: {notification.get_message()[:100]}...")
        
        success = self._simulate_send(0.15)
        
        if success:
            print(f"   ✅ SMS sent successfully")
        else:
            print(f"   ❌ SMS failed to send")
        
        return success


class PushChannel(NotificationChannel):
    """Push notification channel"""
    
    def __init__(self):
        super().__init__(ChannelType.PUSH)
        self._rate_limit_per_second = 1000
    
    def send(self, user: User, notification: Notification) -> bool:
        """Send push notification"""
        device_tokens = user.get_device_tokens()
        if not device_tokens:
            return False
        
        print(f"🔔 Sending PUSH to {user.get_name()} ({len(device_tokens)} devices)")
        print(f"   Title: {notification.get_title()}")
        print(f"   Message: {notification.get_message()[:50]}...")
        
        success = self._simulate_send(0.1)
        
        if success:
            print(f"   ✅ Push sent to {len(device_tokens)} device(s)")
        else:
            print(f"   ❌ Push failed to send")
        
        return success


class InAppChannel(NotificationChannel):
    """In-app notification channel"""
    
    def __init__(self):
        super().__init__(ChannelType.IN_APP)
        self._rate_limit_per_second = 5000
    
    def send(self, user: User, notification: Notification) -> bool:
        """Send in-app notification"""
        print(f"📲 Sending IN-APP notification to {user.get_name()}")
        print(f"   Title: {notification.get_title()}")
        
        success = self._simulate_send(0.05)
        
        if success:
            print(f"   ✅ In-app notification sent")
        else:
            print(f"   ❌ In-app notification failed")
        
        return success


# ==================== Notification Service ====================

class NotificationService:
    """
    Core notification service that handles:
    - Multi-channel delivery
    - User preferences
    - Priority-based queuing
    - Rate limiting
    - Retry logic
    - Async processing
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._notifications: Dict[str, Notification] = {}
        
        # Initialize channels
        self._channels: Dict[ChannelType, NotificationChannel] = {
            ChannelType.EMAIL: EmailChannel(),
            ChannelType.SMS: SMSChannel(),
            ChannelType.PUSH: PushChannel(),
            ChannelType.IN_APP: InAppChannel()
        }
        
        # Priority queues for each channel
        self._queues: Dict[ChannelType, queue.PriorityQueue] = {
            channel_type: queue.PriorityQueue()
            for channel_type in ChannelType
        }
        
        # Worker threads for async processing
        self._workers: Dict[ChannelType, Thread] = {}
        self._running = False
        
        # Thread safety
        self._lock = RLock()
        
        # Tracking
        self._user_notification_history: Dict[str, List[str]] = defaultdict(list)
    
    def start(self) -> None:
        """Start background worker threads"""
        self._running = True
        
        for channel_type in ChannelType:
            worker = Thread(
                target=self._process_queue,
                args=(channel_type,),
                daemon=True
            )
            worker.start()
            self._workers[channel_type] = worker
        
        print("🚀 Notification Service started")
    
    def stop(self) -> None:
        """Stop background workers"""
        self._running = False
        
        # Wait for queues to empty
        for channel_type in ChannelType:
            self._queues[channel_type].join()
        
        print("🛑 Notification Service stopped")
    
    def register_user(self, user: User) -> None:
        """Register a user in the system"""
        with self._lock:
            self._users[user.get_user_id()] = user
            print(f"✅ User registered: {user.get_name()} ({user.get_user_id()})")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def send_notification(self, user_id: str, notification_type: NotificationType,
                         title: str, message: str,
                         priority: Priority = Priority.MEDIUM,
                         channels: Optional[Set[ChannelType]] = None,
                         metadata: Optional[Dict] = None) -> Optional[Notification]:
        """
        Send a notification to a user
        
        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Priority level
            channels: Specific channels to use (None = use user preferences)
            metadata: Additional metadata
        
        Returns:
            Notification object if created, None if user not found
        """
        user = self._users.get(user_id)
        if not user:
            print(f"❌ User {user_id} not found")
            return None
        
        # Create notification
        notification_id = str(uuid.uuid4())
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            metadata=metadata
        )
        
        with self._lock:
            self._notifications[notification_id] = notification
            self._user_notification_history[user_id].append(notification_id)
        
        # Determine channels to use
        target_channels = channels if channels else user.get_preferences(notification_type)
        
        # Queue notification for each channel
        for channel_type in target_channels:
            channel = self._channels.get(channel_type)
            if not channel:
                continue
            
            if not channel.can_send(user, notification):
                print(f"⚠️  User {user.get_name()} cannot receive "
                      f"{notification_type.value} via {channel_type.value}")
                continue
            
            # Add to priority queue (lower priority value = higher priority)
            priority_value = -priority.value  # Negative for max-heap behavior
            self._queues[channel_type].put((
                priority_value,
                time.time(),  # Timestamp for FIFO within same priority
                notification_id,
                user_id
            ))
            
            notification.set_channel_status(channel_type, NotificationStatus.QUEUED)
        
        print(f"\n📤 Notification queued: {notification_id}")
        print(f"   Type: {notification_type.value}")
        print(f"   Priority: {priority.value}")
        print(f"   Channels: {[c.value for c in target_channels]}")
        
        return notification
    
    def _process_queue(self, channel_type: ChannelType) -> None:
        """Background worker to process notification queue for a channel"""
        channel = self._channels[channel_type]
        q = self._queues[channel_type]
        
        while self._running:
            try:
                # Get next notification (blocks until available)
                priority, timestamp, notification_id, user_id = q.get(timeout=1)
                
                notification = self._notifications.get(notification_id)
                user = self._users.get(user_id)
                
                if not notification or not user:
                    q.task_done()
                    continue
                
                # Update status
                notification.set_channel_status(channel_type, NotificationStatus.PENDING)
                notification.increment_attempts(channel_type)
                
                # Try to send
                try:
                    success = channel.send(user, notification)
                    
                    if success:
                        notification.set_channel_status(channel_type, NotificationStatus.SENT)
                        # Simulate delivery confirmation
                        time.sleep(0.1)
                        notification.set_channel_status(channel_type, NotificationStatus.DELIVERED)
                    else:
                        # Retry logic
                        attempts = notification.get_attempts(channel_type)
                        if attempts < channel._max_retries:
                            notification.set_channel_status(channel_type, NotificationStatus.RETRYING)
                            # Re-queue with same priority
                            q.put((priority, time.time(), notification_id, user_id))
                        else:
                            notification.set_channel_status(channel_type, NotificationStatus.FAILED)
                            notification.set_error(channel_type, "Max retries exceeded")
                
                except Exception as e:
                    notification.set_channel_status(channel_type, NotificationStatus.FAILED)
                    notification.set_error(channel_type, str(e))
                
                q.task_done()
                
                # Rate limiting
                time.sleep(1.0 / channel._rate_limit_per_second)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error in {channel_type.value} worker: {e}")
    
    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        return self._notifications.get(notification_id)
    
    def get_user_notifications(self, user_id: str) -> List[Notification]:
        """Get all notifications for a user"""
        notification_ids = self._user_notification_history.get(user_id, [])
        return [
            self._notifications[nid]
            for nid in notification_ids
            if nid in self._notifications
        ]
    
    def get_notification_status(self, notification_id: str) -> Dict:
        """Get detailed status of a notification"""
        notification = self._notifications.get(notification_id)
        if not notification:
            return {"error": "Notification not found"}
        
        return {
            "notification_id": notification_id,
            "user_id": notification.get_user_id(),
            "type": notification.get_type().value,
            "title": notification.get_title(),
            "priority": notification.get_priority().value,
            "created_at": notification.get_created_at().isoformat(),
            "statuses": {
                channel.value: status.value
                for channel, status in notification.get_all_statuses().items()
            }
        }
    
    def get_stats(self) -> Dict:
        """Get system statistics"""
        total_notifications = len(self._notifications)
        
        status_counts = defaultdict(int)
        channel_counts = defaultdict(int)
        
        for notification in self._notifications.values():
            for channel, status in notification.get_all_statuses().items():
                status_counts[status.value] += 1
                channel_counts[channel.value] += 1
        
        return {
            "total_users": len(self._users),
            "total_notifications": total_notifications,
            "status_breakdown": dict(status_counts),
            "channel_usage": dict(channel_counts),
            "queue_sizes": {
                channel.value: self._queues[channel].qsize()
                for channel in ChannelType
            }
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_notification_system():
    """Comprehensive demo of the notification system"""
    
    print_section("NOTIFICATION SYSTEM DEMO")
    
    # Initialize service
    service = NotificationService()
    service.start()
    
    try:
        # ==================== User Registration ====================
        print_section("1. User Registration & Preferences")
        
        # Create users
        user1 = User(
            user_id="U001",
            name="Alice Johnson",
            email="alice@example.com",
            phone="+1-555-0101"
        )
        user1.add_device_token("device_token_alice_ios")
        
        user2 = User(
            user_id="U002",
            name="Bob Smith",
            email="bob@example.com",
            phone="+1-555-0102"
        )
        user2.add_device_token("device_token_bob_android")
        
        # Customize preferences
        user1.set_preference(
            NotificationType.PROMOTIONAL,
            {ChannelType.EMAIL}  # Only email for promos
        )
        
        user2.opt_out_channel(ChannelType.SMS)  # Bob doesn't want SMS
        
        service.register_user(user1)
        service.register_user(user2)
        
        time.sleep(1)
        
        # ==================== Transactional Notification ====================
        print_section("2. Transactional Notification (High Priority)")
        
        notification1 = service.send_notification(
            user_id="U001",
            notification_type=NotificationType.TRANSACTIONAL,
            title="Payment Successful",
            message="Your payment of $99.99 has been processed successfully.",
            priority=Priority.HIGH,
            metadata={"transaction_id": "TXN123456", "amount": 99.99}
        )
        
        time.sleep(3)  # Wait for processing
        
        if notification1:
            status = service.get_notification_status(notification1.get_id())
            print(f"\n📊 Status: {status}")
        
        # ==================== Alert Notification ====================
        print_section("3. Alert Notification (Urgent)")
        
        notification2 = service.send_notification(
            user_id="U001",
            notification_type=NotificationType.ALERT,
            title="Security Alert",
            message="New login detected from an unknown device.",
            priority=Priority.URGENT,
            metadata={"ip_address": "192.168.1.1", "device": "Unknown"}
        )
        
        time.sleep(3)
        
        # ==================== Promotional Notification ====================
        print_section("4. Promotional Notification (Low Priority)")
        
        notification3 = service.send_notification(
            user_id="U002",
            notification_type=NotificationType.PROMOTIONAL,
            title="Special Offer - 50% Off!",
            message="Limited time offer: Get 50% off on all premium features.",
            priority=Priority.LOW,
            metadata={"campaign_id": "SUMMER2025"}
        )
        
        time.sleep(3)
        
        # ==================== Reminder Notification ====================
        print_section("5. Reminder Notification")
        
        notification4 = service.send_notification(
            user_id="U001",
            notification_type=NotificationType.REMINDER,
            title="Appointment Reminder",
            message="You have a meeting scheduled at 3:00 PM today.",
            priority=Priority.MEDIUM,
            metadata={"meeting_id": "MTG789", "time": "15:00"}
        )
        
        time.sleep(3)
        
        # ==================== System Notification ====================
        print_section("6. System Notification")
        
        notification5 = service.send_notification(
            user_id="U002",
            notification_type=NotificationType.SYSTEM,
            title="System Maintenance",
            message="Scheduled maintenance will occur tonight from 2-4 AM.",
            priority=Priority.MEDIUM
        )
        
        time.sleep(3)
        
        # ==================== Bulk Notifications ====================
        print_section("7. Bulk Notifications with Different Priorities")
        
        for i in range(5):
            priority = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.URGENT][i % 4]
            service.send_notification(
                user_id="U001",
                notification_type=NotificationType.PROMOTIONAL,
                title=f"Bulk Notification #{i+1}",
                message=f"This is bulk notification number {i+1}",
                priority=priority
            )
        
        time.sleep(5)  # Wait for all to process
        
        # ==================== User Notification History ====================
        print_section("8. User Notification History")
        
        alice_notifications = service.get_user_notifications("U001")
        print(f"\n📋 Alice's Notifications ({len(alice_notifications)} total):")
        for notif in alice_notifications[:5]:  # Show first 5
            print(f"   • {notif.get_title()} - Priority: {notif.get_priority().value}")
            statuses = notif.get_all_statuses()
            for channel, status in statuses.items():
                print(f"     └─ {channel.value}: {status.value}")
        
        # ==================== System Statistics ====================
        print_section("9. System Statistics")
        
        stats = service.get_stats()
        print(f"\n📊 System Overview:")
        print(f"   Total Users: {stats['total_users']}")
        print(f"   Total Notifications: {stats['total_notifications']}")
        print(f"\n   Status Breakdown:")
        for status, count in stats['status_breakdown'].items():
            print(f"     • {status}: {count}")
        print(f"\n   Channel Usage:")
        for channel, count in stats['channel_usage'].items():
            print(f"     • {channel}: {count}")
        
        # ==================== Opt-out Scenario ====================
        print_section("10. Opt-out Scenario")
        
        print("\n⚠️  Alice opts out of promotional notifications...")
        user1.opt_out_type(NotificationType.PROMOTIONAL)
        
        notification6 = service.send_notification(
            user_id="U001",
            notification_type=NotificationType.PROMOTIONAL,
            title="Another Promo",
            message="This should not be delivered.",
            priority=Priority.LOW
        )
        
        time.sleep(2)
        
        print("\n✅ Alice opts back in...")
        user1.opt_in_type(NotificationType.PROMOTIONAL)
        
        # ==================== Custom Channel Selection ====================
        print_section("11. Custom Channel Selection")
        
        notification7 = service.send_notification(
            user_id="U002",
            notification_type=NotificationType.TRANSACTIONAL,
            title="Order Shipped",
            message="Your order #12345 has been shipped.",
            priority=Priority.HIGH,
            channels={ChannelType.EMAIL, ChannelType.PUSH},  # Override preferences
            metadata={"order_id": "12345", "tracking": "TRACK123"}
        )
        
        time.sleep(3)
        
        time.sleep(2)  # Let everything finish
        
    finally:
        print_section("Shutting Down System")
        service.stop()
        print("\n✅ Demo completed successfully!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_notification_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
