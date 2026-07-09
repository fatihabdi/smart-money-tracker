"""
Smart Money Tracker — Main Entry Point
Memulai database, Telegram bot, dan scheduler.
"""

import logging
import asyncio
import sys
import argparse

import config
from utils.helpers import setup_logging
from database.db import init_db, close_db
from bot.telegram_bot import create_bot, run_full_scan
from scheduler.jobs import create_scheduler, start_scheduler

logger = logging.getLogger(__name__)


async def main():
    """Main function."""
    # 1. Parse arguments
    parser = argparse.ArgumentParser(description="AI Smart Money Tracker Bot")
    parser.add_argument("--test-scan", action="store_true", help="Run full scan immediately and exit")
    args = parser.parse_args()

    # 2. Setup Logging
    setup_logging()
    logger.info("Starting Smart Money Tracker...")

    # 3. Setup Database
    await init_db()

    # Jika hanya test scan
    if args.test_scan:
        logger.info("Running test scan...")
        signals = await run_full_scan()
        logger.info(f"Test scan finished. Found {len(signals)} signals.")
        await close_db()
        return

    # 4. Check Config
    if not config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        sys.exit(1)
    
    if not config.TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID is not set. Bot will not respond to anyone.")

    if not config.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set. AI analysis will use fallback.")

    try:
        # 5. Start Scheduler
        scheduler = create_scheduler()
        start_scheduler()

        # 6. Start Bot (blocking)
        logger.info("Starting Telegram Bot...")
        app = create_bot()
        
        # Run bot polling (ini akan memblokir sampai stop)
        # Gunakan await app.run_polling() untuk versi > 20
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        logger.info("Bot is running. Press Ctrl+C to stop.")
        
        # Keep alive
        stop_event = asyncio.Event()
        await stop_event.wait()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down...")
        try:
            if 'app' in locals() and app.updater:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
        except Exception:
            pass
        
        from scheduler.jobs import stop_scheduler
        stop_scheduler()
        
        await close_db()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    # Windows asyncio workaround
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown by user.")
