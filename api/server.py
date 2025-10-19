from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
import re

app = FastAPI(
    title="XNXX Scraper API V3",
    description="Unofficial API to search and fetch XNXX videos",
    version="2.3"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def home():
    return PlainTextResponse("XNXX Scraper API v3 is running by jsk")

@app.get("/api/search")
async def search(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, description="Page number")
):
    """Scrape search results from txnhh.com (latest mirror)."""
    try:
        base_url = "https://www.txnhh.com"
        search_url = f"{base_url}/search/fullhd/{q.replace(' ', '+')}/{page}"
        headers = {"User-Agent": "Mozilla/5.0"}

        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(search_url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        videos = []
        for block in soup.select("div.mozaique div.thumb-block"):
            a_tag = block.select_one("a[href]")
            img_tag = block.select_one("img")
            title_tag = block.select_one("p.metadata, p.thumb-under")

            raw_text = title_tag.get_text(strip=True) if title_tag else ""
            title = re.sub(r"\s+", " ", raw_text).strip() or "Untitled"

            # Extract details: views, rating, duration, quality
            views = re.search(r"([\d\.]+[MK])", raw_text)
            rating = re.search(r"(\d{1,3}%)", raw_text)
            duration = re.search(r"(\d+:\d+)", raw_text)
            quality = re.search(r"(\d+p)", raw_text)

            thumb = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
            link = f"{base_url}{a_tag['href']}" if a_tag else None

            if link:
                videos.append({
                    "title": title,
                    "url": link,
                    "thumbnail": thumb,
                    "views": views.group(1) if views else None,
                    "rating": rating.group(1) if rating else None,
                    "duration": duration.group(1) if duration else None,
                    "quality": quality.group(1) if quality else None
                })

        return JSONResponse(videos)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/video")
async def get_video_details(
    url: str = Query(..., description="Full video page URL")
):
    """Extract HD and SD video URLs + metadata."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")

        video_hd, video_sd = None, None
        title = soup.select_one("title")
        title_text = title.text.strip() if title else "Unknown Title"

        # Find script tags containing URLs
        for script in soup.find_all("script"):
            if not script.string:
                continue
            if "html5player.setVideoUrlHigh" in script.string:
                match = re.search(r"html5player\.setVideoUrlHigh\('(.*?)'\)", script.string)
                if match:
                    video_hd = match.group(1)
            if "html5player.setVideoUrlLow" in script.string:
                match = re.search(r"html5player\.setVideoUrlLow\('(.*?)'\)", script.string)
                if match:
                    video_sd = match.group(1)

        duration = None
        dur_tag = soup.select_one(".duration")
        if dur_tag:
            duration = dur_tag.get_text(strip=True)

        if not video_hd and not video_sd:
            return JSONResponse({"error": "Video URLs not found"}, status_code=404)

        return JSONResponse({
            "title": title_text,
            "duration": duration,
            "video_hd": video_hd,
            "video_sd": video_sd,
            "source": url
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
