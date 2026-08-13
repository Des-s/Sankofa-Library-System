"""One-off script to create an admin and a librarian account.

Run with: python create_accounts.py
Edit the EMAIL / PASSWORD / USERNAME values below before running.
"""
from app import create_app
from app.extensions import db, bcrypt
from app.models import User

app = create_app()

with app.app_context():
    accounts = [
        {
            "full_name": "Admin User",
            "username": "admin",
            "email": "admin@st.knust.edu.gh",
            "password": "ChangeMe123",
            "role": "admin",
        },
        {
            "full_name": "Librarian User",
            "username": "librarian",
            "email": "librarian@st.knust.edu.gh",
            "password": "ChangeMe123",
            "role": "librarian",
        },
    ]

    for acc in accounts:
        existing = User.query.filter(
            (User.username == acc["username"]) | (User.email == acc["email"])
        ).first()
        if existing:
            print(f"Skipping {acc['username']} — already exists.")
            continue

        user = User(
            full_name=acc["full_name"],
            username=acc["username"],
            email=acc["email"],
            password_hash=bcrypt.generate_password_hash(acc["password"]).decode("utf-8"),
            role=acc["role"],
            student_id=None,
            department=None,
            year_of_study=None,
            is_active=True,
            approval_status="approved",
            theme_preference="light",
            language_preference="en",
            email_notifications=True,
            must_change_password=False,
            failed_login_attempts=0,
        )
        db.session.add(user)
        print(f"Created {acc['role']} account: {acc['username']} / {acc['password']}")

    db.session.commit()
    print("Done.")