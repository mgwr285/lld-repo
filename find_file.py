from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path
import os
import re
from collections import defaultdict
from threading import Thread, RLock
import queue
import time


# ==================== Enums ====================

class FileType(Enum):
    """File types"""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    ALL = "all"


class SizeUnit(Enum):
    """Size units for comparison"""
    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024


class SearchMode(Enum):
    """Search execution mode"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"


class MatchType(Enum):
    """Pattern matching type"""
    EXACT = "exact"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    WILDCARD = "wildcard"


# ==================== Core Models ====================

class FileInfo:
    """Information about a file/directory"""
    
    def __init__(self, path: str):
        self._path = path
        self._abs_path = os.path.abspath(path)
        
        try:
            stat_info = os.stat(path)
            self._exists = True
            self._size = stat_info.st_size
            self._created_time = datetime.fromtimestamp(stat_info.st_ctime)
            self._modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            self._accessed_time = datetime.fromtimestamp(stat_info.st_atime)
            
            if os.path.isfile(path):
                self._file_type = FileType.FILE
            elif os.path.isdir(path):
                self._file_type = FileType.DIRECTORY
            elif os.path.islink(path):
                self._file_type = FileType.SYMLINK
            else:
                self._file_type = FileType.FILE
            
            self._is_hidden = os.path.basename(path).startswith('.')
            self._permissions = oct(stat_info.st_mode)[-3:]
            
        except (OSError, FileNotFoundError):
            self._exists = False
            self._size = 0
            self._created_time = None
            self._modified_time = None
            self._accessed_time = None
            self._file_type = None
            self._is_hidden = False
            self._permissions = None
    
    def get_path(self) -> str:
        return self._path
    
    def get_absolute_path(self) -> str:
        return self._abs_path
    
    def get_name(self) -> str:
        return os.path.basename(self._path)
    
    def get_extension(self) -> str:
        """Get file extension (without dot)"""
        name = self.get_name()
        if '.' in name and not name.startswith('.'):
            return name.split('.')[-1].lower()
        return ""
    
    def get_size(self) -> int:
        """Get size in bytes"""
        return self._size
    
    def get_size_in_unit(self, unit: SizeUnit) -> float:
        """Get size in specified unit"""
        return self._size / unit.value
    
    def get_type(self) -> FileType:
        return self._file_type
    
    def get_created_time(self) -> Optional[datetime]:
        return self._created_time
    
    def get_modified_time(self) -> Optional[datetime]:
        return self._modified_time
    
    def get_accessed_time(self) -> Optional[datetime]:
        return self._accessed_time
    
    def is_hidden(self) -> bool:
        return self._is_hidden
    
    def exists(self) -> bool:
        return self._exists
    
    def get_permissions(self) -> Optional[str]:
        return self._permissions
    
    def get_parent_directory(self) -> str:
        return os.path.dirname(self._abs_path)
    
    def __str__(self) -> str:
        size_kb = self.get_size_in_unit(SizeUnit.KB)
        return (f"{self.get_name()} ({self._file_type.value if self._file_type else 'unknown'}) "
                f"- {size_kb:.2f} KB")
    
    def __repr__(self) -> str:
        return f"FileInfo(path={self._path})"


# ==================== Search Filters ====================

class SearchFilter(ABC):
    """Abstract base class for search filters"""
    
    @abstractmethod
    def matches(self, file_info: FileInfo) -> bool:
        """Check if file matches this filter"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of filter"""
        pass


