from linkedin_scraper import scrape_linkedin_jobs, categorize_jobs

def test_scraping():
    # Test with some skills
    skills = ["Python", "FastAPI", "React"]
    
    print("="*60)
    print("Testing LinkedIn Job Scraper")
    print("="*60)
    
    # Scrape jobs
    jobs = scrape_linkedin_jobs(skills, location="India", max_jobs=10)
    
    if jobs:
        print("\n" + "="*60)
        print("Job Details:")
        print("="*60 + "\n")
        
        for job in jobs[:5]:  # Show first 5
            print(f"Title: {job['title']}")
            print(f"Company: {job['company']}")
            print(f"Location: {job['location']}")
            print(f"Link: {job['link']}")
            print("-" * 60)
        
        # Categorize jobs
        categorized = categorize_jobs(jobs)
        print(f"\n📊 Summary:")
        print(f"Total jobs: {categorized['total_jobs']}")
        print(f"Jobs with email: {categorized['jobs_with_email']}")
        print(f"Jobs without email: {categorized['jobs_without_email']}")
    else:
        print("❌ No jobs found")

if __name__ == "__main__":
    test_scraping()
