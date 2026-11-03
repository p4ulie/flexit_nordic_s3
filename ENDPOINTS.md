# Flexit Nordic BACnet objects

This file lists every BACnet object the Flexit Nordic controller exposes. These objects are the unit's "endpoints". See [README.md](README.md) for how to connect.

> **Source.** Flexit's official point list (`bacnet-nordic-basic_2963.xlsx`) has been removed from flexit.no: it returns 404 on .no, .se and .com, and the Wayback Machine never saved a copy.
> The table below is generated from [`bac0_points_dump.txt`](https://github.com/piotrbulinski/flexit_bacnet/blob/main/bac0_points_dump.txt), a dump of a real Nordic unit in the
> `flexit-bacnet` library's repo. Descriptions are Flexit's own object descriptions. The example values come from that one unit, not from this one.
> The dump has no read/write flags or state-text lists. Those are filled in below only for the objects the library uses, as listed in its
> [`nordic.py`](https://github.com/piotrbulinski/flexit_bacnet/blob/main/flexit_bacnet/nordic.py), which was itself built from the xlsx.

## Addressing

Every object is addressed as **`<object-type>,<instance>`**, for example `multi-state-value,42`. A read or write targets that object's `present-value` property (85).

| Object type | Number | Value type when writing |
|---|---:|---|
| `analog-input` | 0 | read-only |
| `analog-output` | 1 | read-only in practice (actuator signal) |
| `analog-value` | 2 | REAL |
| `binary-input` | 3 | read-only |
| `binary-output` | 4 | read-only in practice |
| `binary-value` | 5 | ENUMERATED (`0` inactive, `1` active) |
| `multi-state-value` | 19 | UNSIGNED (states start at 1) |
| `positive-integer-value` | 48 | UNSIGNED |

Objects marked **priority 13** are written at priority 13 by `flexit-bacnet`, so use the same priority. In BACnet, a write at a higher priority (a lower number) overrides lower ones until it is relinquished. A write at a lower priority is ignored while a higher one is set. Objects without a priority use the default, 16.

## Writable objects used for control

Each of these is used by `flexit-bacnet`, the library behind the Home Assistant integration, so they are known to work.

### Modes

| Object | Priority | Meaning | Values |
|---|---:|---|---|
| `binary-value,50` | 13 | Comfort (HOME/AWAY) button | `1` follow the ventilation mode · `0` drop to Away after the delay in `positive-integer-value,318` |
| `positive-integer-value,318` | – | Comfort button off-delay | minutes (0–600) |
| `multi-state-value,42` | 13 | Ventilation mode. Honoured only while `binary-value,50` = 1 | `1` Stop · `2` Away · `3` Home · `4` High |
| `multi-state-value,361` | read-only | Operation mode (heat exchanger state) | `1` Off · `2` Away · `3` Home · `4` High · `5` Cooker hood · `6` Fireplace · `7` Temporary high |

### Temporary modes

| Object | Priority | Meaning | Values |
|---|---:|---|---|
| `positive-integer-value,293` | – | Rapid ventilation (boost) runtime | minutes (1–360) |
| `multi-state-value,357` | – | Rapid ventilation trigger | write `2` to start |
| `analog-value,2031` | read-only | Rapid ventilation remaining | minutes |
| `positive-integer-value,270` | – | Fireplace ventilation runtime | minutes (1–360) |
| `multi-state-value,360` | – | Fireplace ventilation trigger | write `2` to start |
| `analog-value,2038` | read-only | Fireplace ventilation remaining | minutes |
| `binary-value,400` | read-only | Fireplace mode active | `0` / `1` |
| `binary-value,402` | 13 | Cooker hood | `1` on · `0` off |

### Temperature setpoints

| Object | Meaning | Unit |
|---|---|---|
| `analog-value,1994` | Air temperature setpoint HOME | °C |
| `analog-value,1985` | Air temperature setpoint AWAY | °C |

### Fan setpoints (fan speed per mode)

| Object | Supply air | Object | Exhaust air |
|---|---|---|---|
| `analog-value,1836` | HOME % | `analog-value,1841` | HOME % |
| `analog-value,1837` | AWAY % | `analog-value,1842` | AWAY % |
| `analog-value,1835` | HIGH % | `analog-value,1840` | HIGH % |
| `analog-value,1838` | FIREPLACE % | `analog-value,1843` | FIREPLACE % |
| `analog-value,1839` | COOKER HOOD % | `analog-value,1844` | COOKER HOOD % |

### Heater and filter

| Object | Meaning | Values |
|---|---|---|
| `binary-value,445` | Electric heater enable | `1` on · `0` off |
| `analog-value,190` | Electric heater nominal power | kW (read-only) |
| `analog-value,285` | Filter operating time | hours (read-only) |
| `analog-value,286` | Filter exchange interval | hours |
| `binary-value,522` | Filter polluted | `1` = replace filter (read-only) |
| `multi-state-value,613` | Filter timer reset | write `2` to reset |

### Write examples

```python
from flexit_bacnet import FlexitBACnet
unit = FlexitBACnet(host, device_id)
await unit.update()
await unit.activate_comfort_button()            # binary-value,50 = 1 @13
await unit.set_ventilation_mode(3)              # multi-state-value,42 = 3 @13 (Home)
await unit.set_air_temp_setpoint_home(21.0)     # analog-value,1994 = 21.0
await unit.start_rapid_ventilation(30)          # positive-integer-value,293 = 30, then multi-state-value,357 = 2
```

```sh
# bacnet-stack: bacwp <device> <type> <instance> <property> <priority> <index> <tag> <value>  (tags: 2 unsigned, 4 real, 9 enumerated)
bacwp 2 5 50 85 13 -1 9 1          # comfort button on
bacwp 2 19 42 85 13 -1 2 3         # ventilation mode Home
bacwp 2 2 1994 85 16 -1 4 21.0     # HOME setpoint 21 °C
```

## All objects

These are all 653 objects from the dump, sorted by object type and instance. "Internal name" is the object's path inside the controller application.
To decode multi-state values, read the object's `state-text` property (110) from the unit. For example, run `bacrp <device> 19 <instance> 110`.

**Positive-integer values** (type 48), such as instances 270, 293 and 318 above, are missing from the dump because BAC0 doesn't scan that object type.
The unit may expose more of them than the three the library uses.

### Analog inputs (sensors)

`analog-input` · object type 0 · 27 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 1 | Outside air temperature | 11.91 | degreesCelsius | `R(1)'TOa` |
| 4 | Supply air temperature | 21.8 | degreesCelsius | `R(1)'TSu` |
| 5 | Tacho, supply fan | 3108 | revolutionsPerMinute | `R(1)'FanSuSpdFb` |
| 11 | Exhaust air temperature | 15.08 | degreesCelsius | `R(1)'TEh` |
| 12 | Tacho, exhaust fan | 3068 | revolutionsPerMinute | `R(1)'FanEhSpdFb` |
| 59 | Extract air temperature | 21.91 | degreesCelsius | `R(1)'TEx` |
| 71 | Temperature, supply air after rotor | 0 | degreesCelsius | `R(1)'IOExtnDevEcul'TSuAfHExg` |
| 72 | Air flow, pressure exhaust fan | 0 | pascals | `R(1)'IOExtnDevEcul'DiffPFanEh` |
| 73 | Air flow, pressure supply fan | 0 | pascals | `R(1)'IOExtnDevEcul'DiffPFanSu` |
| 75 | Room temperature | 22.44 | degreesCelsius | `R(1)'ROpUnDev'TR` |
| 77 | Air quality, input value | 0 | partsPerMillion | `R(1)'IOExtnDevEcul'AQualRIn` |
| 78 | Extract air pressure | 0 | pascals | `R(1)'PDuctDevQbm'PEx` |
| 79 | Supply air pressure | 0 | pascals | `R(1)'PDuctDevQbm'PSu` |
| 80 | Maximum room temperature RF system | 0 | degreesCelsius | `R(1)'FanNodeDev'TRMaxRfqs` |
| 81 | Maximum room air humidity RF system | 0 | percent | `R(1)'FanNodeDev'HuRMaxRfqs` |
| 82 | Maximum room air quality RF system | 0 | partsPerMillion | `R(1)'FanNodeDev'AQualRMaxRfqs` |
| 83 | Room temperature VMSH 1 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh1'TRVmsh1` |
| 84 | Room air humidity VMSH 1 | 0 | percent | `R(1)'ROpUnDevVmsh1'HuRVmsh1` |
| 85 | Room dew point temperature VMSH 1 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh1'TDwpRVmsh1` |
| 86 | Room temperature VMSH 2 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh2'TRVmsh2` |
| 87 | Room air humidity VMSH 2 | 0 | percent | `R(1)'ROpUnDevVmsh2'HuRVmsh2` |
| 88 | Room dew point temperature VMSH 2 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh2'TDwpRVmsh2` |
| 89 | Room temperature VMSH 3 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh3'TRVmsh3` |
| 90 | Room air humidity VMSH 3 | 0 | percent | `R(1)'ROpUnDevVmsh3'HuRVmsh3` |
| 91 | Room dew point temperature VMSH 3 | 0 | degreesCelsius | `R(1)'ROpUnDevVmsh3'TDwpRVmsh3` |
| 92 | Air quality, max value RF | 0 | partsPerMillion | `R(1)'ROpUnDevVmsc'AQualRVmsc` |
| 93 | Inputs state VMC | 0 |  | `R(1)'IOExtnDevVmc'InStaVmc` |

### Analog outputs (actuator signals)

`analog-output` · object type 1 · 5 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 0 | Rotating heat exchanger | 100 | percent | `R(1)'RotHExgSpd` |
| 3 | Fan speed, supply air | 70 | percent | `R(1)'FanSuSpd` |
| 4 | Fan speed, exhaust air | 70 | percent | `R(1)'FanEhSpd` |
| 28 | Cooling, valve position | 0 | percent | `R(1)'IOExtnDevEcul'CclVlvPos(1)` |
| 29 | Heating battery, electrical | 59.9 | percent | `R(1)'HclElPos` |

### Analog values (setpoints, parameters, calculated values)

`analog-value` · object type 2 · 263 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 0 | Diagnostics for automation station | 2 |  | `Infra'DiagAs` |
| 3 | Diagnostics for KNX PL-Link bus | 1 |  | `PlnkBus'DiagPlnkBus` |
| 5 | Result of room temperature | 22.44 | degreesCelsius | `R(1)'RHvacCoo'TRCol'TRRs` |
| 8 | Alarm, code type A | 0 |  | `R(1)'RHvacCoo'AlmFnct'AalmCode` |
| 56 | Fire alarm, limit supply air | 72 | degreesCelsius | `R(1)'RHvacCoo'SftyCtl'TSuFireAlmLm` |
| 57 | Maint.alarm, max limit supply air | 60 | degreesCelsius | `R(1)'RHvacCoo'SftyCtl'TSuHiAlmLm` |
| 58 | Maint.alarm, min limit supply air | 0 | degreesCelsius | `R(1)'RHvacCoo'SftyCtl'TSuLoAlmLm` |
| 59 | Fire alarm, limit extract air | 72 | degreesCelsius | `R(1)'RHvacCoo'SftyCtl'TExFireAlmLm` |
| 69 | Present cooling setpoint for comfort | 24.5 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'PrSpCCmf` |
| 70 | Present cooling setpoint for pre-comfort | 26 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'PrSpCPcf` |
| 71 | Present cooling setpoint for economy | 30 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'PrSpCEco` |
| 72 | Present cooling setpoint for protection | 32 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'PrSpCPrt` |
| 73 | Present cooling setpoint | 26 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'PrSpC` |
| 75 | Cooling, setpoint end value shift | 40 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'EndSpShftC` |
| 76 | Cooling, outdoor air limit for release | 20 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'CLmCmf` |
| 78 | Cooling setpoint start value shift | 30 | degreesCelsius | `R(1)'RHvacCoo'TCtlC'SttSpShftC` |
| 79 | Cooling, setpoint for shift | 0 | degreesKelvin | `R(1)'RHvacCoo'TCtlC'SpShftC` |
| 96 | Present heating setpoint for comfort | 23.5 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'PrSpHCmf` |
| 97 | Present heating setpoint for pre-comfort | 23 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'PrSpHPcf` |
| 98 | Present heating setpoint for economy | 23 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'PrSpHEco` |
| 99 | Present heating setpoint for protection | 10 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'PrSpHPrt` |
| 100 | Present heating setpoint | 23 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'PrSpH` |
| 102 | Heating, setpoint end value shift | -15 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'EndSpShftH` |
| 103 | Heating limit comfort | 99.9 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'HLmCmf` |
| 104 | Outs.air temp.limit to start correction | -5 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'TOaLmSttCorr` |
| 106 | Heating, setpoint start value shift | -5 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'SttSpShftH` |
| 107 | Heating, setpoint for shift | 0 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'SpShftH` |
| 126 | Room temperature setpoint | 24 | degreesCelsius | `R(1)'RHvacCoo'SpTRDtr'SpTR` |
| 127 | Room temperature setpoint shift | 0 | degreesKelvin | `R(1)'RHvacCoo'SpTRDtr'SpTRShft` |
| 130 | Alarm, state code B | 0 |  | `R(1)'RHvacCoo'MntnFnct'BalmCode` |
| 131 | Effective room temperature | 21.91 | degreesCelsius | `R(1)'HVAC'TREff` |
| 132 | Present setpoint supply temperature | 23 | degreesCelsius | `R(1)'HVAC'PrSpTSu` |
| 134 | Rotating heat exchanger, cooling Kp | 10 | code 623 | `R(1)'HVAC'Erc'GainRotHxCtrC` |
| 135 | Rotating heat exchanger, heating Kp | 10 | code 623 | `R(1)'HVAC'Erc'GainRotHxCtrH` |
| 136 | Cooling, dT B3-B4 start | 4 | degreesKelvin | `R(1)'HVAC'Erc'DiffTRTOaMinC` |
| 140 | De-icing, humidity comp. Start | 80 | percent | `R(1)'HVAC'Erc'SstHuCmpDeic` |
| 142 | De-icing, humidity comp. End | 20 | percent | `R(1)'HVAC'Erc'EndHuCmpDeic` |
| 144 | Rotary heat exchanger heating request | 100 | percent | `R(1)'HVAC'Erc'RotHExgHReq` |
| 145 | Rotary heat exchanger cooling request | 0 | percent | `R(1)'HVAC'Erc'RotHExgCReq` |
| 147 | Rotating heat exchanger , min speed | 0 | percent | `R(1)'HVAC'Erc'RotHExgSpdMin` |
| 148 | Rotating heat exchanger , max speed | 100 | percent | `R(1)'HVAC'Erc'RotHExgSpdMax` |
| 189 | Switch-on point for air flow hold heat. | 4 | percent | `R(1)'HVAC'Hcl'SwiOnAirFlHldH` |
| 190 | Electric heater, nom. Power | 0.8 | kilowatts | `R(1)'HVAC'Hcl'NomElPwr` |
| 194 | Heating coil electric power | 0.471 | kilowatts | `R(1)'HVAC'Hcl'HclElPwr` |
| 195 | Heating coil heating request minimum | 35.45 | percent | `R(1)'HVAC'Hcl'HclHReqMin` |
| 196 | Heating coil heating request | 59.09 | percent | `R(1)'HVAC'Hcl'HclHReq` |
| 197 | Supply, heater, Kp zone 2 | 5 | code 623 | `R(1)'HVAC'Hcl'GainHclTSuCtrH` |
| 285 | Air filter, operating time | 24 | hours | `R(1)'HVAC'AlmBdl'TiOpFil` |
| 286 | Air filter, time period for exchange | 4380 | hours | `R(1)'HVAC'AlmBdl'TiOpFilRpc` |
| 296 | Diagnostics for Modbus | 0 |  | `ModBus'DiagModBus` |
| 297 | Diagnostics for I/O bus | 3 |  | `IOBus'DiagIOBus` |
| 1794 | Present A-Alarm code | 0 |  | `R(1)'RHvacCoo'AlmFnct'PrAalmCode` |
| 1796 | Diagnostics for ECUL | 8 |  | `R(1)'IOExtnDevEcul'DiagEcul` |
| 1814 | Time counter, FIRE | 0 | hours | `R(1)'RHvacCoo'FplcVntOp'OphFplcVnt` |
| 1820 | Time counter, cooker hood | 0 | hours | `R(1)'RHvacCoo'FhVntOp'OphFhVnt` |
| 1831 | Air quality, present setpoint | 700 | partsPerMillion | `R(1)'RHvacCoo'VntCtl'PrSpVnt` |
| 1832 | Air quality, setpoint  HIGH | 1500 | partsPerMillion | `R(1)'RHvacCoo'VntCtl'SpAQualRCmf` |
| 1833 | Air quality, setpoint  HOME | 700 | partsPerMillion | `R(1)'RHvacCoo'VntCtl'SpAQualRPcf` |
| 1834 | Air quality, setpoint  AWAY | 700 | partsPerMillion | `R(1)'RHvacCoo'VntCtl'SpAQualREco` |
| 1835 | Linear, setpoint supply air HIGH | 100 | percent | `R(1)'RHvacCoo'VntCtl'SpFanSuSpdHi` |
| 1836 | Linear, setpoint supply air HOME | 70 | percent | `R(1)'RHvacCoo'VntCtl'SpFanSuSpdHome` |
| 1837 | Linear, setpoint supply air AWAY | 50 | percent | `R(1)'RHvacCoo'VntCtl'SpFanSuSpdAway` |
| 1838 | Linear, setpoint supply air FIRE | 90 | percent | `R(1)'RHvacCoo'VntCtl'SpFanSuSpdFplc` |
| 1839 | Linear, setpoint supply air COOKER | 90 | percent | `R(1)'RHvacCoo'VntCtl'SpFanSuSpdCkr` |
| 1840 | Linear, setpoint exhaust air HIGH | 100 | percent | `R(1)'RHvacCoo'VntCtl'SpFanEhSpdHi` |
| 1841 | Linear, setpoint exhaust air HOME | 70 | percent | `R(1)'RHvacCoo'VntCtl'SpFanEhSpdHome` |
| 1842 | Linear, setpoint exhaust air AWAY | 50 | percent | `R(1)'RHvacCoo'VntCtl'SpFanEhSpdAway` |
| 1843 | Linear, setpoint exhaust air FIRE | 50 | percent | `R(1)'RHvacCoo'VntCtl'SpFanEhSpdFplc` |
| 1844 | Linear, setpoint exhaust air COOKER | 50 | percent | `R(1)'RHvacCoo'VntCtl'SpFanEhSpdCkr` |
| 1845 | Gain for ventilation controller | 0.23 | code 625 | `R(1)'RHvacCoo'VntCtl'GainVntCtr` |
| 1846 | Present B-Alarm code | 0 |  | `R(1)'RHvacCoo'MntnFnct'PrBalmCode` |
| 1847 | Operating hours, total time | 8760 | hours | `R(1)'HVAC'AlmBdl'OphDev` |
| 1849 | De-icing, humidity comp. Delta | 1.5 | degreesKelvin | `R(1)'HVAC'Erc'DiffTHuCmpDeic` |
| 1850 | Belt broken, delta B3-B6 | 4 | degreesKelvin | `R(1)'HVAC'Erc'DTRotHxBltFlt` |
| 1851 | Time counter, op. time RMC | 8096 | hours | `R(1)'HVAC'Erc'OphErc` |
| 1852 | De-icing, rotor speed | 100 | percent | `R(1)'HVAC'Erc'RotHExgSpdDeic` |
| 1869 | Air quality, present fan control | 0 | percent | `R(1)'HVAC'FanSu'FanVntReq` |
| 1870 | Humidity, present fan control | 0 | percent | `R(1)'HVAC'FanSu'FanDhuReq` |
| 1878 | De-icing, setpoint supply fan speed | 15 | percent | `R(1)'HVAC'FanSu'SpFanSuSpdDeic` |
| 1879 | Time counter, op. time - El. heater | 4184 | hours | `R(1)'HVAC'Hcl'OphHcl` |
| 1913 | Time counter, STOP | 0 | hours | `R(1)'ROpModDtr'OphStop` |
| 1914 | Time counter, AWAY | 0 | hours | `R(1)'ROpModDtr'OphAway` |
| 1915 | Time counter, HOME | 7760 | hours | `R(1)'ROpModDtr'OphHome` |
| 1916 | Time counter, HIGH | 980 | hours | `R(1)'ROpModDtr'OphHi` |
| 1919 | Air quality, max value | 0 | partsPerMillion | `R(1)'RHvacCoo'AQualRCol'AQualRRs` |
| 1920 | Air temp., setpoint | 24 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'SpTHrv` |
| 1921 | Air temp., delta setpoint heating HOME | 1 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'DSpHHome` |
| 1922 | Supply, delta HOME | 1 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'NzTHrv` |
| 1926 | Air temp., delta setpoint cooling HOME | 2 | degreesKelvin | `R(1)'RHvacCoo'TCtlC'DSpCHome` |
| 1933 | Free cooling, d B3-setpoint  start | 2 | degreesKelvin | `R(1)'RHvacCoo'FreeCDtr'HysSpTR` |
| 1934 | Outside air temp.limit | 14 | degreesCelsius | `R(1)'RHvacCoo'FreeCDtr'TOaLm` |
| 1935 | Free cooling, d B4-setpoint | 2 | degreesKelvin | `R(1)'RHvacCoo'FreeCDtr'HysTOaLm` |
| 1936 | Free cooling, dT B3-B4 start | 4 | degreesKelvin | `R(1)'RHvacCoo'FreeCDtr'DiffTRTOaSwiOn` |
| 1937 | Free cooling, dT B3-B4 stop | 2 | degreesKelvin | `R(1)'RHvacCoo'FreeCDtr'DiffTRTOaSwiOf` |
| 1938 | De-icing, setpoint fan start | 0 | degreesCelsius | `R(1)'HVAC'Erc'SpTDeicFan` |
| 1939 | De-icing, setpoint rotor start | 0 | degreesCelsius | `R(1)'HVAC'Erc'SpTDeicHExg` |
| 1940 | Heat exchanger, skip speed end | 0 | percent | `R(1)'HVAC'Erc'RotHxSkipSpdHi` |
| 1941 | Heat exchanger, skip speed start | 0 | percent | `R(1)'HVAC'Erc'RotHxSkipSpdLo` |
| 1942 | Heat exchanger, ramp down start | 0 | degreesCelsius | `R(1)'HVAC'Erc'TDeicTiOffStt` |
| 1943 | Heat exchanger, ramp down end | -9 | degreesCelsius | `R(1)'HVAC'Erc'TDeicTiOffEnd` |
| 1948 | Tacho, alarm limit fan speed | 100 | revolutionsPerMinute | `R(1)'HVAC'FanSu'FanSpdFbFltLm` |
| 1958 | De-icing, setpoint exhaust fan speed | 75 | percent | `R(1)'HVAC'FanEh'SpFanEhSpdDeic` |
| 1977 | Supply air, setpoint for heating | 23 | degreesCelsius | `R(1)'HVAC'Hcl'SpTSuHcl` |
| 1978 | Belt broken, delta B3-B4 | 10 | degreesKelvin | `R(1)'HVAC'Erc'DiffTExTOaMin` |
| 1983 | Diagnostics value | 0 |  | `R(1)'HVAC'DiagVal` |
| 1984 | Heating, present setpoint shift | 0 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'PrSpShftH` |
| 1985 | Air temp., setpoint AWAY | 17 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'SpTAway` |
| 1986 | Supply, delta AWAY | 1 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'NzTAway` |
| 1987 | Air temp., delta setpoint heating AWAY | 1 | degreesKelvin | `R(1)'RHvacCoo'TCtlH'DSpHAway` |
| 1991 | Cooling, present setpoint shift | 0 | degreesKelvin | `R(1)'RHvacCoo'TCtlC'PrSpShftC` |
| 1992 | Air temp., delta setpoint cooling AWAY | 6 | degreesKelvin | `R(1)'RHvacCoo'TCtlC'DSpCAway` |
| 1994 | Air temp., setpoint HOME | 24 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'SpTHome` |
| 1997 | Heating coil position | 59.18 | percent | `R(1)'HVAC'HclPos` |
| 2004 | Time for temporary rapid ventilation | 0 |  | `R(1)'ROpUnDev'TiTmpRpdVnt` |
| 2005 | Remaining time temporary ventilation op. | 0 |  | `R(1)'ROpUnDev'TiRmgTmpVntOp` |
| 2006 | Pres.setp.temp.for room operator unit | 24 | degreesCelsius | `R(1)'ROpUnDev'PrSpTRu` |
| 2007 | Time for temporary fireplace ventilation | 0 |  | `R(1)'ROpUnDev'TiTmpFplcVnt` |
| 2023 | Rotating heat exchanger, efficiency | 68.3 | percent | `R(1)'HVAC'Erc'PrHExgEfcy` |
| 2025 | Alarm, no of displayed alarms in list | 1 |  | `R(1)'RHvacCoo'AlmBdl'FltListNum` |
| 2026 | Alarm, no of alarms in list | 1 |  | `R(1)'RHvacCoo'AlmBdl'FltCnt` |
| 2027 | Alarm, error code | 1020 |  | `R(1)'RHvacCoo'AlmBdl'DspyFltList` |
| 2028 | Fault counter 1 | 0 |  | `R(1)'RHvacCoo'AlmBdl'FltCnt1` |
| 2031 | Forced ventilation, remaining time | 1 | minutes | `R(1)'RHvacCoo'RpdVntOp'TiRmgRpdVnt` |
| 2038 | Speed FIRE, remaining time | 1 | minutes | `R(1)'RHvacCoo'FplcVntOp'TiRmgFplcVnt` |
| 2039 | Fault code for room operator unit | 0 |  | `R(1)'ROpUnDev'FltCodeRu` |
| 2040 | Maintenance code for room operator unit | 0 |  | `R(1)'ROpUnDev'MntnCodeRu` |
| 2042 | Room air quality | 0 | partsPerMillion | `R(1)'Modbus'AQualR(2)` |
| 2053 | Diagnostics for QBM | 8 |  | `R(1)'PDuctDevQbm'DiagQbm` |
| 2064 | Relative setpoint f.supply air fan speed | 70 | percent | `R(1)'HVAC'FanSu'SpFanSuSpdRel` |
| 2071 | Free cooling, setpoint room | 22 | degreesCelsius | `R(1)'RHvacCoo'TCtlH'SpTRFreeC` |
| 2076 | Setp.supply air temp.rotary heat exch. | 23.5 | degreesCelsius | `R(1)'HVAC'Erc'SpTSuRotHExg` |
| 2078 | Diagnostics BRDG | 8 |  | `R(1)'ComItfDevBrdg'DiagBrdg` |
| 2080 | Diagnostics FAN node | 9 |  | `R(1)'FanNodeDev'DiagFanNode` |
| 2081 | Time for tmp.op.mode outp.for RF system | 0 | minutes | `R(1)'FanNodeDev'TiTmpOpMOutRfq` |
| 2082 | Diagnostics VMN 1 | 8 |  | `R(1)'PshBtnDevVmn1'DiagVmn1` |
| 2083 | Diagnostics VMN 2 | 8 |  | `R(1)'PshBtnDevVmn2'DiagVmn2` |
| 2084 | Diagnostics VMN 3 | 8 |  | `R(1)'PshBtnDevVmn3'DiagVmn3` |
| 2085 | Diagnostics VMSH 1 | 8 |  | `R(1)'ROpUnDevVmsh1'DiagVmsh1` |
| 2086 | Diagnostics VMSH 2 | 8 |  | `R(1)'ROpUnDevVmsh2'DiagVmsh2` |
| 2087 | Diagnostics VMSH 3 | 8 |  | `R(1)'ROpUnDevVmsh3'DiagVmsh3` |
| 2088 | Diagnostics VMSC | 8 |  | `R(1)'ROpUnDevVmsc'DiagVmsc` |
| 2089 | Diagnostics VMC | 8 |  | `R(1)'IOExtnDevVmc'DiagVmc` |
| 2090 | Humidity, limit max value | 0 | percent | `R(1)'RHvacCoo'HuRelMax` |
| 2091 | Fan speed,  min | 30 | percent | `R(1)'HVAC'FanSu'FanSpdMinRel` |
| 2098 | Process val.1 for room air qual,on-board | 0 | partsPerMillion | `R(1)'PrpyExtdCnf'AQualROnbPrcv1(OnbIO)` |
| 2099 | Process val.2 for room air qual,on-board | 0 | partsPerMillion | `R(1)'PrpyExtdCnf'AQualROnbPrcv2(OnbIO)` |
| 2100 | Signal val.1 for room air qual.,on-board | 0 | volts | `R(1)'PrpyExtdCnf'AQualROnbSigv1(OnbIO)` |
| 2101 | Signal val.2 for room air qual.,on-board | 0 | volts | `R(1)'PrpyExtdCnf'AQualROnbSigv2(OnbIO)` |
| 2102 | Process val.1 for room air quality, ECU | 0 | partsPerMillion | `R(1)'PrpyExtdCnf'AQualREcuPrcv1(Ecu)` |
| 2103 | Process val.2 for room air quality, ECU | 2000 | partsPerMillion | `R(1)'PrpyExtdCnf'AQualREcuPrcv2(Ecu)` |
| 2104 | Signal value 1 for room air quality, ECU | 0 | millivolts | `R(1)'PrpyExtdCnf'AQualREcuSigv1(Ecu)` |
| 2105 | Signal value 2 for room air quality, ECU | 1e+04 | millivolts | `R(1)'PrpyExtdCnf'AQualREcuSigv2(Ecu)` |
| 2106 | Process val.1 for rel.humidity extr.air | 0 | percentRelativeHumidity | `R(1)'PrpyExtdCnf'HuRelExPrcv1` |
| 2107 | Process val.2 for rel.humidity extr.air | 0 | percentRelativeHumidity | `R(1)'PrpyExtdCnf'HuRelExPrcv2` |
| 2108 | Signal value 1 for rel.humidity extr.air | 0 | volts | `R(1)'PrpyExtdCnf'HuRelExSigv1` |
| 2109 | Signal value 2 for rel.humidity extr.air | 0 | volts | `R(1)'PrpyExtdCnf'HuRelExSigv2` |
| 2113 | Actual configuration of control funct.1 | 441 |  | `R(1)'RHvacCoo'ActlCnfCtl1` |
| 2114 | Actual configuration of control funct.2 | 1213 |  | `R(1)'HVAC'ActlCnfCtl2` |
| 2115 | Actual configuration of control funct.3 | 2001 |  | `R(1)'HVAC'ActlCnfCtl3` |
| 2118 | Actual hardware configuration 1 | 205 |  | `R(1)'HdwCnf'ActlHdwCnf1` |
| 2119 | Actual hardware configuration 2 | 203 |  | `R(1)'HdwCnf'ActlHdwCnf2` |
| 2120 | Actual hardware configuration 3 | 104 |  | `R(1)'HdwCnf'ActlHdwCnf3` |
| 2121 | Actual hardware configuration 4 | 1212 |  | `R(1)'HdwCnf'ActlHdwCnf4` |
| 2122 | Actual hardware configuration 5 | 111 |  | `R(1)'HdwCnf'ActlHdwCnf5` |
| 2125 | Operating mode input from RF system | 0 |  | `R(1)'FanNodeDev'OpModInRfqs` |
| 2197 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1001'AlmCode` |
| 2198 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1002'AlmCode` |
| 2199 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1003'AlmCode` |
| 2200 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1004'AlmCode` |
| 2201 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1005'AlmCode` |
| 2202 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1006'AlmCode` |
| 2203 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1007'AlmCode` |
| 2204 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1008'AlmCode` |
| 2205 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1009'AlmCode` |
| 2206 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1010'AlmCode` |
| 2207 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1011'AlmCode` |
| 2208 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1020'AlmCode` |
| 2209 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1032'AlmCode` |
| 2210 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1033'AlmCode` |
| 2211 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1034'AlmCode` |
| 2212 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1035'AlmCode` |
| 2213 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1040'AlmCode` |
| 2214 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2001'AlmCode` |
| 2215 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2002'AlmCode` |
| 2216 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2003'AlmCode` |
| 2217 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2004'AlmCode` |
| 2218 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2005'AlmCode` |
| 2219 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2007'AlmCode` |
| 2220 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2010'AlmCode` |
| 2221 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3001'AlmCode` |
| 2222 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3002'AlmCode` |
| 2223 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3003'AlmCode` |
| 2224 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3004'AlmCode` |
| 2225 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3006'AlmCode` |
| 2226 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm3007'AlmCode` |
| 2227 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2008'AlmCode` |
| 2228 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2009'AlmCode` |
| 2229 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2011'AlmCode` |
| 2230 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2014'AlmCode` |
| 2232 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2016'AlmCode` |
| 2233 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9001'AlmCode` |
| 2234 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9002'AlmCode` |
| 2235 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9003'AlmCode` |
| 2236 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9004'AlmCode` |
| 2237 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9005'AlmCode` |
| 2238 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9006'AlmCode` |
| 2239 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9007'AlmCode` |
| 2240 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9008'AlmCode` |
| 2241 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9009'AlmCode` |
| 2242 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9010'AlmCode` |
| 2243 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9011'AlmCode` |
| 2244 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9012'AlmCode` |
| 2245 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9013'AlmCode` |
| 2246 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9014'AlmCode` |
| 2247 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9015'AlmCode` |
| 2248 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9016'AlmCode` |
| 2249 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9017'AlmCode` |
| 2250 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9018'AlmCode` |
| 2251 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9019'AlmCode` |
| 2252 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9020'AlmCode` |
| 2253 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9021'AlmCode` |
| 2254 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9022'AlmCode` |
| 2255 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9023'AlmCode` |
| 2256 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9024'AlmCode` |
| 2257 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9025'AlmCode` |
| 2258 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9026'AlmCode` |
| 2259 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9027'AlmCode` |
| 2260 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm9028'AlmCode` |
| 2261 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1022'AlmCode` |
| 2262 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1023'AlmCode` |
| 2263 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1024'AlmCode` |
| 2264 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1025'AlmCode` |
| 2265 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1026'AlmCode` |
| 2266 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1027'AlmCode` |
| 2267 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1028'AlmCode` |
| 2268 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1029'AlmCode` |
| 2269 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1030'AlmCode` |
| 2270 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1036'AlmCode` |
| 2275 | State 1 | 0 |  | `R(1)'HdwCnf'Sta1` |
| 2276 | State 2 | 0 |  | `R(1)'HdwCnf'Sta2` |
| 2277 | State 3 | 0 |  | `R(1)'HdwCnf'Sta3` |
| 2278 | State 4 | 0 |  | `R(1)'HdwCnf'Sta4` |
| 2279 | State 5 | 0 |  | `R(1)'HdwCnf'Sta5` |
| 2280 | State 6 | 0 |  | `R(1)'HdwCnf'Sta6` |
| 2281 | State 7 | 0 |  | `R(1)'HdwCnf'Sta7` |
| 2282 | State 8 | 0 |  | `R(1)'HdwCnf'Sta8` |
| 2283 | State 9 | 0 |  | `R(1)'HdwCnf'Sta9` |
| 2284 | State 10 | 0 |  | `R(1)'HdwCnf'Sta10` |
| 2285 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2013'AlmCode` |
| 2289 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2018'AlmCode` |
| 2290 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm2019'AlmCode` |
| 2293 | Rotating heat exchanger speed feedback | 96.23 |  | `R(1)'HVAC'Erc'RotHExgSpdFb` |
| 2294 | Motor failure count | 0 |  | `R(1)'HVAC'Erc'RotHExgFailCnt` |
| 2297 | Alarm code | 0 |  | `R(1)'AlmHdl'Alm1039'AlmCode` |
| 2299 | Monitor BA to DAQ value | 180 |  | `RotHExgSpdcmdRPM` |
| 2300 | Monitor host MCU HAL speed value | 102 |  | `RotHExgSpdABIRPM` |
| 2301 | Monitor host MCU and motor MCU communication count | 3.043e+04 |  | `RotHExgSpdCOMUpCnt` |
| 2302 | Monitor motor short loop state | 0 |  | `RotHExgShortLoopState` |
| 2303 | Monitor DRV8305 register 1 | 0 |  | `RotHExg8305R1` |
| 2304 | Monitor DRV8305 register 2 | 0 |  | `RotHExg8305R2` |
| 2305 | Monitor DRV8305 register 3 | 0 |  | `RotHExg8305R3` |
| 2306 | Monitor DRV8305 register 4 | 0 |  | `RotHExg8305R4` |
| 2307 | Monitor Motor MCU running time | 9.122e+04 |  | `RotHExgFWRnTm` |

### Binary inputs

`binary-input` · object type 3 · 4 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 23 | Fume hood ventilation input | inactive |  | `R(1)'FhVntIn` |
| 31 | Speed AWAY activate DI | inactive |  | `R(1)'Away` |
| 33 | Fire thermostat, state | inactive |  | `R(1)'HclOvrTDet` |
| 82 | Speed HIGH activate DI | inactive |  | `R(1)'High` |

### Binary outputs

`binary-output` · object type 4 · 3 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 18 | Damper, outside air | active |  | `R(1)'DmpOaCmd` |
| 20 | Alarm, common output | inactive |  | `R(1)'CmnAlmIndOut` |
| 71 | Cooling, pump state | inactive |  | `R(1)'IOExtnDevEcul'CclPuCmd(1)` |

### Binary values (switches, alarms, states)

`binary-value` · object type 5 · 90 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 11 | Fire alarm | inactive |  | `R(1)'RHvacCoo'SftyCtl'FireAlm` |
| 15 | Forced ventilation | inactive |  | `R(1)'RHvacCoo'RpdVntOp'RpdVntOp` |
| 16 | Enable linear outside temp.compensation | inactive |  | `R(1)'RHvacCoo'TCtlH'EnLinTOaCmp` |
| 17 | Cool down request | inactive |  | `R(1)'RHvacCoo'PltModDtr'CoolDwnReq` |
| 18 | Warm-up request | inactive |  | `R(1)'RHvacCoo'PltModDtr'WarmUpReq` |
| 22 | Rotating heat exchanger , demand mode | inactive |  | `R(1)'HVAC'Erc'HExgEcmSta` |
| 25 | Rotary heat exchanger available f.heat. | active |  | `R(1)'HVAC'Erc'RotHExgAvlH` |
| 26 | Rotary heat exchanger available f.cool. | inactive |  | `R(1)'HVAC'Erc'RotHExgAvlC` |
| 38 | Heating coil available for heating | active |  | `R(1)'HVAC'Hcl'HclAvlH` |
| 50 | HOME/AWAY button status | active |  | `R(1)'ROpModDtr'CmfBtn` |
| 62 | Device mode | active |  | `R(1)'IOExtnDevEcul'DevMod` |
| 395 | Maintenance, activate | inactive |  | `R(1)'HVAC'MntnCmd` |
| 400 | Fireplace, state DI | inactive |  | `R(1)'RHvacCoo'FplcVntOp'FplcVnt` |
| 402 | Cooker hood, activate | inactive |  | `R(1)'RHvacCoo'FhVntOp'FhVnt` |
| 403 | Cacade control, sensor selection | active |  | `R(1)'RHvacCoo'EnTExCtl` |
| 404 | De-icing, rotor active | inactive |  | `R(1)'HVAC'Erc'DeicReqHExg` |
| 405 | De-icing, fan active | inactive |  | `R(1)'HVAC'Erc'DeicReqFan` |
| 406 | De-icing, enable | active |  | `R(1)'HVAC'Erc'EnDeic` |
| 409 | Fan available for ventilation | active |  | `R(1)'HVAC'FanSu'FanAvlVnt` |
| 410 | Fan available for dehumidification | active |  | `R(1)'HVAC'FanSu'FanAvlDhu` |
| 428 | Tacho, enable | active |  | `R(1)'HVAC'FanSu'EnFanSpdFbIn` |
| 429 | Zero pressure calibration trigger ECU | inactive |  | `R(1)'IOExtnDevEcul'ZePClbTrgEcu` |
| 430 | Fire damper, alarm | inactive |  | `R(1)'RHvacCoo'SftyCtl'FdpAlm` |
| 431 | Duct air temperature fire alarm | inactive |  | `R(1)'RHvacCoo'SftyCtl'TDuctFireAlm` |
| 434 | Exhaust air fan fault | inactive |  | `R(1)'HVAC'FanEhFlt` |
| 435 | Supply air fan fault | inactive |  | `R(1)'HVAC'FanSuFlt` |
| 436 | Energy recovery belt broken | inactive |  | `R(1)'HVAC'ErcBltBrk` |
| 438 | Max.rotary heat exchanger speed state | active |  | `R(1)'HVAC'Erc'RotHExgSpmaSta` |
| 440 | Heating coil state | active |  | `R(1)'HVAC'HclSta` |
| 445 | Electrical heater, OFF/ON | active |  | `R(1)'HVAC'Hcl'EnHclEl` |
| 452 | Reset temporary ventilation operation | inactive |  | `R(1)'ROpUnDev'RstTmpVntOp` |
| 453 | Temporary fireplace ventilation | inactive |  | `R(1)'ROpUnDev'TmpFplcVnt` |
| 454 | Temporary rapid ventilation | inactive |  | `R(1)'ROpUnDev'TmpRpdVnt` |
| 455 | Presence button for room operator unit | active |  | `R(1)'ROpUnDev'PscBtnRu` |
| 456 | Presence button input value | inactive |  | `R(1)'ROpUnDev'PscBtnIn` |
| 466 | Alarm, acknowledgement type B | inactive |  | `R(1)'RHvacCoo'MntnFnct'BalmAckd` |
| 467 | Fault list reset | inactive |  | `R(1)'RHvacCoo'AlmBdl'FltListRst` |
| 468 | A-Alarm acknowledged | inactive |  | `R(1)'RHvacCoo'AlmFnct'AalmAckd` |
| 469 | A-Alarm reset | inactive |  | `R(1)'RHvacCoo'AlmFnct'AalmRst` |
| 473 | Zero pressure calibration trigger QBM | inactive |  | `R(1)'PDuctDevQbm'ZePClbTrgQbm` |
| 474 | Scheduler, override | inactive |  | `R(1)'ROpModDtr'SchedRstManCnf` |
| 475 | Fireplace or fume hood ventilation input | inactive |  | `R(1)'ROpModDtr'FplcOrFhVntIn` |
| 476 | Backup of comfort button | inactive |  | `R(1)'ROpModDtr'BckpCmfBtn` |
| 478 | Enable free cooling | inactive |  | `R(1)'RHvacCoo'FreeCDtr'EnFreeC` |
| 489 | Configuration for IO extension ECUL | inactive |  | `R(1)'Modbus'IOExtnEcul'IOExtnEculCnf` |
| 491 | Rot.exch.motor stuck, stop before retry | inactive |  | `R(1)'PrpyExtdCnf'RoxStopBfRetry` |
| 495 | Emergency off activated | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm2001` |
| 496 | Smoke detector tripped | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm2002` |
| 497 | CO detector tripped | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm2003` |
| 498 | Fire alarm activated | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm2004` |
| 499 | Fire damper, position feedback fault | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm1009` |
| 500 | Supply air temp., operat.limits exceeded | inactive |  | `R(1)'RHvacCoo'AlmBdl'Alm2005` |
| 501 | Supply air temperature, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1001` |
| 502 | Frost prot.temp.heat.coil, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1005` |
| 503 | Supply air fan, speed feedback fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1010` |
| 504 | Exhaust air fan, speed feedback fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1011` |
| 505 | Heating coil, frost warning | inactive |  | `R(1)'HVAC'AlmBdl'Alm2007` |
| 506 | Reheating coil zone, overtemperature | inactive |  | `R(1)'HVAC'AlmBdl'Alm2009` |
| 507 | Heating coil, overtemperature | inactive |  | `R(1)'HVAC'AlmBdl'Alm2010` |
| 508 | Reheating coil zone, frost warning | inactive |  | `R(1)'HVAC'AlmBdl'Alm2011` |
| 509 | Heat pump air damper stops air flow | inactive |  | `R(1)'HVAC'AlmBdl'Alm2014` |
| 510 | Frost prot.temp.reheat.zone,sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1029` |
| 511 | Outside air temperature, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1004` |
| 512 | Rotary heat exchanger, motor stuck | inactive |  | `R(1)'HVAC'AlmBdl'Alm1007` |
| 513 | Rotary heat exchanger, belt broken | inactive |  | `R(1)'HVAC'AlmBdl'Alm1008` |
| 514 | Heat pump, common alarm | inactive |  | `R(1)'HVAC'AlmBdl'Alm2015` |
| 515 | Heat pump controller, Modbus comm.error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3001` |
| 516 | I/O exten.module 1, Modbus comm.error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3002` |
| 517 | I/O exten.module 2, Modbus comm.error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3003` |
| 518 | Diff.pressure sensor, Modbus comm.error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3004` |
| 519 | Exhaust air temperature, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1002` |
| 520 | Extract air temperature, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1003` |
| 521 | Rel.humidity extract air, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1006` |
| 522 | Air filter polluted | inactive |  | `R(1)'HVAC'AlmBdl'Alm1020` |
| 523 | Zone supply air temp., sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1030` |
| 524 | Supply air pressure, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1032` |
| 525 | Extract air pressure, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1033` |
| 526 | Diff.press.supply air fan, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1034` |
| 527 | Diff.press.exhaust air fan, sensor fault | inactive |  | `R(1)'HVAC'AlmBdl'Alm1035` |
| 528 | RF interface device, Modbus comm.error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3006` |
| 529 | RF communication error | inactive |  | `R(1)'HVAC'AlmBdl'Alm3007` |
| 530 | RF device, battery low | inactive |  | `R(1)'HVAC'AlmBdl'Alm1040` |
| 574 | Delay for away active | inactive |  | `R(1)'ROpModDtr'DlyAwayAct` |
| 575 | Next operating mode | inactive |  | `R(1)'ROpUnDev'NxOpMod` |
| 576 | Binary calculated value | inactive |  | `R(1)'ROpModDtr'SchedRstManTrg` |
| 580 | Outside air damper stops air flow | inactive |  | `R(1)'HVAC'AlmBdl'Alm2013` |
| 581 | Plant shutdown | inactive |  | `R(1)'HVAC'PltShdn` |
| 587 | Rotary heat exch. motor short circuit | inactive |  | `R(1)'HVAC'AlmBdl'Alm1039` |
| 589 | Rotating heat exchanger motor reset | inactive |  | `R(1)'HVAC'Erc'RotHExgSpdRst` |
| 590 | Stop RMC if Beltbroken | inactive |  | `R(1)'HVAC'Erc'BltBrkStopRMC` |

### Multi-state values (modes, triggers, alarms)

`multi-state-value` · object type 19 · 261 points

| Instance | Description | Example | Unit | Internal name |
|---:|---|---:|---|---|
| 2 | I/O bus management | 1 |  | `IOBus'IOBusMgmt` |
| 4 | KNX PL-Link bus management | 1 |  | `PlnkBus'PlnkBusMgmt` |
| 7 | Alarm, state type A | 1 |  | `R(1)'RHvacCoo'AlmFnct'AalmSta` |
| 12 | Supply air temperature state | 2 |  | `R(1)'RHvacCoo'SftyCtl'TSuSta` |
| 13 | Heating/cooling state | 2 |  | `R(1)'RHvacCoo'HCStaDtr'HCSta` |
| 14 | Plant operating mode | 4 |  | `R(1)'RHvacCoo'PltModDtr'PltOpMod` |
| 16 | Air quality, indication | 1 |  | `R(1)'RHvacCoo'AQualRInd` |
| 17 | Heating/cooling demand | 3 |  | `R(1)'RHvacCoo'HCDmd` |
| 18 | Alarm, state type B | 1 |  | `R(1)'RHvacCoo'MntnFnct'BalmSta` |
| 19 | Actual ventilation mode | 4 |  | `R(1)'HVAC'PrPltOpMod` |
| 20 | Outside air damper device mode | 2 |  | `R(1)'HVAC'DmpOa'DmpOaDevMod` |
| 21 | Rotating heat exchanger , operating mode | 2 |  | `R(1)'HVAC'Erc'RotHExgDevMod` |
| 26 | Electrical heater mode | 2 |  | `R(1)'HVAC'Hcl'HclDevMod` |
| 41 | Present operating mode | 3 |  | `R(1)'ROpModDtr'PrOpMod` |
| 42 | Present ventilation mode | 3 |  | `R(1)'ROpModDtr'ROpMod` |
| 43 | Manual operation condition | 1 |  | `R(1)'ROpModDtr'ManOpCnd` |
| 44 | Central condition trigger | 1 |  | `R(1)'ROpModDtr'CenCndTrg` |
| 45 | Comfort condition trigger | 1 |  | `R(1)'ROpModDtr'CmfCndTrg` |
| 46 | Energy efficiency condition trigger | 1 |  | `R(1)'ROpModDtr'EefCndTrg` |
| 60 | Modbus management | 4 |  | `ModBus'ModBusMgmt` |
| 61 | On-board module | 1 |  | `OnbMdl4UI'OnbMdl` |
| 62 | On-board module | 1 |  | `OnbMdl3AO'OnbMdl` |
| 63 | On-board module | 1 |  | `OnbMdl4AI1UI'OnbMdl` |
| 64 | On-board module | 1 |  | `OnbMdl4BI'OnbMdl` |
| 65 | On-board module | 1 |  | `OnbMdl4BO'OnbMdl` |
| 66 | On-board module | 1 |  | `OnbMTR-V000514B0032` |
| 284 | IO extension module ECUL | 4 |  | `R(1)'IOExtnDevEcul'IOExtnEcul` |
| 288 | Supply fan, operating mode | 2 |  | `R(1)'HVAC'FanSu'FanSuDevMod` |
| 289 | Supply air fan air demand for plant mode | 4 |  | `R(1)'HVAC'FanSu'FanSuAirDmd` |
| 293 | Exhaust fan, operating mode | 2 |  | `R(1)'HVAC'FanEh'FanEhDevMod` |
| 294 | Maintenance, operating mode | 1 |  | `R(1)'HVAC'PrMntnSta` |
| 295 | Reliab.of diff.pressure supply air fan | 1 |  | `R(1)'IOExtnDevEcul'DiffPFanSuRlb` |
| 296 | Reliab.of diff.pressure exhaust air fan | 1 |  | `R(1)'IOExtnDevEcul'DiffPFanEhRlb` |
| 307 | Reliability of room air quality | 1 |  | `R(1)'IOExtnDevEcul'AQualRRlb` |
| 319 | Temporary ventilation operation | 1 |  | `R(1)'ROpUnDev'TmpVntOp` |
| 320 | Room climate op.mode for room op.unit | 3 |  | `R(1)'ROpUnDev'RClmOpModRu` |
| 323 | Maintenance indication for room op.unit | 1 |  | `R(1)'ROpUnDev'MntnIndRu` |
| 326 | Fault indication for room operator unit | 1 |  | `R(1)'ROpUnDev'FltIndRu` |
| 327 | Room operator unit | 1 |  | `R(1)'ROpUnDev'ROpUn` |
| 328 | Room climate operating mode input value | 1 |  | `R(1)'ROpUnDev'RClmOpModIn` |
| 333 | Alarm, XCU modbus | 2 |  | `R(1)'HVAC'AlmBdl'AlmCnfXcu` |
| 334 | Alarm, ECU modbus | 1 |  | `R(1)'HVAC'AlmBdl'AlmCnfEcu` |
| 335 | Alarm, ECUL modbus | 2 |  | `R(1)'HVAC'AlmBdl'AlmCnfEcul` |
| 336 | Alarm, QBM modbus | 2 |  | `R(1)'HVAC'AlmBdl'AlmCnfQbm` |
| 337 | Alarm, B4 selection | 1 |  | `R(1)'HVAC'AlmBdl'AlmCnfTOa` |
| 338 | Alarm, heat exchanger selection | 2 |  | `R(1)'HVAC'AlmBdl'AlmCnfRotHExg` |
| 339 | Alarm, HP selection | 3 |  | `R(1)'HVAC'AlmBdl'AlmCnfHpu` |
| 340 | Alarm, indication type B | 1 |  | `R(1)'RHvacCoo'MntnFnct'BalmInd` |
| 341 | Alarm, acknowledgement state type B | 1 |  | `R(1)'RHvacCoo'MntnFnct'BalmAck` |
| 342 | Alarm, operation of alarms list | 1 |  | `R(1)'RHvacCoo'AlmBdl'FltListOp` |
| 343 | Alarm, indication type A | 1 |  | `R(1)'RHvacCoo'AlmFnct'AalmInd` |
| 344 | Alarm, acknowledgement state type A | 1 |  | `R(1)'RHvacCoo'AlmFnct'AalmAck` |
| 345 | Control panel, fault state | 1 |  | `R(1)'ROpUnDev'FltStaRu` |
| 346 | Fault acknowledgement input | 1 |  | `R(1)'ROpUnDev'FltAckIn` |
| 347 | Maintenance state for room operator unit | 1 |  | `R(1)'ROpUnDev'MntnStaRu` |
| 348 | Maintenance acknowledgement input | 1 |  | `R(1)'ROpUnDev'MntnAckIn` |
| 349 | Reliab.of supply air temp.af.heat exch. | 1 |  | `R(1)'IOExtnDevEcul'TSuAfHExgRlb` |
| 352 | Duct pressure sensor QBM | 4 |  | `R(1)'PDuctDevQbm'PDuctQbm` |
| 353 | Reliability of supply air pressure | 1 |  | `R(1)'PDuctDevQbm'PSuRlb` |
| 354 | Reliability of extract air pressure | 1 |  | `R(1)'PDuctDevQbm'PExRlb` |
| 357 | Forced ventilation, state | 1 |  | `R(1)'RHvacCoo'RpdVntOp'TmpRpdVntTrg` |
| 360 | Speed FIRE, trigger APP | 1 |  | `R(1)'RHvacCoo'FplcVntOp'TmpFplcVntTrg` |
| 361 | Rotating heat exchanger, state | 3 |  | `R(1)'ROpModDtr'HrvSta` |
| 364 | Communication interface BRDG | 4 |  | `R(1)'ComItfDevBrdg'ComItfBrdg` |
| 365 | Communication state RF system | 1 |  | `R(1)'ComItfDevBrdg'ComStaRfqs` |
| 366 | Battery state RF system | 1 |  | `R(1)'ComItfDevBrdg'BattStaRfqs` |
| 367 | Fault state RF system | 1 |  | `R(1)'ComItfDevBrdg'FltStaRfqs` |
| 368 | Remove RF device | 1 |  | `R(1)'ComItfDevBrdg'RmvRfqDev` |
| 369 | Connected RF device 1 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev1` |
| 370 | Connected RF device 2 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev2` |
| 371 | Connected RF device 3 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev3` |
| 372 | Connected RF device 4 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev4` |
| 373 | Connected RF device 5 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev5` |
| 374 | Connected RF device 6 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev6` |
| 375 | Connected RF device 7 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev7` |
| 376 | Connected RF device 8 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev8` |
| 377 | Connected RF device 9 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev9` |
| 378 | Connected RF device 10 | 1 |  | `R(1)'ComItfDevBrdg'CnctdRfqDev10` |
| 379 | RF device address output | 2 |  | `R(1)'ComItfDevBrdg'RfqDevAddrOut` |
| 381 | RF device address input | 1 |  | `R(1)'ComItfDevBrdg'RfqDevAddrIn` |
| 382 | Binding state input | 1 |  | `R(1)'ComItfDevBrdg'BdgStaIn` |
| 384 | FAN node | 4 |  | `R(1)'FanNodeDev'FanNode` |
| 386 | Operating mode output for RF system | 1 |  | `R(1)'FanNodeDev'OpModOutRfqs` |
| 387 | Binding command | 3 |  | `R(1)'FanNodeDev'BdgCmd` |
| 388 | Pushbutton VMN 1 | 4 |  | `R(1)'PshBtnDevVmn1'PshBtnVmn1` |
| 389 | Battery state VMN 1 | 1 |  | `R(1)'PshBtnDevVmn1'BattStaVmn1` |
| 390 | Pushbutton VMN 2 | 4 |  | `R(1)'PshBtnDevVmn2'PshBtnVmn2` |
| 391 | Battery state VMN 2 | 1 |  | `R(1)'PshBtnDevVmn2'BattStaVmn2` |
| 392 | Pushbutton VMN 3 | 4 |  | `R(1)'PshBtnDevVmn3'PshBtnVmn3` |
| 393 | Battery state VMN 3 | 1 |  | `R(1)'PshBtnDevVmn3'BattStaVmn3` |
| 394 | Room operator unit VMSH 1 | 4 |  | `R(1)'ROpUnDevVmsh1'ROpUnVmsh1` |
| 395 | Battery state VMSH 1 | 1 |  | `R(1)'ROpUnDevVmsh1'BattStaVmsh1` |
| 396 | Room operator unit VMSH 2 | 4 |  | `R(1)'ROpUnDevVmsh2'ROpUnVmsh2` |
| 397 | Battery state VMSH 2 | 1 |  | `R(1)'ROpUnDevVmsh2'BattStaVmsh2` |
| 398 | Room operator unit VMSH 3 | 4 |  | `R(1)'ROpUnDevVmsh3'ROpUnVmsh3` |
| 399 | Battery state VMSH 3 | 1 |  | `R(1)'ROpUnDevVmsh3'BattStaVmsh3` |
| 400 | Room operator unit VMSC | 4 |  | `R(1)'ROpUnDevVmsc'ROpUnVmsc` |
| 401 | I/O extension module VMC | 4 |  | `R(1)'IOExtnDevVmc'IOExtnVmc` |
| 434 | Alarm acknowledgement | 1 |  | `R(1)'AlmHdl'AlmAck` |
| 435 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1001'AlmSta` |
| 436 | Alarm type | 1 |  | `R(1)'AlmHdl'Alm1001'AlmType` |
| 437 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1002'AlmSta` |
| 438 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1002'AlmType` |
| 439 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1003'AlmSta` |
| 440 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1003'AlmType` |
| 441 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1004'AlmSta` |
| 442 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm1004'AlmType` |
| 443 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1005'AlmSta` |
| 444 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm1005'AlmType` |
| 445 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1006'AlmSta` |
| 446 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1006'AlmType` |
| 447 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1007'AlmSta` |
| 448 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1007'AlmType` |
| 449 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1008'AlmSta` |
| 450 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1008'AlmType` |
| 451 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1009'AlmSta` |
| 452 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm1009'AlmType` |
| 453 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1010'AlmSta` |
| 454 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1010'AlmType` |
| 455 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1011'AlmSta` |
| 456 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1011'AlmType` |
| 457 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1020'AlmSta` |
| 458 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1020'AlmType` |
| 459 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1032'AlmSta` |
| 460 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1032'AlmType` |
| 461 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1033'AlmSta` |
| 462 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1033'AlmType` |
| 463 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1034'AlmSta` |
| 464 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1034'AlmType` |
| 465 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1035'AlmSta` |
| 466 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1035'AlmType` |
| 467 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1040'AlmSta` |
| 468 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1040'AlmType` |
| 469 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2001'AlmSta` |
| 470 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2001'AlmType` |
| 471 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2002'AlmSta` |
| 472 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2002'AlmType` |
| 473 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2003'AlmSta` |
| 474 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2003'AlmType` |
| 475 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2004'AlmSta` |
| 476 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2004'AlmType` |
| 477 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2005'AlmSta` |
| 478 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm2005'AlmType` |
| 479 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2007'AlmSta` |
| 480 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2007'AlmType` |
| 481 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2010'AlmSta` |
| 482 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2010'AlmType` |
| 483 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3001'AlmSta` |
| 484 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm3001'AlmType` |
| 485 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3002'AlmSta` |
| 486 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm3002'AlmType` |
| 487 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3003'AlmSta` |
| 488 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm3003'AlmType` |
| 489 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3004'AlmSta` |
| 490 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm3004'AlmType` |
| 491 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3006'AlmSta` |
| 492 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm3006'AlmType` |
| 493 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm3007'AlmSta` |
| 494 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm3007'AlmType` |
| 495 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2008'AlmSta` |
| 496 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2008'AlmType` |
| 497 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2009'AlmSta` |
| 498 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2009'AlmType` |
| 499 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2011'AlmSta` |
| 500 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2011'AlmType` |
| 501 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2014'AlmSta` |
| 502 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm2014'AlmType` |
| 505 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2016'AlmSta` |
| 506 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm2016'AlmType` |
| 507 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9001'AlmSta` |
| 508 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9001'AlmType` |
| 509 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9002'AlmSta` |
| 510 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9002'AlmType` |
| 511 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9003'AlmSta` |
| 512 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9003'AlmType` |
| 513 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9004'AlmSta` |
| 514 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9004'AlmType` |
| 515 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9005'AlmSta` |
| 516 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9005'AlmType` |
| 517 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9006'AlmSta` |
| 518 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9006'AlmType` |
| 519 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9007'AlmSta` |
| 520 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9007'AlmType` |
| 521 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9008'AlmSta` |
| 522 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9008'AlmType` |
| 523 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9009'AlmSta` |
| 524 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9009'AlmType` |
| 525 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9010'AlmSta` |
| 526 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9010'AlmType` |
| 527 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9011'AlmSta` |
| 528 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9011'AlmType` |
| 529 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9012'AlmSta` |
| 530 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9012'AlmType` |
| 531 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9013'AlmSta` |
| 532 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9013'AlmType` |
| 533 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9014'AlmSta` |
| 534 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9014'AlmType` |
| 535 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9015'AlmSta` |
| 536 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9015'AlmType` |
| 537 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9016'AlmSta` |
| 538 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9016'AlmType` |
| 539 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9017'AlmSta` |
| 540 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9017'AlmType` |
| 541 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9018'AlmSta` |
| 542 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9018'AlmType` |
| 543 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9019'AlmSta` |
| 544 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9019'AlmType` |
| 545 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9020'AlmSta` |
| 546 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9020'AlmType` |
| 547 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9021'AlmSta` |
| 548 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9021'AlmType` |
| 549 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9022'AlmSta` |
| 550 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9022'AlmType` |
| 551 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9023'AlmSta` |
| 552 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9023'AlmType` |
| 553 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9024'AlmSta` |
| 554 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9024'AlmType` |
| 555 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9025'AlmSta` |
| 556 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9025'AlmType` |
| 557 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9026'AlmSta` |
| 558 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9026'AlmType` |
| 559 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9027'AlmSta` |
| 560 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm9027'AlmType` |
| 561 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm9028'AlmSta` |
| 562 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm9028'AlmType` |
| 563 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1022'AlmSta` |
| 564 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1022'AlmType` |
| 565 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1023'AlmSta` |
| 566 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1023'AlmType` |
| 567 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1024'AlmSta` |
| 568 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1024'AlmType` |
| 569 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1025'AlmSta` |
| 570 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1025'AlmType` |
| 571 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1026'AlmSta` |
| 572 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1026'AlmType` |
| 573 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1027'AlmSta` |
| 574 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1027'AlmType` |
| 575 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1028'AlmSta` |
| 576 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1028'AlmType` |
| 577 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1029'AlmSta` |
| 578 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm1029'AlmType` |
| 579 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1030'AlmSta` |
| 580 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1030'AlmType` |
| 581 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1036'AlmSta` |
| 582 | Multistate calculated value | 1 |  | `R(1)'AlmHdl'Alm1036'AlmType` |
| 583 | Next room operating mode | 5 |  | `R(1)'ROpUnDev'NxROpMod` |
| 584 | Room op.mode determ.for room op.unit | 1 |  | `R(1)'ROpUnDev'ROpModDtrRu` |
| 585 | Temporary room operating mode input | 1 |  | `R(1)'ROpUnDev'TmpROpModIn` |
| 605 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2013'AlmSta` |
| 606 | Alarm type | 1 |  | `R(1)'AlmHdl'Alm2013'AlmType` |
| 607 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2018'AlmSta` |
| 608 | Alarm type | 2 |  | `R(1)'AlmHdl'Alm2018'AlmType` |
| 609 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm2019'AlmSta` |
| 610 | Alarm type | 2 |  | `R(1)'AlmHdl'Alm2019'AlmType` |
| 611 | Alarm state | 1 |  | `R(1)'AlmHdl'Alm1039'AlmSta` |
| 612 | Multistate calculated value | 2 |  | `R(1)'AlmHdl'Alm1039'AlmType` |
| 613 | Air filter replace timer reset | 1 |  | `R(1)'HVAC'AlmBdl'FilRpcRst` |
| 614 | Alarm config.for fan speed feedback | 2 |  | `R(1)'HVAC'AlmBdl'AlmCnfFanFb` |
| 617 | Device low power | 1 |  | `R(1)'HdwCnf'DevLwPwr` |
| 618 | Motor manual reset  | 1 |  | `R(1)'HVAC'Erc'MotorManRst` |
| 619 | Monitor motor MCU state | 1 |  | `RotHExgSpdState` |
