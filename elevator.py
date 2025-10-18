from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Set, Dict
from dataclasses import dataclass
from threading import Lock, Thread
import time


# ==================== Enums ====================

class Direction(Enum):
    """Elevator movement direction"""
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"


class ElevatorState(Enum):
    """Elevator operational state"""
    IDLE = "IDLE"
    MOVING = "MOVING"
    STOPPED = "STOPPED"
    MAINTENANCE = "MAINTENANCE"


class RequestType(Enum):
    """Type of elevator request"""
    HALL_CALL = "HALL_CALL"      # Request from floor (up/down button)
    CAR_CALL = "CAR_CALL"         # Request from inside elevator


# ==================== Core Models ====================

@dataclass
class Request:
    """Represents an elevator request"""
    floor: int
    direction: Optional[Direction]  # None for car calls
    request_type: RequestType
    timestamp: float
    
    def __repr__(self) -> str:
        dir_str = f", {self.direction.value}" if self.direction else ""
        return f"Request(Floor {self.floor}{dir_str}, {self.request_type.value})"


class Elevator:
    """Represents a single elevator"""
    
    def __init__(self, elevator_id: int, min_floor: int, max_floor: int):
        self._id = elevator_id
        self._min_floor = min_floor
        self._max_floor = max_floor
        self._current_floor = 1
        self._direction = Direction.IDLE
        self._state = ElevatorState.IDLE
        self._target_floors: Set[int] = set()  # Floors this elevator needs to visit
        self._lock = Lock()  # Thread safety
        
    def get_id(self) -> int:
        return self._id
    
    def get_current_floor(self) -> int:
        with self._lock:
            return self._current_floor
    
    def get_direction(self) -> Direction:
        with self._lock:
            return self._direction
    
    def get_state(self) -> ElevatorState:
        with self._lock:
            return self._state
    
    def add_target_floor(self, floor: int) -> bool:
        """Add a target floor for this elevator"""
        if not self._min_floor <= floor <= self._max_floor:
            return False
        
        with self._lock:
            self._target_floors.add(floor)
        return True
    
    def get_target_floors(self) -> Set[int]:
        with self._lock:
            return self._target_floors.copy()
    
    def remove_target_floor(self, floor: int) -> None:
        with self._lock:
            self._target_floors.discard(floor)
    
    def has_target_floors(self) -> bool:
        with self._lock:
            return len(self._target_floors) > 0
    
    def move_to_next_floor(self) -> None:
        """Move elevator one floor in current direction"""
        with self._lock:
            if self._direction == Direction.UP:
                if self._current_floor < self._max_floor:
                    self._current_floor += 1
                    self._state = ElevatorState.MOVING
            elif self._direction == Direction.DOWN:
                if self._current_floor > self._min_floor:
                    self._current_floor -= 1
                    self._state = ElevatorState.MOVING
    
    def stop_at_floor(self) -> None:
        """Stop elevator at current floor"""
        with self._lock:
            self._state = ElevatorState.STOPPED
    
    def set_direction(self, direction: Direction) -> None:
        with self._lock:
            self._direction = direction
    
    def set_state(self, state: ElevatorState) -> None:
        with self._lock:
            self._state = state
    
    def set_idle(self) -> None:
        with self._lock:
            self._direction = Direction.IDLE
            self._state = ElevatorState.IDLE
    
    def is_moving_towards(self, floor: int) -> bool:
        """Check if elevator is moving towards the given floor"""
        with self._lock:
            if self._direction == Direction.UP:
                return floor > self._current_floor
            elif self._direction == Direction.DOWN:
                return floor < self._current_floor
            return False
    
    def __repr__(self) -> str:
        return (f"Elevator {self._id}: Floor {self._current_floor}, "
                f"{self._direction.value}, {self._state.value}")


class Floor:
    """Represents a building floor"""
    
    def __init__(self, floor_number: int):
        self._floor_number = floor_number
        self._up_button_pressed = False
        self._down_button_pressed = False
        self._lock = Lock()
    
    def get_floor_number(self) -> int:
        return self._floor_number
    
    def press_up_button(self) -> None:
        with self._lock:
            self._up_button_pressed = True
    
    def press_down_button(self) -> None:
        with self._lock:
            self._down_button_pressed = True
    
    def clear_up_button(self) -> None:
        with self._lock:
            self._up_button_pressed = False
    
    def clear_down_button(self) -> None:
        with self._lock:
            self._down_button_pressed = False
    
    def is_up_button_pressed(self) -> bool:
        with self._lock:
            return self._up_button_pressed
    
    def is_down_button_pressed(self) -> bool:
        with self._lock:
            return self._down_button_pressed


