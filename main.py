import base64
import json
import names
import os
import random
import string
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
from curl_cffi import requests as curl_requests
from datetime import datetime, timezone
from fake_useragent import UserAgent
from twocaptcha import TwoCaptcha
from anticaptchaofficial.imagecaptcha import *
from anticaptchaofficial.turnstileproxyless import turnstileProxyless

init(autoreset=True)
ua = UserAgent()

model = None
successful_accounts = 0
failed_accounts = 0
MAX_RETRIES = 10

def print_summary():
    total = successful_accounts + failed_accounts
    print("\n")
    print(f"{Fore.LIGHTCYAN_EX}All Process Completed{Style.RESET_ALL}")
    print(f"From {total}/{total_accounts} account(s)")
    print(f"{Fore.LIGHTGREEN_EX}Success: {successful_accounts}{Style.RESET_ALL}")
    print(f"{Fore.LIGHTRED_EX}Failed: {failed_accounts}{Style.RESET_ALL}")

def get_headers(token=None):
    headers = {
        'accept': '/',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp',
        'priority': 'u=1, i',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': ua.chrome
    }
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.load_proxies()
        
    def load_proxies(self):
        try:
            if os.path.exists('proxies.txt') and os.path.getsize('proxies.txt') > 0:
                with open('proxies.txt', 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                print(f"{Fore.LIGHTGREEN_EX}Loaded proxies from proxies.txt\n{Style.RESET_ALL}")
            else:
                print(f"{Fore.LIGHTRED_EX}WARNING: proxies.txt not found or empty. Using direct connection.{Style.RESET_ALL}")
                print(f"{Fore.LIGHTRED_EX}For better success rate, please use proxies!\n{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.LIGHTRED_EX}Error loading proxies: {str(e)}{Style.RESET_ALL}")
            
    def get_random_proxy(self):
        if not self.proxies:
            return None
        proxy = random.choice(self.proxies)
        return {
            "http": f"{proxy}",
            "https": f"{proxy}"
        }

def generate_password():
    first_letter = random.choice(string.ascii_uppercase)
    other_letters = ''.join(random.choices(string.ascii_lowercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"{first_letter}{other_letters}@{numbers}!"

def generate_app_id():
    return f"67{''.join(random.choices(string.hexdigits, k=22)).lower()}"

def log_message(message="", message_type="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    account_status = f"[{current_account}/{total_accounts}] " if 'current_account' in globals() else ""
    
    colors = {
        "success": Fore.LIGHTGREEN_EX,
        "error": Fore.LIGHTRED_EX,
        "warning": Fore.LIGHTYELLOW_EX,
        "process": Fore.LIGHTCYAN_EX
    }
    
    log_color = colors.get(message_type, Fore.LIGHTWHITE_EX)
    print(f"{Fore.WHITE}[{Style.DIM}{timestamp}{Style.RESET_ALL}{Fore.WHITE}] {account_status}{log_color}{message}")

def setup_captcha_solver(api_key, solver_type):
    global solver, model
    model = solver_type
    
    if solver_type == "2captcha":
        solver = TwoCaptcha(api_key)
    else:
        solver = imagecaptcha()
        solver.set_key(api_key)
    return solver

def get_random_domain(proxies):
    log_message("Searching for available email domain...", "process")
    vowels = 'aeiou'
    consonants = 'bcdfghjklmnpqrstvwxyz'
    keyword = random.choice(consonants) + random.choice(vowels)
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = curl_requests.get(
                f'https://generator.email/search.php?key={keyword}',
                headers=get_headers(),
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            domains = response.json()
            valid_domains = [d for d in domains if all(ord(c) < 128 for c in d)]
            
            if valid_domains:
                selected_domain = random.choice(valid_domains)
                log_message(f"Selected domain: {selected_domain}", "success")
                return selected_domain
                
            log_message("Could not find valid domain", "error")
            return None
            
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Connection error: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Error getting domain after {MAX_RETRIES} attempts: {str(e)}", "error")
                return None

def generate_email(domain):
    log_message("Generating email address...", "process")
    first_name = names.get_first_name().lower()
    last_name = names.get_last_name().lower()
    random_nums = ''.join(random.choices(string.digits, k=3))
    
    separator = random.choice(['', '.'])
    email = f"{first_name}{separator}{last_name}{random_nums}@{domain}"
    log_message(f"Email created: {email}", "success")
    return email

def get_puzzle_id(app_id, proxies):
    url = 'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle'
    params = {
        'appid': app_id
    }
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = curl_requests.get(
                url, 
                headers=get_headers(),
                params=params,
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            response.raise_for_status()
            return response.json()['puzzle_id']
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Connection error getting puzzle ID: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Error getting puzzle ID after {MAX_RETRIES} attempts: {str(e)}", "error")
                raise

def get_puzzle_image(puzzle_id, app_id, proxies):
    url = 'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/get-puzzle-image'
    params = {
        'puzzle_id': puzzle_id,
        'appid': app_id
    }
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            response = curl_requests.get(
                url, 
                headers=get_headers(),
                params=params,
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            response.raise_for_status()
            return response.json()['imgBase64']
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Connection error getting puzzle image: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Error getting puzzle image after {MAX_RETRIES} attempts: {str(e)}", "error")
                raise

def process_image(base64_image, solver_type):
    try:
        image_data = base64.b64decode(base64_image)
        temp_image = "temp_captcha.png"
        
        with open(temp_image, "wb") as f:
            f.write(image_data)

        try:
            if solver_type == "2captcha":
                result = solver.normal(temp_image)
                captcha_text = result['code']
            else:
                solver.set_verbose(0)
                captcha_text = solver.solve_and_return_solution(file_path=temp_image)
                if captcha_text == 0:
                    raise Exception("Failed to solve captcha")
            
            return captcha_text
            
        finally:
            if os.path.exists(temp_image):
                os.remove(temp_image)
                
    except Exception as e:
        log_message(f"Error solving captcha: {str(e)}", "error")
        raise

def verify_email(verification_url, proxies, solver_type, api_key):
    log_message("Verifying email...", "process")
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            key = verification_url.split('key=')[1]
            
            response = curl_requests.get(
                verification_url,
                headers=get_headers(),
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )

            if solver_type == "2captcha":
                solver = TwoCaptcha(api_key)
                result = solver.turnstile(
                    sitekey="0x4AAAAAAA0DVmzm9PiLTNuf",
                    url=f"https://www.aeropres.in/chromeapi/dawn/v1/userverify/verifyconfirm?key={key}"
                )
                turnstile_token = result['code']
            else:
                solver = turnstileProxyless()
                solver.set_verbose(0)
                solver.set_key(api_key)
                solver.set_website_url(f"https://www.aeropres.in/chromeapi/dawn/v1/userverify/verifyconfirm?key={key}")
                solver.set_website_key("0x4AAAAAAA0DVmzm9PiLTNuf")
                solver.set_action("login")
                turnstile_token = solver.solve_and_return_solution()
                
                if turnstile_token == 0:
                    raise Exception("Failed to solve verification captcha")
            
            verify_response = curl_requests.post(
                'https://www.aeropres.in/chromeapi/dawn/v1/userverify/verifycheck',
                params={'key': key},
                headers=get_headers(),
                json={'token': turnstile_token},
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            
            if verify_response.status_code == 200:
                log_message("Email verification successful", "success")
                return True
            else:
                log_message(f"Verification failed with status {verify_response.status_code}", "error")
                retry_count += 1
                
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Verification error: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Verification failed after {MAX_RETRIES} attempts: {str(e)}", "error")
                return False
    
    return False

def get_verification_link(email, domain, proxies):
    log_message("Waiting for verification email...", "process")
    cookies = {
        'embx': f'[%22{email}%22]',
        'surl': f'{domain}/{email.split("@")[0]}'
    }
    
    max_attempts = 5
    retry_count = 0
    
    while retry_count < max_attempts:
        try:
            response = curl_requests.get(
                'https://generator.email/inbox1/',
                headers=get_headers(),
                cookies=cookies,
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            
            soup = BeautifulSoup(response.text, 'html.parser')
            mailextra = soup.find('p', {'class': 'mailextra'})
            
            if mailextra:
                maillink = mailextra.find('a', {'class': 'maillink'})
                if maillink:
                    link = maillink.text.strip()
                    if 'verifyconfirm' in link:
                        log_message("Verification link found", "success")
                        return link
            
            log_message(f"Attempt {retry_count + 1}: Waiting for email...", "process")
            retry_count += 1
            
        except Exception as e:
            retry_count += 1
            if retry_count < max_attempts:
                log_message(f"Connection error getting verification link: {str(e)}. Retrying... ({retry_count}/{max_attempts})", "warning")
            else:
                log_message(f"Error getting verification link after {max_attempts} attempts: {str(e)}", "error")
                return None
    
    log_message("Could not find verification link", "error")
    return None

def register_user(puzzle_id, captcha_text, email, password, referral_code, app_id, proxies):
    url = 'https://www.aeropres.in/chromeapi/dawn/v1/puzzle/validate-register'
    
    data = {
        "firstname": names.get_first_name(),
        "lastname": names.get_last_name(),
        "email": email,
        "mobile": "",
        "password": password,
        "country": "+91",
        "referralCode": referral_code,
        "puzzle_id": puzzle_id,
        "ans": captcha_text,
        "ismarketing": True,
        "browserName": "Chrome"
    }
    
    params = {
        'appid': app_id
    }
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            headers = get_headers()
            headers['content-type'] = 'application/json'
            
            response = curl_requests.post(
                url, 
                headers=headers,
                params=params, 
                json=data,
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            return response.status_code
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Connection error registering user: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Error registering user after {MAX_RETRIES} attempts: {str(e)}", "error")
                return None
def login_user(email, password, app_id, proxies):
    log_message("Attempting to login...", "process")
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            login_successful = False
            while not login_successful:
                puzzle_id = get_puzzle_id(app_id, proxies)
                log_message(f"Login Captcha ID: {puzzle_id}", "process")
                
                image_base64 = get_puzzle_image(puzzle_id, app_id, proxies)
                captcha_text = process_image(image_base64, model)
                log_message(f"Solved Login Captcha: {captcha_text}", "success")
                
                current_datetime = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                
                login_data = {
                    "username": email,
                    "password": password,
                    "logindata": {
                        "_v": {"version": "1.1.2"},
                        "datetime": current_datetime
                    },
                    "puzzle_id": puzzle_id,
                    "ans": captcha_text
                }
                
                headers = get_headers()
                headers['content-type'] = 'application/json'
                
                response = curl_requests.post(
                    f'https://www.aeropres.in/chromeapi/dawn/v1/user/login/v2',
                    params={'appid': app_id},
                    headers=headers,
                    json=login_data,
                    proxies=proxies,
                    impersonate="chrome110",
                    timeout=120
                )
                
                if response.status_code == 200:
                    log_message("Login successful!", "success")
                    login_successful = True
                    return response.json()
                elif response.status_code == 400:
                    log_message("Invalid CAPTCHA, retrying with new captcha...", "warning")
                    continue
                else:
                    log_message(f"Login failed with status {response.status_code}, retrying...", "warning")
                    retry_count += 1
                    break
                    
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Login error: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Login failed after {MAX_RETRIES} attempts: {str(e)}", "error")
                return None
    
    return None

def verify_social_media(token, app_id, proxies):
    log_message("Verifying social media...", "process")
    social_data = [
        {"twitter_x_id": "twitter_x_id"},
        {"discordid": "discordid"},
        {"telegramid": "telegramid"}
    ]
    
    headers = get_headers(token)
    headers['content-type'] = 'application/json'
    
    for data in social_data:
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                response = curl_requests.post(
                    f'https://www.aeropres.in/chromeapi/dawn/v1/profile/update',
                    params={'appid': app_id},
                    headers=headers,
                    json=data,
                    proxies=proxies,
                    impersonate="chrome110",
                    timeout=120
                )
                
                if response.status_code == 200:
                    log_message(f"Verified {list(data.keys())[0]}", "success")
                    break
                else:
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        log_message(f"Failed to verify {list(data.keys())[0]}, retrying... ({retry_count}/{MAX_RETRIES})", "warning")
                    
            except Exception as e:
                retry_count += 1
                if retry_count < MAX_RETRIES:
                    log_message(f"Social verification error: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
                else:
                    log_message(f"Social verification failed after {MAX_RETRIES} attempts: {str(e)}", "error")

def get_user_points(token, app_id, proxies):
    log_message("Retrieving user points...", "process")
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            headers = get_headers(token)
            
            response = curl_requests.get(
                f'https://www.aeropres.in/api/atom/v1/userreferral/getpoint',
                params={'appid': app_id},
                headers=headers,
                proxies=proxies,
                impersonate="chrome110",
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    referral_data = data['data']['referralPoint']
                    reward_data = data['data']['rewardPoint']
                    
                    total_points = (
                        referral_data.get('commission', 0) +
                        reward_data.get('points', 0) +
                        reward_data.get('registerpoints', 0) +
                        reward_data.get('twitter_x_id_points', 0) +
                        reward_data.get('discordid_points', 0) +
                        reward_data.get('telegramid_points', 0)
                    )
                    
                    log_message(f"Total points: {total_points}", "success")
                    return total_points
            
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Failed to get points, retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message("Failed to retrieve points after all retries", "error")
                return 0
                
        except Exception as e:
            retry_count += 1
            if retry_count < MAX_RETRIES:
                log_message(f"Error getting points: {str(e)}. Retrying... ({retry_count}/{MAX_RETRIES})", "warning")
            else:
                log_message(f"Error getting points after {MAX_RETRIES} attempts: {str(e)}", "error")
                return 0
    
    return 0

def process_single_account(current_account, proxy_manager, email_domain, referral_code, api_key, solver_type):
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            proxies = proxy_manager.get_random_proxy()
            domain = email_domain or get_random_domain(proxies)
            if not domain:
                return False
                
            email = generate_email(domain)
            password = generate_password()
            app_id = generate_app_id()
            
            log_message(f"Using email: {email}", "process")
            log_message(f"App ID: {app_id}", "process")
            
            registration_successful = False
            
            while not registration_successful:
                puzzle_id = get_puzzle_id(app_id, proxies)
                log_message(f"Register Captcha ID: {puzzle_id}", "process")
                
                image_base64 = get_puzzle_image(puzzle_id, app_id, proxies)
                captcha_text = process_image(image_base64, model)
                log_message(f"Solved Register Captcha: {captcha_text}", "success")
                
                status_code = register_user(puzzle_id, captcha_text, email, password, referral_code, app_id, proxies)
                
                if status_code == 200:
                    registration_successful = True
                    log_message("Registration successful!", "success")
                elif status_code == 400:
                    log_message("Invalid CAPTCHA, retrying with new captcha...", "warning")
                    continue
                else:
                    log_message(f"Registration failed with status {status_code}, retrying...", "warning")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        return False
                    break
            
            if registration_successful:
                verification_url = get_verification_link(email, domain, proxies)
                if verification_url and verify_email(verification_url, proxies, solver_type, api_key):
                    log_message("Account verified successfully!", "success")
                    
                    with open("accounts.txt", "a") as f:
                        f.write(f"Email: {email}\n")
                        f.write(f"Password: {password}\n")
                        f.write("-" * 50 + "\n")
                    
                    login_response = login_user(email, password, app_id, proxies)
                    if login_response:
                        token = login_response['data']['token']
                        verify_social_media(token, app_id, proxies)
                        total_points = get_user_points(token, app_id, proxies)
                        
                        with open("accounts.txt", "r") as f:
                            lines = f.readlines()
                        with open("accounts.txt", "w") as f:
                            f.writelines(lines[:-1])
                            f.write(f"Token: {token}\n")
                            f.write(f"Points: {total_points}\n")
                            f.write("-" * 50 + "\n")
                        
                        with open("accounts-for-dawn-validator-bot.txt", "a") as f:
                            f.write(f"{email}:{token}\n")
                        
                        print(f"\nAccount {current_account} success referred to {Fore.LIGHTMAGENTA_EX}{referral_code}{Fore.RESET}{Fore.LIGHTCYAN_EX}, Processing next account...{Fore.RESET}\n")
                        return True
                    else:
                        log_message("Login failed, please login manually. Moving to next account...", "warning")
                        print(f"\nAccount {current_account} registration success, but login failed. Moving to next account...\n")
                        return True 
                else:
                    log_message("Verification failed, retrying...", "warning")
                    retry_count += 1
                    if retry_count >= MAX_RETRIES:
                        return False
                    continue
                    
        except Exception as e:
            log_message(f"Error occurred: {str(e)}", "error")
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                return False
            log_message(f"Retrying account creation... Attempt {retry_count + 1}/{MAX_RETRIES}", "warning")
            continue
    
    return False

def main():
    global current_account, total_accounts, successful_accounts, failed_accounts
    
    banner = f"""
{Fore.LIGHTCYAN_EX}╔═══════════════════════════════════════════╗
║       Dawn Validator Autoreferral         ║
║       https://github.com/im-hanzou        ║
╚═══════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)
    print(f"{Fore.LIGHTRED_EX}Once All Process Completed, run this bot: {Fore.LIGHTMAGENTA_EX}https://github.com/im-hanzou/dawn-validator-bot{Fore.RESET}\n{Fore.LIGHTRED_EX}Copy and Paste content of {Fore.LIGHTMAGENTA_EX}accounts-for-dawn-validator-bot.txt{Fore.RESET} {Fore.LIGHTRED_EX}to{Fore.RESET} {Fore.LIGHTMAGENTA_EX}accounts.txt{Fore.RESET} {Fore.LIGHTRED_EX}in{Fore.RESET} {Fore.LIGHTMAGENTA_EX}dawn-validator-bot{Style.RESET_ALL}\n")

    while True:
        print(f"{Fore.CYAN}Choose your captcha solver:")
        print(f"1. 2captcha")
        print(f"2. Anti-Captcha")
        print(f"Enter your choice (1 or 2): {Style.RESET_ALL}", end="")
        solver_choice = input().strip()
        
        if solver_choice in ['1', '2']:
            solver_type = "2captcha" if solver_choice == '1' else "anticaptcha"
            break
        else:
            print(f"{Fore.LIGHTRED_EX}Invalid choice. Please enter 1 or 2.{Style.RESET_ALL}")

    print(f"{Fore.CYAN}\nEnter referral code: {Style.RESET_ALL}", end="")
    referral_code = input()
    
    print(f"{Fore.CYAN}Enter your {solver_type} API key: {Style.RESET_ALL}", end="")
    captcha_api_key = input()
    
    print(f"{Fore.CYAN}Enter how many accounts: {Style.RESET_ALL}", end="")
    num_accounts = int(input())
    total_accounts = num_accounts
    
    try:
        setup_captcha_solver(captcha_api_key, solver_type)
        proxy_manager = ProxyManager()
        
        for current_account in range(1, num_accounts + 1):
            if process_single_account(current_account, proxy_manager, None, referral_code, captcha_api_key, solver_type):
                successful_accounts += 1
            else:
                failed_accounts += 1
                
    except Exception as e:
        log_message(f"Fatal error: {str(e)}", "error")
        
if __name__ == "__main__":
    try:
        main()
        print_summary()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        print_summary()
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
