"""
世界时钟模块
============
实现游戏内时间系统，支持时间缩放和持久化

时间规则：
- 现实1分钟 = 游戏内 time_scale 分钟（默认10分钟）
- 游戏日从 06:00 开始（日出）
- 游戏夜从 22:00 开始（入夜）

持久化规则：
- 服务器关闭期间，世界时间冻结（智能体无法活动）
- 服务器重启后，从上次保存的世界时间继续
- 首次启动时，从"第1天 08:00"开始

使用示例：
    clock = WorldClock(time_scale=10)
    clock.start()
    
    # 获取游戏内当前时间
    game_time = clock.now()
    
    # 检查是否是白天
    if clock.is_daytime():
        print("现在是白天")
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.core.events import Event, EventType, event_bus


class TimeOfDay(str, Enum):
    """一天中的时间段"""
    DAWN = "dawn"        # 黎明 (05:00-07:00)
    MORNING = "morning"  # 上午 (07:00-12:00)
    NOON = "noon"        # 中午 (12:00-14:00)
    AFTERNOON = "afternoon"  # 下午 (14:00-18:00)
    EVENING = "evening"  # 傍晚 (18:00-20:00)
    NIGHT = "night"      # 夜晚 (20:00-05:00)


@dataclass
class WorldTime:
    """
    世界时间数据类
    
    Attributes:
        datetime: 游戏内日期时间
        day: 游戏内天数（从第1天开始）
        time_of_day: 当前时间段
        is_daytime: 是否是白天
    """
    datetime: datetime
    day: int
    time_of_day: TimeOfDay
    is_daytime: bool
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "datetime": self.datetime.isoformat(),
            "day": self.day,
            "time_of_day": self.time_of_day.value,
            "is_daytime": self.is_daytime,
            "formatted_time": self.datetime.strftime("%H:%M"),
            "formatted_date": f"第{self.day}天",
        }


class WorldClock:
    """
    世界时钟
    
    负责管理游戏内时间，支持时间缩放和持久化
    
    设计理念：
    - 服务器关闭期间，世界时间冻结（因为智能体需要LLM驱动，无法离线活动）
    - 重启后从上次保存的世界时间继续
    - 首次启动创建新世界，从第1天08:00开始
    
    Attributes:
        time_scale: 时间缩放比例
        start_real_time: 现实世界启动时间
        start_world_time: 游戏世界初始时间（创世时间）
        current_world_time: 当前世界时间（从持久化加载或计算）
        is_running: 时钟是否运行中
        is_paused: 是否暂停
    """
    
    # 持久化文件路径
    SAVE_FILE = Path("data/world_state.json")
    
    def __init__(
        self,
        time_scale: int = settings.time_scale,
        start_world_time: Optional[datetime] = None,
    ):
        """
        初始化世界时钟
        
        Args:
            time_scale: 时间缩放比例，默认从配置读取
            start_world_time: 游戏世界初始时间，默认为第1天08:00
        """
        self.time_scale = time_scale
        self.is_running: bool = False
        self.is_paused: bool = False
        self._pause_time: Optional[datetime] = None
        self._accumulated_pause: timedelta = timedelta()
        
        # 上一次tick的时间（用于检测时间段变化）
        self._last_tick_time_of_day: Optional[TimeOfDay] = None
        
        # 尝试从文件加载世界状态
        loaded = self._load_from_file()
        
        if loaded:
            # 从持久化恢复
            logger.info(f"世界时钟从存档恢复: 第{self.get_world_time().day}天 {self.get_world_time().datetime.strftime('%H:%M')}")
        else:
            # 首次启动，创建新世界
            self.start_real_time: datetime = datetime.now(timezone.utc)
            
            if start_world_time is None:
                # 创世时间：第1天 08:00
                # 使用固定的起始日期，确保"天数"计算一致
                self.start_world_time = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
            else:
                self.start_world_time = start_world_time
            
            logger.info(
                f"新世界创建: time_scale={time_scale}, "
                f"start_world_time={self.start_world_time.isoformat()}"
            )
            
            # 立即保存初始状态
            self._save_to_file()
    
    # ==================
    # 持久化方法
    # ==================
    
    def _save_to_file(self) -> None:
        """保存世界时钟状态到文件"""
        try:
            self.SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存当前状态
            data = {
                "version": "1.0",
                "time_scale": self.time_scale,
                "start_world_time": self.start_world_time.isoformat(),
                "start_real_time": self.start_real_time.isoformat(),
                "accumulated_pause_seconds": self._accumulated_pause.total_seconds(),
                "is_paused": self.is_paused,
                # 保存当前世界时间，用于重启后恢复
                "saved_world_time": self.now().isoformat(),
                "saved_real_time": datetime.now(timezone.utc).isoformat(),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            
            with open(self.SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"世界状态已保存: 第{self.get_world_time().day}天")
        except Exception as e:
            logger.error(f"保存世界状态失败: {e}")
    
    def _load_from_file(self) -> bool:
        """
        从文件加载世界时钟状态
        
        Returns:
            是否成功加载
        """
        if not self.SAVE_FILE.exists():
            logger.info("无已保存的世界状态，将创建新世界")
            return False
        
        try:
            with open(self.SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 恢复状态
            self.time_scale = data.get("time_scale", settings.time_scale)
            self.start_world_time = datetime.fromisoformat(data["start_world_time"])
            
            # 关键：恢复时间连续性
            # 思路：上次保存时的世界时间 + 现在重启，需要让时间从上次继续
            saved_world_time = datetime.fromisoformat(data["saved_world_time"])
            saved_real_time = datetime.fromisoformat(data["saved_real_time"])
            
            # 计算：如果从 saved_world_time 继续，start_real_time 应该是多少？
            # saved_world_time = start_world_time + (saved_real_time - start_real_time) * time_scale
            # 反推：start_real_time = saved_real_time - (saved_world_time - start_world_time) / time_scale
            # 但更简单的方式：调整 start_real_time，使得 now() 返回 saved_world_time
            
            # 当前现实时间
            current_real_time = datetime.now(timezone.utc)
            
            # 设置 start_real_time，使得计算出的世界时间 = saved_world_time
            # world_delta = (current_real_time - start_real_time) * time_scale
            # saved_world_time = start_world_time + world_delta
            # => world_delta = saved_world_time - start_world_time
            # => current_real_time - start_real_time = world_delta / time_scale
            # => start_real_time = current_real_time - world_delta / time_scale
            
            world_delta = saved_world_time - self.start_world_time
            real_delta = world_delta / self.time_scale
            self.start_real_time = current_real_time - real_delta
            
            # 恢复累计暂停时间
            self._accumulated_pause = timedelta(seconds=data.get("accumulated_pause_seconds", 0))
            
            logger.info(
                f"世界状态已加载: 第{self.get_world_time().day}天 "
                f"{self.get_world_time().datetime.strftime('%H:%M')}"
            )
            return True
            
        except Exception as e:
            logger.error(f"加载世界状态失败: {e}")
            return False
    
    def get_time(self) -> datetime:
        """获取当前游戏内时间（now 的别名）"""
        return self.now()
    
    def now(self) -> datetime:
        """
        获取当前游戏内时间
        
        Returns:
            游戏内当前时间
        """
        if self.is_paused and self._pause_time:
            # 暂停时返回暂停时的时间
            real_delta = self._pause_time - self.start_real_time - self._accumulated_pause
        else:
            real_delta = datetime.now(timezone.utc) - self.start_real_time - self._accumulated_pause
        
        # 应用时间缩放
        world_delta = real_delta * self.time_scale
        return self.start_world_time + world_delta
    
    def get_world_time(self) -> WorldTime:
        """
        获取完整的世界时间信息
        
        Returns:
            WorldTime 对象，包含完整时间信息
        """
        current_time = self.now()
        
        # 计算游戏天数
        delta_days = (current_time - self.start_world_time).days
        day = delta_days + 1  # 从第1天开始
        
        # 获取时间段
        time_of_day = self._get_time_of_day(current_time.hour)
        
        # 是否是白天 (06:00-22:00)
        is_daytime = 6 <= current_time.hour < 22
        
        return WorldTime(
            datetime=current_time,
            day=day,
            time_of_day=time_of_day,
            is_daytime=is_daytime,
        )
    
    def _get_time_of_day(self, hour: int) -> TimeOfDay:
        """
        根据小时获取时间段
        
        Args:
            hour: 小时 (0-23)
        
        Returns:
            时间段枚举
        """
        if 5 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 14:
            return TimeOfDay.NOON
        elif 14 <= hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= hour < 20:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def is_daytime(self) -> bool:
        """是否是白天 (06:00-22:00)"""
        hour = self.now().hour
        return 6 <= hour < 22
    
    def is_working_hours(self) -> bool:
        """是否是工作时间 (09:00-18:00)"""
        hour = self.now().hour
        return 9 <= hour < 18
    
    def is_sleeping_hours(self) -> bool:
        """是否是睡眠时间 (23:00-06:00)"""
        hour = self.now().hour
        return hour >= 23 or hour < 6
    
    def pause(self) -> None:
        """暂停时钟"""
        if not self.is_paused:
            self.is_paused = True
            self._pause_time = datetime.now(timezone.utc)
            self._save_to_file()  # 暂停时保存
            logger.info("世界时钟已暂停")
    
    def resume(self) -> None:
        """恢复时钟"""
        if self.is_paused and self._pause_time:
            pause_duration = datetime.now(timezone.utc) - self._pause_time
            self._accumulated_pause += pause_duration
            self.is_paused = False
            self._pause_time = None
            self._save_to_file()  # 恢复时保存
            logger.info(f"世界时钟已恢复，暂停时长: {pause_duration}")
    
    def set_time_scale(self, scale: int) -> None:
        """
        动态调整时间缩放
        
        Args:
            scale: 新的时间缩放比例
        """
        if scale < 1 or scale > 100:
            raise ValueError("时间缩放比例必须在 1-100 之间")
        
        old_scale = self.time_scale
        self.time_scale = scale
        self._save_to_file()  # 缩放变化时保存
        logger.info(f"时间缩放调整: {old_scale} -> {scale}")
    
    async def start(self) -> None:
        """
        启动时钟tick循环
        
        每现实1秒tick一次，发送世界时间变化事件
        """
        self.is_running = True
        logger.info("世界时钟开始运行")
        
        # 定期保存计数器
        save_counter = 0
        
        while self.is_running:
            if not self.is_paused:
                await self._tick()
                
                # 每60秒自动保存一次（防止意外关闭丢失进度）
                save_counter += 1
                if save_counter >= 60:
                    self._save_to_file()
                    save_counter = 0
                    
            await asyncio.sleep(1)  # 每秒tick一次
    
    async def _tick(self) -> None:
        """时钟tick，发送时间相关事件"""
        world_time = self.get_world_time()
        
        # 检查时间段是否变化
        if self._last_tick_time_of_day != world_time.time_of_day:
            await event_bus.publish(Event(
                event_type=EventType.WORLD_TIME_CHANGED,
                data={
                    "old_time_of_day": self._last_tick_time_of_day.value if self._last_tick_time_of_day else None,
                    "new_time_of_day": world_time.time_of_day.value,
                    "world_time": world_time.to_dict(),
                },
                source="world_clock",
            ))
            self._last_tick_time_of_day = world_time.time_of_day
        
        # 每分钟发送一次tick事件（游戏内时间）
        if world_time.datetime.second == 0:
            await event_bus.publish(Event(
                event_type=EventType.WORLD_TICK,
                data={"world_time": world_time.to_dict()},
                source="world_clock",
            ))
    
    def stop(self) -> None:
        """停止时钟（关闭前保存状态）"""
        self.is_running = False
        self._save_to_file()  # 停止时保存
        logger.info("世界时钟已停止，状态已保存")
    
    def to_dict(self) -> dict:
        """转换为字典，用于API返回"""
        world_time = self.get_world_time()
        return {
            "time_scale": self.time_scale,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "world_time": world_time.to_dict(),
        }
    
    def reset_world(self) -> None:
        """
        重置世界（危险操作！）
        
        删除存档，下次启动将创建新世界
        """
        if self.SAVE_FILE.exists():
            self.SAVE_FILE.unlink()
            logger.warning("世界已重置！下次启动将创建新世界")


# 创建全局世界时钟单例
world_clock = WorldClock()
