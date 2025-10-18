from typing import List, Optional, Dict, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import Thread, RLock, Condition, Event
from collections import defaultdict
import time
import json
import pickle
from pathlib import Path


# ==================== Enums ====================

class MessageStatus(Enum):
    """Status of a message"""
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"


class ConsumerState(Enum):
    """State of a consumer"""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


# ==================== Data Models ====================

@dataclass
class Message:
    """Represents a message in the system"""
    message_id: str
    topic: str
    partition: int
    offset: int
    key: Optional[str]
    value: any
    timestamp: datetime
    headers: Dict[str, str] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return (f"Message(id={self.message_id[:8]}..., topic={self.topic}, "
                f"partition={self.partition}, offset={self.offset})")


@dataclass
class ConsumerRecord:
    """Record consumed by a consumer"""
    message: Message
    consumed_at: datetime
    consumer_id: str
    
    def __repr__(self) -> str:
        return f"ConsumerRecord(msg={self.message}, consumer={self.consumer_id})"


@dataclass
class PartitionOffset:
    """Tracks offset information for a partition"""
    topic: str
    partition: int
    current_offset: int  # Next offset to write
    committed_offsets: Dict[str, int]  # consumer_id -> last committed offset
    
    def __repr__(self) -> str:
        return f"PartitionOffset(topic={self.topic}, partition={self.partition}, offset={self.current_offset})"


@dataclass
class ConsumerLag:
    """Consumer lag information"""
    consumer_id: str
    topic: str
    partition: int
    current_offset: int  # Consumer's current position
    log_end_offset: int  # Latest offset in partition
    lag: int  # Difference
    
    def __repr__(self) -> str:
        return (f"ConsumerLag(consumer={self.consumer_id}, topic={self.topic}, "
                f"partition={self.partition}, lag={self.lag})")


# ==================== Partition ====================

class Partition:
    """
    Represents a partition in a topic.
    Stores messages sequentially with increasing offsets.
    """
    
    def __init__(self, topic: str, partition_id: int, storage_path: Optional[str] = None):
        self._topic = topic
        self._partition_id = partition_id
        self._messages: List[Message] = []
        self._current_offset = 0
        self._lock = RLock()
        
        # Persistence
        self._storage_path = storage_path
        if storage_path:
            self._ensure_storage_directory()
            self._load_from_disk()
    
    def append(self, message: Message) -> int:
        """
        Append message to partition
        
        Returns:
            Offset of the appended message
        """
        with self._lock:
            message.offset = self._current_offset
            message.partition = self._partition_id
            self._messages.append(message)
            offset = self._current_offset
            self._current_offset += 1
            
            # Persist to disk
            if self._storage_path:
                self._persist_message(message)
            
            return offset
    
    def get_message(self, offset: int) -> Optional[Message]:
        """Get message at specific offset"""
        with self._lock:
            if 0 <= offset < len(self._messages):
                return self._messages[offset]
            return None
    
    def get_messages(self, start_offset: int, max_messages: int = 100) -> List[Message]:
        """
        Get messages starting from offset
        
        Args:
            start_offset: Starting offset
            max_messages: Maximum number of messages to return
            
        Returns:
            List of messages
        """
        with self._lock:
            if start_offset < 0 or start_offset >= len(self._messages):
                return []
            
            end_offset = min(start_offset + max_messages, len(self._messages))
            return self._messages[start_offset:end_offset]
    
    def get_current_offset(self) -> int:
        """Get next offset to be written"""
        with self._lock:
            return self._current_offset
    
    def get_earliest_offset(self) -> int:
        """Get earliest available offset"""
        return 0
    
    def get_size(self) -> int:
        """Get number of messages in partition"""
        with self._lock:
            return len(self._messages)
    
    def _ensure_storage_directory(self) -> None:
        """Create storage directory if it doesn't exist"""
        path = Path(self._storage_path) / self._topic / f"partition-{self._partition_id}"
        path.mkdir(parents=True, exist_ok=True)
    
    def _get_storage_file(self) -> Path:
        """Get path to partition storage file"""
        return (Path(self._storage_path) / self._topic / 
                f"partition-{self._partition_id}" / "messages.dat")
    
    def _persist_message(self, message: Message) -> None:
        """Persist message to disk"""
        try:
            file_path = self._get_storage_file()
            with open(file_path, 'ab') as f:
                pickle.dump(message, f)
        except Exception as e:
            print(f"Error persisting message: {e}")
    
    def _load_from_disk(self) -> None:
        """Load messages from disk"""
        try:
            file_path = self._get_storage_file()
            if not file_path.exists():
                return
            
            with open(file_path, 'rb') as f:
                while True:
                    try:
                        message = pickle.load(f)
                        self._messages.append(message)
                        self._current_offset = message.offset + 1
                    except EOFError:
                        break
            
            print(f"Loaded {len(self._messages)} messages from {file_path}")
        except Exception as e:
            print(f"Error loading messages: {e}")
    
    def __repr__(self) -> str:
        return f"Partition(topic={self._topic}, id={self._partition_id}, size={len(self._messages)})"


