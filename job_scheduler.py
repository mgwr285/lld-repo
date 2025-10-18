from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import Thread, RLock, Event, Condition
import time
import uuid
import heapq
from dataclasses import dataclass
import traceback


# ==================== Enums ====================

class JobStatus(Enum):
    """Job execution status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ScheduleType(Enum):
    """Type of job schedule"""
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"


class RetryStrategy(Enum):
    """Retry strategies"""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


# ==================== Core Models ====================

class JobResult:
    """Result of job execution"""
    
    def __init__(self, success: bool, result: Any = None, error: Optional[str] = None):
        self._success = success
        self._result = result
        self._error = error
        self._timestamp = datetime.now()
    
    def is_success(self) -> bool:
        return self._success
    
    def get_result(self) -> Any:
        return self._result
    
    def get_error(self) -> Optional[str]:
        return self._error
    
    def get_timestamp(self) -> datetime:
        return self._timestamp


class Job(ABC):
    """Abstract base class for all jobs"""
    
    def __init__(self, job_id: str, name: str, priority: JobPriority = JobPriority.MEDIUM):
        self._job_id = job_id
        self._name = name
        self._priority = priority
        self._status = JobStatus.PENDING
        
        # Execution tracking
        self._created_at = datetime.now()
        self._scheduled_at: Optional[datetime] = None
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        
        # Retry configuration
        self._max_retries = 3
        self._retry_count = 0
        self._retry_strategy = RetryStrategy.EXPONENTIAL_BACKOFF
        self._retry_delay = 60  # seconds
        
        # Dependencies
        self._dependencies: Set[str] = set()  # Job IDs this job depends on
        self._dependents: Set[str] = set()  # Job IDs that depend on this job
        
        # Results and errors
        self._result: Optional[JobResult] = None
        self._execution_history: List[JobResult] = []
        
        # Callbacks
        self._on_success: Optional[Callable[[JobResult], None]] = None
        self._on_failure: Optional[Callable[[JobResult], None]] = None
        self._on_complete: Optional[Callable[[JobResult], None]] = None
        
        # Metadata
        self._metadata: Dict[str, Any] = {}
        
        # Thread safety
        self._lock = RLock()
    
    @abstractmethod
    def execute(self) -> JobResult:
        """Execute the job - must be implemented by subclasses"""
        pass
    
    def get_id(self) -> str:
        return self._job_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_priority(self) -> JobPriority:
        return self._priority
    
    def set_priority(self, priority: JobPriority) -> None:
        self._priority = priority
    
    def get_status(self) -> JobStatus:
        return self._status
    
    def set_status(self, status: JobStatus) -> None:
        with self._lock:
            self._status = status
            
            if status == JobStatus.SCHEDULED:
                self._scheduled_at = datetime.now()
            elif status == JobStatus.RUNNING:
                self._started_at = datetime.now()
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                self._completed_at = datetime.now()
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def get_scheduled_at(self) -> Optional[datetime]:
        return self._scheduled_at
    
    def get_started_at(self) -> Optional[datetime]:
        return self._started_at
    
    def get_completed_at(self) -> Optional[datetime]:
        return self._completed_at
    
    def get_execution_time(self) -> Optional[float]:
        """Get execution time in seconds"""
        if self._started_at and self._completed_at:
            return (self._completed_at - self._started_at).total_seconds()
        return None
    
    def add_dependency(self, job_id: str) -> None:
        """Add job dependency"""
        self._dependencies.add(job_id)
    
    def get_dependencies(self) -> Set[str]:
        return self._dependencies.copy()
    
    def add_dependent(self, job_id: str) -> None:
        """Add job that depends on this job"""
        self._dependents.add(job_id)
    
    def get_dependents(self) -> Set[str]:
        return self._dependents.copy()
    
    def set_max_retries(self, max_retries: int) -> None:
        self._max_retries = max_retries
    
    def get_max_retries(self) -> int:
        return self._max_retries
    
    def increment_retry_count(self) -> None:
        with self._lock:
            self._retry_count += 1
    
    def get_retry_count(self) -> int:
        return self._retry_count
    
    def can_retry(self) -> bool:
        return self._retry_count < self._max_retries
    
    def set_retry_strategy(self, strategy: RetryStrategy, delay: int = 60) -> None:
        self._retry_strategy = strategy
        self._retry_delay = delay
    
    def get_retry_delay(self) -> int:
        """Calculate retry delay based on strategy"""
        if self._retry_strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self._retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            return self._retry_delay * (2 ** self._retry_count)
        elif self._retry_strategy == RetryStrategy.LINEAR_BACKOFF:
            return self._retry_delay * (self._retry_count + 1)
        else:  # FIXED_DELAY
            return self._retry_delay
    
    def set_result(self, result: JobResult) -> None:
        with self._lock:
            self._result = result
            self._execution_history.append(result)
            
            # Trigger callbacks
            if result.is_success() and self._on_success:
                self._on_success(result)
            elif not result.is_success() and self._on_failure:
                self._on_failure(result)
            
            if self._on_complete:
                self._on_complete(result)
    
    def get_result(self) -> Optional[JobResult]:
        return self._result
    
    def get_execution_history(self) -> List[JobResult]:
        return self._execution_history.copy()
    
    def on_success(self, callback: Callable[[JobResult], None]) -> None:
        """Register success callback"""
        self._on_success = callback
    
    def on_failure(self, callback: Callable[[JobResult], None]) -> None:
        """Register failure callback"""
        self._on_failure = callback
    
    def on_complete(self, callback: Callable[[JobResult], None]) -> None:
        """Register completion callback (success or failure)"""
        self._on_complete = callback
    
    def set_metadata(self, key: str, value: Any) -> None:
        self._metadata[key] = value
    
    def get_metadata(self, key: str) -> Optional[Any]:
        return self._metadata.get(key)
    
    def __lt__(self, other: 'Job') -> bool:
        """For priority queue comparison"""
        if self._priority.value != other._priority.value:
            return self._priority.value > other._priority.value  # Higher priority first
        return self._created_at < other._created_at  # Earlier jobs first
    
    def to_dict(self) -> Dict:
        """Convert job to dictionary"""
        return {
            'job_id': self._job_id,
            'name': self._name,
            'status': self._status.value,
            'priority': self._priority.value,
            'created_at': self._created_at.isoformat(),
            'scheduled_at': self._scheduled_at.isoformat() if self._scheduled_at else None,
            'started_at': self._started_at.isoformat() if self._started_at else None,
            'completed_at': self._completed_at.isoformat() if self._completed_at else None,
            'retry_count': self._retry_count,
            'max_retries': self._max_retries,
            'dependencies': list(self._dependencies),
            'execution_time': self.get_execution_time()
        }


class FunctionJob(Job):
    """Job that executes a function"""
    
    def __init__(self, job_id: str, name: str, func: Callable[..., Any],
                 args: tuple = (), kwargs: dict = None,
                 priority: JobPriority = JobPriority.MEDIUM):
        super().__init__(job_id, name, priority)
        self._func = func
        self._args = args
        self._kwargs = kwargs or {}
    
    def execute(self) -> JobResult:
        """Execute the function"""
        try:
            result = self._func(*self._args, **self._kwargs)
            return JobResult(success=True, result=result)
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return JobResult(success=False, error=error_msg)


class Schedule:
    """Scheduling configuration for jobs"""
    
    def __init__(self, schedule_type: ScheduleType):
        self._schedule_type = schedule_type
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        
        # For recurring jobs
        self._interval: Optional[timedelta] = None
        
        # For cron-like jobs (simplified)
        self._cron_expression: Optional[str] = None
    
    def get_type(self) -> ScheduleType:
        return self._schedule_type
    
    def set_start_time(self, start_time: datetime) -> None:
        self._start_time = start_time
    
    def get_start_time(self) -> Optional[datetime]:
        return self._start_time
    
    def set_end_time(self, end_time: datetime) -> None:
        self._end_time = end_time
    
    def set_interval(self, interval: timedelta) -> None:
        """Set interval for recurring jobs"""
        self._interval = interval
    
    def get_interval(self) -> Optional[timedelta]:
        return self._interval
    
    def get_next_run_time(self, current_time: datetime) -> Optional[datetime]:
        """Calculate next run time"""
        if self._schedule_type == ScheduleType.ONE_TIME:
            if self._start_time and current_time < self._start_time:
                return self._start_time
            return None
        
        elif self._schedule_type == ScheduleType.RECURRING:
            if not self._start_time or not self._interval:
                return None
            
            if current_time < self._start_time:
                return self._start_time
            
            # Calculate next occurrence
            elapsed = current_time - self._start_time
            intervals = int(elapsed / self._interval) + 1
            next_time = self._start_time + (self._interval * intervals)
            
            if self._end_time and next_time > self._end_time:
                return None
            
            return next_time
        
        return None


class ScheduledJob:
    """Wrapper for scheduled jobs"""
    
    def __init__(self, job: Job, schedule: Schedule):
        self._job = job
        self._schedule = schedule
        self._next_run_time: Optional[datetime] = None
        self._last_run_time: Optional[datetime] = None
        self._run_count = 0
        
        # Calculate initial next run time
        self._update_next_run_time()
    
    def get_job(self) -> Job:
        return self._job
    
    def get_schedule(self) -> Schedule:
        return self._schedule
    
    def get_next_run_time(self) -> Optional[datetime]:
        return self._next_run_time
    
    def _update_next_run_time(self) -> None:
        """Update next run time"""
        current_time = datetime.now()
        self._next_run_time = self._schedule.get_next_run_time(current_time)
    
    def mark_executed(self) -> None:
        """Mark job as executed"""
        self._last_run_time = datetime.now()
        self._run_count += 1
        self._update_next_run_time()
    
    def should_run(self) -> bool:
        """Check if job should run now"""
        if not self._next_run_time:
            return False
        return datetime.now() >= self._next_run_time
    
    def __lt__(self, other: 'ScheduledJob') -> bool:
        """For priority queue comparison"""
        if self._next_run_time is None:
            return False
        if other._next_run_time is None:
            return True
        return self._next_run_time < other._next_run_time


# ==================== Worker ====================

class Worker(Thread):
    """Worker thread that executes jobs"""
    
    def __init__(self, worker_id: str, scheduler: 'JobScheduler'):
        super().__init__(daemon=True)
        self._worker_id = worker_id
        self._scheduler = scheduler
        self._running = True
        self._current_job: Optional[Job] = None
        self._jobs_executed = 0
    
    def get_id(self) -> str:
        return self._worker_id
    
    def get_current_job(self) -> Optional[Job]:
        return self._current_job
    
    def get_jobs_executed(self) -> int:
        return self._jobs_executed
    
    def stop(self) -> None:
        """Stop the worker"""
        self._running = False
    
    def run(self) -> None:
        """Main worker loop"""
        print(f"👷 Worker {self._worker_id} started")
        
        while self._running:
            try:
                # Get next job from scheduler
                job = self._scheduler._get_next_job_for_worker()
                
                if job:
                    self._execute_job(job)
                else:
                    # No job available, sleep briefly
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"❌ Worker {self._worker_id} error: {e}")
                time.sleep(1)
        
        print(f"👷 Worker {self._worker_id} stopped")
    
    def _execute_job(self, job: Job) -> None:
        """Execute a job"""
        self._current_job = job
        job.set_status(JobStatus.RUNNING)
        
        print(f"▶️  Worker {self._worker_id} executing: {job.get_name()} ({job.get_id()})")
        
        try:
            # Execute the job
            result = job.execute()
            
            # Set result
            job.set_result(result)
            
            if result.is_success():
                job.set_status(JobStatus.COMPLETED)
                print(f"✅ Job completed: {job.get_name()}")
                
                # Notify scheduler to process dependents
                self._scheduler._on_job_completed(job)
            else:
                # Handle failure
                if job.can_retry():
                    job.increment_retry_count()
                    job.set_status(JobStatus.RETRY)
                    
                    # Re-schedule with delay
                    retry_delay = job.get_retry_delay()
                    print(f"🔄 Job failed, retrying in {retry_delay}s: {job.get_name()} "
                          f"(attempt {job.get_retry_count() + 1}/{job.get_max_retries() + 1})")
                    
                    self._scheduler._schedule_retry(job, retry_delay)
                else:
                    job.set_status(JobStatus.FAILED)
                    print(f"❌ Job failed: {job.get_name()} - {result.get_error()}")
                    
                    # Notify scheduler
                    self._scheduler._on_job_failed(job)
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            result = JobResult(success=False, error=error_msg)
            job.set_result(result)
            job.set_status(JobStatus.FAILED)
            print(f"❌ Job execution error: {job.get_name()} - {error_msg}")
            
            self._scheduler._on_job_failed(job)
        
        finally:
            self._current_job = None
            self._jobs_executed += 1


# ==================== Job Scheduler ====================

class JobScheduler:
    """
    Main job scheduler that manages job execution
    Features:
    - Priority-based execution
    - Dependency management
    - Retry mechanism
    - One-time and recurring jobs
    - Worker pool
    - Concurrent execution
    """
    
    def __init__(self, num_workers: int = 4):
        # Job storage
        self._jobs: Dict[str, Job] = {}
        self._scheduled_jobs: Dict[str, ScheduledJob] = {}
        
        # Execution queue (priority queue)
        self._job_queue: List[Job] = []
        self._queue_lock = RLock()
        self._queue_condition = Condition(self._queue_lock)
        
        # Scheduled jobs queue (heap based on next run time)
        self._scheduled_queue: List[ScheduledJob] = []
        self._scheduled_lock = RLock()
        
        # Workers
        self._workers: List[Worker] = []
        self._num_workers = num_workers
        
        # Dependency tracking
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self._total_jobs_submitted = 0
        self._total_jobs_completed = 0
        self._total_jobs_failed = 0
        
        # Scheduler state
        self._running = False
        self._scheduler_thread: Optional[Thread] = None
        
        # Global lock
        self._lock = RLock()
    
    def start(self) -> None:
        """Start the scheduler and workers"""
        if self._running:
            return
        
        self._running = True
        
        # Start workers
        for i in range(self._num_workers):
            worker = Worker(f"W{i+1}", self)
            worker.start()
            self._workers.append(worker)
        
        # Start scheduler thread for recurring jobs
        self._scheduler_thread = Thread(target=self._schedule_loop, daemon=True)
        self._scheduler_thread.start()
        
        print(f"🚀 Job Scheduler started with {self._num_workers} workers")
    
    def stop(self) -> None:
        """Stop the scheduler and workers"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop workers
        for worker in self._workers:
            worker.stop()
        
        # Wake up all waiting workers
        with self._queue_condition:
            self._queue_condition.notify_all()
        
        # Wait for workers to finish
        for worker in self._workers:
            worker.join(timeout=5)
        
        print("🛑 Job Scheduler stopped")
    
    def submit_job(self, job: Job) -> str:
        """Submit a job for execution"""
        with self._lock:
            self._jobs[job.get_id()] = job
            self._total_jobs_submitted += 1
            
            # Check if dependencies are satisfied
            if self._are_dependencies_satisfied(job):
                self._enqueue_job(job)
            else:
                job.set_status(JobStatus.PENDING)
                print(f"⏸️  Job pending (waiting for dependencies): {job.get_name()}")
            
            return job.get_id()
    
    def schedule_job(self, job: Job, schedule: Schedule) -> str:
        """Schedule a job with a schedule"""
        with self._lock:
            self._jobs[job.get_id()] = job
            
            scheduled_job = ScheduledJob(job, schedule)
            self._scheduled_jobs[job.get_id()] = scheduled_job
            
            with self._scheduled_lock:
                heapq.heappush(self._scheduled_queue, scheduled_job)
            
            print(f"📅 Job scheduled: {job.get_name()} - "
                  f"Next run: {scheduled_job.get_next_run_time()}")
            
            return job.get_id()
    
    def submit_function(self, func: Callable, name: str,
                       args: tuple = (), kwargs: dict = None,
                       priority: JobPriority = JobPriority.MEDIUM) -> str:
        """Submit a function as a job"""
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, name, func, args, kwargs, priority)
        return self.submit_job(job)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False
            
            if job.get_status() == JobStatus.RUNNING:
                print(f"⚠️  Cannot cancel running job: {job.get_name()}")
                return False
            
            job.set_status(JobStatus.CANCELLED)
            
            # Remove from queue if present
            with self._queue_lock:
                self._job_queue = [j for j in self._job_queue if j.get_id() != job_id]
                heapq.heapify(self._job_queue)
            
            print(f"🚫 Job cancelled: {job.get_name()}")
            return True
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self._jobs.get(job_id)
    
    def add_dependency(self, job_id: str, depends_on_job_id: str) -> bool:
        """Add dependency between jobs"""
        with self._lock:
            job = self._jobs.get(job_id)
            depends_on_job = self._jobs.get(depends_on_job_id)
            
            if not job or not depends_on_job:
                return False
            
            # Check for circular dependency
            if self._would_create_cycle(job_id, depends_on_job_id):
                print(f"⚠️  Cannot add dependency - would create cycle")
                return False
            
            job.add_dependency(depends_on_job_id)
            depends_on_job.add_dependent(job_id)
            
            self._dependency_graph[job_id].add(depends_on_job_id)
            self._reverse_dependency_graph[depends_on_job_id].add(job_id)
            
            return True
    
    def _would_create_cycle(self, from_job: str, to_job: str) -> bool:
        """Check if adding dependency would create a cycle"""
        visited = set()
        
        def dfs(node: str) -> bool:
            if node == from_job:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            for dep in self._dependency_graph.get(node, []):
                if dfs(dep):
                    return True
            return False
        
        return dfs(to_job)
    
    def _are_dependencies_satisfied(self, job: Job) -> bool:
        """Check if all dependencies are completed"""
        for dep_id in job.get_dependencies():
            dep_job = self._jobs.get(dep_id)
            if not dep_job or dep_job.get_status() != JobStatus.COMPLETED:
                return False
        return True
    
    def _enqueue_job(self, job: Job) -> None:
        """Add job to execution queue"""
        with self._queue_condition:
            heapq.heappush(self._job_queue, job)
            job.set_status(JobStatus.SCHEDULED)
            self._queue_condition.notify()
            print(f"📥 Job queued: {job.get_name()} (priority: {job.get_priority().name})")
    
    def _get_next_job_for_worker(self) -> Optional[Job]:
        """Get next job for worker to execute"""
        with self._queue_condition:
            while self._running and len(self._job_queue) == 0:
                self._queue_condition.wait(timeout=1)
            
            if not self._running or len(self._job_queue) == 0:
                return None
            
            job = heapq.heappop(self._job_queue)
            return job
    
    def _schedule_retry(self, job: Job, delay: int) -> None:
        """Schedule job for retry after delay"""
        def retry_job():
            time.sleep(delay)
            with self._lock:
                if job.get_status() == JobStatus.RETRY:
                    self._enqueue_job(job)
        
        thread = Thread(target=retry_job, daemon=True)
        thread.start()
    
    def _on_job_completed(self, job: Job) -> None:
        """Handle job completion"""
        with self._lock:
            self._total_jobs_completed += 1
            
            # Check if any dependent jobs can now be executed
            for dependent_id in job.get_dependents():
                dependent_job = self._jobs.get(dependent_id)
                if dependent_job and self._are_dependencies_satisfied(dependent_job):
                    self._enqueue_job(dependent_job)
    
    def _on_job_failed(self, job: Job) -> None:
        """Handle job failure"""
        with self._lock:
            self._total_jobs_failed += 1
            
            # Cancel dependent jobs
            for dependent_id in job.get_dependents():
                dependent_job = self._jobs.get(dependent_id)
                if dependent_job:
                    dependent_job.set_status(JobStatus.CANCELLED)
                    print(f"🚫 Dependent job cancelled: {dependent_job.get_name()}")
    
    def _schedule_loop(self) -> None:
        """Background loop for scheduled jobs"""
        while self._running:
            try:
                with self._scheduled_lock:
                    now = datetime.now()
                    
                    # Check if any scheduled jobs should run
                    while self._scheduled_queue and self._scheduled_queue[0].should_run():
                        scheduled_job = heapq.heappop(self._scheduled_queue)
                        
                        job = scheduled_job.get_job()
                        
                        # Create new instance for recurring jobs
                        if scheduled_job.get_schedule().get_type() == ScheduleType.RECURRING:
                            # Clone the job for this execution
                            new_job_id = str(uuid.uuid4())
                            new_job = FunctionJob(
                                new_job_id,
                                f"{job.get_name()} (run {scheduled_job._run_count + 1})",
                                job._func if isinstance(job, FunctionJob) else None,
                                job._args if isinstance(job, FunctionJob) else (),
                                job._kwargs if isinstance(job, FunctionJob) else {},
                                job.get_priority()
                            )
                            self.submit_job(new_job)
                            
                            # Mark as executed and re-add to queue if has next run
                            scheduled_job.mark_executed()
                            if scheduled_job.get_next_run_time():
                                heapq.heappush(self._scheduled_queue, scheduled_job)
                        else:
                            # One-time job
                            self.submit_job(job)
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"❌ Scheduler loop error: {e}")
                time.sleep(1)
    
    def get_statistics(self) -> Dict:
        """Get scheduler statistics"""
        running_jobs = sum(1 for j in self._jobs.values() if j.get_status() == JobStatus.RUNNING)
        pending_jobs = sum(1 for j in self._jobs.values() if j.get_status() == JobStatus.PENDING)
        scheduled_jobs = sum(1 for j in self._jobs.values() if j.get_status() == JobStatus.SCHEDULED)
        
        return {
            'total_submitted': self._total_jobs_submitted,
            'total_completed': self._total_jobs_completed,
            'total_failed': self._total_jobs_failed,
            'running': running_jobs,
            'pending': pending_jobs,
            'scheduled': scheduled_jobs,
            'queue_size': len(self._job_queue),
            'workers': len(self._workers),
            'worker_stats': [
                {
                    'id': w.get_id(),
                    'jobs_executed': w.get_jobs_executed(),
                    'current_job': w.get_current_job().get_name() if w.get_current_job() else None
                }
                for w in self._workers
            ]
        }
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all jobs to complete"""
        start_time = time.time()
        
        while True:
            with self._lock:
                active_jobs = sum(1 for j in self._jobs.values() 
                                if j.get_status() in [JobStatus.PENDING, JobStatus.SCHEDULED, 
                                                     JobStatus.RUNNING, JobStatus.RETRY])
                
                if active_jobs == 0:
                    return True
            
            if timeout and (time.time() - start_time) > timeout:
                return False
            
            time.sleep(0.5)


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_job_scheduler():
    """Comprehensive demo of the job scheduler"""
    
    print_section("JOB SCHEDULER DEMO")
    
    scheduler = JobScheduler(num_workers=3)
    scheduler.start()
    
    try:
        # ==================== Simple Function Jobs ====================
        print_section("1. Submit Simple Function Jobs")
        
        def process_data(data_id: int, sleep_time: float = 1.0):
            """Simulate data processing"""
            print(f"   Processing data {data_id}...")
            time.sleep(sleep_time)
            return f"Data {data_id} processed"
        
        # Submit multiple jobs
        job_ids = []
        for i in range(5):
            job_id = scheduler.submit_function(
                process_data,
                f"Process Data {i}",
                args=(i,),
                kwargs={'sleep_time': 0.5},
                priority=JobPriority.MEDIUM
            )
            job_ids.append(job_id)
        
        time.sleep(3)
        
        # ==================== Priority Jobs ====================
        print_section("2. Priority-based Execution")
        
        def urgent_task(task_id: int):
            print(f"   URGENT: Executing task {task_id}")
            time.sleep(0.3)
            return f"Urgent task {task_id} done"
        
        # Submit low priority jobs
        for i in range(3):
            scheduler.submit_function(
                process_data,
                f"Low Priority Task {i}",
                args=(i,),
                kwargs={'sleep_time': 1.0},
                priority=JobPriority.LOW
            )
        
        # Submit high priority jobs (should execute first)
        for i in range(2):
            scheduler.submit_function(
                urgent_task,
                f"High Priority Task {i}",
                args=(i,),
                priority=JobPriority.CRITICAL
            )
        
        time.sleep(3)
        
        # ==================== Job with Callbacks ====================
        print_section("3. Jobs with Callbacks")
        
        def compute_sum(a: int, b: int):
            result = a + b
            print(f"   Computing {a} + {b} = {result}")
            return result
        
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, "Sum Computation", compute_sum, args=(10, 20))
        
        # Add callbacks
        job.on_success(lambda result: print(f"   ✅ Success callback: Result = {result.get_result()}"))
        job.on_failure(lambda result: print(f"   ❌ Failure callback: {result.get_error()}"))
        job.on_complete(lambda result: print(f"   🏁 Complete callback executed"))
        
        scheduler.submit_job(job)
        time.sleep(2)
        
        # ==================== Job Dependencies ====================
        print_section("4. Job Dependencies")
        
        def step1():
            print("   Step 1: Fetching data...")
            time.sleep(0.5)
            return "data_fetched"
        
        def step2(data):
            print(f"   Step 2: Processing {data}...")
            time.sleep(0.5)
            return "data_processed"
        
        def step3(data):
            print(f"   Step 3: Storing {data}...")
            time.sleep(0.5)
            return "data_stored"
        
        # Create jobs
        job1_id = str(uuid.uuid4())
        job1 = FunctionJob(job1_id, "Fetch Data", step1)
        
        job2_id = str(uuid.uuid4())
        job2 = FunctionJob(job2_id, "Process Data", step2, args=("data",))
        
        job3_id = str(uuid.uuid4())
        job3 = FunctionJob(job3_id, "Store Data", step3, args=("processed_data",))
        
        # Set up dependencies: job1 -> job2 -> job3
        scheduler.submit_job(job1)
        scheduler.submit_job(job2)
        scheduler.submit_job(job3)
        
        scheduler.add_dependency(job2_id, job1_id)  # job2 depends on job1
        scheduler.add_dependency(job3_id, job2_id)  # job3 depends on job2
        
        time.sleep(3)
        
        # ==================== Retry Mechanism ====================
        print_section("5. Retry Mechanism")
        
        attempt_count = {'count': 0}
        
        def failing_task():
            attempt_count['count'] += 1
            print(f"   Attempt {attempt_count['count']}")
            
            if attempt_count['count'] < 3:
                raise Exception("Simulated failure")
            
            return "Success after retries"
        
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, "Failing Task", failing_task)
        job.set_max_retries(3)
        job.set_retry_strategy(RetryStrategy.FIXED_DELAY, delay=1)
        
        scheduler.submit_job(job)
        time.sleep(5)
        
        # ==================== Scheduled Jobs ====================
        print_section("6. Scheduled Jobs (One-time)")
        
        def scheduled_task():
            print(f"   Scheduled task executed at {datetime.now().strftime('%H:%M:%S')}")
            return "Scheduled task completed"
        
        # Schedule job to run 3 seconds from now
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, "Future Task", scheduled_task)
        
        schedule = Schedule(ScheduleType.ONE_TIME)
        schedule.set_start_time(datetime.now() + timedelta(seconds=3))
        
        scheduler.schedule_job(job, schedule)
        
        print(f"   Waiting for scheduled job...")
        time.sleep(5)
        
        # ==================== Recurring Jobs ====================
        print_section("7. Recurring Jobs")
        
        def recurring_task():
            print(f"   Recurring task executed at {datetime.now().strftime('%H:%M:%S')}")
            return "Recurring execution"
        
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, "Recurring Task", recurring_task)
        
        schedule = Schedule(ScheduleType.RECURRING)
        schedule.set_start_time(datetime.now() + timedelta(seconds=1))
        schedule.set_interval(timedelta(seconds=2))
        schedule.set_end_time(datetime.now() + timedelta(seconds=10))
        
        scheduler.schedule_job(job, schedule)
        
        print(f"   Recurring job will run every 2 seconds for 10 seconds...")
        time.sleep(12)
        
        # ==================== Complex Dependency Graph ====================
        print_section("8. Complex Dependency Graph")
        
        def task(name: str):
            print(f"   Executing: {name}")
            time.sleep(0.3)
            return f"{name} completed"
        
        # Create a complex DAG
        #     A
        #    / \
        #   B   C
        #    \ /
        #     D
        
        job_a = FunctionJob(str(uuid.uuid4()), "Task A", task, args=("A",))
        job_b = FunctionJob(str(uuid.uuid4()), "Task B", task, args=("B",))
        job_c = FunctionJob(str(uuid.uuid4()), "Task C", task, args=("C",))
        job_d = FunctionJob(str(uuid.uuid4()), "Task D", task, args=("D",))
        
        scheduler.submit_job(job_a)
        scheduler.submit_job(job_b)
        scheduler.submit_job(job_c)
        scheduler.submit_job(job_d)
        
        scheduler.add_dependency(job_b.get_id(), job_a.get_id())
        scheduler.add_dependency(job_c.get_id(), job_a.get_id())
        scheduler.add_dependency(job_d.get_id(), job_b.get_id())
        scheduler.add_dependency(job_d.get_id(), job_c.get_id())
        
        time.sleep(3)
        
        # ==================== Job Cancellation ====================
        print_section("9. Job Cancellation")
        
        def long_running_task():
            print("   Starting long task...")
            time.sleep(5)
            return "Long task completed"
        
        job_id = str(uuid.uuid4())
        job = FunctionJob(job_id, "Long Running Task", long_running_task)
        job.set_priority(JobPriority.LOW)
        
        scheduler.submit_job(job)
        time.sleep(0.5)
        
        # Cancel the job
        success = scheduler.cancel_job(job_id)
        print(f"   Cancellation {'successful' if success else 'failed'}")
        
        # ==================== Statistics ====================
        print_section("10. Scheduler Statistics")
        
        stats = scheduler.get_statistics()
        print(f"\n📊 Scheduler Statistics:")
        print(f"   Total Jobs Submitted: {stats['total_submitted']}")
        print(f"   Total Jobs Completed: {stats['total_completed']}")
        print(f"   Total Jobs Failed: {stats['total_failed']}")
        print(f"   Currently Running: {stats['running']}")
        print(f"   Pending: {stats['pending']}")
        print(f"   Scheduled: {stats['scheduled']}")
        print(f"   Queue Size: {stats['queue_size']}")
        print(f"\n   Worker Statistics:")
        for worker_stat in stats['worker_stats']:
            current = worker_stat['current_job'] or "Idle"
            print(f"      {worker_stat['id']}: {worker_stat['jobs_executed']} jobs, Current: {current}")
        
        # ==================== Wait for Completion ====================
        print_section("11. Wait for All Jobs")
        
        # Submit a few more jobs
        for i in range(3):
            scheduler.submit_function(
                process_data,
                f"Final Task {i}",
                args=(i,),
                kwargs={'sleep_time': 0.5}
            )
        
        print("   Waiting for all jobs to complete...")
        success = scheduler.wait_for_completion(timeout=10)
        
        if success:
            print("   ✅ All jobs completed!")
        else:
            print("   ⏱️  Timeout waiting for jobs")
        
        # Final statistics
        final_stats = scheduler.get_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Total Completed: {final_stats['total_completed']}")
        print(f"   Total Failed: {final_stats['total_failed']}")
        print(f"   Success Rate: {final_stats['total_completed'] / max(final_stats['total_submitted'], 1) * 100:.1f}%")
        
    finally:
        print_section("Shutdown")
        scheduler.stop()
        print("\n✅ Job Scheduler demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_job_scheduler()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

# Job Scheduler System - Low Level Design
# Here's a comprehensive job scheduler system design:

# Key Design Decisions:
# 1. Core Components:
# Job: Abstract base class for all jobs
# FunctionJob: Execute Python functions as jobs
# Schedule: Define when jobs should run
# ScheduledJob: Wrapper for scheduled jobs
# Worker: Thread that executes jobs
# JobScheduler: Main orchestrator
# 2. Key Features:
# ✅ Priority-based execution (Critical > High > Medium > Low) ✅ Job dependencies (DAG-based with cycle detection) ✅ Retry mechanism (Exponential/Linear/Fixed backoff) ✅ One-time scheduled jobs ✅ Recurring jobs with intervals ✅ Callbacks (on_success, on_failure, on_complete) ✅ Worker pool (configurable size) ✅ Thread-safe concurrent execution ✅ Job cancellation ✅ Statistics and monitoring

# 3. Retry Strategies:
# Immediate: Retry without delay
# Exponential Backoff: delay × 2^retry_count
# Linear Backoff: delay × (retry_count + 1)
# Fixed Delay: Constant delay
# 4. Job Lifecycle:
# 5. Dependency Management:
# DAG-based dependencies
# Cycle detection
# Automatic execution when dependencies satisfied
# Cascade cancellation on failure
# 6. Design Patterns:
# Worker Pool Pattern: Fixed number of worker threads
# Producer-Consumer: Scheduler produces, workers consume
# Priority Queue: Jobs ordered by priority and creation time
# Observer Pattern: Callbacks for job events
# Template Method: Abstract Job class with execute()
# 7. Concurrency:
# Thread-safe job queue with locks
# Condition variables for worker coordination
# Heap-based priority queue
# Separate scheduler thread for recurring jobs
# This is a production-grade job scheduler like Celery or Quartz! 🔄⚙️
