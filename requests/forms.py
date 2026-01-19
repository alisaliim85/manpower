from django import forms
from .models import Request, RequestComment, RequestAttachment
from vendors.models import Worker

class RequestCreateForm(forms.ModelForm):
    """فورم إنشاء الطلب الأساسي"""
    class Meta:
        model = Request
        fields = ['request_type', 'worker', 'title', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'عنوان مختصر للطلب'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ملاحظات إضافية'}),
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'worker': forms.Select(attrs={'class': 'form-select select2'}),
        }

    def __init__(self, *args, **kwargs):
        # نستخرج المستخدم من المعاملات بشكل آمن ثم نحذفه حتى لا يسبب خطأ عند تمريره للـ super
        user = kwargs.pop('user', None)
        
        # استدعاء دالة البناء الأساسية
        super(RequestCreateForm, self).__init__(*args, **kwargs)

        # منطق فلترة العمالة
        if user and hasattr(user, 'company') and user.company:
            if user.company.company_type == 'client':
                # الحالة الأولى: المستخدم هو "عميل"
                # يجب أن يرى فقط العمال التابعين للموردين المتعاقد معهم
                self.fields['worker'].queryset = Worker.objects.filter(
                    vendor__clients=user.company
                )
                # ملاحظة: إذا أردت تفعيل شرط الحالة لاحقاً تأكد من الاسم الدقيق في قاعدة البيانات
                # .filter(status__iexact='active')

            elif user.company.company_type == 'vendor':
                # الحالة الثانية: المستخدم هو "مورد"
                # يرى عمال شركتة فقط
                self.fields['worker'].queryset = Worker.objects.filter(
                    vendor__company=user.company
                )
        else:
            # حالة أمان: إذا لم يكن هناك مستخدم أو شركة، لا تعرض أي عامل
            self.fields['worker'].queryset = Worker.objects.none()

class CommentForm(forms.ModelForm):
    """فورم إضافة تعليق"""
    class Meta:
        model = RequestComment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'اكتب تعليقك هنا...'})
        }

class AttachmentForm(forms.ModelForm):
    """فورم رفع المرفقات"""
    description = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'وصف الملف (اختياري)'}))
    
    class Meta:
        model = RequestAttachment
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
        }

# فورمات للإجراءات الخاصة (الرفض، الإعادة، الإغلاق)
class RejectRequestForm(forms.Form):
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'سبب الرفض...'})
    )

class ReturnRequestForm(forms.Form):
    return_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'سبب الإعادة والنواقص...'})
    )

class CompleteRequestForm(forms.Form):
    closure_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'ملاحظة الإغلاق (اختياري)...'})
    )