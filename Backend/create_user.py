"""Deprecated compatibility entrypoint for seeding the default HR user."""
from seed_hr_user import seed_user


if __name__ == "__main__":
    print("create_user.py is deprecated. Seeding the default HR user instead.")
    seed_user()
