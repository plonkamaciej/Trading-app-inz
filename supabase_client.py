import requests
from config import SUPABASE_URL, HEADERS

def get_from_supabase(endpoint, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    response = requests.get(url, headers=HEADERS, params=params)
    return response

def post_to_supabase(endpoint, data):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    response = requests.post(url, headers=HEADERS, json=data)
    print(f"Odpowiedź z Supabase (status: {response.status_code}):")
    print(f"Treść: {response.text}")
    return response

def patch_to_supabase(endpoint, data):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    response = requests.patch(url, headers=HEADERS, json=data)
    return response

def delete_from_supabase(endpoint, params=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    response = requests.delete(url, headers=HEADERS, params=params)
    return response
