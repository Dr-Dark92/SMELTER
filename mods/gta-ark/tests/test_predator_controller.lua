package.path = "Mods/GtaArkLink/Scripts/?.lua;" .. package.path
local controller = require("predator_controller")
assert(type(controller.new) == "function", "predator_controller.new must exist")