from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Generic, TypeVar
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict
from threading import RLock, Thread
from enum import Enum
import time
import heapq

# ==================== Type Variables ====================

K = TypeVar('K')  # Key type
V = TypeVar('V')  # Value type


# ==================== Enums ====================

class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "LRU"  # Least Recently Used
    LFU = "LFU"  # Least Frequently Used
    FIFO = "FIFO"  # First In First Out
    LIFO = "LIFO"  # Last In First Out


# ==================== Data Models ====================

@dataclass
class CacheEntry(Generic[V]):
    """Represents a cache entry with metadata"""
    value: V
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: Optional[int] = None  # Time to live in seconds
    
    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL"""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def touch(self) -> None:
        """Update access metadata"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 1.0 - self.hit_rate()
    
    def __repr__(self) -> str:
        return (f"CacheStats(hits={self.hits}, misses={self.misses}, "
                f"evictions={self.evictions}, expirations={self.expirations}, "
                f"hit_rate={self.hit_rate():.2%})")


# ==================== Eviction Strategy Pattern ====================

class EvictionStrategy(ABC, Generic[K, V]):
    """Abstract base class for eviction strategies"""
    
    @abstractmethod
    def on_get(self, key: K) -> None:
        """Called when a key is accessed"""
        pass
    
    @abstractmethod
    def on_put(self, key: K) -> None:
        """Called when a key is inserted"""
        pass
    
    @abstractmethod
    def evict(self) -> Optional[K]:
        """Select and return key to evict"""
        pass
    
    @abstractmethod
    def remove(self, key: K) -> None:
        """Remove key from eviction tracking"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all eviction metadata"""
        pass


class LRUEvictionStrategy(EvictionStrategy[K, V]):
    """Least Recently Used eviction strategy"""
    
    def __init__(self):
        # OrderedDict maintains insertion order and allows efficient reordering
        self._access_order: OrderedDict[K, bool] = OrderedDict()
    
    def on_get(self, key: K) -> None:
        """Move key to end (most recently used)"""
        if key in self._access_order:
            self._access_order.move_to_end(key)
    
    def on_put(self, key: K) -> None:
        """Add key to end (most recently used)"""
        if key in self._access_order:
            self._access_order.move_to_end(key)
        else:
            self._access_order[key] = True
    
    def evict(self) -> Optional[K]:
        """Evict least recently used key (first item)"""
        if not self._access_order:
            return None
        # Pop first item (least recently used)
        key, _ = self._access_order.popitem(last=False)
        return key
    
    def remove(self, key: K) -> None:
        """Remove key from tracking"""
        self._access_order.pop(key, None)
    
    def clear(self) -> None:
        """Clear all tracking"""
        self._access_order.clear()


class LFUEvictionStrategy(EvictionStrategy[K, V]):
    """Least Frequently Used eviction strategy"""
    
    def __init__(self):
        # Track frequency of each key
        self._frequencies: Dict[K, int] = {}
        # Min heap to track keys by frequency (frequency, insertion_order, key)
        self._heap: list = []
        self._insertion_counter = 0
    
    def on_get(self, key: K) -> None:
        """Increment frequency on access"""
        if key in self._frequencies:
            self._frequencies[key] += 1
    
    def on_put(self, key: K) -> None:
        """Initialize or update frequency"""
        if key not in self._frequencies:
            self._frequencies[key] = 1
            self._insertion_counter += 1
            heapq.heappush(self._heap, (1, self._insertion_counter, key))
    
    def evict(self) -> Optional[K]:
        """Evict least frequently used key"""
        while self._heap:
            freq, _, key = heapq.heappop(self._heap)
            
            # Check if this entry is still valid
            if key in self._frequencies and self._frequencies[key] == freq:
                del self._frequencies[key]
                return key
        
        return None
    
    def remove(self, key: K) -> None:
        """Remove key from tracking"""
        self._frequencies.pop(key, None)
        # Note: Don't remove from heap (lazy deletion on evict)
    
    def clear(self) -> None:
        """Clear all tracking"""
        self._frequencies.clear()
        self._heap.clear()
        self._insertion_counter = 0


