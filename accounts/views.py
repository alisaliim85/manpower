from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .decorators import company_access_required
from vendors.models import Vendor


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
    vendors_list = Vendor.objects.all()
    
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
    return render(request, 'vendor/dashboard.html')


def logout_view(request):
    """
    تسجيل خروج المستخدم وإنهاء الجلسة
    """
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح")
    return redirect('/accounts/login/')
