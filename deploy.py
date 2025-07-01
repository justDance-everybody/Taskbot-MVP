#!/usr/bin/env python3
"""
部署脚本 - 用于自动化部署Feishu Chat-Ops应用

支持的部署方式：
1. 本地开发环境
2. Docker容器
3. Docker Compose
4. 生产环境

使用方法：
    python deploy.py --mode local
    python deploy.py --mode docker
    python deploy.py --mode compose
    python deploy.py --mode production
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentManager:
    """部署管理器"""
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.env_file = self.project_root / '.env'
        self.env_example = self.project_root / '.env.example'
        
    def check_prerequisites(self) -> bool:
        """检查部署前置条件"""
        logger.info("检查部署前置条件...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            logger.error("需要Python 3.8或更高版本")
            return False
        
        # 检查必要文件
        required_files = [
            'main.py',
            'requirements.txt',
            '.env.example'
        ]
        
        for file in required_files:
            if not (self.project_root / file).exists():
                logger.error(f"缺少必要文件: {file}")
                return False
        
        logger.info("前置条件检查通过")
        return True
    
    def setup_environment(self) -> bool:
        """设置环境变量"""
        logger.info("设置环境变量...")
        
        if not self.env_file.exists():
            if self.env_example.exists():
                logger.info("复制.env.example到.env")
                shutil.copy2(self.env_example, self.env_file)
                logger.warning("请编辑.env文件并填入正确的配置值")
            else:
                logger.error("找不到.env.example文件")
                return False
        
        return True
    
    def install_dependencies(self) -> bool:
        """安装依赖"""
        logger.info("安装Python依赖...")
        
        try:
            # 升级pip
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], 
                         check=True, capture_output=True)
            
            # 安装依赖
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                         check=True, capture_output=True, cwd=self.project_root)
            
            logger.info("依赖安装完成")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"依赖安装失败: {e}")
            return False
    
    def run_tests(self) -> bool:
        """运行测试"""
        logger.info("运行测试...")
        
        try:
            # 检查是否安装了pytest
            subprocess.run([sys.executable, '-m', 'pytest', '--version'], 
                         check=True, capture_output=True)
            
            # 运行测试
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', 'tests/', '-v'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("所有测试通过")
                return True
            else:
                logger.warning(f"测试失败: {result.stdout}\n{result.stderr}")
                return False
                
        except subprocess.CalledProcessError:
            logger.warning("pytest未安装，跳过测试")
            return True
    
    def deploy_local(self) -> bool:
        """本地部署"""
        logger.info("开始本地部署...")
        
        if not self.check_prerequisites():
            return False
        
        if not self.setup_environment():
            return False
        
        if not self.install_dependencies():
            return False
        
        if not self.run_tests():
            logger.warning("测试未通过，但继续部署")
        
        logger.info("本地部署完成")
        logger.info("启动应用: python main.py")
        return True
    
    def deploy_docker(self) -> bool:
        """Docker部署"""
        logger.info("开始Docker部署...")
        
        if not self.check_prerequisites():
            return False
        
        if not self.setup_environment():
            return False
        
        # 检查Docker
        try:
            subprocess.run(['docker', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Docker未安装或不可用")
            return False
        
        try:
            # 构建Docker镜像
            logger.info("构建Docker镜像...")
            subprocess.run(
                ['docker', 'build', '-t', 'feishu-chatops', '.'],
                check=True,
                cwd=self.project_root
            )
            
            logger.info("Docker镜像构建完成")
            logger.info("启动容器: docker run -p 8000:8000 --env-file .env feishu-chatops")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker构建失败: {e}")
            return False
    
    def deploy_compose(self) -> bool:
        """Docker Compose部署"""
        logger.info("开始Docker Compose部署...")
        
        if not self.check_prerequisites():
            return False
        
        if not self.setup_environment():
            return False
        
        # 检查Docker Compose
        try:
            subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['docker', 'compose', 'version'], check=True, capture_output=True)
                compose_cmd = ['docker', 'compose']
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("Docker Compose未安装或不可用")
                return False
        else:
            compose_cmd = ['docker-compose']
        
        try:
            # 启动服务
            logger.info("启动Docker Compose服务...")
            subprocess.run(
                compose_cmd + ['up', '--build', '-d'],
                check=True,
                cwd=self.project_root
            )
            
            logger.info("Docker Compose部署完成")
            logger.info("查看状态: docker-compose ps")
            logger.info("查看日志: docker-compose logs -f")
            logger.info("停止服务: docker-compose down")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker Compose部署失败: {e}")
            return False
    
    def deploy_production(self) -> bool:
        """生产环境部署"""
        logger.info("开始生产环境部署...")
        
        if not self.check_prerequisites():
            return False
        
        if not self.setup_environment():
            return False
        
        if not self.install_dependencies():
            return False
        
        if not self.run_tests():
            logger.error("测试未通过，停止生产环境部署")
            return False
        
        # 生产环境特定配置
        logger.info("配置生产环境...")
        
        # 创建日志目录
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # 创建systemd服务文件（如果在Linux上）
        if sys.platform.startswith('linux'):
            self.create_systemd_service()
        
        logger.info("生产环境部署完成")
        logger.info("启动应用: python main.py")
        logger.info("建议使用进程管理器如supervisor或systemd管理应用")
        return True
    
    def create_systemd_service(self):
        """创建systemd服务文件"""
        service_content = f"""[Unit]
