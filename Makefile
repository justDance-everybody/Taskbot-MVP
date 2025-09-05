# Task Bot MVP - Makefile
# 支持开发、测试、部署等常用命令

.PHONY: help dev test test-unit test-integration test-coverage clean lint format security install docker-build docker-run setup

# 默认目标：显示帮助信息
help:
	@echo "📋 Task Bot MVP - 可用命令："
	@echo ""
	@echo "🔧 开发环境"
	@echo "  make setup           - 初始化开发环境"
	@echo "  make install         - 安装依赖"
	@echo "  make dev             - 启动开发服务器"
	@echo "  make dev-reload      - 启动带自动重载的开发服务器"
	@echo ""
	@echo "🧪 测试相关"
	@echo "  make test            - 运行所有测试"
	@echo "  make test-unit       - 运行单元测试"
	@echo "  make test-integration- 运行集成测试"
	@echo "  make test-coverage   - 运行测试并生成覆盖率报告"
	@echo "  make test-watch      - 监视文件变化并自动运行测试"
	@echo ""
	@echo "📏 代码质量"
	@echo "  make lint            - 运行代码检查"
	@echo "  make format          - 格式化代码"
	@echo "  make format-check    - 检查代码格式"
	@echo "  make security        - 安全扫描"
	@echo "  make type-check      - 类型检查"
	@echo ""
	@echo "🐳 Docker"
	@echo "  make docker-build    - 构建Docker镜像"
	@echo "  make docker-run      - 运行Docker容器"
	@echo "  make docker-test     - 在Docker中运行测试"
	@echo ""
	@echo "🧹 清理"
	@echo "  make clean           - 清理临时文件"
	@echo "  make clean-cache     - 清理Python缓存"

# Python和应用设置
PYTHON := python3
VENV := venv
APP_NAME := main:app
TEST_PATH := tests
SOURCE_PATH := app

# 检查虚拟环境
check-venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "❌ 虚拟环境不存在，请运行 'make setup'"; \
		exit 1; \
	fi

# 初始化开发环境
setup:
	@echo "🔧 初始化开发环境..."
	$(PYTHON) -m venv $(VENV)
	@echo "📦 安装依赖..."
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install -r requirements-dev.txt 2>/dev/null || echo "⚠️ requirements-dev.txt 不存在，跳过开发依赖"
	@echo "✅ 开发环境初始化完成"
	@echo "💡 激活虚拟环境: source $(VENV)/bin/activate"

# 安装依赖
install: check-venv
	@echo "📦 安装生产依赖..."
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

# 安装开发依赖
install-dev: install
	@echo "📦 安装开发依赖..."
	$(VENV)/bin/pip install pytest pytest-cov pytest-asyncio pytest-mock
	$(VENV)/bin/pip install black isort flake8 mypy bandit safety
	$(VENV)/bin/pip install uvicorn[standard] fastapi-cli

# 启动开发服务器
dev: check-venv
	@echo "🚀 启动开发服务器..."
	$(VENV)/bin/uvicorn $(APP_NAME) --host 0.0.0.0 --port 8000

# 启动带自动重载的开发服务器
dev-reload: check-venv
	@echo "🚀 启动开发服务器 (自动重载)..."
	$(VENV)/bin/uvicorn $(APP_NAME) --host 0.0.0.0 --port 8000 --reload

# 运行所有测试
test: check-venv
	@echo "🧪 运行所有测试..."
	@if [ -d "$(TEST_PATH)" ]; then \
		$(VENV)/bin/python -m pytest $(TEST_PATH) -v; \
	else \
		echo "⚠️ 测试目录不存在，创建基础测试结构..."; \
		$(MAKE) create-test-structure; \
		$(VENV)/bin/python -m pytest $(TEST_PATH) -v; \
	fi

# 运行单元测试
test-unit: check-venv
	@echo "🧪 运行单元测试..."
	$(VENV)/bin/python -m pytest $(TEST_PATH)/unit -v

# 运行集成测试
test-integration: check-venv
	@echo "🧪 运行集成测试..."
	$(VENV)/bin/python -m pytest $(TEST_PATH)/integration -v

# 运行测试并生成覆盖率报告
test-coverage: check-venv
	@echo "🧪 运行测试并生成覆盖率报告..."
	$(VENV)/bin/python -m pytest $(TEST_PATH) -v \
		--cov=$(SOURCE_PATH) \
		--cov-report=html \
		--cov-report=xml \
		--cov-report=term-missing \
		--cov-fail-under=80