class NameFilter(SearchFilter):
    """Filter by file name"""
    
    def __init__(self, pattern: str, match_type: MatchType = MatchType.CONTAINS,
                 case_sensitive: bool = False):
        self._pattern = pattern if case_sensitive else pattern.lower()
        self._match_type = match_type
        self._case_sensitive = case_sensitive
        
        # Compile regex if needed
        if match_type == MatchType.REGEX:
            flags = 0 if case_sensitive else re.IGNORECASE
            self._compiled_pattern = re.compile(pattern, flags)
        elif match_type == MatchType.WILDCARD:
            # Convert wildcard to regex (* -> .*, ? -> .)
            regex_pattern = pattern.replace('.', r'\.').replace('*', '.*').replace('?', '.')
            flags = 0 if case_sensitive else re.IGNORECASE
            self._compiled_pattern = re.compile(f'^{regex_pattern}$', flags)
        else:
            self._compiled_pattern = None
    
    def matches(self, file_info: FileInfo) -> bool:
        name = file_info.get_name()
        if not self._case_sensitive:
            name = name.lower()
        
        if self._match_type == MatchType.EXACT:
            return name == self._pattern
        elif self._match_type == MatchType.CONTAINS:
            return self._pattern in name
        elif self._match_type == MatchType.STARTS_WITH:
            return name.startswith(self._pattern)
        elif self._match_type == MatchType.ENDS_WITH:
            return name.endswith(self._pattern)
        elif self._match_type == MatchType.REGEX:
            return bool(self._compiled_pattern.search(file_info.get_name()))
        elif self._match_type == MatchType.WILDCARD:
            return bool(self._compiled_pattern.match(file_info.get_name()))
        
        return False
    
    def get_description(self) -> str:
        return f"Name {self._match_type.value} '{self._pattern}'"


class ExtensionFilter(SearchFilter):
    """Filter by file extension"""
    
    def __init__(self, extensions: List[str]):
        # Normalize extensions (remove dots, lowercase)
        self._extensions = {ext.lower().lstrip('.') for ext in extensions}
    
    def matches(self, file_info: FileInfo) -> bool:
        if file_info.get_type() != FileType.FILE:
            return False
        return file_info.get_extension() in self._extensions
    
    def get_description(self) -> str:
        return f"Extension in {{{', '.join(self._extensions)}}}"


class SizeFilter(SearchFilter):
    """Filter by file size"""
    
    def __init__(self, min_size: Optional[int] = None, max_size: Optional[int] = None,
                 unit: SizeUnit = SizeUnit.BYTES):
        self._min_size = min_size * unit.value if min_size else None
        self._max_size = max_size * unit.value if max_size else None
        self._unit = unit
    
    def matches(self, file_info: FileInfo) -> bool:
        size = file_info.get_size()
        
        if self._min_size is not None and size < self._min_size:
            return False
        if self._max_size is not None and size > self._max_size:
            return False
        
        return True
    
    def get_description(self) -> str:
        parts = []
        if self._min_size is not None:
            parts.append(f"size >= {self._min_size / self._unit.value} {self._unit.name}")
        if self._max_size is not None:
            parts.append(f"size <= {self._max_size / self._unit.value} {self._unit.name}")
        return " AND ".join(parts) if parts else "Any size"


class TypeFilter(SearchFilter):
    """Filter by file type"""
    
    def __init__(self, file_type: FileType):
        self._file_type = file_type
    
    def matches(self, file_info: FileInfo) -> bool:
        if self._file_type == FileType.ALL:
            return True
        return file_info.get_type() == self._file_type
    
    def get_description(self) -> str:
        return f"Type = {self._file_type.value}"


class DateFilter(SearchFilter):
    """Filter by modification date"""
    
    def __init__(self, modified_after: Optional[datetime] = None,
                 modified_before: Optional[datetime] = None):
        self._modified_after = modified_after
        self._modified_before = modified_before
    
    def matches(self, file_info: FileInfo) -> bool:
        modified = file_info.get_modified_time()
        if not modified:
            return False
        
        if self._modified_after and modified < self._modified_after:
            return False
        if self._modified_before and modified > self._modified_before:
            return False
        
        return True
    
    def get_description(self) -> str:
        parts = []
        if self._modified_after:
            parts.append(f"modified after {self._modified_after.strftime('%Y-%m-%d')}")
        if self._modified_before:
            parts.append(f"modified before {self._modified_before.strftime('%Y-%m-%d')}")
        return " AND ".join(parts) if parts else "Any date"


class HiddenFilter(SearchFilter):
    """Filter hidden files"""
    
    def __init__(self, include_hidden: bool = False):
        self._include_hidden = include_hidden
    
    def matches(self, file_info: FileInfo) -> bool:
        if self._include_hidden:
            return True
        return not file_info.is_hidden()
    
    def get_description(self) -> str:
        return "Include hidden" if self._include_hidden else "Exclude hidden"


