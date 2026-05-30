[Home](https://kellyjonbrazil.github.io/jc/)
<a id="jc.parsers.arp"></a>

# jc.parsers.arp

jc - JSON Convert `arp` command output parser

Supports `arp` and `arp -a` output.

Usage (cli):

    $ arp | jc --arp

or

    $ jc arp

Usage (module):

    import jc
    result = jc.parse('arp', arp_command_output)

Schema:

    [
      {
        "name":         string,
        "address":      string,
        "hwtype":       string,
        "hwaddress":    string,
        "flags_mask":   string,
        "iface":        string,
        "permanent":    boolean,
        "expires":      integer
      }
    ]

Examples:

    $ arp | jc --arp -p
    [
      {
        "address": "192.168.71.254",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f0:98:26",
        "flags_mask": "C",
        "iface": "ens33"
      },
      {
        "address": "gateway",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f7:4a:fc",
        "flags_mask": "C",
        "iface": "ens33"
      }
    ]

    $ arp | jc --arp -p -r
    [
      {
        "address": "gateway",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f7:4a:fc",
        "flags_mask": "C",
        "iface": "ens33"
      },
      {
        "address": "192.168.71.254",
        "hwtype": "ether",
        "hwaddress": "00:50:56:fe:7a:b4",
        "flags_mask": "C",
        "iface": "ens33"
      }
    ]

    $ arp -a | jc --arp -p
    [
      {
        "name": null,
        "address": "192.168.71.254",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f0:98:26",
        "iface": "ens33"
        "permanent": false,
        "expires": 1182
      },
      {
        "name": "gateway",
        "address": "192.168.71.2",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f7:4a:fc",
        "iface": "ens33"
        "permanent": false,
        "expires": 110
      }
    ]

    $ arp -a | jc --arp -p -r
    [
      {
        "name": "?",
        "address": "192.168.71.254",
        "hwtype": "ether",
        "hwaddress": "00:50:56:fe:7a:b4",
        "iface": "ens33"
        "permanent": false,
        "expires": "1182"
      },
      {
        "name": "_gateway",
        "address": "192.168.71.2",
        "hwtype": "ether",
        "hwaddress": "00:50:56:f7:4a:fc",
        "iface": "ens33"
        "permanent": false,
        "expires": "110"
      }
    ]

<a id="jc.parsers.arp.parse"></a>

### parse

```python
def parse(data: str, raw: bool = False, quiet: bool = False) -> List[Dict]
```

Main text parsing function

Parameters:

    data:        (string)  text data to parse
    raw:         (boolean) unprocessed output if True
    quiet:       (boolean) suppress warning messages if True

Returns:

    List of Dictionaries. Raw or processed structured data.

### Example Input

```
Address                  HWtype  HWaddress           Flags Mask            Iface
gateway                  ether   00:50:56:f7:4a:fc   C                     ens33
192.168.71.1             ether   00:50:56:c0:00:08   C                     ens33
192.168.71.254           ether   00:50:56:fe:7a:b4   C                     ens33
```

### Example Output (Processed)

```json
[
  {
    "address": "gateway",
    "hwtype": "ether",
    "hwaddress": "00:50:56:f7:4a:fc",
    "flags_mask": "C",
    "iface": "ens33"
  },
  {
    "address": "192.168.71.1",
    "hwtype": "ether",
    "hwaddress": "00:50:56:c0:00:08",
    "flags_mask": "C",
    "iface": "ens33"
  }
]
```

### Example Output (Raw)

```json
[
  {
    "address": "gateway",
    "hwtype": "ether",
    "hwaddress": "00:50:56:f7:4a:fc",
    "flags_mask": "C",
    "iface": "ens33"
  },
  {
    "address": "192.168.71.1",
    "hwtype": "ether",
    "hwaddress": "00:50:56:c0:00:08",
    "flags_mask": "C",
    "iface": "ens33"
  }
]
```

### Platform Limitations

- On AIX, bucket information lines and "There are X entries" lines are automatically skipped
- On AIX, the interface field may be omitted for incomplete entries
- On FreeBSD/Darwin, the `name` field is set to null if it is "?"

### Common Exceptions

- **ParseError**: Raised when the input format does not match any known arp output style

### Parser Information
Compatibility:  linux, aix, freebsd, darwin

Source: [`jc/parsers/arp.py`](https://github.com/kellyjonbrazil/jc/blob/master/jc/parsers/arp.py)

Version 1.12 by Kelly Brazil (kellyjonbrazil@gmail.com)