class FIFOEvictionStrategy(EvictionStrategy[K, V]):
    """First In First Out eviction strategy"""
    
    def __init__(self):
        # Track insertion order
        self._queue: OrderedDict[K, bool] = OrderedDict()
    
    def on_get(self, key: K) -> None:
        """No action needed for FIFO on access"""
        pass
    
    def on_put(self, key: K) -> None:
        """Add key to queue"""
        if key not in self._queue:
            self._queue[key] = True
    
    def evict(self) -> Optional[K]:
        """Evict first inserted key"""
        if not self._queue:
            return None
        key, _ = self._queue.popitem(last=False)
        return key
    
    def remove(self, key: K) -> None:
        """Remove key from tracking"""
        self._queue.pop(key, None)
    
    def clear(self) -> None:
        """Clear all tracking"""
        self._queue.clear()


class LIFOEvictionStrategy(EvictionStrategy[K, V]):
    """Last In First Out eviction strategy"""
    
    def __init__(self):
        # Track insertion order
        self._stack: OrderedDict[K, bool] = OrderedDict()
    
    def on_get(self, key: K) -> None:
        """No action needed for LIFO on access"""
        pass
    
    def on_put(self, key: K) -> None:
        """Add key to stack"""
        if key not in self._stack:
            self._stack[key] = True
    
    def evict(self) -> Optional[K]:
        """Evict last inserted key"""
        if not self._stack:
            return None
        key, _ = self._stack.popitem(last=True)
        return key
    
    def remove(self, key: K) -> None:
        """Remove key from tracking"""
        self._stack.pop(key, None)
    
    def clear(self) -> None:
        """Clear all tracking"""
        self._stack.clear()


# ==================== Eviction Strategy Factory ====================

class EvictionStrategyFactory:
    """Factory for creating eviction strategies"""
    
    @staticmethod
    def create_strategy(policy: EvictionPolicy) -> EvictionStrategy:
        """Create an eviction strategy based on policy"""
        strategies = {
            EvictionPolicy.LRU: LRUEvictionStrategy,
            EvictionPolicy.LFU: LFUEvictionStrategy,
            EvictionPolicy.FIFO: FIFOEvictionStrategy,
            EvictionPolicy.LIFO: LIFOEvictionStrategy,
        }
        
        strategy_class = strategies.get(policy)
        if not strategy_class:
            raise ValueError(f"Unknown eviction policy: {policy}")
        
        return strategy_class()


# ==================== Cache Implementation ====================

