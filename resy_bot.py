import os
import json
import requests
import datetime
import pytz
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

class ResyBot:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('RESY_API_KEY')
        self.auth_token = os.getenv('RESY_AUTH_TOKEN')
        
        # Validate credentials are loaded
        if not self.api_key or not self.auth_token:
            print("Error: Missing API credentials in .env file")
            raise ValueError("Missing API credentials")
            
        self.base_url = 'https://api.resy.com/3'
        self.headers = {
            'authorization': f'ResyAPI api_key="{self.api_key}"',
            'x-resy-universal-auth': self.auth_token,
            'accept': 'application/json',
            'content-type': 'application/json',
            'origin': 'https://resy.com',
            'referer': 'https://resy.com/'
        }
        
        # Initialize Playwright
        self.playwright = sync_playwright().start()
        
        # Create user data directory if it doesn't exist
        user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_data')
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Launch browser with persistent context
        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        # Use persistent context to maintain login state
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            storage_state="auth.json" if os.path.exists("auth.json") else None
        )
        
        self.page = self.context.new_page()
        
        # Check if we need to log in
        if not os.path.exists("auth.json"):
            self.login()
        
        # Default settings
        self.default_party_size = int(os.getenv('DEFAULT_PARTY_SIZE', 2))
        self.default_dining_time = os.getenv('DEFAULT_DINING_TIME', '19:00')
        
        print("\nAPI Configuration:")
        print(f"API Key: {self.api_key[:10]}..." if self.api_key else "API Key: Not found")
        print(f"Auth Token: {self.auth_token[:10]}..." if self.auth_token else "Auth Token: Not found")
        print("\nPlaywright browser initialized")

    def __del__(self):
        """Clean up browser when done."""
        try:
            if hasattr(self, 'context'):
                self.context.close()
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except:
            pass

    def test_api_connection(self):
        """Test the API connection and credentials."""
        print("\n=== Testing API Connection ===")
        url = f"{self.base_url}/venues/search"  # Changed to a more reliable endpoint
        params = {
            'lat': '28.538300',
            'lng': '-81.379200',
            'day': datetime.datetime.now().strftime('%Y-%m-%d'),
            'party_size': '2'
        }
        
        try:
            # Use allow_redirects=False to prevent redirect loops
            response = requests.get(url, headers=self.headers, params=params, allow_redirects=False)
            print(f"Test request status code: {response.status_code}")
            
            if response.status_code in [401, 403]:
                print("Authentication failed. Please check your API credentials.")
                print("\nDebug Info:")
                print(f"API Key (first 10 chars): {self.api_key[:10]}...")
                print(f"Auth Token (first 10 chars): {self.auth_token[:10]}...")
                print("\nFull response:")
                print(response.text)
                raise ValueError("API Authentication failed")
            elif response.status_code == 302:
                print("Warning: Redirect detected. This is unexpected but may not be an issue.")
            elif response.status_code != 200:
                print(f"Warning: Unexpected status code {response.status_code}")
                print("Response:", response.text[:500])
                
        except requests.exceptions.RequestException as e:
            print(f"Error testing API connection: {e}")
            print("This error is not fatal, continuing with initialization...")

    def get_valid_date_input(self):
        """Prompt for and validate a date input."""
        while True:
            date_str = input("Enter desired reservation date (YYYY-MM-DD): ")
            try:
                # Parse the date to validate format
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                
                # Check if date is in the past
                if date.date() < datetime.datetime.now().date():
                    print("Error: Date cannot be in the past")
                    continue
                
                return date_str
            except ValueError:
                print("Error: Invalid date format. Please use YYYY-MM-DD")

    def search_venues(self, query, lat='28.538300', lng='-81.379200'):  # Orlando coordinates as strings
        """Search for restaurants by name."""
        url = f"{self.base_url}/venues/search"
        
        # Format date as required by Resy API
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Clean up the query - remove URL parts if present
        if 'resy.com' in query:
            parts = query.strip('/').split('/')
            query = parts[-1]  # Get just the restaurant name part
            # Handle /venues/ in path
            if 'venues' in parts:
                venue_index = parts.index('venues')
                if venue_index + 1 < len(parts):
                    query = parts[venue_index + 1]
        
        params = {
            'query': query,
            'lat': lat,
            'lng': lng,
            'day': today,
            'party_size': str(self.default_party_size),  # Convert to string
            'limit': '25',  # Convert to string
            'location': 'orlando-fl',
            'radius': '20'  # Convert to string
        }
        
        print("\n=== API Request Details ===")
        print(f"URL: {url}")
        print("Headers:")
        for key, value in self.headers.items():
            # Truncate long values for readability
            print(f"{key}: {value[:50]}..." if len(str(value)) > 50 else f"{key}: {value}")
        print("\nParameters:")
        print(json.dumps(params, indent=2))
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            print("\n=== API Response Details ===")
            print(f"Status Code: {response.status_code}")
            print("Response Headers:")
            print(json.dumps(dict(response.headers), indent=2))
            print("\nResponse Body:")
            try:
                print(json.dumps(response.json(), indent=2))
            except:
                print(response.text)
            
            if response.status_code == 200:
                data = response.json()
                if 'venues' in data and len(data['venues']) > 0:
                    print(f"\nFound {len(data['venues'])} venues:")
                    for venue in data['venues']:
                        print(f"- {venue['name']} ({venue['location'].get('neighborhood', 'Unknown area')})")
                return data
            else:
                print(f"\nRequest failed with status code: {response.status_code}")
                if response.status_code == 404:
                    print("Tip: The restaurant might be listed under a different name or location.")
                    print("Try using the exact name from the Resy website.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"\nNetwork error: {str(e)}")
            if 'response' in locals():
                print(f"Full URL called: {response.url}")
            return None

    def find_reservation(self, url, party_size=None, date=None):
        """Find available reservations for a specific venue using Playwright."""
        if not party_size:
            party_size = self.default_party_size
        
        if not date:
            date = self.get_valid_date_input()
            
        # Convert date to Eastern Time
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
        eastern = pytz.timezone('America/New_York')
        date_et = eastern.localize(date_obj)
        
        print(f"\nSearching for reservations at: {url}")
        print(f"Date (ET): {date_et.strftime('%Y-%m-%d')}")
        print(f"Party size: {party_size}")
        
        try:
            # Navigate to the page and wait for it to load
            self.page.goto(url)
            
            # Wait for time slots to appear
            print("Waiting for time slots to load...")
            self.page.wait_for_selector('button.ReservationButton', timeout=10000)
            
            # Get all time slots
            time_slots = self.page.query_selector_all('button.ReservationButton')
            
            if time_slots:
                print(f"\nFound {len(time_slots)} available slots:")
                for slot in time_slots:
                    # Get time text from the nested div
                    time_text = slot.query_selector('.ReservationButton__time').inner_text()
                    print(f"- {time_text}")
                    
                    # Print button ID for debugging
                    button_id = slot.get_attribute('id')
                    if button_id:
                        print(f"  Button ID: {button_id}")
                    
                    # Ask user if they want to book this time slot
                    choice = input(f"\nWould you like to book the {time_text} slot? (y/n): ")
                    if choice.lower() == 'y':
                        print(f"\nAttempting to book {time_text} slot...")
                        
                        # Click the time slot and wait for popup
                        slot.click()
                        print("Clicked time slot, waiting for reservation popup...")
                        
                        try:
                            # Wait for the iframe to appear
                            print("Waiting for reservation iframe...")
                            self.page.wait_for_selector('iframe[title="Resy - Book Now"]', timeout=10000)
                            print("Found iframe, switching context...")
                            
                            # Get the frame locator
                            frame = self.page.frame_locator('iframe[title="Resy - Book Now"]')
                            
                            # Wait for the popup title to appear in the iframe
                            print("Looking for reservation details in iframe...")
                            frame.locator('div.WidgetTitle h1:has-text("Complete Your Reservation")').wait_for(timeout=10000)
                            print("Found reservation popup in iframe")
                            
                            # Wait for and click the first Reserve Now button within the iframe
                            reserve_button = frame.locator('button[data-test-id="order_summary_page-button-book"]')
                            reserve_button.wait_for(state="visible", timeout=10000)
                            print("Found Reserve Now button in iframe, clicking...")
                            reserve_button.click()
                            
                            # Wait for and click the second Reserve Now button (Confirm) within the iframe
                            print("Waiting for second Reserve Now button in iframe...")
                            self.page.wait_for_timeout(2000)  # Wait for animation
                            
                            confirm_button = frame.locator('button[data-test-id="order_summary_page-button-book"]')
                            confirm_button.wait_for(state="visible", timeout=10000)
                            print("Found Confirm button in iframe, clicking...")
                            confirm_button.click()
                            
                            # Wait for the booking form within the iframe
                            frame.locator('form.BookingForm, div.BookingConfirmation').wait_for(timeout=10000)
                            print("\nReservation page loaded. Please complete your booking in the browser.")
                            return True
                            
                        except PlaywrightTimeoutError:
                            print("\nTimeout waiting for reservation elements. Please try again.")
                            return False
                        except Exception as e:
                            print(f"\nError during reservation: {str(e)}")
                            return False
                
                return True
            else:
                print("\nNo available slots found for this date")
                return None
                
        except PlaywrightTimeoutError:
            print("\nTimeout waiting for page elements")
            print("This could mean the page is not loading or the restaurant is not accepting reservations")
            return None
        except Exception as e:
            print(f"\nError finding reservations: {str(e)}")
            return None

    def make_reservation(self, config_id, party_size=None, date=None):
        """Attempt to make a reservation."""
        if not party_size:
            party_size = self.default_party_size
            
        url = f"{self.base_url}/reservation"
        data = {
            'config_id': config_id,
            'party_size': party_size,
            'date': date,
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        if response.status_code == 201:
            return response.json()
        else:
            print(f"Error making reservation: {response.status_code}")
            return None

    def book_specific_restaurant(self, venue_id, party_size=None, date=None):
        """Complete flow to book a specific restaurant."""
        try:
            # First get the venue details to get the slug
            venue_url = f"{self.base_url}/venue"
            params = {
                'id': venue_id,
                'location': 'orlando-fl'
            }
            
            response = requests.get(venue_url, headers=self.headers, params=params)
            if response.status_code == 200:
                venue_data = response.json()
                venue_slug = venue_data.get('url_slug', 'edoboy')  # Use the slug from venue data
            else:
                venue_slug = 'edoboy'  # Fallback to known slug
            
            # Convert date to Eastern Time since Resy uses ET
            date_obj = datetime.datetime.strptime(date, '%Y-%m-%d')
            eastern = pytz.timezone('America/New_York')
            date_et = eastern.localize(date_obj)
            formatted_date = date_et.strftime('%Y-%m-%d')
            
            # Construct URL with venue slug instead of ID
            url = f"https://resy.com/cities/orlando-fl/venues/{venue_slug}?date={formatted_date}"
            if party_size:
                url += f"&seats={party_size}"
            
            print(f"\nOpening URL: {url}")
            
            # Find available reservations using the full URL
            availability = self.find_reservation(url, party_size, date)
            if not availability:
                print("No available reservations found")
                return False

            return True
            
        except Exception as e:
            print(f"Error during booking process: {str(e)}")
            return False

    def extract_venue_id_from_url(self, url):
        """Extract venue ID from a Resy URL."""
        try:
            # Handle URLs like https://resy.com/cities/orlando-fl/venues/edoboy
            parts = url.strip('/').split('/')
            
            # Get venue name from the last part
            venue_name = parts[-1]
            
            # Try direct venue lookup first
            venue_url = f"{self.base_url}/venue"
            params = {
                'url_slug': venue_name,
                'location': 'orlando-fl'
            }
            
            print("\n=== Venue Lookup Details ===")
            print(f"URL: {venue_url}")
            print(f"Params: {json.dumps(params, indent=2)}")
            
            response = requests.get(venue_url, headers=self.headers, params=params)
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                venue_data = response.json()
                if 'id' in venue_data:
                    # Extract just the Resy ID number
                    resy_id = venue_data['id'].get('resy')
                    if resy_id:
                        print(f"\nFound venue:")
                        print(f"Name: {venue_data.get('name', venue_name)}")
                        print(f"Resy ID: {resy_id}")
                        print(f"Location: {venue_data.get('location', {}).get('neighborhood', 'Unknown')}")
                        return resy_id
                    else:
                        print("\nError: Could not find Resy ID in venue data")
                else:
                    print("\nError: Venue data missing ID")
                print("Response data:")
                print(json.dumps(venue_data, indent=2))
            else:
                print(f"\nVenue lookup failed with status {response.status_code}")
                print("Response:")
                print(response.text)
            
            # If direct lookup fails, try search
            print("\nTrying search fallback...")
            search_results = self.search_venues(venue_name)
            if search_results and 'venues' in search_results:
                for venue in search_results['venues']:
                    if venue.get('url_slug') == venue_name or venue.get('name', '').lower() == venue_name.lower():
                        resy_id = venue.get('id', {}).get('resy')
                        if resy_id:
                            print(f"\nFound via search:")
                            print(f"Name: {venue['name']}")
                            print(f"Resy ID: {resy_id}")
                            print(f"Location: {venue.get('location', {}).get('neighborhood', 'Unknown')}")
                            return resy_id
            
            print("\nCould not find venue. Debug info:")
            print(f"URL parts: {parts}")
            print(f"Venue name extracted: {venue_name}")
            return None
            
        except Exception as e:
            print(f"Error extracting venue ID: {e}")
            print(f"Full URL being processed: {url}")
            return None

    def get_venue_input(self):
        """Get venue information from user input."""
        choice = input("\nEnter Resy URL: ").strip()
        
        if 'resy.com' in choice.lower():
            venue_id = self.extract_venue_id_from_url(choice)
            if venue_id:
                return {'id': venue_id}
        
        # If not a URL or URL lookup failed, search by name
        return self.search_venues(choice)

    def login(self):
        """Log into Resy and save authentication state."""
        print("\nNo saved login state found. Please log in to Resy...")
        
        # Navigate to Resy login page
        self.page.goto("https://resy.com/login")
        
        # Wait for user to complete login manually
        print("\nPlease log in to your Resy account in the browser.")
        print("Once logged in, the session will be saved for future use.")
        
        # Wait for successful login (redirect to home page or presence of user menu)
        self.page.wait_for_selector('div[data-test-id="user-menu"]', timeout=300000)  # 5 minute timeout
        
        # Save authentication state
        self.context.storage_state(path="auth.json")
        print("\nLogin successful! Authentication state saved for future sessions.")

def main():
    bot = None
    try:
        bot = ResyBot()
        
        # Get inputs
        venue_info = bot.get_venue_input()
        if not venue_info:
            print("Restaurant not found. Please check the URL and try again.")
            return
            
        date = bot.get_valid_date_input()
        
        if 'id' in venue_info:  # Direct venue ID from URL
            venue_id = venue_info['id']
        elif 'venues' in venue_info and venue_info['venues']:
            venue = venue_info['venues'][0]
            venue_id = venue['id']
        else:
            print("Restaurant not found")
            return
            
        # Try to book
        bot.book_specific_restaurant(venue_id, date=date)
        
        # Keep the browser window open until user is done
        input("\nPress Enter to close the browser window...")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if bot:
            try:
                bot.browser.close()
                bot.playwright.stop()
            except:
                pass  # Ignore errors during cleanup

if __name__ == "__main__":
    main() 