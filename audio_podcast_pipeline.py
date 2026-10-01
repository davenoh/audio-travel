import os
import re
import requests
import datetime
from feedgen.feed import FeedGenerator
import edge_tts
import asyncio
from dotenv import load_dotenv
load_dotenv()

RSS_BASE_URL = "https://davenoh.github.io/audio-travel/"
AUDIO_BASE_URL = RSS_BASE_URL + "audio/"
FEED_PATH = "feed/podcast.xml"

def fetch_recent_papers(days=14):
    today = datetime.date.today()
    since = today - datetime.timedelta(days=days)
    url = "https://api.openalex.org/works"
    params = {
        "filter": f"from_publication_date:{since}",
        "search": "development economics",
        "sort": "publication_date:desc",
        "per-page": "10"
    }
    print(f"Fetching papers since {since}...")
    headers = {"User-Agent": "audio-travel/1.0 (mailto:dnohkim00@gmail.com)"}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    results = r.json().get('results', [])
    print(f"Found {len(results)} papers")
    return results

def summarize_paper(paper):
    title = paper.get('display_name') or paper.get('title') or "Untitled"
    abstract = ""
    if paper.get('abstract_inverted_index'):
        inv = paper['abstract_inverted_index']
        try:
            max_pos = max([max(v) for v in inv.values()])
            words = [''] * (max_pos + 1)
            for w, pos in inv.items():
                for p in pos:
                    if p < len(words):
                        words[p] = w
            abstract = ' '.join(words)
        except:
            abstract = ""

    if not abstract:
        abstract = paper.get('abstract') or title

    # Make it speakable - no LLM needed
    summary = f"Paper title: {title}. Here is the abstract: {abstract[:2000]}. That's the key takeaway for today's commute."
    print(f" Prepared summary for: {title[:80]}... ({len(summary)} chars)")
    return title, summary

async def text_to_mp3(text, out_path):
    print(f" TTS -> {out_path}")
    communicate = edge_tts.Communicate(text, "en-US-AndrewNeural")
    await communicate.save(out_path)

def build_rss(episodes):
    fg = FeedGenerator()
    fg.load_extension('podcast')  # <-- add this, required for itunes tags
    fg.title("Devecon Commute")
    fg.link(href="https://davenoh.github.io/audio-travel/", rel='alternate')
    fg.description("Daily development economics papers for the commute")
    fg.language('en')

    # Required by Spotify:
    fg.author(name="Dave Noh", email="nvb4y2rwnb@privaterelay.appleid.com") # <-- put your REAL gmail here, same as Spotify login
    fg.podcast.itunes_author("Dave Noh")
    fg.podcast.itunes_owner(name="Dave Noh", email="nvb4y2rwnb@privaterelay.appleid.com")
    fg.podcast.itunes_category("Education")
    fg.podcast.itunes_explicit("no")

    # Cover art - must be publicly reachable:
    fg.image(url="https://davenoh.github.io/audio-travel/cover_devecon.png", title="Devecon Commute")
    fg.podcast.itunes_image("https://davenoh.github.io/audio-travel/cover_devecon.png")

    for ep in episodes:
        fe = fg.add_entry()
        fe.id(ep['url'])
        fe.title(ep['title'])
        fe.description(ep['summary'][:500])
        fe.enclosure(ep['url'], 0, 'audio/mpeg')
        fe.pubDate(ep['date'])
    os.makedirs("feed", exist_ok=True)
    fg.rss_file(FEED_PATH)
    print(f"RSS written to {FEED_PATH} with {len(episodes)} episodes")

async def main():
    papers = fetch_recent_papers()
    episodes = []
    for paper in papers[:2]:
        try:
            title, summary = summarize_paper(paper)
            safe = re.sub(r'[^a-zA-Z0-9]+', '_', title)[:50]
            mp3_name = f"{safe}.mp3"
            mp3_path = os.path.join("audio", mp3_name)
            if not os.path.exists(mp3_path):
                await text_to_mp3(summary, mp3_path)
            else:
                print(f" Already exists: {mp3_path}")
            episodes.append({
                'title': title,
                'summary': summary,
                'url': AUDIO_BASE_URL + mp3_name,
                'date': datetime.datetime.now(datetime.timezone.utc)
            })
        except Exception as e:
            print(f"Skipped: {e}")
            import traceback
            traceback.print_exc()
    build_rss(episodes)

if __name__ == "__main__":
    asyncio.run(main())