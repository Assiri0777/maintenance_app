from django.db import models
from django.utils import timezone
from datetime import date
class Equipment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active / Functional'),
        ('Need maintenance', 'Need Maintenance'),
        ('Out of Service', 'Out of Service'),
    ]
    CATEGORY_CHOICES = [
        ('generator', 'Generator (Bi-weekly Maintenance)'),
        ('fire_extinguisher', 'Fire Extinguisher'),
        ('floodlight', 'Floodlight / Emergency Lighting'),
        ('scaba', 'Scaba'),
        ('other', 'Other Equipment'),
    ]
   
    name = models.CharField(max_length=100)
    def __str__(self):
        return f"{self.name} - ({self.serial_number})"
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    serial_number = models.CharField(max_length=50, unique=True)
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    equipment_pdf = models.FileField(upload_to='equipment_pdfs/', null=True, blank=True, verbose_name=" Equipment PDF ")

    # حقول الصيانة والساعات
    running_hours = models.FloatField(default=0.0)
    last_maintenance_date = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    last_maintenance_hours= models.FloatField(default=0.0)
    @property
    def hours_until_maintenance(self):
        # الحساب للمولدات وكشافات الطوارئ فقط
        if self.category in ['generator', 'floodlight']:
            MAINTENANCE_INTERVAL = 250 
            hours_since_last = self.running_hours - self.last_maintenance_hours
            remaining = MAINTENANCE_INTERVAL - hours_since_last
            return remaining
        return None # لا ينطبق عليها نظام الساعات

    @property
    def needs_maintenance(self):
        from datetime import date
        today = date.today()
        
        # 1. معدات تعتمد على الساعات (Generators & Floodlights)
        if self.category in ['generator', 'floodlight']:
            # تنبيه إذا باقي أقل من 20 ساعة، أو إذا حل تاريخ الصيانة المجدول
            hour_check = self.hours_until_maintenance <= 20 if self.hours_until_maintenance is not None else False
            date_check = (self.next_maintenance_date <= today) if self.next_maintenance_date else False
            return hour_check or date_check
            
        # 2. معدات تعتمد على التاريخ فقط (Fire Extinguisher & SCABA)
        elif self.category in ['fire_extinguisher', 'scaba']:
            if self.next_maintenance_date:
                # تنبيه إذا حل التاريخ، أو إذا باقي على موعدها أسبوع أو أقل (7 أيام)
                days_remaining = (self.next_maintenance_date - today).days
                return days_remaining <= 7
            return False
            
        # 3. أي معدات أخرى مضافة مستقبلاً
        else:
            if self.next_maintenance_date:
                return self.next_maintenance_date <= today
            return False


    class Meta:
            verbose_name_plural = "Equipment"

class MaintenanceTicket(models.Model):
    PRIORITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High / Urgent')]
   
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    is_resolved = models.BooleanField(default=False)
    reported_at = models.DateTimeField(auto_now_add=True)

    ticket_pdf = models.FileField(upload_to='ticket_pdfs/', null=True, blank=True, verbose_name=" Closing Report PDF")
    
    def save(self, *args, **kwargs):
        # 1. حفظ التذكرة أولاً بالشكل الطبيعي
        super().save(*args, **kwargs)
       
        # 2. الأتمتة: إذا تم تحديد التذكرة كـ "محلولة"
        if self.is_resolved:
           
            # تعديل: استخدمنا action_taken بدلاً من description المتسبب في الخطأ
            log_exists = MaintenanceLog.objects.filter(
                equipment=self.equipment,
                action_taken__contains=f"Ticket No. ({self.id})"
            ).exists()
           
            if not log_exists:
                # 3. إنشاء سجل الصيانة تلقائياً بحقولك الحقيقية
                MaintenanceLog.objects.create(
                    equipment=self.equipment,
                    action_taken=f"Automated Maintenance - Closed Ticket No. ({self.id}): {self.title}",
                    performed_by = "System / Automated"                    # حقل timestamp سيتحدث تلقائياً من دجانغو فلا داعي لكتابته هنا
                )
               
                # 4. تحديث عداد آخر صيانة في جدول المعدة فوراً ليطابق القراءة الحالية
                from datetime import date
                self.equipment.last_maintenance_hours = self.equipment.running_hours
                self.equipment.last_maintenance_date = date.today()
                self.equipment.save()


    def __str__(self):
        return f"Ticket: {self.title}"

class MaintenanceLog(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='logs')
    action_taken = models.TextField()
    performed_by = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for {self.equipment.name}"