class ContentFilter(SearchFilter):
    """Filter by file content (text search)"""
    
    def __init__(self, pattern: str, case_sensitive: bool = False):
        self._pattern = pattern
        self._case_sensitive = case_sensitive
        self._max_file_size = 10 * 1024 * 1024  # 10 MB limit for reading
    
    def matches(self, file_info: FileInfo) -> bool:
        # Only search in text files
        if file_info.get_type() != FileType.FILE:
            return False
        
        # Skip large files
        if file_info.get_size() > self._max_file_size:
            return False
        
        try:
            with open(file_info.get_path(), 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if not self._case_sensitive:
                    content = content.lower()
                    pattern = self._pattern.lower()
                else:
                    pattern = self._pattern
                
                return pattern in content
        except (OSError, UnicodeDecodeError, PermissionError):
            return False
    
    def get_description(self) -> str:
        return f"Content contains '{self._pattern}'"


# ==================== Search Criteria ====================

class SearchCriteria:
    """Combination of multiple filters"""
    
    def __init__(self):
        self._filters: List[SearchFilter] = []
        self._max_results: Optional[int] = None
        self._max_depth: Optional[int] = None
    
    def add_filter(self, filter: SearchFilter) -> 'SearchCriteria':
        """Add a filter (chainable)"""
        self._filters.append(filter)
        return self
    
    def set_max_results(self, max_results: int) -> 'SearchCriteria':
        """Limit number of results"""
        self._max_results = max_results
        return self
    
    def set_max_depth(self, max_depth: int) -> 'SearchCriteria':
        """Limit directory traversal depth"""
        self._max_depth = max_depth
        return self
    
    def matches(self, file_info: FileInfo) -> bool:
        """Check if file matches all filters"""
        return all(filter.matches(file_info) for filter in self._filters)
    
    def get_filters(self) -> List[SearchFilter]:
        return self._filters.copy()
    
    def get_max_results(self) -> Optional[int]:
        return self._max_results
    
    def get_max_depth(self) -> Optional[int]:
        return self._max_depth
    
    def get_description(self) -> str:
        """Get human-readable description of criteria"""
        if not self._filters:
            return "No filters (match all)"
        
        descriptions = [f.get_description() for f in self._filters]
        result = " AND ".join(descriptions)
        
        if self._max_results:
            result += f" (limit: {self._max_results})"
        if self._max_depth:
            result += f" (max depth: {self._max_depth})"
        
        return result


# ==================== Search Result ====================

class SearchResult:
    """Search operation result"""
    
    def __init__(self, criteria: SearchCriteria):
        self._criteria = criteria
        self._matches: List[FileInfo] = []
        self._total_searched = 0
        self._start_time = datetime.now()
        self._end_time: Optional[datetime] = None
        self._errors: List[str] = []
        self._lock = RLock()
    
    def add_match(self, file_info: FileInfo) -> None:
        """Add a matching file"""
        with self._lock:
            max_results = self._criteria.get_max_results()
            if max_results and len(self._matches) >= max_results:
                return
            self._matches.append(file_info)
    
    def increment_searched(self) -> None:
        """Increment count of searched files"""
        with self._lock:
            self._total_searched += 1
    
    def add_error(self, error: str) -> None:
        """Add an error message"""
        with self._lock:
            self._errors.append(error)
    
    def finalize(self) -> None:
        """Mark search as complete"""
        self._end_time = datetime.now()
    
    def get_matches(self) -> List[FileInfo]:
        """Get all matching files"""
        with self._lock:
            return self._matches.copy()
    
    def get_match_count(self) -> int:
        """Get number of matches"""
        with self._lock:
            return len(self._matches)
    
    def get_total_searched(self) -> int:
        """Get total files searched"""
        return self._total_searched
    
    def get_duration(self) -> Optional[timedelta]:
        """Get search duration"""
        if not self._end_time:
            return None
        return self._end_time - self._start_time
    
    def get_errors(self) -> List[str]:
        """Get error messages"""
        with self._lock:
            return self._errors.copy()
    
    def has_reached_limit(self) -> bool:
        """Check if result limit reached"""
        max_results = self._criteria.get_max_results()
        if not max_results:
            return False
        with self._lock:
            return len(self._matches) >= max_results
    
    def get_summary(self) -> Dict:
        """Get search summary"""
        duration = self.get_duration()
        return {
            'criteria': self._criteria.get_description(),
            'matches_found': self.get_match_count(),
            'files_searched': self.get_total_searched(),
            'duration_seconds': duration.total_seconds() if duration else None,
            'errors': len(self._errors)
        }


# ==================== Search Engine ====================

class FileSearchEngine:
    """
    Main search engine with support for:
    - Multiple search filters
    - Sequential and parallel searching
    - Depth control
    - Result limiting
    - Error handling
    """
    
    def __init__(self):
        self._search_mode = SearchMode.SEQUENTIAL
        self._num_workers = 4
        self._follow_symlinks = False
        self._lock = RLock()
    
    def set_search_mode(self, mode: SearchMode) -> None:
        """Set search execution mode"""
        self._search_mode = mode
    
    def set_num_workers(self, num_workers: int) -> None:
        """Set number of parallel workers"""
        self._num_workers = max(1, num_workers)
    
    def set_follow_symlinks(self, follow: bool) -> None:
        """Set whether to follow symbolic links"""
        self._follow_symlinks = follow
    
    def search(self, root_path: str, criteria: SearchCriteria) -> SearchResult:
        """
        Execute search starting from root_path
        
        Args:
            root_path: Starting directory for search
            criteria: Search criteria with filters
        
        Returns:
            SearchResult with matches
        """
        if not os.path.exists(root_path):
            result = SearchResult(criteria)
            result.add_error(f"Root path does not exist: {root_path}")
            result.finalize()
            return result
        
        if self._search_mode == SearchMode.PARALLEL:
            return self._parallel_search(root_path, criteria)
        else:
            return self._sequential_search(root_path, criteria)
    
    def _sequential_search(self, root_path: str, criteria: SearchCriteria) -> SearchResult:
        """Sequential depth-first search"""
        result = SearchResult(criteria)
        
        try:
            self._dfs_search(root_path, criteria, result, depth=0)
        except Exception as e:
            result.add_error(f"Search error: {str(e)}")
        
        result.finalize()
        return result
    
    def _dfs_search(self, path: str, criteria: SearchCriteria, 
                   result: SearchResult, depth: int) -> None:
        """Recursive depth-first search"""
        # Check depth limit
        max_depth = criteria.get_max_depth()
        if max_depth is not None and depth > max_depth:
            return
        
        # Check result limit
        if result.has_reached_limit():
            return
        
        try:
            # Check current path
            file_info = FileInfo(path)
            result.increment_searched()
            
            if criteria.matches(file_info):
                result.add_match(file_info)
            
            # If directory, recurse into it
            if os.path.isdir(path) and not (os.path.islink(path) and not self._follow_symlinks):
                try:
                    entries = os.listdir(path)
                    for entry in entries:
                        entry_path = os.path.join(path, entry)
                        self._dfs_search(entry_path, criteria, result, depth + 1)
                        
                        if result.has_reached_limit():
                            return
                
                except PermissionError:
                    result.add_error(f"Permission denied: {path}")
                except OSError as e:
                    result.add_error(f"Error accessing {path}: {str(e)}")
        
        except Exception as e:
            result.add_error(f"Error processing {path}: {str(e)}")
    
    def _parallel_search(self, root_path: str, criteria: SearchCriteria) -> SearchResult:
        """Parallel breadth-first search using work queue"""
        result = SearchResult(criteria)
        
        # Work queue
        work_queue = queue.Queue()
        work_queue.put((root_path, 0))  # (path, depth)
        
        # Worker function
        def worker():
            while True:
                try:
                    path, depth = work_queue.get(timeout=1)
                    
                    # Check result limit
                    if result.has_reached_limit():
                        work_queue.task_done()
                        continue
                    
                    # Check depth limit
                    max_depth = criteria.get_max_depth()
                    if max_depth is not None and depth > max_depth:
                        work_queue.task_done()
                        continue
                    
                    try:
                        # Check current path
                        file_info = FileInfo(path)
                        result.increment_searched()
                        
                        if criteria.matches(file_info):
                            result.add_match(file_info)
                        
                        # If directory, add children to queue
                        if os.path.isdir(path) and not (os.path.islink(path) and not self._follow_symlinks):
                            try:
                                entries = os.listdir(path)
                                for entry in entries:
                                    entry_path = os.path.join(path, entry)
                                    work_queue.put((entry_path, depth + 1))
                            
                            except PermissionError:
                                result.add_error(f"Permission denied: {path}")
                            except OSError as e:
                                result.add_error(f"Error accessing {path}: {str(e)}")
                    
                    except Exception as e:
                        result.add_error(f"Error processing {path}: {str(e)}")
                    
                    work_queue.task_done()
                
                except queue.Empty:
                    break
        
        # Start workers
        workers = []
        for _ in range(self._num_workers):
            t = Thread(target=worker, daemon=True)
            t.start()
            workers.append(t)
        
        # Wait for completion
        work_queue.join()
        
        # Wait for workers
        for t in workers:
            t.join(timeout=1)
        
        result.finalize()
        return result
    
    def find_duplicates(self, root_path: str, 
                       by_name: bool = True,
                       by_size: bool = False,
                       by_content: bool = False) -> Dict[str, List[FileInfo]]:
        """
        Find duplicate files
        
        Args:
            root_path: Starting directory
            by_name: Group by file name
            by_size: Group by file size
            by_content: Group by content hash (expensive)
        
        Returns:
            Dictionary of duplicate groups
        """
        # First, get all files
        criteria = SearchCriteria()
        criteria.add_filter(TypeFilter(FileType.FILE))
        
        result = self.search(root_path, criteria)
        files = result.get_matches()
        
        # Group files
        groups: Dict[str, List[FileInfo]] = defaultdict(list)
        
        for file_info in files:
            key_parts = []
            
            if by_name:
                key_parts.append(file_info.get_name())
            if by_size:
                key_parts.append(str(file_info.get_size()))
            if by_content:
                # Simple content hash (first 1KB)
                try:
                    with open(file_info.get_path(), 'rb') as f:
                        content = f.read(1024)
                        key_parts.append(str(hash(content)))
                except:
                    key_parts.append("error")
            
            key = "|".join(key_parts)
            groups[key].append(file_info)
        
        # Filter to only duplicates (more than 1 file per group)
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        
        return duplicates


# ==================== Utility Functions ====================

class SearchQueryBuilder:
    """Builder for constructing search queries fluently"""
    
    def __init__(self):
        self._criteria = SearchCriteria()
    
    def with_name(self, pattern: str, match_type: MatchType = MatchType.CONTAINS,
                  case_sensitive: bool = False) -> 'SearchQueryBuilder':
        """Add name filter"""
        self._criteria.add_filter(NameFilter(pattern, match_type, case_sensitive))
        return self
    
    def with_extension(self, *extensions: str) -> 'SearchQueryBuilder':
        """Add extension filter"""
        self._criteria.add_filter(ExtensionFilter(list(extensions)))
        return self
    
    def with_size(self, min_size: Optional[int] = None, max_size: Optional[int] = None,
                  unit: SizeUnit = SizeUnit.BYTES) -> 'SearchQueryBuilder':
        """Add size filter"""
        self._criteria.add_filter(SizeFilter(min_size, max_size, unit))
        return self
    
    def with_type(self, file_type: FileType) -> 'SearchQueryBuilder':
        """Add type filter"""
        self._criteria.add_filter(TypeFilter(file_type))
        return self
    
    def modified_after(self, date: datetime) -> 'SearchQueryBuilder':
        """Add modification date filter (after)"""
        self._criteria.add_filter(DateFilter(modified_after=date))
        return self
    
    def modified_before(self, date: datetime) -> 'SearchQueryBuilder':
        """Add modification date filter (before)"""
        self._criteria.add_filter(DateFilter(modified_before=date))
        return self
    
    def modified_within_days(self, days: int) -> 'SearchQueryBuilder':
        """Add filter for files modified in last N days"""
        after = datetime.now() - timedelta(days=days)
        self._criteria.add_filter(DateFilter(modified_after=after))
        return self
    
    def include_hidden(self, include: bool = True) -> 'SearchQueryBuilder':
        """Include or exclude hidden files"""
        self._criteria.add_filter(HiddenFilter(include))
        return self
    
    def with_content(self, pattern: str, case_sensitive: bool = False) -> 'SearchQueryBuilder':
        """Add content search filter"""
        self._criteria.add_filter(ContentFilter(pattern, case_sensitive))
        return self
    
    def limit_results(self, max_results: int) -> 'SearchQueryBuilder':
        """Limit number of results"""
        self._criteria.set_max_results(max_results)
        return self
    
    def limit_depth(self, max_depth: int) -> 'SearchQueryBuilder':
        """Limit search depth"""
        self._criteria.set_max_depth(max_depth)
        return self
    
    def build(self) -> SearchCriteria:
        """Build the search criteria"""
        return self._criteria


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def print_search_results(result: SearchResult, limit: int = 10) -> None:
    """Print search results"""
    summary = result.get_summary()
    
    print(f"\n📊 Search Summary:")
    print(f"   Criteria: {summary['criteria']}")
    print(f"   Matches: {summary['matches_found']}")
    print(f"   Files searched: {summary['files_searched']}")
    if summary['duration_seconds']:
        print(f"   Duration: {summary['duration_seconds']:.3f} seconds")
    if summary['errors'] > 0:
        print(f"   Errors: {summary['errors']}")
    
    matches = result.get_matches()
    if matches:
        print(f"\n📁 Results (showing first {min(limit, len(matches))}):")
        for i, file_info in enumerate(matches[:limit], 1):
            print(f"   {i}. {file_info.get_path()}")
            print(f"      Type: {file_info.get_type().value}, "
                  f"Size: {file_info.get_size_in_unit(SizeUnit.KB):.2f} KB, "
                  f"Modified: {file_info.get_modified_time().strftime('%Y-%m-%d %H:%M')}")
        
        if len(matches) > limit:
            print(f"   ... and {len(matches) - limit} more")
    else:
        print("\n   No matches found")


def setup_demo_file_structure(base_path: str) -> None:
    """Create a demo file structure for testing"""
    import os
    
    # Create directories
    dirs = [
        "documents",
        "documents/reports",
        "documents/drafts",
        "images",
        "images/photos",
        "code",
        "code/python",
        "code/javascript",
        ".hidden"
    ]
    
    for dir_path in dirs:
        full_path = os.path.join(base_path, dir_path)
        os.makedirs(full_path, exist_ok=True)
    
    # Create sample files
    files = [
        ("documents/report_2024.txt", "Annual report for 2024\nSales: $1M"),
        ("documents/meeting_notes.txt", "Meeting notes from Monday"),
        ("documents/reports/q1_report.txt", "Q1 financial report"),
        ("documents/reports/q2_report.txt", "Q2 financial report"),
        ("documents/drafts/draft1.txt", "Draft document version 1"),
        ("images/photo1.jpg", "fake jpg content"),
        ("images/photo2.png", "fake png content"),
        ("images/photos/vacation.jpg", "vacation photo"),
        ("code/python/main.py", "print('Hello World')\n# Python code"),
        ("code/python/utils.py", "def helper():\n    pass"),
        ("code/javascript/app.js", "console.log('JavaScript')"),
        ("README.md", "# Demo Project\nThis is a demo"),
        ("config.json", '{"setting": "value"}'),
        (".hidden/secret.txt", "hidden file content"),
    ]
    
    for file_path, content in files:
        full_path = os.path.join(base_path, file_path)
        with open(full_path, 'w') as f:
            f.write(content)
    
    # Create some larger files
    large_content = "x" * 10000
    large_files = [
        "documents/large_file.txt",
        "documents/reports/detailed_report.txt"
    ]
    
    for file_path in large_files:
        full_path = os.path.join(base_path, file_path)
        with open(full_path, 'w') as f:
            f.write(large_content)
    
    print(f"✅ Demo file structure created at: {base_path}")


def demo_file_search_system():
    """Comprehensive demo of the file search system"""
    
    print_section("FILE SEARCH UTILITY DEMO")
    
    # Setup demo files
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="file_search_demo_")
    
    try:
        setup_demo_file_structure(temp_dir)
        
        # Initialize search engine
        engine = FileSearchEngine()
        
        # ==================== Basic Name Search ====================
        print_section("1. Search by Name (Contains)")
        
        criteria = SearchQueryBuilder() \
            .with_name("report", MatchType.CONTAINS, case_sensitive=False) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Extension Search ====================
        print_section("2. Search by Extension")
        
        criteria = SearchQueryBuilder() \
            .with_extension("txt", "md") \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Size Filter ====================
        print_section("3. Search by Size (> 5 KB)")
        
        criteria = SearchQueryBuilder() \
            .with_size(min_size=5, unit=SizeUnit.KB) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Wildcard Search ====================
        print_section("4. Wildcard Search (*.py)")
        
        criteria = SearchQueryBuilder() \
            .with_name("*.py", MatchType.WILDCARD) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Regex Search ====================
        print_section("5. Regex Search (q[0-9]_report)")
        
        criteria = SearchQueryBuilder() \
            .with_name(r"q[0-9]_report", MatchType.REGEX) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Type Filter ====================
        print_section("6. Search Only Directories")
        
        criteria = SearchQueryBuilder() \
            .with_type(FileType.DIRECTORY) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Combined Filters ====================
        print_section("7. Combined Filters (Python files > 10 bytes)")
        
        criteria = SearchQueryBuilder() \
            .with_extension("py") \
            .with_size(min_size=10, unit=SizeUnit.BYTES) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Modified Date Filter ====================
        print_section("8. Files Modified in Last 1 Day")
        
        criteria = SearchQueryBuilder() \
            .modified_within_days(1) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Hidden Files ====================
        print_section("9. Include Hidden Files")
        
        # Without hidden
        criteria_no_hidden = SearchQueryBuilder() \
            .include_hidden(False) \
            .build()
        
        result_no_hidden = engine.search(temp_dir, criteria_no_hidden)
        print(f"\n📁 Without hidden files: {result_no_hidden.get_match_count()} matches")
        
        # With hidden
        criteria_with_hidden = SearchQueryBuilder() \
            .include_hidden(True) \
            .build()
        
        result_with_hidden = engine.search(temp_dir, criteria_with_hidden)
        print(f"📁 With hidden files: {result_with_hidden.get_match_count()} matches")
        
        # ==================== Content Search ====================
        print_section("10. Content Search (files containing 'report')")
        
        criteria = SearchQueryBuilder() \
            .with_content("report", case_sensitive=False) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Depth Limit ====================
        print_section("11. Search with Depth Limit")
        
        criteria_depth_1 = SearchQueryBuilder() \
            .with_type(FileType.FILE) \
            .limit_depth(1) \
            .build()
        
        result_depth_1 = engine.search(temp_dir, criteria_depth_1)
        print(f"\n📊 Depth 1: {result_depth_1.get_match_count()} files")
        
        criteria_depth_3 = SearchQueryBuilder() \
            .with_type(FileType.FILE) \
            .limit_depth(3) \
            .build()
        
        result_depth_3 = engine.search(temp_dir, criteria_depth_3)
        print(f"📊 Depth 3: {result_depth_3.get_match_count()} files")
        
        # ==================== Result Limit ====================
        print_section("12. Limit Results (First 3 matches)")
        
        criteria = SearchQueryBuilder() \
            .with_type(FileType.FILE) \
            .limit_results(3) \
            .build()
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Parallel Search ====================
        print_section("13. Parallel vs Sequential Search")
        
        criteria = SearchQueryBuilder() \
            .with_type(FileType.FILE) \
            .build()
        
        # Sequential
        engine.set_search_mode(SearchMode.SEQUENTIAL)
        result_seq = engine.search(temp_dir, criteria)
        
        # Parallel
        engine.set_search_mode(SearchMode.PARALLEL)
        engine.set_num_workers(4)
        result_par = engine.search(temp_dir, criteria)
        
        print(f"\n⏱️  Sequential: {result_seq.get_duration().total_seconds():.4f}s")
        print(f"⏱️  Parallel (4 workers): {result_par.get_duration().total_seconds():.4f}s")
        
        # ==================== Find Duplicates ====================
        print_section("14. Find Duplicate Files")
        
        # Create some duplicates
        import shutil
        shutil.copy(
            os.path.join(temp_dir, "documents/report_2024.txt"),
            os.path.join(temp_dir, "documents/report_2024_copy.txt")
        )
        
        duplicates = engine.find_duplicates(temp_dir, by_name=False, by_size=True)
        
        print(f"\n📋 Found {len(duplicates)} duplicate groups:")
        for i, (key, files) in enumerate(duplicates.items(), 1):
            if i > 5:  # Show first 5 groups
                break
            print(f"\n   Group {i} ({len(files)} files):")
            for file_info in files:
                print(f"      • {file_info.get_path()}")
        
        # ==================== Complex Query ====================
        print_section("15. Complex Query")
        
        criteria = SearchQueryBuilder() \
            .with_extension("txt", "py", "js") \
            .with_size(min_size=10, max_size=15, unit=SizeUnit.KB) \
            .modified_within_days(7) \
            .include_hidden(False) \
            .limit_results(10) \
            .build()
        
        print(f"\n🔍 Query: {criteria.get_description()}")
        
        result = engine.search(temp_dir, criteria)
        print_search_results(result)
        
        # ==================== Statistics ====================
        print_section("16. Search Statistics by Extension")
        
        criteria = SearchQueryBuilder().with_type(FileType.FILE).build()
        result = engine.search(temp_dir, criteria)
        
        ext_stats = defaultdict(lambda: {'count': 0, 'total_size': 0})
        
        for file_info in result.get_matches():
            ext = file_info.get_extension() or "(no extension)"
            ext_stats[ext]['count'] += 1
            ext_stats[ext]['total_size'] += file_info.get_size()
        
        print(f"\n📊 Files by Extension:")
        for ext, stats in sorted(ext_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            avg_size = stats['total_size'] / stats['count'] if stats['count'] > 0 else 0
            print(f"   .{ext}: {stats['count']} files, "
                  f"avg size: {avg_size / SizeUnit.KB.value:.2f} KB")
        
    finally:
        # Cleanup
        print_section("Cleanup")
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n✅ Demo files cleaned up")
        print("\n✅ File search utility demo completed!")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_file_search_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# File System Search Utility - Low Level Design
# Here's a comprehensive file search system design:

# Key Design Decisions:
# 1. Core Components:
# FileInfo: Encapsulates file metadata (size, dates, type, permissions)
# SearchFilter: Abstract interface for different filter types
# SearchCriteria: Combination of filters with limits
# SearchResult: Thread-safe result accumulator
# FileSearchEngine: Main orchestrator
# 2. Filter Types (Strategy Pattern):
# NameFilter: Exact, contains, regex, wildcard matching
# ExtensionFilter: File extension matching
# SizeFilter: Size range filtering with units
# TypeFilter: File/directory/symlink filtering
# DateFilter: Modification date filtering
# HiddenFilter: Include/exclude hidden files
# ContentFilter: Text content search
# 3. Search Strategies:
# Sequential: DFS with recursion
# Parallel: BFS with work queue and thread pool
# Both handle depth limits and result limits
# 4. Key Features:
# ✅ Multiple filter types (composable)
# ✅ Flexible pattern matching (exact, contains, regex, wildcard)
# ✅ Size filtering with units (B, KB, MB, GB)
# ✅ Date/time filtering
# ✅ Content search (grep-like)
# ✅ Hidden file handling
# ✅ Depth control
# ✅ Result limiting
# ✅ Parallel execution
# ✅ Duplicate file detection
# ✅ Error handling (permissions, etc.)
# ✅ Search statistics
# ✅ Fluent query builder
# 5. Design Patterns:
# Strategy Pattern: Different filter implementations
# Builder Pattern: SearchQueryBuilder for fluent API
# Composite Pattern: SearchCriteria combines multiple filters
# Template Method: Base SearchFilter with common interface
# Producer-Consumer: Parallel search with work queue
# 6. Performance Optimizations:
# Thread-safe result accumulation
# Early termination on result limit
# Depth limiting to avoid deep recursion
# Content search size limit (skip large files)
# Parallel execution for large directories
# This is a production-grade file search utility similar to Unix find command! 🔍
