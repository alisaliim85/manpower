from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import Request, RequestType, RequestField, RequestFieldValue
from vendors.models import Worker
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

class RequestWizardView(LoginRequiredMixin, TemplateView):
    template_name = 'requests-templates/create_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_types'] = RequestType.objects.filter(is_active=True)
        # جلب عمال شركة العميل (بناءً على منطق مشروعك)
        user = self.request.user
        
        # منطق عرض العمال في القائمة المنسدلة
        if user.company.company_type == 'client':
            # العميل: يرى جميع العمال (أو العمال الذين لديهم عقود معه)
            context['workers'] = Worker.objects.all()
        elif user.company.company_type == 'vendor':
            # المورد (إذا سمحنا له بالإنشاء): يرى عماله فقط
            context['workers'] = Worker.objects.filter(vendor__company=user.company)
            
        return context

    def post(self, request, *args, **kwargs):
        # التحقق من صلاحية الإنشاء (اختياري: قصرها على العميل فقط)
        if request.user.company.company_type == 'vendor':
             # يمكنك منع المورد من الإنشاء هنا إذا رغبت
             pass 

        type_id = request.POST.get('request_type')
        worker_id = request.POST.get('worker')
        
        # إنشاء الطلب
        new_request = Request.objects.create(
            request_type_id=type_id,
            worker_id=worker_id,
            title=request.POST.get('title', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user,
            status='submitted', # الحالة الافتراضية
            current_company=request.user.company # الجهة الحالية هي من أنشأت الطلب
        )

        # حفظ الحقول الديناميكية
        fields = RequestField.objects.filter(request_type_id=type_id)
        for field in fields:
            val = request.POST.get(f'field_{field.id}')
            if val is not None and val != "":
                fv = RequestFieldValue(request=new_request, field=field)
                if field.field_type == 'text': fv.value_text = val
                elif field.field_type == 'number': fv.value_number = val
                elif field.field_type == 'date': fv.value_date = val
                elif field.field_type == 'bool': fv.value_bool = (val == 'True')
                elif field.field_type == 'choice': fv.value_text = val
                fv.save()

        messages.success(request, "تم إرسال الطلب بنجاح!")
        return redirect('requests:list')

def get_request_fields(request, type_id):
    fields = RequestField.objects.filter(request_type_id=type_id, is_active=True).values(
        'id', 'label', 'field_type', 'is_required', 'help_text', 'choices'
    ).order_by('sort_order')
    return JsonResponse(list(fields), safe=False)

class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = 'requests-templates/request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        user = self.request.user
        qs = Request.objects.select_related('worker', 'request_type', 'created_by')

        if user.company.company_type == 'client':
            # العميل: يشاهد الطلبات التي قامت شركته بإنشائها
            # (أو يمكنك جعلها qs.all() إذا كان العميل هو الأدمن للنظام)
            return qs.filter(created_by__company=user.company)
        
        elif user.company.company_type == 'vendor':
            # المورد: يشاهد فقط الطلبات الخاصة بعمال شركته
            # يفترض هنا أن المودل Worker مرتبط بـ Vendor ومنه لـ Company
            return qs.filter(worker__vendor__company=user.company)
            
        return qs.none() # في حالة عدم وجود نوع شركة

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # الإحصائيات تحسب بناءً على الـ QuerySet المفلتر أعلاه (لضمان الدقة)
        qs = self.get_queryset() 
        
        context['total_count'] = qs.count()
        context['submitted_count'] = qs.filter(status='submitted').count()
        context['in_progress_count'] = qs.filter(status='in_progress').count()
        context['completed_count'] = qs.filter(status='completed').count()
        context['rejected_count'] = qs.filter(status='rejected').count()
        
        return context
        
        
        # 3. عرض تفاصيل الطلب (الكلاس الذي كان ينقصك)

class RequestDetailView(LoginRequiredMixin, DetailView):
    model = Request
    template_name = 'requests-templates/request_detail.html'
    context_object_name = 'req'

    # 1. حماية العرض: العميل يرى طلباته، والمورد يرى طلبات عماله
    def get_queryset(self):
        user = self.request.user
        qs = Request.objects.select_related('worker', 'request_type', 'created_by')

        if user.company.company_type == 'client':
            return qs.filter(created_by__company=user.company)
        
        elif user.company.company_type == 'vendor':
            return qs.filter(worker__vendor__company=user.company)
            
        return qs.none() # في حال لم يكن المستخدم يتبع لأي نوع شركة معروف

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_values'] = self.object.field_values.all().select_related('field')
        return context

    # 2. منطق المعالجة (POST) متوافق مع شروط المودل
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        user = request.user
        
        # التحقق من الصلاحية: فقط المورد (أو السوبر يوزر) يمكنه تغيير الحالة
        # (يمكنك تعديل الشرط إذا كان العميل يملك صلاحية الإلغاء مثلاً)
        if user.company.company_type != 'vendor' and not user.is_superuser:
            messages.error(request, "ليس لديك صلاحية لتعديل حالة هذا الطلب.")
            return redirect('requests:detail', pk=self.object.pk)

        # 1. زر "بدء المعالجة"
        if action == 'start_processing' and self.object.status == 'submitted':
                self.object.status = 'in_progress'
                self.object.current_company = user.company
                self.object.save()
                messages.success(request, "تم بدء معالجة الطلب.")
        # 2. زر "إعادة لوجود نقص"
        elif action == 'return_defect' and self.object.status == 'in_progress':
                reason = request.POST.get('return_reason')
                if reason:
                    self.object.status = 'returned'
                    self.object.return_reason = reason # أو self.object.notes += ...
                    self.object.save()
                    messages.warning(request, "تم إعادة الطلب للعميل لاستكمال النواقص.")
                else:
                    messages.error(request, "يجب ذكر سبب الإعادة.")
        # --- الحالة 2: رفض الطلب (Reject) ---
        elif action == 'reject':
            reason = request.POST.get('rejection_reason') # قادم من الـ Modal
            
            # شرط المودل: rejection_reason إلزامي عند الرفض
            if not reason:
                messages.error(request, "عذراً، يجب ذكر سبب الرفض.")
                return redirect('requests:detail', pk=self.object.pk)

            self.object.status = 'rejected'
            self.object.rejection_reason = reason
            
            # شروط المودل عند الإغلاق النهائي (closed_by + closed_at)
            self.object.closed_by = user
            self.object.closed_at = timezone.now()
            
            self.object.save()
            messages.error(request, "تم رفض الطلب وإغلاقه.")

        # --- الحالة 3: إكمال الطلب (Complete) ---
        elif action == 'complete':
            # الحقل في المودل اسمه closure_note
            note = request.POST.get('closure_note') 
            
            self.object.status = 'completed'
            
            # حفظ ملاحظة الإغلاق إن وجدت
            if note:
                self.object.closure_note = note
            
            # شروط المودل عند الإغلاق النهائي (closed_by + closed_at)
            self.object.closed_by = user
            self.object.closed_at = timezone.now()
            
            self.object.save()
            messages.success(request, "تم إكمال الطلب وإغلاقه بنجاح!")
        elif user.company.company_type == 'client':
            
            # 4. زر "إعادة إرسال" (بعد تصحيح النقص)
            if action == 'resubmit' and self.object.status == 'returned':
                # يمكن هنا تحديث الملاحظات أو الحقول إذا كان هناك فورم تعديل
                self.object.status = 'submitted'
                self.object.rejection_reason = "" # تنظيف أسباب الرفض القديمة إن وجدت
                self.object.return_reason = ""    # تنظيف سبب الإعادة
                self.object.save()
                messages.success(request, "تم إعادة إرسال الطلب بنجاح.")

        return redirect('requests:detail', pk=self.object.pk)
        
# دالة مساعدة AJAX للحقول
def get_request_fields(request, type_id):
    fields = RequestField.objects.filter(request_type_id=type_id, is_active=True).values(
        'id', 'label', 'field_type', 'is_required', 'help_text', 'choices'
    ).order_by('sort_order')
    return JsonResponse(list(fields), safe=False)