# ==================== Strategy Pattern: Scheduling Algorithms ====================

class SchedulingStrategy(ABC):
    """Abstract strategy for elevator scheduling"""
    
    @abstractmethod
    def select_elevator(self, elevators: List[Elevator], request: Request) -> Optional[Elevator]:
        """Select the best elevator for the given request"""
        pass
    
    @abstractmethod
    def get_next_floor(self, elevator: Elevator) -> Optional[int]:
        """Determine the next floor for the elevator to visit"""
        pass


class FCFSSchedulingStrategy(SchedulingStrategy):
    """First-Come-First-Serve scheduling"""
    
    def select_elevator(self, elevators: List[Elevator], request: Request) -> Optional[Elevator]:
        """Select nearest idle elevator, or any idle elevator"""
        idle_elevators = [e for e in elevators if e.get_state() == ElevatorState.IDLE]
        
        if idle_elevators:
            # Select nearest idle elevator
            return min(idle_elevators, 
                      key=lambda e: abs(e.get_current_floor() - request.floor))
        
        # If no idle elevators, select the one with fewest targets
        return min(elevators, key=lambda e: len(e.get_target_floors()))
    
    def get_next_floor(self, elevator: Elevator) -> Optional[int]:
        """Simply go to the nearest target floor"""
        target_floors = elevator.get_target_floors()
        if not target_floors:
            return None
        
        current_floor = elevator.get_current_floor()
        return min(target_floors, key=lambda f: abs(f - current_floor))


class LOOKSchedulingStrategy(SchedulingStrategy):
    """LOOK scheduling algorithm (like SCAN but reverses at last request, not end)"""
    
    def select_elevator(self, elevators: List[Elevator], request: Request) -> Optional[Elevator]:
        """Select elevator based on direction and proximity"""
        best_elevator = None
        best_score = float('inf')
        
        for elevator in elevators:
            score = self._calculate_score(elevator, request)
            if score < best_score:
                best_score = score
                best_elevator = elevator
        
        return best_elevator
    
    def _calculate_score(self, elevator: Elevator, request: Request) -> float:
        """Calculate a score for how suitable this elevator is for the request"""
        current_floor = elevator.get_current_floor()
        direction = elevator.get_direction()
        request_floor = request.floor
        
        # If elevator is idle, score is just distance
        if direction == Direction.IDLE:
            return abs(current_floor - request_floor)
        
        # If elevator is moving in same direction as request
        if request.direction and direction == request.direction:
            if direction == Direction.UP and request_floor >= current_floor:
                return request_floor - current_floor  # Small score if on the way
            elif direction == Direction.DOWN and request_floor <= current_floor:
                return current_floor - request_floor
        
        # Otherwise, elevator needs to finish current direction first
        target_floors = elevator.get_target_floors()
        if not target_floors:
            return abs(current_floor - request_floor)
        
        if direction == Direction.UP:
            max_target = max(target_floors)
            return (max_target - current_floor) + (max_target - request_floor)
        else:
            min_target = min(target_floors)
            return (current_floor - min_target) + (request_floor - min_target)
    
    def get_next_floor(self, elevator: Elevator) -> Optional[int]:
        """
        LOOK algorithm: Continue in current direction until no more requests,
        then reverse direction
        """
        target_floors = elevator.get_target_floors()
        if not target_floors:
            return None
        
        current_floor = elevator.get_current_floor()
        direction = elevator.get_direction()
        
        # Get floors in current direction
        if direction == Direction.UP or direction == Direction.IDLE:
            floors_ahead = [f for f in target_floors if f > current_floor]
            if floors_ahead:
                return min(floors_ahead)  # Next floor going up
            
            # No floors ahead, reverse direction
            floors_behind = [f for f in target_floors if f < current_floor]
            if floors_behind:
                return max(floors_behind)  # Next floor going down
        
        elif direction == Direction.DOWN:
            floors_ahead = [f for f in target_floors if f < current_floor]
            if floors_ahead:
                return max(floors_ahead)  # Next floor going down
            
            # No floors ahead, reverse direction
            floors_behind = [f for f in target_floors if f > current_floor]
            if floors_behind:
                return min(floors_behind)  # Next floor going up
        
        return None


