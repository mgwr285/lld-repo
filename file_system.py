from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict
from datetime import datetime
from threading import Lock


# ==================== Enums ====================

class FileSystemNodeType(Enum):
    """Types of file system nodes"""
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"
    SYMLINK = "SYMLINK"


class Permission(Enum):
    """File permissions"""
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"


# ==================== Core Models ====================

class FileSystemNode(ABC):
    """Abstract base class for file system nodes"""
    
    def __init__(self, name: str, parent: Optional['Directory'] = None):
        self._name = name
        self._parent = parent
        self._created_at = datetime.now()
        self._modified_at = datetime.now()
        self._lock = Lock()
    
    @abstractmethod
    def get_type(self) -> FileSystemNodeType:
        """Get the type of this node"""
        pass
    
    @abstractmethod
    def get_size(self) -> int:
        """Get size in bytes"""
        pass
    
    @abstractmethod
    def is_directory(self) -> bool:
        """Check if this is a directory"""
        pass
    
    def get_name(self) -> str:
        with self._lock:
            return self._name
    
    def set_name(self, name: str) -> None:
        with self._lock:
            self._name = name
            self._modified_at = datetime.now()
    
    def get_parent(self) -> Optional['Directory']:
        with self._lock:
            return self._parent
    
    def set_parent(self, parent: Optional['Directory']) -> None:
        with self._lock:
            self._parent = parent
    
    def get_created_at(self) -> datetime:
        with self._lock:
            return self._created_at
    
    def get_modified_at(self) -> datetime:
        with self._lock:
            return self._modified_at
    
    def touch(self) -> None:
        """Update modified timestamp"""
        with self._lock:
            self._modified_at = datetime.now()
    
    def get_path(self) -> str:
        """Get full path of this node"""
        if not self._parent:
            return "/" if self._name == "/" else f"/{self._name}"
        
        parent_path = self._parent.get_path()
        if parent_path == "/":
            return f"/{self._name}"
        return f"{parent_path}/{self._name}"
    
    def __repr__(self) -> str:
        return f"{self.get_type().value}({self._name})"


class File(FileSystemNode):
    """Represents a file"""
    
    def __init__(self, name: str, parent: Optional['Directory'] = None, 
                 content: str = ""):
        super().__init__(name, parent)
        self._content = content
        self._extension = self._get_extension(name)
    
    def get_type(self) -> FileSystemNodeType:
        return FileSystemNodeType.FILE
    
    def is_directory(self) -> bool:
        return False
    
    def get_size(self) -> int:
        """Get file size in bytes"""
        with self._lock:
            return len(self._content.encode('utf-8'))
    
    def get_content(self) -> str:
        """Read file content"""
        with self._lock:
            return self._content
    
    def set_content(self, content: str) -> None:
        """Write file content"""
        with self._lock:
            self._content = content
            self._modified_at = datetime.now()
    
    def append_content(self, content: str) -> None:
        """Append to file content"""
        with self._lock:
            self._content += content
            self._modified_at = datetime.now()
    
    def get_extension(self) -> Optional[str]:
        """Get file extension"""
        return self._extension
    
    @staticmethod
    def _get_extension(filename: str) -> Optional[str]:
        """Extract file extension"""
        if '.' not in filename:
            return None
        return filename.rsplit('.', 1)[1].lower()


