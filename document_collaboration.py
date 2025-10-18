from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid
import re


# ==================== Enums ====================

class AccessLevel(Enum):
    """Access levels for documents"""
    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"
    NONE = "none"
    
    def can_edit(self) -> bool:
        return self in [AccessLevel.OWNER, AccessLevel.EDITOR]
    
    def can_comment(self) -> bool:
        return self in [AccessLevel.OWNER, AccessLevel.EDITOR, AccessLevel.COMMENTER]
    
    def can_view(self) -> bool:
        return self in [AccessLevel.OWNER, AccessLevel.EDITOR, AccessLevel.COMMENTER, AccessLevel.VIEWER]
    
    def can_manage_permissions(self) -> bool:
        return self == AccessLevel.OWNER
    
    def _get_level_value(self) -> int:
        """Get numeric value for comparison"""
        order = {
            AccessLevel.NONE: 0,
            AccessLevel.VIEWER: 1,
            AccessLevel.COMMENTER: 2,
            AccessLevel.EDITOR: 3,
            AccessLevel.OWNER: 4
        }
        return order[self]
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._get_level_value() < other._get_level_value()
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self._get_level_value() <= other._get_level_value()
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self._get_level_value() > other._get_level_value()
        return NotImplemented
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self._get_level_value() >= other._get_level_value()
        return NotImplemented

class OperationType(Enum):
    """Types of operations on document"""
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


class SharingMode(Enum):
    """Document sharing modes"""
    PRIVATE = "private"          # Only specific users
    ANYONE_WITH_LINK = "anyone_with_link"  # Anyone with link can view
    PUBLIC = "public"            # Anyone can search and view


class DocumentStatus(Enum):
    """Document status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CommentStatus(Enum):
    """Comment status"""
    OPEN = "open"
    RESOLVED = "resolved"


# ==================== Models ====================

class User:
    """User of the document system"""
    
    def __init__(self, user_id: str, name: str, email: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._created_at = datetime.now()
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self._user_id,
            'name': self._name,
            'email': self._email
        }


class Operation:
    """A single edit operation"""
    
    def __init__(self, operation_id: str, user: User, 
                 operation_type: OperationType,
                 position: int, content: str):
        self._operation_id = operation_id
        self._user = user
        self._operation_type = operation_type
        self._position = position
        self._content = content
        self._timestamp = datetime.now()
    
    def get_id(self) -> str:
        return self._operation_id
    
    def get_user(self) -> User:
        return self._user
    
    def get_type(self) -> OperationType:
        return self._operation_type
    
    def get_position(self) -> int:
        return self._position
    
    def get_content(self) -> str:
        return self._content
    
    def get_timestamp(self) -> datetime:
        return self._timestamp
    
    def apply(self, text: str) -> str:
        """Apply this operation to text"""
        if self._operation_type == OperationType.INSERT:
            return text[:self._position] + self._content + text[self._position:]
        elif self._operation_type == OperationType.DELETE:
            length = len(self._content)
            return text[:self._position] + text[self._position + length:]
        elif self._operation_type == OperationType.REPLACE:
            length = len(self._content.split('|')[0])  # Old content length
            new_content = self._content.split('|')[1]  # New content
            return text[:self._position] + new_content + text[self._position + length:]
        
        return text
    
    def to_dict(self) -> Dict:
        return {
            'operation_id': self._operation_id,
            'user': self._user.get_name(),
            'type': self._operation_type.value,
            'position': self._position,
            'content': self._content[:50] + ('...' if len(self._content) > 50 else ''),
            'timestamp': self._timestamp.isoformat()
        }


class Version:
    """Document version/revision"""
    
    def __init__(self, version_number: int, content: str, 
                 modified_by: User, operation: Optional[Operation] = None):
        self._version_number = version_number
        self._content = content
        self._modified_by = modified_by
        self._operation = operation
        self._timestamp = datetime.now()
    
    def get_version_number(self) -> int:
        return self._version_number
    
    def get_content(self) -> str:
        return self._content
    
    def get_modified_by(self) -> User:
        return self._modified_by
    
    def get_timestamp(self) -> datetime:
        return self._timestamp
    
    def to_dict(self) -> Dict:
        return {
            'version': self._version_number,
            'modified_by': self._modified_by.get_name(),
            'timestamp': self._timestamp.isoformat(),
            'content_length': len(self._content),
            'operation': self._operation.to_dict() if self._operation else None
        }


class Comment:
    """Comment on document"""
    
    def __init__(self, comment_id: str, user: User, content: str,
                 position: Optional[int] = None, length: Optional[int] = None):
        self._comment_id = comment_id
        self._user = user
        self._content = content
        self._position = position  # Character position in document
        self._length = length      # Length of selected text
        self._status = CommentStatus.OPEN
        self._replies: List['Comment'] = []
        self._created_at = datetime.now()
        self._resolved_at: Optional[datetime] = None
        self._resolved_by: Optional[User] = None
    
    def get_id(self) -> str:
        return self._comment_id
    
    def get_user(self) -> User:
        return self._user
    
    def get_content(self) -> str:
        return self._content
    
    def get_status(self) -> CommentStatus:
        return self._status
    
    def add_reply(self, reply: 'Comment') -> None:
        """Add a reply to this comment"""
        self._replies.append(reply)
    
    def resolve(self, user: User) -> None:
        """Mark comment as resolved"""
        self._status = CommentStatus.RESOLVED
        self._resolved_at = datetime.now()
        self._resolved_by = user
    
    def reopen(self) -> None:
        """Reopen resolved comment"""
        self._status = CommentStatus.OPEN
        self._resolved_at = None
        self._resolved_by = None
    
    def to_dict(self) -> Dict:
        return {
            'comment_id': self._comment_id,
            'user': self._user.get_name(),
            'content': self._content,
            'position': self._position,
            'status': self._status.value,
            'replies': len(self._replies),
            'created_at': self._created_at.isoformat(),
            'resolved_at': self._resolved_at.isoformat() if self._resolved_at else None
        }


class AccessControl:
    """Access control for a document"""
    
    def __init__(self):
        # User-specific permissions
        self._user_permissions: Dict[str, AccessLevel] = {}
        
        # Link sharing settings
        self._sharing_mode = SharingMode.PRIVATE
        self._link_access_level = AccessLevel.VIEWER  # Default for link sharing
    
    def grant_access(self, user_id: str, level: AccessLevel) -> None:
        """Grant access to a user"""
        self._user_permissions[user_id] = level
    
    def revoke_access(self, user_id: str) -> None:
        """Revoke user's access"""
        if user_id in self._user_permissions:
            del self._user_permissions[user_id]
    
    def get_access_level(self, user_id: str) -> AccessLevel:
        """Get user's access level"""
        # Check user-specific permission
        if user_id in self._user_permissions:
            return self._user_permissions[user_id]
        
        # Check sharing mode
        if self._sharing_mode == SharingMode.PUBLIC:
            return AccessLevel.VIEWER
        elif self._sharing_mode == SharingMode.ANYONE_WITH_LINK:
            return self._link_access_level
        
        return AccessLevel.NONE
    
    def set_sharing_mode(self, mode: SharingMode, 
                        link_access_level: AccessLevel = AccessLevel.VIEWER) -> None:
        """Set document sharing mode"""
        self._sharing_mode = mode
        self._link_access_level = link_access_level
    
    def get_sharing_mode(self) -> SharingMode:
        return self._sharing_mode
    
    def list_permissions(self) -> Dict[str, str]:
        """List all user permissions"""
        return {
            user_id: level.value 
            for user_id, level in self._user_permissions.items()
        }
    
    def to_dict(self) -> Dict:
        return {
            'sharing_mode': self._sharing_mode.value,
            'link_access_level': self._link_access_level.value,
            'user_count': len(self._user_permissions),
            'users': self.list_permissions()
        }


