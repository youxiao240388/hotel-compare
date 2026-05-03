#!/usr/bin/env python3
"""测试完整比价链路"""
import sys
sys.path.insert(0, "/home/hermes/projects/hotel-compare")

from src.platforms.base import RoomInfo
from src.matcher.room_matcher import RoomMatcher
from src.comparator.engine import PriceComparator

# 模拟多平台采集结果
ctrip_rooms = [
    RoomInfo(platform="ctrip", room_name="豪华大床房", price=388, includes_breakfast=True, cancellation="免费取消", bed_type="大床1.8m", room_area="28㎡"),
    RoomInfo(platform="ctrip", room_name="高级双床房", price=428, includes_breakfast=False, cancellation="限时取消", bed_type="双床1.2m×2", room_area="35㎡"),
    RoomInfo(platform="ctrip", room_name="行政套房", price=888, includes_breakfast=True, cancellation="不可取消", bed_type="大床2.0m", room_area="55㎡"),
]

meituan_rooms = [
    RoomInfo(platform="meituan", room_name="豪华大床房", price=368, includes_breakfast=True, cancellation="免费取消", bed_type="大床1.8m", room_area="28㎡"),
    RoomInfo(platform="meituan", room_name="高级双床房", price=418, includes_breakfast=False, cancellation="限时取消", bed_type="双床1.2m×2", room_area="35㎡"),
    RoomInfo(platform="meituan", room_name="行政套房", price=868, includes_breakfast=True, cancellation="不可取消", bed_type="大床2.0m", room_area="55㎡"),
]

fliggy_rooms = [
    RoomInfo(platform="fliggy", room_name="豪华海景大床房", price=399, includes_breakfast=True, cancellation="免费取消", bed_type="大床1.8m", room_area="30㎡"),
    RoomInfo(platform="fliggy", room_name="高级双床", price=408, includes_breakfast=False, cancellation="限时取消", bed_type="双床1.2m×2", room_area="35㎡"),
    RoomInfo(platform="fliggy", room_name="行政套房", price=899, includes_breakfast=True, cancellation="不可取消", bed_type="大床2.0m", room_area="58㎡"),
]

rooms_by_platform = {
    "ctrip": ctrip_rooms,
    "meituan": meituan_rooms,
    "fliggy": fliggy_rooms,
}

# 1. 房型匹配
matcher = RoomMatcher()
matched = matcher.match_rooms(rooms_by_platform)
print(f"匹配到 {len(matched)} 个房型组:")
for g in matched:
    prices = g["prices"]
    cheapest = min(prices, key=prices.get)
    print(f"  {g['room_name']} | 置信度={g['confidence']:.2f}")
    for p, v in prices.items():
        flag = " ← 最低" if p == cheapest else ""
        print(f"    {p}: ¥{v:.0f}{flag}")

# 2. 比价
print("\n--- 比价引擎 ---")
comparator = PriceComparator()
result = comparator.compare(rooms_by_platform, "测试酒店")
print(f"摘要: {result['summary']}")

cheapest = result["rooms"]
for room in cheapest:
    print(f"  {room['room_name']}: ¥{room['cheapest_price']:.0f} @ {room['cheapest_platform']} (置信度={room['confidence']:.2f})")

if result["alerts"]:
    print(f"\n预警: {result['alerts']}")
if result["trends"]:
    print(f"趋势: {result['trends']}")
