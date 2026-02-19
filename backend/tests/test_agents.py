"""
智能体模块测试
==============
测试人格系统、需求系统、记忆系统和智能体管理
"""

import time
from datetime import datetime, timedelta

import pytest

from app.agents.personality import Personality, PersonalityTrait
from app.agents.needs import Needs, NeedType, NEED_CONFIG
from app.agents.memory import Memory, MemoryType, MemoryManager
from app.agents.models import Agent, AgentState, ActionType, Position


# ==================
# 人格系统测试
# ==================

class TestPersonality:
    """人格系统测试"""
    
    def test_default_personality(self):
        """测试默认人格"""
        p = Personality()
        
        assert p.openness == 50
        assert p.conscientiousness == 50
        assert p.extraversion == 50
        assert p.agreeableness == 50
        assert p.neuroticism == 50
    
    def test_custom_personality(self):
        """测试自定义人格"""
        p = Personality(
            openness=80,
            conscientiousness=70,
            extraversion=30,
            agreeableness=60,
            neuroticism=40,
        )
        
        assert p.openness == 80
        assert p.extraversion == 30
    
    def test_invalid_values(self):
        """测试无效值"""
        with pytest.raises(ValueError):
            Personality(openness=150)
        
        with pytest.raises(ValueError):
            Personality(neuroticism=-10)
    
    def test_get_level(self):
        """测试获取特质等级"""
        p = Personality(openness=20, extraversion=80)
        
        assert p.get_level(PersonalityTrait.OPENNESS) == "low"
        assert p.get_level(PersonalityTrait.EXTRAVERSION) == "high"
    
    def test_get_description(self):
        """测试获取人格描述"""
        p = Personality(extraversion=90, agreeableness=85)
        desc = p.get_description()
        
        # 描述应该包含一些词
        assert len(desc) > 0
        assert "、" in desc
    
    def test_social_tendency(self):
        """测试社交倾向"""
        p_extrovert = Personality(extraversion=90, agreeableness=80, neuroticism=20)
        p_introvert = Personality(extraversion=20, agreeableness=40, neuroticism=60)
        
        assert p_extrovert.social_tendency() > p_introvert.social_tendency()
    
    def test_work_efficiency(self):
        """测试工作效率"""
        p_diligent = Personality(conscientiousness=90, neuroticism=20)
        p_casual = Personality(conscientiousness=30, neuroticism=70)
        
        assert p_diligent.work_efficiency() > p_casual.work_efficiency()
    
    def test_random_personality(self):
        """测试随机人格生成"""
        p = Personality.random()
        
        # 所有值应该在0-100之间
        for trait in PersonalityTrait:
            value = p.get_trait(trait)
            assert 0 <= value <= 100
    
    def test_archetype(self):
        """测试人格原型"""
        leader = Personality.from_archetype("leader")
        creative = Personality.from_archetype("creative")
        
        # leader应该有高外向性和高尽责性
        assert leader.conscientiousness > 60
        assert leader.extraversion > 60
        
        # creative应该有高开放性
        assert creative.openness > 80
    
    def test_to_dict_and_from_dict(self):
        """测试序列化"""
        p = Personality(openness=70, extraversion=40)
        d = p.to_dict()
        
        p2 = Personality.from_dict(d)
        assert p2.openness == 70
        assert p2.extraversion == 40


# ==================
# 需求系统测试
# ==================

class TestNeeds:
    """需求系统测试"""
    
    def test_default_needs(self):
        """测试默认需求"""
        n = Needs()
        
        assert 0 <= n.hunger <= 100
        assert 0 <= n.fatigue <= 100
    
    def test_get_and_set(self):
        """测试获取和设置需求"""
        n = Needs()
        
        n.set(NeedType.HUNGER, 80)
        assert n.get(NeedType.HUNGER) == 80
        
        # 超出范围应该被裁剪
        n.set(NeedType.HUNGER, 150)
        assert n.get(NeedType.HUNGER) == 100
    
    def test_update(self):
        """测试需求更新"""
        n = Needs(hunger=30, fatigue=20)
        
        # 经过2小时
        changes = n.update(elapsed_hours=2.0)
        
        # 需求应该增长
        assert n.hunger > 30
        assert n.fatigue > 20
        assert NeedType.HUNGER in changes
    
    def test_satisfy(self):
        """测试满足需求"""
        n = Needs(hunger=80)
        
        decrease = n.satisfy(NeedType.HUNGER)
        
        assert decrease > 0
        assert n.hunger < 80
    
    def test_satisfy_by_activity(self):
        """测试活动满足需求"""
        n = Needs(hunger=70, fatigue=60)
        
        # 吃饭活动
        changes = n.satisfy_by_activity("eat lunch")
        
        assert NeedType.HUNGER in changes
    
    def test_urgent_needs(self):
        """测试紧急需求"""
        n = Needs(hunger=85, fatigue=50, social=30)
        
        urgent = n.get_urgent_needs()
        
        # 饥饿应该是紧急的
        assert any(u[0] == NeedType.HUNGER for u in urgent)
    
    def test_most_urgent(self):
        """测试最紧急需求"""
        n = Needs(hunger=90, fatigue=75)
        
        most = n.get_most_urgent()
        
        assert most is not None
        assert most[0] == NeedType.HUNGER
    
    def test_wellbeing(self):
        """测试幸福指数"""
        n_good = Needs(hunger=10, fatigue=10, social=20, entertainment=15)
        n_bad = Needs(hunger=80, fatigue=90, social=70, entertainment=85)
        
        assert n_good.get_overall_wellbeing() > n_bad.get_overall_wellbeing()
    
    def test_random_needs(self):
        """测试随机需求生成"""
        n = Needs.random(max_value=50)
        
        # 所有值应该在50以内
        for need in NeedType:
            assert n.get(need) <= 60  # 加一点容差
    
    def test_morning_evening_states(self):
        """测试预设状态"""
        morning = Needs.morning_state()
        evening = Needs.evening_state()
        
        # 早上疲劳低，晚上疲劳高
        assert morning.fatigue < evening.fatigue


