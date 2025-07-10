import requests
import os
import dotenv
import json
import traceback

dotenv.load_dotenv()

class DevToService:
    def __init__(self):
        self.api_key = os.getenv('DEVTO_API_KEY')
        self.base_url = os.getenv('DEVTO_BASE_URL')
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def send_request(self, method: str, endpoint: str, params=None, data=None):
        url = f"{self.base_url}/{endpoint}"
        headers = self.headers

        if method.lower() == 'get':
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == 'post':
            response = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError("Unsupported HTTP method")

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()


    # Article-related methods
    def get_articles(self, page: int = 1, per_page: int = 30):
        endpoint = "articles"
        params = {
            'page': page,
            'per_page': per_page
        }

        return self.send_request('get', endpoint, params=params)
    
    def get_articles_by_tag(self, tag: str):
        endpoint = "articles"
        params = {'tag': tag}

        return self.send_request('get', endpoint, params=params)
    
    def get_articles_by_tags(self, tags: list):
        endpoint = "articles"
        params = {'tags': ', '.join(tags)}

        return self.send_request('get', endpoint, params=params)
    
    def get_article_content(self, article_id: int):
        endpoint = f"articles/{article_id}"

        return self.send_request('get', endpoint)


    # User-related methods
    def get_user(self):
        endpoint = "users/me"

        return self.send_request('get', endpoint)

    def get_user_articles(self):
        endpoint = "articles/me/all"
        
        return self.send_request('get', endpoint)
    
    def get_user_published_articles(self):
        endpoint = f"articles/me/published"

        return self.send_request('get', endpoint)
    
    def post_article(self, title: str, body: str, tags: list):
        endpoint = "articles"
        data = {
            'article': {
                'title': title,
                'body_markdown': body,
                'tags': tags
            }
        }

        return self.send_request('post', endpoint, data=data)
    
    def get_user_followers(self):
        endpoint = "followers/users"

        return self.send_request('get', endpoint)
    
    def get_user_reading_list(self):
        endpoint = "readinglist"

        return self.send_request('get', endpoint)


    # Comment-related methods
    def get_article_comments(self, article_id: int):
        endpoint = "comments"
        params = {'a_id': article_id}

        return self.send_request('get', endpoint, params=params)


if __name__ == "__main__":
    devto_service = DevToService()

    # try:

    #     # Use article-related methods
    #     articles = devto_service.get_articles()
    #     with open("articles.json", "w", encoding="utf-8") as f:
    #         json.dump(articles, f, ensure_ascii=False, indent=2)

    #     articles_by_tag = devto_service.get_articles_by_tag("python")
    #     with open("articles_by_tag_python.json", "w", encoding="utf-8") as f:
    #         json.dump(articles_by_tag, f, ensure_ascii=False, indent=2)

    #     articles_by_tags = devto_service.get_articles_by_tags(["mcp", "a2a"])
    #     with open("articles_by_tags_mcp_a2a.json", "w", encoding="utf-8") as f:
    #         json.dump(articles_by_tags, f, ensure_ascii=False, indent=2)

    #     # Use user-related methods
    #     user_info = devto_service.get_user()
    #     with open("user_info.json", "w", encoding="utf-8") as f:
    #         json.dump(user_info, f, ensure_ascii=False, indent=2)

    #     user_articles = devto_service.get_user_articles()
    #     with open("user_articles.json", "w", encoding="utf-8") as f:
    #         json.dump(user_articles, f, ensure_ascii=False, indent=2)

    #     published_articles = devto_service.get_user_published_articles()
    #     with open("published_articles.json", "w", encoding="utf-8") as f:
    #         json.dump(published_articles, f, ensure_ascii=False, indent=2)

    #     new_article = devto_service.post_article(
    #         title="Sample Article",
    #         body="This is a sample article body.",
    #         tags=["sample", "article"]
    #     )
    #     with open("new_article.json", "w", encoding="utf-8") as f:
    #         json.dump(new_article, f, ensure_ascii=False, indent=2)

    #     followers = devto_service.get_user_followers()
    #     with open("followers.json", "w", encoding="utf-8") as f:
    #         json.dump(followers, f, ensure_ascii=False, indent=2)

    #     reading_list = devto_service.get_user_reading_list()
    #     with open("reading_list.json", "w", encoding="utf-8") as f:
    #         json.dump(reading_list, f, ensure_ascii=False, indent=2)

    #     # Use comment-related methods
    #     for article in user_articles:
    #         article_id = article['id']
    #         comments = devto_service.get_article_comments(article_id)
    #         with open(f"comments_article_{article_id}.json", "w", encoding="utf-8") as f:
    #             json.dump(comments, f, ensure_ascii=False, indent=2)


    # except requests.exceptions.RequestException as e:
    #     print(f"An error occurred: {e}")
    #     print(traceback.format_exc())
        

