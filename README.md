# ytbuddy - YouTube Video Analysis Tool

A powerful tool for analyzing YouTube videos, extracting transcripts, and answering questions about video content using AI.

## Features
- YouTube URL validation and video ID extraction
- Transcript extraction and storage
- AI-powered Q&A system using gemini-2.0-flash-lite
- Rate limiting and caching
- Usage metrics tracking

## Setup
1. Clone this repository
2. Install dependencies: `pip install -r server/requirements.txt`
3. Create `.env` file with your API keys (see `.env.example`)
4. Run the server: `python server/main.py`

https://github.com/ayushmanmishra18/ytbuddy

## Deployment
### Render
1. Connect your GitHub repository to Render
2. Set up environment variables from your `.env` file in Render's dashboard
3. The `render.yaml` file will automatically configure the deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Direct Deployment
```bash
python server/main.py
```

## API Endpoints
- `POST /api/ask` - Ask questions about a video (requires `video_id` and `question`)
- `GET /api/metrics` - Get usage metrics

## Requirements
- Python 3.9+
- Google API key for YouTube access
- Gemini API key for AI features
