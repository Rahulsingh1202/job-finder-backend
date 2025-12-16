from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import google.generativeai as genai
from google.oauth2 import id_token
from google.auth.transport import requests
import fitz  # PyMuPDF
import json
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time


# Import authentication
from auth import get_current_user


# Load environment variables
load_dotenv()


# Configure Gemini AI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    print("⚠️ Warning: GOOGLE_API_KEY not found. Resume parsing will fail.")


# Database setup
DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    phone = Column(String)
    linkedin = Column(String)
    profile_picture = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = relationship("Resume", back_populates="user")
    experiences = relationship("Experience", back_populates="user")
    saved_jobs = relationship("SavedJob", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    skills = Column(Text)
    education = Column(Text)
    phone = Column(String)
    linkedin = Column(String)
    github = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")


class Experience(Base):
    __tablename__ = "experiences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    duration = Column(String)
    description = Column(Text)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="experiences")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    link = Column(String, nullable=False)
    hr_email = Column(String)
    status = Column(String, default="pending")
    saved_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="saved_jobs")


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic Models
class GoogleToken(BaseModel):
    token: str


class JobSearch(BaseModel):
    skills: List[str]
    location: str = "India"
    experience_years: int = 0
    max_jobs: int = 50


class SavedJobCreate(BaseModel):
    title: str
    company: str
    location: str
    link: str
    hr_email: Optional[str] = None


class ExperienceItem(BaseModel):
    company: str
    role: str
    duration: str
    description: str


class ExperienceCreate(BaseModel):
    experiences: List[ExperienceItem]


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None


# FastAPI App
app = FastAPI(
    title="🍔 Job Finder API",
    description="AI-powered job search with resume parsing and Google OAuth",
    version="1.0.0"
)


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper Functions
def parse_resume_with_gemini(resume_text: str) -> dict:
    """Parse resume using Gemini AI"""
    try:
        model = genai.GenerativeModel('gemini-flash-latest')

        
        prompt = f"""
        Parse the following resume and extract information in JSON format:
        
        Resume Text:
        {resume_text}
        
        Please extract:
        1. Skills (as a list)
        2. Education
        3. Contact information (email, phone, LinkedIn, GitHub)
        4. Work experience (if any)
        
        Return ONLY valid JSON without any markdown formatting or code blocks.
        Format:
        {{
            "skills": ["skill1", "skill2"],
            "education": "education details",
            "contact": {{
                "email": "email",
                "phone": "phone",
                "linkedin": "linkedin_url",
                "github": "github_url"
            }},
            "experience": "experience summary"
        }}
        """
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Remove markdown code blocks - simple approach
        if "```json" in result_text:
            result_text = result_text.replace("```json", "")
        if "```" in result_text:
            result_text = result_text.replace("```", "")

        result_text = result_text.strip()
        parsed_data = json.loads(result_text)
        
        return parsed_data
        
    except Exception as e:
        print(f"Error parsing resume: {str(e)}")
        return {
            "skills": [],
            "education": "",
            "contact": {},
            "experience": ""
        }


