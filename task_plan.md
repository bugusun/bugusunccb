# C++ 迁移任务计划

## 目标
将当前 pygame 2D 俯视角门切房肉鸽原型迁移为 C++20 + CMake + SDL 平台层项目，保持核心行为一致，同时显著提升架构可维护性。

## 阶段
- [x] 1. 原项目结构与风险分析
- [x] 2. C++ 模块与目录设计
- [x] 3. 第一阶段骨架工程落地
- [in_progress] 4. 第二阶段核心玩法迁移草案
- [pending] 5. 测试与验收方案

## 约束
- 固定步长 60Hz
- 平台层与逻辑层隔离
- 数据驱动优先
- 不直接逐行翻译 Python

## 风险初记
- game/game.py 体量极大，存在 God Object 风险
- 房间状态持久化、门锁逻辑、导航缓存失效是迁移关键

## 状态更新
- [x] 1. 原项目结构与风险分析
- [x] 2. C++ 模块与目录设计
- [x] 3. 第一阶段骨架工程落地
- [~] 4. 第二阶段核心玩法迁移草案
- [ ] 5. 测试与验收方案

## 第二阶段已落地内容
- [x] `SkillSystem` 独立落地，并接入固定步主循环
- [x] 主动技能运行态：pulse / basketball / mamba_smash
- [x] Q 长按派生技能首版：先锋全屏震波 / 坤坤八向齐射
- [x] 升级加权抽取与宝箱/升级选择态基础逻辑
- [x] 右键限定自动瞄准
- [x] Mamba 首次死亡复活
- [x] 敌人受眩晕停摆
- [x] 篮球反弹 / 普通 ricochet / 火箭爆炸首版

## 第二阶段待完成内容
- [x] SDL 文本渲染，真正把选择态/UI 变成可读界面
- [x] 更完整的激光武器行为（BeamSystem 首版替代 projectile 占位）
- [x] 更接近 Python 的 shop offer 加权与房间结算掉落
- [x] Boss/Elite 更完整 AI 与 phase-two 细分招式（标准 Boss + Laser 怪首版）
- [x] hazard / event 第一轮迁移（毒气云、爆炸桶/毒气桶/核弹、elite_turret 事件、治疗阻断）
- [~] 真机编译与一轮手感校准（已完成 clang 语法扫查，仍缺 CMake 真正链接）

## 已生成产物
- CMakeLists.txt
- cpp/src/core, math, platform, game, game/systems, frontends
- cpp/assets/data/*.json
- `.pipeline-workspace/spec.json`
- `.pipeline-workspace/plan.json`
- `.pipeline-workspace/architecture.json`

## 本轮新增
- [x] `HazardSystem` 独立落地并接入 `ProjectileSystem` / `BeamSystem` / `SkillSystem`
- [x] `RoomSystem` 接入 `nuke` / `elite_turret` 房间事件
- [x] `Game` 接入毒气云渲染、房间事件 warning、特殊障碍标识、辐射治疗阻断 HUD
- [x] 使用 NDK clang 对 `cpp/src`（除 SDL 前端）执行 `-fsyntax-only` 收口
- [ ] 等待 `cmake` 在当前 shell 可用后做 configure + build + 运行验证
