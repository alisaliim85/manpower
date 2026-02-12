from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from .models import Vendor, Worker
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin # استيراد الميكسين الخاص بالكلاسات
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.generic import ListView, DetailView
from django.core.exceptions import PermissionDenied
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


class VendorListView(LoginRequiredMixin,UserPassesTestMixin, ListView): # تصحيح الوراثة هنا
    model = Vendor
    template_name = 'vendors-templates/vendor_list.html'
    context_object_name = 'vendors'
    paginate_by = 10
    ordering = ['-id']
    # هذه الدالة هي المسؤولة عن اختبار صلاحية المستخدم
# دالة التحقق من الصلاحية
    def test_func(self):
        user = self.request.user
        # نتحقق: هل المستخدم مرتبط بشركة؟ وهل نوع هذه الشركة 'client'؟
        return user.company and user.company.company_type == 'client'

    # معالجة فشل التحقق (إظهار خطأ 403)
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()

    def get_queryset(self):
        # تحسين الأداء: جلب الشركات مع عدد العمال في استعلام واحد
        return Vendor.objects.select_related('company').annotate(workers_count=Count('workers')).order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "قائمة شركات التوريد"
        return context

class WorkerListView(LoginRequiredMixin, ListView):
    model = Worker
    template_name = 'vendors-templates/worker_list.html'
    context_object_name = 'workers'
    paginate_by = 10  # عدد العمال في كل صفحة

    def get_queryset(self):
        user = self.request.user
        # الترتيب الافتراضي: الأحدث إضافة
        qs = Worker.objects.select_related('vendor__company').all().order_by('-created_at')

        # 1. فلترة حسب نوع المستخدم
        if user.company.company_type == 'vendor':
            # المورد يرى عماله فقط
            qs = qs.filter(vendor__company=user.company)
        # العميل (Client) يرى الجميع حالياً (يمكن تخصيصها ليرى المتعاقد معهم فقط)

        # 2. البحث النصي (الاسم، رقم الإقامة، المسمى الوظيفي)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(full_name__icontains=query) |
                Q(iqama_number__icontains=query) |
                Q(job_title__icontains=query)
            )

        # 3. فلترة الحالة (نشط، إجازة، خروج...)
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # حساب الإحصائيات للكروت العلوية (بناءً على العمال المتاحين للمستخدم)
        user = self.request.user
        base_qs = Worker.objects.all()
        if user.company.company_type == 'vendor':
            base_qs = base_qs.filter(vendor__company=user.company)
            
        context['active_count'] = base_qs.filter(status='active').count()
        context['vacation_count'] = base_qs.filter(status='vacation').count()
        
        return context

class WorkerDetailView(LoginRequiredMixin, DetailView):
    model = Worker
    template_name = 'vendors-templates/worker_detail.html'
    context_object_name = 'worker'

    def get_queryset(self):
        """
        حماية البيانات:
        - المورد يرى فقط عماله.
        - العميل يرى جميع العمال (أو حسب المنطق الخاص بك).
        """
        user = self.request.user
        qs = super().get_queryset()
        
        if user.company.company_type == 'vendor':
            return qs.filter(vendor__company=user.company)
            
        return qs