import streamlit as st
from whaleseason_tracker import scan_latest_whale_season_packs

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Whale Season Scanner",
    layout="wide"
)

st.title("🐋 Whale Season On-chain Scanner (Base)")
st.caption(
    "Quét ngược block trên Base và decode event log theo ABI "
    "để tìm pack type **whale-season**."
)

st.divider()

# ============================================================
# USER INPUT
# ============================================================

col1, col2 = st.columns([1, 3])

with col1:
    target_count = st.number_input(
        "Số pack whale-season cần tìm",
        min_value=1,
        max_value=50,
        value=3,
        step=1
    )

with col2:
    st.markdown(
        """
        **Cách hoạt động**
        - Lấy block mới nhất trên Base  
        - Quét ngược từng block  
        - Lọc transaction gửi tới contract  
        - Decode event `PackPurchased` bằng ABI  
        - Dừng khi đủ số pack yêu cầu  
        """
    )

scan_btn = st.button("🚀 Bắt đầu scan", type="primary")

# ============================================================
# SCAN ACTION
# ============================================================

if scan_btn:
    with st.spinner("⏳ Đang scan on-chain… việc này có thể mất 1–3 phút"):
        try:
            results = scan_latest_whale_season_packs(target_count)

            st.divider()

            if not results:
                st.warning("❌ Không tìm thấy pack whale-season nào trong phạm vi scan.")
            else:
                st.success(f"✅ Đã tìm được {len(results)} pack whale-season")

                for i, pack in enumerate(results, start=1):
                    with st.expander(f"🐋 Pack #{i}", expanded=False):
                        st.write("**Tx Hash:**", pack["buy_tx_hash"])
                        st.write("**Buyer:**", pack["buyer"])
                        st.write("**Block:**", pack["buy_block"])
                        st.write("**Pack Type:**", pack["pack_type"])
                        st.write("**Pack ID:**", pack["pack_id"])

                        st.markdown(
                            f"[🔗 Xem trên Basescan]"
                            f"(https://basescan.org/tx/{pack['buy_tx_hash']})"
                        )

        except Exception as e:
            st.error("❌ Có lỗi xảy ra trong quá trình scan")
            st.exception(e)

# ============================================================
# FOOTER
# ============================================================

st.divider()
st.caption(
    "Scanner decode event log trực tiếp từ ABI – "
    "không phụ thuộc token transfer hay explorer mapping."
)

