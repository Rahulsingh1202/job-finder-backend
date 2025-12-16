from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Create SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./job_finder.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database Models

class User(Base):
    """User table - stores authenticated users"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    google_id = Column(String, unique=True, nullable=False)
    picture = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")
    experiences = relationship("Experience", back_populates="user")
    saved_jobs = relationship("SavedJob", back_populates="user")


class Resume(Base):
    """Resume table - stores parsed resume data"""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    name = Column(String)
    email = Column(String)
    phone = Column(String)
    skills = Column(Text)  # JSON string of skills list
    raw_text = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    user = relationship("User", back_populates="resumes")


class Experience(Base):
    """Experience table - stores user work experience"""
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    duration = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="experiences")


class SavedJob(Base):
    """Saved Jobs table - stores jobs bookmarked by users"""
    __tablename__ = "saved_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    link = Column(String, nullable=False)
    hr_email = Column(String)
    saved_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  
    is_applied = Column(Boolean, default=False)
    notes = Column(Text)
    
    # Relationship
    user = relationship("User", back_populates="saved_jobs")


# Database helper functions

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def get_or_create_user(db, user_info):
    """Get existing user or create new one"""
    user = db.query(User).filter(User.google_id == user_info['google_id']).first()
    
    if not user:
        # Create new user
        user = User(
            email=user_info['email'],
            name=user_info['name'],
            google_id=user_info['google_id'],
            picture=user_info.get('picture')
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ New user created: {user.email}")
    else:
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        print(f"✅ User logged in: {user.email}")
    
    return user
