# PlateauNurseRegister

Plateau State Nurse Registry and Licence Verification Platform.

## Local setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```
