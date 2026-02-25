import streamlit as st
from whaleseason_tracker import scan_latest_whale_season_packs

st.set_page_config(page_title="Whale Season Scanner", page_icon="🐋", layout="wide")

st.title("🐋 Whale Season Scanner (Base)")
st.caption("Dò tìm giao dịch dựa trên dữ liệu 'whale-season' trong logs và trạng thái trả thưởng.")

target_count = st.sidebar.number_input("Số lượng pack cần tìm", 1, 50, 5)

if st.sidebar.button("🚀 Bắt đầu quét", type="primary"):
    with st.spinner("Đang tìm kiếm dữ liệu Whale Season..."):
        try:
            results = scan_latest_whale_season_packs(target_count)
            if not results:
                st.warning("Không tìm thấy giao dịch nào khớp với Whale Season.")
            else:
                st.success(f"Đã tìm thấy {len(results)} pack!")
                for i, pack in enumerate(results, start=1):
                    with st.expander(f"📦 Whale Pack #{i} - Block {pack['buy_block']}"):
                        st.markdown(f"**Buyer**: `{pack['buyer']}`")
                        st.markdown(f"**TX**: [Xem trên Blockscout](https://base.blockscout.com/tx/{pack['buy_tx_hash']})")
                        
                        if pack['reward']:
                            st.divider()
                            st.markdown("✅ **Phần thưởng đã trả:**")
                            for tk in pack['reward']['reward_tokens']:
                                st.success(f"💰 {tk['amount']} {tk['token_symbol']}")
                        else:
                            st.info("Chưa tìm thấy TX trả thưởng trong phạm vi 50 block.")
        except Exception as e:
            st.error(f"Lỗi: {e}")

