from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from .models import Request, RequestType, RequestField, RequestFieldValue, RequestTimeline, RequestAttachment
from .forms import (
    RequestCreateForm, CommentForm, AttachmentForm, 
    RejectRequestForm, ReturnRequestForm, CompleteRequestForm
)
from notifications.models import Notification
from vendors.models import Worker  

# دالة مساعدة لإنشاء الإشعارات
def create_notification(user, request_obj, title, message):
    if user:
        Notification.objects.create(
            recipient=user,
            request=request_obj,
            title=title,
            message=message
        )

# دالة مساعدة لتسجيل التايم لاين
def log_timeline(request_obj, user, action, desc="", old_status="", new_status=""):
    RequestTimeline.objects.create(
        request=request_obj,
        user=user,
        action_name=action,
        description=desc,
        old_status=old_status,
        new_status=new_status
    )

# ==========================================
# 1. إنشاء الطلب (Create Request)
# ==========================================
@login_required
def create_request_wizard(request):

    if request.user.company.company_type != 'client':
        messages.error(request, "عذراً، إنشاء الطلبات متاح لشركات العملاء فقط.")
        return redirect('dashboard')
    # --- DEBUGGING START ---
    print(f"User: {request.user.username}")
    print(f"My Company: {request.user.company}")
    print(f"My Company Type: {request.user.company.company_type}")

    # لنحاول جلب العمال يدوياً لنرى هل توجد نتائج
    workers_test = Worker.objects.filter(vendor__clients=request.user.company)
    print(f"Workers Found Count: {workers_test.count()}")

    if workers_test.count() == 0:
        print("WARNING: No workers found. Checking Vendors...")
        # لنفحص الموردين المتعاقد معهم
        vendors = request.user.company.contracted_vendors.all() # لاحظ استخدام related_name العكسي
        print(f"Contracted Vendors Count: {vendors.count()}")
        for v in vendors:
            print(f" - Vendor: {v.id} | Workers Count: {v.worker_set.count()}")
    # --- DEBUGGING END ---    
    if request.method == 'POST':
        form = RequestCreateForm(request.POST, user=request.user)
        if form.is_valid():
            new_request = form.save(commit=False)
            new_request.created_by = request.user
            new_request.status = 'draft'
            new_request.current_company = request.user.company
            new_request.save()

            # معالجة الحقول الديناميكية (تبقى يدوية لأنها تعتمد على النوع المختار)
            type_id = new_request.request_type.id
            fields = RequestField.objects.filter(request_type_id=type_id)
            
            for field in fields:
                val = request.POST.get(f'field_{field.id}')
                if val:
                    fv = RequestFieldValue(request=new_request, field=field)
                    if field.field_type == 'text': fv.value_text = val
                    elif field.field_type == 'number': fv.value_number = val
                    elif field.field_type == 'date': fv.value_date = val
                    elif field.field_type == 'bool': fv.value_bool = (val == 'True')
                    elif field.field_type == 'choice': fv.value_text = val
                    fv.save()

            messages.info(request, "تم حفظ المسودة. يرجى إضافة المرفقات ثم الإرسال.")
            return redirect('requests:detail', pk=new_request.pk)
        else:
            messages.error(request, "يرجى التأكد من صحة البيانات المدخلة.")
    else:
        form = RequestCreateForm(user=request.user)
    workers = form.fields['worker'].queryset
    # نحتاج قائمة الأنواع للعرض في القائمة المنسدلة الأولية في الـ Wizard
    request_types = RequestType.objects.filter(is_active=True)
    
    context = {
        'form': form,
        'workers': workers,
        'request_types': request_types,
    }
    return render(request, 'requests-templates/create_wizard.html', context)


