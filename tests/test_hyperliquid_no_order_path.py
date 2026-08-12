"""WO-066 §2 — THE ORDER PATH IS ABSENT, NOT DISABLED. Asserted STRUCTURALLY.

§2's wording is exact: *"Confirm no order path exists in the adapter at all — not disabled,
absent."* The difference is not pedantry. **A disabled order path can be re-enabled by a flag, an
environment variable, or a merge. An absent one cannot** — re-enabling it requires writing code,
which is reviewable.

So these tests do not call the adapter and check it refuses. **They inspect the module's symbols,
its source, and its imports**, and assert the capability is not present to be enabled. A
behavioural test ("ordering raises") would pass just as happily against a disabled path, which is
exactly the state §2 forbids.
"""

import ast
import inspect
import pathlib

import pytest

from trading.data.adapters import hyperliquid_v1 as hl


# The vocabulary an order path would have to use. Deliberately broad: this is a structural
# guard, so a false positive costs a rename and a false negative costs the whole property.
ORDER_PATH_TOKENS = (
    "place_order", "submit_order", "create_order", "send_order", "new_order",
    "cancel_order", "cancel_all", "modify_order", "amend_order", "replace_order",
    "sign", "signature", "signed", "private_key", "privatekey", "secret_key",
    "wallet", "account_address", "api_secret", "eip712", "eip_712",
    "withdraw", "transfer", "approve", "leverage", "margin_mode",
)

SIGNING_CAPABLE_MODULES = (
    "eth_account", "web3", "eth_keys", "ecdsa", "coincurve", "nacl", "secp256k1",
    "cryptography", "hmac",
)


def _module_source() -> str:
    return pathlib.Path(inspect.getfile(hl)).read_text(encoding="utf-8")


def _code_only(source: str) -> str:
    """Source with docstrings and comments stripped.

    The module DOCUMENTS the absence — it names `{"method":"post"}` to say it is never
    constructed, and lists the tokens it avoids. Matching against prose would fail on the very
    sentences that establish the property, so the assertion is made against CODE.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


def test_no_order_path_symbol_exists_on_the_module_or_the_adapter():
    """No public symbol on the module or the adapter class names an order-path capability."""
    names = set(dir(hl)) | set(dir(hl.HyperliquidBookAdapter))
    offenders = sorted(n for n in names
                       if any(tok in n.lower() for tok in ORDER_PATH_TOKENS))
    assert offenders == [], (
        f"ORDER_PATH_PRESENT: {offenders}. §2 requires the order path to be ABSENT, not "
        f"disabled — a symbol that exists can be called."
    )


def test_no_order_path_token_appears_in_the_module_CODE():
    """No order-path token appears in executable code (docstrings/comments excluded)."""
    code = _code_only(_module_source()).lower()
    offenders = sorted({tok for tok in ORDER_PATH_TOKENS if tok in code})
    assert offenders == [], (
        f"ORDER_PATH_TOKEN_IN_CODE: {offenders}. The module may DOCUMENT what it does not do; "
        f"it may not contain the capability."
    )


def test_the_venues_own_order_method_is_never_constructed():
    """Hyperliquid exposes order actions via {"method":"post"} on the SAME socket.

    Every outbound frame this adapter can send is enumerated by `subscriptions()` plus the ping;
    none of them is a `post`. This is the venue-specific form of the guard: the generic token list
    would not catch `"post"`, which is an ordinary word.
    """
    outbound = hl_adapter_outbound_frames()
    methods = {f.get("method") for f in outbound}
    assert methods == {"subscribe", "ping"}, (
        f"UNEXPECTED_OUTBOUND_METHOD: {methods}. Only 'subscribe' and 'ping' are read-only; "
        f"'post' is Hyperliquid's ORDER ACTION method and must never be constructed here."
    )


def hl_adapter_outbound_frames() -> list:
    a = hl.HyperliquidBookAdapter()
    return list(a.subscriptions()) + [hl.build_ping()]


def test_module_imports_nothing_signing_capable():
    """The module imports no library that could sign a transaction."""
    tree = ast.parse(_module_source())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    offenders = sorted(imported & set(SIGNING_CAPABLE_MODULES))
    assert offenders == [], (
        f"SIGNING_CAPABLE_IMPORT: {offenders}. A capture module must not be able to sign."
    )


# ── the venue's declared taxonomy ─────────────────────────────────────────────────────────────

def test_four_gap_causes_and_the_fifth_is_documented_absent():
    """FOUR causes, and CHECKSUM_RESYNC's absence carries its reason (ratified, WO-066)."""
    assert len(hl.GAP_CAUSES) == 4
    assert "CHECKSUM_RESYNC" not in hl.GAP_CAUSES
    assert "CHECKSUM_RESYNC" in hl.CAUSE_ABSENT_FROM_THIS_VENUE
    assert "no book checksum" in hl.CAUSE_ABSENT_FROM_THIS_VENUE["CHECKSUM_RESYNC"]


