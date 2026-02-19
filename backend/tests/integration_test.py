"""
AI Society 集成测试脚本
========================
验证整个系统的功能和稳定性

运行方式：
    python tests/integration_test.py
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any

import httpx
import websockets

# ==================
# 配置
# ==================
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/world/ws"

# 测试结果存储
test_results: Dict[str, Dict[str, Any]] = {}


def log_result(category: str, test_name: str, passed: bool, message: str = "", duration: float = 0):
    """记录测试结果"""
    if category not in test_results:
        test_results[category] = {"passed": 0, "failed": 0, "tests": []}
    
    result = {
        "name": test_name,
        "passed": passed,
        "message": message,
        "duration_ms": round(duration * 1000, 2)
    }
    test_results[category]["tests"].append(result)
    
    if passed:
        test_results[category]["passed"] += 1
        print(f"  ✅ {test_name} ({result['duration_ms']}ms)")
    else:
        test_results[category]["failed"] += 1
        print(f"  ❌ {test_name}: {message}")


async def test_api_endpoint(
    client: httpx.AsyncClient,
    category: str,
    test_name: str,
    method: str,
    url: str,
    expected_status: int = 200,
    body: dict = None,
    check_fields: List[str] = None
) -> bool:
    """通用API端点测试"""
    start = time.time()
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=body)
        elif method == "PUT":
            response = await client.put(url, json=body)
        else:
            raise ValueError(f"不支持的方法: {method}")
        
        duration = time.time() - start
        
        if response.status_code != expected_status:
            log_result(category, test_name, False, 
                      f"状态码 {response.status_code} != {expected_status}", duration)
            return False
        
        if check_fields and response.status_code == 200:
            data = response.json()
            missing = [f for f in check_fields if f not in data]
            if missing:
                log_result(category, test_name, False, 
                          f"缺少字段: {missing}", duration)
                return False
        
        log_result(category, test_name, True, duration=duration)
        return True
        
    except Exception as e:
        duration = time.time() - start
        log_result(category, test_name, False, str(e), duration)
        return False


async def test_health_endpoints(client: httpx.AsyncClient):
    """测试健康检查端点"""
    print("\n📋 健康检查端点测试")
    
    await test_api_endpoint(client, "健康检查", "根路径", "GET", "/",
                           check_fields=["name", "version", "status"])
    await test_api_endpoint(client, "健康检查", "健康检查", "GET", "/health",
                           check_fields=["status", "world_clock", "locations_loaded"])


async def test_world_endpoints(client: httpx.AsyncClient):
    """测试世界系统端点"""
    print("\n🌍 世界系统端点测试")
    
    await test_api_endpoint(client, "世界系统", "获取世界状态", "GET", "/api/world/status",
                           check_fields=["clock", "cost"])
    await test_api_endpoint(client, "世界系统", "获取世界时间", "GET", "/api/world/time",
                           check_fields=["day", "time_of_day", "is_daytime"])
    await test_api_endpoint(client, "世界系统", "获取时钟状态", "GET", "/api/world/clock",
                           check_fields=["is_running", "is_paused", "time_scale"])
    await test_api_endpoint(client, "世界系统", "获取事件类型", "GET", "/api/world/event-types")
    await test_api_endpoint(client, "世界系统", "获取事件历史", "GET", "/api/world/events")
    
    # 测试时间控制
    await test_api_endpoint(client, "世界系统", "暂停世界", "POST", "/api/world/pause")
    await test_api_endpoint(client, "世界系统", "恢复世界", "POST", "/api/world/resume")
    await test_api_endpoint(client, "世界系统", "设置时间缩放", "POST", "/api/world/time-scale/10")


async def test_location_endpoints(client: httpx.AsyncClient):
    """测试地点系统端点"""
    print("\n📍 地点系统端点测试")
    
    await test_api_endpoint(client, "地点系统", "获取地点列表", "GET", "/api/locations",
                           check_fields=["locations", "total"])
    await test_api_endpoint(client, "地点系统", "获取地点类型", "GET", "/api/locations/types")
    await test_api_endpoint(client, "地点系统", "获取活动类型", "GET", "/api/locations/activities")
    await test_api_endpoint(client, "地点系统", "获取地点统计", "GET", "/api/locations/stats",
                           check_fields=["total_locations", "total_capacity"])
    await test_api_endpoint(client, "地点系统", "按类型筛选", "GET", "/api/locations?type=cafe")


async def test_agent_endpoints(client: httpx.AsyncClient):
    """测试智能体系统端点"""
    print("\n🤖 智能体系统端点测试")
    
    await test_api_endpoint(client, "智能体系统", "获取智能体列表", "GET", "/api/agents")
    await test_api_endpoint(client, "智能体系统", "获取智能体数量", "GET", "/api/agents/count",
                           check_fields=["total", "max"])
    
    # 测试批量生成智能体
    print("    生成智能体中...")
    start = time.time()
    response = await client.post("/api/agents/generate/batch", json={"count": 5, "use_llm_ratio": 0})
    duration = time.time() - start
    if response.status_code == 200:
        log_result("智能体系统", "批量生成智能体", True, duration=duration)
    else:
        log_result("智能体系统", "批量生成智能体", False, 
                  f"状态码 {response.status_code}", duration)
    
    # 获取生成后的列表
    response = await client.get("/api/agents/")
    if response.status_code == 200:
        agents = response.json()
        if len(agents) > 0:
            log_result("智能体系统", "验证生成结果", True)
            
            # 测试获取单个智能体
            agent_id = agents[0]["id"]
            await test_api_endpoint(client, "智能体系统", "获取智能体详情", "GET", 
                                   f"/api/agents/{agent_id}",
                                   check_fields=["id", "name", "age", "occupation"])
        else:
            log_result("智能体系统", "验证生成结果", False, "生成后列表为空")


async def test_conversation_endpoints(client: httpx.AsyncClient):
    """测试对话系统端点"""
    print("\n💬 对话系统端点测试")
    
    await test_api_endpoint(client, "对话系统", "获取对话列表", "GET", "/api/conversations/")
    await test_api_endpoint(client, "对话系统", "获取对话统计", "GET", "/api/conversations/stats",
                           check_fields=["active_conversations"])


async def test_llm_endpoints(client: httpx.AsyncClient):
    """测试LLM系统端点"""
    print("\n🧠 LLM系统端点测试")
    
    await test_api_endpoint(client, "LLM系统", "获取模型列表", "GET", "/api/llm/models",
                           check_fields=["default_model", "models"])
    await test_api_endpoint(client, "LLM系统", "获取LLM统计", "GET", "/api/llm/stats",
                           check_fields=["cost", "cache"])
    await test_api_endpoint(client, "LLM系统", "获取成本信息", "GET", "/api/llm/cost",
                           check_fields=["monthly_budget", "current_month_cost"])
    await test_api_endpoint(client, "LLM系统", "获取缓存统计", "GET", "/api/llm/cache/stats",
                           check_fields=["size", "hit_rate"])


async def test_websocket():
    """测试WebSocket连接"""
    print("\n🔌 WebSocket连接测试")
    
    start = time.time()
    try:
        async with websockets.connect(WS_URL, close_timeout=5) as ws:
            duration = time.time() - start
            log_result("WebSocket", "建立连接", True, duration=duration)
            
            # 等待接收初始消息
            start = time.time()
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=10)
                duration = time.time() - start
                data = json.loads(message)
                
                # 验证消息格式统一性（所有消息都应该有 event_type 字段）
                if "event_type" in data:
                    log_result("WebSocket", "接收初始消息", True, 
                              f"event_type={data['event_type']}", duration)
                else:
                    log_result("WebSocket", "接收初始消息", False, 
                              f"消息缺少 event_type 字段: {list(data.keys())}", duration)
            except asyncio.TimeoutError:
                log_result("WebSocket", "接收初始消息", False, "10秒内未收到消息")
                
    except Exception as e:
        duration = time.time() - start
        log_result("WebSocket", "建立连接", False, str(e), duration)


async def test_error_handling(client: httpx.AsyncClient):
    """测试错误处理"""
    print("\n⚠️ 错误处理测试")
    
    # 测试404
    await test_api_endpoint(client, "错误处理", "不存在的端点", "GET", 
                           "/api/nonexistent", expected_status=404)
    
    # 测试无效参数（scale=0 应该被拒绝）
    await test_api_endpoint(client, "错误处理", "无效的时间缩放", "POST",
                           "/api/world/time-scale/0", expected_status=400)
    
    # 测试不存在的智能体
    await test_api_endpoint(client, "错误处理", "不存在的智能体", "GET",
                           "/api/agents/nonexistent-id", expected_status=404)


async def test_performance(client: httpx.AsyncClient):
    """性能基准测试"""
    print("\n⚡ 性能基准测试")
    
    # 测试响应时间
    endpoints = [
        ("/health", "健康检查响应时间"),
        ("/api/world/status", "世界状态响应时间"),
        ("/api/locations/", "地点列表响应时间"),
        ("/api/agents/", "智能体列表响应时间"),
    ]
    
    for url, name in endpoints:
        times = []
        for _ in range(5):
            start = time.time()
            await client.get(url)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        if avg_time < 0.5:  # 500ms以内算通过
            log_result("性能测试", name, True, f"平均 {avg_time*1000:.1f}ms", avg_time)
        else:
            log_result("性能测试", name, False, f"平均 {avg_time*1000:.1f}ms (超过500ms)")
    
    # 并发请求测试
    print("    并发请求测试中...")
    start = time.time()
    tasks = [client.get("/api/world/status") for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    duration = time.time() - start
    
    success_count = sum(1 for r in responses if r.status_code == 200)
    if success_count == 10 and duration < 2:
        log_result("性能测试", "10个并发请求", True, f"全部成功，耗时 {duration*1000:.1f}ms", duration)
    else:
        log_result("性能测试", "10个并发请求", False, 
                  f"{success_count}/10 成功，耗时 {duration*1000:.1f}ms")


def print_summary():
    """打印测试摘要"""
    print("\n" + "=" * 60)
    print("📊 测试报告摘要")
    print("=" * 60)
    
    total_passed = 0
    total_failed = 0
    
    for category, results in test_results.items():
        status = "✅" if results["failed"] == 0 else "❌"
        print(f"\n{status} {category}: {results['passed']} 通过, {results['failed']} 失败")
        total_passed += results["passed"]
        total_failed += results["failed"]
    
    print("\n" + "-" * 60)
    total = total_passed + total_failed
    pass_rate = (total_passed / total * 100) if total > 0 else 0
    
    if total_failed == 0:
        print(f"🎉 全部测试通过！ {total_passed}/{total} ({pass_rate:.1f}%)")
    else:
        print(f"⚠️ 测试完成: {total_passed}/{total} 通过 ({pass_rate:.1f}%)")
        print(f"   {total_failed} 个测试失败")
    
    print("=" * 60)
    
    return total_failed == 0


async def main():
    """主测试入口"""
    print("=" * 60)
    print("🧪 AI Society 集成测试")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 后端地址: {BASE_URL}")
    print("=" * 60)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, follow_redirects=True) as client:
        # 1. 健康检查
        await test_health_endpoints(client)
        
        # 2. 世界系统
        await test_world_endpoints(client)
        
        # 3. 地点系统
        await test_location_endpoints(client)
        
        # 4. 智能体系统
        await test_agent_endpoints(client)
        
        # 5. 对话系统
        await test_conversation_endpoints(client)
        
        # 6. LLM系统
        await test_llm_endpoints(client)
        
        # 7. WebSocket
        await test_websocket()
        
        # 8. 错误处理
        await test_error_handling(client)
        
        # 9. 性能测试
        await test_performance(client)
    
    # 打印摘要
    success = print_summary()
    
    # 保存详细报告
    report_path = "tests/integration_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "results": test_results,
            "success": success
        }, f, ensure_ascii=False, indent=2)
    print(f"\n📄 详细报告已保存至: {report_path}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
