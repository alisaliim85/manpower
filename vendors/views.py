from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Vendor
from django.contrib.auth.mixins import LoginRequiredMixin # استيراد الميكسين الخاص بالكلاسات
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from accounts.models import Company

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

class VendorCreateView(LoginRequiredMixin, CreateView):
    model = Vendor
    fields = ['company', 'contact_name', 'contact_phone', 'is_active']
    template_name = 'vendors-templates/vendor_create.html'
    success_url = reverse_lazy('vendors:vendor_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "إضافة شركة توريد جديدة"
        context['available_companies'] = Company.objects.filter(
            company_type='vendor', 
            vendor_profile__isnull=True
        )
        return context