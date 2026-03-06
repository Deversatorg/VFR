import os
import urllib.request

def reporthook(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        s = f"\rDownloading... {percent:5.1f}% ({read_so_far} / {total_size} bytes)"
        print(s, end='')

def download_url(url, output_path):
    print(f"Downloading {url} to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    urllib.request.urlretrieve(url, filename=output_path, reporthook=reporthook)
    print("\n")

if __name__ == "__main__":
    base_url = "https://huggingface.co/camenduru/SMPLer-X/resolve/main/smplx"
    models = ["SMPLX_NEUTRAL.npz"]
    
    out_dir = os.path.join(os.path.dirname(__file__), "models", "smplx")
    
    for model in models:
        download_url(f"{base_url}/{model}?download=true", os.path.join(out_dir, model))
    
    print("Download complete!")
