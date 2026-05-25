"""Hermes 进化日志 — 路径配置"""
import os

HOME = os.environ["HOME"]

# 项目路径
PROJECT_DIR = os.path.join(HOME, "projects", "hermes-evolution")
DATA_FILE = os.path.join(PROJECT_DIR, "data", "evolution.json")
HTML_FILE = os.path.join(PROJECT_DIR, "index.html")
VERSION_FILE = os.path.join(PROJECT_DIR, "VERSION")

# 数据采集目标路径
HERMES_SKILLS = os.path.join(HOME, ".hermes", "skills")
WIKI_DIR = os.path.join(HOME, "wiki")
STATE_DB = os.path.join(HOME, ".hermes", "state.db")

# 需要检查运行状态的服务列表
SERVICES = ["hermes-gateway", "hermes-dashboard", "hermes-web-ui"]

# 飞书推送配置
FEISHU_CHAT_ID = "oc_36d64f1bf4f4e4492295b4a59eb55dc5"
LARK_CLI = os.path.expanduser("~/.local/bin/lark-cli")
