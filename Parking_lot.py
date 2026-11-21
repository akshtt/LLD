import math
import threading
from abc import ABC, abstractmethod
from enum import Enum


class VehicleType(Enum):
    CAR = 1
    TRUCK = 2
    ELECTRIC = 3
    VAN = 4
    MOTORBIKE = 5


class ParkingSpotType(Enum):
    HANDICAPPED = 1
    COMPACT = 2
    LARGE = 3
    MOTORBIKE = 4
    ELECTRIC = 5


class AccountStatus(Enum):
    ACTIVE = 1
    BLOCKED = 2
    BANNED = 3
    COMPROMISED = 4
    ARCHIVED = 5
    UNKNOWN = 6


class ParkingTicketStatus(Enum):
    ACTIVE = 1
    PAID = 2
    LOST = 3


class Address:
    def __init__(self, street, city, state, zip_code, country):
        self.street_address = street
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.country = country


class Person:
    def __init__(self, name, address, email, phone):
        self.name = name
        self.address = address
        self.email = email
        self.phone = phone


class ParkingFullException(Exception):
    """Raised when no spot of a suitable type is free."""


class ParkingSpot(ABC):
    def __init__(self, number, spot_type):
        self.number = number
        self.spot_type = spot_type
        self.free = True
        self.vehicle = None

    def get_number(self):
        return self.number

    def get_type(self):
        return self.spot_type

    def is_free(self):
        return self.free

    def get_vehicle(self):
        return self.vehicle

    def assign_vehicle(self, vehicle):
        if not self.free:
            return False
        self.vehicle = vehicle
        # Assign to the attribute, not to a local name, or the spot never
        # actually changes state.
        self.free = False
        return True

    def remove_vehicle(self):
        if self.free:
            return False
        self.vehicle = None
        self.free = True
        return True


class HandicappedSpot(ParkingSpot):
    def __init__(self, number):
        super().__init__(number, ParkingSpotType.HANDICAPPED)


class CompactSpot(ParkingSpot):
    def __init__(self, number):
        super().__init__(number, ParkingSpotType.COMPACT)


class LargeSpot(ParkingSpot):
    def __init__(self, number):
        super().__init__(number, ParkingSpotType.LARGE)


class MotorbikeSpot(ParkingSpot):
    def __init__(self, number):
        super().__init__(number, ParkingSpotType.MOTORBIKE)


class ElectricSpot(ParkingSpot):
    """The only subclass that adds anything of its own: an electric spot owns
    the panel a driver uses to pay for charging."""

    def __init__(self, number, electric_panel=None):
        super().__init__(number, ParkingSpotType.ELECTRIC)
        self.electric_panel = electric_panel

    def get_electric_panel(self):
        return self.electric_panel

class Vehicle(ABC):
    def __init__(self, license_number, vehicle_type):
        self.license_number = license_number
        self.vehicle_type = vehicle_type
        self.ticket = None

    def get_license_number(self):
        return self.license_number

    def get_type(self):
        return self.vehicle_type

    def get_ticket(self):
        return self.ticket

    def assign_ticket(self, ticket):
        self.ticket = ticket

    def spot_types_that_fit(self):
        """Which spot types this vehicle may use, best fit first. Keeping the
        rule on the vehicle means adding a vehicle type does not force a
        change in ParkingLot."""
        if self.vehicle_type == VehicleType.MOTORBIKE:
            return [ParkingSpotType.MOTORBIKE]
        if self.vehicle_type in (VehicleType.TRUCK, VehicleType.VAN):
            return [ParkingSpotType.LARGE]
        if self.vehicle_type == VehicleType.ELECTRIC:
            return [ParkingSpotType.ELECTRIC, ParkingSpotType.COMPACT,
                    ParkingSpotType.LARGE]
        return [ParkingSpotType.COMPACT, ParkingSpotType.LARGE]


class Car(Vehicle):
    def __init__(self, license_number):
        super().__init__(license_number, VehicleType.CAR)


class Van(Vehicle):
    def __init__(self, license_number):
        super().__init__(license_number, VehicleType.VAN)


class Truck(Vehicle):
    def __init__(self, license_number):
        super().__init__(license_number, VehicleType.TRUCK)


class Motorbike(Vehicle):
    def __init__(self, license_number):
        super().__init__(license_number, VehicleType.MOTORBIKE)


class ElectricCar(Vehicle):
    def __init__(self, license_number):
        super().__init__(license_number, VehicleType.ELECTRIC)


