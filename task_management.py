from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, date, timedelta
from dataclasses import dataclass
import uuid


# ==================== Enums ====================

class TaskStatus(Enum):
    """Task status"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOWEST = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    HIGHEST = 5
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class TaskType(Enum):
    """Type of task"""
    STORY = "story"
    BUG = "bug"
    TASK = "task"
    EPIC = "epic"
    SUBTASK = "subtask"


class UserRole(Enum):
    """User roles"""
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    TESTER = "tester"
    VIEWER = "viewer"


class CommentType(Enum):
    """Comment types"""
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    ASSIGNMENT_CHANGE = "assignment_change"
    PRIORITY_CHANGE = "priority_change"


# ==================== Models ====================

class User:
    """User in the system"""
    
    def __init__(self, user_id: str, name: str, email: str, role: UserRole):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._role = role
        self._active = True
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def get_role(self) -> UserRole:
        return self._role
    
    def is_active(self) -> bool:
        return self._active
    
    def deactivate(self) -> None:
        self._active = False
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self._user_id,
            'name': self._name,
            'email': self._email,
            'role': self._role.value,
            'active': self._active
        }


class Comment:
    """Comment on a task"""
    
    def __init__(self, comment_id: str, author: User, text: str, 
                 comment_type: CommentType = CommentType.COMMENT):
        self._comment_id = comment_id
        self._author = author
        self._text = text
        self._comment_type = comment_type
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._deleted = False
    
    def get_id(self) -> str:
        return self._comment_id
    
    def get_author(self) -> User:
        return self._author
    
    def get_text(self) -> str:
        return self._text
    
    def update_text(self, text: str) -> None:
        self._text = text
        self._updated_at = datetime.now()
    
    def delete(self) -> None:
        self._deleted = True
    
    def is_deleted(self) -> bool:
        return self._deleted
    
    def to_dict(self) -> Dict:
        return {
            'comment_id': self._comment_id,
            'author': self._author.get_name(),
            'text': self._text,
            'type': self._comment_type.value,
            'created_at': self._created_at.isoformat(),
            'updated_at': self._updated_at.isoformat()
        }


class Attachment:
    """File attachment"""
    
    def __init__(self, attachment_id: str, filename: str, file_path: str,
                 uploaded_by: User, file_size: int):
        self._attachment_id = attachment_id
        self._filename = filename
        self._file_path = file_path
        self._uploaded_by = uploaded_by
        self._file_size = file_size
        self._uploaded_at = datetime.now()
    
    def get_id(self) -> str:
        return self._attachment_id
    
    def get_filename(self) -> str:
        return self._filename
    
    def get_file_path(self) -> str:
        return self._file_path
    
    def to_dict(self) -> Dict:
        return {
            'attachment_id': self._attachment_id,
            'filename': self._filename,
            'uploaded_by': self._uploaded_by.get_name(),
            'file_size': self._file_size,
            'uploaded_at': self._uploaded_at.isoformat()
        }


class Task:
    """Main task/issue"""
    
    def __init__(self, task_id: str, title: str, description: str,
                 task_type: TaskType, reporter: User, project_id: str):
        self._task_id = task_id
        self._title = title
        self._description = description
        self._task_type = task_type
        self._reporter = reporter
        self._project_id = project_id
        
        # Status and assignment
        self._status = TaskStatus.TODO
        self._assignee: Optional[User] = None
        self._priority = TaskPriority.MEDIUM
        
        # Relationships
        self._parent_task: Optional['Task'] = None
        self._subtasks: List['Task'] = []
        self._blocked_by: Set[str] = set()  # Task IDs
        self._blocks: Set[str] = set()  # Task IDs
        
        # Additional fields
        self._labels: Set[str] = set()
        self._sprint_id: Optional[str] = None
        self._story_points: Optional[int] = None
        self._due_date: Optional[datetime] = None
        
        # Activity
        self._comments: List[Comment] = []
        self._attachments: List[Attachment] = []
        self._watchers: Set[User] = set()
        
        # Audit
        self._created_at = datetime.now()
        self._updated_at = datetime.now()
        self._resolved_at: Optional[datetime] = None
        
        # Add reporter as watcher by default
        self._watchers.add(reporter)
    
    def get_id(self) -> str:
        return self._task_id
    
    def get_title(self) -> str:
        return self._title
    
    def get_description(self) -> str:
        return self._description
    
    def get_type(self) -> TaskType:
        return self._task_type
    
    def get_status(self) -> TaskStatus:
        return self._status
    
    def get_priority(self) -> TaskPriority:
        return self._priority
    
    def get_reporter(self) -> User:
        return self._reporter
    
    def get_assignee(self) -> Optional[User]:
        return self._assignee
    
    def get_project_id(self) -> str:
        return self._project_id
    
    def update_title(self, title: str) -> None:
        self._title = title
        self._updated_at = datetime.now()
    
    def update_description(self, description: str) -> None:
        self._description = description
        self._updated_at = datetime.now()
    
    def set_status(self, status: TaskStatus, changed_by: User) -> None:
        """Update task status"""
        old_status = self._status
        self._status = status
        self._updated_at = datetime.now()
        
        # Mark resolved time
        if status == TaskStatus.DONE and not self._resolved_at:
            self._resolved_at = datetime.now()
        
        # Add system comment
        comment = Comment(
            str(uuid.uuid4()),
            changed_by,
            f"Status changed from {old_status.value} to {status.value}",
            CommentType.STATUS_CHANGE
        )
        self._comments.append(comment)
    
    def set_priority(self, priority: TaskPriority, changed_by: User) -> None:
        """Update task priority"""
        old_priority = self._priority
        self._priority = priority
        self._updated_at = datetime.now()
        
        # Add system comment
        comment = Comment(
            str(uuid.uuid4()),
            changed_by,
            f"Priority changed from {old_priority.name} to {priority.name}",
            CommentType.PRIORITY_CHANGE
        )
        self._comments.append(comment)
    
    def assign_to(self, assignee: User, assigned_by: User) -> None:
        """Assign task to user"""
        old_assignee = self._assignee
        self._assignee = assignee
        self._updated_at = datetime.now()
        
        # Add assignee as watcher
        self._watchers.add(assignee)
        
        # Add system comment
        old_name = old_assignee.get_name() if old_assignee else "Unassigned"
        comment = Comment(
            str(uuid.uuid4()),
            assigned_by,
            f"Assignee changed from {old_name} to {assignee.get_name()}",
            CommentType.ASSIGNMENT_CHANGE
        )
        self._comments.append(comment)
    
    def unassign(self, unassigned_by: User) -> None:
        """Unassign task"""
        if self._assignee:
            old_assignee = self._assignee
            self._assignee = None
            self._updated_at = datetime.now()
            
            comment = Comment(
                str(uuid.uuid4()),
                unassigned_by,
                f"Unassigned from {old_assignee.get_name()}",
                CommentType.ASSIGNMENT_CHANGE
            )
            self._comments.append(comment)
    
    def set_due_date(self, due_date: datetime) -> None:
        self._due_date = due_date
        self._updated_at = datetime.now()
    
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if self._due_date and self._status != TaskStatus.DONE:
            return datetime.now() > self._due_date
        return False
    
    def add_label(self, label: str) -> None:
        self._labels.add(label)
        self._updated_at = datetime.now()
    
    def remove_label(self, label: str) -> None:
        self._labels.discard(label)
        self._updated_at = datetime.now()
    
    def get_labels(self) -> Set[str]:
        return self._labels.copy()
    
    def set_story_points(self, points: int) -> None:
        self._story_points = points
        self._updated_at = datetime.now()
    
    def get_story_points(self) -> Optional[int]:
        return self._story_points
    
    def set_sprint(self, sprint_id: str) -> None:
        self._sprint_id = sprint_id
        self._updated_at = datetime.now()
    
    def get_sprint_id(self) -> Optional[str]:
        return self._sprint_id
    
    # Subtask management
    def add_subtask(self, subtask: 'Task') -> None:
        """Add a subtask"""
        if subtask._task_type != TaskType.SUBTASK:
            raise ValueError("Only SUBTASK type can be added as subtask")
        
        if subtask in self._subtasks:
            return
        
        self._subtasks.append(subtask)
        subtask._parent_task = self
        self._updated_at = datetime.now()
    
    def remove_subtask(self, subtask: 'Task') -> bool:
        """Remove a subtask"""
        if subtask in self._subtasks:
            self._subtasks.remove(subtask)
            subtask._parent_task = None
            self._updated_at = datetime.now()
            return True
        return False
    
    def get_subtasks(self) -> List['Task']:
        return self._subtasks.copy()
    
    def get_parent_task(self) -> Optional['Task']:
        return self._parent_task
    
    def get_completion_percentage(self) -> float:
        """Calculate completion percentage based on subtasks"""
        if not self._subtasks:
            return 100.0 if self._status == TaskStatus.DONE else 0.0
        
        completed = sum(1 for subtask in self._subtasks 
                       if subtask.get_status() == TaskStatus.DONE)
        return (completed / len(self._subtasks)) * 100
    
    # Blocking relationships
    def add_blocker(self, task_id: str) -> None:
        """Add a task that blocks this task"""
        self._blocked_by.add(task_id)
        self._updated_at = datetime.now()
    
    def remove_blocker(self, task_id: str) -> None:
        """Remove a blocker"""
        self._blocked_by.discard(task_id)
        self._updated_at = datetime.now()
    
    def is_blocked(self) -> bool:
        return len(self._blocked_by) > 0
    
    def get_blockers(self) -> Set[str]:
        return self._blocked_by.copy()
    
    def add_blocks(self, task_id: str) -> None:
        """Add a task that this task blocks"""
        self._blocks.add(task_id)
        self._updated_at = datetime.now()
    
    def remove_blocks(self, task_id: str) -> None:
        self._blocks.discard(task_id)
        self._updated_at = datetime.now()
    
    # Comments
    def add_comment(self, author: User, text: str) -> Comment:
        """Add a comment"""
        comment = Comment(str(uuid.uuid4()), author, text)
        self._comments.append(comment)
        self._updated_at = datetime.now()
        return comment
    
    def get_comments(self) -> List[Comment]:
        """Get all non-deleted comments"""
        return [c for c in self._comments if not c.is_deleted()]
    
    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment"""
        for comment in self._comments:
            if comment.get_id() == comment_id:
                comment.delete()
                self._updated_at = datetime.now()
                return True
        return False
    
    # Attachments
    def add_attachment(self, filename: str, file_path: str, 
                      uploaded_by: User, file_size: int) -> Attachment:
        """Add an attachment"""
        attachment = Attachment(
            str(uuid.uuid4()),
            filename,
            file_path,
            uploaded_by,
            file_size
        )
        self._attachments.append(attachment)
        self._updated_at = datetime.now()
        return attachment
    
    def get_attachments(self) -> List[Attachment]:
        return self._attachments.copy()
    
    # Watchers
    def add_watcher(self, user: User) -> None:
        self._watchers.add(user)
    
    def remove_watcher(self, user: User) -> None:
        self._watchers.discard(user)
    
    def get_watchers(self) -> Set[User]:
        return self._watchers.copy()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'task_id': self._task_id,
            'title': self._title,
            'description': self._description,
            'type': self._task_type.value,
            'status': self._status.value,
            'priority': self._priority.name,
            'reporter': self._reporter.get_name(),
            'assignee': self._assignee.get_name() if self._assignee else None,
            'project_id': self._project_id,
            'parent_task': self._parent_task.get_id() if self._parent_task else None,
            'subtasks': len(self._subtasks),
            'completion_percentage': self.get_completion_percentage(),
            'labels': list(self._labels),
            'story_points': self._story_points,
            'sprint_id': self._sprint_id,
            'due_date': self._due_date.isoformat() if self._due_date else None,
            'is_overdue': self.is_overdue(),
            'is_blocked': self.is_blocked(),
            'blockers': list(self._blocked_by),
            'blocks': list(self._blocks),
            'comments_count': len(self.get_comments()),
            'attachments_count': len(self._attachments),
            'watchers_count': len(self._watchers),
            'created_at': self._created_at.isoformat(),
            'updated_at': self._updated_at.isoformat(),
            'resolved_at': self._resolved_at.isoformat() if self._resolved_at else None
        }


