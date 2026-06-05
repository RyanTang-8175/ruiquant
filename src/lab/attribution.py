"""
短线实验室三类归因 —— 策略/AI/用户执行
把验证记录拆成三个维度：策略是否有效、AI判断是否准确、用户是否按计划执行
"""

from collections import defaultdict


def compute_attribution() -> dict:
    try:
        from src.memory.analysis_memory import AnalysisMemory
        with AnalysisMemory() as memory:
            verifications = memory.get_verification_results()
        if not verifications:
            return _empty_result()

        return {
            "total": len(verifications),
            "strategy": _strategy_attribution(verifications),
            "ai": _ai_attribution(verifications),
            "user": _user_attribution(verifications),
        }
    except Exception as e:
        return {"error": str(e)[:100], "total": 0}


def _strategy_attribution(verifications: list) -> dict:
    stats = defaultdict(lambda: {"total": 0, "hit_2pct": 0, "by_strategy": defaultdict(lambda: {"total": 0, "hit_2pct": 0})})

    for v in verifications:
        source = v.get("source_type", "unknown")
        sa = v.get("strategy_name") or source
        stats[source]["total"] += 1
        stats[source]["by_strategy"][sa]["total"] += 1
        for bf in v.get("backfills", []):
            if bf.get("hit_2pct"):
                stats[source]["hit_2pct"] += 1
                stats[source]["by_strategy"][sa]["hit_2pct"] += 1

    result = []
    for source, data in stats.items():
        by_strat = [{"name": n, "total": d["total"],
                      "hit_rate": round(d["hit_2pct"] / max(d["total"], 1) * 100, 1)}
                    for n, d in data.get("by_strategy", {}).items()]
        by_strat.sort(key=lambda x: x["hit_rate"], reverse=True)
        result.append({
            "source": source,
            "total": data["total"],
            "hit_rate": round(data["hit_2pct"] / max(data["total"], 1) * 100, 1),
            "by_strategy": by_strat[:5],
        })
    result.sort(key=lambda x: x["total"], reverse=True)

    best = max(
        ((n, d["hit_2pct"] / max(d["total"], 1) * 100, d["total"])
         for source, data in stats.items()
         for n, d in data.get("by_strategy", {}).items() if d["total"] >= 2),
        key=lambda x: x[1], default=("数据不足", 0, 0))

    return {
        "by_source": result,
        "best_strategy": {"name": best[0], "total": best[2], "hit_rate": round(best[1], 1)},
        "total_verified": len(verifications),
    }


def _ai_attribution(verifications: list) -> dict:
    ai_v = [v for v in verifications if v.get("source_type") == "ai_prediction"]
    if not ai_v:
        return {"total": 0, "message": "暂无 AI 来源的验证记录"}

    hit = 0; total_bf = 0; returns = []
    for v in ai_v:
        for bf in v.get("backfills", []):
            total_bf += 1
            if bf.get("hit_2pct"): hit += 1
            r = bf.get("hold_1d")
            if r is not None: returns.append(r)

    rate = hit / max(total_bf, 1) * 100
    avg_r = sum(returns) / max(len(returns), 1)
    verdict = "AI 方向可参考" if rate >= 60 and avg_r > 0 else \
              "有一定参考价值" if rate >= 40 else "准确率偏低，建议加策略/风控权重"

    return {"total": len(ai_v), "hit_rate": round(rate, 1),
            "avg_1d_return": round(avg_r, 2), "verdict": verdict}


def _user_attribution(verifications: list) -> dict:
    fb = [v for v in verifications if v.get("user_action")]
    if not fb:
        return {"total": 0, "message": "暂无用户反馈数据"}

    good_actions = {"按计划操作"}
    bad_actions = {"没止损", "追高", "反向操作", "提前卖出", "没止盈"}

    good = sum(1 for v in fb if v.get("user_action") in good_actions)
    bad = sum(1 for v in fb if v.get("user_action") in bad_actions)
    discipline = round(good / max(len(fb), 1) * 100, 1)

    bad_counts = defaultdict(int)
    for v in fb:
        a = v.get("user_action", "")
        if a in bad_actions: bad_counts[a] += 1

    verdict = f"纪律良好({discipline:.0f}%)" if discipline >= 80 else \
              f"纪律一般({discipline:.0f}%)，最大问题是未按计划执行止损" if discipline >= 50 else \
              f"纪律较差({discipline:.0f}%)，建议先做好止损再追收益"

    return {
        "total": len(fb), "disciplined": good, "undisciplined": bad,
        "discipline_rate": discipline,
        "top_bad_behaviors": sorted(bad_counts.items(), key=lambda x: x[1], reverse=True)[:3],
        "verdict": verdict,
    }


def _empty_result() -> dict:
    return {
        "total": 0,
        "strategy": {"total_verified": 0, "best_strategy": {"name": "暂无数据"}},
        "ai": {"total": 0, "message": "暂无 AI 来源的验证记录"},
        "user": {"total": 0, "message": "暂无用户反馈数据"},
    }
