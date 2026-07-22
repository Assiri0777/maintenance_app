from django.contrib import admin
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Flange, WellheadTree, GateValve, BpvPart, AssetMovement, MovementItem
import csv
from django.http import HttpResponse

class YardAssetAdminBase(admin.ModelAdmin):
    list_display = ('name', 'asset_id', 'status', 'size', 'pressure_rating', 'last_inspection')
    list_filter = ('status', 'size', 'pressure_rating')
    search_fields = ('name', 'asset_id')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['stat_total'] = self.model.objects.count()
        extra_context['stat_available'] = self.model.objects.filter(status='Available').count()
        extra_context['stat_dispatched'] = self.model.objects.filter(status='Dispatched').count()
        extra_context['is_bpv'] = False
        return super().changelist_view(request, extra_context=extra_context)

@admin.register(Flange)
class FlangeAdmin(YardAssetAdminBase): pass

@admin.register(WellheadTree)
class WellheadTreeAdmin(YardAssetAdminBase): pass

@admin.register(GateValve)
class GateValveAdmin(YardAssetAdminBase): pass


@admin.register(BpvPart)
class BpvPartAdmin(admin.ModelAdmin):
    list_display = ('part_type', 'quantity', 'status')
    list_filter = ('status', 'part_type')

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['bpv_items'] = BpvPart.objects.annotate(
            dispatched_qty=Coalesce(Sum('movementitem__quantity', filter=Q(movementitem__movement__movement_type__in=['Out', 'Transfer', 'For use', 'Loan'])), 0)
        ).order_by('part_type')
        extra_context['is_bpv'] = True
        return super().changelist_view(request, extra_context=extra_context)
        self.readonly_fields = ('serial_number',)

# 📥 جدول الأسطر المتعددة لإضافة أكثر من مادة بسيريلات مختلفة
class MovementItemInline(admin.TabularInline):
    model = MovementItem
    extra = 3  # تظهر لك 3 أسطر تلقائية لسرعة الإدخال
    fields = ('flange', 'wellhead_tree', 'gate_valve', 'serial_number', 'bpv_part', 'quantity')


