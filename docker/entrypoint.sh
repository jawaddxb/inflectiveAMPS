#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Inflectiv Vertical Intelligence Node v1.0.0     ║"
echo "║  earn $INAI · power the intelligence economy     ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# Validate required env vars
if [ -z "$INFLECTIV_API_KEY" ]; then
  echo "⚠️  Warning: INFLECTIV_API_KEY not set — running in demo mode"
fi
if [ -z "$LLM_API_KEY" ]; then
  echo "⚠️  Warning: LLM_API_KEY not set — running in demo mode"
fi
if [ -z "$WALLET_ADDRESS" ]; then
  echo "⚠️  Warning: WALLET_ADDRESS not set — earnings will not be tracked"
fi

echo "🔧 Profile:  ${PROFILE}"
echo "🔑 API Key:  ${INFLECTIV_API_KEY:0:8}..."
echo "👛 Wallet:   ${WALLET_ADDRESS:0:10}..."
echo ""

# Copy registry to data dir if not exists
if [ ! -f "$DATA_DIR/node_registry.json" ]; then
  cp /app/nodes/node_registry.json $DATA_DIR/node_registry.json
  echo "📦 Registry initialised at $DATA_DIR"
fi

# Mode selection
case "${1:-run}" in
  run)
    echo "🚀 Starting node in continuous mode..."
    echo "   Profile: $PROFILE | Refresh: per schedule"
    echo ""
    exec python /app/nodes/node_runner.py --profile "$PROFILE" --continuous
    ;;
  once)
    echo "▶️  Running single cycle..."
    exec python /app/nodes/node_launcher.py --profile "$PROFILE"
    ;;
  list)
    exec python /app/nodes/node_launcher.py --list
    ;;
  leaderboard)
    exec python /app/nodes/leaderboard.py
    ;;
  shell)
    exec /bin/bash
    ;;
  *)
    echo "Usage: docker run inflectiv/node [run|once|list|leaderboard|shell]"
    exit 1
    ;;
esac
