from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re



def get_experience_level(years):
    """Get experience level description"""
    if years is None:
        return "All Levels"
    elif years <= 2:
        return "Entry Level (0-2 years)"
    elif years <= 5:
        return "Mid Level (2-5 years)"
    else:
        return "Senior Level (5+ years)"


def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_email_from_text(text):
    """Extract email addresses from text"""
    if not text:
        return []
    
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    # Filter out common generic emails
    filtered_emails = [email for email in emails if not any(
        x in email.lower() for x in ['noreply', 'no-reply', 'donotreply']
    )]
    return filtered_emails

def scrape_linkedin_jobs(skills, location="India", max_jobs=20, experience_years=None):
    """
    Scrape LinkedIn jobs based on skills and experience level
    
    Args:
        skills: List of skills to search for
        location: Job location (default: India)
        max_jobs: Maximum number of jobs to scrape
        experience_years: Years of experience (0-2: Entry, 2-5: Mid, 5+: Senior)
    
    Returns:
        List of job dictionaries
    """
    print(f"\n🔍 Starting LinkedIn job search...")
    print(f"Skills: {', '.join(skills[:5])}...")
    print(f"Location: {location}")
    print(f"Experience Level: {get_experience_level(experience_years)}")
    print(f"Max jobs: {max_jobs}\n")
    
    driver = None
    
    try:
        # Setup driver
        driver = setup_driver()
        
        # Create search query from skills
        keywords = "+".join(skills[:3])  # Use top 3 skills
        
        # Build URL with experience filter
        url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location}"
        
        # Add experience level filter to URL
        # Add experience level filter to URL
        if experience_years is not None:
            if experience_years == 0:
                # Fresher - Internship only
                url += "&f_E=1"
            elif experience_years <= 2:
                # Entry level & Internship
                url += "&f_E=1,2"
            elif experience_years <= 5:
                # Associate & Mid-Senior level
                url += "&f_E=3,4"
            else:
                # Director and above
                url += "&f_E=5,6"

        
        print(f"📡 Accessing LinkedIn: {url}")
        driver.get(url)
        time.sleep(3)  # Wait for page to load
        
        jobs = []
        job_cards = driver.find_elements(By.CLASS_NAME, "base-card")
        
        print(f"✅ Found {len(job_cards)} job listings\n")
        
        for idx, card in enumerate(job_cards[:max_jobs], 1):
            try:
                # Extract job title
                title_elem = card.find_element(By.CLASS_NAME, "base-search-card__title")
                title = title_elem.text.strip()
                
                # Extract company name
                company_elem = card.find_element(By.CLASS_NAME, "base-search-card__subtitle")
                company = company_elem.text.strip()
                
                # Extract location
                location_elem = card.find_element(By.CLASS_NAME, "job-search-card__location")
                job_location = location_elem.text.strip()
                
                # Extract job link
                link_elem = card.find_element(By.TAG_NAME, "a")
                job_link = link_elem.get_attribute("href")
                
                job_data = {
                    "id": idx,
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "link": job_link,
                    "hr_email": None  # Will be populated if found
                }
                
                jobs.append(job_data)
                print(f"✅ {idx}. {title} at {company}")
                
            except Exception as e:
                print(f"⚠️  Skipped job {idx}: {str(e)}")
                continue
        
        print(f"\n🎉 Successfully scraped {len(jobs)} jobs!\n")
        return jobs
        
    except Exception as e:
        print(f"❌ Error during scraping: {str(e)}")
        return []
        
    finally:
        if driver:
            driver.quit()

def get_experience_level(years):
    """Get experience level description"""
    if years is None:
        return "All Levels"
    elif years == 0:
        return "Fresher/Internship (0 years)"
    elif years <= 2:
        return "Entry Level (0-2 years)"
    elif years <= 5:
        return "Mid Level (2-5 years)"
    else:
        return "Senior Level (5+ years)"



def categorize_jobs(jobs):
    """
    Categorize jobs into:
    1. Jobs with HR email
    2. Jobs with apply link only
    """
    jobs_with_email = []
    jobs_with_link_only = []
    
    for job in jobs:
        if job.get('hr_email'):
            jobs_with_email.append(job)
        else:
            jobs_with_link_only.append(job)
    
    return {
        "direct_contact_jobs": jobs_with_email,
        "standard_jobs": jobs_with_link_only,
        "total_jobs": len(jobs),
        "jobs_with_email": len(jobs_with_email),
        "jobs_without_email": len(jobs_with_link_only)
    }
