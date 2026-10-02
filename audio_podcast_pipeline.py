import os
import glob
import time
import re
import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# --- CONFIG ---
NUM_PAPERS = 5
DAYS_TO_KEEP = 15
AUDIO_DIR = "audio"
FEED_DIR = "feed"
FEED_PATH = f"{FEED_DIR}/podcast.xml"

# For OpenAI - set your key in terminal: export OPENAI_API_KEY="sk-..."
# pip install openai
try:
    from openai import OpenAI
    client = OpenAI()
except:
    client = None

# --- YOUR EXISTING FETCH LOGIC ---
# Replace this with your real fetch function if different
# This is a placeholder that matches your log output
def fetch_papers(since_days=14):
    """Return list of papers - replace with your real implementation"""
    # Example: your real code probably does arXiv / Semantic Scholar fetch
    # Keeping same interface: returns list of dicts with 'title'
    print(f"Fetching papers since {(datetime.date.today() - datetime.timedelta(days=since_days)).isoformat()}...")
    # TODO: Your existing fetch logic here
    # For now, returning dummy to keep file runnable - your real function will overwrite this
    return []

def sanitize_filename(title):
    safe = re.sub(r'[^A-Za-z0-9_]+', '_', title)[:50]
    return f"{safe}.mp3"

def prepare_summary(paper):
    title = paper.get('title', 'Untitled')
    # --- YOUR EXISTING SUMMARY LOGIC ---
    # Replace with your real OpenAI summarization
    if client:
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Summarize this academic paper for a 3-minute podcast, conversational, for development economist commute."},
                    {"role": "user", "content": f"Title: {title}\nAbstract: {paper.get('abstract','')[:4000]}"}
                ]
            )
            summary = resp.choices[0].message.content
        except Exception as e:
            print(f"Summary failed for {title}: {e}")
            summary = paper.get('abstract','')[:1000]
    else:
        summary = paper.get('abstract','')[:1000]

    print(f" Prepared summary for: {title[:60]}... ({len(summary)} chars)")
    return summary

def text_to_speech(text, out_path):
    """Your existing TTS logic"""
    if not client:
        print("No OpenAI client - skipping TTS")
        return False
    try:
        print(f" TTS -> {out_path}")
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text[:4000] # TTS limit
        )
        response.stream_to_file(out_path)
        return True
    except Exception as e:
        print(f"TTS failed: {e}")
        return False

def write_rss(episodes):
    """Your existing RSS writer - keeps only existing files"""
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
  <description>Private research commute - 5 papers daily</description>
  {rss_items}
</channel>
</rss>"""
    with open(FEED_PATH, 'w') as f:
        f.write(rss)
    print(f"RSS written to {FEED_PATH} with {len(episodes)} episodes")

def cleanup_old_audio(audio_dir=AUDIO_DIR, days=DAYS_TO_KEEP):
    """Auto-delete mp3s older than `days`"""
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

# --- MAIN ---
def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    papers = fetch_papers(since_days=14) # your existing logic

    # If you paste this into your real file, replace fetch_papers() above
    # with your actual fetch so this next line is not needed:
    if not papers:
        print("Found 0 papers - using existing audio/ to build feed (so cleanup can be tested)")
        # Build episodes from existing audio for testing
        existing = sorted(glob.glob(f"{AUDIO_DIR}/*.mp3"), key=os.path.getmtime, reverse=True)[:NUM_PAPERS]
        episodes = [{"title": Path(p).stem.replace('_',' '), "audio_path": p} for p in existing]
        write_rss(episodes)
        cleanup_old_audio(days=DAYS_TO_KEEP)
        return

    print(f"Found {len(papers)} papers")
    episodes = []
    for paper in papers[:NUM_PAPERS]:
        title = paper.get('title','Untitled')
        fname = sanitize_filename(title)
        out_path = os.path.join(AUDIO_DIR, fname)

        if os.path.exists(out_path):
            print(f" Already exists: {out_path}")
        else:
            summary = prepare_summary(paper)
            text_to_speech(summary, out_path)

        if os.path.exists(out_path):
            episodes.append({"title": title, "audio_path": out_path})

    write_rss(episodes)
    # --- THIS IS THE NEW PART ---
    cleanup_old_audio(days=DAYS_TO_KEEP)

if __name__ == "__main__":
    main()