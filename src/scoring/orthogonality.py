"""因子正交化检查: 新因子对旧因子回归取残差=真正的新信息"""

def check_redundancy(new_scores: dict, existing_scores: list[dict], threshold: float = 0.7) -> dict:
    """检查新因子与已有因子的相关性,超过阈值则提示冗余"""
    import math
    results = []
    for i, old in enumerate(existing_scores):
        new_vals = [new_scores.get(k, 0) for k in old]
        old_vals = [old.get(k, 0) for k in old]
        n = min(len(new_vals), len(old_vals))
        if n < 3:
            results.append({"factor": f"因子{i+1}", "r": 0.0, "r2": 0.0, "redundant": False})
            continue
        mx = sum(new_vals) / n
        my = sum(old_vals) / n
        sx = (sum((x-mx)**2 for x in new_vals)/(n-1))**0.5 if n > 1 else 1
        sy = (sum((y-my)**2 for y in old_vals)/(n-1))**0.5 if n > 1 else 1
        if sx < 1e-10 or sy < 1e-10:
            r = 0.0
        else:
            cov = sum((new_vals[i]-mx)*(old_vals[i]-my) for i in range(n))/(n-1)
            r = cov/(sx*sy)
        r2 = r**2
        results.append({
            "factor": f"因子{i+1}", "r": round(r, 3), "r2": round(r2, 3),
            "redundant": r2 > threshold,
            "advice": f"R²={r2:.3f}>{threshold}, 新增信息有限" if r2 > threshold else f"R²={r2:.3f}, 可独立贡献"
        })
    return {"redundant_count": sum(1 for r in results if r["redundant"]),
            "details": results,
            "summary": f"{sum(1 for r in results if r['redundant'])}/{len(results)} 个因子与现有因子高度相关"}
