from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def company_access_required(company_type):
    """
    يسمح بالدخول فقط حسب نوع الشركة
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                messages.error(request, "يرجى تسجيل الدخول أولًا")
                return redirect('/accounts/login/')

            if not request.user.company:
                messages.error(request, "لا توجد شركة مرتبطة بهذا الحساب")
                return redirect('/accounts/login/')

            if request.user.company.company_type != company_type:
                messages.error(request, "غير مصرح لك بالدخول إلى هذه الصفحة")
                return redirect('/accounts/login/')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
