import time
import requests
from typing import Dict, List
from eth_utils import keccak, to_checksum_address

# ============================================================
# CONFIG
# ============================================================

BASE_BLOCKSCOUT_V2 = "https://base.blockscout.com/api/v2"
REQUEST_DELAY = 0.4
MAX_SCAN_BLOCKS = 6000

TARGET_PACK_TYPE = "whale-season"
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

# ============================================================
# EVENT SIGNATURE
# ============================================================

EVENT_SIGNATURE = "PackPurchased(address,string,string)"
EVENT_TOPIC0 = "0x" + keccak(text=EVENT_SIGNATURE).hex()

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
        time.sleep(0.4)
    return {}

# ============================================================
# ABI STRING DECODER (NO eth-abi)
# ============================================================

def _read_string(data: bytes, offset: int) -> str:
    start = int.from_bytes(data[offset:offset+32], "big")
    strlen = int.from_bytes(data[start:start+32], "big")
    return data[start+32:start+32+strlen].decode("utf-8", errors="ignore")

def decode_pack_event(log: Dict) -> Dict | None:
    try:
        if log["topics"][0].lower() != EVENT_TOPIC0.lower():
            return None

        buyer = to_checksum_address("0x" + log["topics"][1][-40:])

        data = bytes.fromhex(log["data"][2:])
        pack_type = _read_string(data, 0)
        pack_id = _read_string(data, 32)

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
# BLOCK / TX HELPERS
# ============================================================

def get_latest_block() -> int:
    data = _get(f"{BASE_BLOCKSCOUT_V2}/blocks?limit=1&sort=desc")
    return int(data["items"][0]["height"])

def get_block_transactions(block: int) -> List[Dict]:
    data = _get(f"{BASE_BLOCKSCOUT_V2}/blocks/{block}/transactions")
    return data.get("items", [])

def get_tx_logs(tx_hash: str) -> List[Dict]:
    data = _get(f"{BASE_BLOCKSCOUT_V2}/transactions/{tx_hash}/logs")
    return data.get("items", [])

# ============================================================
# MAIN SCANNER
# ============================================================

def scan_latest_whale_season_packs(target_count: int) -> List[Dict]:
    latest = get_latest_block()
    found: List[Dict] = []

    scanned = 0
    block = latest

    while block > 0 and scanned < MAX_SCAN_BLOCKS:
        txs = get_block_transactions(block)

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

        block -= 1
        scanned += 1

    return found
