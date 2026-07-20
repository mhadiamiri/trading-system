"""
GROUND TRUTH: captured live from Kraken v2, 2026-07-19T17:54:37.034140+00:00, run WO-008b-A3 smoke.

Endpoint : wss://ws.kraken.com/v2    Symbol: BTC/USD    Depth: 10
Window   : 1 snapshot + 1253 book updates over ~122s (1376 raw frames).
Retained : snapshot + first 40 updates, as RAW WIRE TEXT.

SECOND independent capture. WO-008b-A2's fixture is KEPT, not replaced —
ground truth accretes (WO-008b-A3 addendum E).

⚠ WHY RAW TEXT, NOT PARSED STRUCTURE
A2 stored the POST-parse structure, which had already lost the trailing zeros
the checksum depends on ("0.00005100" -> 0.0). These frames are the bytes as
received, so they can verify the parse layer itself — which A2's could not.

Validated under the ruled fix (json.loads parse_float=Decimal, parse_int=Decimal):
snapshot checksum reproduced, and 1253 of 1253 incremental checksums reproduced.

connection_id REDACTED from the status frame (session identifier, not a
credential). Nothing else altered.

EVIDENTIARY BOUNDS (WO-011 section 6.3)
---------------------------------------
This fixture is RAW WIRE TEXT — the bytes as received. Its evidentiary power is
therefore the widest available: it witnesses EVERYTHING downstream of the wire,
including the parse/rendering layer that the A2 post-parse fixture structurally
cannot. Both fixtures are kept (ground truth accretes); A2 proves book/checksum
LOGIC, A3 proves that plus RENDERING. Doctrine: future captures default to raw
wire text, and redaction is applied mechanically via trading.logkit.redaction.
"""

CAPTURED_UTC = "2026-07-19T17:54:37.034140+00:00"
ENDPOINT = "wss://ws.kraken.com/v2"
SYMBOL = "BTC/USD"
DEPTH = 10
RUN_ID = "WO-008b-A3-smoke"

CAPTURED_SNAPSHOT_TEXT = '{"channel":"book","type":"snapshot","data":[{"symbol":"BTC/USD","bids":[{"price":64525.0,"qty":0.53807066},{"price":64524.2,"qty":0.03095975},{"price":64524.1,"qty":0.24102802},{"price":64524.0,"qty":0.77490540},{"price":64523.3,"qty":0.00154900},{"price":64522.9,"qty":0.00005100},{"price":64521.9,"qty":0.77493047},{"price":64521.5,"qty":0.00123904},{"price":64521.4,"qty":0.37127532},{"price":64521.3,"qty":0.47213100}],"asks":[{"price":64525.1,"qty":0.01077490},{"price":64526.1,"qty":0.00005100},{"price":64529.3,"qty":0.00005100},{"price":64530.8,"qty":0.03095975},{"price":64530.9,"qty":0.15498085},{"price":64531.0,"qty":0.77482234},{"price":64532.2,"qty":0.23247128},{"price":64532.5,"qty":0.00005100},{"price":64532.6,"qty":0.03099208},{"price":64532.8,"qty":1.23479983}],"checksum":2175437505,"timestamp":"2026-07-19T17:54:39.753424Z"}]}'

