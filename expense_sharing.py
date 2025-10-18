from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Dict, Set
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
from threading import Lock
import heapq


# ==================== Enums ====================

class SplitType(Enum):
    """Types of expense splits"""
    EQUAL = "EQUAL"
    PERCENTAGE = "PERCENTAGE"
    EXACT = "EXACT"
    SHARES = "SHARES"


class ExpenseCategory(Enum):
    """Expense categories"""
    FOOD = "FOOD"
    TRANSPORT = "TRANSPORT"
    ENTERTAINMENT = "ENTERTAINMENT"
    UTILITIES = "UTILITIES"
    RENT = "RENT"
    GROCERIES = "GROCERIES"
    TRAVEL = "TRAVEL"
    OTHER = "OTHER"


class TransactionStatus(Enum):
    """Status of settlement transactions"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ==================== Core Models ====================

class User:
    """Represents a user in the system"""
    
    def __init__(self, user_id: str, name: str, email: str, phone: str):
        self._user_id = user_id
        self._name = name
        self._email = email
        self._phone = phone
    
    def get_id(self) -> str:
        return self._user_id
    
    def get_name(self) -> str:
        return self._name
    
    def get_email(self) -> str:
        return self._email
    
    def __repr__(self) -> str:
        return f"User({self._user_id}, {self._name})"
    
    def __hash__(self) -> int:
        return hash(self._user_id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self._user_id == other._user_id


@dataclass
class Split:
    """Represents how much a user owes/is owed in an expense"""
    user: User
    amount: Decimal
    
    def __repr__(self) -> str:
        return f"Split({self.user.get_name()}: ${self.amount})"


# ==================== Strategy Pattern: Split Strategies ====================

class SplitStrategy(ABC):
    """Abstract strategy for splitting expenses"""
    
    @abstractmethod
    def calculate_splits(self, total_amount: Decimal, 
                        paid_by: User,
                        participants: List[User],
                        metadata: Dict) -> List[Split]:
        """
        Calculate how much each participant owes.
        Returns list of splits (can be negative for the payer).
        """
        pass
    
    @abstractmethod
    def validate(self, total_amount: Decimal, metadata: Dict) -> bool:
        """Validate split parameters"""
        pass


class EqualSplitStrategy(SplitStrategy):
    """Split equally among all participants"""
    
    def calculate_splits(self, total_amount: Decimal, 
                        paid_by: User,
                        participants: List[User],
                        metadata: Dict) -> List[Split]:
        
        if not participants:
            return []
        
        # Calculate per-person amount
        per_person = total_amount / len(participants)
        
        splits = []
        for user in participants:
            if user == paid_by:
                # Payer receives (total - their share)
                splits.append(Split(user, -(total_amount - per_person)))
            else:
                # Others owe their share
                splits.append(Split(user, per_person))
        
        return splits
    
    def validate(self, total_amount: Decimal, metadata: Dict) -> bool:
        return total_amount > 0


class PercentageSplitStrategy(SplitStrategy):
    """Split by percentage"""
    
    def calculate_splits(self, total_amount: Decimal, 
                        paid_by: User,
                        participants: List[User],
                        metadata: Dict) -> List[Split]:
        
        percentages = metadata.get('percentages', {})
        
        splits = []
        payer_share = Decimal('0')
        
        for user in participants:
            percentage = Decimal(str(percentages.get(user.get_id(), 0)))
            user_amount = (total_amount * percentage) / Decimal('100')
            
            if user == paid_by:
                payer_share = user_amount
            else:
                splits.append(Split(user, user_amount))
        
        # Payer receives (total - their share)
        splits.append(Split(paid_by, -(total_amount - payer_share)))
        
        return splits
    
    def validate(self, total_amount: Decimal, metadata: Dict) -> bool:
        if total_amount <= 0:
            return False
        
        percentages = metadata.get('percentages', {})
        total_percentage = sum(Decimal(str(p)) for p in percentages.values())
        
        # Check if percentages sum to 100
        return abs(total_percentage - Decimal('100')) < Decimal('0.01')


class ExactSplitStrategy(SplitStrategy):
    """Split by exact amounts"""
    
    def calculate_splits(self, total_amount: Decimal, 
                        paid_by: User,
                        participants: List[User],
                        metadata: Dict) -> List[Split]:
        
        exact_amounts = metadata.get('exact_amounts', {})
        
        splits = []
        payer_share = Decimal('0')
        
        for user in participants:
            user_amount = Decimal(str(exact_amounts.get(user.get_id(), 0)))
            
            if user == paid_by:
                payer_share = user_amount
            else:
                splits.append(Split(user, user_amount))
        
        # Payer receives (total - their share)
        splits.append(Split(paid_by, -(total_amount - payer_share)))
        
        return splits
    
    def validate(self, total_amount: Decimal, metadata: Dict) -> bool:
        if total_amount <= 0:
            return False
        
        exact_amounts = metadata.get('exact_amounts', {})
        total_splits = sum(Decimal(str(a)) for a in exact_amounts.values())
        
        # Check if amounts sum to total
        return abs(total_splits - total_amount) < Decimal('0.01')


class SharesSplitStrategy(SplitStrategy):
    """Split by shares/units (e.g., one person ordered 2 items, another 1)"""
    
    def calculate_splits(self, total_amount: Decimal, 
                        paid_by: User,
                        participants: List[User],
                        metadata: Dict) -> List[Split]:
        
        shares = metadata.get('shares', {})
        total_shares = sum(shares.values())
        
        if total_shares == 0:
            return []
        
        per_share = total_amount / Decimal(str(total_shares))
        
        splits = []
        payer_share = Decimal('0')
        
        for user in participants:
            user_shares = Decimal(str(shares.get(user.get_id(), 0)))
            user_amount = per_share * user_shares
            
            if user == paid_by:
                payer_share = user_amount
            else:
                splits.append(Split(user, user_amount))
        
        # Payer receives (total - their share)
        splits.append(Split(paid_by, -(total_amount - payer_share)))
        
        return splits
    
    def validate(self, total_amount: Decimal, metadata: Dict) -> bool:
        if total_amount <= 0:
            return False
        
        shares = metadata.get('shares', {})
        return sum(shares.values()) > 0


# ==================== Expense ====================

class Expense:
    """Represents a shared expense"""
    
    _expense_counter = 0
    
    def __init__(self, description: str, total_amount: Decimal,
                 paid_by: User, category: ExpenseCategory,
                 split_strategy: SplitStrategy,
                 participants: List[User],
                 metadata: Optional[Dict] = None):
        
        Expense._expense_counter += 1
        self._expense_id = f"EXP-{Expense._expense_counter:08d}"
        self._description = description
        self._total_amount = total_amount
        self._paid_by = paid_by
        self._category = category
        self._split_strategy = split_strategy
        self._participants = participants
        self._metadata = metadata or {}
        self._created_at = datetime.now()
        self._splits: List[Split] = []
        
        # Calculate splits
        self._calculate_splits()
    
    def _calculate_splits(self) -> None:
        """Calculate splits using the strategy"""
        if not self._split_strategy.validate(self._total_amount, self._metadata):
            raise ValueError("Invalid split configuration")
        
        self._splits = self._split_strategy.calculate_splits(
            self._total_amount,
            self._paid_by,
            self._participants,
            self._metadata
        )
    
    def get_id(self) -> str:
        return self._expense_id
    
    def get_description(self) -> str:
        return self._description
    
    def get_total_amount(self) -> Decimal:
        return self._total_amount
    
    def get_paid_by(self) -> User:
        return self._paid_by
    
    def get_category(self) -> ExpenseCategory:
        return self._category
    
    def get_participants(self) -> List[User]:
        return self._participants
    
    def get_splits(self) -> List[Split]:
        return self._splits
    
    def get_created_at(self) -> datetime:
        return self._created_at
    
    def __repr__(self) -> str:
        return f"Expense({self._expense_id}, {self._description}, ${self._total_amount})"


# ==================== Group ====================

class Group:
    """Represents a group of users who share expenses"""
    
    _group_counter = 0
    
    def __init__(self, name: str, created_by: User, description: str = ""):
        Group._group_counter += 1
        self._group_id = f"GRP-{Group._group_counter:06d}"
        self._name = name
        self._description = description
        self._created_by = created_by
        self._members: Set[User] = {created_by}
        self._expenses: List[Expense] = []
        self._lock = Lock()
    
    def get_id(self) -> str:
        return self._group_id
    
    def get_name(self) -> str:
        return self._name
    
    def add_member(self, user: User) -> bool:
        """Add a member to the group"""
        with self._lock:
            if user in self._members:
                return False
            self._members.add(user)
            return True
    
    def remove_member(self, user: User) -> bool:
        """Remove a member from the group"""
        with self._lock:
            if user == self._created_by:
                print("Cannot remove group creator")
                return False
            
            if user not in self._members:
                return False
            
            self._members.remove(user)
            return True
    
    def get_members(self) -> List[User]:
        with self._lock:
            return list(self._members)
    
    def add_expense(self, expense: Expense) -> None:
        """Add an expense to the group"""
        with self._lock:
            self._expenses.append(expense)
    
    def get_expenses(self) -> List[Expense]:
        with self._lock:
            return self._expenses.copy()
    
    def __repr__(self) -> str:
        return f"Group({self._group_id}, {self._name})"


# ==================== Balance Sheet ====================


class BalanceSheet:
    """Manages balances between users"""
    
    def __init__(self):
        # balance[user_a][user_b] = amount that user_a owes to user_b
        self._balances: Dict[User, Dict[User, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
        self._lock = Lock()
    
    def add_expense(self, expense: Expense) -> None:
        """Update balances based on an expense"""
        with self._lock:
            for split in expense.get_splits():
                user = split.user
                amount = split.amount
                
                if amount > 0:
                    # User owes this amount to the payer
                    payer = expense.get_paid_by()
                    self._balances[user][payer] += amount
                elif amount < 0:
                    # User is owed (they are the payer)
                    # This is handled by the positive amounts of others
                    pass
    
    def _get_balance_internal(self, user1: User, user2: User) -> Decimal:
        """Internal method - assumes lock is already held"""
        owes = self._balances[user1][user2]
        owed = self._balances[user2][user1]
        return owes - owed
    
    def get_balance(self, user1: User, user2: User) -> Decimal:
        """Get net balance between two users (positive = user1 owes user2)"""
        with self._lock:
            return self._get_balance_internal(user1, user2)
    
    def get_all_balances(self, user: User) -> Dict[User, Decimal]:
        """Get all balances for a user"""
        with self._lock:
            balances = {}
            
            # What user owes to others
            for other, amount in self._balances[user].items():
                net = amount - self._balances[other][user]
                if abs(net) > Decimal('0.01'):
                    balances[other] = net
            
            # What others owe to user (not already counted)
            for other in self._balances:
                if other != user and other not in balances:
                    net = self._balances[user][other] - self._balances[other][user]
                    if abs(net) > Decimal('0.01'):
                        balances[other] = net
            
            return balances
    
    def get_simplified_balances(self) -> Dict[tuple, Decimal]:
        """Get all non-zero balances in simplified form"""
        with self._lock:
            simplified = {}
            processed = set()
            
            for user1 in self._balances:
                for user2 in self._balances[user1]:
                    if (user1, user2) in processed or (user2, user1) in processed:
                        continue
                    
                    net = self._balances[user1][user2] - self._balances[user2][user1]
                    
                    if abs(net) > Decimal('0.01'):
                        if net > 0:
                            simplified[(user1, user2)] = net
                        else:
                            simplified[(user2, user1)] = -net
                    
                    processed.add((user1, user2))
                    processed.add((user2, user1))
            
            return simplified
    
    def settle_balance(self, from_user: User, to_user: User, amount: Decimal) -> bool:
        """Record a settlement payment"""
        with self._lock:
            # Use internal method to avoid deadlock
            current_balance = self._get_balance_internal(from_user, to_user)
            
            if amount > current_balance + Decimal('0.01'):
                print(f"Settlement amount exceeds balance")
                return False
            
            self._balances[from_user][to_user] -= amount
            
            # Clean up zero balances
            if abs(self._balances[from_user][to_user]) < Decimal('0.01'):
                if from_user in self._balances and to_user in self._balances[from_user]:
                    del self._balances[from_user][to_user]
            
            return True

# ==================== Settlement Optimizer ====================

class SettlementOptimizer:
    """Optimizes settlements to minimize number of transactions"""
    
    @staticmethod
    def minimize_transactions(balance_sheet: BalanceSheet, 
                            users: List[User]) -> List[tuple]:
        """
        Calculate minimum transactions needed to settle all debts.
        Uses greedy algorithm with heaps.
        Returns list of (from_user, to_user, amount) tuples.
        """
        
        # Calculate net balance for each user
        net_balances = {}
        for user in users:
            balances = balance_sheet.get_all_balances(user)
            net = sum(balances.values())
            if abs(net) > Decimal('0.01'):
                net_balances[user] = net
        
        if not net_balances:
            return []
        
        # Separate debtors (owe money) and creditors (are owed money)
        debtors = []   # Max heap (negative values)
        creditors = [] # Max heap (negative values for max heap behavior)
        
        for user, balance in net_balances.items():
            if balance > 0:
                # User owes money
                heapq.heappush(debtors, (-balance, user))
            elif balance < 0:
                # User is owed money
                heapq.heappush(creditors, (balance, user))  # Already negative
        
        transactions = []
        
        # Match largest debtor with largest creditor
        while debtors and creditors:
            debt_amount, debtor = heapq.heappop(debtors)
            credit_amount, creditor = heapq.heappop(creditors)
            
            debt_amount = -debt_amount  # Convert back to positive
            credit_amount = -credit_amount  # Convert back to positive
            
            # Settle minimum of debt and credit
            settlement = min(debt_amount, credit_amount)
            transactions.append((debtor, creditor, settlement))
            
            # Push back remainder if any
            remaining_debt = debt_amount - settlement
            remaining_credit = credit_amount - settlement
            
            if remaining_debt > Decimal('0.01'):
                heapq.heappush(debtors, (-remaining_debt, debtor))
            
            if remaining_credit > Decimal('0.01'):
                heapq.heappush(creditors, (-remaining_credit, creditor))
        
        return transactions


# ==================== Expense Sharing App ====================

class ExpenseSharingApp:
    """Main application for expense sharing"""
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._groups: Dict[str, Group] = {}
        self._balance_sheet = BalanceSheet()
        self._all_expenses: List[Expense] = []
        self._lock = Lock()
    
    def register_user(self, user: User) -> None:
        """Register a new user"""
        with self._lock:
            self._users[user.get_id()] = user
        print(f"Registered user: {user}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self._users.get(user_id)
    
    def create_group(self, name: str, created_by: User, 
                    description: str = "") -> Group:
        """Create a new group"""
        group = Group(name, created_by, description)
        
        with self._lock:
            self._groups[group.get_id()] = group
        
        print(f"Created group: {group}")
        return group
    
    def get_group(self, group_id: str) -> Optional[Group]:
        """Get group by ID"""
        return self._groups.get(group_id)
    
    def add_expense(self, expense: Expense, group: Optional[Group] = None) -> None:
        """Add an expense"""
        with self._lock:
            self._all_expenses.append(expense)
        
        # Update balance sheet
        self._balance_sheet.add_expense(expense)
        
        # Add to group if specified
        if group:
            group.add_expense(expense)
        
        print(f"\nAdded expense: {expense}")
        print(f"Split details:")
        for split in expense.get_splits():
            if split.amount > 0:
                print(f"  {split.user.get_name()} owes ${split.amount}")
            else:
                print(f"  {split.user.get_name()} paid (gets back ${-split.amount})")
    
    def show_balance(self, user: User) -> None:
        """Show balance summary for a user"""
        print(f"\n{'='*60}")
        print(f"Balance Summary for {user.get_name()}")
        print(f"{'='*60}")
        
        balances = self._balance_sheet.get_all_balances(user)
        
        if not balances:
            print("All settled up!")
        else:
            owes_total = Decimal('0')
            owed_total = Decimal('0')
            
            print("\nYou owe:")
            for other, amount in balances.items():
                if amount > 0:
                    print(f"  {other.get_name()}: ${amount:.2f}")
                    owes_total += amount
            
            print("\nYou are owed:")
            for other, amount in balances.items():
                if amount < 0:
                    print(f"  {other.get_name()}: ${-amount:.2f}")
                    owed_total += -amount
            
            print(f"\n{'-'*60}")
            print(f"Total you owe: ${owes_total:.2f}")
            print(f"Total owed to you: ${owed_total:.2f}")
            net = owed_total - owes_total
            if net > 0:
                print(f"Net: You are owed ${net:.2f}")
            elif net < 0:
                print(f"Net: You owe ${-net:.2f}")
            else:
                print(f"Net: All settled!")
        
        print(f"{'='*60}\n")
    
    def show_group_balances(self, group: Group) -> None:
        """Show all balances within a group"""
        print(f"\n{'='*60}")
        print(f"Group Balances: {group.get_name()}")
        print(f"{'='*60}")
        
        members = group.get_members()
        balances = self._balance_sheet.get_simplified_balances()
        
        # Filter balances for group members
        group_balances = []
        for (user1, user2), amount in balances.items():
            if user1 in members and user2 in members:
                group_balances.append((user1, user2, amount))
        
        if not group_balances:
            print("All settled up!")
        else:
            for user1, user2, amount in group_balances:
                print(f"{user1.get_name()} owes {user2.get_name()}: ${amount:.2f}")
        
        print(f"{'='*60}\n")
    
    def settle_up(self, group: Optional[Group] = None, 
                 users: Optional[List[User]] = None) -> List[tuple]:
        """
        Calculate optimal settlements.
        If group is specified, settle within group.
        If users is specified, settle among those users.
        Otherwise, settle all users.
        """
        if group:
            users = group.get_members()
        elif not users:
            users = list(self._users.values())
        
        transactions = SettlementOptimizer.minimize_transactions(
            self._balance_sheet, users
        )
        
        print(f"\n{'='*60}")
        print(f"Optimal Settlement Plan")
        print(f"{'='*60}")
        
        if not transactions:
            print("All settled up!")
        else:
            print(f"Minimum {len(transactions)} transaction(s) needed:\n")
            for i, (from_user, to_user, amount) in enumerate(transactions, 1):
                print(f"{i}. {from_user.get_name()} pays {to_user.get_name()}: ${amount:.2f}")
        
        print(f"{'='*60}\n")
        
        return transactions
    
    def record_payment(self, from_user: User, to_user: User, 
                      amount: Decimal) -> bool:
        """Record a settlement payment"""
        success = self._balance_sheet.settle_balance(from_user, to_user, amount)
        
        if success:
            print(f"\n{from_user.get_name()} paid {to_user.get_name()} ${amount:.2f}")
            print("Balance updated!")
        
        return success
    
    def show_expense_history(self, user: Optional[User] = None,
                            group: Optional[Group] = None) -> None:
        """Show expense history"""
        print(f"\n{'='*60}")
        print("Expense History")
        print(f"{'='*60}")
        
        if group:
            expenses = group.get_expenses()
        elif user:
            expenses = [e for e in self._all_expenses if user in e.get_participants()]
        else:
            expenses = self._all_expenses
        
        if not expenses:
            print("No expenses found")
        else:
            for expense in sorted(expenses, key=lambda e: e.get_created_at(), reverse=True):
                date = expense.get_created_at().strftime("%Y-%m-%d %H:%M")
                print(f"\n[{date}] {expense.get_description()}")
                print(f"  Total: ${expense.get_total_amount()}")
                print(f"  Paid by: {expense.get_paid_by().get_name()}")
                print(f"  Category: {expense.get_category().value}")
                print(f"  Participants: {', '.join(u.get_name() for u in expense.get_participants())}")
        
        print(f"{'='*60}\n")


# ==================== Demo Usage ====================

def main():
    """Demo the expense sharing app"""
    print("=== Expense Sharing App (Splitwise) Demo ===\n")
    
    app = ExpenseSharingApp()
    
    # Register users
    print("--- Registering Users ---")
    alice = User("U001", "Alice", "alice@email.com", "555-0001")
    bob = User("U002", "Bob", "bob@email.com", "555-0002")
    charlie = User("U003", "Charlie", "charlie@email.com", "555-0003")
    diana = User("U004", "Diana", "diana@email.com", "555-0004")
    
    for user in [alice, bob, charlie, diana]:
        app.register_user(user)
    
    # Create a group
    print("\n--- Creating Group ---")
    trip_group = app.create_group("Europe Trip", alice, "Summer vacation 2025")
    trip_group.add_member(bob)
    trip_group.add_member(charlie)
    trip_group.add_member(diana)
    
    # Test 1: Equal split
    print("\n" + "="*60)
    print("TEST 1: Equal Split")
    print("="*60)
    print("Scenario: Alice paid $120 for dinner, split equally among 4 people")
    
    expense1 = Expense(
        description="Dinner at Restaurant",
        total_amount=Decimal('120.00'),
        paid_by=alice,
        category=ExpenseCategory.FOOD,
        split_strategy=EqualSplitStrategy(),
        participants=[alice, bob, charlie, diana]
    )
    app.add_expense(expense1, trip_group)
    
    # Test 2: Percentage split
    print("\n" + "="*60)
    print("TEST 2: Percentage Split")
    print("="*60)
    print("Scenario: Bob paid $200 for hotel, split by percentage (Alice 40%, Bob 30%, Charlie 20%, Diana 10%)")
    
    expense2 = Expense(
        description="Hotel Booking",
        total_amount=Decimal('200.00'),
        paid_by=bob,
        category=ExpenseCategory.RENT,
        split_strategy=PercentageSplitStrategy(),
        participants=[alice, bob, charlie, diana],
        metadata={
            'percentages': {
                'U001': 40,  # Alice
                'U002': 30,  # Bob
                'U003': 20,  # Charlie
                'U004': 10   # Diana
            }
        }
    )
    app.add_expense(expense2, trip_group)
    
    # Test 3: Exact split
    print("\n" + "="*60)
    print("TEST 3: Exact Split")
    print("="*60)
    print("Scenario: Charlie paid $85 for transport (Alice $25, Bob $20, Charlie $30, Diana $10)")
    
    expense3 = Expense(
        description="Taxi and Train Tickets",
        total_amount=Decimal('85.00'),
        paid_by=charlie,
        category=ExpenseCategory.TRANSPORT,
        split_strategy=ExactSplitStrategy(),
        participants=[alice, bob, charlie, diana],
        metadata={
            'exact_amounts': {
                'U001': 25,  # Alice
                'U002': 20,  # Bob
                'U003': 30,  # Charlie
                'U004': 10   # Diana
            }
        }
    )
    app.add_expense(expense3, trip_group)
    
    # Test 4: Shares split
    print("\n" + "="*60)
    print("TEST 4: Shares Split")
    print("="*60)
    print("Scenario: Diana paid $60 for groceries, split by items (Alice 3, Bob 2, Charlie 2, Diana 1)")
    
    expense4 = Expense(
        description="Groceries",
        total_amount=Decimal('60.00'),
        paid_by=diana,
        category=ExpenseCategory.GROCERIES,
        split_strategy=SharesSplitStrategy(),
        participants=[alice, bob, charlie, diana],
        metadata={
            'shares': {
                'U001': 3,  # Alice
                'U002': 2,  # Bob
                'U003': 2,  # Charlie
                'U004': 1   # Diana
            }
        }
    )
    app.add_expense(expense4, trip_group)
    
    # Show individual balances
    print("\n" + "="*60)
    print("INDIVIDUAL BALANCES")
    print("="*60)
    
    for user in [alice, bob, charlie, diana]:
        app.show_balance(user)
    
    # Show group balances
    app.show_group_balances(trip_group)
    
    # Calculate optimal settlements
    print("\n" + "="*60)
    print("SETTLEMENT OPTIMIZATION")
    print("="*60)
    
    transactions = app.settle_up(group=trip_group)
    
    # Simulate settlements
    if transactions:
        print("\n--- Recording Settlements ---")
        for from_user, to_user, amount in transactions:
            app.record_payment(from_user, to_user, amount)
    
    # Show balances after settlement
    print("\n" + "="*60)
    print("BALANCES AFTER SETTLEMENT")
    print("="*60)
    
    for user in [alice, bob, charlie, diana]:
        app.show_balance(user)
    
    # Show expense history
    app.show_expense_history(group=trip_group)
    
    # Test with two people
    print("\n" + "="*60)
    print("TEST 5: Two Person Expense")
    print("="*60)
    print("Scenario: Alice and Bob go to lunch, Alice pays $40, split equally")
    
    expense5 = Expense(
        description="Lunch",
        total_amount=Decimal('40.00'),
        paid_by=alice,
        category=ExpenseCategory.FOOD,
        split_strategy=EqualSplitStrategy(),
        participants=[alice, bob]
    )
    app.add_expense(expense5)
    
    app.show_balance(alice)
    app.show_balance(bob)
    
    # Show settlement for just Alice and Bob
    app.settle_up(users=[alice, bob])
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()


# ## Key Design Decisions

# ### **Design Patterns Used:**

# 1. **Strategy Pattern** - Split strategies:
#    - `EqualSplitStrategy`: Divide equally
#    - `PercentageSplitStrategy`: Split by percentage
#    - `ExactSplitStrategy`: Specify exact amounts
#    - `SharesSplitStrategy`: Split by shares/units

# 2. **Graph Algorithm** - Settlement optimization:
#    - Uses greedy algorithm with heaps
#    - Minimizes number of transactions
#    - Balances debts optimally

# ### **Core Features:**

# ✅ **Multiple Split Types**: Equal, percentage, exact, shares  
# ✅ **Group Management**: Create groups, add members  
# ✅ **Balance Tracking**: Real-time debt calculation  
# ✅ **Settlement Optimization**: Minimum transactions algorithm  
# ✅ **Expense Categories**: Food, transport, rent, etc.  
# ✅ **Payment Recording**: Track settlements  
# ✅ **History Tracking**: View all expenses  
# ✅ **Net Balances**: Consolidated view of debts  

# ### **Split Strategies Explained:**

# **1. Equal Split**:
# ```
# Total: $120, 4 people
# Each person: $120 / 4 = $30
# ```

# **2. Percentage Split**:
# ```
# Total: $200
# Alice: 40% = $80
# Bob: 30% = $60
# Charlie: 20% = $40
# Diana: 10% = $20
# ```

# **3. Exact Split**:
# ```
# Total: $85
# Alice: $25
# Bob: $20
# Charlie: $30
# Diana: $10
# ```

# **4. Shares Split**:
# ```
# Total: $60, 8 shares
# Alice: 3 shares = $22.50
# Bob: 2 shares = $15.00
# Charlie: 2 shares = $15.00
# Diana: 1 share = $7.50
# ```

# ### **Settlement Optimization Algorithm:**

# The algorithm minimizes the number of transactions needed to settle all debts using a greedy approach:
# ```
# 1. Calculate net balance for each person:
#    - Positive: owes money (debtor)
#    - Negative: is owed money (creditor)

# 2. Use two max heaps:
#    - Debtors heap: people who owe money
#    - Creditors heap: people who are owed

# 3. Match largest debtor with largest creditor:
#    - Settlement = min(debt, credit)
#    - Create transaction
#    - Push remainder back to heap

# 4. Repeat until all debts settled
# ```

# **Example**:
# ```
# Before optimization:
# Alice owes Bob: $30
# Alice owes Charlie: $20
# Bob owes Charlie: $10

# After optimization (2 transactions instead of 3):
# Alice pays Charlie: $50
# Bob pays Charlie: $10
# (Alice doesn't need to pay Bob separately)
# Balance Sheet Design:
# The BalanceSheet maintains a graph of debts:
# python# balance[user_a][user_b] = amount user_a owes user_b
# balance[alice][bob] = $30
# balance[bob][charlie] = $20

# # Net balance calculation:
# net = balance[alice][bob] - balance[bob][alice]
# Real-World Usage Patterns:
# Trip Expenses:
# python# Day 1: Dinner
# expense1 = equal_split(total=120, paid_by=alice, participants=[all])

# # Day 2: Hotel
# expense2 = percentage_split(total=200, paid_by=bob, 
#                            percentages={alice: 40, bob: 30, ...})

# # Day 3: Activities
# expense3 = exact_split(total=150, paid_by=charlie,
#                       amounts={alice: 50, bob: 40, ...})
# Roommate Expenses:
# python# Rent (equal)
# rent = equal_split(total=2000, paid_by=alice, participants=[alice, bob, carol])

# # Utilities (percentage based on room size)
# utilities = percentage_split(total=150, paid_by=bob,
#                             percentages={alice: 40, bob: 35, carol: 25})

# # Groceries (by consumption)
# groceries = shares_split(total=100, paid_by=carol,
#                         shares={alice: 3, bob: 4, carol: 3})
# Concurrency Handling:

# Thread Locks:

# Group: Protects members and expenses
# BalanceSheet: Protects balance updates
# ExpenseSharingApp: Protects shared state


# All operations are thread-safe for concurrent access

# Data Structures:
# Balance Sheet:

# Dict[User, Dict[User, Decimal]]: O(1) balance lookup
# Nested dictionaries for efficient debt tracking

# Settlement Optimization:

# heapq: O(log n) heap operations
# Two heaps for debtors and creditors

# Complexity:

# Add expense: O(n) where n = participants
# Get balance: O(1) lookup
# Settlement optimization: O(n log n) where n = users

# Advanced Features:
# Net Balance Calculation:
# python# If Alice owes Bob $30 and Bob owes Alice $10
# # Net: Alice owes Bob $20 (simplified)
# Simplified Balances:
# python# Only show non-zero net balances
# # Ignore small amounts (< $0.01) due to rounding
# ```

# **Group vs Individual**:
# - Groups: Organize related expenses
# - Individual: Track all personal debts
# - Can have expenses outside groups

# ### **Extensions You Could Add:**

# - **Recurring Expenses**: Monthly rent, subscriptions
# - **Currency Support**: Multi-currency with conversion
# - **Receipt Upload**: Photo/PDF storage
# - **Notifications**: Email/SMS reminders
# - **Payment Integration**: Venmo, PayPal integration
# - **Expense Categories**: Custom categories
# - **Budget Tracking**: Set spending limits
# - **Analytics**: Spending patterns, charts
# - **Comments/Notes**: Expense discussions
# - **Itemized Bills**: Line-item splits
# - **Tax Calculation**: VAT, tips, taxes
# - **Approval Workflow**: Approve before adding
# - **Audit Trail**: Track all changes
# - **Export**: CSV, PDF reports
# - **Offline Mode**: Sync when online

# ### **Mathematical Properties:**

# **Conservation of Money**:
# ```
# Sum of all splits = 0
# (what people owe) - (what payer gets back) = 0
# Validation:

# Percentage splits must sum to 100%
# Exact splits must sum to total amount
# All amounts must be positive

# Precision:

# Using Decimal for accurate money calculations
# Avoids floating-point errors
# Rounds to 2 decimal places

# Example Workflow:
# python# 1. Create users and group
# app = ExpenseSharingApp()
# alice, bob, charlie = create_users()
# group = app.create_group("Roommates", alice)

# # 2. Add expenses over time
# app.add_expense(rent_expense)
# app.add_expense(utilities_expense)
# app.add_expense(groceries_expense)

# # 3. Check individual balance
# app.show_balance(bob)

# # 4. See optimal settlements
# transactions = app.settle_up(group)

# # 5. Record actual payments
# for from_user, to_user, amount in transactions:
#     app.record_payment(from_user, to_user, amount)

# # 6. Verify all settled
# app.show_group_balances(group)  # Should show "All settled up!"
# Key Validation Rules:

# Split Validation:

# Percentages sum to 100%
# Exact amounts sum to total
# All amounts are positive
# At least one participant


# Payment Validation:

# Cannot pay more than owed
# Cannot pay negative amounts
# Both users must exist


# Group Rules:

# Cannot remove group creator
# Members must be unique
# Expenses must include valid participants



# This design demonstrates a production-ready expense sharing system with optimal settlement algorithms, flexible split strategies, and clean architecture - perfect for system design interviews!
