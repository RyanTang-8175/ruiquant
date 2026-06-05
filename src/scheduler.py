"""
定时任务调度器
收盘后自动跑数据管道，盘中自动抓新闻
Phase 2.1: 信息雷达分层抓取 — 免费源高频 + iFinD 精准低频
Phase 2.2: 研究审计自动回填
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def _is_trade_day() -> bool:
    """简单判断是否为交易日：周一至周五"""
    w = datetime.now().weekday()
    return w < 5  # 0=Mon ... 4=Fri


def _daily_data_pipeline():
    """每日数据管道：采集 -> 指标 -> 评分"""
    try:
        logger.info("开始每日数据管道...")
        from src.data.collector import DataCollector
        collector = DataCollector()
        collector.collect_all_stocks(days=5)
        collector.close()
        logger.info("数据采集完成")

        from src.data.indicators import IndicatorCalculator
        calc = IndicatorCalculator()
        calc.calculate_for_all()
        calc.close()
        logger.info("技术指标计算完成")

        from src.scoring.engine import ScoringEngine
        engine = ScoringEngine()
        results = engine.get_watchlist(min_score=0, limit=80)
        engine.close()
        logger.info(f"评分完成，保存 {len(results)} 条记录")

    except Exception as e:
        logger.error(f"每日数据管道失败: {e}")


def _fetch_news_job():
    """抓取新闻并分析情绪"""
    try:
        logger.info("开始抓取新闻...")
        from src.news.fetcher import fetch_all_news
        from src.news.analyzer import NewsAnalyzer

        news = fetch_all_news(limit=30)
        logger.info(f"抓取到 {len(news)} 条新闻")

        if news:
            analyzer = NewsAnalyzer()
            analyzed = analyzer.analyze_batch(news)
            saved = analyzer.save_news(analyzed)
            analyzer.close()
            logger.info(f"保存 {saved} 条新闻")

    except Exception as e:
        logger.error(f"新闻抓取失败: {e}")


def _backfill_job():
    """回填预测结果"""
    try:
        from src.prediction.predictor import PredictionEngine
        engine = PredictionEngine()
        engine.backfill_predictions()
        engine.close()
        logger.info("预测回填完成")
        from src.lab.backfill import backfill_pending_verifications
        result = backfill_pending_verifications()
        logger.info(f"实验室验证回填完成: {result}")
    except Exception as e:
        logger.error(f"预测回填失败: {e}")


# ═══════════════════════════════════════════════════════════
# Phase 2.1: 信息雷达分层抓取
# ═══════════════════════════════════════════════════════════

def _radar_hourly():
    """每小时：只抓免费源，不耗 iFinD"""
    logger.info("雷达每小时抓取开始（免费源）...")
    try:
        from src.news.radar import fetch_free_hotspots
        items = fetch_free_hotspots(limit=30)
        logger.info(f"雷达免费层抓取完成: {len(items)} 条")
    except Exception as e:
        logger.error(f"雷达每小时抓取失败: {e}")


def _radar_premarket():
    """交易日 08:33 + 收盘 15:33：补 iFinD 公告（低频精准）"""
    if not _is_trade_day():
        return
    logger.info("雷达盘前/盘后 iFinD 精准抓取开始...")
    try:
        from src.news.radar import fetch_radar_precision_layer
        items = fetch_radar_precision_layer()
        logger.info(f"雷达精准层抓取完成: {items} 条")
    except Exception as e:
        logger.error(f"雷达精准抓取失败: {e}")


def _radar_auto_backfill_audit():
    """每交易日 16:07 自动回填待验证的研究审计记录 — Phase 2.2"""
    if not _is_trade_day():
        return
    logger.info("研究审计自动回填开始...")
    try:
        from src.ai.chat import AIChat
        AIChat.auto_backfill()
        logger.info("研究审计自动回填完成")
    except Exception as e:
        logger.error(f"研究审计自动回填失败: {e}")


def create_scheduler() -> BackgroundScheduler:
    """创建并启动调度器"""
    scheduler = BackgroundScheduler()

    # 收盘后：数据管道（周一到周五 16:30）
    scheduler.add_job(
        _daily_data_pipeline, 'cron',
        hour=16, minute=30, day_of_week='mon-fri',
        id='daily_pipeline', name='每日数据管道',
        replace_existing=True
    )

    # 盘中：新闻抓取（周一到周五每30分钟）
    scheduler.add_job(
        _fetch_news_job, 'interval',
        minutes=30, day_of_week='mon-fri',
        id='news_fetch', name='新闻抓取',
        replace_existing=True
    )

    # 收盘后：预测回填（周一到周五 16:00）
    scheduler.add_job(
        _backfill_job, 'cron',
        hour=16, minute=0, day_of_week='mon-fri',
        id='backfill', name='预测回填',
        replace_existing=True
    )

    # Phase 2.1: 雷达每小时免费源抓取
    scheduler.add_job(
        _radar_hourly, 'cron',
        minute=3,
        id='radar_hourly', name='雷达免费每小时',
        replace_existing=True
    )

    # Phase 2.1: 雷达盘前/盘后 iFinD 精准抓取
    scheduler.add_job(
        _radar_premarket, 'cron',
        hour='8,15', minute=33, day_of_week='mon-fri',
        id='radar_premarket', name='雷达iFinD精准',
        replace_existing=True
    )

    # Phase 2.2: 研究审计自动回填
    scheduler.add_job(
        _radar_auto_backfill_audit, 'cron',
        hour=16, minute=7, day_of_week='mon-fri',
        id='audit_backfill', name='研究审计自动回填',
        replace_existing=True
    )

    scheduler.start()
    logger.info("调度器已启动（含雷达分层+审计自动回填）")
    return scheduler
