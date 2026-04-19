# resources 资源说明

This folder stores the sprites and animated frames now used by the game at runtime.
The game loads these PNG files first; only missing assets fall back to the old procedural drawing code.

## characters / 角色

- `characters/mamba.png`: player body for Mamba (曼巴), drawn at the player center.
- `characters/kunkun.png`: player body for Kunkun (坤坤), drawn at the player center.

## weapons / 武器

- `weapons/rifle.png`: held weapon sprite for `rifle`.
- `weapons/scatter.png`: held weapon sprite for `scatter`.
- `weapons/shotgun.png`: held weapon sprite for `shotgun`.
- `weapons/rail.png`: held weapon sprite for `rail`.
- `weapons/rocket.png`: held weapon sprite for `rocket`.
- `weapons/laser_burst.png`: held weapon sprite for `laser_burst` (脉冲激光); beam uses `effects/combat/laser_trace/`.
- `weapons/laser_lance.png`: held weapon sprite for `laser_lance` (棱镜重激光); beam uses `effects/combat/laser_lance_trace/`.

## bullets / 子弹

- `bullets/bullet.png`: friendly default bullet.
- `bullets/bullet_enemy.png`: enemy default bullet.
- `bullets/bullet_elite.png`: elite enemy bullet.
- `bullets/bullet_shock.png`: shock / pulse bullet.
- `bullets/shotgun_pellet.png`: shotgun pellet.
- `bullets/rocket.png`: rocket projectile in flight.
- `bullets/basketball.png`: basketball projectile used by Kunkun skill.

## enemies / 敌人

- `enemies/grunt.png`: basic enemy.
- `enemies/laser.png`: laser enemy.
- `enemies/shooter.png`: ranged shooter enemy.
- `enemies/shotgunner.png`: shotgun enemy.
- `enemies/charger.png`: charging melee enemy.
- `enemies/elite.png`: elite enemy.
- `enemies/boss.png`: normal boss.
- `enemies/challenge.png`: challenge boss.
- `enemies/engineer.png`: engineer-themed enemy.
- `enemies/turret.png`: normal turret.
- `enemies/elite_turret.png`: elite turret and `elite_turret` room event turret.
- `enemies/toxic_bloater.png`: toxic enemy paired with gas cloud effects.
- `enemies/reactor_bomber.png`: reactor / explosive enemy.

## map / 地图

- `map/wall.png`: solid wall.
- `map/cover.png`: default destructible cover.
- `map/crate.png`: crate cover.
- `map/bullet.png`: ammo-box style cover.
- `map/toxic.png`: toxic barrel / toxic obstacle.
- `map/reactor.png`: reactor obstacle.
- `map/nuke.png`: destroyable core used in the nuke room event.
- `map/treasure.png`: treasure room chest.
- `map/exit_active.png`: boss-room exit portal after clear.
- `map/north.png` / `map/north_locked.png`: north door open / locked.
- `map/east.png` / `map/east_locked.png`: east door open / locked.
- `map/south.png` / `map/south_locked.png`: south door open / locked.
- `map/west.png` / `map/west_locked.png`: west door open / locked.

## effects / 动效

- `effects/skills/pulse/`: pulse skill animation.
- `effects/skills/mamba_smash_startup/`: Mamba skill startup animation.
- `effects/skills/mamba_smash_impact/`: Mamba skill impact animation.
- `effects/combat/explosion_wave/`: explosion wave animation.
- `effects/combat/laser_trace/`: player `laser_burst` beam frames.
- `effects/combat/laser_lance_trace/`: player `laser_lance` beam frames.
- `effects/combat/enemy_laser_trace/`: enemy laser beam frames.
- `effects/telegraphs/boss_stomp/`: boss stomp telegraph.
- `effects/telegraphs/boss_nova/`: boss nova telegraph.
- `effects/telegraphs/challenge_dash_charge/`: challenge boss dash-charge telegraph.
- `effects/telegraphs/challenge_summon/`: challenge boss summon telegraph.
- `effects/telegraphs/enemy_laser/`: enemy laser lock telegraph.
- `effects/status/stun_marker/`: stun marker.
- `effects/status/poison_marker/`: poison marker.
- `effects/environment/gas_cloud/`: gas cloud animation.
- `effects/room_events/nuke/`: nuke room-event marker.
- `effects/room_events/elite_turret/`: elite turret room-event marker.
- `effects/ui/auto_aim/`: auto-aim lock ring.
- `effects/ui/screen_flash/`: full-screen flash.

## alignment / 对齐说明

- Characters and enemies use entity center + anchor alignment.
- Weapons are attached to the player hand and rotate with aim.
- Bullets use projectile center; `rocket` and `shotgun_pellet` rotate with travel direction.
- Laser traces are drawn per straight segment; `laser_burst`, `laser_lance`, and enemy laser no longer share one texture.
