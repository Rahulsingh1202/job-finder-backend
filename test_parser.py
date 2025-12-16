import pdfplumber
import re
import nltk

# Download required NLTK data (only runs once)
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
except:
    pass

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()
    return text

def extract_email(text):
    """Extract email from text"""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else None

def extract_phone(text):
    """Extract phone number from text"""
    # Pattern for Indian phone numbers
    phone_patterns = [
        r'\+91[-\s]?\d{10}',  # +91 with 10 digits
        r'\+91\d{10}',         # +91 without space
        r'\d{10}',             # Just 10 digits
        r'\d{5}\s?\d{5}',      # 5 digits space 5 digits
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            # Clean up the phone number
            phone = phones[0].replace(' ', '').replace('-', '')
            return phone
    
    return None


def extract_skills(text):
    """Extract skills from text"""
    # Common tech skills to look for
    skill_keywords = [
        'python', 'javascript', 'java', 'react', 'node', 'fastapi', 
        'flask', 'django', 'html', 'css', 'sql', 'mysql', 'mongodb',
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',
        'langchain', 'llm', 'nlp', 'machine learning', 'deep learning',
        'ai', 'artificial intelligence', 'git', 'github', 'docker',
        'aws', 'azure', 'gcp', 'api', 'rest', 'graphql',
        'typescript', 'angular', 'vue', 'express', 'bootstrap',
        'tailwind', 'redux', 'nextjs', 'nestjs', 'spring boot',
        'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'rust',
        'opencv', 'keras', 'spark', 'hadoop', 'kafka', 'redis',
        'faiss', 'hugging face', 'rag', 'semantic search'
    ]
    
    text_lower = text.lower()
    found_skills = []
    
    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill.title())
    
    # Remove duplicates and return
    return list(set(found_skills))

def extract_name(text):
    """Extract name from first line"""
    lines = text.split('\n')
    # Name is usually in first few lines
    for line in lines[:5]:
        line = line.strip()
        if line and len(line.split()) <= 4 and not '@' in line:
            return line
    return None

def parse_resume(pdf_path):
    """Main function to parse resume"""
    print(f"\n{'='*50}")
    print("Testing Resume Parser with Rahul's Resume")
    print(f"{'='*50}\n")
    
    try:
        print(f"📄 Parsing resume: {pdf_path}")
        print("⏳ Please wait...\n")
        
        # Extract text from PDF
        text = extract_text_from_pdf(pdf_path)
        
        # Extract information
        name = extract_name(text)
        email = extract_email(text)
        phone = extract_phone(text)
        skills = extract_skills(text)
        
        print("✅ Resume parsed successfully!\n")
        
        # Display results
        print(f"👤 Name: {name}")
        print(f"📧 Email: {email}")
        print(f"📱 Phone: {phone}")
        
        print(f"\n💼 Skills Found ({len(skills)}):")
        if skills:
            for i, skill in enumerate(skills, 1):
                print(f"  {i}. {skill}")
        else:
            print("  No skills extracted")
        
        print(f"\n{'='*50}")
        print("✅ Test completed successfully!")
        print(f"{'='*50}\n")
        
        # Return structured data
        return {
            'name': name,
            'email': email,
            'phone': phone,
            'skills': skills,
            'raw_text': text
        }
        
    except FileNotFoundError:
        print("❌ Error: Resume file not found!")
        print("Make sure 'RahulSinghResume.pdf' is in the same folder.")
        return None
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = parse_resume('RahulSinghResume.pdf')
    
    if result:
        print("\n📊 Summary:")
        print(f"  • Name extracted: {'✅' if result['name'] else '❌'}")
        print(f"  • Email extracted: {'✅' if result['email'] else '❌'}")
        print(f"  • Phone extracted: {'✅' if result['phone'] else '❌'}")
        print(f"  • Skills extracted: {len(result['skills'])} skills")