# ==================
# 记忆系统测试
# ==================

class TestMemory:
    """记忆测试"""
    
    def test_create_memory(self):
        """测试创建记忆"""
        m = Memory(
            type=MemoryType.EVENT,
            content="今天去了公园",
            importance=7.0,
        )
        
        assert m.type == MemoryType.EVENT
        assert m.content == "今天去了公园"
        assert m.importance == 7.0
        assert len(m.id) > 0
    
    def test_keyword_extraction(self):
        """测试关键词提取"""
        m = Memory(content="在咖啡馆遇到了张三，聊了很久")
        
        assert len(m.keywords) > 0
    
    def test_recency_score(self):
        """测试时效性分数"""
        m = Memory(content="test")
        
        # 新记忆应该有高分数
        assert m.get_recency_score() > 0.9
    
    def test_relevance_score(self):
        """测试相关性分数"""
        m = Memory(content="今天在咖啡馆工作")
        
        # 使用记忆中实际存在的关键词
        score = m.get_relevance_score(m.keywords)
        assert score == 1.0  # 完全匹配
        
        # 无交集的关键词
        score_irrelevant = m.get_relevance_score({"公园里", "睡大觉"})
        assert score_irrelevant == 0.0
    
    def test_access(self):
        """测试访问计数"""
        m = Memory(content="test")
        
        assert m.access_count == 0
        m.access()
        assert m.access_count == 1
    
    def test_to_dict_and_from_dict(self):
        """测试序列化"""
        m = Memory(
            type=MemoryType.CONVERSATION,
            content="和李四聊天",
            importance=6.0,
            related_agents=["agent_1"],
        )
        
        d = m.to_dict()
        m2 = Memory.from_dict(d)
        
        assert m2.type == MemoryType.CONVERSATION
        assert m2.content == "和李四聊天"
        assert m2.importance == 6.0


class TestMemoryManager:
    """记忆管理器测试"""
    
    def test_add_and_get(self):
        """测试添加和获取记忆"""
        mm = MemoryManager()
        
        m = Memory(content="测试记忆")
        mid = mm.add(m)
        
        retrieved = mm.get(mid)
        assert retrieved is not None
        assert retrieved.content == "测试记忆"
    
    def test_create_and_add(self):
        """测试便捷方法"""
        mm = MemoryManager()
        
        m = mm.create_and_add(
            content="便捷方法创建",
            memory_type=MemoryType.EVENT,
            importance=5.0,
        )
        
        assert mm.count() == 1
        assert m.content == "便捷方法创建"
    
    def test_remove(self):
        """测试删除记忆"""
        mm = MemoryManager()
        
        m = mm.create_and_add("to be removed")
        mid = m.id
        
        assert mm.count() == 1
        mm.remove(mid)
        assert mm.count() == 0
    
    def test_retrieve_recent(self):
        """测试获取最近记忆"""
        mm = MemoryManager()
        
        for i in range(5):
            mm.create_and_add(f"记忆 {i}")
        
        recent = mm.retrieve_recent(3)
        assert len(recent) == 3
    
    def test_retrieve_by_type(self):
        """测试按类型检索"""
        mm = MemoryManager()
        
        mm.create_and_add("事件1", MemoryType.EVENT)
        mm.create_and_add("事件2", MemoryType.EVENT)
        mm.create_and_add("对话1", MemoryType.CONVERSATION)
        
        events = mm.retrieve_by_type(MemoryType.EVENT)
        assert len(events) == 2
    
    def test_retrieve_by_agent(self):
        """测试按智能体检索"""
        mm = MemoryManager()
        
        mm.create_and_add("和A聊天", related_agents=["agent_a"])
        mm.create_and_add("和B聊天", related_agents=["agent_b"])
        mm.create_and_add("和A再聊", related_agents=["agent_a"])
        
        memories_with_a = mm.retrieve_by_agent("agent_a")
        assert len(memories_with_a) == 2
    
    def test_max_capacity(self):
        """测试最大容量"""
        mm = MemoryManager(max_memories=10)
        
        for i in range(15):
            mm.create_and_add(f"记忆 {i}")
        
        # 应该自动遗忘一些
        assert mm.count() <= 10
    
    def test_get_context_for_llm(self):
        """测试生成LLM上下文"""
        mm = MemoryManager()
        
        mm.create_and_add("去了咖啡馆")
        mm.create_and_add("买了面包")
        
        context = mm.get_context_for_llm()
        
        assert "咖啡馆" in context
        assert "面包" in context


