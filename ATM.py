from abc import ABC, abstractmethod
from enum import Enum


class TransactionType(Enum):
    BALANCE_INQUIRY = 1
    DEPOSIT_CASH = 2
    DEPOSIT_CHECK = 3
    WITHDRAW = 4
    TRANSFER = 5


class TransactionStatus(Enum):
    SUCCESS = 1
    FAILURE = 2
    BLOCKED = 3
    FULL = 4
    PARTIAL = 5
    NONE = 6


class CustomerStatus(Enum):
    ACTIVE = 1
    BLOCKED = 2
    BANNED = 3
    COMPROMISED = 4
    ARCHIVED = 5
    CLOSED = 6
    UNKNOWN = 7


class Constants:
    # The dispenser only holds these notes, so every withdrawal has to be a
    # multiple of the smallest one.
    BILL_VALUES = [20, 5]
    SMALLEST_BILL = 5


class Address:
    def __init__(self, street, city, state, zip_code, country):
        self.street_address = street
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.country = country

class Account(ABC):
    def __init__(self, account_number, total_balance):
        self.account_number = account_number
        self.total_balance = total_balance
        self.available_balance = total_balance

    def get_account_number(self):
        return self.account_number

    def get_available_balance(self):
        return self.available_balance

    def get_total_balance(self):
        return self.total_balance

    def can_withdraw(self, amount):
        return 0 < amount <= self.available_balance

    def withdraw(self, amount):
        if not self.can_withdraw(amount):
            return False
        self.available_balance -= amount
        self.total_balance -= amount
        return True

    def deposit(self, amount, available_now=True):
        """A cash deposit is spendable at once. A check is not, so the total
        goes up while the available balance waits for the check to clear."""
        if amount <= 0:
            return False
        self.total_balance += amount
        if available_now:
            self.available_balance += amount
        return True


class SavingAccount(Account):
    def __init__(self, account_number, total_balance, withdraw_limit):
        super().__init__(account_number, total_balance)
        self.withdraw_limit = withdraw_limit

    def can_withdraw(self, amount):
        # A savings account adds a per transaction cap on top of the balance.
        return super().can_withdraw(amount) and amount <= self.withdraw_limit


class CheckingAccount(Account):
    def __init__(self, account_number, total_balance, debit_card_number):
        super().__init__(account_number, total_balance)
        self.debit_card_number = debit_card_number


class Card:
    def __init__(self, card_number, customer_name, card_expiry, pin,
                 billing_address=None):
        self.card_number = card_number
        self.customer_name = customer_name
        self.card_expiry = card_expiry
        self.pin = pin
        self.billing_address = billing_address

    def get_card_number(self):
        return self.card_number

    def get_billing_address(self):
        return self.billing_address

    def is_expired(self, today):
        return today > self.card_expiry

    def verify_pin(self, entered):
        # A real machine sends the PIN to the bank rather than comparing it here.
        return self.pin == entered


class Customer:
    def __init__(self, name, email, phone, address, card, accounts):
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address
        self.status = CustomerStatus.ACTIVE
        self.card = card
        self.accounts = {a.get_account_number(): a for a in accounts}

    def get_name(self):
        return self.name

    def get_card(self):
        return self.card

    def get_status(self):
        return self.status

    def set_status(self, status):
        self.status = status

    def get_billing_address(self):
        return self.card.get_billing_address()

    def get_account(self, account_number):
        return self.accounts.get(account_number)

    def get_accounts(self):
        return list(self.accounts.values())
