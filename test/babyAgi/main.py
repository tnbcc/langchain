"""
鲜花存储策略系统 - 主程序入口
基于BabyAGI架构，根据气候变化自动定制鲜花的存储策略
向量数据库: Chroma
"""

from baby_agi import BabyAGI


def main():
    climate_scenarios = [
        "高温预警：今天气温38°C，湿度60%，连续晴天",
        "寒潮来袭：明天凌晨气温降至-5°C，有霜冻风险",
        "暴雨天气：未来3天持续降雨，湿度达90%",
        "干燥季节：连续一周无降水，室内湿度40%",
    ]

    print("\n" + "=" * 60)
    print("🌷 鲜花存储策略智能系统 - BabyAGI Demo")
    print("=" * 60)

    for i, climate in enumerate(climate_scenarios, 1):
        print(f"\n{'=' * 60}")
        print(f"📌 场景 {i}: {climate}")
        print("=" * 60)

        objective = f"分析以下气候情况并制定鲜花储存策略：{climate}"

        baby_agi = BabyAGI(objective=objective, data_dir="./data")

        baby_agi.add_initial_task(
            f"分析气候信息：{climate}，并制定相应的鲜花存储策略"
        )

        baby_agi.run(max_iterations=5)

        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()