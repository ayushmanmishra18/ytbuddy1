import re
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
import pytube
from typing import Optional, Tuple

# Rate limiting
LAST_REQUEST_TIME = 0
MIN_REQUEST_INTERVAL = 1  # 1 second between requests

logger = logging.getLogger(__name__)

def validate_youtube_url(url: str) -> bool:
    """Validate YouTube URLs or standalone video IDs"""
    logging.debug(f"Validating URL: {url}")
    if not url:
        logging.debug("Empty URL provided")
        return False
        
    # Check if it's already just a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        logging.debug("Valid video ID provided")
        return True
        
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^\&]+)',
        r'(?:https?:\/\/)?youtu\.be\/([^\?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([^\?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^\?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^\?]+)'
    ]
    logging.debug(f"Testing patterns: {patterns} - Result: {any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)}")
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in patterns)

def get_video_id(url: str) -> str:
    """Extract video ID from URL or return if already an ID"""
    logging.debug(f"Extracting video ID from: {url}")
    
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        logging.debug(f"Video ID is already provided: {url}")
        return url
        
    patterns = [
        r'[?&]v=([^&]+)',
        r'youtu\.be\/([^?]+)',
        r'shorts\/([^?]+)',
        r'embed\/([^?]+)',
        r'v\/([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            video_id = match.group(1)
            logging.debug(f"Extracted video ID: {video_id}")
            return video_id
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_youtube_transcript(video_id: str) -> tuple[list, str]:
    """Get transcript with retry logic and language fallback"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return transcript, 'en'
    except NoTranscriptFound:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi'])
            return transcript, 'hi'
        except NoTranscriptFound:
            raise ValueError("No English or Hindi transcript available")

def get_manual_captions(video_id: str) -> Optional[str]:
    """Fallback method with improved error handling"""
    try:
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # First try with OAuth
        try:
            video = pytube.YouTube(youtube_url, use_oauth=True, allow_oauth_cache=True)
            caption = video.captions.get_by_language_code('en') or video.captions.get('a.en')
            if caption:
                return caption.generate_srt_captions()
        except Exception as oauth_error:
            logger.warning(f"OAuth attempt failed: {str(oauth_error)}")
        
        # Fallback to non-OAuth
        video = pytube.YouTube(youtube_url)
        caption = video.captions.get_by_language_code('en') or video.captions.get('a.en')
        return caption.generate_srt_captions() if caption else None
        
    except Exception as e:
        logger.error(f"Manual caption fetch failed: {str(e)}", exc_info=True)
        return None

def get_transcript(url: str) -> tuple[str, str]:
    global LAST_REQUEST_TIME
    try:
        logging.info(f"Starting transcript processing for URL: {url}")
        
        # Rate limiting
        elapsed = time.time() - LAST_REQUEST_TIME
        if elapsed < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - elapsed
            logging.debug(f"Rate limiting - waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        LAST_REQUEST_TIME = time.time()
        
        video_id = get_video_id(url)
        logging.info(f"Extracted video ID: {video_id}")
        
        try:
            transcript_data, language = get_youtube_transcript(video_id)
            transcript = ' '.join([item['text'] for item in transcript_data])
            logging.info(f"Successfully retrieved {language} transcript with {len(transcript_data)} segments")
            return transcript, language
        except ValueError as e:
            manual_captions = get_manual_captions(video_id)
            if manual_captions:
                logging.info(f"Successfully retrieved manual captions for video {video_id}")
                return manual_captions, 'en'
            raise
    except ValueError as ve:
        logging.warning(f"Input validation error: {str(ve)}")
        raise ve
    except Exception as e:
        logging.error("Unexpected error processing transcript", exc_info=True)
        raise ValueError("An error occurred while processing the video. Please try again later.")
