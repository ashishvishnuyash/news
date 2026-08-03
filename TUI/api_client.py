import requests

BASE_URL = "http://localhost:8000/api"

class APIClient:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.current_user = None

    def set_token(self, token: str):
        self.token = token

    def get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def register(self, username, email, password, role="USER", bio=""):
        url = f"{self.base_url}/auth/register"
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "role": role,
            "bio": bio
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code in (200, 201):
                return True, resp.json()
            return False, resp.json().get("detail", "Registration failed.")
        except Exception as e:
            return False, f"Connection error: {e}"

    def login(self, username, password):
        url = f"{self.base_url}/auth/login"
        payload = {
            "username": username,
            "password": password
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json()
                self.token = result.get("access_token")
                # Fetch profile
                ok, user = self.get_me()
                if ok:
                    self.current_user = user
                return True, "Login successful!"
            else:
                detail = resp.json().get("detail", "Invalid username or password.")
                return False, detail
        except Exception as e:
            return False, f"Connection error: {e}"

    def logout(self):
        if self.token:
            try:
                requests.post(f"{self.base_url}/auth/logout", headers=self.get_headers(), timeout=3)
            except Exception:
                pass
        self.token = None
        self.current_user = None

    def get_me(self):
        if not self.token:
            return False, "Not authenticated."
        try:
            resp = requests.get(f"{self.base_url}/auth/me", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                self.current_user = resp.json()
                return True, self.current_user
            return False, "Session expired or invalid token."
        except Exception as e:
            return False, f"Connection error: {e}"

    def get_settings(self):
        try:
            resp = requests.get(f"{self.base_url}/settings", timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, "Failed to load settings."
        except Exception as e:
            return False, f"Error: {e}"

    def update_settings(self, payload):
        try:
            resp = requests.put(f"{self.base_url}/settings", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to update settings.")
        except Exception as e:
            return False, f"Error: {e}"

    def get_articles(self, category=None, search=None):
        try:
            params = {}
            if category and category.lower() != "all":
                params["category"] = category
            if search:
                params["search"] = search
            resp = requests.get(f"{self.base_url}/articles", params=params, timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, "Failed to retrieve articles."
        except Exception as e:
            return False, f"Error: {e}"

    def get_article(self, slug):
        try:
            resp = requests.get(f"{self.base_url}/articles/{slug}", timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, "Article not found."
        except Exception as e:
            return False, f"Error: {e}"

    def get_comments(self, slug):
        try:
            resp = requests.get(f"{self.base_url}/articles/{slug}/comments", timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, []
        except Exception:
            return False, []

    def post_comment(self, slug, content):
        try:
            resp = requests.post(f"{self.base_url}/articles/{slug}/comments", json={"content": content}, headers=self.get_headers(), timeout=5)
            if resp.status_code in (200, 201):
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to post comment.")
        except Exception as e:
            return False, f"Error: {e}"

    # Journalist methods
    def get_my_articles(self):
        try:
            resp = requests.get(f"{self.base_url}/articles/journalist/my", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to load dispatches.")
        except Exception as e:
            return False, f"Error: {e}"

    def create_article(self, title, summary, category, content, image_url="", tags=""):
        payload = {
            "title": title,
            "summary": summary,
            "category": category,
            "content": content,
            "image_url": image_url,
            "tags": tags
        }
        try:
            resp = requests.post(f"{self.base_url}/articles/journalist/create", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code in (200, 201):
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to create article.")
        except Exception as e:
            return False, f"Error: {e}"

    def update_article(self, article_id, payload):
        try:
            resp = requests.put(f"{self.base_url}/articles/journalist/{article_id}", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to update article.")
        except Exception as e:
            return False, f"Error: {e}"

    def submit_article(self, article_id):
        try:
            resp = requests.post(f"{self.base_url}/articles/journalist/{article_id}/submit", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to submit article for review.")
        except Exception as e:
            return False, f"Error: {e}"

    # Editor methods
    def get_editor_queue(self, status_filter=None):
        try:
            params = {}
            if status_filter:
                params["status_filter"] = status_filter
            resp = requests.get(f"{self.base_url}/articles/editor/queue", params=params, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to fetch review queue.")
        except Exception as e:
            return False, f"Error: {e}"

    def review_article(self, article_id, status, editorial_notes=""):
        payload = {
            "status": status,
            "editorial_notes": editorial_notes
        }
        try:
            resp = requests.post(f"{self.base_url}/articles/editor/{article_id}/review", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Review submission failed.")
        except Exception as e:
            return False, f"Error: {e}"

    def get_article_reviews(self, article_id):
        try:
            resp = requests.get(f"{self.base_url}/articles/{article_id}/reviews", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, []
        except Exception:
            return False, []

    # Admin methods
    def get_admin_stats(self):
        try:
            resp = requests.get(f"{self.base_url}/admin/stats", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to fetch stats.")
        except Exception as e:
            return False, f"Error: {e}"

    def get_admin_users(self):
        try:
            resp = requests.get(f"{self.base_url}/admin/users", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to fetch users.")
        except Exception as e:
            return False, f"Error: {e}"

    def update_user_role(self, user_id, role):
        try:
            resp = requests.put(f"{self.base_url}/admin/users/{user_id}/role", json={"role": role}, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to update role.")
        except Exception as e:
            return False, f"Error: {e}"

    def get_admin_articles(self):
        try:
            resp = requests.get(f"{self.base_url}/admin/articles", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, resp.json().get("detail", "Failed to fetch articles.")
        except Exception as e:
            return False, f"Error: {e}"

    def delete_admin_article(self, article_id):
        try:
            resp = requests.delete(f"{self.base_url}/admin/articles/{article_id}", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, "Article deleted successfully."
            return False, resp.json().get("detail", "Failed to delete article.")
        except Exception as e:
            return False, f"Error: {e}"

    # Profile / User profile methods
    def update_profile(self, email=None, bio=None):
        payload = {}
        if email: payload["email"] = email
        if bio is not None: payload["bio"] = bio
        try:
            resp = requests.put(f"{self.base_url}/users/me", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                self.current_user = resp.json()
                return True, self.current_user
            return False, resp.json().get("detail", "Failed to update profile.")
        except Exception as e:
            return False, f"Error: {e}"

    def update_password(self, old_password, new_password):
        payload = {"old_password": old_password, "new_password": new_password}
        try:
            resp = requests.put(f"{self.base_url}/users/me/password", json=payload, headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, "Password updated successfully."
            return False, resp.json().get("detail", "Failed to update password.")
        except Exception as e:
            return False, f"Error: {e}"

    def get_notifications(self):
        try:
            resp = requests.get(f"{self.base_url}/users/me/notifications", headers=self.get_headers(), timeout=5)
            if resp.status_code == 200:
                return True, resp.json()
            return False, []
        except Exception:
            return False, []
