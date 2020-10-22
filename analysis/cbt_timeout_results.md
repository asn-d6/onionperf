## tor vanilla pareto

https://github.com/asn-d6/onionperf/blob/save_state_file/analysis/state_vanilla_pareto.png
https://github.com/asn-d6/onionperf/blob/save_state_file/analysis/state_vanilla_2_pareto.png

```2020-10-13 13:40:54 1602596454.75 650 BUILDTIMEOUT_SET COMPUTED TOTAL_TIMES=1000 TIMEOUT_MS=1500 XM=462 ALPHA=3.378735 CUTOFF_QUANTILE=0.800000 TIMEOUT_RATE=0.059899 CLOSE_MS=60000 CLOSE_RATE=0.017725```

**We can see Pareto not hugging nicely the tail of the timeout histogram.**

## abandon_cbt_abandoned (841d5a9c)

https://github.com/asn-d6/onionperf/blob/save_state_file/analysis/state_abandoned_841d5a9c_1_pareto.png
https://github.com/asn-d6/onionperf/blob/save_state_file/analysis/state_abandoned_841d5a9c_2_pareto.png

```2020-10-21 07:26:15 1603265175.49 650 BUILDTIMEOUT_SET COMPUTED TOTAL_TIMES=1000 TIMEOUT_MS=1500 XM=337 ALPHA=3.471656 CUTOFF_QUANTILE=0.800000 TIMEOUT_RATE=0.056886 CLOSE_MS=60000 CLOSE_RATE=0.019960```

**Perhaps a bit better but still not perfect?**

## abandon_cbt_abandoned (0edb2c9d0)

https://github.com/asn-d6/onionperf/blob/save_state_file/analysis/state_abandoned_0edb2c9d0_1_pareto.png

```2020-10-22 07:20:20 1603351220.40 650 BUILDTIMEOUT_SET COMPUTED TOTAL_TIMES=1000 TIMEOUT_MS=533 XM=385 ALPHA=4.927989 CUTOFF_QUANTILE=0.800000 TIMEOUT_RATE=0.180934 CLOSE_MS=60000 CLOSE_RATE=0.022374```

**Perfect!**