class Project:
    """Project containing tasks"""
    
    def __init__(self, project_id: str, name: str, key: str, owner: User):
        self._project_id = project_id
        self._name = name
        self._key = key.upper()  # e.g., "PROJ"
        self._owner = owner
        self._description = ""
        
        # Members
        self._members: Set[User] = set()
        self._members.add(owner)
        
        # Tasks
        self._tasks: Dict[str, Task] = {}
        self._task_counter = 1
        
        # Sprints
        self._sprints: Dict[str, 'Sprint'] = {}
        
        # Metadata
        self._created_at = datetime.now()
        self._active = True
    
    def get_id(self) -> str:
        return self._project_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_key(self) -> str:
        return self._key
    
    def get_owner(self) -> User:
        return self._owner
    
    def set_description(self, description: str) -> None:
        self._description = description
    
    def add_member(self, user: User) -> None:
        self._members.add(user)
    
    def remove_member(self, user: User) -> None:
        self._members.discard(user)
    
    def get_members(self) -> Set[User]:
        return self._members.copy()
    
    def is_member(self, user: User) -> bool:
        return user in self._members
    
    def generate_task_key(self) -> str:
        """Generate unique task key like PROJ-123"""
        key = f"{self._key}-{self._task_counter}"
        self._task_counter += 1
        return key
    
    def add_task(self, task: Task) -> None:
        """Add task to project"""
        self._tasks[task.get_id()] = task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    def remove_task(self, task_id: str) -> bool:
        """Remove task from project"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False
    
    def get_all_tasks(self) -> List[Task]:
        return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [task for task in self._tasks.values() 
                if task.get_status() == status]
    
    def get_tasks_by_assignee(self, assignee: User) -> List[Task]:
        return [task for task in self._tasks.values() 
                if task.get_assignee() == assignee]
    
    def get_tasks_by_sprint(self, sprint_id: str) -> List[Task]:
        return [task for task in self._tasks.values() 
                if task.get_sprint_id() == sprint_id]
    
    def add_sprint(self, sprint: 'Sprint') -> None:
        self._sprints[sprint.get_id()] = sprint
    
    def get_sprint(self, sprint_id: str) -> Optional['Sprint']:
        return self._sprints.get(sprint_id)
    
    def to_dict(self) -> Dict:
        return {
            'project_id': self._project_id,
            'name': self._name,
            'key': self._key,
            'owner': self._owner.get_name(),
            'description': self._description,
            'members_count': len(self._members),
            'tasks_count': len(self._tasks),
            'sprints_count': len(self._sprints),
            'active': self._active,
            'created_at': self._created_at.isoformat()
        }


class Sprint:
    """Sprint for agile planning"""
    
    def __init__(self, sprint_id: str, name: str, project_id: str,
                 start_date: datetime, end_date: datetime):
        self._sprint_id = sprint_id
        self._name = name
        self._project_id = project_id
        self._start_date = start_date
        self._end_date = end_date
        self._goal = ""
        self._active = False
        self._completed = False
    
    def get_id(self) -> str:
        return self._sprint_id
    
    def get_name(self) -> str:
        return self._name
    
    def set_goal(self, goal: str) -> None:
        self._goal = goal
    
    def start(self) -> None:
        self._active = True
    
    def complete(self) -> None:
        self._active = False
        self._completed = True
    
    def is_active(self) -> bool:
        return self._active
    
    def to_dict(self) -> Dict:
        return {
            'sprint_id': self._sprint_id,
            'name': self._name,
            'project_id': self._project_id,
            'start_date': self._start_date.isoformat(),
            'end_date': self._end_date.isoformat(),
            'goal': self._goal,
            'active': self._active,
            'completed': self._completed
        }


# ==================== Task Management System ====================

class TaskManagementSystem:
    """
    Main JIRA-like task management system
    
    Features:
    - Create/Update/Delete tasks
    - Add/Remove subtasks
    - Task assignment and status tracking
    - Comments and attachments
    - Blocking relationships
    - Sprint management
    - Project management
    - Search and filtering
    """
    
    def __init__(self):
        # Storage
        self._users: Dict[str, User] = {}
        self._projects: Dict[str, Project] = {}
        self._tasks: Dict[str, Task] = {}
        
        # Indexes
        self._tasks_by_key: Dict[str, str] = {}  # key -> task_id
        
        # Notifications (simplified)
        self._notifications: List[Dict] = []
    
    # ==================== User Management ====================
    
    def create_user(self, name: str, email: str, role: UserRole) -> User:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        user = User(user_id, name, email, role)
        self._users[user_id] = user
        
        print(f"✅ User created: {name} ({role.value})")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Project Management ====================
    
    def create_project(self, name: str, key: str, owner: User) -> Project:
        """Create a new project"""
        project_id = str(uuid.uuid4())
        project = Project(project_id, name, key, owner)
        self._projects[project_id] = project
        
        print(f"✅ Project created: {name} ({key})")
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)
    
    # ==================== Task Management ====================
    
    def create_task(self, project_id: str, title: str, description: str,
                   task_type: TaskType, reporter: User) -> Optional[Task]:
        """Create a new task"""
        project = self._projects.get(project_id)
        if not project:
            print(f"❌ Project not found: {project_id}")
            return None
        
        if not project.is_member(reporter):
            print(f"❌ User {reporter.get_name()} is not a member of project {project.get_name()}")
            return None
        
        task_id = str(uuid.uuid4())
        task_key = project.generate_task_key()
        
        task = Task(task_id, title, description, task_type, reporter, project_id)
        
        self._tasks[task_id] = task
        self._tasks_by_key[task_key] = task_id
        project.add_task(task)
        
        print(f"✅ Task created: {task_key} - {title}")
        self._notify_watchers(task, f"New task created: {task_key} - {title}")
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    def get_task_by_key(self, task_key: str) -> Optional[Task]:
        """Get task by key like PROJ-123"""
        task_id = self._tasks_by_key.get(task_key.upper())
        if task_id:
            return self._tasks.get(task_id)
        return None
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if 'title' in kwargs:
            task.update_title(kwargs['title'])
        
        if 'description' in kwargs:
            task.update_description(kwargs['description'])
        
        if 'status' in kwargs and 'changed_by' in kwargs:
            task.set_status(kwargs['status'], kwargs['changed_by'])
        
        if 'priority' in kwargs and 'changed_by' in kwargs:
            task.set_priority(kwargs['priority'], kwargs['changed_by'])
        
        if 'assignee' in kwargs and 'assigned_by' in kwargs:
            task.assign_to(kwargs['assignee'], kwargs['assigned_by'])
        
        if 'due_date' in kwargs:
            task.set_due_date(kwargs['due_date'])
        
        if 'story_points' in kwargs:
            task.set_story_points(kwargs['story_points'])
        
        print(f"✅ Task updated: {task.get_id()}")
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        # Remove from project
        project = self._projects.get(task.get_project_id())
        if project:
            project.remove_task(task_id)
        
        # Remove subtasks if any
        for subtask in task.get_subtasks():
            self.delete_task(subtask.get_id())
        
        # Remove from parent if it's a subtask
        parent = task.get_parent_task()
        if parent:
            parent.remove_subtask(task)
        
        # Remove task key mapping
        for key, tid in list(self._tasks_by_key.items()):
            if tid == task_id:
                del self._tasks_by_key[key]
                break
        
        # Remove task
        del self._tasks[task_id]
        
        print(f"🗑️  Task deleted: {task_id}")
        return True
    
    # ==================== Subtask Management ====================
    
    def create_subtask(self, parent_task_id: str, title: str, description: str,
                      reporter: User) -> Optional[Task]:
        """Create a subtask"""
        parent_task = self._tasks.get(parent_task_id)
        if not parent_task:
            print(f"❌ Parent task not found: {parent_task_id}")
            return None
        
        # Create subtask
        subtask = self.create_task(
            parent_task.get_project_id(),
            title,
            description,
            TaskType.SUBTASK,
            reporter
        )
        
        if subtask:
            parent_task.add_subtask(subtask)
            print(f"✅ Subtask added to {parent_task_id}")
        
        return subtask
    
    def remove_subtask(self, parent_task_id: str, subtask_id: str) -> bool:
        """Remove a subtask from parent"""
        parent_task = self._tasks.get(parent_task_id)
        subtask = self._tasks.get(subtask_id)
        
        if not parent_task or not subtask:
            return False
        
        if parent_task.remove_subtask(subtask):
            print(f"✅ Subtask removed from {parent_task_id}")
            return True
        
        return False
    
    # ==================== Assignment ====================
    
    def assign_task(self, task_id: str, assignee: User, assigned_by: User) -> bool:
        """Assign task to user"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.assign_to(assignee, assigned_by)
        self._notify_user(assignee, f"You have been assigned to task: {task.get_title()}")
        
        print(f"✅ Task {task_id} assigned to {assignee.get_name()}")
        return True
    
    def unassign_task(self, task_id: str, unassigned_by: User) -> bool:
        """Unassign task"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.unassign(unassigned_by)
        print(f"✅ Task {task_id} unassigned")
        return True
    
    # ==================== Status Management ====================
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          changed_by: User) -> bool:
        """Update task status"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        task.set_status(status, changed_by)
        self._notify_watchers(task, f"Task status changed to {status.value}")
        
        print(f"✅ Task {task_id} status updated to {status.value}")
        return True
    
    # ==================== Blocking Relationships ====================
    
    def add_blocker(self, blocked_task_id: str, blocker_task_id: str) -> bool:
        """Add blocking relationship"""
        blocked_task = self._tasks.get(blocked_task_id)
        blocker_task = self._tasks.get(blocker_task_id)
        
        if not blocked_task or not blocker_task:
            return False
        
        blocked_task.add_blocker(blocker_task_id)
        blocker_task.add_blocks(blocked_task_id)
        
        print(f"✅ {blocker_task_id} blocks {blocked_task_id}")
        return True
    
    def remove_blocker(self, blocked_task_id: str, blocker_task_id: str) -> bool:
        """Remove blocking relationship"""
        blocked_task = self._tasks.get(blocked_task_id)
        blocker_task = self._tasks.get(blocker_task_id)
        
        if not blocked_task or not blocker_task:
            return False
        
        blocked_task.remove_blocker(blocker_task_id)
        blocker_task.remove_blocks(blocked_task_id)
        
        print(f"✅ Blocker relationship removed")
        return True
    
    # ==================== Comments ====================
    
    def add_comment(self, task_id: str, author: User, text: str) -> Optional[Comment]:
        """Add comment to task"""
        task = self._tasks.get(task_id)
        if not task:
            return None
        
        comment = task.add_comment(author, text)
        self._notify_watchers(task, f"{author.get_name()} commented on task")
        
        print(f"💬 Comment added to task {task_id}")
        return comment
    
    # ==================== Sprint Management ====================
    
    def create_sprint(self, project_id: str, name: str,
                     start_date: datetime, end_date: datetime) -> Optional[Sprint]:
        """Create a sprint"""
        project = self._projects.get(project_id)
        if not project:
            return None
        
        sprint_id = str(uuid.uuid4())
        sprint = Sprint(sprint_id, name, project_id, start_date, end_date)
        project.add_sprint(sprint)
        
        print(f"✅ Sprint created: {name}")
        return sprint
    
    def add_task_to_sprint(self, task_id: str, sprint_id: str) -> bool:
        """Add task to sprint"""
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        project = self._projects.get(task.get_project_id())
        if not project:
            return False
        
        sprint = project.get_sprint(sprint_id)
        if not sprint:
            return False
        
        task.set_sprint(sprint_id)
        print(f"✅ Task {task_id} added to sprint {sprint.get_name()}")
        return True
    
    # ==================== Search and Filter ====================
    
    def search_tasks(self, **filters) -> List[Task]:
        """Search tasks with filters"""
        results = list(self._tasks.values())
        
        if 'project_id' in filters:
            results = [t for t in results if t.get_project_id() == filters['project_id']]
        
        if 'status' in filters:
            results = [t for t in results if t.get_status() == filters['status']]
        
        if 'assignee' in filters:
            results = [t for t in results if t.get_assignee() == filters['assignee']]
        
        if 'priority' in filters:
            results = [t for t in results if t.get_priority() == filters['priority']]
        
        if 'task_type' in filters:
            results = [t for t in results if t.get_type() == filters['task_type']]
        
        if 'sprint_id' in filters:
            results = [t for t in results if t.get_sprint_id() == filters['sprint_id']]
        
        if 'label' in filters:
            results = [t for t in results if filters['label'] in t.get_labels()]
        
        if 'overdue' in filters and filters['overdue']:
            results = [t for t in results if t.is_overdue()]
        
        if 'blocked' in filters and filters['blocked']:
            results = [t for t in results if t.is_blocked()]
        
        return results
    
    def get_my_tasks(self, user: User) -> List[Task]:
        """Get tasks assigned to user"""
        return [task for task in self._tasks.values() 
                if task.get_assignee() == user]
    
    def get_reported_tasks(self, user: User) -> List[Task]:
        """Get tasks reported by user"""
        return [task for task in self._tasks.values() 
                if task.get_reporter() == user]
    
    def get_watching_tasks(self, user: User) -> List[Task]:
        """Get tasks user is watching"""
        return [task for task in self._tasks.values() 
                if user in task.get_watchers()]
    
    # ==================== Notifications (Simplified) ====================
    
    def _notify_watchers(self, task: Task, message: str) -> None:
        """Notify all watchers of a task"""
        for watcher in task.get_watchers():
            self._notify_user(watcher, message)
    
    def _notify_user(self, user: User, message: str) -> None:
        """Send notification to user"""
        notification = {
            'user_id': user.get_id(),
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        self._notifications.append(notification)
    
    # ==================== Statistics ====================
    
    def get_project_statistics(self, project_id: str) -> Optional[Dict]:
        """Get project statistics"""
        project = self._projects.get(project_id)
        if not project:
            return None
        
        tasks = project.get_all_tasks()
        
        status_breakdown = {}
        for status in TaskStatus:
            status_breakdown[status.value] = len(
                [t for t in tasks if t.get_status() == status]
            )
        
        type_breakdown = {}
        for task_type in TaskType:
            type_breakdown[task_type.value] = len(
                [t for t in tasks if t.get_type() == task_type]
            )
        
        return {
            'project_name': project.get_name(),
            'total_tasks': len(tasks),
            'status_breakdown': status_breakdown,
            'type_breakdown': type_breakdown,
            'overdue_tasks': len([t for t in tasks if t.is_overdue()]),
            'blocked_tasks': len([t for t in tasks if t.is_blocked()]),
            'total_story_points': sum(
                t.get_story_points() or 0 for t in tasks
            )
        }
    
    def get_sprint_statistics(self, project_id: str, sprint_id: str) -> Optional[Dict]:
        """Get sprint statistics"""
        project = self._projects.get(project_id)
        if not project:
            return None
        
        sprint = project.get_sprint(sprint_id)
        if not sprint:
            return None
        
        sprint_tasks = project.get_tasks_by_sprint(sprint_id)
        
        completed = len([t for t in sprint_tasks if t.get_status() == TaskStatus.DONE])
        total_points = sum(t.get_story_points() or 0 for t in sprint_tasks)
        completed_points = sum(
            t.get_story_points() or 0 for t in sprint_tasks 
            if t.get_status() == TaskStatus.DONE
        )
        
        return {
            'sprint_name': sprint.get_name(),
            'total_tasks': len(sprint_tasks),
            'completed_tasks': completed,
            'completion_rate': (completed / len(sprint_tasks) * 100) if sprint_tasks else 0,
            'total_story_points': total_points,
            'completed_story_points': completed_points,
            'velocity': completed_points if sprint.is_active() else 0
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_task_management_system():
    """Comprehensive demo of task management system"""
    
    print_section("TASK MANAGEMENT SYSTEM (JIRA-LIKE) DEMO")
    
    system = TaskManagementSystem()
    
    # ==================== Create Users ====================
    print_section("1. Create Users")
    
    admin = system.create_user("Alice Admin", "alice@company.com", UserRole.ADMIN)
    pm = system.create_user("Bob PM", "bob@company.com", UserRole.PROJECT_MANAGER)
    dev1 = system.create_user("Charlie Dev", "charlie@company.com", UserRole.DEVELOPER)
    dev2 = system.create_user("Diana Dev", "diana@company.com", UserRole.DEVELOPER)
    tester = system.create_user("Eve Tester", "eve@company.com", UserRole.TESTER)
    
    # ==================== Create Project ====================
    print_section("2. Create Project")
    
    project = system.create_project("E-Commerce Platform", "ECOM", pm)
    project.set_description("Main e-commerce platform development")
    
    # Add members
    project.add_member(dev1)
    project.add_member(dev2)
    project.add_member(tester)
    
    print(f"\n📋 Project: {project.get_name()}")
    print(f"   Key: {project.get_key()}")
    print(f"   Members: {len(project.get_members())}")
    
    # ==================== Create Sprint ====================
    print_section("3. Create Sprint")
    
    sprint_start = datetime.now()
    sprint_end = datetime.now() + timedelta(days=14)
    sprint = system.create_sprint(
        project.get_id(),
        "Sprint 1 - Core Features",
        sprint_start,
        sprint_end
    )
    sprint.set_goal("Implement user authentication and product catalog")
    sprint.start()
    
    print(f"\n🏃 Sprint: {sprint.get_name()}")
    print(f"   Duration: {sprint_start.date()} to {sprint_end.date()}")
    print(f"   Goal: {sprint._goal}")
    
    # ==================== Create Tasks ====================
    print_section("4. Create Tasks")
    
    # Story 1: User Authentication
    story1 = system.create_task(
        project.get_id(),
        "Implement User Authentication",
        "As a user, I want to login and register so that I can access my account",
        TaskType.STORY,
        pm
    )
    story1.set_story_points(8)
    story1.add_label("authentication")
    story1.add_label("backend")
    system.add_task_to_sprint(story1.get_id(), sprint.get_id())
    
    # Story 2: Product Catalog
    story2 = system.create_task(
        project.get_id(),
        "Build Product Catalog",
        "As a user, I want to browse products so that I can find what I need",
        TaskType.STORY,
        pm
    )
    story2.set_story_points(13)
    story2.add_label("frontend")
    story2.add_label("backend")
    system.add_task_to_sprint(story2.get_id(), sprint.get_id())
    
    # Bug
    bug1 = system.create_task(
        project.get_id(),
        "Login button not responsive on mobile",
        "The login button doesn't work on iOS Safari",
        TaskType.BUG,
        tester
    )
    system.update_task(bug1.get_id(), priority=TaskPriority.HIGH, changed_by=pm)
    bug1.add_label("mobile")
    bug1.add_label("urgent")
    
    # Epic
    epic1 = system.create_task(
        project.get_id(),
        "Payment Integration",
        "Integrate payment gateway for checkout process",
        TaskType.EPIC,
        pm
    )
    epic1.set_story_points(21)
    
    print(f"\n✅ Created {len(system._tasks)} tasks")
    
    # ==================== Create Subtasks ====================
    print_section("5. Create Subtasks")
    
    # Subtasks for Story 1
    subtask1 = system.create_subtask(
        story1.get_id(),
        "Create User Registration API",
        "Implement REST API endpoint for user registration",
        dev1
    )
    subtask1.set_story_points(3)
    
    subtask2 = system.create_subtask(
        story1.get_id(),
        "Create Login API",
        "Implement REST API endpoint for user login with JWT",
        dev1
    )
    subtask2.set_story_points(3)
    
    subtask3 = system.create_subtask(
        story1.get_id(),
        "Build Login UI",
        "Create responsive login form with validation",
        dev2
    )
    subtask3.set_story_points(2)
    
    # Subtasks for Story 2
    subtask4 = system.create_subtask(
        story2.get_id(),
        "Create Product API",
        "Implement product CRUD APIs",
        dev1
    )
    
    subtask5 = system.create_subtask(
        story2.get_id(),
        "Build Product Listing UI",
        "Create product grid with filters",
        dev2
    )
    
    print(f"\n📌 Story 1 subtasks: {len(story1.get_subtasks())}")
    for subtask in story1.get_subtasks():
        print(f"   • {subtask.get_title()}")
    
    print(f"\n📌 Story 2 subtasks: {len(story2.get_subtasks())}")
    for subtask in story2.get_subtasks():
        print(f"   • {subtask.get_title()}")
    
    # ==================== Assign Tasks ====================
    print_section("6. Assign Tasks")
    
    system.assign_task(story1.get_id(), dev1, pm)
    system.assign_task(story2.get_id(), dev2, pm)
    system.assign_task(bug1.get_id(), dev2, pm)
    
    system.assign_task(subtask1.get_id(), dev1, pm)
    system.assign_task(subtask2.get_id(), dev1, pm)
    system.assign_task(subtask3.get_id(), dev2, pm)
    system.assign_task(subtask4.get_id(), dev1, pm)
    system.assign_task(subtask5.get_id(), dev2, pm)
    
    # ==================== Update Task Status ====================
    print_section("7. Update Task Status")
    
    # Start working on subtasks
    system.update_task_status(subtask1.get_id(), TaskStatus.IN_PROGRESS, dev1)
    system.update_task_status(subtask2.get_id(), TaskStatus.IN_PROGRESS, dev1)
    
    # Complete some subtasks
    system.update_task_status(subtask1.get_id(), TaskStatus.DONE, dev1)
    system.update_task_status(subtask3.get_id(), TaskStatus.IN_PROGRESS, dev2)
    system.update_task_status(subtask3.get_id(), TaskStatus.DONE, dev2)
    
    print(f"\n📊 Story 1 Progress: {story1.get_completion_percentage():.1f}%")
    
    # ==================== Add Blocking Relationships ====================
    print_section("8. Add Blocking Relationships")
    
    # Story 2 is blocked by Story 1
    system.add_blocker(story2.get_id(), story1.get_id())
    
    print(f"\n🚧 Story 2 blocked by: {story2.get_blockers()}")
    print(f"   Story 1 blocks: {story1._blocks}")
    
    # ==================== Add Comments ====================
    print_section("9. Add Comments")
    
    system.add_comment(
        story1.get_id(),
        dev1,
        "Registration API is complete. Moving to login API now."
    )
    
    system.add_comment(
        story1.get_id(),
        pm,
        "@charlie Great work! Please ensure proper validation is in place."
    )
    
    system.add_comment(
        bug1.get_id(),
        dev2,
        "Investigating the issue. Seems to be a CSS problem with touch events."
    )
    
    print(f"\n💬 Story 1 comments: {len(story1.get_comments())}")
    for comment in story1.get_comments():
        print(f"   {comment.get_author().get_name()}: {comment.get_text()}")
    
    # ==================== Add Attachments ====================
    print_section("10. Add Attachments")
    
    story1.add_attachment(
        "auth-flow-diagram.png",
        "/uploads/auth-flow-diagram.png",
        dev1,
        245678
    )
    
    bug1.add_attachment(
        "screenshot-ios.png",
        "/uploads/screenshot-ios.png",
        tester,
        125432
    )
    
    print(f"\n📎 Story 1 attachments: {len(story1.get_attachments())}")
    for attachment in story1.get_attachments():
        print(f"   • {attachment.get_filename()} ({attachment._file_size} bytes)")
    
    # ==================== Search Tasks ====================
    print_section("11. Search and Filter Tasks")
    
    # Find all tasks in progress
    in_progress_tasks = system.search_tasks(status=TaskStatus.IN_PROGRESS)
    print(f"\n🔍 Tasks IN_PROGRESS: {len(in_progress_tasks)}")
    for task in in_progress_tasks:
        print(f"   • {task.get_title()} (assigned to {task.get_assignee().get_name()})")
    
    # Find high priority tasks
    high_priority_tasks = system.search_tasks(priority=TaskPriority.HIGH)
    print(f"\n🔍 High Priority Tasks: {len(high_priority_tasks)}")
    for task in high_priority_tasks:
        print(f"   • {task.get_title()}")
    
    # Find blocked tasks
    blocked_tasks = system.search_tasks(blocked=True)
    print(f"\n🔍 Blocked Tasks: {len(blocked_tasks)}")
    for task in blocked_tasks:
        print(f"   • {task.get_title()}")
    
    # Find tasks by label
    backend_tasks = system.search_tasks(label="backend")
    print(f"\n🔍 Backend Tasks: {len(backend_tasks)}")
    for task in backend_tasks:
        print(f"   • {task.get_title()}")
    
    # ==================== My Tasks ====================
    print_section("12. User's Tasks")
    
    charlie_tasks = system.get_my_tasks(dev1)
    print(f"\n👤 Charlie's assigned tasks: {len(charlie_tasks)}")
    for task in charlie_tasks:
        print(f"   • {task.get_title()} - {task.get_status().value}")
    
    diana_tasks = system.get_my_tasks(dev2)
    print(f"\n👤 Diana's assigned tasks: {len(diana_tasks)}")
    for task in diana_tasks:
        print(f"   • {task.get_title()} - {task.get_status().value}")
    
    # ==================== Remove Subtask ====================
    print_section("13. Remove Subtask")
    
    print(f"\n📌 Story 2 subtasks before removal: {len(story2.get_subtasks())}")
    
    system.remove_subtask(story2.get_id(), subtask5.get_id())
    
    print(f"📌 Story 2 subtasks after removal: {len(story2.get_subtasks())}")
    
    # ==================== Project Statistics ====================
    print_section("14. Project Statistics")
    
    project_stats = system.get_project_statistics(project.get_id())
    
    print(f"\n📊 {project_stats['project_name']} Statistics:")
    print(f"   Total Tasks: {project_stats['total_tasks']}")
    print(f"\n   Status Breakdown:")
    for status, count in project_stats['status_breakdown'].items():
        if count > 0:
            print(f"      • {status}: {count}")
    
    print(f"\n   Type Breakdown:")
    for task_type, count in project_stats['type_breakdown'].items():
        if count > 0:
            print(f"      • {task_type}: {count}")
    
    print(f"\n   Other Metrics:")
    print(f"      • Overdue Tasks: {project_stats['overdue_tasks']}")
    print(f"      • Blocked Tasks: {project_stats['blocked_tasks']}")
    print(f"      • Total Story Points: {project_stats['total_story_points']}")
    
    # ==================== Sprint Statistics ====================
    print_section("15. Sprint Statistics")
    
    sprint_stats = system.get_sprint_statistics(project.get_id(), sprint.get_id())
    
    print(f"\n📊 {sprint_stats['sprint_name']} Statistics:")
    print(f"   Total Tasks: {sprint_stats['total_tasks']}")
    print(f"   Completed Tasks: {sprint_stats['completed_tasks']}")
    print(f"   Completion Rate: {sprint_stats['completion_rate']:.1f}%")
    print(f"   Total Story Points: {sprint_stats['total_story_points']}")
    print(f"   Completed Story Points: {sprint_stats['completed_story_points']}")
    print(f"   Velocity: {sprint_stats['velocity']}")
    
    # ==================== Task Details ====================
    print_section("16. Detailed Task View")
    
    print(f"\n📋 Task Details: {story1.get_title()}")
    task_dict = story1.to_dict()
    
    print(f"   Task ID: {task_dict['task_id']}")
    print(f"   Type: {task_dict['type']}")
    print(f"   Status: {task_dict['status']}")
    print(f"   Priority: {task_dict['priority']}")
    print(f"   Reporter: {task_dict['reporter']}")
    print(f"   Assignee: {task_dict['assignee']}")
    print(f"   Story Points: {task_dict['story_points']}")
    print(f"   Labels: {', '.join(task_dict['labels'])}")
    print(f"   Subtasks: {task_dict['subtasks']}")
    print(f"   Completion: {task_dict['completion_percentage']:.1f}%")
    print(f"   Comments: {task_dict['comments_count']}")
    print(f"   Attachments: {task_dict['attachments_count']}")
    print(f"   Watchers: {task_dict['watchers_count']}")
    print(f"   Is Blocked: {task_dict['is_blocked']}")
    print(f"   Created: {task_dict['created_at'][:10]}")
    
    # ==================== Delete Task ====================
    print_section("17. Delete Task")
    
    print(f"\n🗑️  Deleting bug task...")
    system.delete_task(bug1.get_id())
    
    print(f"   Remaining tasks: {len(system._tasks)}")
    
    # ==================== System Summary ====================
    print_section("18. System Summary")
    
    print(f"\n📊 Task Management System Statistics:")
    print(f"   Total Users: {len(system._users)}")
    print(f"   Total Projects: {len(system._projects)}")
    print(f"   Total Tasks: {len(system._tasks)}")
    
    print(f"\n   User Roles:")
    role_counts = {}
    for user in system._users.values():
        role = user.get_role().value
        role_counts[role] = role_counts.get(role, 0) + 1
    
    for role, count in role_counts.items():
        print(f"      • {role}: {count}")
    
    print(f"\n   Task Types:")
    type_counts = {}
    for task in system._tasks.values():
        task_type = task.get_type().value
        type_counts[task_type] = type_counts.get(task_type, 0) + 1
    
    for task_type, count in type_counts.items():
        print(f"      • {task_type}: {count}")
    
    print(f"\n   Total Notifications: {len(system._notifications)}")
    
    print_section("Demo Complete")
    print("\n✅ Task Management System (JIRA-like) demo completed!")
    print("\n🎯 Key Features Demonstrated:")
    print("   ✅ Project and Sprint management")
    print("   ✅ Task creation with types (Story, Bug, Epic, Subtask)")
    print("   ✅ Subtask management (add/remove)")
    print("   ✅ Task assignment and status tracking")
    print("   ✅ Priority management")
    print("   ✅ Blocking relationships")
    print("   ✅ Comments and attachments")
    print("   ✅ Labels and categorization")
    print("   ✅ Story points and estimation")
    print("   ✅ Search and filtering")
    print("   ✅ Watchers and notifications")
    print("   ✅ Project and sprint statistics")
    print("   ✅ User role management")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_task_management_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Task Management System (JIRA-like) - Low Level Design
# Here's a comprehensive task management system inspired by JIRA:

# Key Design Decisions:
# 1. Core Components:
# Task: Main work item with subtasks support
# Project: Container for tasks
# Sprint: Agile sprint management
# User: System users with roles
# Comment: Task comments with types
# Attachment: File attachments
# 2. Task Types:
# 3. Task Status Flow:
# 4. Key Features:
# Task Management:

# ✅ Create/Update/Delete tasks
# ✅ Add/Remove subtasks
# ✅ Task hierarchy (parent-child)
# ✅ Completion percentage tracking
# Assignment & Workflow:

# ✅ Assign/Unassign tasks
# ✅ Status transitions
# ✅ Priority management
# ✅ Due date tracking
# Relationships:

# ✅ Blocking relationships (task blocks/blocked by)
# ✅ Parent-child (subtasks)
# ✅ Labels and categorization
# Collaboration:

# ✅ Comments with types
# ✅ File attachments
# ✅ Watchers and notifications
# ✅ Activity tracking
# Agile Features:

# ✅ Sprint management
# ✅ Story points
# ✅ Velocity tracking
# ✅ Burndown data
# 5. Design Patterns:
# Composite Pattern: Task with subtasks Observer Pattern: Watchers and notifications Strategy Pattern: Different comment types Builder Pattern: Task creation Repository Pattern: Task storage and retrieval

# 6. Search & Filter:
# 7. Subtask Management:
# 8. Task Hierarchy:
# 9. Blocking Relationships:
# 10. Statistics & Reporting:
# Project statistics (status breakdown, types)
# Sprint statistics (velocity, completion)
# User workload
# Overdue tasks
# Blocked tasks
# 11. Notification System:
# Notify watchers on updates
# Notify assignee on assignment
# Status change notifications
# Comment notifications
