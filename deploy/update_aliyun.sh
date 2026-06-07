#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${ALPHAEYE_REPO_DIR:-/root/ruiquant}"
BRANCH="${ALPHAEYE_BRANCH:-main}"
SERVICE="${ALPHAEYE_SERVICE:-ruiquant}"
PORT="${ALPHAEYE_PORT:-8501}"
VENV_DIR="${ALPHAEYE_VENV_DIR:-$REPO_DIR/venv}"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
TARGET_REF="origin/$BRANCH"
WORKTREE=""

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

cleanup() {
  if [[ -n "$WORKTREE" && -d "$WORKTREE" ]]; then
    git -C "$REPO_DIR" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if [[ $EUID -ne 0 ]]; then
  echo "请使用 root 运行：sudo bash deploy/update_aliyun.sh"
  exit 1
fi

cd "$REPO_DIR"

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "生产目录存在未提交的已跟踪改动，已停止更新，避免覆盖服务器文件。"
  git status --short
  exit 1
fi

log "拉取 GitHub 最新版本"
fetch_ok=0
for attempt in 1 2 3 4 5; do
  echo "fetch 尝试 $attempt/5"
  if timeout 180 git \
    -c http.version=HTTP/1.1 \
    -c http.lowSpeedLimit=1 \
    -c http.lowSpeedTime=120 \
    fetch --prune origin "$BRANCH"; then
    fetch_ok=1
    break
  fi
  sleep $((attempt * 3))
done

if [[ $fetch_ok -ne 1 ]]; then
  echo "GitHub 连续 5 次拉取失败，线上服务保持原版本运行。"
  exit 2
fi

target_commit="$(git rev-parse "$TARGET_REF")"
echo "目标版本：${target_commit:0:12}"

if [[ ! -x "$PYTHON" || ! -x "$PIP" ]]; then
  echo "虚拟环境不存在：$VENV_DIR"
  exit 3
fi

log "在隔离 worktree 安装依赖并验证目标版本"
WORKTREE="$(mktemp -d /tmp/alphaeye-release.XXXXXX)"
git worktree add --detach "$WORKTREE" "$target_commit"

timeout 300 "$PIP" install -r "$WORKTREE/requirements.txt"
"$PYTHON" -m compileall -q "$WORKTREE/app.py" "$WORKTREE/src" "$WORKTREE/tests"

(
  cd "$WORKTREE"
  env \
    -u IFIND_REFRESH_TOKEN \
    -u IFIND_ACCESS_TOKEN \
    ALPHAEYE_DATA_PROVIDER=open \
    IFIND_VERIFY_SSL=1 \
    PYTHONPATH=. \
    "$PYTHON" -m pytest -q
)

log "测试通过，快进生产目录"
git merge --ff-only "$target_commit"

log "安装并重启 systemd 服务"
install -m 0644 "$REPO_DIR/deploy/ruiquant.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null

if systemctl is-active --quiet "$SERVICE"; then
  systemctl restart "$SERVICE"
else
  fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
  systemctl start "$SERVICE"
fi

log "等待 AlphaEye 健康检查"
health_ok=0
for attempt in $(seq 1 60); do
  if curl -fsS --max-time 5 "http://127.0.0.1:$PORT/_stcore/health" | grep -q "ok"; then
    health_ok=1
    echo "健康检查通过（第 $attempt 秒）"
    break
  fi
  sleep 1
done

if [[ $health_ok -ne 1 ]]; then
  echo "AlphaEye 在 60 秒内未通过健康检查。"
  systemctl status "$SERVICE" --no-pager -l || true
  journalctl -u "$SERVICE" -n 120 --no-pager || true
  exit 4
fi

curl -fsSI --max-time 10 "http://127.0.0.1:$PORT" >/dev/null
systemctl status "$SERVICE" --no-pager -l

log "部署完成"
echo "当前版本：$(git rev-parse --short HEAD)"
echo "本机地址：http://127.0.0.1:$PORT"
