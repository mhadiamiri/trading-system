"""
GROUND TRUTH: captured live from Kraken v2, 2026-07-19T17:26:53.817753+00:00, run WO-008b-A2 smoke.

Endpoint : wss://ws.kraken.com/v2
Symbol   : BTC/USD   Depth: 10
Captured : 1 snapshot + 1071 updates over a 120s window (1192 raw frames total).
Retained : the snapshot + the first 40 updates, verbatim as received.

WHY THIS FILE MATTERS
---------------------
Kraken documents a checksum for the SNAPSHOT case ONLY. Until this capture, the
INCREMENTAL path had no independent ground truth anywhere — every incremental
fixture was self-generated, encoding our own assumptions on both sides of the
comparison. These frames carry KRAKEN'S OWN CHECKSUMS for real incremental
updates, permanently closing a verification gap no constructed fixture could.

WHAT THEY ALREADY PROVED
------------------------
Replayed offline, all 1070 usable updates validate against Kraken's checksums
when the checksum is computed over the POST-update book, and NONE validate
pre-update (1070/1070 vs 0/1070). That is independent confirmation of the
FR-018a(b) ordering fix from WO-008b-A1, which no fixture could establish.

⚠ NOTE ON NUMBER RENDERING — the defect this capture exposed
------------------------------------------------------------
Kraken sends price and qty as JSON NUMBERS, not strings, so `json.loads` floats
them before any project code runs. `Decimal(str(5.1e-05))` renders "0.000051",
dropping trailing zeros the checksum digits require; Kraken's own rendering is
fixed-point 8dp, "0.00005100". Reproducing these checksums therefore requires
fixed-point rendering, NOT str(Decimal(float)).

EVIDENTIARY BOUNDS (WO-011 section 6.3)
---------------------------------------
This fixture is the POST-PARSE STRUCTURE (Python dicts). It verifies the
book-maintenance and checksum LOGIC — snapshot and incremental checksums replay
against Kraken's own values. It STRUCTURALLY CANNOT witness the parse layer:
by the time these dicts existed, json.loads had already floated the numbers and
the trailing zeros were gone. Proving the parse/rendering layer needs raw wire
text — that is what the A3 fixture (kraken_v2_captured_frames_a3.py) is for.
Doctrine: future captures default to RAW WIRE TEXT.

REDACTION (WO-011 section 6.1)
------------------------------
These retained book frames contain no credential, token, or session id. However
the full raw capture, evidence/WO-008b-A2/captured_frames_raw.json, contained a
`connection_id` in a status frame (a session identifier, not a credential). It
was SCRUBBED to "<REDACTED>" under WO-011 section 6.1 via
trading.logkit.redaction. Noted here so a future diff of A2 against A3's
redaction does not read as tampering — the scrub is deliberate and recorded.
"""

CAPTURED_UTC = "2026-07-19T17:26:53.817753+00:00"
ENDPOINT = "wss://ws.kraken.com/v2"
SYMBOL = "BTC/USD"
DEPTH = 10

CAPTURED_SNAPSHOT = {
    "channel": "book",
    "type": "snapshot",
    "data": [
        {
            "symbol": "BTC/USD",
            "bids": [
                {
                    "price": 64623.3,
                    "qty": 0.00335266
                },
                {
                    "price": 64623.1,
                    "qty": 5.1e-05
                },
                {
                    "price": 64619.9,
                    "qty": 5.1e-05
                },
                {
                    "price": 64616.9,
                    "qty": 0.00154759
                },
                {
                    "price": 64616.6,
                    "qty": 5.1e-05
                },
                {
                    "price": 64613.6,
                    "qty": 0.02960322
                },
                {
                    "price": 64613.5,
                    "qty": 0.03093444
                },
                {
                    "price": 64613.4,
                    "qty": 5.1e-05
                },
                {
                    "price": 64612.8,
                    "qty": 0.05605355
                },
                {
                    "price": 64610.6,
                    "qty": 0.60592337
                }
            ],
            "asks": [
                {
                    "price": 64623.4,
                    "qty": 1.35151858
                },
                {
                    "price": 64623.6,
                    "qty": 0.54856995
                },
                {
                    "price": 64623.7,
                    "qty": 0.77371026
                },
                {
                    "price": 64624.7,
                    "qty": 0.23215013
                },
                {
                    "price": 64624.8,
                    "qty": 0.77369788
                },
                {
                    "price": 64626.2,
                    "qty": 5.1e-05
                },
                {
                    "price": 64627.2,
                    "qty": 0.04537069
                },
                {
                    "price": 64628.6,
                    "qty": 0.30136725
                },
                {
                    "price": 64629.0,
                    "qty": 0.77364704
                },
                {
                    "price": 64629.5,
                    "qty": 5.1e-05
                }
            ],
            "checksum": 3372482100,
            "timestamp": "2026-07-19T17:26:55.273960Z"
        }
    ]
}

