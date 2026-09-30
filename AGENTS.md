# Video Automation Pipeline Architecture

## Goal
Automate the production of 9:16 Instagram Reels (1080x1920) split into two sections:
- Top (1080x960): Dynamic B-Roll timeline (minimal motion typography on light gray #f1f3f5 + AI cinematic images).
- Bottom (1080x960): Speaker raw footage (cut silences, color correction, noise reduction).
- Middle: Synchronized dynamic Persian subtitle overlay with high-contrast badge.

## Core Rules
1. Video Generation: Use Python + Playwright + Gemini Pro API for text/layout reasoning.
2. Styling: Strict viewport isolation (1080x960, overflow hidden). Never animate document root.
3. Fallback: Always implement robust retries and deterministic fallback routines for external APIs.
4. Python Env: Execute scripts strictly inside `./venv/Scripts/python.exe`.