# 监视文件变化并自动运行测试
test-watch: check-venv
	@echo "👀 监视文件变化并自动运行测试..."
	$(VENV)/bin/python -m pytest $(TEST_PATH) -v --tb=short -x --lf --ff

# 代码格式化
format: check-venv
	@echo "🎨 格式化代码..."
	$(VENV)/bin/black $(SOURCE_PATH) $(TEST_PATH) main.py
	$(VENV)/bin/isort $(SOURCE_PATH) $(TEST_PATH) main.py

# 检查代码格式
format-check: check-venv
	@echo "📏 检查代码格式..."
	$(VENV)/bin/black --check --diff $(SOURCE_PATH) $(TEST_PATH) main.py
	$(VENV)/bin/isort --check-only --diff $(SOURCE_PATH) $(TEST_PATH) main.py

# 代码检查
lint: check-venv
	@echo "🔍 运行代码检查..."
	$(VENV)/bin/flake8 $(SOURCE_PATH) $(TEST_PATH) main.py \
		--count \
		--select=E9,F63,F7,F82 \
		--show-source \
		--statistics
	$(VENV)/bin/flake8 $(SOURCE_PATH) $(TEST_PATH) main.py \
		--count \
		--exit-zero \
		--max-complexity=10 \
		--max-line-length=127 \
		--statistics

# 类型检查
type-check: check-venv
	@echo "🔍 运行类型检查..."
	$(VENV)/bin/mypy $(SOURCE_PATH) --ignore-missing-imports --no-strict-optional

# 安全扫描
security: check-venv
	@echo "🔒 运行安全扫描..."
	$(VENV)/bin/safety check -r requirements.txt
	$(VENV)/bin/bandit -r $(SOURCE_PATH) -f json -o bandit-report.json
	@echo "📄 安全扫描报告已生成: bandit-report.json"

# 创建测试目录结构
create-test-structure:
	@echo "📁 创建测试目录结构..."
	@mkdir -p $(TEST_PATH)/unit $(TEST_PATH)/integration $(TEST_PATH)/fixtures
	@touch $(TEST_PATH)/__init__.py
	@touch $(TEST_PATH)/unit/__init__.py
	@touch $(TEST_PATH)/integration/__init__.py
	@echo "# 单元测试配置" > $(TEST_PATH)/conftest.py
	@echo "import pytest" >> $(TEST_PATH)/conftest.py
	@echo "" >> $(TEST_PATH)/conftest.py
	@echo "@pytest.fixture" >> $(TEST_PATH)/conftest.py
	@echo "def test_client():" >> $(TEST_PATH)/conftest.py
	@echo "    \"\"\"测试客户端fixture\"\"\"" >> $(TEST_PATH)/conftest.py
	@echo "    from fastapi.testclient import TestClient" >> $(TEST_PATH)/conftest.py
	@echo "    from main import app" >> $(TEST_PATH)/conftest.py
	@echo "    return TestClient(app)" >> $(TEST_PATH)/conftest.py
	@echo "✅ 测试目录结构创建完成"

# Docker构建
docker-build:
	@echo "🐳 构建Docker镜像..."
	docker build -t task-bot:latest .
	@echo "✅ Docker镜像构建完成"

# 运行Docker容器
docker-run:
	@echo "🐳 运行Docker容器..."
	docker run -d \
		--name task-bot \
		-p 8000:8000 \
		--env-file .env \
		task-bot:latest
	@echo "✅ Docker容器启动完成，访问: http://localhost:8000"

# 在Docker中运行测试
docker-test:
	@echo "🐳 在Docker中运行测试..."
	docker build -t task-bot:test --target test .
	docker run --rm task-bot:test

# 停止Docker容器
docker-stop:
	@echo "🐳 停止Docker容器..."
	docker stop task-bot || true
	docker rm task-bot || true

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf bandit-report.json
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# 清理Python缓存
clean-cache: clean
	@echo "🧹 清理Python缓存..."
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

# 健康检查
health-check:
	@echo "🏥 检查服务健康状态..."
	@curl -f http://localhost:8000/health || echo "❌ 服务不可用"
	@curl -f http://localhost:8000/api/v1/health || echo "❌ API不可用"

# 查看服务日志
logs:
	@echo "📋 查看服务日志..."
	docker logs -f task-bot

# 生产部署前检查
pre-deploy: format-check lint type-check test security
	@echo "✅ 部署前检查完成"

# 快速开发流程
quick-start: setup install-dev create-test-structure
	@echo "🚀 快速开发环境已就绪！"
	@echo "💡 下一步："
	@echo "   source $(VENV)/bin/activate"
	@echo "   make dev-reload" 