class ParkingDisplayBoard:
    """The board shows how many spots of each type are free. Counting is
    cheaper and steadier than tracking one example spot per type, which has to
    be recomputed every time that one spot fills up."""

    def __init__(self, board_id):
        self.board_id = board_id
        self.free_counts = {spot_type: 0 for spot_type in ParkingSpotType}

    def update(self, free_counts):
        self.free_counts = dict(free_counts)

    def get_free_count(self, spot_type):
        return self.free_counts.get(spot_type, 0)

    def show_free_spots(self):
        lines = []
        for spot_type in ParkingSpotType:
            count = self.free_counts.get(spot_type, 0)
            name = spot_type.name.capitalize()
            lines.append(f"{name} is full" if count == 0
                         else f"Free {name}: {count}")
        return "\n".join(lines)


class ParkingFloor:
    def __init__(self, name):
        self.name = name
        # One map of every spot, plus an index by type. Adding a spot type does
        # not mean adding another map and another branch in five methods.
        self.spots = {}
        self.spots_by_type = {spot_type: [] for spot_type in ParkingSpotType}
        self.display_board = ParkingDisplayBoard(f"{name}-board")

    def get_name(self):
        return self.name

    def get_display_board(self):
        return self.display_board

    def add_parking_spot(self, spot):
        if spot.get_type() not in self.spots_by_type:
            print("Wrong parking spot type!")
            return False
        self.spots[spot.get_number()] = spot
        self.spots_by_type[spot.get_type()].append(spot)
        self.update_display_board()
        return True

    def find_available_spot(self, vehicle):
        """The first free spot of a type this vehicle fits in, or None."""
        for spot_type in vehicle.spot_types_that_fit():
            for spot in self.spots_by_type[spot_type]:
                if spot.is_free():
                    return spot
        return None

    def assign_vehicle_to_spot(self, vehicle, spot):
        if not spot.assign_vehicle(vehicle):
            return False
        self.update_display_board()
        return True

    def free_spot(self, spot):
        if not spot.remove_vehicle():
            return False
        self.update_display_board()
        return True

    def free_count(self, spot_type):
        return sum(1 for spot in self.spots_by_type[spot_type] if spot.is_free())

    def is_full(self):
        return all(not spot.is_free() for spot in self.spots.values())

    def update_display_board(self):
        self.display_board.update(
            {spot_type: self.free_count(spot_type) for spot_type in ParkingSpotType})

class ParkingRate:
    """The hourly rate card: 4.00 for the first hour, 3.50 for the second and
    third, 2.50 for every hour after that."""

    FIRST_HOUR = 4.0
    SECOND_AND_THIRD_HOUR = 3.5
    REMAINING_HOURS = 2.5

    def calculate(self, hours):
        if hours <= 0:
            return 0.0
        amount = ParkingRate.FIRST_HOUR
        amount += min(max(hours - 1, 0), 2) * ParkingRate.SECOND_AND_THIRD_HOUR
        amount += max(hours - 3, 0) * ParkingRate.REMAINING_HOURS
        return amount


class ParkingTicket:
    """A ticket points at the spot the vehicle is actually in, which is what
    makes it possible to find the vehicle again at the exit."""

    def __init__(self, ticket_number, vehicle, spot, issued_at_minute):
        self.ticket_number = ticket_number
        self.vehicle = vehicle
        self.spot = spot
        self.issued_at_minute = issued_at_minute
        self.paid_at_minute = None
        self.amount = 0.0
        self.status = ParkingTicketStatus.ACTIVE
        self.payment = None

    def get_ticket_number(self):
        return self.ticket_number

    def get_spot(self):
        return self.spot

    def get_vehicle(self):
        return self.vehicle

    def get_amount(self):
        return self.amount

    def get_status(self):
        return self.status

    def hours_parked(self, now_minute):
        """Part hours are charged as full hours, which is how car parks bill."""
        return max(1, math.ceil((now_minute - self.issued_at_minute) / 60))

    def is_paid(self):
        return self.status == ParkingTicketStatus.PAID

    def mark_paid(self, amount, payment, now_minute):
        self.amount = amount
        self.payment = payment
        self.paid_at_minute = now_minute
        self.status = ParkingTicketStatus.PAID


class Payment(ABC):
    def __init__(self, amount):
        self.amount = amount
        self.completed = False

    def get_amount(self):
        return self.amount

    def is_completed(self):
        return self.completed

    @abstractmethod
    def initiate_transaction(self):
        """Returns True when the money has been taken."""


class CashTransaction(Payment):
    def __init__(self, amount, cash_tendered):
        super().__init__(amount)
        self.cash_tendered = cash_tendered

    def initiate_transaction(self):
        if self.cash_tendered < self.amount:
            return False
        self.completed = True
        return True


