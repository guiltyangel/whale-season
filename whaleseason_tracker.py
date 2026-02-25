import requests
import time
from typing import List, Dict, Optional
from requests.exceptions import ReadTimeout, ConnectionError

# ============================================================
# CONFIGURATION
# ============================================================
BASE_BLOCKSCOUT_API = "https://base.blockscout.com/api"
USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913".lower()
RIPS_MANAGER = "0x7f84b6cd975db619e3f872e3f8734960353c7a09".lower()

# Hex của chuỗi "whale-season" để nhận diện trong data log
TARGET_PACK_HEX = "7768616c652d736561736f6e" 

REQUEST_DELAY = 0.5  # Tránh bị Blockscout chặn (Rate Limit)
MAX_RETRIES = 3      
MAX_LOOKAHEAD_BLOCKS = 50 

# ============================================================
# HTTP HELPERS
# ============================================================
def _get(url: str) -> Dict:
    for i in range(MAX_RETRIES):
        try:
            time.sleep(REQUEST_DELAY)
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            return r.json()
        except (ReadTimeout, ConnectionError):
            if i == MAX_RETRIES - 1: raise
            time.sleep(2)
    return {}

def get_tx_logs(tx_hash: str) -> List[Dict]:
    url = f"{BASE_BLOCKSCOUT_API}?module=logs&action=getLogs&txhash={tx_hash}"
    data = _get(url)
    result = data.get("result", [])
    return result if isinstance(result, list) else []

# ============================================================
# LOGIC: DYNAMIC DATA SCANNING
# ============================================================
def is_buy_whale_season(tx_hash: str) -> bool:
    """Quét toàn bộ logs trong TX để tìm nội dung whale-season."""
    logs = get_tx_logs(tx_hash)
    for log in logs:
        data = log.get("data", "").lower()
        # Tìm kiếm trực tiếp chuỗi hex của whale-season trong data
        if TARGET_PACK_HEX in data:
            return True
    return False

def find_reward_payout(buyer: str, buy_block: int) -> Optional[Dict]:
    """Tìm giao dịch trả thưởng (Token Transfer) từ Manager tới Buyer."""
    start = buy_block + 1
    end = buy_block + MAX_LOOKAHEAD_BLOCKS
    url = (f"{BASE_BLOCKSCOUT_API}?module=account&action=tokentx"
           f"&address={RIPS_MANAGER}&startblock={start}&endblock={end}&sort=asc")
    
    data = _get(url)
    transfers = data.get("result", [])
    if not isinstance(transfers, list): return None

    payouts = [t for t in transfers if t.get("to", "").lower() == buyer.lower()]
    if not payouts: return None

    payout_tx = payouts[0].get("hash")
    reward_tokens = []
    for t in payouts:
        if t.get("hash") == payout_tx:
            decimal = int(t.get("tokenDecimal", 18))
            amount = int(t.get("value", 0)) / (10 ** decimal)
            reward_tokens.append({
                "token_symbol": t.get("tokenSymbol", "Unknown"),
                "amount": amount
            })

    return {
        "reward_tx_hash": payout_tx,
        "reward_block": int(payouts[0].get("blockNumber", 0)),
        "reward_tokens": reward_tokens
    }

def scan_latest_whale_season_packs(target_count: int) -> List[Dict]:
    results = []
    page = 1
    processed_txs = set()

    # Sử dụng phân trang (offset=50) thay vì quét từng block đơn lẻ để tránh Timeout
    while len(results) < target_count and page <= 50:
        url = (f"{BASE_BLOCKSCOUT_API}?module=account&action=tokentx"
               f"&address={RIPS_MANAGER}&page={page}&offset=50&sort=desc")
        
        data = _get(url)
        transfers = data.get("result", [])
        if not isinstance(transfers, list) or not transfers: break

        for t in transfers:
            tx_hash = t.get("hash")
            if not tx_hash or tx_hash in processed_txs: continue
            processed_txs.add(tx_hash)

            # Điều kiện: Người dùng gửi USDC tới contract RIPS_MANAGER
            if (t.get("tokenAddress", "").lower() == USDC_ADDRESS and 
                t.get("to", "").lower() == RIPS_MANAGER):
                
                # Kiểm tra nội dung whale-season trong logs của TX này
                if is_buy_whale_season(tx_hash):
                    buyer = t.get("from", "").lower()
                    buy_block = int(t.get("blockNumber", 0))
                    reward = find_reward_payout(buyer, buy_block)

                    results.append({
                        "buy_tx_hash": tx_hash,
                        "buy_block": buy_block,
                        "buyer": buyer,
                        "reward": reward
                    })
                    if len(results) >= target_count: break
        page += 1
    return results
