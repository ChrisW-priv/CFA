from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from cfa_simulation.views import SimulationRunView, SimulationListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', SimulationListView.as_view(), name='simulation_list'),
    path('simulations/<int:pk>/run/', SimulationRunView.as_view(), name='simulation_run'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
