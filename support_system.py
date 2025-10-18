from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import deque
import uuid
import random


# ==================== Enums ====================

class AgentLevel(Enum):
    """Support agent levels"""
    L1 = 1
    L2 = 2
    SUPERVISOR = 3
    
    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
    
    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented
    
    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented
    
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented


class AgentStatus(Enum):
    """Agent availability status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class ChatStatus(Enum):
    """Chat session status"""
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    ABANDONED = "abandoned"


class ChatPriority(Enum):
    """Chat priority levels"""
    NORMAL = 1
    PREEMPTED = 2  # User requested supervisor directly


class PriorityMode(Enum):
    """Admin-controlled priority mode"""
    PREEMPTED_FIRST = "preempted_first"  # Preempted users get supervisor first
    NORMAL_FIRST = "normal_first"        # Normal queue gets supervisor first


class MessageType(Enum):
    """Message types"""
    TEXT = "text"
    SYSTEM = "system"
    ESCALATION_REQUEST = "escalation_request"


# ==================== Models ====================

class User:
    """User requesting support"""
    
    def __init__(self, user_id: str, name: str, email: str):
        self._user_id = user_id
        self._name = name
        self._email = email
    
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


class Message:
    """Chat message"""
    
    def __init__(self, sender: str, content: str, 
                 message_type: MessageType = MessageType.TEXT):
        self._message_id = str(uuid.uuid4())
        self._sender = sender
        self._content = content
        self._message_type = message_type
        self._timestamp = datetime.now()
    
    def get_id(self) -> str:
        return self._message_id
    
    def get_sender(self) -> str:
        return self._sender
    
    def get_content(self) -> str:
        return self._content
    
    def get_timestamp(self) -> datetime:
        return self._timestamp
    
    def to_dict(self) -> Dict:
        return {
            'message_id': self._message_id,
            'sender': self._sender,
            'content': self._content,
            'type': self._message_type.value,
            'timestamp': self._timestamp.isoformat()
        }


class SupportAgent:
    """Support agent (L1/L2/Supervisor)"""
    
    def __init__(self, agent_id: str, name: str, level: AgentLevel):
        self._agent_id = agent_id
        self._name = name
        self._level = level
        self._status = AgentStatus.AVAILABLE
        self._current_chat: Optional['ChatSession'] = None
        
        # Statistics
        self._total_chats_handled = 0
        self._total_ratings = 0
        self._rating_count = 0
        self._average_rating = 0.0
        
        # Timestamps
        self._last_status_change = datetime.now()
    
    def get_id(self) -> str:
        return self._agent_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_level(self) -> AgentLevel:
        return self._level
    
    def get_status(self) -> AgentStatus:
        return self._status
    
    def is_available(self) -> bool:
        return self._status == AgentStatus.AVAILABLE
    
    def assign_chat(self, chat: 'ChatSession') -> bool:
        """Assign a chat to this agent"""
        if not self.is_available():
            return False
        
        self._current_chat = chat
        self._status = AgentStatus.BUSY
        self._last_status_change = datetime.now()
        
        return True
    
    def release_chat(self) -> None:
        """Release current chat and become available"""
        self._current_chat = None
        self._status = AgentStatus.AVAILABLE
        self._last_status_change = datetime.now()
        self._total_chats_handled += 1
    
    def get_current_chat(self) -> Optional['ChatSession']:
        return self._current_chat
    
    def add_rating(self, rating: int) -> None:
        """Add a rating from user feedback"""
        if 1 <= rating <= 5:
            self._total_ratings += rating
            self._rating_count += 1
            self._average_rating = self._total_ratings / self._rating_count
    
    def get_average_rating(self) -> float:
        return self._average_rating
    
    def set_offline(self) -> None:
        self._status = AgentStatus.OFFLINE
        self._last_status_change = datetime.now()
    
    def set_available(self) -> None:
        if self._current_chat is None:
            self._status = AgentStatus.AVAILABLE
            self._last_status_change = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self._agent_id,
            'name': self._name,
            'level': self._level.name,
            'status': self._status.value,
            'total_chats': self._total_chats_handled,
            'average_rating': round(self._average_rating, 2),
            'rating_count': self._rating_count
        }


class ChatSession:
    """Chat session between user and support agent"""
    
    def __init__(self, session_id: str, user: User, priority: ChatPriority):
        self._session_id = session_id
        self._user = user
        self._priority = priority
        self._status = ChatStatus.WAITING
        
        # Assignment
        self._assigned_agent: Optional[SupportAgent] = None
        self._requested_level: Optional[AgentLevel] = None  # For preempted chats
        
        # Messages
        self._messages: List[Message] = []
        
        # Timestamps
        self._created_at = datetime.now()
        self._assigned_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        
        # Metrics
        self._wait_time: Optional[timedelta] = None
        self._duration: Optional[timedelta] = None
        
        # Feedback
        self._feedback_given = False
        self._rating: Optional[int] = None
        self._feedback_comment: Optional[str] = None
    
    def get_id(self) -> str:
        return self._session_id
    
    def get_user(self) -> User:
        return self._user
    
    def get_priority(self) -> ChatPriority:
        return self._priority
    
    def get_status(self) -> ChatStatus:
        return self._status
    
    def get_assigned_agent(self) -> Optional[SupportAgent]:
        return self._assigned_agent
    
    def get_requested_level(self) -> Optional[AgentLevel]:
        return self._requested_level
    
    def set_requested_level(self, level: AgentLevel) -> None:
        """Set the requested agent level (for preempted chats)"""
        self._requested_level = level
    
    def assign_to_agent(self, agent: SupportAgent) -> None:
        """Assign this chat to an agent"""
        self._assigned_agent = agent
        self._assigned_at = datetime.now()
        self._status = ChatStatus.ACTIVE
        
        if self._assigned_at and self._created_at:
            self._wait_time = self._assigned_at - self._created_at
        
        # System message
        self.add_message(
            "System",
            f"Connected to {agent.get_name()} ({agent.get_level().name} Support)",
            MessageType.SYSTEM
        )
    
    def add_message(self, sender: str, content: str, 
                   message_type: MessageType = MessageType.TEXT) -> Message:
        """Add a message to the chat"""
        message = Message(sender, content, message_type)
        self._messages.append(message)
        return message
    
    def escalate(self, to_level: AgentLevel) -> None:
        """Escalate chat to higher level"""
        self._status = ChatStatus.ESCALATED
        self._requested_level = to_level
        
        # System message
        self.add_message(
            "System",
            f"Chat escalated to {to_level.name} level",
            MessageType.SYSTEM
        )
    
    def complete(self) -> None:
        """Complete the chat session"""
        self._status = ChatStatus.COMPLETED
        self._completed_at = datetime.now()
        
        if self._assigned_at and self._completed_at:
            self._duration = self._completed_at - self._assigned_at
        
        # System message
        self.add_message(
            "System",
            "Chat session ended. Please provide feedback.",
            MessageType.SYSTEM
        )
    
    def abandon(self) -> None:
        """Mark chat as abandoned (user left)"""
        self._status = ChatStatus.ABANDONED
        self._completed_at = datetime.now()
    
    def submit_feedback(self, rating: int, comment: Optional[str] = None) -> bool:
        """Submit feedback for the chat"""
        if not (1 <= rating <= 5):
            return False
        
        if self._status != ChatStatus.COMPLETED:
            return False
        
        self._feedback_given = True
        self._rating = rating
        self._feedback_comment = comment
        
        # Update agent's rating
        if self._assigned_agent:
            self._assigned_agent.add_rating(rating)
        
        return True
    
    def get_messages(self) -> List[Message]:
        return self._messages
    
    def get_wait_time(self) -> Optional[timedelta]:
        return self._wait_time
    
    def get_duration(self) -> Optional[timedelta]:
        return self._duration
    
    def has_feedback(self) -> bool:
        return self._feedback_given
    
    def to_dict(self) -> Dict:
        return {
            'session_id': self._session_id,
            'user': self._user.to_dict(),
            'priority': self._priority.value,
            'status': self._status.value,
            'assigned_agent': self._assigned_agent.to_dict() if self._assigned_agent else None,
            'created_at': self._created_at.isoformat(),
            'assigned_at': self._assigned_at.isoformat() if self._assigned_at else None,
            'completed_at': self._completed_at.isoformat() if self._completed_at else None,
            'wait_time': str(self._wait_time) if self._wait_time else None,
            'duration': str(self._duration) if self._duration else None,
            'feedback_given': self._feedback_given,
            'rating': self._rating,
            'message_count': len(self._messages)
        }


class WaitQueue:
    """Queue for waiting chat sessions"""
    
    def __init__(self, name: str):
        self._name = name
        self._queue: deque[ChatSession] = deque()
    
    def enqueue(self, chat: ChatSession) -> None:
        """Add chat to queue"""
        self._queue.append(chat)
    
    def dequeue(self) -> Optional[ChatSession]:
        """Remove and return first chat from queue"""
        if self._queue:
            return self._queue.popleft()
        return None
    
    def remove(self, chat: ChatSession) -> bool:
        """Remove specific chat from queue"""
        try:
            self._queue.remove(chat)
            return True
        except ValueError:
            return False
    
    def peek(self) -> Optional[ChatSession]:
        """View first chat without removing"""
        if self._queue:
            return self._queue[0]
        return None
    
    def is_empty(self) -> bool:
        return len(self._queue) == 0
    
    def size(self) -> int:
        return len(self._queue)
    
    def get_all(self) -> List[ChatSession]:
        return list(self._queue)


# ==================== Support Chat System ====================

class SupportChatSystem:
    """
    Main Support Chat System
    
    Features:
    - Multi-level support (L1, L2, Supervisor)
    - Automatic routing based on availability
    - Priority queue for preempted users (direct to supervisor)
    - Admin-controlled priority mode
    - Feedback system with star ratings
    - Wait queue management
    - Chat escalation
    """
    
    def __init__(self, system_name: str = "Support Chat System"):
        self._system_name = system_name
        
        # Agents organized by level
        self._agents: Dict[str, SupportAgent] = {}
        self._agents_by_level: Dict[AgentLevel, List[SupportAgent]] = {
            AgentLevel.L1: [],
            AgentLevel.L2: [],
            AgentLevel.SUPERVISOR: []
        }
        
        # Users and sessions
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, ChatSession] = {}
        
        # Queues
        self._normal_queue = WaitQueue("Normal Queue")
        self._preempted_queue = WaitQueue("Preempted Queue (Supervisor)")
        
        # Admin settings
        self._priority_mode = PriorityMode.PREEMPTED_FIRST  # Default: preempted first
        
        # Statistics
        self._total_chats = 0
        self._completed_chats = 0
        self._abandoned_chats = 0
    
    # ==================== User Management ====================
    
    def register_user(self, name: str, email: str) -> User:
        """Register a new user"""
        user_id = str(uuid.uuid4())
        user = User(user_id, name, email)
        
        self._users[user_id] = user
        
        print(f"✅ User registered: {name}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)
    
    # ==================== Agent Management ====================
    
    def add_agent(self, name: str, level: AgentLevel) -> SupportAgent:
        """Add a support agent"""
        agent_id = str(uuid.uuid4())
        agent = SupportAgent(agent_id, name, level)
        
        self._agents[agent_id] = agent
        self._agents_by_level[level].append(agent)
        
        print(f"✅ Agent added: {name} ({level.name})")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[SupportAgent]:
        return self._agents.get(agent_id)
    
    def get_available_agents(self, level: AgentLevel) -> List[SupportAgent]:
        """Get available agents at specific level"""
        return [
            agent for agent in self._agents_by_level[level]
            if agent.is_available()
        ]
    
    # ==================== Chat Session Management ====================
    
    def start_chat(self, user_id: str, preempt_to_supervisor: bool = False) -> Optional[ChatSession]:
        """
        Start a new chat session
        
        Args:
            user_id: User requesting support
            preempt_to_supervisor: If True, user wants to talk directly to supervisor
        """
        user = self._users.get(user_id)
        if not user:
            print(f"❌ User not found: {user_id}")
            return None
        
        # Create chat session
        session_id = str(uuid.uuid4())
        priority = ChatPriority.PREEMPTED if preempt_to_supervisor else ChatPriority.NORMAL
        chat = ChatSession(session_id, user, priority)
        
        self._sessions[session_id] = chat
        self._total_chats += 1
        
        if preempt_to_supervisor:
            chat.set_requested_level(AgentLevel.SUPERVISOR)
            print(f"📞 {user.get_name()} requesting supervisor directly")
        else:
            print(f"📞 {user.get_name()} starting chat")
        
        # Try to assign immediately
        assigned = self._try_assign_chat(chat)
        
        if not assigned:
            # Add to appropriate queue
            if preempt_to_supervisor:
                self._preempted_queue.enqueue(chat)
                print(f"⏳ Added to preempted queue (waiting for supervisor)")
                print(f"   Queue position: {self._preempted_queue.size()}")
            else:
                self._normal_queue.enqueue(chat)
                print(f"⏳ Added to normal queue")
                print(f"   Queue position: {self._normal_queue.size()}")
        
        return chat
    
    def _try_assign_chat(self, chat: ChatSession) -> bool:
        """
        Try to assign chat to an available agent
        
        Routing logic:
        - Normal users: Try L1 -> L2 -> Supervisor
        - Preempted users: Only try Supervisor
        """
        if chat.get_priority() == ChatPriority.PREEMPTED:
            # Preempted users only want supervisor
            return self._assign_to_level(chat, AgentLevel.SUPERVISOR)
        else:
            # Normal users: escalate through levels
            # Try L1 first
            if self._assign_to_level(chat, AgentLevel.L1):
                return True
            
            # Try L2
            if self._assign_to_level(chat, AgentLevel.L2):
                return True
            
            # Try Supervisor
            if self._assign_to_level(chat, AgentLevel.SUPERVISOR):
                return True
            
            return False
    
    def _assign_to_level(self, chat: ChatSession, level: AgentLevel) -> bool:
        """Try to assign chat to an agent at specific level"""
        available_agents = self.get_available_agents(level)
        
        if not available_agents:
            return False
        
        # Pick agent with least chats handled (load balancing)
        agent = min(available_agents, key=lambda a: a._total_chats_handled)
        
        # Assign
        if agent.assign_chat(chat):
            chat.assign_to_agent(agent)
            print(f"✅ Assigned to {agent.get_name()} ({agent.get_level().name})")
            return True
        
        return False
    
    def _process_wait_queues(self) -> None:
        """
        Process waiting chats and assign to available agents
        
        Priority handling based on admin setting:
        - PREEMPTED_FIRST: Process preempted queue before normal queue
        - NORMAL_FIRST: Process normal queue before preempted queue
        """
        if self._priority_mode == PriorityMode.PREEMPTED_FIRST:
            # Process preempted queue first
            self._process_preempted_queue()
            self._process_normal_queue()
        else:
            # Process normal queue first
            self._process_normal_queue()
            self._process_preempted_queue()
    
    def _process_preempted_queue(self) -> None:
        """Process preempted queue (supervisor only)"""
        while not self._preempted_queue.is_empty():
            chat = self._preempted_queue.peek()
            
            if self._assign_to_level(chat, AgentLevel.SUPERVISOR):
                self._preempted_queue.dequeue()
            else:
                break  # No available supervisor
    
    def _process_normal_queue(self) -> None:
        """Process normal queue (try L1 -> L2 -> Supervisor)"""
        while not self._normal_queue.is_empty():
            chat = self._normal_queue.peek()
            
            if self._try_assign_chat(chat):
                self._normal_queue.dequeue()
            else:
                break  # No available agents at any level
    
    # ==================== Chat Operations ====================
    
    def send_message(self, session_id: str, sender: str, content: str) -> Optional[Message]:
        """Send a message in a chat session"""
        chat = self._sessions.get(session_id)
        if not chat:
            return None
        
        if chat.get_status() != ChatStatus.ACTIVE:
            print(f"❌ Chat is not active")
            return None
        
        message = chat.add_message(sender, content)
        return message
    
    def escalate_chat(self, session_id: str) -> bool:
        """
        Escalate chat to next level
        - L1 -> L2
        - L2 -> Supervisor
        """
        chat = self._sessions.get(session_id)
        if not chat or chat.get_status() != ChatStatus.ACTIVE:
            return False
        
        current_agent = chat.get_assigned_agent()
        if not current_agent:
            return False
        
        current_level = current_agent.get_level()
        
        # Determine target level
        if current_level == AgentLevel.L1:
            target_level = AgentLevel.L2
        elif current_level == AgentLevel.L2:
            target_level = AgentLevel.SUPERVISOR
        else:
            print(f"❌ Already at highest level (Supervisor)")
            return False
        
        print(f"⬆️  Escalating from {current_level.name} to {target_level.name}")
        
        # Release from current agent
        current_agent.release_chat()
        
        # Mark as escalated
        chat.escalate(target_level)
        
        # Try to assign to target level
        if self._assign_to_level(chat, target_level):
            # Process queues in case other chats can now be assigned
            self._process_wait_queues()
            return True
        else:
            # No available agent at target level, add to preempted queue
            self._preempted_queue.enqueue(chat)
            print(f"⏳ Waiting for available {target_level.name}")
            return True
    
    def end_chat(self, session_id: str) -> bool:
        """End a chat session"""
        chat = self._sessions.get(session_id)
        if not chat:
            return False
        
        if chat.get_status() not in [ChatStatus.ACTIVE, ChatStatus.ESCALATED]:
            return False
        
        # Release agent
        agent = chat.get_assigned_agent()
        if agent:
            agent.release_chat()
            print(f"📞 Chat ended with {agent.get_name()}")
        
        # Complete chat
        chat.complete()
        self._completed_chats += 1
        
        # Process waiting chats
        self._process_wait_queues()
        
        return True
    
    def abandon_chat(self, session_id: str) -> bool:
        """User abandoned chat (left without completing)"""
        chat = self._sessions.get(session_id)
        if not chat:
            return False
        
        # Remove from queues if waiting
        self._normal_queue.remove(chat)
        self._preempted_queue.remove(chat)
        
        # Release agent if assigned
        agent = chat.get_assigned_agent()
        if agent:
            agent.release_chat()
        
        chat.abandon()
        self._abandoned_chats += 1
        
        print(f"👋 User abandoned chat")
        
        # Process waiting chats
        self._process_wait_queues()
        
        return True
    
    # ==================== Feedback ====================
    
    def submit_feedback(self, session_id: str, rating: int, 
                       comment: Optional[str] = None) -> bool:
        """Submit feedback for completed chat"""
        chat = self._sessions.get(session_id)
        if not chat:
            print(f"❌ Session not found")
            return False
        
        if chat.submit_feedback(rating, comment):
            agent = chat.get_assigned_agent()
            agent_name = agent.get_name() if agent else "Unknown"
            
            print(f"⭐ Feedback submitted: {rating}/5 for {agent_name}")
            if comment:
                print(f"   Comment: {comment}")
            return True
        
        return False
    
    # ==================== Admin Operations ====================
    
    def set_priority_mode(self, mode: PriorityMode) -> None:
        """Admin sets priority mode for supervisor assignment"""
        old_mode = self._priority_mode
        self._priority_mode = mode
        
        print(f"🔧 Admin: Priority mode changed from {old_mode.value} to {mode.value}")
        
        # Re-process queues with new priority
        self._process_wait_queues()
    
    def get_priority_mode(self) -> PriorityMode:
        return self._priority_mode
    
    def set_agent_offline(self, agent_id: str) -> bool:
        """Admin sets agent offline"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        # If agent has active chat, end it first
        if agent.get_current_chat():
            self.end_chat(agent.get_current_chat().get_id())
        
        agent.set_offline()
        print(f"🔧 Admin: {agent.get_name()} set offline")
        
        return True
    
    def set_agent_available(self, agent_id: str) -> bool:
        """Admin sets agent available"""
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        
        agent.set_available()
        print(f"🔧 Admin: {agent.get_name()} set available")
        
        # Process waiting chats
        self._process_wait_queues()
        
        return True
    
    # ==================== Queries ====================
    
    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)
    
    def get_queue_status(self) -> Dict:
        """Get status of wait queues"""
        return {
            'normal_queue': {
                'size': self._normal_queue.size(),
                'oldest_wait_time': str(datetime.now() - self._normal_queue.peek()._created_at) 
                                   if not self._normal_queue.is_empty() else None
            },
            'preempted_queue': {
                'size': self._preempted_queue.size(),
                'oldest_wait_time': str(datetime.now() - self._preempted_queue.peek()._created_at)
                                   if not self._preempted_queue.is_empty() else None
            }
        }
    
    def get_agent_statistics(self, level: Optional[AgentLevel] = None) -> List[Dict]:
        """Get statistics for agents"""
        if level:
            agents = self._agents_by_level[level]
        else:
            agents = list(self._agents.values())
        
        return [agent.to_dict() for agent in agents]
    
    def get_system_statistics(self) -> Dict:
        """Get overall system statistics"""
        total_agents = len(self._agents)
        available_agents = sum(1 for a in self._agents.values() if a.is_available())
        busy_agents = sum(1 for a in self._agents.values() if a.get_status() == AgentStatus.BUSY)
        
        return {
            'system_name': self._system_name,
            'total_agents': total_agents,
            'available_agents': available_agents,
            'busy_agents': busy_agents,
            'agents_by_level': {
                'L1': len(self._agents_by_level[AgentLevel.L1]),
                'L2': len(self._agents_by_level[AgentLevel.L2]),
                'Supervisor': len(self._agents_by_level[AgentLevel.SUPERVISOR])
            },
            'available_by_level': {
                'L1': len(self.get_available_agents(AgentLevel.L1)),
                'L2': len(self.get_available_agents(AgentLevel.L2)),
                'Supervisor': len(self.get_available_agents(AgentLevel.SUPERVISOR))
            },
            'total_users': len(self._users),
            'total_chats': self._total_chats,
            'completed_chats': self._completed_chats,
            'abandoned_chats': self._abandoned_chats,
            'active_chats': sum(1 for c in self._sessions.values() 
                              if c.get_status() in [ChatStatus.ACTIVE, ChatStatus.ESCALATED]),
            'queue_status': self.get_queue_status(),
            'priority_mode': self._priority_mode.value
        }


