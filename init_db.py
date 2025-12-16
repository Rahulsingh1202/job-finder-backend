from database import create_tables

if __name__ == "__main__":
    print("🔧 Initializing database...")
    create_tables()
    print("✅ Database initialized successfully!")
    print("📁 Database file: job_finder.db")
