#!/usr/bin/env bash

echo "Stopping demo processes (cloudflared, caddy, uvicorn, next dev)..."

pkill -f cloudflared >/dev/null 2>&1 || true
pkill -f caddy >/dev/null 2>&1 || true
pkill -f uvicorn >/dev/null 2>&1 || true
pkill -f "next dev" >/dev/null 2>&1 || true

echo "Done. If anything is still running, check:"
echo "  sudo ss -lptn 'sport = :3000'  # frontend"
echo "  sudo ss -lptn 'sport = :8000'  # API"
echo "  sudo ss -lptn 'sport = :8080'  # caddy"
