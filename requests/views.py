from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import Request, RequestType, RequestField, RequestFieldValue, RequestComment
from vendors.models import Worker
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

# ==========================================
# 1. إنشاء الطلب (Wizard)
# ==========================================
class RequestWizardView(LoginRequiredMixin, TemplateView):
    template_name = 'requests-templates/create_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_types'] = RequestType.objects.filter(is_active=True)
        
        user = self.request.user
        if user.company.company_type == 'client':
            context['workers'] = Worker.objects.all()
        elif user.company.company_type == 'vendor':
            context['workers'] = Worker.objects.filter(vendor__company=user.company)
            
        return context

    def post(self, request, *args, **kwargs):
        type_id = request.POST.get('request_type')
        worker_id = request.POST.get('worker')
        
        # إنشاء الطلب
        new_request = Request.objects.create(
            request_type_id=type_id,
            worker_id=worker_id,
            title=request.POST.get('title', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user,
            status='submitted',
            current_company=request.user.company
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

# ==========================================
# 2. قائمة الطلبات (List)
# ==========================================
class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = 'requests-templates/request_list.html'
    context_object_name = 'requests'

    def get_queryset(self):
        user = self.request.user
        qs = Request.objects.select_related('worker', 'request_type', 'created_by')

        if user.company.company_type == 'client':
            return qs.filter(created_by__company=user.company)
        elif user.company.company_type == 'vendor':
            return qs.filter(worker__vendor__company=user.company)
            
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset() 
        
        context['total_count'] = qs.count()
        context['submitted_count'] = qs.filter(status='submitted').count()
        context['in_progress_count'] = qs.filter(status='in_progress').count()
        context['completed_count'] = qs.filter(status='completed').count()
        context['rejected_count'] = qs.filter(status='rejected').count()
        
        return context

# ==========================================
# 3. تفاصيل الطلب (Detail) - تم التصحيح
# ==========================================
class RequestDetailView(LoginRequiredMixin, DetailView):
    model = Request
    template_name = 'requests-templates/request_detail.html'
    context_object_name = 'req'

    def get_queryset(self):
        user = self.request.user
        qs = Request.objects.select_related('worker', 'request_type', 'created_by')

        if user.company.company_type == 'client':
            return qs.filter(created_by__company=user.company)
        elif user.company.company_type == 'vendor':
            return qs.filter(worker__vendor__company=user.company)
            
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_values'] = self.object.field_values.all().select_related('field')
        return context

    # ---------------------------------------------------------
    # دالة POST واحدة مدمجة تعالج كل شيء (أهم جزء للتصحيح)
    # ---------------------------------------------------------
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        user = request.user
        
        # 1. إضافة تعليق (متاح للجميع)
        if action == 'add_comment':
            comment_body = request.POST.get('comment_body')
            if comment_body:
                RequestComment.objects.create(
                    request=self.object,
                    author=user,
                    body=comment_body
                )
                messages.success(request, "تم إضافة التعليق بنجاح.")
            else:
                messages.error(request, "لا يمكن إضافة تعليق فارغ.")
            return redirect('requests:detail', pk=self.object.pk)

        # 2. إجراءات المورد (Vendor)
        if user.company.company_type == 'vendor':
            if action == 'start_processing' and self.object.status == 'submitted':
                self.object.status = 'in_progress'
                self.object.current_company = user.company
                self.object.save()
                messages.success(request, "تم بدء معالجة الطلب.")

            elif action == 'return_defect' and self.object.status == 'in_progress':
                reason = request.POST.get('return_reason')
                if reason:
                    self.object.status = 'returned'
                    self.object.return_reason = reason
                    self.object.save()
                    messages.warning(request, "تم إعادة الطلب للعميل لاستكمال النواقص.")
                else:
                    messages.error(request, "يجب ذكر سبب الإعادة.")

            elif action == 'reject':
                reason = request.POST.get('rejection_reason')
                if not reason:
                    messages.error(request, "عذراً، يجب ذكر سبب الرفض.")
                    return redirect('requests:detail', pk=self.object.pk)

                self.object.status = 'rejected'
                self.object.rejection_reason = reason
                self.object.closed_by = user
                self.object.closed_at = timezone.now()
                self.object.save()
                messages.error(request, "تم رفض الطلب وإغلاقه.")

            elif action == 'complete':
                note = request.POST.get('closure_note')
                self.object.status = 'completed'
                if note:
                    self.object.closure_note = note
                self.object.closed_by = user
                self.object.closed_at = timezone.now()
                self.object.save()
                messages.success(request, "تم إكمال الطلب وإغلاقه بنجاح!")

        # 3. إجراءات العميل (Client) - هنا التصحيح الأساسي لإعادة الإرسال
        elif user.company.company_type == 'client':
            
            if action == 'resubmit' and self.object.status == 'returned':
                # أ) تحديث البيانات الأساسية (العنوان والملاحظات)
                new_title = request.POST.get('title')
                new_notes = request.POST.get('notes')
                if new_title: self.object.title = new_title
                if new_notes: self.object.notes = new_notes

                # ب) تحديث الحقول الديناميكية
                # نمر على القيم الموجودة ونبحث عن تحديث لها في الـ POST
                for fv in self.object.field_values.all():
                    field_key = f'field_{fv.field.id}' # نفس الاسم في الـ HTML
                    
                    if field_key in request.POST:
                        val = request.POST.get(field_key)
                        
                        # تحديث القيمة حسب نوع الحقل
                        if fv.field.field_type in ['text', 'choice']:
                            fv.value_text = val
                        elif fv.field.field_type == 'number':
                            fv.value_number = val
                        elif fv.field.field_type == 'date':
                            fv.value_date = val
                        elif fv.field.field_type == 'bool':
                            fv.value_bool = (val == 'True')
                        
                        fv.save() # حفظ القيمة الجديدة

                # ج) تغيير الحالة وتنظيف أسباب الرفض
                self.object.status = 'submitted'
                self.object.rejection_reason = "" 
                self.object.return_reason = ""    
                self.object.save()
                
                messages.success(request, "تم تحديث البيانات وإعادة إرسال الطلب بنجاح.")

        return redirect('requests:detail', pk=self.object.pk)

# دالة مساعدة AJAX
def get_request_fields(request, type_id):
    fields = RequestField.objects.filter(request_type_id=type_id, is_active=True).values(
        'id', 'label', 'field_type', 'is_required', 'help_text', 'choices'
    ).order_by('sort_order')
    return JsonResponse(list(fields), safe=False)