# ==================== Demo ====================

def print_section(title: str) -> None:
    """Print section header"""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print('=' * 70)


def demo_support_chat_system():
    """Comprehensive demo of support chat system"""
    
    print_section("SUPPORT CHAT SYSTEM DEMO")
    
    system = SupportChatSystem("Customer Support Center")
    
    # ==================== Add Support Agents ====================
    print_section("1. Add Support Agents")
    
    # L1 Agents
    l1_alice = system.add_agent("Alice Johnson", AgentLevel.L1)
    l1_bob = system.add_agent("Bob Smith", AgentLevel.L1)
    l1_charlie = system.add_agent("Charlie Brown", AgentLevel.L1)
    
    # L2 Agents
    l2_diana = system.add_agent("Diana Prince", AgentLevel.L2)
    l2_edward = system.add_agent("Edward Norton", AgentLevel.L2)
    
    # Supervisors
    sup_frank = system.add_agent("Frank Miller", AgentLevel.SUPERVISOR)
    sup_grace = system.add_agent("Grace Hopper", AgentLevel.SUPERVISOR)
    
    # ==================== Register Users ====================
    print_section("2. Register Users")
    
    user1 = system.register_user("Priya Sharma", "priya@email.com")
    user2 = system.register_user("Rahul Verma", "rahul@email.com")
    user3 = system.register_user("Neha Gupta", "neha@email.com")
    user4 = system.register_user("Amit Singh", "amit@email.com")
    user5 = system.register_user("Kavita Desai", "kavita@email.com")
    
    # ==================== Normal Chat Flow ====================
    print_section("3. Normal Chat Flow (L1 Assignment)")
    
    # User 1 starts chat
    chat1 = system.start_chat(user1.get_id())
    
    if chat1:
        # Send some messages
        system.send_message(chat1.get_id(), user1.get_name(), "Hi, I need help with my order")
        system.send_message(chat1.get_id(), l1_alice.get_name(), "Hello! I'd be happy to help. What's your order number?")
        system.send_message(chat1.get_id(), user1.get_name(), "Order #12345")
        system.send_message(chat1.get_id(), l1_alice.get_name(), "Let me check that for you...")
        
        # End chat
        system.end_chat(chat1.get_id())
        
        # Submit feedback
        system.submit_feedback(chat1.get_id(), 5, "Very helpful!")
    
    # ==================== Multiple Users - Queue Scenario ====================
    print_section("4. Multiple Users - Queue Management")
    
    # Start multiple chats (more than L1 agents)
    print(f"\n🔄 Starting 5 chats with only 3 L1 agents...")
    
    chat2 = system.start_chat(user2.get_id())
    chat3 = system.start_chat(user3.get_id())
    chat4 = system.start_chat(user4.get_id())
    chat5 = system.start_chat(user5.get_id())
    
    # Check queue status
    print(f"\n📊 Current Queue Status:")
    queue_status = system.get_queue_status()
    print(f"   Normal Queue: {queue_status['normal_queue']['size']} waiting")
    print(f"   Preempted Queue: {queue_status['preempted_queue']['size']} waiting")
    
    # ==================== Preempted Chat (Direct to Supervisor) ====================
    print_section("5. Preempted User (Direct Supervisor Request)")
    
    # User wants to talk directly to supervisor
    chat_preempt = system.start_chat(user1.get_id(), preempt_to_supervisor=True)
    
    # Check queue
    print(f"\n📊 Queue Status After Preemption:")
    queue_status = system.get_queue_status()
    print(f"   Preempted Queue: {queue_status['preempted_queue']['size']} waiting")
    
    # ==================== Chat Escalation ====================
    print_section("6. Chat Escalation (L1 -> L2 -> Supervisor)")
    
    # End one chat to free up agent
    if chat2:
        print(f"\n📞 User 2 chat in progress with {chat2.get_assigned_agent().get_name()}...")
        system.send_message(chat2.get_id(), user2.get_name(), "This is more complex than I thought")
        system.send_message(chat2.get_id(), l1_bob.get_name(), "Let me escalate this to L2 support")
        
        # Escalate to L2
        system.escalate_chat(chat2.get_id())
        
        # Send more messages
        if chat2.get_assigned_agent():
            system.send_message(chat2.get_id(), chat2.get_assigned_agent().get_name(), 
                              "Hi, I'm L2 support. How can I help?")
            system.send_message(chat2.get_id(), user2.get_name(), "Still need help with complex issue")
            system.send_message(chat2.get_id(), chat2.get_assigned_agent().get_name(),
                              "This requires supervisor approval")
            
            # Escalate to Supervisor
            system.escalate_chat(chat2.get_id())
    
    # ==================== Complete Some Chats ====================
    print_section("7. Complete Chats and Process Queue")
    
    # Complete chat 3
    if chat3:
        print(f"\n✅ Completing chat 3...")
        system.end_chat(chat3.get_id())
        system.submit_feedback(chat3.get_id(), 4, "Good service")
    
    # Complete preempted chat
    if chat_preempt:
        print(f"\n✅ Completing preempted chat...")
        system.end_chat(chat_preempt.get_id())
        system.submit_feedback(chat_preempt.get_id(), 5, "Supervisor was excellent!")
    
    # Check if queue processed
    print(f"\n📊 Queue Status After Completions:")
    queue_status = system.get_queue_status()
    print(f"   Normal Queue: {queue_status['normal_queue']['size']} waiting")
    print(f"   Preempted Queue: {queue_status['preempted_queue']['size']} waiting")
    
    # ==================== Admin Changes Priority Mode ====================
    print_section("8. Admin Changes Priority Mode")
    
    print(f"\n🔧 Current priority mode: {system.get_priority_mode().value}")
    
    # Change to normal users first
    system.set_priority_mode(PriorityMode.NORMAL_FIRST)
    
    # ==================== User Abandons Chat ====================
    print_section("9. User Abandons Chat")
    
    # User 4 abandons chat
    if chat4:
        print(f"\n👋 User 4 abandoning chat...")
        system.abandon_chat(chat4.get_id())
    
    # ==================== Agent Goes Offline ====================
    print_section("10. Admin Sets Agent Offline")
    
    # Set L1 agent offline
    system.set_agent_offline(l1_charlie.get_id())
    
    # Check availability
    print(f"\n📊 L1 Agents Available: {len(system.get_available_agents(AgentLevel.L1))}")
    
    # ==================== View Chat Messages ====================
    print_section("11. View Chat History")
    
    if chat1:
        print(f"\n💬 Chat History for Session {chat1.get_id()[:8]}:")
        messages = chat1.get_messages()
        for msg in messages:
            timestamp = msg.get_timestamp().strftime("%H:%M:%S")
            print(f"   [{timestamp}] {msg.get_sender()}: {msg.get_content()}")
    
    # ==================== Agent Statistics ====================
    print_section("12. Agent Performance Statistics")
    
    print(f"\n📊 L1 Agent Statistics:")
    l1_stats = system.get_agent_statistics(AgentLevel.L1)
    for stat in l1_stats:
        print(f"   • {stat['name']}:")
        print(f"     Status: {stat['status']}")
        print(f"     Total Chats: {stat['total_chats']}")
        print(f"     Average Rating: {stat['average_rating']:.2f}/5.0 ({stat['rating_count']} ratings)")
    
    print(f"\n📊 L2 Agent Statistics:")
    l2_stats = system.get_agent_statistics(AgentLevel.L2)
    for stat in l2_stats:
        print(f"   • {stat['name']}:")
        print(f"     Status: {stat['status']}")
        print(f"     Total Chats: {stat['total_chats']}")
        print(f"     Average Rating: {stat['average_rating']:.2f}/5.0 ({stat['rating_count']} ratings)")
    
    print(f"\n📊 Supervisor Statistics:")
    sup_stats = system.get_agent_statistics(AgentLevel.SUPERVISOR)
    for stat in sup_stats:
        print(f"   • {stat['name']}:")
        print(f"     Status: {stat['status']}")
        print(f"     Total Chats: {stat['total_chats']}")
        print(f"     Average Rating: {stat['average_rating']:.2f}/5.0 ({stat['rating_count']} ratings)")
    
    # ==================== System Statistics ====================
    print_section("13. System-Wide Statistics")
    
    stats = system.get_system_statistics()
    
    print(f"\n📊 {stats['system_name']} Statistics:")
    print(f"\n   Agents:")
    print(f"   Total: {stats['total_agents']}")
    print(f"   Available: {stats['available_agents']}")
    print(f"   Busy: {stats['busy_agents']}")
    
    print(f"\n   Agents by Level:")
    for level, count in stats['agents_by_level'].items():
        available = stats['available_by_level'][level]
        print(f"   • {level}: {count} total ({available} available)")
    
    print(f"\n   Chats:")
    print(f"   Total: {stats['total_chats']}")
    print(f"   Completed: {stats['completed_chats']}")
    print(f"   Abandoned: {stats['abandoned_chats']}")
    print(f"   Active: {stats['active_chats']}")
    
    print(f"\n   Queue Status:")
    print(f"   Normal Queue: {stats['queue_status']['normal_queue']['size']} waiting")
    print(f"   Preempted Queue: {stats['queue_status']['preempted_queue']['size']} waiting")
    
    print(f"\n   Settings:")
    print(f"   Priority Mode: {stats['priority_mode']}")
    
    # ==================== Detailed Chat Session Info ====================
    print_section("14. Detailed Chat Session Information")
    
    if chat2:
        chat_info = chat2.to_dict()
        print(f"\n📋 Chat Session Details (Escalated Chat):")
        print(f"   Session ID: {chat_info['session_id'][:8]}")
        print(f"   User: {chat_info['user']['name']}")
        print(f"   Priority: {chat_info['priority']}")
        print(f"   Status: {chat_info['status']}")
        if chat_info['assigned_agent']:
            print(f"   Final Agent: {chat_info['assigned_agent']['name']} ({chat_info['assigned_agent']['level']})")
        print(f"   Wait Time: {chat_info['wait_time']}")
        print(f"   Duration: {chat_info['duration']}")
        print(f"   Messages: {chat_info['message_count']}")
        print(f"   Feedback Given: {chat_info['feedback_given']}")
    
    print_section("Demo Complete")
    print("\n✅ Support Chat System demo completed!")
    
    print("\n" + "="*70)
    print(" KEY FEATURES DEMONSTRATED")
    print("="*70)
    
    print("\n✅ Multi-Level Support:")
    print("   • L1 -> L2 -> Supervisor hierarchy")
    print("   • Automatic routing to available agents")
    print("   • Escalation between levels")
    
    print("\n✅ Queue Management:")
    print("   • Normal queue for regular users")
    print("   • Preempted queue for supervisor requests")
    print("   • FIFO processing within each queue")
    print("   • Automatic assignment when agents free up")
    
    print("\n✅ Priority System:")
    print("   • Users can request supervisor directly (preempt)")
    print("   • Admin-controlled priority mode:")
    print("     - PREEMPTED_FIRST: Supervisor requests processed first")
    print("     - NORMAL_FIRST: Normal queue processed first")
    print("   • Dynamic priority switching")
    
    print("\n✅ Feedback System:")
    print("   • Star rating (1-5)")
    print("   • Optional comments")
    print("   • Agent performance tracking")
    print("   • Average rating calculation")
    
    print("\n✅ Chat Operations:")
    print("   • Start/end chat")
    print("   • Send messages")
    print("   • Escalate to higher level")
    print("   • Abandon chat")
    print("   • Complete chat history")
    
    print("\n✅ Admin Controls:")
    print("   • Set priority mode")
    print("   • Set agents online/offline")
    print("   • View system statistics")
    print("   • Monitor queue status")
    
    print("\n✅ Metrics & Analytics:")
    print("   • Agent performance statistics")
    print("   • Wait time tracking")
    print("   • Chat duration monitoring")
    print("   • Queue length tracking")
    print("   • Completion/abandonment rates")


