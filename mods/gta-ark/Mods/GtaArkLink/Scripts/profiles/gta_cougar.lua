-- GTA Cougar profile definition.
-- Initial offline tuning values; runtime_verified=false does not confirm GTA capability.
return {
  units = "metres",
  clock_units = "seconds",
  asset_id = "a_c_mtlion",
  runtime_verified = false,
  profile = {
    detect_radius = 10,
    attack_radius = 2,
    lose_radius = 20,
    attack_cooldown = 3
  },
  policy = {
    allowed_kinds = {character = true},
    blocked_kinds = {vehicle = true},
    required_traits = {human = true}
  }
}
