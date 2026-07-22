from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Equipment, MaintenanceTicket, MaintenanceLog
from import_export.admin import ImportExportActionModelAdmin
import openpyxl
# 1. تخصيص أسماء لوحة التحكم
admin.site.site_header = "HZEM yard"
admin.site.site_title = "HZEM yard Admin Portal"
admin.site.index_title = "Welcom to HZEM yard equipment control"

# 2. التحكم في شاشة المعدات (مع إضافة دالة البطاقات)
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Equipment, MaintenanceTicket, MaintenanceLog

# 💡 1. استيراد كلاس التصدير + كلاس صيغة الإكسل XLSX فقط:
from import_export.admin import ImportExportActionModelAdmin
from import_export.formats.base_formats import XLSX

# 1. تخصيص أسماء لوحة التحكم
admin.site.site_header = "HZEM yard"
admin.site.site_title = "HZEM yard Admin Portal"
admin.site.index_title = "HZEM Yard Equipment control"

# 2. التحكم في شاشة المعدات
@admin.register(Equipment)
class EquipmentAdmin(ImportExportActionModelAdmin):
    change_list_template = 'custom_list.html'
    
    # 💡 2. هذا السطر السحري يحذف كل الصيغ الأخرى ويترك الإكسل فقط في القائمة:
    formats = [XLSX]
    
    list_display = ('name', 'serial_number', 'category', 'status', 'running_hours', 'next_inspection_date', 'get_maintenance_status', 'get_equipment_pdf', 'print_dn_link')
    list_editable = ('running_hours', 'status')
    search_fields = ('name', 'serial_number')
    from django.utils.html import format_html  # 👈 تأكد من وجود هذا الاستيراد في أعلى الملف

# داخل كلاس EquipmentAdmin:
    @admin.display(description='Next Inspection Date', ordering='next_maintenance_date')
    def next_inspection_date(self, obj):
        if obj.next_maintenance_date:
            # تحويل التاريخ إلى صيغة: يوم / شهر / سنة
            formatted_date = obj.next_maintenance_date.strftime('%d/%m/%Y')
            # إجبار المتصفح على عرض النص من اليسار لليمين لمنع الانعكاس البصري
            return format_html('<span dir="ltr">{}</span>', formatted_date)
        return "NUN⚠️"
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['active_count'] = Equipment.objects.filter(status__iexact='active').count()
        extra_context['maintenance_count'] = Equipment.objects.filter(status__in=['Need maintenance','need maintenance']).count()
        extra_context['outofservice_count'] = Equipment.objects.filter(status__iexact='Out of Service').count()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description=' Maintenance status')
    def get_maintenance_status(self, obj):
        if obj.needs_maintenance:
            if obj.category in ['generator', 'floodlight'] and obj.hours_until_maintenance is not None and obj.hours_until_maintenance <= 20:
                return f": Maintenance soon({int(obj.hours_until_maintenance)} Remaining hours ) ⚠️"
            return "Alert: Maintenance Due soon 📅⚠️"
        return "Ready ✅"

    @admin.display(description='Equipment Document')
    def get_equipment_pdf(self, obj):
        if obj.equipment_pdf:
            return format_html('<a href="{}" target="_blank" style="color: #007a87; font-weight: bold;">📄 View  PDF</a>', obj.equipment_pdf.url)
        return "No Document"

    @admin.display(description='Delivery Note')
    def print_dn_link(self, obj):
        url = reverse('print_delivery_note', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank" style="background-color: #007a87; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">Delivery_Note</a>',
            url
        )

# 3. التحكم في شاشة تذاكر الصيانة
@admin.register(MaintenanceTicket)
class MaintenanceTicketAdmin(admin.ModelAdmin):
    # 1. أضفنا 'get_ticket_pdf' هنا في السطر 59 لكي يظهر العمود في الجدول
    list_display = ('title', 'equipment', 'priority', 'is_resolved', 'get_ticket_pdf')
    list_filter = ('is_resolved', 'priority')

    # 2. الطريقة الحديثة المعتمدة في Django 6 لتسمية العمود بدلاً من السطر 66
    @admin.display(description=' Attached File ')
    def get_ticket_pdf(self, obj):
        if obj.ticket_pdf:
            return format_html('<a href="{}" target="_blank" style="color: #d9534f; font-weight: bold;">📕 Closure Report</a>', obj.ticket_pdf.url)
        return "No Document"

# 4. التحكم في شاشة سجل الصيانة
@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'action_taken', 'performed_by', 'timestamp')

    








    # ... بقية إعداداتك هنا ...

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # حساب الحالات بناءً على اسم الحالة في المودل الخاص بك
        # تأكد أن الكلمات 'Active', 'Under Maintenance', 'Out of Service' تطابق ما هو مسجل في قاعدة البيانات
        extra_context['active_count'] = Equipment.objects.filter(status='Active').count()
        extra_context['maintenance_count'] = Equipment.objects.filter(status='Under Maintenance').count()
        extra_context['outofservice_count'] = Equipment.objects.filter(status='Out of Service').count()
        return super().changelist_view(request, extra_context=extra_context)