class CreditCardTransaction(Payment):
    def __init__(self, amount, card_number):
        super().__init__(amount)
        self.card_number = card_number

    def initiate_transaction(self):
        # A real system calls out to the payment gateway here.
        self.completed = True
        return True

class Account(ABC):
    def __init__(self, user_name, password, person,
                 status=AccountStatus.ACTIVE):
        self.user_name = user_name
        self.password = password
        self.person = person
        self.status = status

    def reset_password(self, new_password):
        # A real system stores a hash, never the password itself.
        self.password = new_password
        return True


class Admin(Account):
    def add_parking_floor(self, parking_lot, floor):
        return parking_lot.add_parking_floor(floor)

    def add_parking_spot(self, parking_lot, floor_name, spot):
        floor = parking_lot.get_floor(floor_name)
        if floor is None:
            return False
        floor.add_parking_spot(spot)
        return True

    def add_entrance_panel(self, parking_lot, panel):
        return parking_lot.add_entrance_panel(panel)

    def add_exit_panel(self, parking_lot, panel):
        return parking_lot.add_exit_panel(panel)


class ParkingAttendant(Account):
    def process_ticket(self, parking_lot, ticket_number, payment):
        """An attendant can take a payment on the customer's behalf."""
        return parking_lot.pay_ticket(ticket_number, payment)


