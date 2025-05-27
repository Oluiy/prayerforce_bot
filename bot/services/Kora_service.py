# import os
# import json
# import uuid
# import requests
# from datetime import datetime
# from dotenv import load_dotenv

# load_dotenv()

# class KoraPayService:
#     def __init__(self):
#         self.base_url = os.getenv("KORA_BASE_URL", "https://api.korapay.com/merchant/api/v1")
#         self.public_key = os.getenv("KORA_PUBLIC_KEY")
#         self.secret_key = os.getenv("KORA_SECRET_KEY")
        
#         if not self.public_key or not self.secret_key:
#             print("WARNING: KoraPay credentials not found in environment variables")
#             # Using dummy values for testing only

#     def generate_payment_link(self, amount, name, email, description):
#         endpoint = f"{self.base_url}/charges/initialize"
#         reference = f"PF-{uuid.uuid4().hex[:8]}"

#         # if self.public_key.startswith("pk_test"):
#         #     print(f"TEST MODE: Generated dummy payment link for {email}, amount: {amount}")
#         #     return f"https://checkout.korapay.com/test/{reference}", reference
        
#         payload = {
#             "amount": str(amount),
#             "currency": "NGN",
#             "reference": reference,
#             "notification_url": "https://your-webhook-url.com/kora-webhook",
#             "merchant_bears_cost": True,
#             "customer": {
#                 "name": name,
#                 "email": email
#             },
#             "description": description,
#             "redirect_url": "https://t.me/@Tefillah_PF_bot",  # Redirect back to your bot
#         }
        
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {self.secret_key}"
#         }
        
#         try:
#             print(f"Sending request to KoraPay API: {endpoint}")
#             print(f"Payload: {payload}")
            
#             response = requests.post(endpoint, headers=headers, json=payload)
#             print(f"KoraPay API response status: {response.status_code}")
            
#             response.raise_for_status()
#             data = response.json()
#             print(f"KoraPay API response: {data}")
            
#             if data.get("status"):
#                 checkout_url = data.get("data", {}).get("checkout_url")
#                 return checkout_url, reference
            
#             print(f"KoraPay API error: {data}")
#             return None, None
            
#         except Exception as e:
#             print(f"Error generating KoraPay link: {e}")
#             return None, None
            
#     def verify_payment(self, reference):
#         endpoint = f"{self.base_url}/charges/verify/{reference}"
        
#         headers = {
#             "Authorization": f"Bearer {self.secret_key}"
#         }
        
#         try:
#             response = requests.get(endpoint, headers=headers)
#             response.raise_for_status()
#             data = response.json()
            
#             if data.get("status") and data.get("data", {}).get("status") == "success":
#                 return True
                
#             return False
            
#         except Exception as e:
#             print(f"Error verifying payment: {e}")
#             return False


import os
import json
import uuid
import traceback
import requests
from dotenv import load_dotenv

load_dotenv()

class KoraPayService:
    def __init__(self):
        self.base_url = os.getenv("KORA_BASE_URL", "https://api.korapay.com/merchant/api/v1")
        self.public_key = os.getenv("KORA_PUBLIC_KEY")
        self.secret_key = os.getenv("KORA_SECRET_KEY")
        
        if not self.public_key or not self.secret_key:
            print("WARNING: KoraPay credentials not found in environment variables")

    def generate_payment_link(self, amount, name, email, description):
        """
        Generate a KoraPay checkout URL
        
        Parameters:
        amount (float): Amount to be paid
        name (str): Customer name
        email (str): Customer email
        description (str): Payment description
        
        Returns:
        tuple: (checkout_url, reference) or (None, None) if failed
        """
        print(f"Generating payment link for {email}, amount: {amount}")
        
        endpoint = f"{self.base_url}/charges/initialize"
        reference = f"PF-{uuid.uuid4().hex[:8]}"
        
        payload = {
            "amount": str(amount),
            "currency": "NGN",
            "reference": reference,
            "notification_url": "https://your-webhook-url.com/kora-webhook",
            "merchant_bears_cost": True,
            "customer": {
                "name": name,
                "email": email
            },
            "redirect_url": "https://t.me/Tefillah_PF_bot",  # Redirect back to your bot
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        print(f"Sending request to KoraPay API: {endpoint}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print(f"Using Authorization: Bearer {self.secret_key[:5]}...{self.secret_key[-5:]}")
        
        try:
            response = requests.post(endpoint, headers=headers, json=payload)
            print(f"KoraPay API response status: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"KoraPay API response: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Non-JSON response: {response.text[:200]}...")
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status"):
                checkout_url = data.get("data", {}).get("checkout_url")
                print(f"Successfully generated payment link: {checkout_url}")
                return checkout_url, reference
            
            print(f"KoraPay API error in response: {data}")
            return None, None
            
        except requests.RequestException as e:
            print(f"Request error: {str(e)}")
            return None, None
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print(traceback.format_exc())
            return None, None