Description=Feishu Chat-Ops Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory={self.project_root}
Environment=PATH={sys.executable}
ExecStart={sys.executable} main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = Path('/tmp/feishu-chatops.service')
        service_file.write_text(service_content)
        
        logger.info(f"systemd服务文件已创建: {service_file}")
        logger.info("安装服务: sudo cp /tmp/feishu-chatops.service /etc/systemd/system/")
        logger.info("启用服务: sudo systemctl enable feishu-chatops")
        logger.info("启动服务: sudo systemctl start feishu-chatops")
    
    def health_check(self) -> bool:
        """健康检查"""
        logger.info("执行健康检查...")
        
        try:
            import requests
            response = requests.get('http://localhost:8000/health', timeout=10)
            if response.status_code == 200:
                logger.info("应用健康检查通过")
                return True
            else:
                logger.error(f"健康检查失败: HTTP {response.status_code}")
                return False
        except ImportError:
            logger.warning("requests库未安装，跳过健康检查")
            return True
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        logger.info("清理临时文件...")
        
        # 清理Python缓存
        for root, dirs, files in os.walk(self.project_root):
            for dir_name in dirs[:]:
                if dir_name == '__pycache__':
                    shutil.rmtree(os.path.join(root, dir_name))
                    dirs.remove(dir_name)
        
        # 清理.pyc文件
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))
        
        logger.info("清理完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Feishu Chat-Ops 部署脚本')
    parser.add_argument(
        '--mode',
        choices=['local', 'docker', 'compose', 'production'],
        required=True,
        help='部署模式'
    )
    parser.add_argument(
        '--project-root',
        help='项目根目录路径',
        default=None
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='跳过测试'
    )
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='部署后清理临时文件'
    )
    
    args = parser.parse_args()
    
    # 创建部署管理器
    deployer = DeploymentManager(args.project_root)
    
    # 根据模式执行部署
    success = False
    
    if args.mode == 'local':
        success = deployer.deploy_local()
    elif args.mode == 'docker':
        success = deployer.deploy_docker()
    elif args.mode == 'compose':
        success = deployer.deploy_compose()
    elif args.mode == 'production':
        success = deployer.deploy_production()
    
    # 清理
    if args.cleanup:
        deployer.cleanup()
    
    # 输出结果
    if success:
        logger.info(f"🎉 {args.mode}模式部署成功！")
        
        # 显示下一步操作
        if args.mode == 'local':
            print("\n下一步操作:")
            print("1. 编辑 .env 文件，填入正确的配置")
            print("2. 运行: python main.py")
            print("3. 访问: http://localhost:8000")
        elif args.mode == 'docker':
            print("\n下一步操作:")
            print("1. 编辑 .env 文件，填入正确的配置")
            print("2. 运行: docker run -p 8000:8000 --env-file .env feishu-chatops")
            print("3. 访问: http://localhost:8000")
        elif args.mode == 'compose':
            print("\n下一步操作:")
            print("1. 编辑 .env 文件，填入正确的配置")
            print("2. 服务已启动，访问: http://localhost:8000")
            print("3. 查看日志: docker-compose logs -f")
        elif args.mode == 'production':
            print("\n下一步操作:")
            print("1. 编辑 .env 文件，填入正确的配置")
            print("2. 配置反向代理（如Nginx）")
            print("3. 设置SSL证书")
            print("4. 配置监控和日志")
        
        sys.exit(0)
    else:
        logger.error(f"❌ {args.mode}模式部署失败！")
        sys.exit(1)

if __name__ == '__main__':
    main()