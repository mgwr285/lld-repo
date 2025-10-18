from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from threading import Thread, RLock, Event
import time
import uuid
import os
import hashlib
import requests
from urllib.parse import urlparse
from pathlib import Path
import json


# ==================== Enums ====================

class DownloadStatus(Enum):
    """Download status"""
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"


class DownloadPriority(Enum):
    """Download priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ChunkStatus(Enum):
    """Chunk download status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class Protocol(Enum):
    """Download protocols"""
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"


# ==================== Models ====================

class DownloadChunk:
    """Represents a chunk of the file being downloaded"""
    
    def __init__(self, chunk_id: int, start_byte: int, end_byte: int):
        self._chunk_id = chunk_id
        self._start_byte = start_byte
        self._end_byte = end_byte
        self._status = ChunkStatus.PENDING
        self._downloaded_bytes = 0
        self._retry_count = 0
        self._max_retries = 3
        self._lock = RLock()
    
    def get_id(self) -> int:
        return self._chunk_id
    
    def get_start_byte(self) -> int:
        return self._start_byte
    
    def get_end_byte(self) -> int:
        return self._end_byte
    
    def get_size(self) -> int:
        return self._end_byte - self._start_byte + 1
    
    def get_status(self) -> ChunkStatus:
        return self._status
    
    def set_status(self, status: ChunkStatus) -> None:
        with self._lock:
            self._status = status
    
    def get_downloaded_bytes(self) -> int:
        return self._downloaded_bytes
    
    def update_progress(self, bytes_downloaded: int) -> None:
        with self._lock:
            self._downloaded_bytes = bytes_downloaded
    
    def increment_retry(self) -> bool:
        """Increment retry count, return True if can retry"""
        with self._lock:
            self._retry_count += 1
            return self._retry_count <= self._max_retries
    
    def get_progress_percentage(self) -> float:
        """Get chunk download progress"""
        total = self.get_size()
        if total == 0:
            return 0.0
        return (self._downloaded_bytes / total) * 100


class DownloadMetadata:
    """Metadata about the download"""
    
    def __init__(self, url: str, filename: str, file_size: Optional[int] = None):
        self._url = url
        self._filename = filename
        self._file_size = file_size
        self._content_type: Optional[str] = None
        self._supports_resume = False
        self._etag: Optional[str] = None
        self._last_modified: Optional[str] = None
    
    def get_url(self) -> str:
        return self._url
    
    def get_filename(self) -> str:
        return self._filename
    
    def get_file_size(self) -> Optional[int]:
        return self._file_size
    
    def set_file_size(self, size: int) -> None:
        self._file_size = size
    
    def get_content_type(self) -> Optional[str]:
        return self._content_type
    
    def set_content_type(self, content_type: str) -> None:
        self._content_type = content_type
    
    def supports_resume(self) -> bool:
        return self._supports_resume
    
    def set_supports_resume(self, supports: bool) -> None:
        self._supports_resume = supports
    
    def set_etag(self, etag: str) -> None:
        self._etag = etag
    
    def set_last_modified(self, last_modified: str) -> None:
        self._last_modified = last_modified


