import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.config import settings
from app.router.github_hook import router as github_webhook_router
from app.router.test_endpoints import router as test_router
from app.services.task_manager import task_manager
from app.webhooks import router as webhook_router
from app.webhooks import setup_websocket_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 后台任务
async def background_tasks():
    """后台定时任务"""
    while True:
        try:
            # 每小时发送提醒
            await task_manager.send_daily_reminders()
            logger.info("Daily reminders sent")
            
            # 等待1小时
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Error in background tasks: {str(e)}")
            await asyncio.sleep(300)  # 出错时等待5分钟后重试

# 飞书长连接任务
async def feishu_websocket_task():
    """飞书长连接任务"""
    try:
        # 检查是否启用WebSocket
        # 如果遇到代理问题，可以通过环境变量禁用
        enable_websocket = settings.enable_websocket if hasattr(settings, 'enable_websocket') else False
        
        if not enable_websocket:
            logger.info("WebSocket客户端已禁用，使用Webhook模式")
            # 保持任务运行但不启动WebSocket
            while True:
                await asyncio.sleep(3600)
            return
        
        logger.info("Starting Feishu WebSocket client...")
        setup_websocket_client()
        # 保持任务运行
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
    except Exception as e:
        logger.error(f"Feishu WebSocket client error: {str(e)}")
        # 不要抛出异常，让服务继续运行
        logger.info("WebSocket连接失败，但服务将继续使用Webhook模式运行")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Application starting up...")
    
    # 启动后台任务
    background_task = asyncio.create_task(background_tasks())
    
    # 启动飞书长连接客户端（所有模式下都启动）
    websocket_task = asyncio.create_task(feishu_websocket_task())
    
    # 启动任务监测服务
    try:
        from app.services.task_monitor import task_monitor
        monitor_task = asyncio.create_task(task_monitor.start_monitoring())
        logger.info("Task monitoring service started")
    except Exception as e:
        logger.error(f"Failed to start task monitoring: {str(e)}")
        monitor_task = None
    
    # 启动调度器服务
    try:
        from app.services.scheduler import task_scheduler
        await task_scheduler.start()
        logger.info("Task scheduler service started")
    except Exception as e:
        logger.error(f"Failed to start task scheduler: {str(e)}")
    
    try:
        yield
    finally:
        # 关闭时执行
        logger.info("Application shutting down...")
        
        # 停止调度器
        try:
            from app.services.scheduler import task_scheduler
            await task_scheduler.stop()
            logger.info("Task scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping task scheduler: {str(e)}")
        
        # 停止任务监测
        if monitor_task:
            try:
                from app.services.task_monitor import task_monitor
                await task_monitor.stop_monitoring()
                monitor_task.cancel()
            except Exception as e:
                logger.error(f"Error stopping task monitor: {str(e)}")
        
        # 停止其他后台任务
        background_task.cancel()
        if websocket_task:
            websocket_task.cancel()
            
        # 等待任务取消
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        if websocket_task:
            try:
                await websocket_task
            except asyncio.CancelledError:
                pass
        if monitor_task:
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

# 创建FastAPI应用
app = FastAPI(
    title="Feishu Chat-Ops",
    description="智能飞书任务管理机器人",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler


# Let HTTPException through with its declared status code (401, 404, etc).
# Without this, the broad Exception handler below would convert every
# HTTPException into a 500.
@app.exception_handler(HTTPException)
async def passthrough_http_exception(request: Request, exc: HTTPException):
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# 注册路由
app.include_router(api_router)
app.include_router(webhook_router)
app.include_router(github_webhook_router)
app.include_router(test_router)

# 静态文件服务（如果需要前端界面）
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    logger.warning("Static directory not found, skipping static file serving")

# 根路径
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": "Feishu Chat-Ops",
        "version": "1.0.0",
        "description": "智能飞书任务管理机器人",
        "docs": "/docs",
        "health": "/api/v1/health",
        "webhooks": {
            "feishu": "/webhooks/feishu",
            "github": "/webhooks/github"
        }
    }

# 健康检查
@app.get("/health")
async def health():
    """简单健康检查"""
    return {"status": "healthy"}

# 启动配置
if __name__ == "__main__":
    logger.info(f"Starting server on {settings.server_host}:{settings.server_port}")
    
    # WebSocket客户端现在通过lifespan事件在所有模式下启动
    # 不再需要在这里单独启动
    
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        workers=1,
        log_level="info"
    )