# ==========================================
# 2. قائمة الطلبات (Request List)
# ==========================================
@login_required
def request_list(request):
    user = request.user
    
    # 1. الاستعلام الأساسي
    qs = Request.objects.select_related('worker', 'request_type', 'created_by').order_by('-created_at')

    # 2. التصفية حسب الصلاحية
    if user.company.company_type == 'client':
        qs = qs.filter(created_by__company=user.company)
    elif user.company.company_type == 'vendor':
        qs = qs.filter(worker__vendor__company=user.company).exclude(status='draft')
    else:
        qs = qs.none()

    # إنشاء نسخة للإحصائيات قبل الفلترة بالبحث
    qs_all = qs 

    # 3. البحث
    search_query = request.GET.get('q')
    if search_query:
        qs = qs.filter(
            Q(id__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(worker__full_name__icontains=search_query) |
            Q(worker__iqama_number__icontains=search_query)
        )

    # 4. فلترة الحالة
    status_filter = request.GET.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)

    # 5. الترحيل (Pagination)
    paginator = Paginator(qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 6. حساب الإحصائيات
    context = {
        'requests': page_obj, # نستخدم requests ليتوافق مع القالب
        'page_obj': page_obj,
        'total_count': qs_all.count(),
        'submitted_count': qs_all.filter(status='submitted').count(),
        'in_progress_count': qs_all.filter(status='in_progress').count(),
        'completed_count': qs_all.filter(status='completed').count(),
        'rejected_count': qs_all.filter(status='rejected').count(),
        'companies_count': qs_all.values('worker__vendor__company').distinct().count(),
        'current_q': search_query or '',
        'current_status': status_filter or '',
    }
    
    return render(request, 'requests-templates/request_list.html', context)


# ==========================================
# 3. تفاصيل الطلب (Request Detail & Actions)
# ==========================================
@login_required
def request_detail(request, pk):
    # جلب الطلب مع التحقق من الصلاحية
    user = request.user
    base_qs = Request.objects.select_related('worker', 'request_type', 'created_by')
    
    if user.company.company_type == 'client':
        req = get_object_or_404(base_qs, pk=pk, created_by__company=user.company)
    elif user.company.company_type == 'vendor':
        req = get_object_or_404(base_qs, pk=pk, worker__vendor__company=user.company)
        # المورد لا يرى المسودات
        if req.status == 'draft':
            return HttpResponseForbidden("لا تملك صلاحية الوصول لهذا الطلب.")
    else:
        return HttpResponseForbidden()

    # تعريف الفورمز (فارغة افتراضياً)
    comment_form = CommentForm()
    attachment_form = AttachmentForm()
    reject_form = RejectRequestForm()
    return_form = ReturnRequestForm()
    complete_form = CompleteRequestForm()

    # معالجة الـ POST (الإجراءات)
    if request.method == 'POST':
        action = request.POST.get('action')
        current_status = req.status

        # --- إضافة تعليق ---
        if action == 'add_comment':
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.request = req
                comment.author = user
                comment.save()
                messages.success(request, "تم إضافة التعليق.")
                return redirect('requests:detail', pk=pk)

        # --- رفع مرفق ---
        elif action == 'upload_attachment':
            attachment_form = AttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                att = attachment_form.save(commit=False)
                att.request = req
                att.uploaded_by = user
                att.save()
                messages.success(request, "تم رفع الملف.")
                return redirect('requests:detail', pk=pk)

        # --- إجراءات المورد ---
        if user.company.company_type == 'vendor':
            if action == 'start_processing' and req.status == 'submitted':
                req.status = 'in_progress'
                req.current_company = user.company
                req.save()
                log_timeline(req, user, "بدء المعالجة", "بدأ المورد في العمل", current_status, 'in_progress')
                messages.success(request, "تم تغيير الحالة إلى قيد المعالجة.")
                create_notification(req.created_by, req, "الطلب قيد المعالجة", f"بدأ {user.company.name} العمل على الطلب.")
            
            elif action == 'return_defect':
                return_form = ReturnRequestForm(request.POST)
                if return_form.is_valid():
                    reason = return_form.cleaned_data['return_reason']
                    req.status = 'returned'
                    req.return_reason = reason
                    req.save()
                    log_timeline(req, user, "إعادة (نواقص)", reason, current_status, 'returned')
                    messages.warning(request, "تم إعادة الطلب للعميل.")
                    create_notification(req.created_by, req, "نقص في الطلب", f"سبب الإعادة: {reason}")
                else:
                    messages.error(request, "يرجى كتابة سبب الإعادة.")

            elif action == 'reject':
                reject_form = RejectRequestForm(request.POST)
                if reject_form.is_valid():
                    reason = reject_form.cleaned_data['rejection_reason']
                    req.status = 'rejected'
                    req.rejection_reason = reason
                    req.closed_by = user
                    req.closed_at = timezone.now()
                    req.save()
                    log_timeline(req, user, "رفض الطلب", reason, current_status, 'rejected')
                    messages.error(request, "تم رفض الطلب.")
                    create_notification(req.created_by, req, "الطلب مرفوض", f"السبب: {reason}")
                else:
                    messages.error(request, "يرجى كتابة سبب الرفض.")

            elif action == 'complete':
                complete_form = CompleteRequestForm(request.POST)
                if complete_form.is_valid():
                    note = complete_form.cleaned_data['closure_note']
                    req.status = 'completed'
                    req.closure_note = note
                    req.closed_by = user
                    req.closed_at = timezone.now()
                    req.save()
                    log_timeline(req, user, "إكمال الطلب", note, current_status, 'completed')
                    messages.success(request, "تم إكمال الطلب بنجاح.")

        # --- إجراءات العميل ---
        elif user.company.company_type == 'client':
            if action == 'confirm_submission' and req.status == 'draft':
                req.status = 'submitted'
                req.created_at = timezone.now()
                req.save()
                log_timeline(req, user, "إرسال الطلب", "تم الاعتماد والإرسال", 'draft', 'submitted')
                messages.success(request, "تم إرسال الطلب.")
                
                # إشعار موظفي المورد
                staff_members = req.worker.vendor.get_all_staff
                for staff in staff_members:
                    if staff.is_active:
                        create_notification(staff, req, "طلب جديد", f"طلب جديد #{req.id} للعامل {req.worker.full_name}")

            elif action == 'delete_draft' and req.status == 'draft':
                req.delete()
                messages.success(request, "تم حذف المسودة.")
                return redirect('requests:list')

            elif action == 'resubmit' and req.status == 'returned':
                # تحديث البيانات (يمكن استخدام فورم هنا أيضاً، لكن للتبسيط سنكتفي بالتحديث المباشر للقيم الأساسية)
                new_title = request.POST.get('title')
                new_notes = request.POST.get('notes')
                if new_title: req.title = new_title
                if new_notes: req.notes = new_notes
                
                # تحديث الحقول الديناميكية
                for fv in req.field_values.all():
                    val = request.POST.get(f'field_{fv.field.id}')
                    if val is not None:
                        # منطق حفظ مبسط
                        if fv.field.field_type in ['text', 'choice']: fv.value_text = val
                        elif fv.field.field_type == 'number': fv.value_number = val
                        # ... بقية الأنواع
                        fv.save()

                req.status = 'submitted'
                req.rejection_reason = ""
                req.return_reason = ""
                req.save()
                log_timeline(req, user, "إعادة إرسال", "تم التصحيح", 'returned', 'submitted')
                messages.success(request, "تم إعادة الإرسال.")

            elif action == 'delete_attachment':
                att_id = request.POST.get('attachment_id')
                try:
                    att = RequestAttachment.objects.get(id=att_id, request=req)
                    att.delete()
                    messages.success(request, "تم حذف المرفق.")
                except RequestAttachment.DoesNotExist:
                    messages.error(request, "المرفق غير موجود.")

        return redirect('requests:detail', pk=pk)

    # Context (GET Request)
    context = {
        'req': req,
        'dynamic_values': req.field_values.all().select_related('field'),
        'timeline': req.timeline_events.all().order_by('-created_at'),
        # Forms
        'comment_form': comment_form,
        'attachment_form': attachment_form,
        'reject_form': reject_form,
        'return_form': return_form,
        'complete_form': complete_form,
    }
    return render(request, 'requests-templates/request_detail.html', context)


# دالة API للحقول الديناميكية (تبقى كما هي)
def get_request_fields(request, type_id):
    fields = RequestField.objects.filter(request_type_id=type_id, is_active=True).values(
        'id', 'label', 'field_type', 'is_required', 'help_text', 'choices'
    ).order_by('sort_order')
    return JsonResponse(list(fields), safe=False)