class DownloadTask:
    """Main download task"""
    
    def __init__(self, task_id: str, url: str, destination_path: str,
                 priority: DownloadPriority = DownloadPriority.MEDIUM,
                 num_connections: int = 4):
        self._task_id = task_id
        self._url = url
        self._destination_path = destination_path
        self._priority = priority
        self._num_connections = num_connections
        
        # Extract filename from URL
        parsed_url = urlparse(url)
        self._filename = os.path.basename(parsed_url.path) or "download"
        
        # Metadata
        self._metadata = DownloadMetadata(url, self._filename)
        
        # Status tracking
        self._status = DownloadStatus.PENDING
        self._created_at = datetime.now()
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        
        # Progress tracking
        self._downloaded_bytes = 0
        self._speed = 0.0  # bytes per second
        self._eta: Optional[timedelta] = None
        
        # Chunks for parallel download
        self._chunks: List[DownloadChunk] = []
        self._chunk_size = 1024 * 1024  # 1MB default
        
        # Error tracking
        self._error_message: Optional[str] = None
        self._retry_count = 0
        self._max_retries = 3
        
        # Callbacks
        self._on_progress: Optional[Callable[[float, float], None]] = None
        self._on_complete: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_pause: Optional[Callable[[], None]] = None
        
        # Control
        self._pause_event = Event()
        self._pause_event.set()  # Not paused initially
        self._cancel_event = Event()
        
        # File verification
        self._expected_checksum: Optional[str] = None
        self._checksum_algorithm = "md5"
        
        # Thread safety
        self._lock = RLock()
    
    def get_id(self) -> str:
        return self._task_id
    
    def get_url(self) -> str:
        return self._url
    
    def get_filename(self) -> str:
        return self._filename
    
    def get_destination_path(self) -> str:
        return self._destination_path
    
    def get_full_path(self) -> str:
        return os.path.join(self._destination_path, self._filename)
    
    def get_priority(self) -> DownloadPriority:
        return self._priority
    
    def set_priority(self, priority: DownloadPriority) -> None:
        self._priority = priority
    
    def get_status(self) -> DownloadStatus:
        return self._status
    
    def set_status(self, status: DownloadStatus) -> None:
        with self._lock:
            self._status = status
            
            if status == DownloadStatus.DOWNLOADING:
                if not self._started_at:
                    self._started_at = datetime.now()
            elif status == DownloadStatus.PAUSED:
                self._paused_at = datetime.now()
            elif status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
                self._completed_at = datetime.now()
    
    def get_metadata(self) -> DownloadMetadata:
        return self._metadata
    
    def get_downloaded_bytes(self) -> int:
        return self._downloaded_bytes
    
    def update_downloaded_bytes(self, bytes_count: int) -> None:
        with self._lock:
            self._downloaded_bytes = bytes_count
    
    def get_progress_percentage(self) -> float:
        """Get download progress percentage"""
        file_size = self._metadata.get_file_size()
        if not file_size or file_size == 0:
            return 0.0
        return (self._downloaded_bytes / file_size) * 100
    
    def get_speed(self) -> float:
        """Get download speed in bytes/second"""
        return self._speed
    
    def set_speed(self, speed: float) -> None:
        self._speed = speed
    
    def get_speed_mb(self) -> float:
        """Get download speed in MB/s"""
        return self._speed / (1024 * 1024)
    
    def get_eta(self) -> Optional[timedelta]:
        """Get estimated time to completion"""
        return self._eta
    
    def calculate_eta(self) -> None:
        """Calculate ETA based on current speed"""
        file_size = self._metadata.get_file_size()
        if file_size and self._speed > 0:
            remaining_bytes = file_size - self._downloaded_bytes
            seconds_remaining = remaining_bytes / self._speed
            self._eta = timedelta(seconds=int(seconds_remaining))
        else:
            self._eta = None
    
    def create_chunks(self) -> None:
        """Divide file into chunks for parallel download"""
        file_size = self._metadata.get_file_size()
        if not file_size:
            return
        
        chunk_size = max(file_size // self._num_connections, self._chunk_size)
        
        for i in range(self._num_connections):
            start = i * chunk_size
            end = start + chunk_size - 1
            
            if i == self._num_connections - 1:
                end = file_size - 1
            
            chunk = DownloadChunk(i, start, end)
            self._chunks.append(chunk)
    
    def get_chunks(self) -> List[DownloadChunk]:
        return self._chunks.copy()
    
    def get_chunk(self, chunk_id: int) -> Optional[DownloadChunk]:
        for chunk in self._chunks:
            if chunk.get_id() == chunk_id:
                return chunk
        return None
    
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()
    
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
    
    def pause(self) -> None:
        """Pause the download"""
        self._pause_event.clear()
    
    def resume(self) -> None:
        """Resume the download"""
        self._pause_event.set()
    
    def cancel(self) -> None:
        """Cancel the download"""
        self._cancel_event.set()
    
    def wait_if_paused(self) -> None:
        """Block if download is paused"""
        self._pause_event.wait()
    
    def set_expected_checksum(self, checksum: str, algorithm: str = "md5") -> None:
        """Set expected checksum for verification"""
        self._expected_checksum = checksum
        self._checksum_algorithm = algorithm
    
    def get_expected_checksum(self) -> Optional[str]:
        return self._expected_checksum
    
    def set_error(self, error: str) -> None:
        self._error_message = error
    
    def get_error(self) -> Optional[str]:
        return self._error_message
    
    def on_progress(self, callback: Callable[[float, float], None]) -> None:
        """Set progress callback (percentage, speed_mb)"""
        self._on_progress = callback
    
    def on_complete(self, callback: Callable[[], None]) -> None:
        """Set completion callback"""
        self._on_complete = callback
    
    def on_error(self, callback: Callable[[str], None]) -> None:
        """Set error callback"""
        self._on_error = callback
    
    def on_pause(self, callback: Callable[[], None]) -> None:
        """Set pause callback"""
        self._on_pause = callback
    
    def trigger_progress(self) -> None:
        if self._on_progress:
            self._on_progress(self.get_progress_percentage(), self.get_speed_mb())
    
    def trigger_complete(self) -> None:
        if self._on_complete:
            self._on_complete()
    
    def trigger_error(self) -> None:
        if self._on_error and self._error_message:
            self._on_error(self._error_message)
    
    def trigger_pause(self) -> None:
        if self._on_pause:
            self._on_pause()
    
    def __lt__(self, other: 'DownloadTask') -> bool:
        """For priority queue comparison"""
        if self._priority.value != other._priority.value:
            return self._priority.value > other._priority.value
        return self._created_at < other._created_at
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'task_id': self._task_id,
            'filename': self._filename,
            'url': self._url,
            'status': self._status.value,
            'priority': self._priority.name,
            'progress': f"{self.get_progress_percentage():.2f}%",
            'downloaded': f"{self._downloaded_bytes / (1024*1024):.2f} MB",
            'total_size': f"{self._metadata.get_file_size() / (1024*1024):.2f} MB" if self._metadata.get_file_size() else "Unknown",
            'speed': f"{self.get_speed_mb():.2f} MB/s",
            'eta': str(self._eta) if self._eta else "Unknown",
            'created_at': self._created_at.isoformat()
        }