class ParkingLot:
    """One object of this class exists per car park, which is what the
    singleton below enforces."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, name, address):
        self.name = name
        self.address = address
        self.parking_rate = ParkingRate()
        self.floors = {}
        self.entrance_panels = {}
        self.exit_panels = {}
        self.active_tickets = {}
        self.next_ticket_number = 1
        # Two entrances can issue a ticket at the same instant, so the code
        # that hands out a spot has to run one caller at a time.
        self.ticket_lock = threading.Lock()

    @classmethod
    def get_instance(cls, name="Main Lot", address=None):
        # The lock matters: without it two threads can both see None and each
        # build a lot, and then the system has two.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ParkingLot(name, address)
        return cls._instance

    def add_parking_floor(self, floor):
        self.floors[floor.get_name()] = floor
        return True

    def get_floor(self, name):
        return self.floors.get(name)

    def add_entrance_panel(self, panel):
        self.entrance_panels[panel.get_id()] = panel
        return True

    def add_exit_panel(self, panel):
        self.exit_panels[panel.get_id()] = panel
        return True

    def is_full(self, vehicle):
        return self.find_available_spot(vehicle) is None

    def find_available_spot(self, vehicle):
        for floor in self.floors.values():
            spot = floor.find_available_spot(vehicle)
            if spot is not None:
                return floor, spot
        return None

    def get_new_parking_ticket(self, vehicle, now_minute):
        with self.ticket_lock:
            found = self.find_available_spot(vehicle)
            if found is None:
                raise ParkingFullException("Parking is full")
            floor, spot = found

            ticket = ParkingTicket(f"T{self.next_ticket_number:05d}",
                                   vehicle, spot, now_minute)
            self.next_ticket_number += 1
            floor.assign_vehicle_to_spot(vehicle, spot)
            vehicle.assign_ticket(ticket)
            self.active_tickets[ticket.get_ticket_number()] = ticket
            return ticket

    def get_ticket(self, ticket_number):
        return self.active_tickets.get(ticket_number)

    def calculate_amount(self, ticket, now_minute):
        return self.parking_rate.calculate(ticket.hours_parked(now_minute))

    def pay_ticket(self, ticket_number, payment, now_minute):
        ticket = self.active_tickets.get(ticket_number)
        if ticket is None or ticket.is_paid():
            return False
        amount = self.calculate_amount(ticket, now_minute)
        if payment.get_amount() < amount or not payment.initiate_transaction():
            return False
        ticket.mark_paid(amount, payment, now_minute)
        return True

    def exit_vehicle(self, ticket_number):
        """A paid ticket releases the spot. This is only possible because the
        ticket knows which spot the vehicle went into."""
        ticket = self.active_tickets.get(ticket_number)
        if ticket is None or not ticket.is_paid():
            return False
        spot = ticket.get_spot()
        for floor in self.floors.values():
            if spot.get_number() in floor.spots:
                floor.free_spot(spot)
                break
        del self.active_tickets[ticket_number]
        return True

class EntrancePanel:
    def __init__(self, panel_id, parking_lot):
        self.panel_id = panel_id
        self.parking_lot = parking_lot

    def get_id(self):
        return self.panel_id

    def print_ticket(self, vehicle, now_minute):
        return self.parking_lot.get_new_parking_ticket(vehicle, now_minute)


class ExitPanel:
    def __init__(self, panel_id, parking_lot):
        self.panel_id = panel_id
        self.parking_lot = parking_lot

    def get_id(self):
        return self.panel_id

    def scan_ticket(self, ticket_number, now_minute):
        ticket = self.parking_lot.get_ticket(ticket_number)
        if ticket is None:
            return None
        # A ticket already paid at an info portal owes nothing at the exit.
        if ticket.is_paid():
            return 0.0
        return self.parking_lot.calculate_amount(ticket, now_minute)

    def process_payment(self, ticket_number, payment, now_minute):
        return self.parking_lot.pay_ticket(ticket_number, payment, now_minute)


class CustomerInfoPortal:
    """Requirement 6: a driver who pays at a floor portal owes nothing at the
    exit, so the portal marks the same ticket as paid."""

    def __init__(self, portal_id, parking_lot):
        self.portal_id = portal_id
        self.parking_lot = parking_lot

    def get_id(self):
        return self.portal_id

    def pay_ticket(self, ticket_number, payment, now_minute):
        return self.parking_lot.pay_ticket(ticket_number, payment, now_minute)


class ElectricPanel:
    def __init__(self, panel_id, rate_per_hour):
        self.panel_id = panel_id
        self.rate_per_hour = rate_per_hour
        self.charging_since_minute = None

    def get_id(self):
        return self.panel_id

    def start_charging(self, now_minute):
        self.charging_since_minute = now_minute

    def cost_of_charging(self, now_minute):
        if self.charging_since_minute is None:
            return 0.0
        hours = max(1, math.ceil((now_minute - self.charging_since_minute) / 60))
        return hours * self.rate_per_hour


def build_lot():
    lot = ParkingLot.get_instance("Downtown Parking", None)
    floor = ParkingFloor("Ground")
    floor.add_parking_spot(HandicappedSpot("G-H1"))
    floor.add_parking_spot(CompactSpot("G-C1"))
    floor.add_parking_spot(CompactSpot("G-C2"))
    floor.add_parking_spot(LargeSpot("G-L1"))
    floor.add_parking_spot(MotorbikeSpot("G-M1"))
    floor.add_parking_spot(ElectricSpot("G-E1", ElectricPanel("panel-1", 2.0)))
    lot.add_parking_floor(floor)
    entrance = EntrancePanel("entrance-1", lot)
    exit_panel = ExitPanel("exit-1", lot)
    lot.add_entrance_panel(entrance)
    lot.add_exit_panel(exit_panel)
    return lot, floor, entrance, exit_panel


def main():
    lot, floor, entrance, exit_panel = build_lot()

    print("Rate card:")
    rate = ParkingRate()
    for hours in (1, 2, 3, 5):
        print(f"  {hours} hour(s): {rate.calculate(hours):.2f}")

    print("\nParking a car:")
    car = Car("KA-01-HH-1234")
    ticket = entrance.print_ticket(car, 0)
    print(f"  ticket {ticket.get_ticket_number()} for spot "
          f"{ticket.get_spot().get_number()} ({ticket.get_spot().get_type().name})")
    print(f"  spot is free now: {ticket.get_spot().is_free()}")

    print("\nA motorbike cannot take a car spot:")
    bike = Motorbike("KA-01-MM-9999")
    bike_ticket = entrance.print_ticket(bike, 0)
    print(f"  bike went to {bike_ticket.get_spot().get_number()} "
          f"({bike_ticket.get_spot().get_type().name})")

    print("\nDisplay board:")
    print("  " + floor.get_display_board().show_free_spots().replace("\n", "\n  "))

    print("\nLeaving after 150 minutes:")
    due = exit_panel.scan_ticket(ticket.get_ticket_number(), 150)
    print(f"  hours charged: {ticket.hours_parked(150)}, amount due: {due:.2f}")
    paid = exit_panel.process_payment(ticket.get_ticket_number(),
                                      CreditCardTransaction(due, "4111"), 150)
    print(f"  payment accepted: {paid}")
    print(f"  vehicle released: {lot.exit_vehicle(ticket.get_ticket_number())}")
    print(f"  spot free again: {ticket.get_spot().is_free()}")

    print("\nFilling the lot:")
    try:
        for i in range(10):
            entrance.print_ticket(Truck(f"TRK-{i}"), 0)
    except ParkingFullException as error:
        print(f"  stopped with: {error}")


main()