class SCANSchedulingStrategy(SchedulingStrategy):
    """
    SCAN scheduling algorithm (Elevator algorithm)
    Goes all the way to top/bottom before reversing
    """
    
    def select_elevator(self, elevators: List[Elevator], request: Request) -> Optional[Elevator]:
        """Select elevator similar to LOOK"""
        best_elevator = None
        best_score = float('inf')
        
        for elevator in elevators:
            score = self._calculate_score(elevator, request)
            if score < best_score:
                best_score = score
                best_elevator = elevator
        
        return best_elevator
    
    def _calculate_score(self, elevator: Elevator, request: Request) -> float:
        """Calculate score - similar to LOOK"""
        current_floor = elevator.get_current_floor()
        direction = elevator.get_direction()
        request_floor = request.floor
        
        if direction == Direction.IDLE:
            return abs(current_floor - request_floor)
        
        if request.direction and direction == request.direction:
            if direction == Direction.UP and request_floor >= current_floor:
                return request_floor - current_floor
            elif direction == Direction.DOWN and request_floor <= current_floor:
                return current_floor - request_floor
        
        # Penalize if elevator needs to go to end first
        if direction == Direction.UP:
            return (elevator._max_floor - current_floor) + abs(elevator._max_floor - request_floor)
        else:
            return (current_floor - elevator._min_floor) + abs(request_floor - elevator._min_floor)
    
    def get_next_floor(self, elevator: Elevator) -> Optional[int]:
        """
        SCAN algorithm: Continue to the end (top/bottom) before reversing
        """
        target_floors = elevator.get_target_floors()
        if not target_floors:
            return None
        
        current_floor = elevator.get_current_floor()
        direction = elevator.get_direction()
        
        if direction == Direction.UP or direction == Direction.IDLE:
            floors_ahead = [f for f in target_floors if f > current_floor]
            if floors_ahead:
                return min(floors_ahead)
            
            # Reached top, go down
            floors_behind = [f for f in target_floors if f < current_floor]
            if floors_behind:
                return max(floors_behind)
        
        elif direction == Direction.DOWN:
            floors_ahead = [f for f in target_floors if f < current_floor]
            if floors_ahead:
                return max(floors_ahead)
            
            # Reached bottom, go up
            floors_behind = [f for f in target_floors if f > current_floor]
            if floors_behind:
                return min(floors_behind)
        
        return None


# ==================== Elevator Controller ====================

class ElevatorController:
    """Controls a single elevator's movement"""
    
    def __init__(self, elevator: Elevator, scheduling_strategy: SchedulingStrategy):
        self._elevator = elevator
        self._scheduling_strategy = scheduling_strategy
        self._running = False
        self._lock = Lock()
    
    def start(self) -> None:
        """Start the elevator controller"""
        with self._lock:
            if self._running:
                return
            self._running = True
        
        # Run controller in separate thread
        controller_thread = Thread(target=self._run, daemon=True)
        controller_thread.start()
    
    def stop(self) -> None:
        """Stop the elevator controller"""
        with self._lock:
            self._running = False
    
    def _run(self) -> None:
        """Main controller loop"""
        while True:
            with self._lock:
                if not self._running:
                    break
            
            self._process_next_move()
            time.sleep(1)  # Simulate time to move one floor
    
    def _process_next_move(self) -> None:
        """Process the next move for this elevator"""
        if not self._elevator.has_target_floors():
            self._elevator.set_idle()
            return
        
        # Get next floor to visit
        next_floor = self._scheduling_strategy.get_next_floor(self._elevator)
        
        if next_floor is None:
            self._elevator.set_idle()
            return
        
        current_floor = self._elevator.get_current_floor()
        
        # Determine direction
        if next_floor > current_floor:
            self._elevator.set_direction(Direction.UP)
        elif next_floor < current_floor:
            self._elevator.set_direction(Direction.DOWN)
        else:
            # Already at target floor
            self._elevator.stop_at_floor()
            self._elevator.remove_target_floor(current_floor)
            print(f"[Elevator {self._elevator.get_id()}] Stopped at floor {current_floor}")
            time.sleep(2)  # Door open time
            return
        
        # Move towards next floor
        self._elevator.move_to_next_floor()
        current_floor = self._elevator.get_current_floor()
        
        # Check if we've arrived at a target floor
        if current_floor in self._elevator.get_target_floors():
            self._elevator.stop_at_floor()
            self._elevator.remove_target_floor(current_floor)
            print(f"[Elevator {self._elevator.get_id()}] Stopped at floor {current_floor}")
            time.sleep(2)  # Door open time


