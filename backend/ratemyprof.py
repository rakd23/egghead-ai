import requests
import json

class RateMyProfScraper:
    def __init__(self, school_id):
        self.school_id = school_id
        self.base_url = "https://www.ratemyprofessors.com/filter/professor"
    
    def SearchProfessor(self, professor_name):
        """Search for a professor by name"""
        # Split name into first and last
        name_parts = professor_name.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
        else:
            first_name = ""
            last_name = professor_name
        
        # Make request to RMP
        params = {
            'sid': self.school_id,
            'query': professor_name,
            'page': 1
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"RMP API returned status {response.status_code}")
                return None
            
            data = response.json()
            
            if not data or 'professors' not in data or not data['professors']:
                print("No professors found")
                return None
            
            # Get first result
            prof = data['professors'][0]
            
            return {
                'tFname': prof.get('tFname', ''),
                'tLname': prof.get('tLname', ''),
                'tDept': prof.get('tDept', 'N/A'),
                'tSid': str(self.school_id),
                'institution_name': 'UC Davis',
                'tid': prof.get('tid', ''),
                'tNumRatings': prof.get('tNumRatings', 0),
                'rating_class': prof.get('rating_class', 'N/A'),
                'overall_rating': prof.get('overall_rating', 'N/A')
            }
        
        except Exception as e:
            print(f"Error in RMP search: {e}")
            return None