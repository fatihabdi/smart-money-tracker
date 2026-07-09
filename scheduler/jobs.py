"""
Smart Money Tracker — Scheduled Jobs
Jadwal otomatis untuk scan dan pengiriman sinyal.

IDX (WIB):
  08:30 — Pre-Market Watchlist
  16:30 — Post-Market Report (swing trade)

US (WIB):
  19:30 — Pre-Market Analysis (US pre-market opens 08:30 ET)
  21:30 — Post-Open Signal (1 hour after US market open)
  00:30 — Mid-Session Signal (US market mid-session)
"""

import logging
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

import config

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def create_scheduler() -> AsyncIOScheduler:
    """Create scheduler dengan semua job otomatis."""
    global _scheduler

    tz = pytz.timezone(config.TIMEZONE)
    _scheduler = AsyncIOScheduler(timezone=tz)

    # ══════════════════════════════════════
    # 🇮🇩 IDX Jobs (WIB)
    # ══════════════════════════════════════

    # ── Pre-Market Watchlist: 08:30 WIB ──
    _scheduler.add_job(
        _job_pre_market,
        CronTrigger(
            hour=config.SCHEDULE_PRE_MARKET[0],
            minute=config.SCHEDULE_PRE_MARKET[1],
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="pre_market",
        name="IDX Pre-Market",
        misfire_grace_time=300,
    )

    # ── Post-Market Report: 16:30 WIB ──
    _scheduler.add_job(
        _job_post_market,
        CronTrigger(
            hour=config.SCHEDULE_POST_MARKET[0],
            minute=config.SCHEDULE_POST_MARKET[1],
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="post_market",
        name="IDX Post-Market (Swing)",
        misfire_grace_time=300,
    )

    # ══════════════════════════════════════
    # 🇺🇸 US Jobs (WIB)
    # ══════════════════════════════════════

    # ── US Pre-Market: 19:30 WIB ──
    _scheduler.add_job(
        _job_us_pre_market,
        CronTrigger(
            hour=config.US_SCHEDULE_PRE_MARKET[0],
            minute=config.US_SCHEDULE_PRE_MARKET[1],
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="us_pre_market",
        name="US Pre-Market",
        misfire_grace_time=300,
    )

    # ── US Post-Open Signal: 21:30 WIB ──
    _scheduler.add_job(
        _job_us_post_open,
        CronTrigger(
            hour=config.US_SCHEDULE_POST_OPEN[0],
            minute=config.US_SCHEDULE_POST_OPEN[1],
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="us_post_open",
        name="US Post-Open Signal",
        misfire_grace_time=300,
    )

    # ── US Mid-Session Signal: 00:30 WIB ──
    _scheduler.add_job(
        _job_us_mid_session,
        CronTrigger(
            hour=config.US_SCHEDULE_MID_SESSION[0],
            minute=config.US_SCHEDULE_MID_SESSION[1],
            day_of_week="mon-fri",
            timezone=tz,
        ),
        id="us_mid_session",
        name="US Mid-Session Signal",
        misfire_grace_time=300,
    )

    logger.info(
        f"Scheduler created (WIB). "
        f"IDX: {config.SCHEDULE_PRE_MARKET[0]:02d}:{config.SCHEDULE_PRE_MARKET[1]:02d} & "
        f"{config.SCHEDULE_POST_MARKET[0]:02d}:{config.SCHEDULE_POST_MARKET[1]:02d} | "
        f"US: {config.US_SCHEDULE_PRE_MARKET[0]:02d}:{config.US_SCHEDULE_PRE_MARKET[1]:02d}, "
        f"{config.US_SCHEDULE_POST_OPEN[0]:02d}:{config.US_SCHEDULE_POST_OPEN[1]:02d}, "
        f"{config.US_SCHEDULE_MID_SESSION[0]:02d}:{config.US_SCHEDULE_MID_SESSION[1]:02d}"
    )

    return _scheduler


def start_scheduler():
    global _scheduler
    if _scheduler and not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


# ══════════════════════════════════════
# 🇮🇩 IDX Job Wrappers
# ══════════════════════════════════════

async def _job_pre_market():
    logger.info("=" * 50)
    logger.info("SCHEDULED JOB: IDX Pre-Market")
    logger.info("=" * 50)
    try:
        from bot.telegram_bot import send_pre_market
        await send_pre_market()
    except Exception as e:
        logger.error(f"Error in IDX pre-market job: {e}", exc_info=True)
        try:
            from bot.telegram_bot import send_message
            await send_message(f"❌ Error IDX Pre-Market: {str(e)[:100]}")
        except Exception:
            pass


async def _job_post_market():
    logger.info("=" * 50)
    logger.info("SCHEDULED JOB: IDX Post-Market (Swing)")
    logger.info("=" * 50)
    try:
        from bot.telegram_bot import send_post_market
        await send_post_market()
    except Exception as e:
        logger.error(f"Error in IDX post-market job: {e}", exc_info=True)
        try:
            from bot.telegram_bot import send_message
            await send_message(f"❌ Error IDX Post-Market: {str(e)[:100]}")
        except Exception:
            pass


# ══════════════════════════════════════
# 🇺🇸 US Job Wrappers
# ══════════════════════════════════════

async def _job_us_pre_market():
    """US Pre-Market signal: 19:30 WIB (08:30 ET)."""
    logger.info("=" * 50)
    logger.info("SCHEDULED JOB: US Pre-Market")
    logger.info("=" * 50)
    try:
        from bot.telegram_bot import send_us_pre_market
        await send_us_pre_market()
    except Exception as e:
        logger.error(f"Error in US pre-market job: {e}", exc_info=True)
        try:
            from bot.telegram_bot import send_message
            await send_message(f"❌ Error US Pre-Market: {str(e)[:100]}")
        except Exception:
            pass


async def _job_us_post_open():
    """US Post-Open Signal: 21:30 WIB (10:30 ET) — 1 hour after market open."""
    logger.info("=" * 50)
    logger.info("SCHEDULED JOB: US Post-Open Signal")
    logger.info("=" * 50)
    try:
        from bot.telegram_bot import send_us_post_open
        await send_us_post_open()
    except Exception as e:
        logger.error(f"Error in US post-open job: {e}", exc_info=True)
        try:
            from bot.telegram_bot import send_message
            await send_message(f"❌ Error US Post-Open: {str(e)[:100]}")
        except Exception:
            pass


async def _job_us_mid_session():
    """US Mid-Session Signal: 00:30 WIB (13:30 ET) — mid-day check."""
    logger.info("=" * 50)
    logger.info("SCHEDULED JOB: US Mid-Session Signal")
    logger.info("=" * 50)
    try:
        from bot.telegram_bot import send_us_mid_session
        await send_us_mid_session()
    except Exception as e:
        logger.error(f"Error in US mid-session job: {e}", exc_info=True)
        try:
            from bot.telegram_bot import send_message
            await send_message(f"❌ Error US Mid-Session: {str(e)[:100]}")
        except Exception:
            pass


# ══════════════════════════════════════
# Info
# ══════════════════════════════════════

def get_next_run_times() -> dict:
    """Return info waktu run berikutnya untuk setiap job."""
    if not _scheduler:
        return {}

    jobs = {}
    try:
        for job in _scheduler.get_jobs():
            try:
                # APScheduler 3.x: job.next_run_time
                next_run = getattr(job, 'next_run_time', None)
                if next_run:
                    jobs[job.id] = {
                        "name": job.name,
                        "next_run": next_run.strftime("%d %b %Y %H:%M WIB"),
                    }
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Error getting next run times: {e}")
    return jobs
