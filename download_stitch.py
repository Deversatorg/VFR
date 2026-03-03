import urllib.request
import urllib.error

urls = {
    "login_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzdlNGZjMGM0MjQxOTQzMjc5OTMyZWY3YmZiMjBmZTNlEgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086",
    "setup_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzhjMzQzZWQzMTg5ZjRmYWZhMjk5OWNhNzk5NGZhMTVhEgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086",
    "avatar_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2QzMTg1NTFjNGQxZDRlMmY5OTZkZjY3MzJmYTRlMmM0EgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

for filename, url in urls.items():
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Successfully downloaded {filename}")
    except urllib.error.URLError as e:
        print(f"Failed to download {filename}: {e}")
