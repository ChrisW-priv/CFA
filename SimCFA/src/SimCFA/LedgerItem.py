from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto

from dateutil.relativedelta import relativedelta

from SimCFA.builder import GenericBuilder
from SimCFA.compound_interest_calculator import compound_interest_calc

DAYS_YEAR = 365


class LedgerItemType(Enum):
    Asset = auto()
    Liability = auto()


@dataclass
class LedgerItemProperties:
    quantity: int
    acquired_on: int  # int number of simulation day
    item_type: LedgerItemType = LedgerItemType.Asset  # helper category to allow easy grouping in the future


@dataclass
class LedgerItem(ABC):
    properties: LedgerItemProperties

    @abstractmethod
    def get_value(self, n_day: int) -> int:
        """will return a value of the object if it was to be sold on the very day passed as param"""


@dataclass
class Cash(LedgerItem):
    def get_value(self, n_day: int) -> int:
        return self.properties.quantity


@dataclass
class Bond(LedgerItem):
    percent: int
    duration: relativedelta
    rebuy_cost: int
    pre_maturity_buy_back_penalty: int
    price: int = 100_00
    capitalisation_periods: int = 1

    def get_value(self, n_day: int):
        days_passed = n_day - self.properties.acquired_on
        use_penalty = self.pre_maturity_buy_back_penalty
        if days_passed > self.max_duration_in_days:
            days_passed = self.max_duration_in_days
            use_penalty = 0

        days_as_year_float = days_passed / DAYS_YEAR

        x = compound_interest_calc(self.percent, days_as_year_float, self.capitalisation_periods)
        cash_received = x * self.price
        return (cash_received - use_penalty) * self.properties.quantity

    @property
    def max_duration_in_days(self):
        year_duration = self.duration.years
        month_duration = self.duration.months

        MONTHS_IN_A_YEAR = 12
        duration_as_full_year_float = year_duration + month_duration / MONTHS_IN_A_YEAR
        DAYS_YEAR = 365
        return duration_as_full_year_float * DAYS_YEAR


bond_builder = GenericBuilder(Bond)

year_bond_builder = (
    bond_builder.set("percent", 6)
    .set("duration", relativedelta(years=1))
    .set("rebuy_cost", 99_90)
    .set("pre_maturity_buy_back_penalty", 70)
    .set("price", 100_00)
    .set("capitalisation_periods", 100_00)
)

three_year_bond_builder = (
    bond_builder.set("percent", 6.6)
    .set("duration", relativedelta(years=3))
    .set("rebuy_cost", 99_90)
    .set("pre_maturity_buy_back_penalty", 70)
    .set("price", 100_00)
    .set("capitalisation_periods", 1)
)


@dataclass
class Debt(LedgerItem):
    percent: int

    def get_value(self, n_day: int) -> int:
        acq_on = self.properties.acquired_on
        days_passed = n_day - acq_on
        multiply = compound_interest_calc(self.percent, days_passed / DAYS_YEAR)
        value = self.properties.quantity * multiply
        return -value

