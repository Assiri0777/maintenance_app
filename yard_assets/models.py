from django.db import models
from django.core.exceptions import ValidationError

class YardAssetBase(models.Model):
    """Base model for serial-numbered assets"""
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Dispatched', 'Dispatched'),
        ('Need inspection', 'Need inspection'),
        ('Expired', 'Expired'),
        ('Damaged', 'Damaged'),
    ]
    
    # 🆕 خانة الاسم لحالها وخانة السيريال لحالها
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Asset Name")
    asset_id = models.CharField(max_length=50, unique=True, verbose_name="Serial Number")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Available', verbose_name="Status")
    size = models.CharField(max_length=30, blank=True, verbose_name="Size")
    pressure_rating = models.CharField(max_length=30, blank=True, verbose_name="Pressure Rating")
    last_inspection = models.DateField(null=True, blank=True, verbose_name="Last Inspection Date")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")

    class Meta:
        abstract = True


class Flange(YardAssetBase):
    class Meta:
        verbose_name = "Flange"
        verbose_name_plural = "Flanges"
    # تعديل طريقة العرض ليظهر الاسم والسيريال معاً في القوائم
    def __str__(self): 
        return f"{self.name} ({self.asset_id})" if self.name else self.asset_id


class WellheadTree(YardAssetBase):
    class Meta:
        verbose_name = "Wellhead tree"
        verbose_name_plural = "Wellhead trees"
    def __str__(self): 
        return f"{self.name} ({self.asset_id})" if self.name else self.asset_id


class GateValve(YardAssetBase):
    class Meta:
        verbose_name = "Gate valve"
        verbose_name_plural = "Gate valves"
    def __str__(self): 
        return f"{self.name} ({self.asset_id})" if self.name else self.asset_id


class BpvPart(models.Model):
    STATUS_CHOICES = [('Available', 'Available'), ('Need inspection', 'Need inspection'), ('Expired', 'Expired'), ('Damaged', 'Damaged')]
    PART_TYPE_CHOICES = [('Seal 2 IN', 'Seal 2 IN'), ('Seal 5 IN', 'Seal 5 IN'), ('Poppet', 'Poppet'), ('Plunger', 'Plunger'), ('Spring', 'Spring')]
    
    part_type = models.CharField(max_length=50, choices=PART_TYPE_CHOICES, default='Seal 2 IN', unique=True, verbose_name="Part Type/Material")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Quantity")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Available', verbose_name="Status")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")

    class Meta:
        verbose_name = "BPV Part"
        verbose_name_plural = "BPV Parts"
    def __str__(self): return f"{self.part_type} (Qty: {self.quantity})"
    

class AssetMovement(models.Model):
    MOVEMENT_TYPES = [('Transfer', 'Transfer'), ('Return back', 'Return back'), ('For use', 'For use'), ('Loan', 'Loan'), ('Out', 'Dispatch'), ('In', 'Receive')]
    
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_TYPES, null=True, blank=True, verbose_name="Movement Type")
    Sender_Name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sender Name (Dispatched By)")
    Receiver_Name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Receiver Name(Received by")
    Driver_Name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Driver Name / Transported By")
    departure_site = models.CharField(max_length=150, blank=True, null=True, verbose_name="From")
    destination_site = models.CharField(max_length=150, blank=True, null=True, verbose_name="Destination")
    movement_date = models.DateTimeField(auto_now_add=True, verbose_name="Movement Date & Time")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")

    # حقول الأمان للحفاظ على الحركات القديمة
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    delivery_note = models.CharField(max_length=100, blank=True, null=True)
    delivery_note_file = models.FileField(upload_to='delivery_notes/', blank=True, null=True)
    flange = models.ForeignKey('Flange', null=True, blank=True, on_delete=models.SET_NULL)
    wellhead_tree = models.ForeignKey('WellheadTree', null=True, blank=True, on_delete=models.SET_NULL)
    gate_valve = models.ForeignKey('GateValve', null=True, blank=True, on_delete=models.SET_NULL)
    bpv_part = models.ForeignKey('BpvPart', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "Asset Movement"
        verbose_name_plural = "Asset Movements Logs"
    def __str__(self): return f"{self.movement_type or 'Unknown'} - {self.id}"


class MovementItem(models.Model):
    movement = models.ForeignKey(AssetMovement, on_delete=models.CASCADE, related_name='items', verbose_name="Movement Reference")
    flange = models.ForeignKey('Flange', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Flange")
    wellhead_tree = models.ForeignKey('WellheadTree', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Wellhead Tree")
    gate_valve = models.ForeignKey('GateValve', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Gate Valve")
    bpv_part = models.ForeignKey('BpvPart', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="BPV Part")
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Serial Number")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantity")

    def clean(self):
        asset = self.flange or self.wellhead_tree or self.gate_valve
        asset_field = 'flange' if self.flange else ('wellhead_tree' if self.wellhead_tree else 'gate_valve')

        parent_movement_type = None
        if hasattr(self, 'movement') and self.movement:
            parent_movement_type = self.movement.movement_type

        if parent_movement_type:
            is_out = parent_movement_type in ['Out', 'Transfer', 'For use', 'Loan']
            is_in = parent_movement_type in ['In', 'Return back']

            # 💡 الحركة الذكية حقتك: القيود تطبق فقط عند إنشاء الحركة لأول مرة وليس عند التعديل والرفع!
            if not self.pk:
                if asset:
                    if self.quantity > 1:
                        raise ValidationError({'quantity': f"This item relies on a unique serial number. Max quantity is 1."})
                    if is_out and asset.status == 'Dispatched':
                        raise ValidationError({asset_field: f"Logical Error: Serial [{asset.asset_id}] is already Dispatched!"})
                    if is_in and asset.status == 'Available':
                        raise ValidationError({asset_field: f"Warning: Serial [{asset.asset_id}] is already available."})

                if self.bpv_part and is_out:
                    if self.bpv_part.quantity < self.quantity:
                        raise ValidationError({'quantity': f"Insufficient balance! Available: ({self.bpv_part.quantity})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        

        parent_movement_type = self.movement.movement_type if (hasattr(self, 'movement') and self.movement) else ''
        move_type = str(parent_movement_type).lower() if parent_movement_type else ''
        
        is_out = move_type in ['out', 'transfer', 'for use', 'loan', 'use']
        is_in = move_type in ['in', 'return back', 'return']

        if self.bpv_part:
            if is_out: 
                self.bpv_part.quantity = max(0, self.bpv_part.quantity - self.quantity)
            elif is_in: 
                self.bpv_part.quantity += self.quantity
            self.bpv_part.status = 'Expired' if self.bpv_part.quantity == 0 else 'Available'
            self.bpv_part.save()
        else:
            asset = self.flange or self.wellhead_tree or self.gate_valve
            if asset:
                if is_out: 
                    asset.status = 'Dispatched'
                elif is_in: 
                    asset.status = 'Available'
                asset.save()
        
        asset = self.flange or self.wellhead_tree or self.gate_valve
        if asset:
            self.serial_number = asset.asset_id

        super(MovementItem, self).save(*args, **kwargs)