# ==================== Topic ====================

class Topic:
    """
    Represents a topic with multiple partitions.
    Messages are distributed across partitions.
    """
    
    def __init__(self, name: str, num_partitions: int = 3, storage_path: Optional[str] = None):
        self._name = name
        self._num_partitions = num_partitions
        self._partitions: List[Partition] = []
        self._lock = RLock()
        
        # Create partitions
        for i in range(num_partitions):
            partition = Partition(name, i, storage_path)
            self._partitions.append(partition)
    
    def get_name(self) -> str:
        return self._name
    
    def get_num_partitions(self) -> int:
        return self._num_partitions
    
    def get_partition(self, partition_id: int) -> Optional[Partition]:
        """Get specific partition"""
        if 0 <= partition_id < self._num_partitions:
            return self._partitions[partition_id]
        return None
    
    def get_all_partitions(self) -> List[Partition]:
        """Get all partitions"""
        return self._partitions.copy()
    
    def select_partition(self, key: Optional[str] = None) -> int:
        """
        Select partition for a message.
        If key is provided, use hash-based partitioning.
        Otherwise, use round-robin.
        """
        if key:
            # Hash-based partitioning
            return hash(key) % self._num_partitions
        else:
            # Round-robin (simplified - in production would track counter)
            return hash(str(time.time())) % self._num_partitions
    
    def __repr__(self) -> str:
        total_messages = sum(p.get_size() for p in self._partitions)
        return f"Topic(name={self._name}, partitions={self._num_partitions}, messages={total_messages})"


# ==================== Producer ====================

class Producer:
    """
    Produces messages to topics.
    Handles partitioning and message delivery.
    """
    
    def __init__(self, producer_id: str, broker: 'MessageBroker'):
        self._producer_id = producer_id
        self._broker = broker
        self._message_counter = 0
        self._lock = RLock()
    
    def send(self, 
             topic: str, 
             value: any,
             key: Optional[str] = None,
             headers: Optional[Dict[str, str]] = None,
             partition: Optional[int] = None) -> Message:
        """
        Send message to topic
        
        Args:
            topic: Topic name
            value: Message value
            key: Optional message key (for partitioning)
            headers: Optional message headers
            partition: Optional specific partition (overrides key-based partitioning)
            
        Returns:
            Sent message with assigned offset
        """
        with self._lock:
            self._message_counter += 1
            message_id = f"{self._producer_id}-{self._message_counter}"
        
        message = Message(
            message_id=message_id,
            topic=topic,
            partition=-1,  # Will be set by broker
            offset=-1,  # Will be set by partition
            key=key,
            value=value,
            timestamp=datetime.now(),
            headers=headers or {}
        )
        
        # Send to broker
        return self._broker.publish(message, partition)
    
    def send_batch(self, topic: str, messages: List[tuple]) -> List[Message]:
        """
        Send batch of messages
        
        Args:
            topic: Topic name
            messages: List of (value, key) tuples
            
        Returns:
            List of sent messages
        """
        sent_messages = []
        for value, key in messages:
            msg = self.send(topic, value, key)
            sent_messages.append(msg)
        return sent_messages
    
    def __repr__(self) -> str:
        return f"Producer(id={self._producer_id})"


# ==================== Consumer ====================

