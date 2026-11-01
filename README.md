# PlateauNurseRegister

Plateau State Nurse Registry and Licence Verification Platform.

## Local setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Put the generated value in NIN_ENCRYPTION_KEY in .env
python manage.py migrate
python manage.py setup_groups
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/` and sign in at `/admin/`.

`NIN_ENCRYPTION_KEY` is required for registration and NIN reveal. Keep the same key for the life of the database; changing it makes existing encrypted NINs unreadable.

## Demo data

`seed_demo` creates 60 fake nurses and 4 employers. Use `--reset` to replace existing demo data:

```bash
python manage.py seed_demo --reset
```

Demo accounts all use password `DemoPass123!`:

- `demo_officer1`, `demo_officer2`
- `demo_supervisor`
- `demo_superadmin`
- `demo_hr1`, `demo_hr2`

## Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
