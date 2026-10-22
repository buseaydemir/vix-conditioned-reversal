Universe: current S&P 500 members (survivorship bias acknowledged)
Signal: 5-day sector-adjusted return (stock return minus its sector's average return)
Rebalance: weekly; signal at close of day t, trade at close of day t+1
Portfolio: long bottom decile, short top decile, equal weight, dollar-neutral
Costs: 5 bps per side (stress test: 10 bps)
Development period: 2005-2017. Test period: 2018-2026 (run once)
VIX rule: weight = clipped function of lagged VIX expanding-window percentile, range 0.5 to 1.5
Failure criterion: reversal returns are not higher after high VIX, or the rule does not beat the unconditional strategy after costs in the test period
Configurations tried: one