# ==================== Elevator System ====================

class ElevatorSystem:
    """Main elevator system managing multiple elevators"""
    
    def __init__(self, num_elevators: int, num_floors: int, 
                 scheduling_strategy: SchedulingStrategy):
        self._num_floors = num_floors
        self._elevators: List[Elevator] = []
        self._controllers: List[ElevatorController] = []
        self._floors: Dict[int, Floor] = {}
        self._scheduling_strategy = scheduling_strategy
        self._request_queue: List[Request] = []
        self._lock = Lock()
        
        # Create floors
        for i in range(1, num_floors + 1):
            self._floors[i] = Floor(i)
        
        # Create elevators and controllers
        for i in range(num_elevators):
            elevator = Elevator(i + 1, 1, num_floors)
            controller = ElevatorController(elevator, scheduling_strategy)
            self._elevators.append(elevator)
            self._controllers.append(controller)
    
    def start(self) -> None:
        """Start all elevator controllers"""
        print(f"Starting elevator system with {len(self._elevators)} elevators...")
        for controller in self._controllers:
            controller.start()
    
    def stop(self) -> None:
        """Stop all elevator controllers"""
        for controller in self._controllers:
            controller.stop()
    
    def request_elevator(self, floor: int, direction: Direction) -> None:
        """Request elevator from a floor (hall call)"""
        if not 1 <= floor <= self._num_floors:
            print(f"Invalid floor: {floor}")
            return
        
        # Press button on floor
        floor_obj = self._floors[floor]
        if direction == Direction.UP:
            floor_obj.press_up_button()
        else:
            floor_obj.press_down_button()
        
        request = Request(
            floor=floor,
            direction=direction,
            request_type=RequestType.HALL_CALL,
            timestamp=time.time()
        )
        
        self._handle_request(request)
        print(f"[System] Hall call: Floor {floor}, {direction.value}")
    
    def request_floor(self, elevator_id: int, target_floor: int) -> None:
        """Request a floor from inside elevator (car call)"""
        if not 1 <= target_floor <= self._num_floors:
            print(f"Invalid floor: {target_floor}")
            return
        
        if not 1 <= elevator_id <= len(self._elevators):
            print(f"Invalid elevator ID: {elevator_id}")
            return
        
        elevator = self._elevators[elevator_id - 1]
        elevator.add_target_floor(target_floor)
        
        print(f"[System] Car call: Elevator {elevator_id} -> Floor {target_floor}")
    
    def _handle_request(self, request: Request) -> None:
        """Handle an elevator request"""
        # Select best elevator for this request
        elevator = self._scheduling_strategy.select_elevator(self._elevators, request)
        
        if elevator:
            elevator.add_target_floor(request.floor)
            print(f"[System] Assigned Elevator {elevator.get_id()} to request")
        else:
            print(f"[System] No available elevator for request")
    
    def display_status(self) -> None:
        """Display current status of all elevators"""
        print("\n" + "="*60)
        print("ELEVATOR SYSTEM STATUS")
        print("="*60)
        for elevator in self._elevators:
            targets = sorted(elevator.get_target_floors())
            targets_str = f"Targets: {targets}" if targets else "No targets"
            print(f"{elevator} | {targets_str}")
        print("="*60 + "\n")
    
    def get_elevators(self) -> List[Elevator]:
        return self._elevators


# ==================== Factory Pattern ====================

