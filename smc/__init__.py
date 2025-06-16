from importlib import import_module
import sys

_module = import_module('smc_bot.smc')
for k, v in _module.__dict__.items():
    if not k.startswith('__'):
        globals()[k] = v
# expose submodules
sys.modules[__name__ + '.detectors'] = import_module('smc_bot.smc.detectors')
sys.modules[__name__ + '.SMCStrategyCore'] = import_module('smc_bot.smc.SMCStrategyCore')
