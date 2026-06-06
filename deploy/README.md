# AlphaEye 阿里云部署

## 首次接入 systemd

旧服务器可能通过 `nohup` 或手工命令运行 Streamlit，因此没有
`ruiquant.service`。首次执行以下命令把现有进程交给 systemd 管理：

```bash
cd /root/ruiquant
git pull --ff-only origin main

source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q

install -m 0644 deploy/ruiquant.service /etc/systemd/system/ruiquant.service
systemctl daemon-reload

# 首次迁移时停止占用 8501 的旧手工进程。
systemctl stop ruiquant 2>/dev/null || true
fuser -k 8501/tcp 2>/dev/null || true

systemctl enable --now ruiquant
systemctl status ruiquant --no-pager
curl -I http://127.0.0.1:8501
```

## 后续更新

systemd 安装完成后，每次更新只需要：

```bash
cd /root/ruiquant
git pull --ff-only origin main

source venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q

systemctl restart ruiquant
systemctl status ruiquant --no-pager
curl -I http://127.0.0.1:8501
```

## 查看日志

```bash
journalctl -u ruiquant -n 100 --no-pager
journalctl -u ruiquant -f
```

## 测试收集范围

仓库通过 `pytest.ini` 固定只收集 `tests/`。服务器根目录残留的历史
`test_*.py` 调试脚本不会再进入正式测试，避免其中写死的 Mac 路径阻断部署。