def scrape_linkedin_jobs(skills: List[str], location: str, experience_years: int, max_jobs: int = 10) -> List[dict]:
    """Scrape LinkedIn jobs based on skills and experience"""
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    jobs = []
    
    try:
        # Determine experience level
        if experience_years == 0:
            experience_level = "Internship"
        elif experience_years <= 2:
            experience_level = "Entry level"
        elif experience_years <= 5:
            experience_level = "Associate"
        else:
            experience_level = "Mid-Senior level"
        
        # Build search query
        skills_query = " ".join(skills[:3])
        search_query = f"{skills_query} {experience_level}"
        encoded_query = search_query.replace(" ", "%20")
        encoded_location = location.replace(" ", "%20")
        
        url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}"
        
        print(f"Searching LinkedIn: {url}")
        driver.get(url)
        time.sleep(5)
        
        # Scroll to load more jobs
        for scroll_count in range(10):  # Changed variable name from i to scroll_count
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            print(f"Scroll {scroll_count + 1}/10 completed...")
        
        # Parse page
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_cards = soup.find_all('div', class_='base-card')
        
        print(f"Found {len(job_cards)} job cards on page")
        
        for card in job_cards[:max_jobs * 2]:
            try:
                title_elem = card.find('h3', class_='base-search-card__title')
                company_elem = card.find('h4', class_='base-search-card__subtitle')
                location_elem = card.find('span', class_='job-search-card__location')
                link_elem = card.find('a', class_='base-card__full-link')
                
                if title_elem and company_elem and link_elem:
                    job = {
                        "title": title_elem.text.strip(),
                        "company": company_elem.text.strip(),
                        "location": location_elem.text.strip() if location_elem else location,
                        "link": link_elem['href'],
                        "experience_level": experience_level
                    }
                    jobs.append(job)
                    
            except Exception as e:
                print(f"Error parsing job card: {str(e)}")
                continue
        
        print(f"Successfully parsed {len(jobs)} jobs")
        
    except Exception as e:
        print(f"Error scraping LinkedIn: {str(e)}")
        
    finally:
        driver.quit()
    
    # Return up to max_jobs
    return jobs[:max_jobs]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - Welcome message"""
    return {
        "message": "🍔 Job Finder API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "auth": "/auth/google/verify",
            "docs": "/docs",
            "upload_resume": "/upload-resume",
            "search_jobs": "/search-jobs",
            "saved_jobs": "/saved-jobs/me",
            "profile": "/user/me"
        }
    }


@app.post("/auth/google/verify")
async def verify_google_token(token_data: GoogleToken, db: Session = Depends(get_db)):
    """Verify Google OAuth token and create/login user"""
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token_data.token, 
            requests.Request(), 
            os.getenv("GOOGLE_CLIENT_ID")
        )
        
        # Extract user info
        email = idinfo['email']
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        google_id = idinfo['sub']
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                email=email,
                name=name,
                profile_picture=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True
        else:
            # Update existing user
            user.name = name
            user.profile_picture = picture
            db.commit()
            is_new_user = False
        
        return {
            "success": True,
            "is_new_user": is_new_user,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.profile_picture
            },
            "token": token_data.token
        }
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying token: {str(e)}")


@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse resume PDF (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Read PDF content
        pdf_content = await file.read()
        
        # Save temporarily
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(pdf_content)
        
        # Extract text from PDF
        doc = fitz.open(temp_path)
        resume_text = ""
        for page in doc:
            resume_text += page.get_text()
        doc.close()
        
        # Clean up temp file
        os.remove(temp_path)
        
        # Parse resume using Gemini
        parsed_data = parse_resume_with_gemini(resume_text)
        
        # Get or create user
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                email=user_email,
                name=current_user.get("name", ""),
                profile_picture=current_user.get("picture")
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Delete old resume if exists
        old_resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        if old_resume:
            db.delete(old_resume)
            db.commit()
        
        # Save new resume to database
        resume = Resume(
            user_id=user.id,
            skills=", ".join(parsed_data.get("skills", [])),
            education=parsed_data.get("education", ""),
            phone=parsed_data.get("contact", {}).get("phone", ""),
            linkedin=parsed_data.get("contact", {}).get("linkedin", ""),
            github=parsed_data.get("contact", {}).get("github", "")
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        
        return {
            "status": "success",
            "message": "Resume uploaded and parsed successfully",
            "data": {
                "user_email": user_email,
                "skills": parsed_data.get("skills", []),
                "education": parsed_data.get("education", ""),
                "contact": parsed_data.get("contact", {})
            }
        }
        
    except Exception as e:
        print(f"Error uploading resume: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing resume: {str(e)}")


@app.post("/search-jobs")
async def search_jobs(
    job_search: JobSearch,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for jobs on LinkedIn based on skills and experience (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please upload resume first.")
        
        jobs = scrape_linkedin_jobs(
            skills=job_search.skills,
            location=job_search.location,
            experience_years=job_search.experience_years,
            max_jobs=job_search.max_jobs
        )
        
        # Separate jobs by type
        jobs_with_email = []
        jobs_without_email = []
        
        for job in jobs:
            if job.get('hr_email'):
                jobs_with_email.append(job)
            else:
                jobs_without_email.append(job)
        
        return {
            "status": "success",
            "user_email": user_email,
            "total_jobs": len(jobs),
            "data": {
                "jobs_with_email": jobs_with_email,
                "jobs_without_email": jobs_without_email,
                "direct_contact_jobs": jobs_with_email,  # Alias for frontend
                "standard_jobs": jobs_without_email  # Alias for frontend
            }
        }
        
    except Exception as e:
        print(f"Error searching jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching jobs: {str(e)}")


@app.post("/save-job")
async def save_job(
    job: SavedJobCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a job for later (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if job already saved
        existing = db.query(SavedJob).filter(
            SavedJob.user_id == user.id,
            SavedJob.link == job.link
        ).first()
        
        if existing:
            return {
                "status": "info",
                "message": "Job already saved",
                "job_id": existing.id
            }
        
        # Save new job
        saved_job = SavedJob(
            user_id=user.id,
            title=job.title,
            company=job.company,
            location=job.location,
            link=job.link,
            hr_email=job.hr_email,
            status="pending"
        )
        db.add(saved_job)
        db.commit()
        db.refresh(saved_job)
        
        return {
            "status": "success",
            "message": "Job saved successfully",
            "job_id": saved_job.id,
            "job": {
                "title": saved_job.title,
                "company": saved_job.company,
                "location": saved_job.location
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving job: {str(e)}")


@app.get("/saved-jobs/me")
async def get_saved_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all saved jobs for current user (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user.id).all()
        
        return {
            "status": "success",
            "user_email": user_email,
            "total_saved": len(saved_jobs),
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "url": job.link,
                    "hr_email": job.hr_email,
                    "status": job.status or "pending",
                    "created_at": job.saved_at
                }
                for job in saved_jobs
            ]
        }
        
    except Exception as e:
        print(f"Error fetching saved jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching saved jobs: {str(e)}")


@app.delete("/saved-jobs/{job_id}")
async def delete_saved_job(
    job_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved job (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Find the job and verify ownership
        job = db.query(SavedJob).filter(
            SavedJob.id == job_id,
            SavedJob.user_id == user.id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or unauthorized")
        
        db.delete(job)
        db.commit()
        
        return {"message": "Job deleted successfully", "job_id": job_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")


@app.post("/add-experience")
async def add_experience(
    exp_data: ExperienceCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add work experience for user (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        added_experiences = []
        for exp in exp_data.experiences:
            experience = Experience(
                user_id=user.id,
                company=exp.company,
                role=exp.role,
                duration=exp.duration,
                description=exp.description
            )
            db.add(experience)
            added_experiences.append({
                "company": exp.company,
                "role": exp.role,
                "duration": exp.duration
            })
        
        db.commit()
        
        return {
            "message": f"Added {len(added_experiences)} experience(s) successfully",
            "user_email": user_email,
            "experiences": added_experiences
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding experience: {str(e)}")


@app.get("/user/me")
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete user profile with resume and experience (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get resume
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        
        # Get experiences
        experiences = db.query(Experience).filter(Experience.user_id == user.id).all()
        
        return {
            "user": {
                "email": user.email,
                "name": user.name,
                "profile_picture": user.profile_picture,
                "created_at": user.created_at
            },
            "resume": {
                "skills": resume.skills if resume else None,
                "education": resume.education if resume else None,
                "phone": resume.phone if resume else None,
                "linkedin": resume.linkedin if resume else None,
                "github": resume.github if resume else None
            } if resume else None,
            "experiences": [
                {
                    "id": exp.id,
                    "company": exp.company,
                    "role": exp.role,
                    "duration": exp.duration,
                    "description": exp.description
                }
                for exp in experiences
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching profile: {str(e)}")


@app.put("/user/me")
async def update_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (AUTHENTICATED)"""
    
    user_email = current_user["email"]
    
    try:
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields if provided
        if user_update.name:
            user.name = user_update.name
        if user_update.phone:
            user.phone = user_update.phone
        if user_update.linkedin:
            user.linkedin = user_update.linkedin
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User updated successfully",
            "user": {
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "linkedin": user.linkedin
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user: {str(e)}")


@app.get("/test-login", response_class=HTMLResponse)
def test_login_page():
    """Test page for Google OAuth login"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Google Login</title>
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            #result {
                margin-top: 30px;
                padding: 20px;
                background: #f0f8ff;
                border-radius: 5px;
            }
            .token {
                font-family: monospace;
                font-size: 12px;
                word-break: break-all;
                background: #eee;
                padding: 10px;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🍔 Test Google Login</h1>
            <p>Click below to sign in with Google</p>
            
            <div id="g_id_onload"
                 data-client_id="663577035472-7fbhku5mq37dpec2p7oo6h354oh4c1k5.apps.googleusercontent.com"
                 data-callback="handleCredentialResponse">
            </div>
            
            <div class="g_id_signin" data-type="standard"></div>
            
            <div id="result"></div>
        </div>

        <script>
            function handleCredentialResponse(response) {
                const token = response.credential;
                console.log("Token received:", token);
                
                localStorage.setItem('google_token', token);
                
                document.getElementById('result').innerHTML = `
                    <h3 style="color: green;">✅ Login Successful!</h3>
                    <p><strong>Token saved to localStorage and console!</strong></p>
                    <div class="token">${token.substring(0, 50)}...</div>
                    <p style="margin-top: 20px;">
                        <strong>Next Steps:</strong><br>
                        1. Copy the full token from console (F12)<br>
                        2. Go to <a href="/docs" target="_blank">/docs</a><br>
                        3. Click "Authorize" button<br>
                        4. Enter: Bearer YOUR_TOKEN<br>
                        5. Test any endpoint!
                    </p>
                `;
            }
        </script>
    </body>
    </html>
    """


@app.get("/stats/dashboard/{user_email}")
async def get_dashboard_stats(user_email: str, db: Session = Depends(get_db)):
    """Get dashboard statistics for a user"""
    try:
        # Find user first
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return {
                "status": "success",
                "data": {
                    "totalApplications": 0,
                    "ended": 0,
                    "running": 0,
                    "pending": 0
                }
            }
        
        # Get all saved jobs for the user
        saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user.id).all()
        
        # Calculate stats
        total = len(saved_jobs)
        ended = len([j for j in saved_jobs if j.status in ['rejected', 'accepted']])
        running = len([j for j in saved_jobs if j.status in ['applied', 'interviewing']])
        pending = len([j for j in saved_jobs if j.status in ['pending', None]])
        
        return {
            "status": "success",
            "data": {
                "totalApplications": total,
                "ended": ended,
                "running": running,
                "pending": pending
            }
        }
    except Exception as e:
        print(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/resume/{user_email}")
async def get_resume(user_email: str, db: Session = Depends(get_db)):
    """Get resume data for a user"""
    try:
        # First find the user
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Then find their resume
        resume = db.query(Resume).filter(Resume.user_id == user.id).first()
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return {
            "status": "success",
            "data": {
                "name": user.name,
                "email": user.email,
                "phone": resume.phone or user.phone,
                "skills": resume.skills.split(', ') if resume.skills else [],
                "education": resume.education,
                "linkedin": resume.linkedin,
                "github": resume.github,
                "uploaded_at": resume.uploaded_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching resume: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Get all resumes for a user
# Get all resumes for a user
@app.get("/api/resumes")
async def get_user_resumes(db: Session = Depends(get_db)):  # Add this
    """Get all uploaded resumes"""
    try:
        resumes = db.query(Resume).all()
        
        resume_list = []
        for resume in resumes:
            # Get user info for each resume
            user = db.query(User).filter(User.id == resume.user_id).first()
            
            resume_list.append({
                "id": resume.id,
                "filename": user.name if user else "Unknown",  # Use user name as filename
                "uploaded_at": resume.uploaded_at.isoformat() if resume.uploaded_at else None,
                "skills": resume.skills.split(', ') if resume.skills else [],
                "education": resume.education,
                "contact": {
                    "phone": resume.phone,
                    "linkedin": resume.linkedin,
                    "github": resume.github
                },
                "experience": ""  # You don't have this field
            })
        
        return {"resumes": resume_list}
    
    except Exception as e:
        print(f"Error in get_user_resumes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
