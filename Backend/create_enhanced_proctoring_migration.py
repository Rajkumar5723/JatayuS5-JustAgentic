"""
create_enhanced_proctoring_migration.py
========================================
Creates database migration for enhanced proctoring tables.
Run this to generate the Alembic migration.
"""
import os
import sys

# Add Backend to path
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from alembic.config import Config
from alembic import command

def create_migration():
    """Create Alembic migration for enhanced proctoring tables."""
    print("Creating database migration for enhanced proctoring tables...")
    
    # Get alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Create migration
    command.revision(
        alembic_cfg,
        autogenerate=True,
        message="Add enhanced proctoring evidence tables"
    )
    
    print("✅ Migration created successfully!")
    print("\nNext steps:")
    print("1. Review the migration file in alembic/versions/")
    print("2. Run: alembic upgrade head")
    print("3. Verify tables were created in database")

if __name__ == "__main__":
    create_migration()