@admin.action(description='Export selected movements to Excel')
def export_movements_to_excel(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="yard_asset_movements.csv"'
    
    writer = csv.writer(response)
    # 🆕 الترتيب الجديد للعناوين حسب طلبك بالضبط:
    writer.writerow([
        'Movement ID', 'Type', 'Sender Name', 'From (Departure)', 
        'Moved Items Summary', 'Serial Numbers', 'Sizes', 'Pressure Ratings', 
        'Destination', 'Driver Name', 'Receiver Name', 'Date & Time'
    ])
    
    for log in queryset:
        items_list = []
        serials_list = []  
        sizes_list = []      
        pressures_list = []  
        
        for item in log.items.all():
            asset = item.flange or item.wellhead_tree or item.gate_valve
            if asset:
                items_list.append(f"{asset.name or asset.asset_id}")
                serials_list.append(f"{asset.asset_id}")
                sizes_list.append(f"{asset.size or '-'}")              
                pressures_list.append(f"{asset.pressure_rating or '-'}")  
            elif item.bpv_part:
                items_list.append(f"{item.bpv_part.part_type} (x{item.quantity})")
                serials_list.append("Bulk")
                sizes_list.append("Bulk")      
                pressures_list.append("Bulk")  
        
        items_summary = " | ".join(items_list) if items_list else "No Items Added"
        serials_summary = " | ".join(serials_list) if serials_list else "N/A"
        sizes_summary = " | ".join(sizes_list) if sizes_list else "N/A"              
        pressures_summary = " | ".join(pressures_list) if pressures_list else "N/A"  
        
        formatted_date = log.movement_date.strftime('%Y-%m-%d %H:%M') if log.movement_date else ''
        
        # 🆕 ترتيب البيانات اللّي تنزل في السطور لتطابق العناوين فوق بالملي:
        writer.writerow([
            log.id, 
            log.get_movement_type_display(), 
            log.Sender_Name, 
            log.departure_site, 
            items_summary, 
            serials_summary,
            sizes_summary,      
            pressures_summary,
            log.destination_site,
            log.Driver_Name,
            log.Receiver_Name,  # حقل المستلم اللّي ضفناه كابيتال
            formatted_date
        ])
    return response

@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    # عرض الزر الذكي الجديد في الجدول الرئيسي مكان زر الطباعة القديم
    list_display = ('id', 'movement_type', 'display_assets_summary','display_serial_numbers','display_size_pressure', 'departure_site', 'destination_site', 'movement_date', 'delivery_note_action')
    list_filter = ('movement_type', 'movement_date')
    actions = [export_movements_to_excel]
    # 🔐 تسجيل الحقل كـ Readonly وتفعيله داخل شاشة الإدخال
    readonly_fields = ['delivery_note_action']
    inlines = [MovementItemInline] 

    fieldsets = [
        ('General Logistics & Transport Information', {
            'fields': ('movement_type', 'Sender_Name', 'Receiver_Name', 'Driver_Name', 'departure_site', 'destination_site', 'delivery_note_file', 'notes', 'delivery_note_action')
        }),
    ]

    def display_assets_summary(self, obj):
        items = obj.items.all()
        if items.exists():
            summary = []
            for item in items:
                asset = item.flange or item.wellhead_tree or item.gate_valve
                if asset: summary.append(f"{asset.name or asset.asset_id}")
                elif item.bpv_part: summary.append(f"{item.bpv_part.part_type} (x{item.quantity})")
            return ", ".join(summary)
        return "No Items Added"
    display_assets_summary.short_description = "Moved Assets / Serials"
 
    def display_serial_numbers(self, obj):
        items = obj.items.all()
        if items.exists():
            serials = []
            for item in items:
                asset = item.flange or item.wellhead_tree or item.gate_valve
                if asset: 
                    serials.append(f"{asset.asset_id}")
                elif item.bpv_part: 
                    serials.append("Bulk")  # قطع الـ BPV مالها سيريال
            return ", ".join(serials)
        return "N/A"
    display_serial_numbers.short_description = "Serial Numbers"

    def display_size_pressure(self, obj):
        items = obj.items.all()
        if items.exists():
            specs = []
            for item in items:
                asset = item.flange or item.wellhead_tree or item.gate_valve
                if asset:
                    size = asset.size if asset.size else "-"
                    pressure = asset.pressure_rating if asset.pressure_rating else "-"
                    specs.append(f"{size} / {pressure}")
                elif item.bpv_part:
                    specs.append("Bulk")
            return ", ".join(specs)
        return "N/A"
    display_size_pressure.short_description = "Size / Pressure"

    # 🎯 دالة الزر الذكي: تفحص تلقائياً وتمنع انهيار دجانغو 6.0 في صفحة الإضافة الجديدة
    def delivery_note_action(self, obj):
        if obj and obj.pk:
            # إذا تم رفع ملف ديليفري نوت موقّع، يظهر زر الاستعراض الأخضر فوراً
            if obj.delivery_note_file:
                return format_html(
                    '<a class="button" href="{}" target="_blank" '
                    'style="background-color: #2e7d32; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">'
                    '📄 View Signed DN</a>', 
                    obj.delivery_note_file.url
                )
            # إذا لم يتم رفع الملف، يظهر زر الطباعة المعتاد
            else:
                url = f"/movement/{obj.pk}/pdf/"
                return format_html(
                    '<a class="button" href="{}" target="_blank" '
                    'style="background-color: #16a085; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">'
                    '🖨️ Print OSU Form</a>', 
                    url
                )
        # 🛡️ حماية صفحة الإضافة الجديدة (add) باستخدام mark_safe لمنع خطأ الـ TypeError
        return mark_safe('<span style="color: #718096; font-style: italic; font-weight: bold;">Save the record first to enable actions</span>')
    
    delivery_note_action.short_description = "Action / Document"







  # 1. حفظ الدالة الأصلية لدجانغو لمنع انهيار النظام
original_get_app_list = admin.AdminSite.get_app_list

# 2. بناء الدالة الجديدة المعدلة باللغة الإنجليزية
def custom_get_app_list(self, request, app_label=None):
    # استدعاء الدالة الأصلية المخزنة بدون استخدام super
    app_list = original_get_app_list(self, request, app_label)
    
    # بناء قسم الداشبورد الجديد بالإنجليزية لتطابق بقية النظام
    dashboard_section = {
        'name': 'Dashboard',  # اسم القسم الرئيسي بالـ سايد بار
        'app_label': 'custom_dashboard',
        'app_url': '/dashboard/',  
        'has_module_perms': True,
        'models': [
            {
                'name': '📊 Open Interactive Dashboard',  # اللينك الداخلي بالإنجليزية
                'object_name': 'dashboard_link',
                'admin_url': '/dashboard/',  
            }
        ]
    }
    
    # وضعه في آخر القائمة ليكون أسفل السايد بار تماماً
    app_list.append(dashboard_section)
    return app_list

# 3. تطبيق التعديل الذكي على دجانغو
admin.AdminSite.get_app_list = custom_get_app_list