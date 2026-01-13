from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import Request, RequestType, RequestField, RequestFieldValue
from vendors.models import Worker
from django.contrib import messages
from django.utils import timezone

class RequestWizardView(LoginRequiredMixin, TemplateView):
    template_name = 'requests-templates/create_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['request_types'] = RequestType.objects.filter(is_active=True)
        # جلب عمال شركة العميل (بناءً على منطق مشروعك)
        context['workers'] = Worker.objects.all() 
        return context

    def post(self, request, *args, **kwargs):
        type_id = request.POST.get('request_type')
        worker_id = request.POST.get('worker')
        
        # 1. إنشاء الطلب الأساسي
        new_request = Request.objects.create(
            request_type_id=type_id,
            worker_id=worker_id,
            title=request.POST.get('title', ''),
            notes=request.POST.get('notes', ''),
            created_by=request.user,
            status='submitted'
        )

        # 2. جلب الحقول وحفظ قيمها
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
# 3. عرض تفاصيل الطلب (الكلاس الذي كان ينقصك)
class RequestDetailView(LoginRequiredMixin, DetailView):
    model = Request
    template_name = 'requests-templates/request_detail.html'
    context_object_name = 'req'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # جلب القيم الديناميكية المرتبطة بهذا الطلب لعرضها
        context['dynamic_values'] = self.object.field_values.all().select_related('field')
        return context