class Directory(FileSystemNode):
    """Represents a directory"""
    
    def __init__(self, name: str, parent: Optional['Directory'] = None):
        super().__init__(name, parent)
        self._children: Dict[str, FileSystemNode] = {}
    
    def get_type(self) -> FileSystemNodeType:
        return FileSystemNodeType.DIRECTORY
    
    def is_directory(self) -> bool:
        return True
    
    def get_size(self) -> int:
        """Get total size of directory (recursive)"""
        with self._lock:
            total = 0
            for child in self._children.values():
                total += child.get_size()
            return total
    
    def add_child(self, child: FileSystemNode) -> bool:
        """Add a child node"""
        name = child.get_name()
        
        with self._lock:
            if name in self._children:
                return False
            self._children[name] = child
            child.set_parent(self)
            self._modified_at = datetime.now()
        
        return True
    
    def remove_child(self, name: str) -> Optional[FileSystemNode]:
        """Remove a child node"""
        with self._lock:
            child = self._children.pop(name, None)
            if child:
                child.set_parent(None)
                self._modified_at = datetime.now()
            return child
    
    def get_child(self, name: str) -> Optional[FileSystemNode]:
        """Get a child by name"""
        with self._lock:
            return self._children.get(name)
    
    def get_children(self) -> List[FileSystemNode]:
        """Get all children"""
        with self._lock:
            return list(self._children.values())
    
    def has_child(self, name: str) -> bool:
        """Check if child exists"""
        with self._lock:
            return name in self._children
    
    def is_empty(self) -> bool:
        """Check if directory is empty"""
        with self._lock:
            return len(self._children) == 0


class SymLink(FileSystemNode):
    """Represents a symbolic link"""
    
    def __init__(self, name: str, target_path: str, 
                 parent: Optional['Directory'] = None):
        super().__init__(name, parent)
        self._target_path = target_path
    
    def get_type(self) -> FileSystemNodeType:
        return FileSystemNodeType.SYMLINK
    
    def is_directory(self) -> bool:
        return False
    
    def get_size(self) -> int:
        return len(self._target_path)
    
    def get_target_path(self) -> str:
        with self._lock:
            return self._target_path
    
    def set_target_path(self, path: str) -> None:
        with self._lock:
            self._target_path = path
            self._modified_at = datetime.now()


# ==================== Path Parser ====================