CAPTURED_UPDATE_TEXTS = [
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00309336}],\"checksum\":1848203113,\"timestamp\":\"2026-07-19T17:54:39.768901Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00000000},{\"price\":64532.8,\"qty\":1.23479983}],\"checksum\":2175437505,\"timestamp\":\"2026-07-19T17:54:39.784623Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64524.0,\"qty\":0.00000000},{\"price\":64521.2,\"qty\":0.00200000}],\"asks\":[],\"checksum\":3906264065,\"timestamp\":\"2026-07-19T17:54:39.799885Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64531.0,\"qty\":0.00000000},{\"price\":64535.7,\"qty\":0.01400000}],\"checksum\":1519900485,\"timestamp\":\"2026-07-19T17:54:39.800094Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00309336}],\"checksum\":120017111,\"timestamp\":\"2026-07-19T17:54:39.815663Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.2,\"qty\":0.77483158}],\"checksum\":891214259,\"timestamp\":\"2026-07-19T17:54:40.752446Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64523.2,\"qty\":0.77491443}],\"asks\":[],\"checksum\":2257459572,\"timestamp\":\"2026-07-19T17:54:40.752552Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.8,\"qty\":0.00000000},{\"price\":64532.8,\"qty\":1.23479983},{\"price\":64530.1,\"qty\":0.03095975}],\"checksum\":996749228,\"timestamp\":\"2026-07-19T17:54:40.753917Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00000000},{\"price\":64532.8,\"qty\":1.23479983}],\"checksum\":2772272784,\"timestamp\":\"2026-07-19T17:54:40.770031Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64525.0,\"qty\":2.27338366}],\"asks\":[],\"checksum\":4243077117,\"timestamp\":\"2026-07-19T17:54:41.299347Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64524.1,\"qty\":0.43229135}],\"asks\":[],\"checksum\":698518623,\"timestamp\":\"2026-07-19T17:54:41.303467Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64525.0,\"qty\":2.44740410}],\"asks\":[],\"checksum\":3323432639,\"timestamp\":\"2026-07-19T17:54:41.305590Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00309336}],\"checksum\":3924207249,\"timestamp\":\"2026-07-19T17:54:41.314972Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64525.3,\"qty\":0.00000000},{\"price\":64532.8,\"qty\":1.23479983}],\"checksum\":3323432639,\"timestamp\":\"2026-07-19T17:54:41.331706Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64521.5,\"qty\":0.66783967}],\"asks\":[],\"checksum\":421922241,\"timestamp\":\"2026-07-19T17:54:41.474428Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64521.4,\"qty\":0.16046087}],\"asks\":[],\"checksum\":582463697,\"timestamp\":\"2026-07-19T17:54:41.476645Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64521.4,\"qty\":0.00000000},{\"price\":64521.2,\"qty\":0.00200000}],\"asks\":[],\"checksum\":3486936882,\"timestamp\":\"2026-07-19T17:54:41.476956Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64521.6,\"qty\":0.59114006}],\"asks\":[],\"checksum\":633442630,\"timestamp\":\"2026-07-19T17:54:41.477915Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64531.5,\"qty\":0.66660063}],\"checksum\":2388736682,\"timestamp\":\"2026-07-19T17:54:41.478184Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64531.5,\"qty\":0.00000000},{\"price\":64532.8,\"qty\":1.23479983}],\"checksum\":633442630,\"timestamp\":\"2026-07-19T17:54:41.492823Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.1,\"qty\":0.00000000},{\"price\":64535.7,\"qty\":0.01400000}],\"checksum\":285760224,\"timestamp\":\"2026-07-19T17:54:41.506425Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64524.2,\"qty\":0.00000000},{\"price\":64521.2,\"qty\":0.00200000},{\"price\":64525.0,\"qty\":2.47836385}],\"asks\":[],\"checksum\":1419780744,\"timestamp\":\"2026-07-19T17:54:41.509015Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64532.5,\"qty\":0.03101075}],\"checksum\":245437198,\"timestamp\":\"2026-07-19T17:54:41.509178Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.2,\"qty\":0.00000000},{\"price\":64535.8,\"qty\":0.00005100}],\"checksum\":1150466026,\"timestamp\":\"2026-07-19T17:54:41.535317Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.9,\"qty\":0.92980361}],\"checksum\":575159853,\"timestamp\":\"2026-07-19T17:54:41.536987Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64523.2,\"qty\":0.00000000},{\"price\":64521.0,\"qty\":0.00187535}],\"asks\":[],\"checksum\":1431048232,\"timestamp\":\"2026-07-19T17:54:41.630657Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64524.1,\"qty\":0.24102802}],\"asks\":[],\"checksum\":1780699255,\"timestamp\":\"2026-07-19T17:54:41.631900Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64523.9,\"qty\":0.77490574}],\"asks\":[],\"checksum\":2657606631,\"timestamp\":\"2026-07-19T17:54:41.632514Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[{\"price\":64524.1,\"qty\":0.43228875}],\"asks\":[],\"checksum\":288390639,\"timestamp\":\"2026-07-19T17:54:41.739795Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.9,\"qty\":0.15498085}],\"checksum\":2011886632,\"timestamp\":\"2026-07-19T17:54:42.159703Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64532.8,\"qty\":0.46000000}],\"checksum\":3772185691,\"timestamp\":\"2026-07-19T17:54:42.159897Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64532.5,\"qty\":0.00005100}],\"checksum\":1160000213,\"timestamp\":\"2026-07-19T17:54:42.160933Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64531.8,\"qty\":0.77481207}],\"checksum\":2430639418,\"timestamp\":\"2026-07-19T17:54:42.162413Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64534.1,\"qty\":0.77478456}],\"checksum\":1199128117,\"timestamp\":\"2026-07-19T17:54:42.162666Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64531.8,\"qty\":0.00000000},{\"price\":64535.7,\"qty\":0.01400000}],\"checksum\":1739848165,\"timestamp\":\"2026-07-19T17:54:42.327361Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64534.1,\"qty\":0.00000000},{\"price\":64535.8,\"qty\":0.00005100}],\"checksum\":1160000213,\"timestamp\":\"2026-07-19T17:54:42.327615Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64530.7,\"qty\":0.77482572}],\"checksum\":2392302228,\"timestamp\":\"2026-07-19T17:54:42.329192Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64533.2,\"qty\":0.66660063}],\"checksum\":1073490389,\"timestamp\":\"2026-07-19T17:54:42.378530Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64533.2,\"qty\":0.00000000},{\"price\":64535.7,\"qty\":0.01400000}],\"checksum\":2392302228,\"timestamp\":\"2026-07-19T17:54:42.750767Z\"}]}",
 "{\"channel\":\"book\",\"type\":\"update\",\"data\":[{\"symbol\":\"BTC/USD\",\"bids\":[],\"asks\":[{\"price\":64533.0,\"qty\":0.77479821}],\"checksum\":3061739456,\"timestamp\":\"2026-07-19T17:54:42.752434Z\"}]}"
]
