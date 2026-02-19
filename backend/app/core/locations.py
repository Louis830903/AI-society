"""
地点/位置模块
============
定义游戏世界中的地点数据结构和管理逻辑

地点类型：
- 住宅区：公寓、别墅
- 商业区：咖啡馆、餐厅、超市、商场
- 工作区：办公楼、工厂、学校、医院
- 公共区：公园、广场、图书馆
- 服务区：银行、邮局、理发店

每个地点包含：
- 位置坐标
- 容量限制
- 营业时间
- 可提供的服务/活动
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from app.core.config import settings


class LocationType(str, Enum):
    """地点类型枚举"""
    
    # 住宅类
    APARTMENT = "apartment"        # 公寓
    HOUSE = "house"               # 住宅
    
    # 商业类
    CAFE = "cafe"                 # 咖啡馆
    RESTAURANT = "restaurant"     # 餐厅
    SUPERMARKET = "supermarket"   # 超市
    MALL = "mall"                 # 商场
    
    # 工作类
    OFFICE = "office"             # 办公楼
    FACTORY = "factory"           # 工厂
    SCHOOL = "school"             # 学校
    HOSPITAL = "hospital"         # 医院
    
    # 公共类
    PARK = "park"                 # 公园
    PLAZA = "plaza"               # 广场
    LIBRARY = "library"           # 图书馆
    
    # 服务类
    BANK = "bank"                 # 银行
    GYM = "gym"                   # 健身房
    BARBERSHOP = "barbershop"     # 理发店


class ActivityType(str, Enum):
    """活动类型枚举"""
    
    SLEEP = "sleep"               # 睡觉
    EAT = "eat"                   # 吃饭
    WORK = "work"                 # 工作
    SHOP = "shop"                 # 购物
    EXERCISE = "exercise"         # 运动
    RELAX = "relax"               # 休闲
    STUDY = "study"               # 学习
    SOCIALIZE = "socialize"       # 社交
    HEALTHCARE = "healthcare"     # 医疗
    FINANCE = "finance"           # 金融


@dataclass
class OpeningHours:
    """
    营业时间
    
    Attributes:
        open_hour: 开门时间（24小时制）
        close_hour: 关门时间（24小时制）
        open_days: 营业日（0=周一, 6=周日）
    """
    open_hour: int = 0
    close_hour: int = 24
    open_days: Set[int] = field(default_factory=lambda: set(range(7)))
    
    def is_open(self, hour: int, weekday: int) -> bool:
        """检查指定时间是否营业"""
        if weekday not in self.open_days:
            return False
        
        # 处理跨夜的情况（如夜店 22:00-04:00）
        if self.open_hour <= self.close_hour:
            return self.open_hour <= hour < self.close_hour
        else:
            return hour >= self.open_hour or hour < self.close_hour
    
    def to_dict(self) -> dict:
        return {
            "open_hour": self.open_hour,
            "close_hour": self.close_hour,
            "open_days": list(self.open_days),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OpeningHours":
        return cls(
            open_hour=data.get("open_hour", 0),
            close_hour=data.get("close_hour", 24),
            open_days=set(data.get("open_days", range(7))),
        )


@dataclass
class Location:
    """
    地点数据类
    
    Attributes:
        id: 唯一标识
        name: 地点名称
        type: 地点类型
        x: X坐标
        y: Y坐标
        width: 宽度（占用格数）
        height: 高度（占用格数）
        capacity: 最大容纳人数
        activities: 可进行的活动类型列表
        opening_hours: 营业时间
        description: 地点描述
        owner_agent_id: 所有者智能体ID（如私人住宅）
    """
    id: str
    name: str
    type: LocationType
    x: float
    y: float
    width: int = 2
    height: int = 2
    capacity: int = 10
    activities: List[ActivityType] = field(default_factory=list)
    opening_hours: OpeningHours = field(default_factory=OpeningHours)
    description: str = ""
    owner_agent_id: Optional[str] = None
    
    # 运行时状态（不序列化）
    current_agents: Set[str] = field(default_factory=set, repr=False)
    
    @property
    def center(self) -> Tuple[float, float]:
        """获取地点中心坐标"""
        return (self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def bounds(self) -> Tuple[float, float, float, float]:
        """获取地点边界 (x1, y1, x2, y2)"""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    @property
    def is_full(self) -> bool:
        """是否已满"""
        return len(self.current_agents) >= self.capacity
    
    @property
    def occupancy(self) -> float:
        """当前占用率 (0-1)"""
        return len(self.current_agents) / self.capacity if self.capacity > 0 else 0
    
    def contains_point(self, x: float, y: float) -> bool:
        """检查点是否在地点范围内"""
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height
    
    def can_do_activity(self, activity: ActivityType) -> bool:
        """检查是否可以进行指定活动"""
        return activity in self.activities
    
    def is_open_at(self, hour: int, weekday: int) -> bool:
        """检查指定时间是否营业"""
        return self.opening_hours.is_open(hour, weekday)
    
    def enter(self, agent_id: str) -> bool:
        """
        智能体进入地点
        
        Returns:
            是否成功进入
        """
        if self.is_full:
            return False
        self.current_agents.add(agent_id)
        return True
    
    def leave(self, agent_id: str) -> None:
        """智能体离开地点"""
        self.current_agents.discard(agent_id)
    
    def to_dict(self) -> dict:
        """转换为字典（用于API/存储）- 符合前端期望格式"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            # 前端期望的格式
            "position": {"x": self.x, "y": self.y},
            "size": {"width": self.width, "height": self.height},
            "capacity": self.capacity,
            "current_occupants": len(self.current_agents),
            "activities": [a.value for a in self.activities],
            "open_hours": {
                "open": self.opening_hours.open_hour,
                "close": self.opening_hours.close_hour,
            } if self.opening_hours else None,
            "is_open_now": True,  # 简化处理
            # 兼容旧格式（后端内部使用）
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "opening_hours": self.opening_hours.to_dict(),
            "owner_agent_id": self.owner_agent_id,
            "current_agent_count": len(self.current_agents),
            "is_full": self.is_full,
            "occupancy": self.occupancy,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Location":
        """从字典创建实例"""
        return cls(
            id=data["id"],
            name=data["name"],
            type=LocationType(data["type"]),
            x=data["x"],
            y=data["y"],
            width=data.get("width", 2),
            height=data.get("height", 2),
            capacity=data.get("capacity", 10),
            activities=[ActivityType(a) for a in data.get("activities", [])],
            opening_hours=OpeningHours.from_dict(data.get("opening_hours", {})),
            description=data.get("description", ""),
            owner_agent_id=data.get("owner_agent_id"),
        )


