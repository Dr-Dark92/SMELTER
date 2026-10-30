-- Generic provider-admission module.
-- Requires a table with six functions and returns an adapter table or nil,reason.

local M = {}

M.adapter_type = "uninitialized"

function M.new(provider)
  if type(provider) ~= "table" then
    return nil, "unsupported_runtime"
  end
  local required = {"position", "describe", "candidates", "move_to", "attack", "stop"}
  for _, func_name in ipairs(required) do
    if type(provider[func_name]) ~= "function" then
      return nil, "unsupported_capability:" .. func_name
    end
  end
  return provider, nil
end

function M.get_adapter_type()
  return M.adapter_type or "uninitialized"
end

function M.init_simulation(provider)
  M.adapter_type = "uninitialized"
  local adapter, reason = M.new(provider)
  if adapter == nil then
    return nil, reason or "invalid_provider"
  end
  M.adapter_type = "simulation"
  return adapter
end

function M.init_real_game(provider)
  M.adapter_type = "uninitialized"
  local adapter, reason = M.new(provider)
  if adapter == nil then
    return nil, reason or "invalid_provider"
  end
  M.adapter_type = "provider"
  return adapter
end

function M.spawn_raptor(...)
  return nil, "unsupported_capability:spawn"
end

return M