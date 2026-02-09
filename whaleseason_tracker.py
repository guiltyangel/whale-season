import time
import requests
from typing import Dict, List
from eth_abi import decode
from eth_utils import keccak, to_checksum_address

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_V2 = "https://base.blockscout.com/api/v2"

REQUEST_DELAY = 0.4
MAX_SCAN_BLOCKS = 8000

TARGET_PACK_TYPE = "whale-season"

# Contract phát event
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

# ============================================================
# ABI EVENT DEFINITION
# ============================================================

EVENT_NAME = "PackPurchased(address,string,string)"
EVENT_TOPIC0 = keccak(text=EVENT_NAME).hex()

# ============================================================
# HTTP SAFE GET
# ============================================================

def _get(url: str, retries: int = 2) -> Dict:
    time.sleep(REQUEST_DELAY)

    for _ in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(0.5)

    return {}

# ============================================================
# BLOCK / TX HELPERS
# ============================================================

def get_latest_block() -> int:
    data = _get(f"{BASE_BLOCKSCOUT_V2}/blocks?limit=1&sort=desc")
    items = data.get("items", [])
    if not items:
        raise RuntimeError("Không lấy được latest block")
    return int(items[0]["height"])

def get_block_transactions(block_number: int) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_V2}/blocks/{block_number}/transactions"
    )
    return data.get("items", [])

def get_tx_logs(tx_hash: str) -> List[Dict]:
    data = _get(
        f"{BASE_BLOCKSCOUT_V2}/transactions/{tx_hash}/logs"
    )
    return data.get("items", [])

# ============================================================
# EVENT DECODER
# ============================================================

def decode_pack_event(log: Dict) -> Dict | None:
    """
    Decode PackPurchased event from raw log
    """
    try:
        topics = log["topics"]
        if topics[0].lower() != EVENT_TOPIC0:
            return None

        # indexed buyer
        buyer = "0x" + topics[1][-40:]
        buyer = to_checksum_address(buyer)

        # data chứa packType + packId
        data_bytes = bytes.fromhex(log["data"][2:])
        pack_type, pack_id = decode(
            ["string", "string"],
            data_bytes
        )

        if pack_type != TARGET_PACK_TYPE:
            return None

        return {
            "buy_tx_hash": log["transaction_hash"],
            "buyer": buyer,
            "pack_type": pack_type,
            "pack_id": pack_id,
            "buy_block": int(log["block_number"]),
        }

    except Exception:
        return None

# ============================================================
# MAIN SCANNER
# ============================================================

def scan_latest_whale_season_packs(target_count: int) -> List[Dict]:
    latest_block = get_latest_block()
    current_block = latest_block

    found: List[Dict] = []
    scanned = 0

    while current_block > 0 and scanned < MAX_SCAN_BLOCKS:
        txs = get_block_transactions(current_block)

        for tx in txs:
            if tx.get("to_address", "").lower() != RIPS_MANAGER:
                continue

            logs = get_tx_logs(tx["hash"])

            for log in logs:
                event = decode_pack_event(log)
                if event:
                    found.append(event)
                    if len(found) >= target_count:
                        return found

        current_block -= 1
        scanned += 1

    return found
