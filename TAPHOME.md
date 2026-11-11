# TapHome: ventilation status and temperatures

TapHome has no BACnet driver, so it talks to the unit through a **Packet Parser** module over UDP, the same way it switches
modes. This page adds monitoring to that module: four air temperatures and the current operation mode, all read with **one**
ReadPropertyMultiple request per poll. Protocol background: [BACNET.md](BACNET.md).

## What is read

| TapHome device | BACnet object | Reply offset (bytes) | Value |
|---|---|---:|---|
| Outdoor air (temperature sensor) | `analog-input,1` | 19 | REAL °C |
| Supply air (temperature sensor) | `analog-input,4` | 35 | REAL °C |
| Extract air (temperature sensor) | `analog-input,95` | 51 | REAL °C |
| Exhaust air (temperature sensor) | `analog-input,11` | 67 | REAL °C |
| Operation mode (multi-value switch, read-only) | `multi-state-value,361` | 83 | `1` Off · `2` Away · `3` Home · `4` High · `5` Cooker hood · `6` Fireplace · `7` Temporary high |

Extract air is `analog-input,95` on this S3 REL; `analog-input,59` (the library's default) answers *unknown object*.
Checked against the unit on 2026-11-11: 5.5 / 19.9 / 22.13 / 11.85 °C, mode 3 (Home).

## The request

Sent unicast to the unit, UDP 47808 (55 bytes):

```
81 0a 00 37 01 04 02 44 01 0e 0c 00 00 00 01 1e 09 55 1f 0c 00 00 00 04 1e 09 55 1f 0c 00 00 00 5f 1e 09 55 1f 0c 00 00 00 0b 1e 09 55 1f 0c 04 c0 01 69 1e 09 55 1f
```

## The reply

When all five points answer, the reply is always **86 bytes** with the values at fixed offsets: a ComplexACK
(`30 01 0e` at bytes 6–8), then per object `0c <id> 1e 29 55 4e <value> 4f 1f`. A REAL value is tag `44` followed by
4 bytes big-endian IEEE 754; the mode is tag `21` followed by 1 byte. If a point fails, the unit puts an error
(`5e … 5f`) in its place, the length changes, and the check below rejects the packet.

```
81 0a 00 56 01 00 30 01 0e
0c 00 00 00 01 1e 29 55 4e 44 40 b0 00 00 4f 1f   outdoor  5.5
0c 00 00 00 04 1e 29 55 4e 44 41 9f 33 33 4f 1f   supply  19.9
0c 00 00 00 5f 1e 29 55 4e 44 41 b1 0f 90 4f 1f   extract 22.13
0c 00 00 00 0b 1e 29 55 4e 44 41 3d 99 9a 4f 1f   exhaust 11.85
0c 04 c0 01 69 1e 29 55 4e 21 03 4f 1f            mode     3
```

## TapHome configuration

Add to the existing Packet Parser module (IP of the unit, port 47808) that already switches modes. Untested in TapHome:
the scripts follow TapHome's documented functions (`SENDDATA`, `BYTECOLLECTION`, `RECEIVEDBYTES`, `GETAT`,
`UNPACKVALUE` needs TapHome Next 2026.1.39016 or later).

1. **Module variables:** `outdoorTemp`, `supplyTemp`, `extractTemp`, `exhaustTemp`, `opMode`.
2. **Module Read script** (the poll; every 30–60 s is plenty):
   ```taphome
   SENDDATA(BYTECOLLECTION("81 0a 00 37 01 04 02 44 01 0e 0c 00 00 00 01 1e 09 55 1f 0c 00 00 00 04 1e 09 55 1f 0c 00 00 00 5f 1e 09 55 1f 0c 00 00 00 0b 1e 09 55 1f 0c 04 c0 01 69 1e 09 55 1f"));
   ```
3. **Module Listener script.** Only the 86-byte ReadPropertyMultiple reply is used; the 9-byte SimpleACKs that answer
   mode writes (`… 20 01 0f`) are skipped. If the module already has a listener, add this block to it.
   ```taphome
   VAR b := RECEIVEDBYTES;
   IF LENGTH(b) = 86 AND GETAT(b, 6) = 0x30 AND GETAT(b, 8) = 0x0e AND GETAT(b, 18) = 0x44 AND GETAT(b, 34) = 0x44 AND GETAT(b, 50) = 0x44 AND GETAT(b, 66) = 0x44 AND GETAT(b, 82) = 0x21
       outdoorTemp := UNPACKVALUE(b, 19, BigEndianFloat);
       supplyTemp := UNPACKVALUE(b, 35, BigEndianFloat);
       extractTemp := UNPACKVALUE(b, 51, BigEndianFloat);
       exhaustTemp := UNPACKVALUE(b, 67, BigEndianFloat);
       opMode := GETAT(b, 83);
   END
   ```
   **Before TapHome 2026.1.39016** (no `UNPACKVALUE`: "unknown variable or contact"), decode the REALs by hand with
   `GETAT`, `MOD` and `POWER` (IEEE 754: sign, 8-bit exponent, 23-bit mantissa; checked against the real reply, and
   for negative and fractional values). Same check line, then per temperature (offset `o` = 19, 35, 51, 67):
   ```taphome
   VAR o := 19;
   VAR b0 := GETAT(b, o); VAR b1 := GETAT(b, o + 1);
   outdoorTemp := IF(b0 >= 128, -1, 1) * (1 + (MOD(b1, 128) * 65536 + GETAT(b, o + 2) * 256 + GETAT(b, o + 3)) / 8388608) * POWER(2, MOD(b0, 128) * 2 + IF(b1 >= 128, 1, 0) - 127);
   ```
   The byte checks are written as decimals (`48`, `14`, `68`, `33`), which every version accepts.
4. **Devices.** Four *Temperature sensor* devices whose Read Value script is just the variable (`outdoorTemp`,
   `supplyTemp`, `extractTemp`, `exhaustTemp`), and one *Multi-value switch* named Operation mode, read-only, Read Value
   `opMode`, with states 1–7 named as in the table above.

Check: the sensors match the Flexit GO app within a few tenths of a degree, and Operation mode changes when the mode is
switched from TapHome or the app.

To regenerate the request or add a point (for example `binary-value,522`, filter polluted), build the bytes as in
[BACNET.md](BACNET.md#packet-anatomy): one `0c <type<<22|instance> 1e 09 55 1f` block per object, BVLC length updated,
and recompute the reply offsets from a real reply.
