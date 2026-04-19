# Progress

- 2026-04-19: 开始执行 pygame -> C++ 迁移分析与骨架搭建。
- 2026-04-19: 继续推进第二阶段玩法迁移：加入 SkillSystem、升级/宝箱选择流、角色技能运行态、右键限定自动瞄准、篮球/反弹/火箭爆炸等核心行为草案。
- 2026-04-19: 补齐 A/B/C：SDL 位图文本渲染、激光 BeamSystem 首版、商店/奖励软权重抽样、Boss 招式化 AI 与可视 telegraph。
- 2026-04-19: 继续迁移 hazard / event：补上 HazardSystem、毒气云、爆炸桶/毒气桶/核弹桶、nuke / elite_turret 房间事件、治疗阻断与一轮 clang 语法收口。

## 进展更新

- 已创建 `cpp/` 目录与 `CMakeLists.txt`。
- 已落地数学层（Vec2/Rect/Geometry）、核心类型、运行态、导航缓存、世界工厂、系统拆分、Game 编排层、headless/SDL 前端骨架。
- 已补充 `SkillSystem`，并把固定步更新顺序调整为：玩家 -> 技能输入/效果 -> 子弹 -> 敌人 -> 拾取 -> 效果 -> 清房 -> 门切换。
- 已加入主动技能首版运行态：
  - `pulse`：清弹 + 推怪 + 持续脉冲圈
  - `basketball`：弹射篮球
  - `mamba_smash`：起手蓄势后扇形重击
  - 长按 Q 的首版派生技能：先锋全屏震波、坤坤八向齐射
- 已把宝箱自动发奖励改成可选升级流；升级时也会进入 `LevelUp` 选择态。
- 已补回升级加权抽取、技能/角色专属升级上限、右键限定自动瞄准、Mamba 首次死亡复活、敌人受眩晕停摆、篮球/反弹/火箭爆炸等关键逻辑。
- 已补上 SDL 前端位图文本渲染、粗线段绘制、多行文字与可读化选择 UI / 商店卡片。
- 已新增 `BeamSystem`，把玩家激光从 projectile 占位改为瞬时 Beam：支持反射、可破坏障碍、命中反馈、导航缓存失效与激光痕迹渲染。
- 已把升级/商店抽取改为更接近 Python 的 `weighted_pick_unique`：重复 bucket 仅做 0.7 软惩罚，而非硬排斥；商店改为 1 个 sustain + 4 个加权 offer。
- 已补齐 Boss 首版动作化 AI：二阶段切换、践踏 telegraph、nova telegraph、相位二火箭，以及 Laser 敌人 telegraph + 发射。
- 已新增 `HazardSystem`，统一承接障碍破坏副作用：毒气云、反应堆爆炸、子弹桶散射、核弹爆炸、辐射 buff、治疗阻断。
- 已把 `RoomSystem` 接到房间事件：`nuke` 会生成可破坏核弹障碍，`elite_turret` 会在入房时生成精英炮塔；房间事件完成态改为持久化而非直接 reset。
- 已把 `ProjectileSystem` / `BeamSystem` / `SkillSystem` 的障碍伤害改为走统一 hazard 路径，保证破坏障碍时导航缓存失效与连锁事件能正确触发。
- 已补充一次真实语法检查：使用 NDK clang 的 `--target=x86_64-none-linux-android24 -fsyntax-only` 对 `cpp/src`（除 SDL 前端）逐文件扫过，当前通过。
- 当前 shell 中 `cmake` 仍不可用，`python -m cmake` 也不存在；因此这轮仍未完成真正的 CMake configure / build / run。
- 当前状态可视为“已通过一轮 clang 语法收口的可编译草案”，仍需在具备 `cmake + 真正本机编译器` 的环境里完成最终链接与手感校正。