# ==================== Main Entry Point ====================

if __name__ == "__main__":
    try:
        demo_support_chat_system()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# Here's a comprehensive Support Chat System design for an LLD interview:

# Key Design Decisions:
# 1. Core Components:
# SupportAgent: L1/L2/Supervisor with availability tracking
# ChatSession: Conversation with status, messages, metrics
# WaitQueue: FIFO queue for waiting users
# User: Customer requesting support
# 2. Routing Algorithm:
# Normal Users (L1 → L2 → Supervisor):

# Preempted Users (Supervisor Only):

# 3. Priority System:
# Two Modes (Admin-controlled):

# PREEMPTED_FIRST: Preempted queue processed before normal
# NORMAL_FIRST: Normal queue processed before preempted
# Dynamic switching: Admin can change at runtime

# 4. Queue Processing:
# 5. Chat Escalation:
# 6. Feedback System:
# 7. Key Features:
# ✅ Implemented:

# Multi-level support hierarchy
# Automatic routing with fallback
# Priority queue for supervisor requests
# Admin priority mode switching
# Chat escalation
# Queue management
# Feedback with ratings
# Agent performance tracking
# Wait time monitoring
# Chat abandonment handling
# 8. Design Patterns:
# Strategy Pattern: Routing algorithm (normal vs preempted)
# Queue Pattern: Wait queue management
# State Pattern: Chat status transitions
# Observer Pattern: Queue processing on agent availability
# Command Pattern: Admin operations
# 9. Workflow Examples:
# Scenario 1: Normal User

# Scenario 2: Preempted User

# Scenario 3: Escalation

# 10. Statistics Tracked:
# Total/completed/abandoned chats
# Agent availability by level
# Queue sizes
# Wait times
# Chat duration
# Agent ratings
# Completion rates
# This is a production-grade support system like Zendesk/Intercom! 🎧💬
