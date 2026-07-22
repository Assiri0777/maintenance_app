from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

 
from maitenance import views as maintenance_views  
from yard_assets import views as yard_views         

urlpatterns = [
    path('',RedirectView.as_view(url='admin/', permanent=False)),
    path('admin/', admin.site.urls),
    
    # روابط التطبيق الأول القديم
    path('dashboard/', maintenance_views.dashboard_view, name='dashboard'),
    path('equipment/<int:equipment_id>/print/', maintenance_views.print_delivery_note, name='print_delivery_note'),
    
    # روابط التطبيق الثاني الجديد
    path('movement/<int:movement_id>/pdf/', yard_views.generate_osu_form_pdf, name='generate_osu_form_pdf'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "URWS HZEM Yard"
admin.site.site_title = "URWS HZEM Yard Equipment control"
admin.site.index_title = "URWS HZEM Yard Equipment control"