class Document:
    """Collaborative document"""
    
    def __init__(self, document_id: str, title: str, owner: User):
        self._document_id = document_id
        self._title = title
        self._owner = owner
        self._content = ""
        
        # Access control
        self._access_control = AccessControl()
        self._access_control.grant_access(owner.get_id(), AccessLevel.OWNER)
        
        # Version history
        self._versions: List[Version] = []
        self._current_version = 0
        self._add_version(owner, None)  # Initial version
        
        # Comments
        self._comments: Dict[str, Comment] = {}
        
        # Active editors (for real-time collaboration)
        self._active_editors: Set[str] = set()  # Set of user_ids
        
        # Metadata
        self._created_at = datetime.now()
        self._modified_at = datetime.now()
        self._status = DocumentStatus.ACTIVE
        
        # Statistics
        self._view_count = 0
        self._edit_count = 0
    
    def get_id(self) -> str:
        return self._document_id
    
    def get_title(self) -> str:
        return self._title
    
    def get_content(self) -> str:
        return self._content
    
    def get_owner(self) -> User:
        return self._owner
    
    def get_status(self) -> DocumentStatus:
        return self._status
    
    def get_access_control(self) -> AccessControl:
        return self._access_control
    
    # ==================== Access Control ====================
    
    def check_access(self, user: User, required_level: AccessLevel) -> bool:
        """Check if user has required access level"""
        user_level = self._access_control.get_access_level(user.get_id())
        return user_level >= required_level
    
    def grant_access(self, granter: User, user_id: str, level: AccessLevel) -> bool:
        """Grant access to another user (only owner can do this)"""
        if not self._access_control.get_access_level(granter.get_id()).can_manage_permissions():
            print(f"❌ Only owner can manage permissions")
            return False
        
        self._access_control.grant_access(user_id, level)
        print(f"✅ Granted {level.value} access to user {user_id}")
        return True
    
    def revoke_access(self, revoker: User, user_id: str) -> bool:
        """Revoke user's access"""
        if not self._access_control.get_access_level(revoker.get_id()).can_manage_permissions():
            print(f"❌ Only owner can manage permissions")
            return False
        
        if user_id == self._owner.get_id():
            print(f"❌ Cannot revoke owner's access")
            return False
        
        self._access_control.revoke_access(user_id)
        print(f"✅ Revoked access for user {user_id}")
        return True
    
    def set_sharing_mode(self, user: User, mode: SharingMode, 
                        link_access_level: AccessLevel = AccessLevel.VIEWER) -> bool:
        """Set sharing mode (only owner)"""
        if not self._access_control.get_access_level(user.get_id()).can_manage_permissions():
            print(f"❌ Only owner can change sharing mode")
            return False
        
        self._access_control.set_sharing_mode(mode, link_access_level)
        print(f"✅ Sharing mode set to {mode.value}")
        return True
    
    # ==================== Document Operations ====================
    
    def view(self, user: User) -> Optional[str]:
        """View document content"""
        if not self.check_access(user, AccessLevel.VIEWER):
            print(f"❌ User {user.get_name()} does not have view access")
            return None
        
        self._view_count += 1
        return self._content
    
    def edit(self, user: User, operation: Operation) -> bool:
        """Apply an edit operation"""
        if not self.check_access(user, AccessLevel.EDITOR):
            print(f"❌ User {user.get_name()} does not have edit access")
            return False
        
        # Apply operation
        try:
            self._content = operation.apply(self._content)
            self._modified_at = datetime.now()
            self._edit_count += 1
            
            # Create new version
            self._add_version(user, operation)
            
            print(f"✅ Edit applied by {user.get_name()}")
            return True
        
        except Exception as e:
            print(f"❌ Error applying edit: {e}")
            return False
    
    def insert(self, user: User, position: int, text: str) -> bool:
        """Insert text at position"""
        operation_id = str(uuid.uuid4())
        operation = Operation(operation_id, user, OperationType.INSERT, position, text)
        return self.edit(user, operation)
    
    def delete(self, user: User, position: int, length: int) -> bool:
        """Delete text from position"""
        if position + length > len(self._content):
            print(f"❌ Delete position out of range")
            return False
        
        deleted_text = self._content[position:position + length]
        operation_id = str(uuid.uuid4())
        operation = Operation(operation_id, user, OperationType.DELETE, position, deleted_text)
        return self.edit(user, operation)
    
    def replace(self, user: User, position: int, old_text: str, new_text: str) -> bool:
        """Replace text at position"""
        operation_id = str(uuid.uuid4())
        content = f"{old_text}|{new_text}"
        operation = Operation(operation_id, user, OperationType.REPLACE, position, content)
        return self.edit(user, operation)
    
    def set_title(self, user: User, new_title: str) -> bool:
        """Change document title"""
        if not self.check_access(user, AccessLevel.EDITOR):
            print(f"❌ User {user.get_name()} does not have edit access")
            return False
        
        old_title = self._title
        self._title = new_title
        self._modified_at = datetime.now()
        
        print(f"✅ Title changed from '{old_title}' to '{new_title}'")
        return True
    
    # ==================== Version History ====================
    
    def _add_version(self, user: User, operation: Optional[Operation]) -> None:
        """Add a new version to history"""
        self._current_version += 1
        version = Version(self._current_version, self._content, user, operation)
        self._versions.append(version)
    
    def get_version(self, version_number: int) -> Optional[Version]:
        """Get specific version"""
        if 1 <= version_number <= self._current_version:
            return self._versions[version_number - 1]
        return None
    
    def get_version_history(self, limit: int = 10) -> List[Version]:
        """Get recent version history"""
        return self._versions[-limit:][::-1]  # Most recent first
    
    def restore_version(self, user: User, version_number: int) -> bool:
        """Restore document to a specific version"""
        if not self.check_access(user, AccessLevel.EDITOR):
            print(f"❌ User {user.get_name()} does not have edit access")
            return False
        
        version = self.get_version(version_number)
        if not version:
            print(f"❌ Version {version_number} not found")
            return False
        
        self._content = version.get_content()
        self._modified_at = datetime.now()
        
        # Create new version for the restore
        self._add_version(user, None)
        
        print(f"✅ Restored to version {version_number}")
        return True
    
    # ==================== Comments ====================
    
    def add_comment(self, user: User, content: str, 
                   position: Optional[int] = None, 
                   length: Optional[int] = None) -> Optional[Comment]:
        """Add a comment to document"""
        if not self.check_access(user, AccessLevel.COMMENTER):
            print(f"❌ User {user.get_name()} does not have comment access")
            return None
        
        comment_id = str(uuid.uuid4())
        comment = Comment(comment_id, user, content, position, length)
        self._comments[comment_id] = comment
        
        print(f"✅ Comment added by {user.get_name()}")
        return comment
    
    def reply_to_comment(self, user: User, comment_id: str, 
                        reply_content: str) -> Optional[Comment]:
        """Reply to a comment"""
        if not self.check_access(user, AccessLevel.COMMENTER):
            print(f"❌ User {user.get_name()} does not have comment access")
            return None
        
        parent_comment = self._comments.get(comment_id)
        if not parent_comment:
            print(f"❌ Comment not found")
            return None
        
        reply_id = str(uuid.uuid4())
        reply = Comment(reply_id, user, reply_content)
        parent_comment.add_reply(reply)
        
        print(f"✅ Reply added by {user.get_name()}")
        return reply
    
    def resolve_comment(self, user: User, comment_id: str) -> bool:
        """Resolve a comment"""
        if not self.check_access(user, AccessLevel.COMMENTER):
            print(f"❌ User {user.get_name()} does not have comment access")
            return False
        
        comment = self._comments.get(comment_id)
        if not comment:
            print(f"❌ Comment not found")
            return False
        
        comment.resolve(user)
        print(f"✅ Comment resolved by {user.get_name()}")
        return True
    
    def get_comments(self, open_only: bool = False) -> List[Comment]:
        """Get all comments"""
        comments = list(self._comments.values())
        
        if open_only:
            comments = [c for c in comments if c.get_status() == CommentStatus.OPEN]
        
        return comments
    
    # ==================== Real-time Collaboration ====================
    
    def join_editing(self, user: User) -> bool:
        """User joins as active editor"""
        if not self.check_access(user, AccessLevel.VIEWER):
            return False
        
        self._active_editors.add(user.get_id())
        print(f"👤 {user.get_name()} joined editing")
        return True
    
    def leave_editing(self, user: User) -> bool:
        """User leaves editing session"""
        if user.get_id() in self._active_editors:
            self._active_editors.remove(user.get_id())
            print(f"👤 {user.get_name()} left editing")
            return True
        return False
    
    def get_active_editors(self) -> Set[str]:
        """Get currently active editors"""
        return self._active_editors.copy()
    
    # ==================== Document Management ====================
    
    def archive(self, user: User) -> bool:
        """Archive document"""
        if not self._access_control.get_access_level(user.get_id()).can_manage_permissions():
            print(f"❌ Only owner can archive document")
            return False
        
        self._status = DocumentStatus.ARCHIVED
        print(f"📦 Document archived")
        return True
    
    def delete(self, user: User) -> bool:
        """Delete document"""
        if not self._access_control.get_access_level(user.get_id()).can_manage_permissions():
            print(f"❌ Only owner can delete document")
            return False
        
        self._status = DocumentStatus.DELETED
        print(f"🗑️  Document deleted")
        return True
    
    # ==================== Search ====================
    
    def matches_search(self, query: str, search_content: bool = True) -> bool:
        """Check if document matches search query"""
        query_lower = query.lower()
        
        # Search in title
        if query_lower in self._title.lower():
            return True
        
        # Search in content if enabled
        if search_content and query_lower in self._content.lower():
            return True
        
        return False
    
    def get_search_snippet(self, query: str, context_length: int = 50) -> Optional[str]:
        """Get snippet of content around search query"""
        query_lower = query.lower()
        content_lower = self._content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            return None
        
        # Get context before and after
        start = max(0, pos - context_length)
        end = min(len(self._content), pos + len(query) + context_length)
        
        snippet = self._content[start:end]
        
        # Add ellipsis if needed
        if start > 0:
            snippet = "..." + snippet
        if end < len(self._content):
            snippet = snippet + "..."
        
        return snippet
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict:
        """Get document statistics"""
        return {
            'view_count': self._view_count,
            'edit_count': self._edit_count,
            'version_count': self._current_version,
            'comment_count': len(self._comments),
            'open_comments': len([c for c in self._comments.values() 
                                 if c.get_status() == CommentStatus.OPEN]),
            'active_editors': len(self._active_editors),
            'content_length': len(self._content),
            'word_count': len(self._content.split()),
            'created_at': self._created_at,
            'modified_at': self._modified_at
        }
    
    def to_dict(self) -> Dict:
        """Convert document to dictionary"""
        return {
            'document_id': self._document_id,
            'title': self._title,
            'owner': self._owner.to_dict(),
            'status': self._status.value,
            'content_preview': self._content[:100] + ('...' if len(self._content) > 100 else ''),
            'access_control': self._access_control.to_dict(),
            'statistics': self.get_statistics(),
            'created_at': self._created_at.isoformat(),
            'modified_at': self._modified_at.isoformat()
        }