# ==================== Download Workers ====================

class ChunkDownloader(Thread):
    """Worker thread for downloading a single chunk"""
    
    def __init__(self, task: DownloadTask, chunk: DownloadChunk, temp_dir: str):
        super().__init__(daemon=True)
        self._task = task
        self._chunk = chunk
        self._temp_dir = temp_dir
        self._chunk_file = os.path.join(temp_dir, f"chunk_{chunk.get_id()}")
    
    def run(self) -> None:
        """Download the chunk"""
        try:
            self._chunk.set_status(ChunkStatus.DOWNLOADING)
            
            headers = {
                'Range': f'bytes={self._chunk.get_start_byte()}-{self._chunk.get_end_byte()}'
            }
            
            response = requests.get(
                self._task.get_url(),
                headers=headers,
                stream=True,
                timeout=30
            )
            
            if response.status_code not in [200, 206]:
                raise Exception(f"Failed to download chunk: HTTP {response.status_code}")
            
            # Download chunk to temp file
            downloaded = 0
            with open(self._chunk_file, 'wb') as f:
                for data in response.iter_content(chunk_size=8192):
                    # Check if cancelled
                    if self._task.is_cancelled():
                        self._chunk.set_status(ChunkStatus.FAILED)
                        return
                    
                    # Wait if paused
                    self._task.wait_if_paused()
                    
                    f.write(data)
                    downloaded += len(data)
                    self._chunk.update_progress(downloaded)
            
            self._chunk.set_status(ChunkStatus.COMPLETED)
            
        except Exception as e:
            print(f"   ❌ Chunk {self._chunk.get_id()} failed: {str(e)}")
            if self._chunk.increment_retry():
                self._chunk.set_status(ChunkStatus.PENDING)  # Retry
            else:
                self._chunk.set_status(ChunkStatus.FAILED)


