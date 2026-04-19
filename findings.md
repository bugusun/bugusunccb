# Findings

## 关键发现补充

- `game/game.py` 约 8893 行，已明显承担状态机、输入、房间、战斗、AI、UI、渲染、音频等多重职责，必须拆分。
- Python 版严格更新顺序：玩家 -> 技能输入/效果 -> 子弹 -> 敌人 -> 拾取物 -> 毒气/爆炸/粒子/激光痕迹/浮字 -> 房间清空判定 -> 房门切换。
- 房间状态持久化通过 `room_states[room_id]` 完成，进入房间时把 enemies/pickups/layout.obstacles 恢复到当前运行态。
- 导航缓存通过 `(room_id, nav_version, radius)` 缓存；障碍破坏后 `nav_version += 1` 并清除该房缓存，这是必须保留的核心行为。
- 迷宫房门锁逻辑关键：未清房时允许 `retreat_door` 回撤，但前进门保持锁定。
- Boss 二阶段在 `hp <= max_hp * BOSS_PHASE_TWO_RATIO` 时触发，且会取消当前动作并重置导航恢复。
- 自动瞄准是隐藏输入：Python 版仅在按住鼠标右键时生效，而非默认常驻。
- 商店限购是房间级状态 `shop_purchases`，不是全局层级状态。
- 升级过滤依赖 weapon tags / weapon exclusive / character / active skill 四类规则，并且还要做上限截断。

## 本轮迁移新增发现

- 现有 C++ 骨架里，`multishot`、`ricochet`、`basketball`、`rocket_blast` 等升级/武器字段虽然已入状态，但此前很多并未真正参与运行时计算；这会造成“能抽到升级但体感无变化”的假迁移。
- `active_skill_id` 在骨架中已存在，但没有独立技能阶段；若继续把技能塞进 `Game::Tick`，会重新走向 God Object，因此单独增加 `SkillSystem` 是必要的。
- `revivesRemaining` 在第一版骨架里已初始化，但未被消费；这会导致 Mamba 被动名存实亡。当前已在子弹/接触伤害路径补上首次死亡复活消费。
- 选择态（升级、宝箱）若没有输入通道会直接卡死；因此平台输入层需要额外提供 1/2/3 选择事件，headless 前端也要给默认选项。
- Python 里 `accuracy/pierce/multishot` 对激光存在“应用时有转化逻辑、抽取规则却仍要求 bullet_weapon tag”的矛盾；这很像预留分支或未完全放开的设计，迁移时应保留实现但标记为可疑死路径。
- SDL 前端现已改为内建 5x7 位图字库；不依赖 SDL_ttf，但后续若要支持中文 UI，仍需单独引入字体管线。
- Boss 在 Python 中分“标准 Boss”和 `challenge boss` 两套；当前 C++ 本轮只补齐标准 Boss + Laser 怪路径，`challenge` 专属 dash/summon 仍是后续高风险项。
- 本轮 hazard/event 迁移后，**障碍破坏副作用终于被统一收口**：此前 projectile / beam / skill 各自减 HP，会导致“障碍爆了但没有毒气 / 爆炸 / 核弹 / 导航失效”的分裂行为；现在统一走 `HazardSystem::ApplyObstacleDamage`。
- `roomEvent` 先前在 `ResolveCurrentRoom` 中被直接 `reset`，这会破坏状态持久化；现已改成保留对象并打 `completed=true`，更接近 Python。
- 当前可用的本机工具链不是 MSVC，也不是 PATH 内 clang，而是 Android NDK 自带 clang；通过给它加 `--target=x86_64-none-linux-android24`，可以完成标准库可用的 `-fsyntax-only` 语法扫查。
- 实测语法检查先暴露出了一个**原有骨架问题**：`Vec2::DistanceSquared/Lerp` 在类内使用了尚未声明的自由运算符，clang 会报错；现已改成直接按坐标计算。

## 高风险迁移点

- `ProjectileSystem`：篮球无限弹射、普通子弹 ricochet、火箭爆炸、穿透与敌人死亡擦除会同时修改 `projectiles/enemies/obstacles`，非常容易出现迭代器失效和“删后再读”问题。
- `SkillSystem`：Mamba 重击既会位移玩家，又会打敌人、打障碍、触发导航失效，跨系统副作用多。
- `Game::Tick`：一旦 `LevelUp/RewardRoom/Dead` 切态时机不对，很容易把清房判定、门切换、交互顺序打乱。
- `UpgradeSystem`：升级抽取、升级适配、升级上限、技能专属升级四套规则叠在一起，最容易出现“可抽不可用”或“永远抽不到”的边界 bug。
- `RunState`：玩法迁移过程中新增了较多玩家技能运行态字段，后续若继续无节制扩张，需要拆到 `PlayerRuntimeSkillState` / `ChoiceState` 等子结构中，避免再次膨胀。
- `BeamSystem`：同一次 beam 会跨段命中障碍/敌人并伴随删除，若后续再加入特殊障碍链式效果（毒气桶/核弹），需要避免“命中表”和“擦除表”交叉失效。
- `HazardSystem`：链式爆炸现在已接上，但仍要警惕递归连锁时的索引失效；本轮通过给 `ObstacleState` 增加 `runtimeId`，把“先记录命中目标、后按 id 回查”作为规避手段。
- `RoomSystem` 的事件落点当前使用 `featureAnchors.front()` / `arena.Center()` 的简化策略，还没完全复刻 Python 的 `get_room_feature_points(..., collision_radius=...)` 采样过程；大多数房间可用，但复杂布局仍需复核。

## 可疑死路径 / 预留状态

- `RoomEventState.spawned` 被写入，但几乎未参与后续判定，疑似预留字段。
- `RoomState.encounter_spawned` 也只在准备房间时写入，当前逻辑没有消费，疑似统计/调试残留。
- Python 版将 `RoomLayout.obstacles` 作为运行期可变对象反复覆盖，这会让“静态布局定义”和“运行态障碍”耦合在一起；C++ 版已改为 `RoomLayout.initialObstacles + RoomState.obstacles` 双层结构，避免别名问题。
- 自动瞄准使用右键这一点与部分文案不完全一致，迁移时需要明确是保留为隐藏高级操作还是改成设置开关。
- Python 中激光升级转化分支与升级过滤规则并不完全一致，当前更像“预留给后续放开规则”的半死路径；如后续确认要开放激光吃 `accuracy/multishot/pierce`，应先调整数据规则，而不是只改 ApplyUpgrade。
- `radiation` 在 Python 中除了“禁止回血”外，还会给玩家攻击附加中毒；本轮 C++ 只迁了**治疗阻断**，尚未把“辐射期间攻击附毒”接回去，这是当前 hazard 子系统里最大的已知残缺点。
- Python 的精英炮塔火箭还有 homing 参数；当前 C++ 先保留了火箭型投射物与事件生成，但追踪行为仍是简化版。