class Consumer:
    """
    Consumes messages from topics.
    Supports pull-based message consumption with offset management.
    """
    
    def __init__(self, 
                 consumer_id: str,
                 group_id: str,
                 broker: 'MessageBroker',
                 auto_commit: bool = True,
                 poll_timeout_ms: int = 1000):
        self._consumer_id = consumer_id
        self._group_id = group_id
        self._broker = broker
        self._auto_commit = auto_commit
        self._poll_timeout_ms = poll_timeout_ms
        
        # Subscriptions
        self._subscribed_topics: Set[str] = set()
        self._assigned_partitions: Dict[str, List[int]] = defaultdict(list)  # topic -> partitions
        
        # Offset management
        self._current_offsets: Dict[tuple, int] = {}  # (topic, partition) -> offset
        
        # State management
        self._state = ConsumerState.IDLE
        self._lock = RLock()
        
        # Message handler
        self._message_handler: Optional[Callable[[Message], None]] = None
        
        # Polling thread
        self._poll_thread: Optional[Thread] = None
        self._stop_polling = Event()
    
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to topics"""
        with self._lock:
            self._subscribed_topics.update(topics)
            
            # Register with broker for partition assignment
            for topic in topics:
                partitions = self._broker.assign_partitions(self._group_id, self._consumer_id, topic)
                self._assigned_partitions[topic] = partitions
                
                # Initialize offsets for assigned partitions
                for partition in partitions:
                    key = (topic, partition)
                    if key not in self._current_offsets:
                        # Try to get committed offset from broker
                        committed_offset = self._broker.get_committed_offset(
                            self._group_id, topic, partition
                        )
                        self._current_offsets[key] = committed_offset
        
        print(f"Consumer {self._consumer_id} subscribed to {topics}")
        print(f"Assigned partitions: {dict(self._assigned_partitions)}")
    
    def poll(self, max_records: int = 100) -> List[Message]:
        """
        Poll for messages from subscribed topics
        
        Args:
            max_records: Maximum number of records to return
            
        Returns:
            List of messages
        """
        messages = []
        
        with self._lock:
            for topic, partitions in self._assigned_partitions.items():
                for partition in partitions:
                    key = (topic, partition)
                    current_offset = self._current_offsets.get(key, 0)
                    
                    # Fetch messages from broker
                    partition_messages = self._broker.fetch_messages(
                        topic, partition, current_offset, max_records
                    )
                    
                    if partition_messages:
                        messages.extend(partition_messages)
                        
                        # Update offset
                        last_offset = partition_messages[-1].offset
                        self._current_offsets[key] = last_offset + 1
                        
                        # Auto-commit if enabled
                        if self._auto_commit:
                            self.commit_offset(topic, partition, last_offset + 1)
        
        return messages
    
    def commit_offset(self, topic: str, partition: int, offset: int) -> None:
        """Commit offset for a partition"""
        self._broker.commit_offset(self._group_id, topic, partition, offset)
    
    def commit_all(self) -> None:
        """Commit all current offsets"""
        with self._lock:
            for (topic, partition), offset in self._current_offsets.items():
                self.commit_offset(topic, partition, offset)
    
    def seek(self, topic: str, partition: int, offset: int) -> None:
        """Seek to specific offset"""
        with self._lock:
            key = (topic, partition)
            self._current_offsets[key] = offset
    
    def get_position(self, topic: str, partition: int) -> int:
        """Get current position for a partition"""
        with self._lock:
            return self._current_offsets.get((topic, partition), 0)
    
    def set_message_handler(self, handler: Callable[[Message], None]) -> None:
        """Set message handler for automatic processing"""
        self._message_handler = handler
    
    def start(self) -> None:
        """Start consumer in background thread"""
        if self._state == ConsumerState.RUNNING:
            return
        
        with self._lock:
            self._state = ConsumerState.RUNNING
            self._stop_polling.clear()
            self._poll_thread = Thread(target=self._polling_loop, daemon=True)
            self._poll_thread.start()
        
        print(f"Consumer {self._consumer_id} started")
    
    def stop(self) -> None:
        """Stop consumer"""
        with self._lock:
            self._state = ConsumerState.STOPPED
            self._stop_polling.set()
        
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
        
        # Commit final offsets
        self.commit_all()
        
        print(f"Consumer {self._consumer_id} stopped")
    
    def _polling_loop(self) -> None:
        """Background polling loop"""
        while not self._stop_polling.is_set():
            try:
                messages = self.poll()
                
                if messages and self._message_handler:
                    for message in messages:
                        try:
                            self._message_handler(message)
                        except Exception as e:
                            print(f"Error processing message: {e}")
                
                # Sleep briefly to avoid tight loop
                time.sleep(self._poll_timeout_ms / 1000.0)
                
            except Exception as e:
                print(f"Error in polling loop: {e}")
                time.sleep(1.0)
    
    def get_lag(self) -> List[ConsumerLag]:
        """Get consumer lag for all assigned partitions"""
        lags = []
        
        with self._lock:
            for topic, partitions in self._assigned_partitions.items():
                for partition in partitions:
                    current_offset = self._current_offsets.get((topic, partition), 0)
                    log_end_offset = self._broker.get_partition_offset(topic, partition)
                    
                    lag = ConsumerLag(
                        consumer_id=self._consumer_id,
                        topic=topic,
                        partition=partition,
                        current_offset=current_offset,
                        log_end_offset=log_end_offset,
                        lag=log_end_offset - current_offset
                    )
                    lags.append(lag)
        
        return lags
    
    def __repr__(self) -> str:
        return f"Consumer(id={self._consumer_id}, group={self._group_id}, topics={list(self._subscribed_topics)})"


# ==================== Message Broker ====================

class MessageBroker:
    """
    Central message broker managing topics, producers, and consumers.
    Handles message routing, partition assignment, and offset management.
    """
    
    def __init__(self, broker_id: str, storage_path: Optional[str] = None):
        self._broker_id = broker_id
        self._storage_path = storage_path
        
        # Topics
        self._topics: Dict[str, Topic] = {}
        
        # Consumer groups and partition assignment
        self._consumer_groups: Dict[str, Set[str]] = defaultdict(set)  # group_id -> consumer_ids
        self._partition_assignments: Dict[str, Dict[str, List[tuple]]] = defaultdict(
            lambda: defaultdict(list)
        )  # group_id -> consumer_id -> [(topic, partition)]
        
        # Offset management (for consumer groups)
        self._committed_offsets: Dict[tuple, int] = {}  # (group_id, topic, partition) -> offset
        
        # Locks
        self._topics_lock = RLock()
        self._consumers_lock = RLock()
        self._offsets_lock = RLock()
        
        # Notification system for new messages
        self._topic_conditions: Dict[str, Condition] = {}
    
    def create_topic(self, topic_name: str, num_partitions: int = 3) -> Topic:
        """Create a new topic"""
        with self._topics_lock:
            if topic_name in self._topics:
                print(f"Topic {topic_name} already exists")
                return self._topics[topic_name]
            
            topic = Topic(topic_name, num_partitions, self._storage_path)
            self._topics[topic_name] = topic
            self._topic_conditions[topic_name] = Condition()
            
            print(f"Created topic: {topic}")
            return topic
    
    def get_topic(self, topic_name: str) -> Optional[Topic]:
        """Get topic by name"""
        with self._topics_lock:
            return self._topics.get(topic_name)
    
    def list_topics(self) -> List[str]:
        """List all topic names"""
        with self._topics_lock:
            return list(self._topics.keys())
    
    def publish(self, message: Message, partition: Optional[int] = None) -> Message:
        """
        Publish message to topic
        
        Args:
            message: Message to publish
            partition: Optional specific partition
            
        Returns:
            Published message with offset assigned
        """
        with self._topics_lock:
            topic = self._topics.get(message.topic)
            if not topic:
                raise ValueError(f"Topic {message.topic} does not exist")
            
            # Select partition
            if partition is not None:
                partition_id = partition
            else:
                partition_id = topic.select_partition(message.key)
            
            # Append to partition
            partition_obj = topic.get_partition(partition_id)
            offset = partition_obj.append(message)
            
            # Notify waiting consumers
            if message.topic in self._topic_conditions:
                with self._topic_conditions[message.topic]:
                    self._topic_conditions[message.topic].notify_all()
        
        return message
    
    def fetch_messages(self, 
                      topic: str, 
                      partition: int, 
                      offset: int, 
                      max_messages: int = 100) -> List[Message]:
        """Fetch messages from a partition"""
        with self._topics_lock:
            topic_obj = self._topics.get(topic)
            if not topic_obj:
                return []
            
            partition_obj = topic_obj.get_partition(partition)
            if not partition_obj:
                return []
            
            return partition_obj.get_messages(offset, max_messages)
    
    def assign_partitions(self, group_id: str, consumer_id: str, topic: str) -> List[int]:
        """
        Assign partitions to consumer (simplified round-robin assignment)
        
        In production, this would implement more sophisticated strategies like
        range assignment or sticky assignment.
        """
        with self._consumers_lock:
            # Add consumer to group
            self._consumer_groups[group_id].add(consumer_id)
            
            # Get topic
            topic_obj = self.get_topic(topic)
            if not topic_obj:
                return []
            
            # Simple round-robin assignment
            consumers = sorted(list(self._consumer_groups[group_id]))
            num_consumers = len(consumers)
            num_partitions = topic_obj.get_num_partitions()
            
            consumer_index = consumers.index(consumer_id)
            assigned_partitions = []
            
            for partition_id in range(num_partitions):
                if partition_id % num_consumers == consumer_index:
                    assigned_partitions.append(partition_id)
            
            # Store assignment
            self._partition_assignments[group_id][consumer_id] = [
                (topic, p) for p in assigned_partitions
            ]
            
            return assigned_partitions
    
    def commit_offset(self, group_id: str, topic: str, partition: int, offset: int) -> None:
        """Commit offset for consumer group"""
        with self._offsets_lock:
            key = (group_id, topic, partition)
            self._committed_offsets[key] = offset
    
    def get_committed_offset(self, group_id: str, topic: str, partition: int) -> int:
        """Get committed offset for consumer group"""
        with self._offsets_lock:
            key = (group_id, topic, partition)
            return self._committed_offsets.get(key, 0)
    
    def get_partition_offset(self, topic: str, partition: int) -> int:
        """Get current offset (end) of a partition"""
        with self._topics_lock:
            topic_obj = self._topics.get(topic)
            if not topic_obj:
                return 0
            
            partition_obj = topic_obj.get_partition(partition)
            if not partition_obj:
                return 0
            
            return partition_obj.get_current_offset()
    
    def get_consumer_lag(self, group_id: str) -> List[ConsumerLag]:
        """Get lag for all consumers in a group"""
        lags = []
        
        with self._consumers_lock, self._offsets_lock, self._topics_lock:
            for consumer_id in self._consumer_groups.get(group_id, []):
                assignments = self._partition_assignments[group_id][consumer_id]
                
                for topic, partition in assignments:
                    committed_offset = self.get_committed_offset(group_id, topic, partition)
                    log_end_offset = self.get_partition_offset(topic, partition)
                    
                    lag = ConsumerLag(
                        consumer_id=consumer_id,
                        topic=topic,
                        partition=partition,
                        current_offset=committed_offset,
                        log_end_offset=log_end_offset,
                        lag=log_end_offset - committed_offset
                    )
                    lags.append(lag)
        
        return lags
    
    def get_stats(self) -> Dict:
        """Get broker statistics"""
        with self._topics_lock, self._consumers_lock:
            stats = {
                "broker_id": self._broker_id,
                "topics": len(self._topics),
                "consumer_groups": len(self._consumer_groups),
                "topic_stats": {}
            }
            
            for topic_name, topic in self._topics.items():
                total_messages = sum(p.get_size() for p in topic.get_all_partitions())
                stats["topic_stats"][topic_name] = {
                    "partitions": topic.get_num_partitions(),
                    "total_messages": total_messages
                }
            
            return stats
    
    def __repr__(self) -> str:
        return f"MessageBroker(id={self._broker_id}, topics={len(self._topics)})"


# ==================== Demo Usage ====================

def main():
    """Demo the pub-sub messaging system"""
    print("=== Pub-Sub Messaging System Demo ===\n")
    
    # Create broker with persistence
    broker = MessageBroker("broker-1", storage_path="./message_storage")
    
    # Test Case 1: Create Topics
    print("="*70)
    print("TEST CASE 1: Create Topics")
    print("="*70)
    
    orders_topic = broker.create_topic("orders", num_partitions=3)
    payments_topic = broker.create_topic("payments", num_partitions=2)
    notifications_topic = broker.create_topic("notifications", num_partitions=4)
    
    print(f"\nTopics: {broker.list_topics()}")
    
    # Test Case 2: Producer Sends Messages
    print("\n" + "="*70)
    print("TEST CASE 2: Producer Sends Messages")
    print("="*70)
    
    producer1 = Producer("producer-1", broker)
    
    print("\nSending orders...")
    for i in range(10):
        order_id = f"order-{i+1}"
        message = producer1.send(
            topic="orders",
            value={"order_id": order_id, "amount": 100 + i * 10, "status": "pending"},
            key=order_id  # Key-based partitioning
        )
        print(f"Sent: {message}")
    
    print(f"\nTopic stats: {orders_topic}")
    
    # Test Case 3: Consumer Subscribes and Polls
    print("\n" + "="*70)
    print("TEST CASE 3: Consumer Subscribes and Polls")
    print("="*70)
    
    consumer1 = Consumer("consumer-1", "order-processing-group", broker)
    consumer1.subscribe(["orders"])
    
    print("\nPolling for messages...")
    messages = consumer1.poll(max_records=5)
    print(f"Received {len(messages)} messages:")
    for msg in messages:
        print(f"  {msg}: {msg.value}")
    
    # Test Case 4: Multiple Consumers in Same Group (Parallel Processing)
    print("\n" + "="*70)
    print("TEST CASE 4: Multiple Consumers in Same Group (Load Balancing)")
    print("="*70)
    
    consumer2 = Consumer("consumer-2", "order-processing-group", broker)
    consumer2.subscribe(["orders"])
    
    print("\nConsumer 1 polls:")
    msgs1 = consumer1.poll(max_records=3)
    print(f"Consumer 1 got {len(msgs1)} messages from partitions: "
          f"{set(m.partition for m in msgs1)}")
    
    print("\nConsumer 2 polls:")
    msgs2 = consumer2.poll(max_records=3)
    print(f"Consumer 2 got {len(msgs2)} messages from partitions: "
          f"{set(m.partition for m in msgs2)}")
    
    # Test Case 5: Consumer Lag
    print("\n" + "="*70)
    print("TEST CASE 5: Consumer Lag Tracking")
    print("="*70)
    
    # Send more messages
    print("\nProducer sends 20 more messages...")
    for i in range(20):
        producer1.send(
            topic="orders",
            value={"order_id": f"order-{i+11}", "amount": 200 + i * 5},
            key=f"order-{i+11}"
        )
    
    print("\nConsumer lag:")
    lag_info = consumer1.get_lag()
    for lag in lag_info:
        print(f"  {lag}")
    
    print("\nConsumer 1 polls remaining messages...")
    while True:
        messages = consumer1.poll(max_records=10)
        if not messages:
            break
        print(f"Polled {len(messages)} messages")
    
    print("\nConsumer lag after catching up:")
    lag_info = consumer1.get_lag()
    for lag in lag_info:
        print(f"  {lag}")
    
    # Test Case 6: Multiple Topics Subscription
    print("\n" + "="*70)
    print("TEST CASE 6: Subscribe to Multiple Topics")
    print("="*70)
    
    consumer3 = Consumer("consumer-3", "multi-topic-group", broker)
    consumer3.subscribe(["orders", "payments"])
    
    print("\nSending messages to both topics...")
    producer1.send("orders", {"order_id": "order-100", "amount": 500}, "order-100")
    producer1.send("payments", {"payment_id": "pay-1", "amount": 500}, "pay-1")
    producer1.send("orders", {"order_id": "order-101", "amount": 600}, "order-101")
    producer1.send("payments", {"payment_id": "pay-2", "amount": 600}, "pay-2")
    
    print("\nConsumer 3 polls from multiple topics:")
    messages = consumer3.poll(max_records=10)
    for msg in messages:
        print(f"  Topic: {msg.topic}, Partition: {msg.partition}, Value: {msg.value}")
    
    # Test Case 7: Automatic Message Processing with Handler
    print("\n" + "="*70)
    print("TEST CASE 7: Automatic Message Processing with Handler")
    print("="*70)
    
    processed_count = [0]  # Use list for closure
    
    def process_notification(message: Message):
        """Message handler function"""
        processed_count[0] += 1
        print(f"  Processing notification {processed_count[0]}: {message.value}")
    
    consumer4 = Consumer("consumer-4", "notification-group", broker, auto_commit=True)
    consumer4.subscribe(["notifications"])
    consumer4.set_message_handler(process_notification)
    
    print("\nSending notifications...")
    for i in range(10):
        producer1.send(
            "notifications",
            {"type": "email", "user_id": f"user-{i}", "message": f"Hello user {i}"},
            key=f"user-{i}"
        )
    
    print("\nStarting consumer in background...")
    consumer4.start()
    
    print("Waiting for consumer to process messages...")
    time.sleep(2)
    
    consumer4.stop()
    print(f"\nTotal notifications processed: {processed_count[0]}")
    
    # Test Case 8: Offset Management (Seek)
    print("\n" + "="*70)
    print("TEST CASE 8: Offset Management - Seek and Replay")
    print("="*70)
    
    consumer5 = Consumer("consumer-5", "replay-group", broker, auto_commit=False)
    consumer5.subscribe(["orders"])
    
    print("\nInitial poll (starting from offset 0):")
    messages = consumer5.poll(max_records=5)
    print(f"Got {len(messages)} messages, offsets: {[m.offset for m in messages]}")
    
    print("\nSeeking back to offset 0...")
    for topic, partitions in consumer5._assigned_partitions.items():
        for partition in partitions:
            consumer5.seek(topic, partition, 0)
    
    print("\nPolling again after seek:")
    messages = consumer5.poll(max_records=5)
    print(f"Got {len(messages)} messages, offsets: {[m.offset for m in messages]}")
    
    # Test Case 9: Batch Publishing
    print("\n" + "="*70)
    print("TEST CASE 9: Batch Publishing")
    print("="*70)
    
    print("\nSending batch of messages...")
    batch = [
        ({"product": "laptop", "price": 1000}, "product-1"),
        ({"product": "mouse", "price": 25}, "product-2"),
        ({"product": "keyboard", "price": 75}, "product-3"),
        ({"product": "monitor", "price": 300}, "product-4"),
    ]
    
    producer2 = Producer("producer-2", broker)
    sent_messages = producer2.send_batch("orders", batch)
    print(f"Sent {len(sent_messages)} messages in batch")
    
    # Test Case 10: Broadcasting (Multiple Consumer Groups)
    print("\n" + "="*70)
    print("TEST CASE 10: Broadcasting to Multiple Consumer Groups")
    print("="*70)
    
    # Create consumers in different groups
    consumer_group_a = Consumer("consumer-a1", "group-a", broker)
    consumer_group_b = Consumer("consumer-b1", "group-b", broker)
    
    consumer_group_a.subscribe(["notifications"])
    consumer_group_b.subscribe(["notifications"])
    
    print("\nSending broadcast message...")
    producer1.send("notifications", {"broadcast": "System maintenance at 2 AM"}, "broadcast-1")
    
    print("\nGroup A consumer polls:")
    msgs_a = consumer_group_a.poll(max_records=5)
    print(f"Group A received: {len(msgs_a)} messages")
    for msg in msgs_a:
        if msg.value.get("broadcast"):
            print(f"  Group A got broadcast: {msg.value['broadcast']}")
    
    print("\nGroup B consumer polls:")
    msgs_b = consumer_group_b.poll(max_records=5)
    print(f"Group B received: {len(msgs_b)} messages")
    for msg in msgs_b:
        if msg.value.get("broadcast"):
            print(f"  Group B got broadcast: {msg.value['broadcast']}")
    
    # Test Case 11: Message Headers and Metadata
    print("\n" + "="*70)
    print("TEST CASE 11: Message Headers and Metadata")
    print("="*70)
    
    print("\nSending message with headers...")
    message_with_headers = producer1.send(
        topic="orders",
        value={"order_id": "special-order-1", "amount": 5000},
        key="special-order-1",
        headers={
            "priority": "high",
            "source": "mobile-app",
            "user-agent": "iOS/14.5"
        }
    )
    
    print(f"Sent message: {message_with_headers}")
    print(f"Headers: {message_with_headers.headers}")
    
    consumer6 = Consumer("consumer-6", "header-test-group", broker)
    consumer6.subscribe(["orders"])
    
    messages = consumer6.poll(max_records=1)
    if messages:
        msg = messages[-1]
        print(f"\nReceived message: {msg}")
        print(f"Headers: {msg.headers}")
        print(f"Timestamp: {msg.timestamp}")
    
    # Test Case 12: Partition-Specific Operations
    print("\n" + "="*70)
    print("TEST CASE 12: Partition-Specific Operations")
    print("="*70)
    
    print("\nSending to specific partitions...")
    for partition_id in range(3):
        msg = producer1.send(
            topic="orders",
            value={"partition_test": True, "partition_id": partition_id},
            partition=partition_id
        )
        print(f"Sent to partition {msg.partition}: {msg.value}")
    
    print("\nPartition distribution:")
    for partition_id in range(orders_topic.get_num_partitions()):
        partition = orders_topic.get_partition(partition_id)
        print(f"  Partition {partition_id}: {partition.get_size()} messages")
    
    # Test Case 13: Consumer Group Lag Monitoring
    print("\n" + "="*70)
    print("TEST CASE 13: Consumer Group Lag Monitoring")
    print("="*70)
    
    print("\nSending more messages to create lag...")
    for i in range(30):
        producer1.send("orders", {"test": f"lag-test-{i}"}, f"key-{i}")
    
    print("\nConsumer group lag (order-processing-group):")
    group_lag = broker.get_consumer_lag("order-processing-group")
    for lag in group_lag:
        print(f"  {lag}")
    
    total_lag = sum(lag.lag for lag in group_lag)
    print(f"\nTotal lag across all partitions: {total_lag} messages")
    
    # Test Case 14: Broker Statistics
    print("\n" + "="*70)
    print("TEST CASE 14: Broker Statistics")
    print("="*70)
    
    stats = broker.get_stats()
    print("\nBroker Stats:")
    print(f"  Broker ID: {stats['broker_id']}")
    print(f"  Total Topics: {stats['topics']}")
    print(f"  Consumer Groups: {stats['consumer_groups']}")
    print("\n  Topic Details:")
    for topic_name, topic_stats in stats['topic_stats'].items():
        print(f"    {topic_name}:")
        print(f"      Partitions: {topic_stats['partitions']}")
        print(f"      Total Messages: {topic_stats['total_messages']}")
    
    # Test Case 15: Message Persistence and Recovery
    print("\n" + "="*70)
    print("TEST CASE 15: Message Persistence and Recovery")
    print("="*70)
    
    print("\nCreating new topic with persistence...")
    persistent_topic = broker.create_topic("persistent-test", num_partitions=2)
    
    print("Writing messages...")
    for i in range(5):
        producer1.send("persistent-test", {"data": f"persistent-{i}"}, f"key-{i}")
    
    print(f"Topic has {persistent_topic.get_partition(0).get_size() + persistent_topic.get_partition(1).get_size()} messages")
    
    print("\nSimulating broker restart...")
    print("Creating new broker instance with same storage path...")
    
    broker2 = MessageBroker("broker-2", storage_path="./message_storage")
    recovered_topic = broker2.get_topic("persistent-test")
    
    if recovered_topic is None:
        # Topic needs to be recreated, but partitions will load from disk
        recovered_topic = broker2.create_topic("persistent-test", num_partitions=2)
    
    total_recovered = sum(p.get_size() for p in recovered_topic.get_all_partitions())
    print(f"Recovered topic has {total_recovered} messages")
    
    # Test Case 16: Concurrent Producers
    print("\n" + "="*70)
    print("TEST CASE 16: Concurrent Producers (Thread Safety)")
    print("="*70)
    
    import threading
    
    messages_sent = [0]
    
    def producer_thread(thread_id: int, count: int):
        producer = Producer(f"producer-thread-{thread_id}", broker)
        for i in range(count):
            producer.send(
                "orders",
                {"thread": thread_id, "seq": i},
                f"thread-{thread_id}-msg-{i}"
            )
            messages_sent[0] += 1
    
    print("\nStarting 5 concurrent producers...")
    threads = []
    for i in range(5):
        t = threading.Thread(target=producer_thread, args=(i, 10))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"Total messages sent by all producers: {messages_sent[0]}")
    
    # Test Case 17: Consumer Offset Commit Strategies
    print("\n" + "="*70)
    print("TEST CASE 17: Manual vs Auto Commit")
    print("="*70)
    
    # Auto-commit consumer
    auto_consumer = Consumer("auto-commit-consumer", "auto-group", broker, auto_commit=True)
    auto_consumer.subscribe(["orders"])
    
    print("\nAuto-commit consumer polls:")
    messages = auto_consumer.poll(max_records=5)
    print(f"Polled {len(messages)} messages (auto-committed)")
    
    # Manual commit consumer
    manual_consumer = Consumer("manual-commit-consumer", "manual-group", broker, auto_commit=False)
    manual_consumer.subscribe(["orders"])
    
    print("\nManual-commit consumer polls:")
    messages = manual_consumer.poll(max_records=5)
    print(f"Polled {len(messages)} messages (not yet committed)")
    
    print("Manually committing offsets...")
    manual_consumer.commit_all()
    print("Offsets committed")
    
    # Test Case 18: Consumer Position Tracking
    print("\n" + "="*70)
    print("TEST CASE 18: Consumer Position Tracking")
    print("="*70)
    
    consumer7 = Consumer("consumer-7", "position-group", broker)
    consumer7.subscribe(["orders"])
    
    print("\nInitial positions:")
    for topic, partitions in consumer7._assigned_partitions.items():
        for partition in partitions:
            position = consumer7.get_position(topic, partition)
            print(f"  Topic: {topic}, Partition: {partition}, Position: {position}")
    
    print("\nPolling messages...")
    consumer7.poll(max_records=10)
    
    print("\nPositions after polling:")
    for topic, partitions in consumer7._assigned_partitions.items():
        for partition in partitions:
            position = consumer7.get_position(topic, partition)
            print(f"  Topic: {topic}, Partition: {partition}, Position: {position}")
    
    # Cleanup
    print("\n" + "="*70)
    print("Cleanup")
    print("="*70)
    
    print("\nStopping all consumers...")
    consumer4.stop()
    
    print("\nFinal broker statistics:")
    final_stats = broker.get_stats()
    print(json.dumps(final_stats, indent=2))
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# Strategy Pattern - Could be extended for different partition assignment strategies (round-robin, range, sticky)
# Observer Pattern - Implicit in the pub-sub model where consumers observe topics
# Factory Pattern - Could add a factory for creating different types of consumers/producers

# Key Features Implemented:

# Topic, Partition, Offset:

# Topics divided into multiple partitions for parallelism
# Sequential offset assignment within partitions
# Offset-based message addressing


# Producer & Consumer:

# Producers send messages with optional keys for partition routing
# Consumers use pull-based model with configurable polling
# Support for batch operations


# Consumer Groups:

# Multiple consumers can be in the same group for load balancing
# Partition assignment across group members
# Each group maintains independent offsets


# Consumer Lag:

# Track difference between consumer position and partition end
# Detailed lag metrics per partition
# Group-level lag monitoring


# Pull Mechanism:

# Consumers actively poll for messages
# Configurable batch sizes
# Offset management for replay capability


# Multiple Topics:

# Consumers can subscribe to multiple topics
# Single consumer handles messages from all subscribed topics
# Topic-level isolation


# Broadcasting:

# Different consumer groups receive same messages independently
# Each group maintains own offsets
# Enables multiple independent processing pipelines


# Parallel Processing:

# Partition-level parallelism
# Multiple consumers in a group process different partitions
# Thread-safe operations


# Message Persistence:

# Partitions persist messages to disk
# Recovery on restart
# Durable message storage


# Additional Features:

# Message headers and metadata
# Key-based and explicit partition routing
# Auto-commit and manual commit strategies
# Seek/replay capability
# Background consumer with message handlers
# Thread-safe concurrent access
# Comprehensive statistics and monitoring



# Architecture Decisions:

# Pull vs Push: Implemented pull-based consumption (like Kafka) giving consumers control over rate
# Partition Assignment: Simplified round-robin (production would use more sophisticated strategies)
# Offset Storage: In-memory with disk persistence (production would use dedicated storage)
# Concurrency: RLock for thread safety, allowing reentrant operations
# Message Ordering: Guaranteed within partitions, not across partitions

# This design provides a solid foundation for a production-ready message broker system!
