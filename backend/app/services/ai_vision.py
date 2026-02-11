"""AI Vision Analysis Service for Screen Recordings.

Uses Anthropic Claude Vision API to analyze screenshots and provide:
  - Application detection
  - Activity classification (coding, browsing, meeting, etc.)
  - Productivity scoring
  - Sensitive content detection
  - Work pattern insights
"""

import base64
import os
from datetime import datetime
from typing import Any

import httpx


class AIVisionAnalyzer:
    """Analyzes screenshots using Claude Vision API."""

    def __init__(self, api_key: str | None = None):
        """Initialize with Anthropic API key."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.model = "claude-3-5-sonnet-20241022"  # Claude 3.5 Sonnet with vision
        self.api_url = "https://api.anthropic.com/v1/messages"

    async def analyze_screenshot(
        self,
        image_bytes: bytes,
        media_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        """Analyze a screenshot and return insights.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG)
            media_type: MIME type (image/jpeg or image/png)

        Returns:
            Analysis results with keys:
              - timestamp: ISO timestamp
              - application: Detected application name
              - activity_type: Type of activity (coding/browsing/meeting/idle/etc)
              - productivity_score: 1-10 score
              - has_sensitive_content: bool
              - summary: Human-readable summary
              - details: Additional metadata
        """
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Construct prompt for Claude
        prompt = """Analyze this screenshot of a user's screen. Provide:

1. **Application**: What application/program is being used? (e.g., "Visual Studio Code", "Google Chrome", "Microsoft Teams")
2. **Activity Type**: What is the user doing? Choose ONE:
   - coding (writing/editing code)
   - browsing (web browsing, research)
   - meeting (video call, presentation)
   - documentation (writing docs, emails)
   - design (graphic design, UI/UX work)
   - idle (desktop, screensaver, no active work)
   - entertainment (games, videos, social media)
   - other (specify)

3. **Productivity Score**: Rate 1-10 (1=not productive, 10=highly productive)
4. **Sensitive Content**: Does the screen contain passwords, personal data, financial info, or other sensitive content? (yes/no)
5. **Summary**: Brief 1-sentence description of what the user is doing.

Respond in JSON format:
```json
{
  "application": "...",
  "activity_type": "...",
  "productivity_score": 8,
  "has_sensitive_content": false,
  "summary": "..."
}
```"""

        # Call Anthropic API
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 512,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": media_type,
                                            "data": image_b64,
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": prompt,
                                    },
                                ],
                            }
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Parse response
                content = data.get("content", [])
                if not content:
                    raise ValueError("Empty response from API")

                text = content[0].get("text", "")

                # Extract JSON from response
                import json
                import re

                # Find JSON block in markdown
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    # Try parsing entire response as JSON
                    result = json.loads(text)

                # Add metadata
                result["timestamp"] = datetime.utcnow().isoformat() + "Z"
                result["model"] = self.model
                result["status"] = "success"

                return result

            except httpx.HTTPStatusError as e:
                return {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "error",
                    "error": f"API error: {e.response.status_code}",
                    "application": "Unknown",
                    "activity_type": "unknown",
                    "productivity_score": 0,
                    "has_sensitive_content": False,
                    "summary": "Analysis failed",
                }
            except Exception as e:
                return {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "status": "error",
                    "error": str(e),
                    "application": "Unknown",
                    "activity_type": "unknown",
                    "productivity_score": 0,
                    "has_sensitive_content": False,
                    "summary": "Analysis failed",
                }

    def analyze_screenshot_sync(
        self,
        image_bytes: bytes,
        media_type: str = "image/jpeg",
    ) -> dict[str, Any]:
        """Synchronous version of analyze_screenshot."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.analyze_screenshot(image_bytes, media_type)
        )


# Singleton instance
_analyzer: AIVisionAnalyzer | None = None


def get_ai_analyzer() -> AIVisionAnalyzer:
    """Get or create AI vision analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = AIVisionAnalyzer()
    return _analyzer