CAPTURED_UPDATES = [
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 1.35114758
                    }
                ],
                "checksum": 2268426556,
                "timestamp": "2026-07-19T17:26:56.189018Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.5,
                        "qty": 0.000371
                    }
                ],
                "checksum": 1722728145,
                "timestamp": "2026-07-19T17:26:56.190753Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64624.6,
                        "qty": 0.011
                    }
                ],
                "checksum": 1558720064,
                "timestamp": "2026-07-19T17:26:56.263909Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64616.9,
                        "qty": 0.0
                    },
                    {
                        "price": 64610.4,
                        "qty": 0.77386837
                    }
                ],
                "asks": [],
                "checksum": 3905585547,
                "timestamp": "2026-07-19T17:26:56.509813Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64615.8,
                        "qty": 0.00154761
                    }
                ],
                "asks": [],
                "checksum": 3027853450,
                "timestamp": "2026-07-19T17:26:57.393117Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.6,
                        "qty": 0.55163725
                    }
                ],
                "checksum": 1063592923,
                "timestamp": "2026-07-19T17:26:57.409151Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.6,
                        "qty": 0.0
                    },
                    {
                        "price": 64610.3,
                        "qty": 0.0615
                    }
                ],
                "asks": [],
                "checksum": 2421895915,
                "timestamp": "2026-07-19T17:26:58.295902Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64611.2,
                        "qty": 0.77385882
                    }
                ],
                "asks": [],
                "checksum": 1835210568,
                "timestamp": "2026-07-19T17:26:58.296897Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 0.80445469
                    }
                ],
                "checksum": 3060894483,
                "timestamp": "2026-07-19T17:26:58.308640Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64611.2,
                        "qty": 0.0
                    },
                    {
                        "price": 64610.3,
                        "qty": 0.45580497
                    }
                ],
                "asks": [],
                "checksum": 3593784609,
                "timestamp": "2026-07-19T17:26:58.309274Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.6,
                        "qty": 0.19953355
                    }
                ],
                "checksum": 3185639731,
                "timestamp": "2026-07-19T17:26:58.311396Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.6,
                        "qty": 0.0030673
                    }
                ],
                "checksum": 3521787238,
                "timestamp": "2026-07-19T17:26:58.314175Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.3,
                        "qty": 0.61910354
                    }
                ],
                "asks": [],
                "checksum": 765574193,
                "timestamp": "2026-07-19T17:26:58.317095Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.3,
                        "qty": 0.22479857
                    }
                ],
                "asks": [],
                "checksum": 1133101049,
                "timestamp": "2026-07-19T17:26:58.317358Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.3,
                        "qty": 0.43492282
                    }
                ],
                "asks": [],
                "checksum": 2213776318,
                "timestamp": "2026-07-19T17:26:58.318113Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.3,
                        "qty": 0.22479857
                    }
                ],
                "asks": [],
                "checksum": 1133101049,
                "timestamp": "2026-07-19T17:26:58.321694Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64610.4,
                        "qty": 0.01846849
                    }
                ],
                "asks": [],
                "checksum": 1777851886,
                "timestamp": "2026-07-19T17:26:58.356800Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.7,
                        "qty": 0.77382929
                    }
                ],
                "asks": [],
                "checksum": 3459106789,
                "timestamp": "2026-07-19T17:26:58.595940Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.6,
                        "qty": 0.00154766
                    }
                ],
                "asks": [],
                "checksum": 3911844188,
                "timestamp": "2026-07-19T17:26:58.597286Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.8,
                        "qty": 0.25743116
                    }
                ],
                "asks": [],
                "checksum": 1410412090,
                "timestamp": "2026-07-19T17:26:58.597650Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.8,
                        "qty": 0.25897881
                    }
                ],
                "asks": [],
                "checksum": 3443133932,
                "timestamp": "2026-07-19T17:26:58.600029Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.6,
                        "qty": 0.0
                    },
                    {
                        "price": 64612.8,
                        "qty": 0.05605355
                    }
                ],
                "asks": [],
                "checksum": 81223638,
                "timestamp": "2026-07-19T17:26:58.600270Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 0.64968794
                    }
                ],
                "checksum": 396352328,
                "timestamp": "2026-07-19T17:26:58.786202Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64624.7,
                        "qty": 0.0
                    },
                    {
                        "price": 64629.0,
                        "qty": 0.77364704
                    }
                ],
                "checksum": 2132508668,
                "timestamp": "2026-07-19T17:26:58.788249Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 1.19638083
                    }
                ],
                "checksum": 245884780,
                "timestamp": "2026-07-19T17:26:58.858024Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 1.20775595
                    }
                ],
                "checksum": 979421078,
                "timestamp": "2026-07-19T17:26:58.861747Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.5,
                        "qty": 0.0
                    },
                    {
                        "price": 64629.5,
                        "qty": 5.1e-05
                    }
                ],
                "checksum": 2779599575,
                "timestamp": "2026-07-19T17:26:59.045550Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 1.36252268
                    }
                ],
                "checksum": 3229725713,
                "timestamp": "2026-07-19T17:26:59.314515Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64624.7,
                        "qty": 0.2321501
                    }
                ],
                "checksum": 3644006418,
                "timestamp": "2026-07-19T17:26:59.314694Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64623.4,
                        "qty": 1.36289368
                    }
                ],
                "checksum": 2978663359,
                "timestamp": "2026-07-19T17:26:59.455847Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [],
                "asks": [
                    {
                        "price": 64627.0,
                        "qty": 0.495031
                    }
                ],
                "checksum": 2403219381,
                "timestamp": "2026-07-19T17:26:59.549536Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.7,
                        "qty": 0.0
                    },
                    {
                        "price": 64611.1,
                        "qty": 0.38076011
                    }
                ],
                "asks": [],
                "checksum": 3681396045,
                "timestamp": "2026-07-19T17:27:00.392760Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.8,
                        "qty": 0.00154765
                    }
                ],
                "asks": [],
                "checksum": 1985929588,
                "timestamp": "2026-07-19T17:27:00.393998Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64612.9,
                        "qty": 0.77383879
                    }
                ],
                "asks": [],
                "checksum": 4036485456,
                "timestamp": "2026-07-19T17:27:00.394241Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.6,
                        "qty": 0.02598114
                    }
                ],
                "asks": [],
                "checksum": 2312492365,
                "timestamp": "2026-07-19T17:27:00.395468Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.8,
                        "qty": 0.00739493
                    }
                ],
                "asks": [],
                "checksum": 1850915043,
                "timestamp": "2026-07-19T17:27:00.395685Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.6,
                        "qty": 0.0275288
                    }
                ],
                "asks": [],
                "checksum": 4285034759,
                "timestamp": "2026-07-19T17:27:00.397321Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.8,
                        "qty": 0.00584728
                    }
                ],
                "asks": [],
                "checksum": 3237869201,
                "timestamp": "2026-07-19T17:27:00.397350Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.6,
                        "qty": 0.02598114
                    }
                ],
                "asks": [],
                "checksum": 1372012405,
                "timestamp": "2026-07-19T17:27:00.398755Z"
            }
        ]
    },
    {
        "channel": "book",
        "type": "update",
        "data": [
            {
                "symbol": "BTC/USD",
                "bids": [
                    {
                        "price": 64613.9,
                        "qty": 0.00154765
                    }
                ],
                "asks": [],
                "checksum": 85849431,
                "timestamp": "2026-07-19T17:27:00.399004Z"
            }
        ]
    }
]

ALL_CAPTURED_FRAMES = [CAPTURED_SNAPSHOT] + CAPTURED_UPDATES
