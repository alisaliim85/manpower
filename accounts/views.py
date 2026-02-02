from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .decorators import company_access_required
from vendors.models import Vendor, Worker
from requests.models import Request
from django.db.models import Q, Count


def landing_page(request):
    return render(request, 'landing/home.html')


def login_view(request):
    # منع الوصول لصفحة الدخول إذا كان مسجل مسبقًا
    if request.user.is_authenticated:
        return redirect_by_company(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "يرجى إدخال اسم المستخدم وكلمة المرور")
            return render(request, "accounts-templates/accounts/login.html")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "هذا الحساب غير مفعل")
                return render(request, "accounts-templates/accounts/login.html")

            login(request, user)
            return redirect_by_company(user)

        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة")

    return render(request, "accounts-templates/accounts/login.html")


def redirect_by_company(user):
    if user.is_superuser:
        return redirect('/admin/')


    if not user.company:
        return redirect('/accounts/login/')

    if user.company.company_type == 'client':
        return redirect('/accounts/client/dashboard/')

    if user.company.company_type == 'vendor':
        return redirect('/accounts/vendor/dashboard/')

    return redirect('/accounts/login/')


@company_access_required('client')
def client_dashboard(request):
    # 1. جلب جميع الموردين من قاعدة البيانات
    vendors_list = Vendor.objects.select_related('company').annotate(workers_count=Count('workers'))
    
    # 2. تجهيز البيانات لإرسالها للقالب
    context = {
        'vendors': vendors_list,
        'vendors_count': vendors_list.count(),
        # يمكنك لاحقاً إضافة إحصائيات الطلبات هنا
    }
    
    # 3. إرسال الـ context مع الـ render
    return render(request, 'client/dashboard.html', context)


@company_access_required('vendor')
def vendor_dashboard(request):
    user_company = request.user.company
    
    # التأكد أن المستخدم يتبع لشركة من نوع مورد (vendor)
    if user_company and user_company.company_type == 'vendor':
        # جلب الطلبات المرتبطة بعمال هذا المورد فقط
        # نستثني المسودات (draft) لأن المورد لا يجب أن يراها حتى يتم إرسالها
        base_requests = Request.objects.filter(
            worker__vendor__company=user_company
        ).exclude(status='draft')
        
        # حساب الإحصائيات
        stats = {
            'workers_count': Worker.objects.filter(vendor__company=user_company).count(),
            'total_incoming': base_requests.count(),
            'new_requests': base_requests.filter(status='submitted').count(),
            'in_progress': base_requests.filter(status='in_progress').count(),
            'completed': base_requests.filter(status='completed').count(),
            'returned_rejected': base_requests.filter(status__in=['returned', 'rejected']).count(),
            'recent_requests': base_requests.order_by('-created_at')[:5]
        }
    else:
        stats = {}

    context = {
        'stats': stats,
    }
    return render(request, 'vendor/dashboard.html', context)


def logout_view(request):
    """
    تسجيل خروج المستخدم وإنهاء الجلسة
    """
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح")
    return redirect('/accounts/login/')
