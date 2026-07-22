from django.shortcuts import render, get_object_or_404
from .models import AssetMovement

def generate_osu_form_pdf(request, movement_id):
    # جلب الحركة الرئيسية
    current_movement = get_object_or_404(AssetMovement, pk=movement_id)
    
    context = {
        'obj': current_movement,               # لطباعة بيانات السائق والوجهة بدون ما يتغير شيء عندك
        'items': current_movement.items.all(), # لطباعة جدول المواد المتعددة الجديدة
    }
    
    return render(request, 'osu_delivery_form.html', context)