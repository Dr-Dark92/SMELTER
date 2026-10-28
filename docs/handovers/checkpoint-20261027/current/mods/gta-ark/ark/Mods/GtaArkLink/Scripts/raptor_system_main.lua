-- Raptor system main loop.
local AGRO_module = require("raptor_aggro")
local ADAPTER_module = require("engine_adapter")

print("[RaptorAggro] LOADED successfully")
print("[ADAPTER] Current mode: " .. ADAPTER_module.get_adapter_type())

return true