def test_checksum_counter_is_NULL_not_ZERO():
    """`0` would claim we checked and found none. `None` says there is nothing to check.

    This is WO-054's `count: 0` vs `count: null` distinction applied to an integrity metric, and
    it is the reason the counter is reported at all rather than silently dropped.
    """
    counters = hl.HyperliquidBookAdapter().get_diagnostic_counters()
    assert counters["checksum_failures_total"] is None
    assert counters["checksum_failures_total"] != 0
    assert counters["checksum_absent_reason"]


# ── the evidentiary bound (§3.4) ──────────────────────────────────────────────────────────────

def test_subscribes_to_the_DEEPER_feed_and_declares_the_bound():
    """`fast` is omitted, which selects the 20-level feed; the bound is declared, not implied."""
    sub = hl.build_book_subscribe()
    assert sub == {"method": "subscribe",
                   "subscription": {"type": "l2Book", "coin": "BTC"}}
    assert "fast" not in sub["subscription"]
    assert hl.PUBLISHED_LEVELS == 20


def test_snapshot_carries_its_own_level_count():
    """A feed that silently returned 5 where 20 was requested must be detectable."""
    raw = {"channel": "l2Book", "data": {
        "coin": "BTC", "time": 1786475506066,
        "levels": [[{"px": "63000.0", "sz": "1.5", "n": 3}],
                   [{"px": "63001.0", "sz": "2.0", "n": 4},
                    {"px": "63002.0", "sz": "1.0", "n": 1}]]}}
    book = hl.parse_l2_book(raw)
    assert book is not None
    assert book.levels_published == 2          # observed, not assumed
    assert book.bids[0].px == hl.Decimal("63000.0")
    assert book.asks[0].sz == hl.Decimal("2.0")


# ── parsing refuses to guess ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [
    {"channel": "trades", "data": []},
    {"channel": "pong"},
    {"channel": "l2Book", "data": {"coin": "BTC"}},                 # no levels
    {"channel": "l2Book", "data": {"coin": "BTC", "levels": []}},   # wrong shape
    {},
])
def test_malformed_or_foreign_book_frames_return_None_not_a_guess(raw):
    assert hl.parse_l2_book(raw) is None


def test_registered_but_NOT_declared_live_capable():
    """0.14: declaring a capability the adapter does not have is the WO-055 defect.

    `live_capture=True` promises `get_live_market_data`, a gap ledger, and the checksum surface
    `trading.loop.live_capture` calls unconditionally. None of that is wired yet, so the flag is
    deliberately off and this test pins that until §3.3 wires it.
    """
    from trading.data.adapters import registry
    assert "hyperliquid_v1" in registry.registered_names()
    assert registry.is_live_capable("hyperliquid_v1") is False
    assert not hasattr(hl.HyperliquidBookAdapter, "get_live_market_data")
