import os
import tempfile

# 必须在导入任何 backend_python 模块之前设置：config.py 在 import 期解析
# DATABASE_URL，默认落在开发库 data/app.db，会把测试夹具泄进本地开发数据。
os.environ["DATABASE_URL"] = (
    f"sqlite:///{tempfile.mkdtemp(prefix='ai-interview-pytest-')}/app.db"
)

import pytest

from backend_python.security import reset_security_state

# 临时库自举 schema：此前部分测试隐式依赖本地 dev 库已建好的表
# （隔离修复后暴露），统一在会话启动时 create_all，全部测试自包含。
from backend_python.database import init_db

init_db()


@pytest.fixture(autouse=True)
def reset_security_state_between_tests() -> None:
    reset_security_state()