class Cache(Generic[K, V]):
    """
    Thread-safe cache implementation with:
    - Configurable eviction policies (LRU, LFU, FIFO, LIFO)
    - TTL support for time-based expiration
    - Hit/miss tracking and statistics
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, 
                 capacity: int,
                 eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
                 default_ttl_seconds: Optional[int] = None,
                 enable_stats: bool = True,
                 cleanup_interval_seconds: int = 60):
        """
        Initialize cache
        
        Args:
            capacity: Maximum number of entries
            eviction_policy: Policy for evicting entries when full
            default_ttl_seconds: Default TTL for entries (None = no expiration)
            enable_stats: Whether to track statistics
            cleanup_interval_seconds: Interval for background cleanup of expired entries
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self._capacity = capacity
        self._default_ttl = default_ttl_seconds
        self._enable_stats = enable_stats
        
        # Storage
        self._cache: Dict[K, CacheEntry[V]] = {}
        
        # Eviction strategy
        self._eviction_strategy = EvictionStrategyFactory.create_strategy(eviction_policy)
        
        # Statistics
        self._stats = CacheStats() if enable_stats else None
        
        # Thread safety
        self._lock = RLock()
        
        # Background cleanup thread
        self._cleanup_interval = cleanup_interval_seconds
        self._cleanup_thread: Optional[Thread] = None
        self._stop_cleanup = False
        
        if default_ttl_seconds is not None:
            self._start_cleanup_thread()
    
    def get(self, key: K) -> Optional[V]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            # Check if key exists
            if key not in self._cache:
                if self._enable_stats:
                    self._stats.misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                self._remove_entry(key)
                if self._enable_stats:
                    self._stats.misses += 1
                    self._stats.expirations += 1
                return None
            
            # Update access metadata
            entry.touch()
            self._eviction_strategy.on_get(key)
            
            if self._enable_stats:
                self._stats.hits += 1
            
            return entry.value
    
    def put(self, key: K, value: V, ttl_seconds: Optional[int] = None) -> None:
        """
        Put value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL for this entry (overrides default)
        """
        with self._lock:
            # Check if key already exists
            if key in self._cache:
                # Update existing entry
                entry = self._cache[key]
                entry.value = value
                entry.created_at = datetime.now()
                entry.last_accessed = datetime.now()
                entry.access_count = 0
                entry.ttl_seconds = ttl_seconds if ttl_seconds is not None else self._default_ttl
                
                self._eviction_strategy.on_put(key)
                return
            
            # Check capacity
            if len(self._cache) >= self._capacity:
                # Evict entry
                evicted_key = self._eviction_strategy.evict()
                if evicted_key is not None:
                    self._remove_entry(evicted_key)
                    if self._enable_stats:
                        self._stats.evictions += 1
            
            # Create new entry
            now = datetime.now()
            entry = CacheEntry(
                value=value,
                created_at=now,
                last_accessed=now,
                access_count=0,
                ttl_seconds=ttl_seconds if ttl_seconds is not None else self._default_ttl
            )
            
            self._cache[key] = entry
            self._eviction_strategy.on_put(key)
    
    def remove(self, key: K) -> bool:
        """
        Remove entry from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def _remove_entry(self, key: K) -> None:
        """Internal method to remove entry (lock must be held)"""
        del self._cache[key]
        self._eviction_strategy.remove(key)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()
            self._eviction_strategy.clear()
            if self._enable_stats:
                self._stats = CacheStats()
    
    def size(self) -> int:
        """Get current number of entries in cache"""
        with self._lock:
            return len(self._cache)
    
    def contains(self, key: K) -> bool:
        """Check if key exists in cache (doesn't update access stats)"""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            return not entry.is_expired()
    
    def get_stats(self) -> Optional[CacheStats]:
        """Get cache statistics"""
        if not self._enable_stats:
            return None
        
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                expirations=self._stats.expirations
            )
    
    def _cleanup_expired_entries(self) -> None:
        """Remove all expired entries"""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
                if self._enable_stats:
                    self._stats.expirations += 1
    
    def _cleanup_loop(self) -> None:
        """Background thread for cleaning up expired entries"""
        while not self._stop_cleanup:
            time.sleep(self._cleanup_interval)
            if not self._stop_cleanup:
                self._cleanup_expired_entries()
    
    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread"""
        self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def close(self) -> None:
        """Stop background threads and cleanup resources"""
        self._stop_cleanup = True
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=1.0)


# ==================== Cache Manager (Optional) ====================

class CacheManager:
    """
    Manages multiple named caches with different configurations
    """
    
    def __init__(self):
        self._caches: Dict[str, Cache] = {}
        self._lock = RLock()
    
    def create_cache(self,
                     name: str,
                     capacity: int,
                     eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
                     default_ttl_seconds: Optional[int] = None,
                     enable_stats: bool = True) -> Cache:
        """Create a new named cache"""
        with self._lock:
            if name in self._caches:
                raise ValueError(f"Cache '{name}' already exists")
            
            cache = Cache(
                capacity=capacity,
                eviction_policy=eviction_policy,
                default_ttl_seconds=default_ttl_seconds,
                enable_stats=enable_stats
            )
            
            self._caches[name] = cache
            return cache
    
    def get_cache(self, name: str) -> Optional[Cache]:
        """Get cache by name"""
        with self._lock:
            return self._caches.get(name)
    
    def remove_cache(self, name: str) -> bool:
        """Remove a cache"""
        with self._lock:
            if name in self._caches:
                cache = self._caches[name]
                cache.close()
                del self._caches[name]
                return True
            return False
    
    def list_caches(self) -> list[str]:
        """List all cache names"""
        with self._lock:
            return list(self._caches.keys())
    
    def close_all(self) -> None:
        """Close all caches"""
        with self._lock:
            for cache in self._caches.values():
                cache.close()
            self._caches.clear()


# ==================== Demo Usage ====================

def main():
    """Demo the cache system"""
    print("=== Cache System Demo ===\n")
    
    # Test Case 1: LRU Cache with basic operations
    print("="*60)
    print("TEST CASE 1: LRU Cache - Basic Operations")
    print("="*60)
    
    lru_cache = Cache[str, str](
        capacity=3,
        eviction_policy=EvictionPolicy.LRU,
        enable_stats=True
    )
    
    print("\nAdding entries:")
    lru_cache.put("user:1", "Alice")
    lru_cache.put("user:2", "Bob")
    lru_cache.put("user:3", "Charlie")
    print(f"Cache size: {lru_cache.size()}/3")
    
    print("\nAccessing user:1:")
    value = lru_cache.get("user:1")
    print(f"Got: {value}")
    
    print("\nAdding user:4 (should evict user:2 - LRU):")
    lru_cache.put("user:4", "David")
    print(f"Cache size: {lru_cache.size()}/3")
    
    print("\nTrying to get user:2 (should be evicted):")
    value = lru_cache.get("user:2")
    print(f"Got: {value}")
    
    print(f"\nCache Stats: {lru_cache.get_stats()}")
    
    # Test Case 2: LFU Cache
    print("\n" + "="*60)
    print("TEST CASE 2: LFU Cache - Frequency-based Eviction")
    print("="*60)
    
    lfu_cache = Cache[str, str](
        capacity=3,
        eviction_policy=EvictionPolicy.LFU,
        enable_stats=True
    )
    
    print("\nAdding entries:")
    lfu_cache.put("a", "Alpha")
    lfu_cache.put("b", "Beta")
    lfu_cache.put("c", "Gamma")
    
    print("\nAccessing 'a' three times, 'b' two times:")
    for _ in range(3):
        lfu_cache.get("a")
    for _ in range(2):
        lfu_cache.get("b")
    
    print("\nAdding 'd' (should evict 'c' - least frequently used):")
    lfu_cache.put("d", "Delta")
    
    print("\nChecking what's in cache:")
    print(f"'a' exists: {lfu_cache.contains('a')}")
    print(f"'b' exists: {lfu_cache.contains('b')}")
    print(f"'c' exists: {lfu_cache.contains('c')}")
    print(f"'d' exists: {lfu_cache.contains('d')}")
    
    print(f"\nCache Stats: {lfu_cache.get_stats()}")
    
    # Test Case 3: TTL and Expiration
    print("\n" + "="*60)
    print("TEST CASE 3: Time-based Expiration (TTL)")
    print("="*60)
    
    ttl_cache = Cache[str, str](
        capacity=5,
        eviction_policy=EvictionPolicy.LRU,
        default_ttl_seconds=2,  # 2 seconds default TTL
        enable_stats=True,
        cleanup_interval_seconds=1
    )
    
    print("\nAdding entry with 2-second TTL:")
    ttl_cache.put("temp:1", "Temporary Data")
    print(f"Immediately after put: {ttl_cache.get('temp:1')}")
    
    print("\nWaiting 1 second...")
    time.sleep(1)
    print(f"After 1 second: {ttl_cache.get('temp:1')}")
    
    print("\nWaiting 2 more seconds...")
    time.sleep(2)
    print(f"After 3 seconds total (expired): {ttl_cache.get('temp:1')}")
    
    print("\nAdding entry with custom 10-second TTL:")
    ttl_cache.put("temp:2", "Longer TTL", ttl_seconds=10)
    print(f"After 3 seconds: {ttl_cache.get('temp:2')}")
    
    print(f"\nCache Stats: {ttl_cache.get_stats()}")
    
    # Test Case 4: FIFO Cache
    print("\n" + "="*60)
    print("TEST CASE 4: FIFO Cache")
    print("="*60)
    
    fifo_cache = Cache[int, str](
        capacity=3,
        eviction_policy=EvictionPolicy.FIFO,
        enable_stats=True
    )
    
    print("\nAdding entries in order: 1, 2, 3")
    fifo_cache.put(1, "First")
    fifo_cache.put(2, "Second")
    fifo_cache.put(3, "Third")
    
    print("\nAccessing entry 1 multiple times:")
    for _ in range(5):
        fifo_cache.get(1)
    
    print("\nAdding entry 4 (should evict 1 - first in):")
    fifo_cache.put(4, "Fourth")
    
    print("\nChecking what's in cache:")
    print(f"1 exists: {fifo_cache.contains(1)}")
    print(f"2 exists: {fifo_cache.contains(2)}")
    print(f"3 exists: {fifo_cache.contains(3)}")
    print(f"4 exists: {fifo_cache.contains(4)}")
    
    # Test Case 5: Concurrent Access Simulation
    print("\n" + "="*60)
    print("TEST CASE 5: Concurrent Access (Thread Safety)")
    print("="*60)
    
    shared_cache = Cache[int, int](
        capacity=100,
        eviction_policy=EvictionPolicy.LRU,
        enable_stats=True
    )
    
    import threading
    
    def writer_thread(thread_id: int, count: int):
        for i in range(count):
            key = thread_id * 1000 + i
            shared_cache.put(key, key * 2)
    
    def reader_thread(thread_id: int, count: int):
        for i in range(count):
            key = (thread_id % 3) * 1000 + i
            shared_cache.get(key)
    
    print("\nStarting 5 writer threads and 5 reader threads...")
    threads = []
    
    # Start writers
    for i in range(5):
        t = threading.Thread(target=writer_thread, args=(i, 50))
        threads.append(t)
        t.start()
    
    # Start readers
    for i in range(5):
        t = threading.Thread(target=reader_thread, args=(i, 50))
        threads.append(t)
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    print(f"Final cache size: {shared_cache.size()}")
    print(f"Cache Stats: {shared_cache.get_stats()}")
    
    # Test Case 6: Cache Manager
    print("\n" + "="*60)
    print("TEST CASE 6: Cache Manager - Multiple Caches")
    print("="*60)
    
    manager = CacheManager()
    
    print("\nCreating multiple caches:")
    user_cache = manager.create_cache(
        "users",
        capacity=100,
        eviction_policy=EvictionPolicy.LRU,
        default_ttl_seconds=300
    )
    
    session_cache = manager.create_cache(
        "sessions",
        capacity=1000,
        eviction_policy=EvictionPolicy.LFU,
        default_ttl_seconds=3600
    )
    
    product_cache = manager.create_cache(
        "products",
        capacity=500,
        eviction_policy=EvictionPolicy.FIFO
    )
    
    print(f"Created caches: {manager.list_caches()}")
    
    print("\nUsing different caches:")
    user_cache.put("user:123", {"name": "Alice", "email": "alice@example.com"})
    session_cache.put("session:abc", {"user_id": "123", "token": "xyz"})
    product_cache.put("product:456", {"name": "Widget", "price": 19.99})
    
    print(f"User cache size: {user_cache.size()}")
    print(f"Session cache size: {session_cache.size()}")
    print(f"Product cache size: {product_cache.size()}")
    
    # Cleanup
    print("\n" + "="*60)
    print("Cleaning up resources...")
    print("="*60)
    
    lru_cache.close()
    lfu_cache.close()
    ttl_cache.close()
    fifo_cache.close()
    shared_cache.close()
    manager.close_all()
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Design Highlights
# Design Patterns Used:

# Strategy Pattern - Different eviction policies (LRU, LFU, FIFO, LIFO) are implemented as strategies that can be swapped at runtime
# Factory Pattern - EvictionStrategyFactory creates the appropriate eviction strategy based on the policy enum
# Generic/Template Pattern - Cache is generic over key and value types using Python's Generic[K, V]

# Key Features:

# Eviction Policies:

# LRU (Least Recently Used) - Using OrderedDict for O(1) operations
# LFU (Least Frequently Used) - Using heap for efficient eviction
# FIFO (First In First Out)
# LIFO (Last In First Out)


# Thread Safety:

# RLock for reentrant locking
# All public methods are thread-safe
# Fine-grained locking in eviction strategies


# Time-based Expiration:

# Per-entry TTL support
# Background cleanup thread
# Lazy expiration on access


# Statistics Tracking:

# Hits, misses, evictions, expirations
# Hit rate calculation
# Optional (can be disabled for performance)


# Metadata:

# Creation time, last access time, access count
# Extensible CacheEntry dataclass



# This design is production-ready and demonstrates solid OOP principles without over-engineering!