# ==================== Document Repository ====================

class DocumentRepository:
    """
    Central repository for managing documents
    
    Features:
    - Create/delete documents
    - Search by filename/content
    - Access control management
    - Real-time collaboration support
    - Version history
    - Comments and discussions
    """
    
    def __init__(self, system_name: str = "CollabDocs"):
        self._system_name = system_name
        
        # Storage
        self._users: Dict[str, User] = {}
        self._documents: Dict[str, Document] = {}
        
        # Indexes for fast search
        self._documents_by_owner: Dict[str, Set[str]] = {}  # owner_id -> doc_ids
        self._documents_by_collaborator: Dict[str, Set[str]] = {}  # user_id -> doc_ids
        
        # Statistics
        self._total_documents_created = 0
        self._total_edits = 0
    
    # ==================== User Management ====================
    
    def register_user(self, name: str, email: str) -> User:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        user = User(user_id, name, email)
        
        self._users[user_id] = user
        self._documents_by_owner[user_id] = set()
        self._documents_by_collaborator[user_id] = set()
        
        print(f"✅ User registered: {name}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Document Management ====================
    
    def create_document(self, owner_id: str, title: str) -> Optional[Document]:
        """Create a new document"""
        owner = self._users.get(owner_id)
        if not owner:
            print(f"❌ User not found")
            return None
        
        document_id = str(uuid.uuid4())
        document = Document(document_id, title, owner)
        
        self._documents[document_id] = document
        self._documents_by_owner[owner_id].add(document_id)
        self._total_documents_created += 1
        
        print(f"📄 Document created: '{title}' by {owner.get_name()}")
        return document
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        return self._documents.get(document_id)
    
    def delete_document(self, document_id: str, user: User) -> bool:
        """Delete a document"""
        document = self._documents.get(document_id)
        if not document:
            return False
        
        if document.delete(user):
            # Remove from indexes
            self._documents_by_owner[document.get_owner().get_id()].discard(document_id)
            
            return True
        
        return False
    
    # ==================== Sharing ====================
    
    def share_document(self, document_id: str, sharer: User, 
                      user_id: str, access_level: AccessLevel) -> bool:
        """Share document with another user"""
        document = self._documents.get(document_id)
        if not document:
            print(f"❌ Document not found")
            return False
        
        if document.grant_access(sharer, user_id, access_level):
            # Update collaborator index
            self._documents_by_collaborator[user_id].add(document_id)
            return True
        
        return False
    
    def unshare_document(self, document_id: str, unsharer: User, user_id: str) -> bool:
        """Remove user's access to document"""
        document = self._documents.get(document_id)
        if not document:
            return False
        
        if document.revoke_access(unsharer, user_id):
            # Update collaborator index
            if user_id in self._documents_by_collaborator:
                self._documents_by_collaborator[user_id].discard(document_id)
            return True
        
        return False
    
    # ==================== Search ====================
    
    def search_documents(self, user: User, query: str, 
                        search_content: bool = True,
                        include_shared: bool = True) -> List[Tuple[Document, Optional[str]]]:
        """
        Search documents by filename or content
        
        Returns list of (document, snippet) tuples
        """
        results = []
        
        # Get documents user has access to
        accessible_docs = set()
        
        # Own documents
        accessible_docs.update(self._documents_by_owner.get(user.get_id(), set()))
        
        # Shared documents
        if include_shared:
            accessible_docs.update(self._documents_by_collaborator.get(user.get_id(), set()))
        
        # Public documents
        for doc_id, doc in self._documents.items():
            if doc.get_access_control().get_sharing_mode() == SharingMode.PUBLIC:
                accessible_docs.add(doc_id)
        
        # Search through accessible documents
        for doc_id in accessible_docs:
            doc = self._documents.get(doc_id)
            if not doc:
                continue
            
            # Skip deleted documents
            if doc.get_status() == DocumentStatus.DELETED:
                continue
            
            # Check if matches search
            if doc.matches_search(query, search_content):
                snippet = None
                
                # Get snippet if searching content
                if search_content:
                    snippet = doc.get_search_snippet(query)
                
                results.append((doc, snippet))
        
        print(f"🔍 Found {len(results)} documents matching '{query}'")
        return results
    
    def search_by_filename(self, user: User, query: str) -> List[Document]:
        """Search documents by filename only"""
        results = self.search_documents(user, query, search_content=False)
        return [doc for doc, _ in results]
    
    def search_by_content(self, user: User, query: str) -> List[Tuple[Document, str]]:
        """Search documents by content with snippets"""
        results = self.search_documents(user, query, search_content=True)
        return [(doc, snippet) for doc, snippet in results if snippet]
    
    # ==================== User's Documents ====================
    
    def get_user_documents(self, user_id: str, include_shared: bool = True) -> List[Document]:
        """Get all documents accessible by user"""
        user = self._users.get(user_id)
        if not user:
            return []
        
        doc_ids = set()
        
        # Own documents
        doc_ids.update(self._documents_by_owner.get(user_id, set()))
        
        # Shared documents
        if include_shared:
            doc_ids.update(self._documents_by_collaborator.get(user_id, set()))
        
        documents = []
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc and doc.get_status() == DocumentStatus.ACTIVE:
                documents.append(doc)
        
        # Sort by modified date (most recent first)
        documents.sort(key=lambda d: d._modified_at, reverse=True)
        
        return documents
    
    def get_owned_documents(self, user_id: str) -> List[Document]:
        """Get documents owned by user"""
        doc_ids = self._documents_by_owner.get(user_id, set())
        
        documents = []
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc and doc.get_status() == DocumentStatus.ACTIVE:
                documents.append(doc)
        
        documents.sort(key=lambda d: d._modified_at, reverse=True)
        return documents
    
    def get_shared_with_user(self, user_id: str) -> List[Document]:
        """Get documents shared with user"""
        doc_ids = self._documents_by_collaborator.get(user_id, set())
        
        documents = []
        for doc_id in doc_ids:
            doc = self._documents.get(doc_id)
            if doc and doc.get_status() == DocumentStatus.ACTIVE:
                documents.append(doc)
        
        documents.sort(key=lambda d: d._modified_at, reverse=True)
        return documents
    
    # ==================== Statistics ====================
    
    def get_system_statistics(self) -> Dict:
        """Get system-wide statistics"""
        active_docs = sum(1 for d in self._documents.values() 
                         if d.get_status() == DocumentStatus.ACTIVE)
        
        total_edits = sum(d._edit_count for d in self._documents.values())
        total_comments = sum(len(d._comments) for d in self._documents.values())
        
        return {
            'system_name': self._system_name,
            'total_users': len(self._users),
            'total_documents': len(self._documents),
            'active_documents': active_docs,
            'archived_documents': sum(1 for d in self._documents.values() 
                                     if d.get_status() == DocumentStatus.ARCHIVED),
            'deleted_documents': sum(1 for d in self._documents.values() 
                                    if d.get_status() == DocumentStatus.DELETED),
            'total_edits': total_edits,
            'total_comments': total_comments,
            'documents_created': self._total_documents_created
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_collaborative_docs():
    """Comprehensive demo of collaborative document system"""
    
    print_section("COLLABORATIVE DOCUMENT SYSTEM DEMO")
    
    repo = DocumentRepository("CollabDocs")
    
    # ==================== Register Users ====================
    print_section("1. Register Users")
    
    alice = repo.register_user("Alice Johnson", "alice@company.com")
    bob = repo.register_user("Bob Smith", "bob@company.com")
    charlie = repo.register_user("Charlie Brown", "charlie@company.com")
    diana = repo.register_user("Diana Prince", "diana@company.com")
    
    # ==================== Create Documents ====================
    print_section("2. Create Documents")
    
    # Alice creates documents
    doc1 = repo.create_document(alice.get_id(), "Project Proposal")
    doc2 = repo.create_document(alice.get_id(), "Meeting Notes - Q4 Planning")
    
    # Bob creates documents
    doc3 = repo.create_document(bob.get_id(), "Technical Specification")
    
    # Charlie creates document
    doc4 = repo.create_document(charlie.get_id(), "Budget Analysis 2024")
    
    # ==================== Edit Documents ====================
    print_section("3. Collaborative Editing")
    
    if doc1:
        # Alice edits her document
        print(f"\n📝 Alice editing '{doc1.get_title()}'...")
        doc1.insert(alice, 0, "Project Proposal: AI-Powered Analytics\n\n")
        doc1.insert(alice, len(doc1.get_content()), "Executive Summary:\n")
        doc1.insert(alice, len(doc1.get_content()), 
                   "This project aims to develop an AI-powered analytics platform...\n\n")
        
        # Share with Bob as editor
        print(f"\n🤝 Alice sharing document with Bob as EDITOR...")
        repo.share_document(doc1.get_id(), alice, bob.get_id(), AccessLevel.EDITOR)
        
        # Bob joins editing
        doc1.join_editing(bob)
        
        # Bob edits
        print(f"\n📝 Bob editing '{doc1.get_title()}'...")
        doc1.insert(bob, len(doc1.get_content()), "Technical Requirements:\n")
        doc1.insert(bob, len(doc1.get_content()), 
                   "1. Machine Learning Framework\n2. Data Pipeline\n3. Visualization Layer\n\n")
        
        # Share with Charlie as commenter
        print(f"\n🤝 Alice sharing document with Charlie as COMMENTER...")
        repo.share_document(doc1.get_id(), alice, charlie.get_id(), AccessLevel.COMMENTER)
        
        # Charlie adds comment
        print(f"\n💬 Charlie adding comment...")
        doc1.add_comment(charlie, "Great proposal! Can we add cost estimates?", 
                        position=50, length=20)
        
        # Share with Diana as viewer
        print(f"\n🤝 Alice sharing document with Diana as VIEWER...")
        repo.share_document(doc1.get_id(), alice, diana.get_id(), AccessLevel.VIEWER)
        
        # Diana views
        print(f"\n👁️  Diana viewing document...")
        content = doc1.view(diana)
        if content:
            print(f"   Content length: {len(content)} characters")
    
    # ==================== Version History ====================
    print_section("4. Version History")
    
    if doc1:
        print(f"\n📚 Version history for '{doc1.get_title()}':")
        versions = doc1.get_version_history(limit=5)
        
        for version in versions:
            ver_dict = version.to_dict()
            print(f"   Version {ver_dict['version']}:")
            print(f"   • Modified by: {ver_dict['modified_by']}")
            print(f"   • Time: {ver_dict['timestamp'][:19]}")
            print(f"   • Content length: {ver_dict['content_length']}")
    
    # ==================== Comments and Discussions ====================
    print_section("5. Comments and Discussions")
    
    if doc1:
        # Alice replies to Charlie's comment
        comments = doc1.get_comments()
        if comments:
            first_comment = comments[0]
            print(f"\n💬 Alice replying to Charlie's comment...")
            doc1.reply_to_comment(alice, first_comment.get_id(), 
                                 "Good point! I'll add that in the next section.")
        
        # Bob adds another comment
        print(f"\n💬 Bob adding comment...")
        comment2 = doc1.add_comment(bob, "Should we include timeline estimates?")
        
        # List all comments
        print(f"\n📋 All comments on '{doc1.get_title()}':")
        for comment in doc1.get_comments():
            comm_dict = comment.to_dict()
            print(f"   • {comm_dict['user']}: {comm_dict['content']}")
            print(f"     Status: {comm_dict['status']}, Replies: {comm_dict['replies']}")
        
        # Resolve comment
        if comment2:
            print(f"\n✅ Alice resolving Bob's comment...")
            doc1.resolve_comment(alice, comment2.get_id())
    
    # ==================== Access Control ====================
    print_section("6. Access Control Management")
    
    if doc1:
        print(f"\n🔐 Access control for '{doc1.get_title()}':")
        ac_dict = doc1.get_access_control().to_dict()
        print(f"   Sharing mode: {ac_dict['sharing_mode']}")
        print(f"   Link access level: {ac_dict['link_access_level']}")
        print(f"\n   Users with access:")
        for user_id, level in ac_dict['users'].items():
            user = repo.get_user(user_id)
            if user:
                print(f"   • {user.get_name()}: {level}")
        
        # Change sharing mode to public
        print(f"\n🌐 Alice making document public (view-only)...")
        doc1.set_sharing_mode(alice, SharingMode.PUBLIC, AccessLevel.VIEWER)
    
    # ==================== Search by Filename ====================
    print_section("7. Search by Filename")
    
    print(f"\n🔍 Bob searching for 'proposal'...")
    results = repo.search_by_filename(bob, "proposal")
    
    print(f"   Found {len(results)} documents:")
    for doc in results:
        print(f"   • {doc.get_title()} (by {doc.get_owner().get_name()})")
    
    # ==================== Search by Content ====================
    print_section("8. Search by Content")
    
    print(f"\n🔍 Charlie searching for 'analytics' in content...")
    results = repo.search_by_content(charlie, "analytics")
    
    print(f"   Found {len(results)} documents:")
    for doc, snippet in results:
        print(f"\n   📄 {doc.get_title()}:")
        print(f"      {snippet}")
    
    # ==================== User's Documents ====================
    print_section("9. User's Documents")
    
    print(f"\n📂 Alice's owned documents:")
    alice_docs = repo.get_owned_documents(alice.get_id())
    for doc in alice_docs:
        print(f"   • {doc.get_title()} (modified: {doc._modified_at.strftime('%Y-%m-%d %H:%M')})")
    
    print(f"\n📂 Bob's accessible documents (owned + shared):")
    bob_docs = repo.get_user_documents(bob.get_id())
    for doc in bob_docs:
        access_level = doc.get_access_control().get_access_level(bob.get_id())
        owner_mark = " [OWNER]" if doc.get_owner().get_id() == bob.get_id() else f" [{access_level.value}]"
        print(f"   • {doc.get_title()}{owner_mark}")
    
    print(f"\n📂 Documents shared with Charlie:")
    shared_docs = repo.get_shared_with_user(charlie.get_id())
    for doc in shared_docs:
        access_level = doc.get_access_control().get_access_level(charlie.get_id())
        print(f"   • {doc.get_title()} [{access_level.value}]")
    
    # ==================== Real-time Collaboration ====================
    print_section("10. Real-time Collaboration")
    
    if doc1:
        print(f"\n👥 Active editors on '{doc1.get_title()}':")
        active = doc1.get_active_editors()
        for user_id in active:
            user = repo.get_user(user_id)
            if user:
                print(f"   • {user.get_name()}")
        
        # Bob leaves
        doc1.leave_editing(bob)
    
    # ==================== Version Restore ====================
    print_section("11. Restore Previous Version")
    
    if doc1:
        print(f"\n⏮️  Alice restoring to version 2...")
        doc1.restore_version(alice, 2)
        
        print(f"\n   Current version: {doc1._current_version}")
        print(f"   Content preview: {doc1.get_content()[:100]}...")
    
    # ==================== Access Denied Scenarios ====================
    print_section("12. Access Control Tests")
    
    if doc1:
        # Diana tries to edit (should fail - viewer only)
        print(f"\n❌ Diana (viewer) trying to edit...")
        doc1.insert(diana, 0, "Unauthorized edit")
        
        # Charlie tries to edit (should fail - commenter only)
        print(f"\n❌ Charlie (commenter) trying to edit...")
        doc1.insert(charlie, 0, "Unauthorized edit")
        
        # Bob tries to change sharing (should fail - not owner)
        print(f"\n❌ Bob trying to change sharing mode...")
        doc1.set_sharing_mode(bob, SharingMode.PRIVATE)
    
    # ==================== Document Statistics ====================
    print_section("13. Document Statistics")
    
    if doc1:
        stats = doc1.get_statistics()
        
        print(f"\n📊 Statistics for '{doc1.get_title()}':")
        print(f"   Views: {stats['view_count']}")
        print(f"   Edits: {stats['edit_count']}")
        print(f"   Versions: {stats['version_count']}")
        print(f"   Comments: {stats['comment_count']} ({stats['open_comments']} open)")
        print(f"   Active editors: {stats['active_editors']}")
        print(f"   Content length: {stats['content_length']} chars")
        print(f"   Word count: {stats['word_count']}")
        print(f"   Created: {stats['created_at'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Modified: {stats['modified_at'].strftime('%Y-%m-%d %H:%M')}")
    
    # ==================== Revoke Access ====================
    print_section("14. Revoke Access")
    
    if doc1:
        print(f"\n🚫 Alice revoking Diana's access...")
        repo.unshare_document(doc1.get_id(), alice, diana.get_id())
        
        # Diana tries to view (should fail)
        print(f"\n❌ Diana trying to view after access revoked...")
        doc1.view(diana)
    
    # ==================== Archive Document ====================
    print_section("15. Archive Document")
    
    if doc3:
        print(f"\n📦 Bob archiving '{doc3.get_title()}'...")
        doc3.archive(bob)
    
    # ==================== System Statistics ====================
    print_section("16. System-Wide Statistics")
    
    sys_stats = repo.get_system_statistics()
    
    print(f"\n📊 {sys_stats['system_name']} Statistics:")
    print(f"   Total users: {sys_stats['total_users']}")
    print(f"   Total documents: {sys_stats['total_documents']}")
    print(f"   Active documents: {sys_stats['active_documents']}")
    print(f"   Archived documents: {sys_stats['archived_documents']}")
    print(f"   Deleted documents: {sys_stats['deleted_documents']}")
    print(f"   Total edits: {sys_stats['total_edits']}")
    print(f"   Total comments: {sys_stats['total_comments']}")
    
    # ==================== Document Details ====================
    print_section("17. Detailed Document Information")
    
    if doc1:
        doc_dict = doc1.to_dict()
        
        print(f"\n📄 Document: {doc_dict['title']}")
        print(f"   ID: {doc_dict['document_id'][:8]}...")
        print(f"   Owner: {doc_dict['owner']['name']}")
        print(f"   Status: {doc_dict['status']}")
        print(f"   Content preview: {doc_dict['content_preview']}")
        
        print(f"\n   Access Control:")
        ac = doc_dict['access_control']
        print(f"   • Sharing mode: {ac['sharing_mode']}")
        print(f"   • Link access: {ac['link_access_level']}")
        print(f"   • User count: {ac['user_count']}")
        
        print(f"\n   Statistics:")
        for key, value in doc_dict['statistics'].items():
            if key not in ['created_at', 'modified_at']:
                print(f"   • {key}: {value}")
    
    print_section("Demo Complete")
    print("\n✅ Collaborative Document System demo completed!")
    
    print("\n" + "="*70)
    print(" KEY FEATURES DEMONSTRATED")
    print("="*70)
    
    print("\n✅ Collaborative Editing:")
    print("   • Multiple users editing same document")
    print("   • Real-time operation tracking")
    print("   • Insert/Delete/Replace operations")
    print("   • Active editor tracking")
    
    print("\n✅ Access Control:")
    print("   • Four access levels: Owner, Editor, Commenter, Viewer")
    print("   • Granular permissions per user")
    print("   • Sharing modes: Private, Link-sharing, Public")
    print("   • Owner-only permission management")
    
    print("\n✅ Version History:")
    print("   • Complete version tracking")
    print("   • Operation-level history")
    print("   • Version restore capability")
    print("   • Who/when/what tracking")
    
    print("\n✅ Search Capabilities:")
    print("   • Search by filename")
    print("   • Search by content with snippets")
    print("   • Access-aware search (only accessible docs)")
    print("   • Context-based result preview")
    
    print("\n✅ Comments & Discussions:")
    print("   • Document-level comments")
    print("   • Position-based comments (on selections)")
    print("   • Threaded replies")
    print("   • Resolve/Reopen functionality")
    
    print("\n✅ Document Management:")
    print("   • Create/Archive/Delete")
    print("   • Title management")
    print("   • Status tracking")
    print("   • Ownership model")
    
    print("\n✅ User Experience:")
    print("   • User's documents (owned + shared)")
    print("   • Recently modified sorting")
    print("   • Statistics and metrics")
    print("   • Access denial with clear messages")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_collaborative_docs()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Key Design Decisions:
# 1. Core Components:
# Document: Content with version history, access control, comments
# Operation: Insert/Delete/Replace operations for editing
# Version: Immutable snapshot with operation history
# AccessControl: Per-document permission management
# Comment: Discussion threads with resolve/reopen
# 2. Access Levels (Hierarchical):
# 3. Sharing Modes:
# 4. Collaborative Editing:
# 5. Search Implementation:
# Filename Search:

# Case-insensitive title matching
# Fast lookup
# Content Search:

# Full-text search with context
# Snippet generation (50 chars before/after)
# Ellipsis for truncated content
# Access-aware (only searchable docs)
# Access Control in Search:

# 6. Version History:
# 7. Real-time Collaboration:
# 8. Comment System:
# 9. Design Patterns Used:
# Strategy Pattern: Different access levels with varying permissions

# Command Pattern: Operations (Insert/Delete/Replace)

# Memento Pattern: Version history for undo/restore

# Observer Pattern: Active editors tracking

# Repository Pattern: Document storage and search

# 10. Key Features:
# ✅ Collaborative Editing:

# Operation-based text manipulation
# Multiple simultaneous editors
# Automatic version creation
# Edit history tracking
# ✅ Access Control:

# Four-level permission hierarchy
# Per-user granular control
# Flexible sharing modes
# Owner-only admin operations
# ✅ Search:

# Filename search
# Content search with snippets
# Access-aware results
# Fast indexing
# ✅ Version History:

# Complete revision tracking
# Restore any version
# Operation-level detail
# Who/when/what audit trail
# ✅ Comments:

# Threaded discussions
# Position-based annotations
# Resolve/reopen workflow
# Reply support
# 11. Scalability Considerations:
# Implemented:

# Document indexing by owner/collaborator
# Version limit (can be configurable)
# Snippet generation (limited context)
# Access check caching opportunity
# Production Additions:

# Operational Transform (OT) for real-time sync
# Differential sync (not full content)
# Search indexing (Elasticsearch)
# Distributed storage
# WebSocket for real-time updates
# Conflict resolution algorithms
# Auto-save drafts
# 12. Comparison with Google Docs:
# Similarities: ✅ Multi-user editing ✅ Access levels (Owner/Editor/Commenter/Viewer) ✅ Version history ✅ Comments with resolve ✅ Search functionality ✅ Sharing controls

# Simplified (for LLD):

# No real-time cursor tracking
# Basic operational transform
# Simplified conflict resolution
# No formatting (plain text)
# No suggestions mode
# This is interview-ready Google Docs! 📝✨
