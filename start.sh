#!/bin/bash

# Arbitrage Bot Startup Script
# Run this on your Proxmox LXC container

set -e

echo "=========================================="
echo "  Arbitrage Bot Startup"
echo "=========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and fill in your credentials:"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Check if keys directory exists
if [ ! -d keys ]; then
    echo "Creating keys directory..."
    mkdir -p keys
    echo "WARNING: Place your kalshi_private_key.pem in ./keys/"
fi

# Check for Kalshi key
if [ ! -f keys/kalshi_private_key.pem ]; then
    echo "WARNING: keys/kalshi_private_key.pem not found"
    echo "Kalshi trading will not work without this key"
fi

# Create gluetun directory for VPN state
mkdir -p gluetun

echo ""
echo "Starting containers..."
echo ""

# Pull latest images
docker-compose pull vpn

# Build and start
docker-compose up -d --build

echo ""
echo "=========================================="
echo "  Waiting for VPN to connect..."
echo "=========================================="
sleep 10

# Check VPN status
echo ""
echo "Checking VPN connection..."
VPN_IP=$(docker exec gluetun-vpn wget -qO- https://ipinfo.io/ip 2>/dev/null || echo "FAILED")

if [ "$VPN_IP" = "FAILED" ]; then
    echo "ERROR: VPN not connected!"
    echo "Check logs: docker-compose logs vpn"
    exit 1
fi

echo "VPN Connected! IP: $VPN_IP"

# Get VPN location
VPN_COUNTRY=$(docker exec gluetun-vpn wget -qO- https://ipinfo.io/country 2>/dev/null || echo "Unknown")
echo "VPN Location: $VPN_COUNTRY"

echo ""
echo "=========================================="
echo "  Services Status"
echo "=========================================="
docker-compose ps

echo ""
echo "=========================================="
echo "  Access Points"
echo "=========================================="
echo "Frontend:  http://$(hostname -I | awk '{print $1}'):3000"
echo "API:       http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "View logs: docker-compose logs -f"
echo "Stop:      docker-compose down"
echo "=========================================="
