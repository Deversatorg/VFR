import fs from 'fs';

const urls = {
    "login_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzdlNGZjMGM0MjQxOTQzMjc5OTMyZWY3YmZiMjBmZTNlEgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086",
    "setup_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzhjMzQzZWQzMTg5ZjRmYWZhMjk5OWNhNzk5NGZhMTVhEgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086",
    "avatar_screen.html": "https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2QzMTg1NTFjNGQxZDRlMmY5OTZkZjY3MzJmYTRlMmM0EgsSBxCd_ObF6Q0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNjIyNTk2NjkxMTkzNTgzODY3NA&filename=&opi=89354086"
};

const headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
};

async function downloadFiles() {
    for (const [filename, url] of Object.entries(urls)) {
        try {
            console.log(`Downloading ${filename}...`);
            const response = await fetch(url, { headers });
            if (!response.ok) {
                console.error(`Failed to download ${filename}, status: ${response.status}`);
                continue;
            }
            const html = await response.text();
            fs.writeFileSync(filename, html, 'utf8');
            console.log(`Successfully downloaded ${filename}`);
        } catch (error) {
            console.error(`Error downloading ${filename}: ${error}`);
        }
    }
}

downloadFiles();