class PathParser:
    """Parses and validates file system paths"""
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize a path (remove redundant separators, etc.)"""
        # Remove trailing slashes except for root
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        
        # Handle empty path
        if not path:
            return "/"
        
        # Ensure absolute path
        if not path.startswith("/"):
            path = "/" + path
        
        return path
    
    @staticmethod
    def split_path(path: str) -> List[str]:
        """Split path into components"""
        path = PathParser.normalize_path(path)
        
        if path == "/":
            return []
        
        # Remove leading slash and split
        components = path[1:].split("/")
        return [c for c in components if c]  # Filter empty strings
    
    @staticmethod
    def get_parent_path(path: str) -> str:
        """Get parent directory path"""
        path = PathParser.normalize_path(path)
        
        if path == "/":
            return "/"
        
        return "/".join(path.rsplit("/", 1)[:-1]) or "/"
    
    @staticmethod
    def get_basename(path: str) -> str:
        """Get the last component of the path"""
        path = PathParser.normalize_path(path)
        
        if path == "/":
            return "/"
        
        return path.rsplit("/", 1)[-1]
    
    @staticmethod
    def join_paths(base: str, *paths: str) -> str:
        """Join multiple path components"""
        base = PathParser.normalize_path(base)
        
        for path in paths:
            if path.startswith("/"):
                # Absolute path, replace base
                base = path
            else:
                # Relative path, append
                if base == "/":
                    base = f"/{path}"
                else:
                    base = f"{base}/{path}"
        
        return PathParser.normalize_path(base)
    
    @staticmethod
    def is_valid_name(name: str) -> bool:
        """Check if name is valid for a file/directory"""
        if not name or name == "." or name == "..":
            return False
        
        # Check for invalid characters
        invalid_chars = ['/', '\0', '\n', '\r']
        for char in invalid_chars:
            if char in name:
                return False
        
        return True


# ==================== File System ====================

class FileSystem:
    """Main file system implementation"""
    
    def __init__(self):
        self._root = Directory("/")
        self._current_directory = self._root
        self._lock = Lock()
    
    def get_root(self) -> Directory:
        """Get root directory"""
        return self._root
    
    def get_current_directory(self) -> Directory:
        """Get current working directory"""
        with self._lock:
            return self._current_directory
    
    def get_current_path(self) -> str:
        """Get current working directory path"""
        return self.get_current_directory().get_path()
    
    def change_directory(self, path: str) -> bool:
        """Change current directory"""
        node = self._resolve_path(path)
        
        if not node:
            print(f"cd: {path}: No such directory")
            return False
        
        if not node.is_directory():
            print(f"cd: {path}: Not a directory")
            return False
        
        with self._lock:
            self._current_directory = node
        
        return True
    
    def _resolve_path(self, path: str, follow_symlinks: bool = True) -> Optional[FileSystemNode]:
        """
        Resolve a path to a node.
        Supports both absolute and relative paths.
        """
        path = PathParser.normalize_path(path)
        
        # Start from root or current directory
        if path.startswith("/"):
            current = self._root
            components = PathParser.split_path(path)
        else:
            current = self.get_current_directory()
            components = path.split("/")
        
        # Handle root
        if not components:
            return self._root
        
        # Traverse path
        for component in components:
            if component == ".":
                continue
            elif component == "..":
                parent = current.get_parent()
                current = parent if parent else current
            else:
                if not current.is_directory():
                    return None
                
                child = current.get_child(component)
                if not child:
                    return None
                
                # Handle symlinks
                if follow_symlinks and isinstance(child, SymLink):
                    target = self._resolve_path(child.get_target_path())
                    if not target:
                        return None
                    current = target
                else:
                    current = child
        
        return current
    
    def create_file(self, path: str, content: str = "") -> Optional[File]:
        """Create a new file"""
        path = PathParser.normalize_path(path)
        parent_path = PathParser.get_parent_path(path)
        filename = PathParser.get_basename(path)
        
        # Validate filename
        if not PathParser.is_valid_name(filename):
            print(f"Invalid filename: {filename}")
            return None
        
        # Get parent directory
        parent = self._resolve_path(parent_path)
        if not parent or not parent.is_directory():
            print(f"Parent directory not found: {parent_path}")
            return None
        
        # Check if file already exists
        if parent.has_child(filename):
            print(f"File already exists: {path}")
            return None
        
        # Create file
        file = File(filename, parent, content)
        parent.add_child(file)
        
        print(f"Created file: {path}")
        return file
    
    def create_directory(self, path: str) -> Optional[Directory]:
        """Create a new directory"""
        path = PathParser.normalize_path(path)
        parent_path = PathParser.get_parent_path(path)
        dirname = PathParser.get_basename(path)
        
        # Validate directory name
        if not PathParser.is_valid_name(dirname):
            print(f"Invalid directory name: {dirname}")
            return None
        
        # Get parent directory
        parent = self._resolve_path(parent_path)
        if not parent or not parent.is_directory():
            print(f"Parent directory not found: {parent_path}")
            return None
        
        # Check if directory already exists
        if parent.has_child(dirname):
            print(f"Directory already exists: {path}")
            return None
        
        # Create directory
        directory = Directory(dirname, parent)
        parent.add_child(directory)
        
        print(f"Created directory: {path}")
        return directory
    
    def create_directories(self, path: str) -> Optional[Directory]:
        """Create directory and all parent directories (like mkdir -p)"""
        path = PathParser.normalize_path(path)
        components = PathParser.split_path(path)
        
        current = self._root
        current_path = "/"
        
        for component in components:
            if not PathParser.is_valid_name(component):
                print(f"Invalid component: {component}")
                return None
            
            # Check if exists
            child = current.get_child(component)
            
            if child:
                if not child.is_directory():
                    print(f"Not a directory: {current_path}/{component}")
                    return None
                current = child
            else:
                # Create directory
                new_dir = Directory(component, current)
                current.add_child(new_dir)
                current = new_dir
            
            current_path = PathParser.join_paths(current_path, component)
        
        print(f"Created directories: {path}")
        return current
    
    def delete(self, path: str, recursive: bool = False) -> bool:
        """Delete a file or directory"""
        node = self._resolve_path(path)
        
        if not node:
            print(f"rm: {path}: No such file or directory")
            return False
        
        # Cannot delete root
        if node == self._root:
            print("rm: Cannot delete root directory")
            return False
        
        # Check if directory is not empty
        if node.is_directory() and not node.is_empty() and not recursive:
            print(f"rm: {path}: Directory not empty (use recursive=True)")
            return False
        
        # Remove from parent
        parent = node.get_parent()
        if parent:
            parent.remove_child(node.get_name())
            print(f"Deleted: {path}")
            return True
        
        return False
    
    def move(self, source_path: str, dest_path: str) -> bool:
        """Move/rename a file or directory"""
        source = self._resolve_path(source_path)
        
        if not source:
            print(f"mv: {source_path}: No such file or directory")
            return False
        
        # Cannot move root
        if source == self._root:
            print("mv: Cannot move root directory")
            return False
        
        # Check if destination exists
        dest = self._resolve_path(dest_path)
        
        if dest:
            # Destination exists
            if dest.is_directory():
                # Move into directory
                dest_parent = dest
                new_name = source.get_name()
            else:
                print(f"mv: {dest_path}: Destination exists and is not a directory")
                return False
        else:
            # Destination doesn't exist - rename or move
            dest_parent_path = PathParser.get_parent_path(dest_path)
            dest_parent = self._resolve_path(dest_parent_path)
            
            if not dest_parent or not dest_parent.is_directory():
                print(f"mv: {dest_parent_path}: Parent directory not found")
                return False
            
            new_name = PathParser.get_basename(dest_path)
        
        # Check if target name already exists in destination
        if dest_parent.has_child(new_name):
            print(f"mv: {dest_path}: File already exists")
            return False
        
        # Remove from old parent
        old_parent = source.get_parent()
        if old_parent:
            old_parent.remove_child(source.get_name())
        
        # Update name if different
        if new_name != source.get_name():
            source.set_name(new_name)
        
        # Add to new parent
        dest_parent.add_child(source)
        
        print(f"Moved: {source_path} -> {dest_path}")
        return True
    
    def copy(self, source_path: str, dest_path: str) -> bool:
        """Copy a file or directory"""
        source = self._resolve_path(source_path)
        
        if not source:
            print(f"cp: {source_path}: No such file or directory")
            return False
        
        # Get destination parent
        dest_parent_path = PathParser.get_parent_path(dest_path)
        dest_parent = self._resolve_path(dest_parent_path)
        
        if not dest_parent or not dest_parent.is_directory():
            print(f"cp: {dest_parent_path}: Parent directory not found")
            return False
        
        dest_name = PathParser.get_basename(dest_path)
        
        # Check if destination already exists
        if dest_parent.has_child(dest_name):
            print(f"cp: {dest_path}: File already exists")
            return False
        
        # Copy based on type
        if isinstance(source, File):
            new_file = File(dest_name, dest_parent, source.get_content())
            dest_parent.add_child(new_file)
            print(f"Copied file: {source_path} -> {dest_path}")
            return True
        elif isinstance(source, Directory):
            new_dir = self._copy_directory(source, dest_name, dest_parent)
            if new_dir:
                dest_parent.add_child(new_dir)
                print(f"Copied directory: {source_path} -> {dest_path}")
                return True
        
        return False
    
    def _copy_directory(self, source: Directory, new_name: str, 
                       new_parent: Directory) -> Directory:
        """Recursively copy a directory"""
        new_dir = Directory(new_name, new_parent)
        
        for child in source.get_children():
            if isinstance(child, File):
                new_file = File(child.get_name(), new_dir, child.get_content())
                new_dir.add_child(new_file)
            elif isinstance(child, Directory):
                new_subdir = self._copy_directory(child, child.get_name(), new_dir)
                new_dir.add_child(new_subdir)
        
        return new_dir
    
    def list_directory(self, path: str = ".", detailed: bool = False) -> List[FileSystemNode]:
        """List contents of a directory"""
        if path == ".":
            node = self.get_current_directory()
        else:
            node = self._resolve_path(path)
        
        if not node:
            print(f"ls: {path}: No such directory")
            return []
        
        if not node.is_directory():
            print(f"ls: {path}: Not a directory")
            return []
        
        children = node.get_children()
        
        if detailed:
            print(f"\nContents of {node.get_path()}:")
            print(f"{'Type':<12} {'Name':<30} {'Size':<12} {'Modified':<20}")
            print("-" * 80)
            
            for child in sorted(children, key=lambda x: x.get_name()):
                type_str = child.get_type().value
                name = child.get_name()
                size = child.get_size()
                modified = child.get_modified_at().strftime("%Y-%m-%d %H:%M:%S")
                
                print(f"{type_str:<12} {name:<30} {size:<12} {modified:<20}")
        else:
            names = [child.get_name() for child in sorted(children, key=lambda x: x.get_name())]
            print("  ".join(names))
        
        return children
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file content"""
        node = self._resolve_path(path)
        
        if not node:
            print(f"cat: {path}: No such file")
            return None
        
        if not isinstance(node, File):
            print(f"cat: {path}: Not a file")
            return None
        
        return node.get_content()
    
    def write_file(self, path: str, content: str) -> bool:
        """Write content to file"""
        node = self._resolve_path(path)
        
        if not node:
            # File doesn't exist, create it
            file = self.create_file(path, content)
            return file is not None
        
        if not isinstance(node, File):
            print(f"write: {path}: Not a file")
            return False
        
        node.set_content(content)
        print(f"Wrote to file: {path}")
        return True
    
    def find(self, name: str, start_path: str = "/") -> List[str]:
        """Find all files/directories matching name"""
        start = self._resolve_path(start_path)
        
        if not start:
            print(f"find: {start_path}: No such directory")
            return []
        
        results = []
        self._find_recursive(start, name, results)
        return results
    
    def _find_recursive(self, node: FileSystemNode, name: str, results: List[str]) -> None:
        """Recursive helper for find"""
        if node.get_name() == name or name in node.get_name():
            results.append(node.get_path())
        
        if node.is_directory():
            for child in node.get_children():
                self._find_recursive(child, name, results)
    
    def get_info(self, path: str) -> None:
        """Display detailed information about a file/directory"""
        node = self._resolve_path(path)
        
        if not node:
            print(f"stat: {path}: No such file or directory")
            return
        
        print(f"\nInformation for: {node.get_path()}")
        print("-" * 60)
        print(f"Name:          {node.get_name()}")
        print(f"Type:          {node.get_type().value}")
        print(f"Size:          {node.get_size()} bytes")
        print(f"Created:       {node.get_created_at().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Modified:      {node.get_modified_at().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if isinstance(node, File):
            ext = node.get_extension()
            print(f"Extension:     {ext if ext else 'None'}")
        elif isinstance(node, Directory):
            print(f"Children:      {len(node.get_children())}")
        elif isinstance(node, SymLink):
            print(f"Target:        {node.get_target_path()}")
        
        print("-" * 60 + "\n")
    
    def tree(self, path: str = ".", max_depth: int = -1) -> None:
        """Display directory tree"""
        node = self._resolve_path(path)
        
        if not node:
            print(f"tree: {path}: No such directory")
            return
        
        print(f"\n{node.get_path()}")
        if node.is_directory():
            self._tree_recursive(node, "", max_depth, 0)
        print()
    
    def _tree_recursive(self, node: Directory, prefix: str, max_depth: int, depth: int) -> None:
        """Recursive helper for tree"""
        if max_depth >= 0 and depth >= max_depth:
            return
        
        children = sorted(node.get_children(), key=lambda x: x.get_name())
        
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{child.get_name()}")
            
            if child.is_directory():
                extension = "    " if is_last else "│   "
                self._tree_recursive(child, prefix + extension, max_depth, depth + 1)


# ==================== Demo Usage ====================

def main():
    """Demo the file system"""
    print("=== File System Demo ===\n")
    
    fs = FileSystem()
    
    # Create directory structure
    print("--- Creating Directory Structure ---")
    fs.create_directories("/home/user/documents")
    fs.create_directories("/home/user/downloads")
    fs.create_directories("/home/user/pictures")
    fs.create_directory("/var")
    fs.create_directory("/etc")
    
    # Create some files
    print("\n--- Creating Files ---")
    fs.create_file("/home/user/documents/readme.txt", "This is a readme file.")
    fs.create_file("/home/user/documents/notes.txt", "My personal notes.")
    fs.create_file("/home/user/downloads/file1.pdf", "PDF content here")
    fs.create_file("/home/user/pictures/photo1.jpg", "JPEG data")
    fs.create_file("/etc/config.conf", "Configuration settings")
    
    # Display tree
    print("\n--- Directory Tree ---")
    fs.tree("/", max_depth=3)
    
    # Change directory
    print("\n--- Changing Directory ---")
    print(f"Current: {fs.get_current_path()}")
    fs.change_directory("/home/user")
    print(f"Current: {fs.get_current_path()}")
    
    # List directory
    print("\n--- Listing Directory ---")
    fs.list_directory(".", detailed=True)
    
    # Read file
    print("\n--- Reading File ---")
    content = fs.read_file("documents/readme.txt")
    if content:
        print(f"Content: {content}")
    
    # Write to file
    print("\n--- Writing to File ---")
    fs.write_file("documents/readme.txt", "Updated readme content!")
    content = fs.read_file("documents/readme.txt")
    if content:
        print(f"New Content: {content}")
    
    # Copy file
    print("\n--- Copying File ---")
    fs.copy("documents/readme.txt", "documents/readme_backup.txt")
    fs.list_directory("documents")
    
    # Move file
    print("\n--- Moving File ---")
    fs.move("documents/notes.txt", "downloads/notes.txt")
    fs.list_directory("documents")
    fs.list_directory("downloads")
    
    # Find files
    print("\n--- Finding Files ---")
    results = fs.find("readme")
    print(f"Found {len(results)} match(es):")
    for result in results:
        print(f"  {result}")
    
    # Get file info
    print("\n--- File Information ---")
    fs.get_info("/home/user/documents/readme.txt")
    
    # Test path parsing
    print("\n--- Path Parsing Tests ---")
    test_paths = [
        "/home/user/documents",
        "/home/user/documents/",
        "documents",
        "./documents",
        "../downloads",
        "/home/user/documents/../downloads"
    ]
    
    for path in test_paths:
        normalized = PathParser.normalize_path(path)
        basename = PathParser.get_basename(path)
        parent = PathParser.get_parent_path(path)
        components = PathParser.split_path(path)
        print(f"Path: {path}")
        print(f"  Normalized: {normalized}")
        print(f"  Basename: {basename}")
        print(f"  Parent: {parent}")
        print(f"  Components: {components}\n")
    
    # Delete operations
    print("\n--- Delete Operations ---")
    fs.create_file("/home/user/temp.txt", "Temporary file")
    fs.list_directory("/home/user")
    fs.delete("/home/user/temp.txt")
    fs.list_directory("/home/user")
    
    # Try to delete non-empty directory
    print("\n--- Attempting to Delete Non-Empty Directory ---")
    fs.delete("/home/user/documents")  # Should fail
    
    print("\n--- Deleting Directory Recursively ---")
    fs.delete("/home/user/downloads", recursive=True)
    fs.tree("/home/user")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# Key Design Decisions
# Design Patterns Used:

# Composite Pattern - File system hierarchy:

# FileSystemNode (Component)
# File (Leaf)
# Directory (Composite)
# SymLink (Leaf with reference)


# Template Method (in abstract class):

# Common operations defined in base class
# Specific implementations in subclasses



# Core Features:
# ✅ Hierarchical Structure: Directories contain files and directories
# ✅ Path Resolution: Absolute and relative paths
# ✅ Path Parsing: Normalize, split, join paths
# ✅ CRUD Operations: Create, read, update, delete
# ✅ Navigation: Change directory, current working directory
# ✅ Search: Find files by name
# ✅ Copy/Move: File and directory operations
# ✅ Metadata: Creation time, modification time, size
# ✅ Tree Display: Visual directory structure
# ✅ Symbolic Links: Reference to other files/directories
