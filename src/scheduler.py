"""
定时任务调度器
收盘后自动跑数据管道，盘中自动抓新闻
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


def _daily_data_pipeline():
    """每日数据管道：采集 → 指标 → 评分"""
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
        saved = engine.rescore_all()
        engine.close()
        logger.info(f"评分完成，保存 {saved} 条记录")

    except Exception as e:
        logger.error(f"每日数据管道失败: {e}")


def _fetch_news_job():
    """抓取新闻并分析情绪"""
    try:
        logger.info("开始抓取新闻...")
        from src.news.fetcher import NewsFetcher
        from src.news.analyzer import NewsAnalyzer

        fetcher = NewsFetcher()
        news = fetcher.fetch_all(limit_per_source=15)
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
    except Exception as e:
        logger.error(f"预测回填失败: {e}")


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

    scheduler.start()
    logger.info("调度器已启动")
    return scheduler
