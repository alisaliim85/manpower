from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Vendor
# تأكد من استيراد موديل الطلبات إذا كان موجوداً في تطبيق requests
# from requests.models import Request 

@login_required
def vendor_detail_view(request, pk):
    # جلب بيانات المورد مع حساب عدد العمال تلقائياً
    vendor = get_object_or_404(Vendor, pk=pk)
    
    # جلب قائمة العمال التابعين لهذا المورد
    workers = vendor.workers.all()
    workers_count = workers.count()

    # جلب إحصائيات الحالات للعمال أو الطلبات 
    # (هنا سنحسبها بناءً على حالات العمال كمثال، ويمكنك ربطها بالطلبات لاحقاً)
    stats = workers.aggregate(
        active_count=Count('id', filter=Q(status='active')),
        vacation_count=Count('id', filter=Q(status='vacation')),
        other_count=Count('id', filter=~Q(status__in=['active', 'vacation']))
    )

    context = {
        'vendor': vendor,
        'workers': workers,
        'workers_count': workers_count,
        'active_count': stats['active_count'],
        'vacation_count': stats['vacation_count'],
        'other_count': stats['other_count'],
    }
    
    return render(request, 'vendors-templates/vendor_detail.html', context)