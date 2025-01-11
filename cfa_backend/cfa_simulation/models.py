from enum import StrEnum, auto

from django.db import models


class SimulationConfig(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    include_inflation = models.BooleanField(default=False)


class ValidChoicesMixin:
    @classmethod
    def choices(cls):
        return list(map(lambda c: (c, c.value), cls))


class ValidEvents(ValidChoicesMixin, StrEnum):
    monthly_income = auto()
    house_buy = auto()
    bonds_buy = auto()
    etf_buy = auto()


class SimulationEvent(models.Model):
    simulation = models.ForeignKey(SimulationConfig, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    event = models.CharField(max_length=255, choices=ValidEvents.choices())
    value = models.FloatField()
