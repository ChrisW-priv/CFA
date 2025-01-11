from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, ListView

from .models import SimulationConfig, SimulationEvent
from .run_simulation import run_simulation


class SimulationListView(ListView):
    model = SimulationConfig
    context_object_name = 'simulations'


class SimulationRunView(TemplateView):
    template_name = 'cfa_simulation/simulation_run.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        simulation_id = self.kwargs.get('pk')
        context['simulation'] = get_object_or_404(SimulationConfig, id=simulation_id)
        context['events'] = SimulationEvent.objects.filter(simulation_id=simulation_id)
        return context

    def post(self, request, *args, **kwargs):
        simulation_id = self.kwargs.get('pk')
        simulation = get_object_or_404(SimulationConfig, pk=simulation_id)
        result = run_simulation(simulation)
        return JsonResponse({'status': 'success', 'result': result})
