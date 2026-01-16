import os
import django
import random
from datetime import timedelta, date
from faker import Faker

# 1. إعداد بيئة جانغو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'manpower.settings')
django.setup()

# 2. استيراد الموديلات
from accounts.models import Company
from vendors.models import Vendor, Worker

def create_seeds():
    # تعديل: إزالة ['ar_SA'] ليستخدم الإنجليزية كافتراضي
    fake = Faker() 
    
    # أسماء شركات التجربة
    target_companies = ['ABDAL', 'MAHARAH', 'SAED']
    vendors_objs = []

    print("--- 1. Preparing Companies and Vendors ---")
    
    for comp_name in target_companies:
        # إنشاء أو جلب الشركة
        company, created = Company.objects.get_or_create(
            name=comp_name,
            defaults={
                'company_type': 'vendor',
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Company created: {comp_name}")
        else:
            print(f"ℹ️ Company exists: {comp_name}")

        # ربط الشركة ببروفايل المورد
        vendor, v_created = Vendor.objects.get_or_create(
            company=company,
            defaults={
                'contact_name': fake.name(), # اسم إنجليزي
                'contact_phone': f"05{random.randint(10000000, 99999999)}",
                'is_active': True
            }
        )
        vendors_objs.append(vendor)
        
        if v_created:
            print(f"   -> Vendor profile created for {comp_name}")

    print("\n--- 2. Adding 100 Workers (English Data) ---")

    # قوائم المهن والجنسيات بالإنجليزية
    job_titles = [
        'Private Driver', 'General Laborer', 'Electrician', 'Plumber', 
        'Carpenter', 'HVAC Technician', 'Cook', 'Security Guard', 
        'Admin Assistant', 'Cleaner', 'Welder', 'Mechanic'
    ]
    
    nationalities = [
        'Egypt', 'India', 'Pakistan', 'Bangladesh', 
        'Philippines', 'Yemen', 'Sudan', 'Nepal', 'Sri Lanka'
    ]
    
    insurance_classes = ['vip', 'a', 'b', 'c']
    
    workers_count = 0
    
    for _ in range(100):
        selected_vendor = random.choice(vendors_objs)
        
        # تواريخ عشوائية
        days_in_future = random.randint(30, 730)
        expiry_date = date.today() + timedelta(days=days_in_future)
        joined_date = date.today() - timedelta(days=random.randint(10, 365))
        
        # رقم إقامة عشوائي
        iqama = str(random.randint(2000000000, 2999999999))

        if not Worker.objects.filter(iqama_number=iqama).exists():
            Worker.objects.create(
                vendor=selected_vendor,
                full_name=fake.name(), # سيولد اسماً إنجليزياً الآن
                iqama_number=iqama,
                nationality=random.choice(nationalities),
                job_title=random.choice(job_titles),
                
                # الحقول حسب المودل الخاص بك
                iqama_expiry_date=expiry_date,
                insurance_class=random.choice(insurance_classes),
                joined_at=joined_date,
                status='active'
            )
            workers_count += 1

    print(f"✅ Success! Added {workers_count} workers distributed among the 3 companies.")

if __name__ == '__main__':
    create_seeds()