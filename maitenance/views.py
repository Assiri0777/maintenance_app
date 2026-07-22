from django.shortcuts import render, get_object_or_404
from .models import Equipment
from .models import MaintenanceTicket
from datetime import date
def print_delivery_note(request, equipment_id):
    # جلب بيانات المعدة من قاعدة البيانات
    equipment = get_object_or_404(Equipment, id=equipment_id)
    
    context = {
        'equipment': equipment,
        'current_date': date.today() 
    }
    # عرض صفحة الـ HTML
    return render(request, 'maitenance/print_delivery_note.html', {'equipment': equipment})

from django.shortcuts import render
from django.db.models import Sum
from .models import Equipment, MaintenanceTicket
# استيراد موديلات البرنامج الثاني (yard_assets) تلقائياً
from yard_assets.models import Flange, WellheadTree, GateValve, BpvPart, AssetMovement

def dashboard_view(request):
    # ================= 1. Maintenance App Data =================
    total_equipment = Equipment.objects.count()
    total_tickets = MaintenanceTicket.objects.count()
    open_tickets = MaintenanceTicket.objects.filter(is_resolved=False).count()
    resolved_tickets = MaintenanceTicket.objects.filter(is_resolved=True).count()
    
    all_equipment = Equipment.objects.all()
    
    needs_maintenance_count = 0
    eq_active = 0
    eq_maintenance = 0
    eq_out_of_service = 0

    for eq in all_equipment:
        if eq.status == 'Out of Service':
            eq_out_of_service += 1
        elif eq.needs_maintenance or eq.status =='need maintenance':
            needs_maintenance_count += 1
            eq_maintenance += 1
        else:
            eq_active += 1

    # ================= 2. Yard Assets App Data =================
    total_flanges = Flange.objects.count()
    total_wellheads = WellheadTree.objects.count()
    total_valves = GateValve.objects.count()
    total_bpv_qty = BpvPart.objects.aggregate(total=Sum('quantity'))['total'] or 0
    
    total_yard_assets = total_flanges + total_wellheads + total_valves + total_bpv_qty
    total_movements = AssetMovement.objects.count()

    # 📊 تفكيك الحسابات بدقة لكل موديل على حدة لتغذية الجدول الجديد
    # 1. الفلنجات
    fl_avail = Flange.objects.filter(status='Available').count()
    fl_disp = Flange.objects.filter(status='Dispatched').count()
    fl_insp = Flange.objects.filter(status='Need inspection').count()

    # 2. رؤوس الآبار
    wh_avail = WellheadTree.objects.filter(status='Available').count()
    wh_disp = WellheadTree.objects.filter(status='Dispatched').count()
    wh_insp = WellheadTree.objects.filter(status='Need inspection').count()

    # 3. الصمامات
    gv_avail = GateValve.objects.filter(status='Available').count()
    gv_disp = GateValve.objects.filter(status='Dispatched').count()
    gv_insp = GateValve.objects.filter(status='Need inspection').count()

    # 4. قطع الـ BPV (تعتمد على مجموع الـ quantity)
    bpv_avail = BpvPart.objects.filter(status='Available').aggregate(total=Sum('quantity'))['total'] or 0
    bpv_disp = BpvPart.objects.filter(movementitem__movement__movement_type__in=['Out','Transfer','For use','Loan']).aggregate(total=Sum('movementitem__quantity'))['total'] or 0
    bpv_insp = BpvPart.objects.filter(status='Need inspection').aggregate(total=Sum('quantity'))['total'] or 0
    total_bpv_qty = bpv_avail + bpv_disp + bpv_insp
    total_yard_assets = total_flanges + total_wellheads + total_valves + total_bpv_qty

    # 🆕 بناء مصفوفة البيانات المنظمة للجدول الجديد
    asset_data = [
        {'name': 'Flanges', 'available': fl_avail, 'dispatched': fl_disp, 'inspection': fl_insp, 'total': total_flanges},
        {'name': 'Wellhead Trees', 'available': wh_avail, 'dispatched': wh_disp, 'inspection': wh_insp, 'total': total_wellheads},
        {'name': 'Gate Valves', 'available': gv_avail, 'dispatched': gv_disp, 'inspection': gv_insp, 'total': total_valves},
        {'name': 'BPV Parts', 'available': bpv_avail, 'dispatched': bpv_disp, 'inspection': bpv_insp, 'total': total_bpv_qty},
    ]

    # 🔄 إعادة تجميع المتغيرات للرسم البياني الأصلي حقك (عشان ما يتأثر كودك القديم بشيء)
    asset_available = fl_avail + wh_avail + gv_avail + bpv_avail
    asset_dispatched = fl_disp + wh_disp + gv_disp + bpv_disp
    asset_inspection = fl_insp + wh_insp + gv_insp + bpv_insp

    context = {
        # Maintenance Data
        'total_equipment': total_equipment,
        'eq_out_of_service': eq_out_of_service,
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'resolved_tickets': resolved_tickets,
        'needs_maintenance_count': needs_maintenance_count,
        'eq_chart_labels': ['Active', 'Need Maintenance', 'Out of Service'],
        'eq_chart_data': [eq_active, eq_maintenance, eq_out_of_service],
        
        # Yard Assets Data
        'total_yard_assets': total_yard_assets,
        'total_movements': total_movements,
        'asset_chart_labels': ['Available in Yard', 'Dispatched to Sites', 'Need Inspection'],
        'asset_chart_data': [asset_available, asset_dispatched, asset_inspection],
        
        # 🆕 تمرير بيانات الجدول الجديد إلى الـ HTML
        'asset_data': asset_data,
    }
    return render(request, 'Maitenance/dashboard.html', context)
