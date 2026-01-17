from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from .models import Request, RequestType, RequestField, RequestFieldValue, RequestComment,RequestAttachment, RequestTimeline
from vendors.models import Worker
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from notifications.models import Notification

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
            status='draft',
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

        messages.info(self.request, "تم حفظ الطلب كمسودة. يرجى مراجعته وإضافة المرفقات ثم الضغط على إرسال.")
        return redirect('requests:detail', pk=new_request.pk)
# ==========================================
# 2. قائمة الطلبات (List)
# ==========================================
class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = 'requests-templates/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        
        # 1. الاستعلام الأساسي وترتيبه
        qs = Request.objects.select_related('worker', 'request_type', 'created_by').order_by('-created_at')

        # 2. تصفية البيانات حسب نوع المستخدم (بدون return)
        if user.company.company_type == 'client':
            qs = qs.filter(created_by__company=user.company)
        elif user.company.company_type == 'vendor':
            qs = qs.filter(worker__vendor__company=user.company).exclude(status='draft')
        else:
            return qs.none() # هنا فقط نعيد فارغ اذا لم يكن عميل او مورد

        # 3. منطق البحث (Search Logic)
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(
                Q(id__icontains=search_query) |               # بحث برقم الطلب
                Q(title__icontains=search_query) |            # بحث بعنوان الطلب
                Q(worker__full_name__icontains=search_query) | # بحث باسم العامل
                Q(worker__iqama_number__icontains=search_query)# بحث برقم الإقامة
            )

        # 4. منطق الفلترة (Status Filter)
        status_filter = self.request.GET.get('status')
        if status_filter and status_filter != "":
            qs = qs.filter(status=status_filter)

        # 5. الإرجاع النهائي بعد تطبيق كل الشروط
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # هنا نحسب العدادات للإحصائيات بناءً على "كل البيانات" وليس نتائج البحث فقط
        # لذلك نعيد استعلاماً جديداً (qs_all)
        user = self.request.user
        qs_all = Request.objects.select_related('worker', 'request_type', 'created_by')
        
        if user.company.company_type == 'client':
            qs_all = qs_all.filter(created_by__company=user.company)
        elif user.company.company_type == 'vendor':
            qs_all = qs_all.filter(worker__vendor__company=user.company).exclude(status='draft')

        # الإحصائيات
        context['total_count'] = qs_all.count()
        context['submitted_count'] = qs_all.filter(status='submitted').count()
        context['in_progress_count'] = qs_all.filter(status='in_progress').count()
        context['completed_count'] = qs_all.filter(status='completed').count()
        context['rejected_count'] = qs_all.filter(status='rejected').count()
        context['companies_count'] = qs_all.values('worker__vendor__company').distinct().count()
        
        # تمرير قيم البحث الحالية للقالب لكي تظل مكتوبة في الحقل
        context['current_q'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', '')
        
        return context
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #qs = self.get_queryset() 
        user = self.request.user
        qs_all = Request.objects.select_related('worker', 'request_type', 'created_by')
        if user.company.company_type == 'client':
            qs_all = qs_all.filter(created_by__company=user.company)
        elif user.company.company_type == 'vendor':
            qs_all = qs_all.filter(worker__vendor__company=user.company).exclude(status='draft')

# الإحصائيات (Counters)
        context['total_count'] = qs_all.count()
        context['submitted_count'] = qs_all.filter(status='submitted').count()
        context['in_progress_count'] = qs_all.filter(status='in_progress').count()
        context['completed_count'] = qs_all.filter(status='completed').count()
        context['rejected_count'] = qs_all.filter(status='rejected').count()
        context['companies_count'] = qs_all.values('worker__vendor__company').distinct().count()        
        return context


def create_notification(user, request_obj, title, message):
    if user:
        Notification.objects.create(
            recipient=user,
            request=request_obj,
            title=title,
            message=message
        )



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
            return qs.filter(worker__vendor__company=user.company).exclude(status='draft')
            
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dynamic_values'] = self.object.field_values.all().select_related('field')
        context['timeline'] = self.object.timeline_events.all().order_by('-created_at')
        return context
# --- دالة مساعدة لتسجيل الحركة في التايم لاين ---
    def log_timeline(self, action, desc="", old_status="", new_status=""):
        RequestTimeline.objects.create(
            request=self.object,
            user=self.request.user,
            action_name=action,
            description=desc,
            old_status=old_status,
            new_status=new_status
        )
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action')
        user = request.user

        # حفظ الحالة القديمة قبل التغيير
        current_status = self.object.status
        
        # ------------------------------------------------------------------
        # 1. إجراءات عامة (متاحة للجميع: عميل ومورد)
        # ------------------------------------------------------------------

        # أ) إضافة تعليق
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

        # ب) رفع مرفق (عام للجميع)
        if action == 'upload_attachment':
            uploaded_file = request.FILES.get('attachment_file')
            file_desc = request.POST.get('attachment_desc')
            
            if uploaded_file:
                RequestAttachment.objects.create(
                    request=self.object,
                    file=uploaded_file,
                    uploaded_by=user,
                    description=file_desc
                )
                messages.success(request, "تم رفع الملف بنجاح.")
            else:
                messages.error(request, "يرجى اختيار ملف لرفعه.")
            return redirect('requests:detail', pk=self.object.pk)

        # ------------------------------------------------------------------
        # 2. إجراءات خاصة بالمورد (Vendor Only)
        # ------------------------------------------------------------------
        if user.company.company_type == 'vendor':
            if action == 'start_processing' and self.object.status == 'submitted':
                self.object.status = 'in_progress'
                self.object.current_company = user.company
                self.object.save()
                # تسجيل الحركة
                self.log_timeline("بدء المعالجة", "بدأ المورد في معالجة الطلب", current_status, 'in_progress')
                messages.success(request, "تم بدء معالجة الطلب.")
                #ارسال الاشعارات
                create_notification(
                    user=self.object.created_by,
                    request_obj=self.object,
                    title="الطلب قيد المعالجة",
                    message=f"قام المورد {user.company.name} ببدء العمل على طلبك."
                )

            elif action == 'return_defect' and self.object.status == 'in_progress':
                reason = request.POST.get('return_reason')
                if reason:
                    self.object.status = 'returned'
                    self.object.return_reason = reason
                    self.object.save()
                    # تسجيل الحركة
                    self.log_timeline("إعادة الطلب (نواقص)", f"السبب: {reason}", current_status, 'returned')
                    messages.warning(request, "تم إعادة الطلب للعميل لاستكمال النواقص.")
                #ارسال الاشعارات
                    create_notification(
                    user=self.object.created_by,
                    request_obj=self.object,
                    title="تنبيه: يوجد نقص في الطلب",
                    message=f"أعاد المورد الطلب لوجود ملاحظات: {reason}"
                )
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
                # تسجيل الحركة
                self.log_timeline("رفض الطلب", f"سبب الرفض: {reason}", current_status, 'rejected')
                messages.error(request, "تم رفض الطلب وإغلاقه.")
                #ارسال الاشعارات
                create_notification(
                    user=self.object.created_by,
                    request_obj=self.object,
                    title="الطلب مرفوض",
                    message=f"قام المورد برفض الطلب لوجود ملاحظات: {reason}"
                    )

            elif action == 'complete':
                note = request.POST.get('closure_note')
                self.object.status = 'completed'
                if note:
                    self.object.closure_note = note
                self.object.closed_by = user
                self.object.closed_at = timezone.now()
                self.object.save()
                # تسجيل الحركة
                self.log_timeline("إكمال الطلب", note, current_status, 'completed')
                messages.success(request, "تم إكمال الطلب وإغلاقه بنجاح!")

        # ------------------------------------------------------------------
        # 3. إجراءات خاصة بالعميل (Client Only)
        # ------------------------------------------------------------------
        elif user.company.company_type == 'client':

            if action == 'confirm_submission' and self.object.status == 'draft':
                # التحقق النهائي (اختياري: مثلاً هل توجد مرفقات؟)
                # if not self.object.attachments.exists():
                #     messages.error(request, "يجب إضافة مرفق واحد على الأقل قبل الإرسال.")
                #     return redirect(...)

                self.object.status = 'submitted' # تحويل الحالة لمرسل
                self.object.created_at = timezone.now() # تحديث وقت الإرسال الفعلي
                self.object.save()
                # تسجيل الحركة (الأهم)
                self.log_timeline("إنشاء وإرسال الطلب", "تم اعتماد المسودة وإرسالها للمورد", 'draft', 'submitted')
                messages.success(request, "تم إرسال الطلب للمورد بنجاح!")
                #ارسال الاشعارات
                vendor_profile = self.object.worker.vendor
                # 1. الوصول لبروفايل المورد المرتبط بالعامل
                vendor_profile = self.object.worker.vendor
                
                # 2. جلب جميع موظفي الشركة
                staff_members = vendor_profile.get_all_staff

                # 3. حلقة تكرار لإرسال الإشعار لكل واحد منهم
                count_sent = 0
                for staff in staff_members:
                    # نتأكد أن الموظف نشط (اختياري)
                    if staff.is_active:
                        create_notification(
                            user=staff,
                            request_obj=self.object,
                            title="طلب جديد وارد 🔔",
                            message=f"قام {user.company.name} بإرسال طلب جديد #{self.object.id} للعامل {self.object.worker.full_name}"
                        )
                        count_sent += 1
                


                return redirect('requests:list') # أو البقاء في نفس الصفحة

            # (ب) حذف المسودة (جديد)
            elif action == 'delete_draft' and self.object.status == 'draft':
                self.object.delete() # حذف الطلب بالكامل
                messages.success(request, "تم إلغاء المسودة وحذفها.")
                return redirect('requests:list') # العودة للقائمة لأن الطلب لم يعد موجوداً
            
            # أ) إعادة الإرسال
            if action == 'resubmit' and self.object.status == 'returned':
                new_title = request.POST.get('title')
                new_notes = request.POST.get('notes')
                if new_title: self.object.title = new_title
                if new_notes: self.object.notes = new_notes

                for fv in self.object.field_values.all():
                    field_key = f'field_{fv.field.id}'
                    if field_key in request.POST:
                        val = request.POST.get(field_key)
                        if fv.field.field_type in ['text', 'choice']:
                            fv.value_text = val
                        elif fv.field.field_type == 'number':
                            fv.value_number = val
                        elif fv.field.field_type == 'date':
                            fv.value_date = val
                        elif fv.field.field_type == 'bool':
                            fv.value_bool = (val == 'True')
                        fv.save()

                self.object.status = 'submitted'
                self.object.rejection_reason = "" 
                self.object.return_reason = ""    
                self.object.save()
                self.log_timeline("إعادة إرسال (تصحيح)", "تم تعديل النواقص وإعادة الإرسال", 'returned', 'submitted')
                messages.success(request, "تم تحديث البيانات وإعادة إرسال الطلب بنجاح.")

            # ب) حذف المرفق (متاح للعميل فقط)
            elif action == 'delete_attachment':
                att_id = request.POST.get('attachment_id')
                try:
                    # نتحقق أن المرفق يتبع نفس الطلب الحالي لزيادة الأمان
                    att = RequestAttachment.objects.get(id=att_id, request=self.object)
                    att.delete()
                    messages.success(request, "تم حذف المرفق بنجاح.")
                except RequestAttachment.DoesNotExist:
                    messages.error(request, "عذراً، المرفق غير موجود أو لا تملك صلاحية حذفه.")

        return redirect('requests:detail', pk=self.object.pk)
# دالة مساعدة AJAX
def get_request_fields(request, type_id):
    fields = RequestField.objects.filter(request_type_id=type_id, is_active=True).values(
        'id', 'label', 'field_type', 'is_required', 'help_text', 'choices'
    ).order_by('sort_order')
    return JsonResponse(list(fields), safe=False)