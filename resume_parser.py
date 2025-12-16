import pdfplumber
import re
import nltk

# Download required NLTK data
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
    phone_patterns = [
        r'\+91[-\s]?\d{10}',
        r'\+91\d{10}',
        r'\d{10}',
        r'\d{5}\s?\d{5}',
    ]
    
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            phone = phones[0].replace(' ', '').replace('-', '')
            return phone
    
    return None

def extract_skills(text):
    """Extract skills from text"""
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
    
    return list(set(found_skills))

def extract_name(text):
    """Extract name from first line"""
    lines = text.split('\n')
    for line in lines[:5]:
        line = line.strip()
        if line and len(line.split()) <= 4 and not '@' in line:
            return line
    return None

def parse_resume(pdf_path):
    """Main function to parse resume"""
    try:
        text = extract_text_from_pdf(pdf_path)
        
        return {
            'name': extract_name(text),
            'email': extract_email(text),
            'phone': extract_phone(text),
            'skills': extract_skills(text),
            'raw_text': text
        }
    except Exception as e:
        raise Exception(f"Error parsing resume: {str(e)}")
