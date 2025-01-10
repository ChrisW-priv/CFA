from django.contrib import admin

from .models import Simulation, SimulationEvent


class SimulationEventInLine(admin.TabularInline):
    model = SimulationEvent
    extra = 0


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    inlines = (SimulationEventInLine,)