class CashDispenser:
    """The dispenser knows what notes it holds. Working out whether an amount
    can be made up is its job, not the transaction's."""

    def __init__(self, bills):
        # bills maps a note value to how many of them are loaded.
        self.bills = dict(bills)

    def get_bills(self):
        return dict(self.bills)

    def total_cash(self):
        return sum(value * count for value, count in self.bills.items())

    def plan(self, amount):
        """Largest notes first. Returns None when the amount cannot be made."""
        remaining = amount
        used = {}
        for value in Constants.BILL_VALUES:
            available = self.bills.get(value, 0)
            take = min(int(remaining // value), available)
            if take:
                used[value] = take
                remaining -= take * value
        return used if remaining == 0 else None

    def can_dispense_cash(self, amount):
        return self.plan(amount) is not None

    def dispense_cash(self, amount):
        used = self.plan(amount)
        if used is None:
            return False
        for value, count in used.items():
            self.bills[value] -= count
        return True

    def load(self, value, count):
        self.bills[value] = self.bills.get(value, 0) + count
        return True


class CardReader:
    """Requirement 1's card reader. It holds the card for as long as the session
    lasts, which is what the lesson means when it says the card is kept until
    the customer ends the session."""

    def __init__(self):
        self.current_card = None

    def has_card(self):
        return self.current_card is not None

    def get_current_card(self):
        return self.current_card

    def insert_card(self, card):
        if self.has_card():
            return False
        self.current_card = card
        return True

    def eject_card(self):
        card = self.current_card
        self.current_card = None
        return card


class Keypad:
    """The keypad is fed a list of inputs so the machine can be run without a
    person standing in front of it."""

    def __init__(self, inputs=None):
        self.inputs = list(inputs or [])

    def get_input(self):
        return self.inputs.pop(0) if self.inputs else ""


class Screen:
    def show_message(self, message):
        print(f"    [screen] {message}")
        return True


class Printer:
    def print_receipt(self, transaction, balance):
        print(f"    [receipt] {transaction.get_type().name} "
              f"{transaction.get_status().name}, balance {balance:.2f}")
        return True


class DepositSlot(ABC):
    def __init__(self):
        self.total_amount = 0.0

    def get_total_amount(self):
        return self.total_amount

    def receive(self, amount):
        self.total_amount += amount
        return True


class CashDepositSlot(DepositSlot):
    def receive_dollar_bill(self, value, count):
        return self.receive(value * count)


class CheckDepositSlot(DepositSlot):
    def get_check_amount(self):
        return self.total_amount

class Transaction(ABC):
    def __init__(self, transaction_id, creation_time):
        self.transaction_id = transaction_id
        self.creation_time = creation_time
        self.status = TransactionStatus.NONE

    def get_id(self):
        return self.transaction_id

    def get_status(self):
        return self.status

    @abstractmethod
    def get_type(self):
        """Which of the five transactions this is."""

    @abstractmethod
    def execute(self, atm, account):
        """Do the work and set the status. Returns True on success."""


class BalanceInquiry(Transaction):
    def __init__(self, transaction_id, creation_time):
        super().__init__(transaction_id, creation_time)
        self.balance = 0.0

    def get_type(self):
        return TransactionType.BALANCE_INQUIRY

    def get_balance(self):
        return self.balance

    def execute(self, atm, account):
        self.balance = account.get_available_balance()
        self.status = TransactionStatus.SUCCESS
        return True


class Deposit(Transaction):
    def __init__(self, transaction_id, creation_time, amount):
        super().__init__(transaction_id, creation_time)
        self.amount = amount

    def get_amount(self):
        return self.amount


class CashDeposit(Deposit):
    def __init__(self, transaction_id, creation_time, amount, cash_deposit_limit=10000):
        super().__init__(transaction_id, creation_time, amount)
        self.cash_deposit_limit = cash_deposit_limit

    def get_type(self):
        return TransactionType.DEPOSIT_CASH

    def execute(self, atm, account):
        if self.amount > self.cash_deposit_limit:
            self.status = TransactionStatus.FAILURE
            return False
        atm.get_cash_deposit_slot().receive(self.amount)
        # Cash is spendable straight away.
        account.deposit(self.amount, available_now=True)
        self.status = TransactionStatus.SUCCESS
        return True


class CheckDeposit(Deposit):
    def __init__(self, transaction_id, creation_time, amount, check_number, bank_code):
        super().__init__(transaction_id, creation_time, amount)
        self.check_number = check_number
        self.bank_code = bank_code

    def get_type(self):
        return TransactionType.DEPOSIT_CHECK

    def get_check_number(self):
        return self.check_number

    def execute(self, atm, account):
        atm.get_check_deposit_slot().receive(self.amount)
        # A check has to clear, so the money is not available yet.
        account.deposit(self.amount, available_now=False)
        self.status = TransactionStatus.SUCCESS
        return True


class Withdraw(Transaction):
    def __init__(self, transaction_id, creation_time, amount):
        super().__init__(transaction_id, creation_time)
        self.amount = amount

    def get_type(self):
        return TransactionType.WITHDRAW

    def get_amount(self):
        return self.amount

    def execute(self, atm, account):
        if self.amount % Constants.SMALLEST_BILL != 0:
            print(f"    amount must be a multiple of {Constants.SMALLEST_BILL}")
            self.status = TransactionStatus.FAILURE
            return False
        if not account.can_withdraw(self.amount):
            print("    insufficient funds or over the withdrawal limit")
            self.status = TransactionStatus.FAILURE
            return False
        if not atm.get_cash_dispenser().can_dispense_cash(self.amount):
            print("    the machine cannot make up that amount")
            self.status = TransactionStatus.FAILURE
            return False
        # The money leaves the account only once the notes are counted out.
        atm.get_cash_dispenser().dispense_cash(self.amount)
        account.withdraw(self.amount)
        self.status = TransactionStatus.SUCCESS
        return True


class Transfer(Transaction):
    def __init__(self, transaction_id, creation_time, amount, destination_account):
        super().__init__(transaction_id, creation_time)
        self.amount = amount
        self.destination_account = destination_account

    def get_type(self):
        return TransactionType.TRANSFER

    def get_destination_account(self):
        return self.destination_account

    def execute(self, atm, account):
        if not account.can_withdraw(self.amount):
            print("    insufficient funds")
            self.status = TransactionStatus.FAILURE
            return False
        account.withdraw(self.amount)
        self.destination_account.deposit(self.amount, available_now=True)
        self.status = TransactionStatus.SUCCESS
        return True
class Bank:
    def __init__(self, name, bank_code):
        self.name = name
        self.bank_code = bank_code
        self.atms = {}

    def get_bank_code(self):
        return self.bank_code

    def add_atm(self, atm):
        self.atms[atm.get_id()] = atm
        return True

    def get_atms(self):
        return list(self.atms.values())


class ATM:
    """One customer at a time, which is why the current customer and account
    are held on the machine while a session is open."""

    def __init__(self, atm_id, location, card_reader, cash_dispenser, keypad, screen,
                 printer, cash_deposit_slot, check_deposit_slot):
        self.atm_id = atm_id
        self.location = location
        self.card_reader = card_reader
        self.cash_dispenser = cash_dispenser
        self.keypad = keypad
        self.screen = screen
        self.printer = printer
        # These are the slots the customer posts money into. The deposit
        # TRANSACTIONS are a separate idea and live on Transaction.
        self.cash_deposit_slot = cash_deposit_slot
        self.check_deposit_slot = check_deposit_slot
        self.current_customer = None
        self.current_account = None

    def get_id(self):
        return self.atm_id

    def get_card_reader(self):
        return self.card_reader

    def get_cash_dispenser(self):
        return self.cash_dispenser

    def get_cash_deposit_slot(self):
        return self.cash_deposit_slot

    def get_check_deposit_slot(self):
        return self.check_deposit_slot

    def is_busy(self):
        return self.current_customer is not None

    def authenticate_user(self, customer, entered_pin, today):
        if self.is_busy():
            self.screen.show_message("Machine is busy")
            return False
        # The card goes in first and comes back out on any failure, which is
        # why every branch below ejects before it returns.
        self.card_reader.insert_card(customer.get_card())
        card = self.card_reader.get_current_card()
        if customer.get_status() != CustomerStatus.ACTIVE:
            self.screen.show_message("This card is blocked")
            self.card_reader.eject_card()
            return False
        if card.is_expired(today):
            self.screen.show_message("This card has expired")
            self.card_reader.eject_card()
            return False
        if not card.verify_pin(entered_pin):
            self.screen.show_message("Incorrect PIN")
            self.card_reader.eject_card()
            return False
        self.current_customer = customer
        self.screen.show_message(f"Welcome {customer.get_name()}")
        return True

    def select_account(self, account_number):
        if self.current_customer is None:
            return False
        account = self.current_customer.get_account(account_number)
        if account is None:
            self.screen.show_message("No such account")
            return False
        self.current_account = account
        return True

    def make_transaction(self, transaction):
        if self.current_customer is None or self.current_account is None:
            self.screen.show_message("Insert a card first")
            return False
        done = transaction.execute(self, self.current_account)
        self.printer.print_receipt(transaction, self.current_account.get_available_balance())
        return done

    def end_session(self):
        self.current_customer = None
        self.current_account = None
        self.card_reader.eject_card()
        self.screen.show_message("Please take your card")
        return True


def main():
    bank = Bank("Bank of Springfield", "BOS")
    dispenser = CashDispenser({20: 10, 5: 10})
    atm = ATM(1, None, CardReader(), dispenser, Keypad(), Screen(), Printer(),
              CashDepositSlot(), CheckDepositSlot())
    bank.add_atm(atm)

    checking = CheckingAccount(1001, 500.0, "4111")
    savings = SavingAccount(2002, 900.0, withdraw_limit=200.0)
    card = Card("5555", "Alice", card_expiry=30, pin=1234)
    alice = Customer("Alice", "alice@example.com", "555", None, card,
                     [checking, savings])

    print(f"Machine holds {dispenser.total_cash():.0f} in notes {dispenser.get_bills()}")

    print("\nWrong PIN is refused:")
    print(f"  authenticated: {atm.authenticate_user(alice, 9999, today=1)}")
    print(f"  card returned: {not atm.get_card_reader().has_card()}")

    print("\nCorrect PIN opens a session:")
    print(f"  authenticated: {atm.authenticate_user(alice, 1234, today=1)}")
    print(f"  card held by the reader: {atm.get_card_reader().has_card()}")
    atm.select_account(1001)

    print("\nBalance inquiry:")
    inquiry = BalanceInquiry(1, 1)
    atm.make_transaction(inquiry)
    print(f"  balance reported: {inquiry.get_balance():.2f}")

    print("\nWithdraw 85:")
    atm.make_transaction(Withdraw(2, 1, 85))
    print(f"  checking balance: {checking.get_available_balance():.2f}")
    print(f"  notes left: {dispenser.get_bills()}")

    print("\nWithdraw 83 is refused, the machine has no singles:")
    atm.make_transaction(Withdraw(3, 1, 83))

    print("\nWithdraw 600 is refused, not enough in the account:")
    atm.make_transaction(Withdraw(4, 1, 600))

    print("\nDeposit 200 in cash is available at once:")
    atm.make_transaction(CashDeposit(5, 1, 200))
    print(f"  available {checking.get_available_balance():.2f}, "
          f"total {checking.get_total_balance():.2f}")

    print("\nDeposit a 300 check has to clear first:")
    atm.make_transaction(CheckDeposit(6, 1, 300, "CHK-1", "BOS"))
    print(f"  available {checking.get_available_balance():.2f}, "
          f"total {checking.get_total_balance():.2f}")

    print("\nTransfer 100 to savings:")
    atm.make_transaction(Transfer(7, 1, 100, savings))
    print(f"  checking {checking.get_available_balance():.2f}, "
          f"savings {savings.get_available_balance():.2f}")

    print("\nThe savings withdrawal limit is 200:")
    atm.select_account(2002)
    atm.make_transaction(Withdraw(8, 1, 300))

    atm.end_session()
    print(f"\nMachine busy after the session: {atm.is_busy()}")


main()

