import os
import requests
from typing import Dict, Any, List

from core.config import settings
GITHUB_TOKEN = settings.GITHUB_TOKEN
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
} if GITHUB_TOKEN else {}

def get_user_profile(username: str) -> Dict[str, Any]:
    url = f"https://api.github.com/users/{username}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass
    return {}

def get_user_repos(username: str) -> List[Dict[str, Any]]:
    # Get up to 100 repositories to analyze top ones
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass
    return []

def get_repo_languages(username: str, repo_name: str) -> Dict[str, int]:
    url = f"https://api.github.com/repos/{username}/{repo_name}/languages"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass
    return {}

def get_repo_contents(username: str, repo_name: str, path: str = "") -> List[Dict[str, Any]]:
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            if isinstance(resp.json(), list):
                return resp.json()
            else:
                return [resp.json()]
    except requests.exceptions.RequestException:
        pass
    return []

def get_file_content(download_url: str) -> str:
    try:
        resp = requests.get(download_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            return resp.text
    except requests.exceptions.RequestException:
        pass
    return ""

def analyze_github_data(username: str) -> Dict[str, Any]:
    profile = get_user_profile(username)
    if not profile:
        return {"error": "User not found or API limit exceeded"}
        
    repos = get_user_repos(username)
    
    # Sort repos by stars (stargazers_count) descending, then grab top 5
    top_repos = sorted(repos, key=lambda x: x.get('stargazers_count', 0), reverse=True)[:5]
    
    repo_details = []
    total_stars = 0
    all_languages = {}
    
    # Analyze all repos for total stars and basic stats
    for repo in repos:
        total_stars += repo.get('stargazers_count', 0)
    
    for repo in top_repos:
        repo_name = repo['name']
        langs = get_repo_languages(username, repo_name)
        
        # Accumulate languages
        for lang, count in langs.items():
            all_languages[lang] = all_languages.get(lang, 0) + count
            
        # Try to find requirements.txt or package.json at root level
        contents = get_repo_contents(username, repo_name)
        important_files = {}
        for item in contents:
            if item['type'] == 'file' and item['name'] in ['package.json', 'requirements.txt', 'pom.xml', 'Gemfile']:
                content = get_file_content(item['download_url'])
                if content:
                    important_files[item['name']] = content[:2000] # truncate to avoid huge prompts
                    
        repo_details.append({
            "name": repo_name,
            "description": repo.get('description'),
            "stars": repo.get('stargazers_count'),
            "forks": repo.get('forks_count'),
            "language": repo.get('language'),
            "languages_breakdown": langs,
            "important_files": important_files
        })
        
    return {
        "profile": {
            "login": profile.get("login"),
            "name": profile.get("name"),
            "public_repos": profile.get("public_repos"),
            "followers": profile.get("followers"),
            "following": profile.get("following"),
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
            "total_stars": total_stars
        },
        "top_repositories": repo_details,
        "aggregated_languages_bytes": all_languages,
        "total_analyzed_repos": len(repos)
    }