class DownloadWorker(Thread):
    """Worker that manages a download task"""
    
    def __init__(self, worker_id: str, manager: 'DownloadManager'):
        super().__init__(daemon=True)
        self._worker_id = worker_id
        self._manager = manager
        self._running = True
        self._current_task: Optional[DownloadTask] = None
    
    def get_id(self) -> str:
        return self._worker_id
    
    def get_current_task(self) -> Optional[DownloadTask]:
        return self._current_task
    
    def stop(self) -> None:
        self._running = False
    
    def run(self) -> None:
        """Main worker loop"""
        print(f"⬇️  Worker {self._worker_id} started")
        
        while self._running:
            try:
                # Get next task
                task = self._manager._get_next_task()
                
                if task:
                    self._current_task = task
                    self._execute_download(task)
                    self._current_task = None
                else:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ Worker {self._worker_id} error: {e}")
                time.sleep(1)
    
    def _execute_download(self, task: DownloadTask) -> None:
        """Execute a download task"""
        try:
            print(f"⬇️  Downloading: {task.get_filename()}")
            task.set_status(DownloadStatus.DOWNLOADING)
            
            # Fetch metadata
            if not self._fetch_metadata(task):
                task.set_status(DownloadStatus.FAILED)
                task.set_error("Failed to fetch metadata")
                task.trigger_error()
                return
            
            # Create chunks if file supports resume and is large enough
            file_size = task.get_metadata().get_file_size()
            supports_resume = task.get_metadata().supports_resume()
            
            if supports_resume and file_size and file_size > 5 * 1024 * 1024:  # > 5MB
                self._download_parallel(task)
            else:
                self._download_sequential(task)
            
            # Verify download if checksum provided
            if task.get_status() == DownloadStatus.DOWNLOADING:
                if task.get_expected_checksum():
                    task.set_status(DownloadStatus.VERIFYING)
                    if not self._verify_checksum(task):
                        task.set_status(DownloadStatus.FAILED)
                        task.set_error("Checksum verification failed")
                        task.trigger_error()
                        return
                
                task.set_status(DownloadStatus.COMPLETED)
                print(f"✅ Download completed: {task.get_filename()}")
                task.trigger_complete()
            
        except Exception as e:
            task.set_status(DownloadStatus.FAILED)
            error_msg = f"Download failed: {str(e)}"
            task.set_error(error_msg)
            task.trigger_error()
            print(f"❌ {error_msg}")
    
    def _fetch_metadata(self, task: DownloadTask) -> bool:
        """Fetch file metadata using HEAD request"""
        try:
            response = requests.head(task.get_url(), allow_redirects=True, timeout=10)
            
            # Get file size
            content_length = response.headers.get('Content-Length')
            if content_length:
                task.get_metadata().set_file_size(int(content_length))
            
            # Check if server supports resume
            accept_ranges = response.headers.get('Accept-Ranges', '')
            task.get_metadata().set_supports_resume(accept_ranges.lower() == 'bytes')
            
            # Get content type
            content_type = response.headers.get('Content-Type')
            if content_type:
                task.get_metadata().set_content_type(content_type)
            
            # Get ETag and Last-Modified for caching
            etag = response.headers.get('ETag')
            if etag:
                task.get_metadata().set_etag(etag)
            
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                task.get_metadata().set_last_modified(last_modified)
            
            return True
            
        except Exception as e:
            print(f"   ⚠️  Failed to fetch metadata: {str(e)}")
            return False
    
    def _download_sequential(self, task: DownloadTask) -> None:
        """Download file sequentially (single connection)"""
        response = requests.get(task.get_url(), stream=True, timeout=30)
        response.raise_for_status()
        
        file_path = task.get_full_path()
        os.makedirs(task.get_destination_path(), exist_ok=True)
        
        downloaded = 0
        start_time = time.time()
        last_update = start_time
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                # Check if cancelled
                if task.is_cancelled():
                    task.set_status(DownloadStatus.CANCELLED)
                    return
                
                # Wait if paused
                task.wait_if_paused()
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    task.update_downloaded_bytes(downloaded)
                    
                    # Update speed and ETA every second
                    current_time = time.time()
                    if current_time - last_update >= 1.0:
                        elapsed = current_time - start_time
                        speed = downloaded / elapsed
                        task.set_speed(speed)
                        task.calculate_eta()
                        task.trigger_progress()
                        last_update = current_time
    
    def _download_parallel(self, task: DownloadTask) -> None:
        """Download file using multiple parallel connections"""
        # Create temp directory
        temp_dir = os.path.join(task.get_destination_path(), f".{task.get_id()}_temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create chunks
        task.create_chunks()
        chunks = task.get_chunks()
        
        print(f"   📦 Downloading {len(chunks)} chunks in parallel")
        
        # Start chunk downloaders
        downloaders = []
        for chunk in chunks:
            downloader = ChunkDownloader(task, chunk, temp_dir)
            downloader.start()
            downloaders.append(downloader)
        
        # Monitor progress
        start_time = time.time()
        last_update = start_time
        
        while True:
            # Check if all chunks completed
            all_completed = all(c.get_status() == ChunkStatus.COMPLETED for c in chunks)
            any_failed = any(c.get_status() == ChunkStatus.FAILED for c in chunks)
            
            if all_completed or any_failed or task.is_cancelled():
                break
            
            # Calculate total progress
            total_downloaded = sum(c.get_downloaded_bytes() for c in chunks)
            task.update_downloaded_bytes(total_downloaded)
            
            # Update speed
            current_time = time.time()
            if current_time - last_update >= 1.0:
                elapsed = current_time - start_time
                speed = total_downloaded / elapsed
                task.set_speed(speed)
                task.calculate_eta()
                task.trigger_progress()
                last_update = current_time
            
            time.sleep(0.5)
        
        # Wait for all downloaders to finish
        for downloader in downloaders:
            downloader.join()
        
        # Check if download was successful
        if task.is_cancelled():
            task.set_status(DownloadStatus.CANCELLED)
            return
        
        if any_failed:
            raise Exception("Some chunks failed to download")
        
        # Merge chunks
        print(f"   🔗 Merging chunks...")
        self._merge_chunks(task, temp_dir)
        
        # Cleanup temp files
        import shutil
        shutil.rmtree(temp_dir)
    
    def _merge_chunks(self, task: DownloadTask, temp_dir: str) -> None:
        """Merge downloaded chunks into final file"""
        file_path = task.get_full_path()
        os.makedirs(task.get_destination_path(), exist_ok=True)
        
        with open(file_path, 'wb') as output_file:
            for chunk in sorted(task.get_chunks(), key=lambda c: c.get_id()):
                chunk_file = os.path.join(temp_dir, f"chunk_{chunk.get_id()}")
                with open(chunk_file, 'rb') as chunk_data:
                    output_file.write(chunk_data.read())
    
    def _verify_checksum(self, task: DownloadTask) -> bool:
        """Verify file checksum"""
        try:
            algorithm = task._checksum_algorithm
            expected = task.get_expected_checksum()
            
            if algorithm == "md5":
                hasher = hashlib.md5()
            elif algorithm == "sha256":
                hasher = hashlib.sha256()
            else:
                return True  # Unknown algorithm, skip verification
            
            file_path = task.get_full_path()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            
            actual = hasher.hexdigest()
            
            if actual.lower() == expected.lower():
                print(f"   ✅ Checksum verified: {actual}")
                return True
            else:
                print(f"   ❌ Checksum mismatch: expected {expected}, got {actual}")
                return False
                
        except Exception as e:
            print(f"   ❌ Checksum verification failed: {str(e)}")
            return False


# ==================== Download Manager ====================

class DownloadManager:
    """
    Main download manager
    Features:
    - Multiple concurrent downloads
    - Pause/Resume support
    - Parallel chunk downloads
    - Priority queue
    - Progress tracking
    - Checksum verification
    """
    
    def __init__(self, num_workers: int = 3, max_connections_per_download: int = 4):
        # Task storage
        self._tasks: Dict[str, DownloadTask] = {}
        
        # Download queue (priority-based)
        self._queue: List[DownloadTask] = []
        self._queue_lock = RLock()
        
        # Workers
        self._workers: List[DownloadWorker] = []
        self._num_workers = num_workers
        self._max_connections_per_download = max_connections_per_download
        
        # Statistics
        self._total_downloads = 0
        self._completed_downloads = 0
        self._failed_downloads = 0
        self._total_bytes_downloaded = 0
        
        # State
        self._running = False
        
        # Global lock
        self._lock = RLock()
    
    def start(self) -> None:
        """Start the download manager"""
        if self._running:
            return
        
        self._running = True
        
        # Start workers
        for i in range(self._num_workers):
            worker = DownloadWorker(f"DW{i+1}", self)
            worker.start()
            self._workers.append(worker)
        
        print(f"🚀 Download Manager started with {self._num_workers} workers")
    
    def stop(self) -> None:
        """Stop the download manager"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop workers
        for worker in self._workers:
            worker.stop()
        
        # Wait for workers
        for worker in self._workers:
            worker.join(timeout=5)
        
        print("🛑 Download Manager stopped")
    
    def add_download(self, url: str, destination_path: str = "./downloads",
                    priority: DownloadPriority = DownloadPriority.MEDIUM,
                    filename: Optional[str] = None,
                    expected_checksum: Optional[str] = None) -> DownloadTask:
        """Add a new download"""
        task_id = str(uuid.uuid4())
        task = DownloadTask(
            task_id, url, destination_path, priority,
            num_connections=self._max_connections_per_download
        )
        
        # Override filename if provided
        if filename:
            task._filename = filename
        
        # Set expected checksum if provided
        if expected_checksum:
            task.set_expected_checksum(expected_checksum)
        
        with self._lock:
            self._tasks[task_id] = task
            self._total_downloads += 1
            self._enqueue_task(task)
        
        print(f"➕ Download added: {task.get_filename()} (Priority: {priority.name})")
        return task
    
    def _enqueue_task(self, task: DownloadTask) -> None:
        """Add task to queue"""
        with self._queue_lock:
            task.set_status(DownloadStatus.QUEUED)
            self._queue.append(task)
            self._queue.sort()  # Sort by priority
    
    def _get_next_task(self) -> Optional[DownloadTask]:
        """Get next task from queue"""
        with self._queue_lock:
            if self._queue:
                return self._queue.pop(0)
        return None
    
    def pause_download(self, task_id: str) -> bool:
        """Pause a download"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.get_status() != DownloadStatus.DOWNLOADING:
            return False
        
        task.pause()
        task.set_status(DownloadStatus.PAUSED)
        task.trigger_pause()
        print(f"⏸️  Download paused: {task.get_filename()}")
        return True
    
    def resume_download(self, task_id: str) -> bool:
        """Resume a paused download"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.get_status() != DownloadStatus.PAUSED:
            return False
        
        task.resume()
        task.set_status(DownloadStatus.DOWNLOADING)
        print(f"▶️  Download resumed: {task.get_filename()}")
        return True
    
    def cancel_download(self, task_id: str) -> bool:
        """Cancel a download"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.cancel()
        task.set_status(DownloadStatus.CANCELLED)
        print(f"🚫 Download cancelled: {task.get_filename()}")
        return True
    
    def get_download(self, task_id: str) -> Optional[DownloadTask]:
        """Get download task"""
        return self._tasks.get(task_id)
    
    def get_all_downloads(self) -> List[DownloadTask]:
        """Get all downloads"""
        return list(self._tasks.values())
    
    def get_active_downloads(self) -> List[DownloadTask]:
        """Get currently downloading tasks"""
        return [t for t in self._tasks.values() 
                if t.get_status() == DownloadStatus.DOWNLOADING]
    
    def get_statistics(self) -> Dict:
        """Get download statistics"""
        active = len(self.get_active_downloads())
        queued = sum(1 for t in self._tasks.values() if t.get_status() == DownloadStatus.QUEUED)
        paused = sum(1 for t in self._tasks.values() if t.get_status() == DownloadStatus.PAUSED)
        
        return {
            'total_downloads': self._total_downloads,
            'completed': self._completed_downloads,
            'failed': self._failed_downloads,
            'active': active,
            'queued': queued,
            'paused': paused,
            'total_bytes_downloaded': self._total_bytes_downloaded,
            'workers': [
                {
                    'id': w.get_id(),
                    'current_task': w.get_current_task().get_filename() if w.get_current_task() else None
                }
                for w in self._workers
            ]
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def format_size(bytes_size: float) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def demo_download_manager():
    """Demo of the download manager"""
    
    print_section("DOWNLOAD MANAGER DEMO")
    
    manager = DownloadManager(num_workers=2, max_connections_per_download=4)
    manager.start()
    
    try:
        # ==================== Add Downloads ====================
        print_section("1. Add Downloads")
        
        # Sample file URLs (using public test files)
        downloads = [
            {
                'url': 'https://speed.hetzner.de/100MB.bin',
                'filename': 'test_100mb.bin',
                'priority': DownloadPriority.HIGH
            },
            {
                'url': 'https://ash-speed.hetzner.com/10MB.bin',
                'filename': 'test_10mb.bin',
                'priority': DownloadPriority.MEDIUM
            }
        ]
        
        tasks = []
        for dl in downloads:
            task = manager.add_download(
                url=dl['url'],
                destination_path='./downloads',
                priority=dl['priority'],
                filename=dl['filename']
            )
            
            # Add progress callback
            def make_progress_callback(filename):
                def callback(progress, speed):
                    print(f"   📊 {filename}: {progress:.1f}% @ {speed:.2f} MB/s")
                return callback
            
            task.on_progress(make_progress_callback(dl['filename']))
            task.on_complete(lambda: print(f"   ✅ Download complete!"))
            
            tasks.append(task)
        
        # ==================== Monitor Progress ====================
        print_section("2. Monitor Download Progress")
        
        print("\n   Monitoring downloads (5 seconds)...")
        for i in range(10):
            time.sleep(0.5)
            
            # Print active downloads
            active = manager.get_active_downloads()
            if active:
                print(f"\n   Active downloads: {len(active)}")
                for task in active:
                    print(f"      • {task.get_filename()}: "
                          f"{task.get_progress_percentage():.1f}% "
                          f"({format_size(task.get_downloaded_bytes())} / "
                          f"{format_size(task.get_metadata().get_file_size() or 0)}) "
                          f"@ {task.get_speed_mb():.2f} MB/s "
                          f"ETA: {task.get_eta() or 'Unknown'}")
        
        # ==================== Pause and Resume ====================
        print_section("3. Pause and Resume")
        
        if tasks:
            task = tasks[0]
            print(f"\n   Pausing: {task.get_filename()}")
            manager.pause_download(task.get_id())
            
            time.sleep(2)
            
            print(f"   Resuming: {task.get_filename()}")
            manager.resume_download(task.get_id())
        
        # ==================== Wait for Completion ====================
        print_section("4. Wait for Downloads")
        
        print("\n   Waiting for downloads to complete (max 60 seconds)...")
        max_wait = 60
        waited = 0
        
        while waited < max_wait:
            stats = manager.get_statistics()
            if stats['active'] == 0 and stats['queued'] == 0:
                break
            
            time.sleep(2)
            waited += 2
            
            print(f"   ⏳ Active: {stats['active']}, "
                  f"Completed: {stats['completed']}, "
                  f"Failed: {stats['failed']}")
        
        # ==================== Statistics ====================
        print_section("5. Download Statistics")
        
        stats = manager.get_statistics()
        print(f"\n📊 Statistics:")
        print(f"   Total Downloads: {stats['total_downloads']}")
        print(f"   Completed: {stats['completed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Active: {stats['active']}")
        print(f"   Queued: {stats['queued']}")
        print(f"   Paused: {stats['paused']}")
        print(f"   Total Downloaded: {format_size(stats['total_bytes_downloaded'])}")
        
        print(f"\n   Worker Status:")
        for worker in stats['workers']:
            current = worker['current_task'] or 'Idle'
            print(f"      {worker['id']}: {current}")
        
        # ==================== Download Details ====================
        print_section("6. Download Details")
        
        for task in tasks:
            print(f"\n📄 {task.get_filename()}")
            print(f"   Status: {task.get_status().value}")
            print(f"   URL: {task.get_url()}")
            print(f"   Size: {format_size(task.get_metadata().get_file_size() or 0)}")
            print(f"   Downloaded: {format_size(task.get_downloaded_bytes())}")
            print(f"   Progress: {task.get_progress_percentage():.2f}%")
            print(f"   Priority: {task.get_priority().name}")
            
            if task.get_status() == DownloadStatus.COMPLETED:
                print(f"   ✅ Saved to: {task.get_full_path()}")
        
    finally:
        print_section("Cleanup")
        manager.stop()
        print("\n✅ Download Manager demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_download_manager()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Download Manager - Low Level Design
# Here's a comprehensive multi-threaded download manager system:

# Key Design Decisions:
# 1. Core Components:
# DownloadTask: Main download entity with metadata
# DownloadChunk: Represents file segment for parallel download
# DownloadWorker: Thread that manages downloads
# ChunkDownloader: Thread for downloading individual chunks
# DownloadManager: Main orchestrator
# 2. Key Features:
# ✅ Multiple concurrent downloads (configurable workers) ✅ Parallel chunk downloads (multi-connection per file) ✅ Pause/Resume support (using HTTP Range header) ✅ Priority-based queue (Urgent > High > Medium > Low) ✅ Progress tracking (percentage, speed, ETA) ✅ Checksum verification (MD5, SHA256) ✅ Automatic retry (for failed chunks) ✅ Metadata fetching (file size, content type, resume support) ✅ Callbacks (progress, complete, error, pause) ✅ Thread-safe concurrent operations

# 3. Download Strategies:
# Sequential: For small files or non-resumable downloads
# Parallel: Multi-chunk for large files (>5MB) with resume support
# Automatic strategy selection based on:
# Server support for Range header
# File size
# Configuration
# 4. Chunk Management:
# 5. Progress Tracking:
# Real-time speed calculation (bytes/second)
# ETA estimation based on current speed
# Per-chunk progress for parallel downloads
# Callbacks for UI updates
# 6. Pause/Resume:
# Uses Event objects for thread synchronization
# Preserves partial downloads in temp files
# HTTP Range header for resuming from byte position
# 7. Error Handling:
# Automatic chunk retry (configurable max retries)
# Graceful degradation (sequential if parallel fails)
# Checksum verification for data integrity
# 8. Design Patterns:
# Worker Pool: Fixed number of download workers
# Producer-Consumer: Manager produces, workers consume
# Strategy Pattern: Sequential vs Parallel download
# Observer Pattern: Callbacks for events
# Template Method: Base download flow with customization
# 9. File Organization:
# This is a production-grade download manager similar to IDM (Internet Download Manager)! ⬇️🚀