class LocationManager:
    """
    地点管理器
    
    负责加载、查询和管理所有地点
    """
    
    def __init__(self):
        """初始化地点管理器"""
        self.locations: Dict[str, Location] = {}
        self._location_grid: Dict[Tuple[int, int], List[str]] = {}  # 空间索引
    
    def load_from_file(self, file_path: Optional[str] = None) -> int:
        """
        从JSON文件加载地点配置
        
        Args:
            file_path: 配置文件路径，默认使用settings中的配置
        
        Returns:
            加载的地点数量
        """
        path = Path(file_path or settings.locations_file)
        
        if not path.exists():
            logger.warning(f"地点配置文件不存在: {path}")
            return 0
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            locations_data = data.get("locations", [])
            for loc_data in locations_data:
                location = Location.from_dict(loc_data)
                self.add_location(location)
            
            logger.info(f"加载了 {len(self.locations)} 个地点")
            return len(self.locations)
            
        except Exception as e:
            logger.error(f"加载地点配置失败: {e}")
            return 0
    
    def add_location(self, location: Location) -> None:
        """添加地点"""
        self.locations[location.id] = location
        self._update_spatial_index(location)
    
    def remove_location(self, location_id: str) -> Optional[Location]:
        """移除地点"""
        location = self.locations.pop(location_id, None)
        if location:
            self._remove_from_spatial_index(location)
        return location
    
    def get_location(self, location_id: str) -> Optional[Location]:
        """根据ID获取地点"""
        return self.locations.get(location_id)
    
    def get(self, location_id: str) -> Optional[Location]:
        """根据ID获取地点（get_location 的别名）"""
        return self.get_location(location_id)
    
    def get_by_name(self, name: str) -> Optional[Location]:
        """
        根据名称获取地点
        
        Args:
            name: 地点名称（支持模糊匹配）
        
        Returns:
            匹配的地点，优先精确匹配，其次部分匹配
        """
        # 精确匹配
        for loc in self.locations.values():
            if loc.name == name:
                return loc
        
        # 部分匹配（名称包含搜索词）
        for loc in self.locations.values():
            if name in loc.name or loc.name in name:
                return loc
        
        return None
    
    def enter(self, agent_id: str, location_id: str) -> bool:
        """
        智能体进入地点
        
        Args:
            agent_id: 智能体ID
            location_id: 地点ID
        
        Returns:
            是否成功进入
        """
        location = self.get_location(location_id)
        if location is None:
            return False
        return location.agent_enter(agent_id)
    
    def leave(self, agent_id: str, location_id: str) -> bool:
        """
        智能体离开地点
        
        Args:
            agent_id: 智能体ID
            location_id: 地点ID
        
        Returns:
            是否成功离开
        """
        location = self.get_location(location_id)
        if location is None:
            return False
        location.agent_leave(agent_id)
        return True
    
    def get_location_at(self, x: float, y: float) -> Optional[Location]:
        """获取指定坐标处的地点"""
        # 先用空间索引快速查找候选
        grid_x, grid_y = int(x // 10), int(y // 10)
        candidates = self._location_grid.get((grid_x, grid_y), [])
        
        for loc_id in candidates:
            loc = self.locations.get(loc_id)
            if loc and loc.contains_point(x, y):
                return loc
        
        # 回退到全量搜索
        for loc in self.locations.values():
            if loc.contains_point(x, y):
                return loc
        
        return None
    
    def get_locations_by_type(self, loc_type: LocationType) -> List[Location]:
        """根据类型获取地点列表"""
        return [loc for loc in self.locations.values() if loc.type == loc_type]
    
    def get_locations_with_activity(self, activity: ActivityType) -> List[Location]:
        """获取可以进行指定活动的地点"""
        return [loc for loc in self.locations.values() if loc.can_do_activity(activity)]
    
    def get_open_locations(self, hour: int, weekday: int) -> List[Location]:
        """获取指定时间营业的地点"""
        return [loc for loc in self.locations.values() if loc.is_open_at(hour, weekday)]
    
    def get_available_locations(
        self, 
        activity: Optional[ActivityType] = None,
        hour: Optional[int] = None,
        weekday: Optional[int] = None,
    ) -> List[Location]:
        """
        获取可用地点（未满、营业中、支持指定活动）
        
        Args:
            activity: 需要进行的活动类型
            hour: 当前小时
            weekday: 当前星期几
        
        Returns:
            符合条件的地点列表
        """
        result = []
        for loc in self.locations.values():
            if loc.is_full:
                continue
            if activity and not loc.can_do_activity(activity):
                continue
            if hour is not None and weekday is not None:
                if not loc.is_open_at(hour, weekday):
                    continue
            result.append(loc)
        return result
    
    def get_nearest_location(
        self, 
        x: float, 
        y: float, 
        loc_type: Optional[LocationType] = None,
        activity: Optional[ActivityType] = None,
    ) -> Optional[Location]:
        """
        获取最近的地点
        
        Args:
            x, y: 起始坐标
            loc_type: 地点类型筛选
            activity: 活动类型筛选
        
        Returns:
            最近的地点，如果没有符合条件的返回None
        """
        min_dist = float("inf")
        nearest = None
        
        for loc in self.locations.values():
            if loc_type and loc.type != loc_type:
                continue
            if activity and not loc.can_do_activity(activity):
                continue
            
            cx, cy = loc.center
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            
            if dist < min_dist:
                min_dist = dist
                nearest = loc
        
        return nearest
    
    def _update_spatial_index(self, location: Location) -> None:
        """更新空间索引"""
        # 计算地点覆盖的网格单元
        x1, y1 = int(location.x // 10), int(location.y // 10)
        x2, y2 = int((location.x + location.width) // 10), int((location.y + location.height) // 10)
        
        for gx in range(x1, x2 + 1):
            for gy in range(y1, y2 + 1):
                if (gx, gy) not in self._location_grid:
                    self._location_grid[(gx, gy)] = []
                if location.id not in self._location_grid[(gx, gy)]:
                    self._location_grid[(gx, gy)].append(location.id)
    
    def _remove_from_spatial_index(self, location: Location) -> None:
        """从空间索引中移除"""
        for cell_locations in self._location_grid.values():
            if location.id in cell_locations:
                cell_locations.remove(location.id)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "locations": [loc.to_dict() for loc in self.locations.values()],
            "count": len(self.locations),
        }
    
    def update_location(self, location_id: str, updates: dict) -> Optional[Location]:
        """
        更新地点属性
        
        Args:
            location_id: 地点ID
            updates: 要更新的字段字典
            
        Returns:
            更新后的地点，如果不存在返回None
        """
        location = self.locations.get(location_id)
        if not location:
            return None
        
        # 更新允许修改的字段
        if "name" in updates:
            location.name = updates["name"]
        if "description" in updates:
            location.description = updates["description"]
        if "capacity" in updates:
            location.capacity = updates["capacity"]
        if "x" in updates:
            old_location = Location(
                id=location.id, name=location.name, type=location.type,
                x=location.x, y=location.y, width=location.width, height=location.height
            )
            self._remove_from_spatial_index(old_location)
            location.x = updates["x"]
            self._update_spatial_index(location)
        if "y" in updates:
            old_location = Location(
                id=location.id, name=location.name, type=location.type,
                x=location.x, y=location.y, width=location.width, height=location.height
            )
            self._remove_from_spatial_index(old_location)
            location.y = updates["y"]
            self._update_spatial_index(location)
        if "width" in updates:
            location.width = updates["width"]
            self._update_spatial_index(location)
        if "height" in updates:
            location.height = updates["height"]
            self._update_spatial_index(location)
        if "activities" in updates:
            location.activities = [ActivityType(a) for a in updates["activities"]]
        if "opening_hours" in updates:
            oh = updates["opening_hours"]
            location.opening_hours = OpeningHours(
                open_hour=oh.get("open_hour", 0),
                close_hour=oh.get("close_hour", 24),
                open_days=set(oh.get("open_days", range(7))),
            )
        
        logger.info(f"更新地点: {location.name} ({location_id})")
        
        # 自动保存
        self.save_to_file()
        
        return location
    
    def save_to_file(self, file_path: Optional[str] = None) -> bool:
        """
        保存地点配置到JSON文件
        
        Args:
            file_path: 配置文件路径，默认使用settings中的配置
            
        Returns:
            是否保存成功
        """
        path = Path(file_path or settings.locations_file)
        
        try:
            # 构建保存数据（只保存需要持久化的字段）
            locations_data = []
            for loc in self.locations.values():
                loc_dict = {
                    "id": loc.id,
                    "name": loc.name,
                    "type": loc.type.value,
                    "x": loc.x,
                    "y": loc.y,
                    "width": loc.width,
                    "height": loc.height,
                    "capacity": loc.capacity,
                    "activities": [a.value for a in loc.activities],
                    "opening_hours": loc.opening_hours.to_dict(),
                    "description": loc.description,
                }
                if loc.owner_agent_id:
                    loc_dict["owner_agent_id"] = loc.owner_agent_id
                locations_data.append(loc_dict)
            
            data = {"locations": locations_data}
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存了 {len(locations_data)} 个地点到 {path}")
            return True
            
        except Exception as e:
            logger.error(f"保存地点配置失败: {e}")
            return False
    
    def generate_id(self, loc_type: LocationType) -> str:
        """
        生成新的地点ID
        
        Args:
            loc_type: 地点类型
            
        Returns:
            新的唯一ID
        """
        import uuid
        prefix = loc_type.value[:4]
        short_uuid = uuid.uuid4().hex[:8]
        return f"{prefix}_{short_uuid}"


# 创建全局地点管理器单例
location_manager = LocationManager()
