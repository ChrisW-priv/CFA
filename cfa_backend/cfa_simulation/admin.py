from django.contrib import admin

from .models import SimulationConfig, SimulationEvent


class SimulationEventInLine(admin.TabularInline):
    model = SimulationEvent
    extra = 0


@admin.register(SimulationConfig)
class SimulationAdmin(admin.ModelAdmin):
    inlines = (SimulationEventInLine,)
