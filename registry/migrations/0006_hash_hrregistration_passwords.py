from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def hash_pending_passwords(apps, schema_editor):
    Request = apps.get_model("registry", "HRRegistrationRequest")
    for request in Request.objects.all().iterator():
        try:
            identify_hasher(request.password)
        except (ValueError, TypeError):
            Request.objects.filter(pk=request.pk).update(password=make_password(request.password))


class Migration(migrations.Migration):
    dependencies = [("registry", "0005_nurse_user_alter_employer_type_and_more")]
    operations = [migrations.RunPython(hash_pending_passwords, migrations.RunPython.noop)]
