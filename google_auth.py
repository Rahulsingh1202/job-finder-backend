from google.oauth2 import id_token
from google.auth.transport import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')

def verify_google_token(token: str):
    """
    Verify Google OAuth token and return user info
    
    Args:
        token: Google ID token from frontend
        
    Returns:
        User info dict with email, name, picture
    """
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Token is valid, extract user info
        user_info = {
            "email": idinfo.get('email'),
            "name": idinfo.get('name'),
            "picture": idinfo.get('picture'),
            "google_id": idinfo.get('sub'),
            "email_verified": idinfo.get('email_verified', False)
        }
        
        return user_info
        
    except ValueError as e:
        # Token is invalid
        raise Exception(f"Invalid token: {str(e)}")
    except Exception as e:
        raise Exception(f"Error verifying token: {str(e)}")

def get_google_client_id():
    """Return Google Client ID for frontend"""
    return GOOGLE_CLIENT_ID