# ==================
# 智能体模型测试
# ==================

class TestAgent:
    """智能体模型测试"""
    
    def test_create_agent(self):
        """测试创建智能体"""
        agent = Agent(
            name="张三",
            age=25,
            occupation="程序员",
        )
        
        assert agent.name == "张三"
        assert agent.age == 25
        assert agent.occupation == "程序员"
        assert len(agent.id) > 0
    
    def test_personality_description(self):
        """测试人格描述"""
        agent = Agent(
            personality=Personality(extraversion=90),
        )
        
        desc = agent.get_personality_description()
        assert len(desc) > 0
    
    def test_add_memory(self):
        """测试添加记忆"""
        agent = Agent(name="测试")
        
        memory = agent.add_memory("今天去了公园", MemoryType.EVENT, 5.0)
        
        assert agent.memory.count() == 1
        assert memory.content == "今天去了公园"
    
    def test_set_action(self):
        """测试设置行为"""
        agent = Agent()
        
        agent.set_action(
            ActionType.WORK,
            target="办公室",
            duration_minutes=60,
            thinking="我要认真工作",
        )
        
        assert agent.current_action.type == ActionType.WORK
        assert agent.current_action.duration_minutes == 60
        assert agent.state == AgentState.BUSY
    
    def test_complete_action(self):
        """测试完成行为"""
        agent = Agent()
        agent.needs.hunger = 80
        
        agent.set_action(ActionType.EAT, duration_minutes=30)
        completed = agent.complete_action()
        
        assert completed.type == ActionType.EAT
        assert agent.needs.hunger < 80  # 饥饿应该降低
        assert agent.state == AgentState.ACTIVE
    
    def test_relationship(self):
        """测试关系系统"""
        agent = Agent()
        
        rel = agent.update_relationship(
            "agent_b",
            "李四",
            closeness_delta=10,
            trust_delta=5,
        )
        
        assert rel.closeness == 60
        assert rel.trust == 55
        assert rel.interaction_count == 1
    
    def test_spend_money(self):
        """测试消费"""
        agent = Agent(balance=1000)
        
        success = agent.spend_money(100, "吃饭")
        
        assert success
        assert agent.balance == 900
        assert agent.daily_expense == 100
        
        # 余额不足
        fail = agent.spend_money(10000, "太贵了")
        assert not fail
    
    def test_move_to(self):
        """测试移动"""
        agent = Agent()
        
        agent.move_to(10, 20, "loc_1", "咖啡馆")
        
        assert agent.position.x == 10
        assert agent.position.y == 20
        assert agent.position.location_id == "loc_1"
        assert agent.position.location_name == "咖啡馆"
    
    def test_wellbeing(self):
        """测试幸福指数"""
        agent = Agent(
            personality=Personality(neuroticism=20),  # 情绪稳定
            needs=Needs(hunger=20, fatigue=20, social=20, entertainment=20),
            balance=20000,
        )
        
        wellbeing = agent.get_wellbeing()
        
        # 应该是个正数
        assert wellbeing > 0
    
    def test_to_dict_and_from_dict(self):
        """测试序列化"""
        agent = Agent(
            name="王五",
            age=30,
            occupation="设计师",
            traits=["有创意", "友善"],
        )
        agent.balance = 15000
        
        d = agent.to_dict()
        agent2 = Agent.from_dict(d)
        
        assert agent2.name == "王五"
        assert agent2.age == 30
        assert agent2.occupation == "设计师"
        assert agent2.balance == 15000


class TestPosition:
    """位置测试"""
    
    def test_distance(self):
        """测试距离计算"""
        p1 = Position(x=0, y=0)
        p2 = Position(x=3, y=4)
        
        assert p1.distance_to(p2) == 5.0
    
    def test_to_dict(self):
        """测试序列化"""
        p = Position(x=10, y=20, location_id="loc_1", location_name="公园")
        d = p.to_dict()
        
        assert d["x"] == 10
        assert d["y"] == 20
        assert d["location_id"] == "loc_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