class ElevatorSystemFactory:
    """Factory for creating elevator system configurations"""
    
    @staticmethod
    def create_fcfs_system(num_elevators: int = 3, num_floors: int = 10) -> ElevatorSystem:
        """Create system with FCFS scheduling"""
        strategy = FCFSSchedulingStrategy()
        return ElevatorSystem(num_elevators, num_floors, strategy)
    
    @staticmethod
    def create_look_system(num_elevators: int = 3, num_floors: int = 10) -> ElevatorSystem:
        """Create system with LOOK scheduling"""
        strategy = LOOKSchedulingStrategy()
        return ElevatorSystem(num_elevators, num_floors, strategy)
    
    @staticmethod
    def create_scan_system(num_elevators: int = 3, num_floors: int = 10) -> ElevatorSystem:
        """Create system with SCAN scheduling"""
        strategy = SCANSchedulingStrategy()
        return ElevatorSystem(num_elevators, num_floors, strategy)


# ==================== Demo Usage ====================

def main():
    """Demo the elevator system"""
    print("=== Elevator System Demo ===\n")
    
    # Create elevator system with LOOK scheduling
    system = ElevatorSystemFactory.create_look_system(num_elevators=3, num_floors=10)
    
    # Start the system
    system.start()
    
    # Display initial status
    time.sleep(1)
    system.display_status()
    
    # Simulate requests
    print("Simulating elevator requests...\n")
    
    # Hall calls (from floors)
    system.request_elevator(5, Direction.UP)
    time.sleep(1)
    
    system.request_elevator(3, Direction.DOWN)
    time.sleep(1)
    
    system.request_elevator(7, Direction.UP)
    time.sleep(2)
    
    system.display_status()
    
    # Car calls (from inside elevators)
    system.request_floor(1, 8)  # Elevator 1 to floor 8
    system.request_floor(2, 1)  # Elevator 2 to floor 1
    
    time.sleep(3)
    system.display_status()
    
    # More requests
    system.request_elevator(9, Direction.DOWN)
    system.request_elevator(2, Direction.UP)
    
    time.sleep(5)
    system.display_status()
    
    # Let system run for a bit
    print("\nLetting system process requests...")
    time.sleep(15)
    
    system.display_status()
    
    # Stop the system
    print("\nStopping elevator system...")
    system.stop()


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Strategy Pattern - Scheduling algorithms:

# FCFS: Assigns nearest idle elevator, simple first-come-first-serve
# LOOK: Continues in direction until no more requests, then reverses
# SCAN: Goes all the way to top/bottom before reversing (classic elevator algorithm)


# Controller Pattern:

# ElevatorController manages individual elevator movement
# Runs in separate thread for each elevator
# Decouples movement logic from elevator state


# Factory Pattern:

# Creates systems with different scheduling strategies
# Easy to configure and test different algorithms



# Concurrency Handling:

# Thread Locks (Lock):

# Every shared state access is protected
# Elevator uses locks for current floor, direction, targets
# Floor uses locks for button states
# ElevatorSystem uses locks for request queue


# Thread-per-Controller:

# Each elevator runs in its own thread
# Allows concurrent elevator movement
# Controllers coordinate through shared ElevatorSystem


# Atomic Operations:

# All state reads/writes are atomic with lock protection
# Prevents race conditions when multiple elevators access same data



# Scheduling Algorithms:
# FCFS (First-Come-First-Serve):

# Simplest algorithm
# Assigns nearest idle elevator
# No optimization for direction or efficiency
# Good for low traffic

# LOOK:

# Services requests in one direction until no more
# Reverses at last request (not at end of shaft)
# More efficient than FCFS
# Best for medium traffic

# SCAN:

# Goes all the way to top/bottom before reversing
# Classic "elevator algorithm" from disk scheduling
# Very predictable behavior
# Good for heavy traffic

# Core Components:
# ✅ Multiple Elevators: Independent operation, coordinated by system
# ✅ Request Types: Hall calls (from floors) vs Car calls (from inside)
# ✅ Direction Management: UP, DOWN, IDLE states
# ✅ Thread Safety: All shared state protected by locks
# ✅ Real-time Processing: Controllers run continuously in background
# ✅ Pluggable Scheduling: Easy to add new algorithms
# Extensions You Could Add:

# Priority requests (VIP floors, emergency)
# Load balancing based on elevator capacity
# Energy optimization (minimize total travel)
# Predictive algorithms using ML
# Express elevators (skip certain floors)
# Destination dispatch (select floor before entering)

# This design demonstrates strong concurrency handling, multiple scheduling strategies, and clean separation of concerns - perfect for FAANG interviews!
