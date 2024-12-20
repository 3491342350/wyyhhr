from typing import Tuple, Dict

from signer import Signer
from extra_task import ExtraTask

class MusicPartnerBot:
    def __init__(self, config, logger, session):
        self.config = config
        self.logger = logger
        self.session = session
        self.api = {
            "user_info": "https://music.163.com/api/nuser/account/get",
            "task_data": "https://interface.music.163.com/api/music/partner/daily/task/get"
        }

    def run(self) -> bool:
        try:
            self._verify_user()
            
            # 处理基础评分任务
            complete, task_data = self._get_daily_tasks()
            if not complete:
                self._process_tasks(task_data)
            
            # 处理额外评分任务
            extra_task = ExtraTask(self.session, self.logger)
            extra_task.process_extra_tasks(task_data["id"])
            
            return True
        except Exception as e:
            self.logger.error(f"执行失败: {str(e)}")
            return False

    def _verify_user(self) -> None:
        """验证用户信息"""
        try:
            self.logger.info(f"开始验证用户信息...")
            response = self.session.get(url=self.api["user_info"])
            
            # 打印响应状态码
            self.logger.info(f"API响应状态码: {response.status_code}")
            response_json = response.json()
            
            profile = response_json.get("profile")
            if profile:
                self.logger.info(f'用户名: {profile["nickname"]}')
            else:
                error_msg = response_json.get("msg", "未知错误")
                self.logger.error(f"获取用户信息失败: {error_msg}")
                raise RuntimeError("用户验证失败")
            
        except Exception as e:
            self.logger.error(f"验证用户信息时发生错误: {str(e)}")
            raise RuntimeError("用户验证失败")

    def _get_daily_tasks(self) -> Tuple[bool, Dict]:
        """获取每日任务"""
        response = self.session.get(url=self.api["task_data"]).json()
        task_data = response.get("data", {})
        
        count = task_data.get("count", 0)
        completed_count = task_data.get("completedCount", 0)
        today_task = f"[{completed_count}/{count}]"
        complete = count == completed_count
        
        self.logger.info(f'今日任务：{"已完成" if complete else "未完成"}{today_task}')
        return complete, task_data

    def _process_tasks(self, task_data: Dict) -> None:
        """处理未完成的任务"""
        self.logger.info("开始评分...")
        signer = Signer(self.session, task_data["id"], self.logger)
        
        for task in task_data.get("works", []):
            work = task["work"]
            if task["completed"]:
                self.logger.info(f'{work["name"]}「{work["authorName"]}」已有评分：{int(task["score"])}分')
            else:
                signer.sign(work)
