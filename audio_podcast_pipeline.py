import os
import glob
import time
import re
import asyncio
import datetime
from pathlib import Path

# pip install edge-tts
import edge_tts

# --- CONFIG ---
NUM_PAPERS = 5
DAYS_TO_KEEP = 15
AUDIO_DIR = "audio"
FEED_DIR = "feed"
FEED_PATH = f"{FEED_DIR}/podcast.xml"
VOICE = "en-US-AndrewNeural"  # free, sounds like Alloy. Try en-US-GuyNeural or en-US-AriaNeural

def sanitize_filename(title):
    safe = re.sub(r'[^A-Za-z0-9_]+', '_', title)[:50]
    return f"{safe}.mp3"

# --- KEEP YOUR REAL FETCH HERE ---
# This dummy fetch is so the file runs even without your old code.
# REPLACE this function with your actual fetch_papers() if you have one.
def fetch_papers(since_days=14):
    print(f"Fetching papers since {(datetime.date.today() - datetime.timedelta(days=since_days)).isoformat()}...")
    # EXAMPLE: return 10 fake papers for testing - your real code will return real papers
    # Your real implementation probably fetches from arXiv / EconPapers
    # Just make sure it returns list of dicts with 'title' and 'abstract'
    return [
        {"title": f"Paper {i} - Devecon Test {datetime.date.today()}", "abstract": f"This is a test abstract for paper {i}. This would be the real abstract of a development economics paper about GIS, big science, urbanism, and industrial organization. We summarize it for a commute."}
        for i in range(1, 11)
    ]

async def text_to_speech_free(text, out_path):
    print(f" TTS (FREE) -> {out_path}")
    try:
        communicate = edge_tts.Communicate(text[:4000], VOICE)
        await communicate.save(out_path)
        return True
    except Exception as e:
        print(f" TTS failed: {e}")
        return False

def prepare_summary_free(paper):
    # 100% free - just uses title + abstract, no OpenAI needed
    # If you want summarization later, you can add it, but this keeps it free
    title = paper.get('title','Untitled')
    abstract = paper.get('abstract','')[:2000]
    summary = f"Today's paper: {title}. Here's the key idea: {abstract}"
    print(f" Prepared summary for: {title[:60]}... ({len(summary)} chars)")
    return summary

def write_rss(episodes):
    os.makedirs(FEED_DIR, exist_ok=True)
    rss_items = ""
    for ep in episodes:
        if not os.path.exists(ep['audio_path']):
            continue
        title = ep['title'].replace('&','&amp;').replace('<','&lt;')
        url = f"https://davenoh.github.io/audio-travel/{ep['audio_path']}"
        rss_items += f"""
    <item>
      <title>{title}</title>
      <enclosure url="{url}" type="audio/mpeg" />
      <guid>{url}</guid>
      <pubDate>{datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
      <description>{title}</description>
    </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>Devecon Commute</title>
  <link>https://davenoh.github.io/audio-travel/</link>
  <description>Private research commute - 5 papers daily - FREE TTS</description>
  {rss_items}
</channel>
</rss>"""
    with open(FEED_PATH, 'w') as f:
        f.write(rss)
    print(f"RSS written to {FEED_PATH} with {len(episodes)} episodes")

def cleanup_old_audio(audio_dir=AUDIO_DIR, days=DAYS_TO_KEEP):
    cutoff = time.time() - (days * 24 * 3600)
    deleted = []
    for fp in glob.glob(os.path.join(audio_dir, "*.mp3")):
        try:
            if os.path.getmtime(fp) < cutoff:
                os.remove(fp)
                deleted.append(fp)
                print(f"🗑️ Removed old (> {days}d): {fp}")
        except Exception as e:
            print(f"Could not delete {fp}: {e}")
    if not deleted:
        print(f"✅ No audio older than {days} days")
    else:
        print(f"Cleaned up {len(deleted)} old files")
    return deleted

async def main_async():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    papers = fetch_papers(since_days=14)
    print(f"Found {len(papers)} papers")

    episodes = []
    for paper in papers[:NUM_PAPERS]:
        title = paper.get('title','Untitled')
        fname = sanitize_filename(title)
        out_path = os.path.join(AUDIO_DIR, fname)

        if os.path.exists(out_path):
            print(f" Already exists: {out_path}")
        else:
            summary = prepare_summary_free(paper)
            await text_to_speech_free(summary, out_path)

        if os.path.exists(out_path):
            episodes.append({"title": title, "audio_path": out_path})

    write_rss(episodes)
    cleanup_old_audio(days=DAYS_TO_KEEP)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()