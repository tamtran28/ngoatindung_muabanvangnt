import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.title("📊 Báo cáo Giao dịch Ngoại tệ – TC5 & TC6")

st.write("Upload các file Excel để tạo báo cáo theo tiêu chí 5 & 6.")

# ---------------- UPLOAD FILES ----------------
file_muc19 = st.file_uploader("Upload file MUC19", type=["xlsx"])
file_muc20 = st.file_uploader("Upload file MUC20", type=["xlsx"])
file_muc21 = st.file_uploader("Upload file MUC21", type=["xlsx"])

if file_muc19 and file_muc20 and file_muc21:

    df_muc19 = pd.read_excel(file_muc19, dtype=str)
    df_muc20 = pd.read_excel(file_muc20, dtype=str)
    df_muc21 = pd.read_excel(file_muc21, dtype=str)

    # ================== XỬ LÝ TC5 ====================
    df = df_muc19.copy()

    df['SOL'] = df['SOL_ID']
    df['ĐON_VI'] = df['SOL_DESC']
    df['CIF'] = df['CIF_ID']
    df['Tên KH'] = df['CUST_NAME']
    df['DEAL_DATE'] = df['DEAL_DATE']
    df['DUE_DATE'] = df['DUE_DATE']

    df['P/S'] = np.where(df['PURCHASED_AMOUNT'].fillna(0) != 0, 'P',
                         np.where(df['SOLD_AMOUNT'].fillna(0) != 0, 'S', ''))

    df['AMOUNT'] = np.where(df['P/S'] == 'P', df['PURCHASED_AMOUNT'],
                            np.where(df['P/S'] == 'S', df['SOLD_AMOUNT'], np.nan))

    df['RATE'] = np.where(df['P/S'] == 'P', df['PURCHASED_RATE'],
                          np.where(df['P/S'] == 'S', df['SOLD_RATE'], np.nan))

    df['TREASURY_RATE'] = np.where(df['P/S'] == 'P', df['TREASURY_BUY_RATE'],
                                   np.where(df['P/S'] == 'S', df['TREASURY_SELL_RATE'], np.nan))

    df['Quy đổi VND'] = df['VALUE_VND']
    df['TRANSACTION_NO'] = df['TRANSACTION_NO'].astype(str).str.strip()

    df['MAKER'] = df['DEALER'].where(
        df['DEALER'].str.contains(r'\.') & ~df['DEALER'].str.contains("ROBOT"),
        np.nan
    )

    df['MAKER_DATE'] = pd.to_datetime(df['MAKER_DATE'], errors='coerce')
    df['VERIFY_DATE'] = pd.to_datetime(df['VERIFY_DATE'], errors='coerce')

    df['Mục đích'] = df['PURPOSE_OF_TRANSACTION']
    df['Transaction_type'] = df['TRANSACTION_TYPE']
    df['Kết quả Lãi/lỗ'] = df['KETQUA']
    df['Số tiền Lãi lỗ'] = pd.to_numeric(df['SOTIEN_LAI_LO'], errors='coerce')

    df['Loại tiền KQ'] = df['KYQUY_NT']
    df['Số tiền KQ'] = df['LOAITIEN_KYQUY']

    df['GD lỗ > 100.000đ'] = np.where(
        (df['Kết quả Lãi/lỗ'] == 'LO') & (df['Số tiền Lãi lỗ'].abs() >= 100000),
        'X', ''
    )

    columns = [
        'SOL', 'ĐON_VI', 'CIF', 'Tên KH', 'DEAL_DATE', 'DUE_DATE', 'P/S', 'AMOUNT',
        'RATE', 'TREASURY_BUY_RATE', 'Quy đổi VND', 'TRANSACTION_NO', 'MAKER',
        'MAKER_DATE', 'CHECKER', 'VERIFY_DATE', 'Mục đích', 'Transaction_type',
        'Kết quả Lãi/lỗ', 'Số tiền Lãi lỗ', 'Loại tiền KQ', 'Số tiền KQ', 'GD lỗ > 100.000đ'
    ]

    df_tc5 = df[columns]

    # ================== XỬ LÝ TC6 ====================

    df_tc6 = df_tc5.copy()

    df_tc6['TIME_DELAY'] = df_tc6['VERIFY_DATE'] - df_tc6['MAKER_DATE']
    df_tc6['GD duyệt trễ > 30p'] = df_tc6['TIME_DELAY'].apply(
        lambda x: str(x) if x and x > pd.Timedelta(minutes=20) else ""
    )

    df_tc6['TRANSACTION_NO_CLEAN'] = df_tc6['TRANSACTION_NO'].astype(str).str.strip()

    df_muc21['FRWRD_CNTRCT_NUM'] = df_muc21['FRWRD_CNTRCT_NUM'].astype(str).str.strip()
    df_muc20['TRAN_ID'] = df_muc20['TRAN_ID'].astype(str).str.strip()
    df_muc20['TRAN_DATE'] = pd.to_datetime(df_muc20['TRAN_DATE'])

    cond_a = df_tc6['TRANSACTION_NO_CLEAN'].isin(
        df_muc21.loc[df_muc21['TREA_REF_NUM'].notna(), 'FRWRD_CNTRCT_NUM']
    )

    cond_b = df_tc6.merge(
        df_muc20[df_muc20['TREA_REF_NUM'].notna()],
        left_on=['TRANSACTION_NO_CLEAN', 'MAKER_DATE'],
        right_on=['TRAN_ID', 'TRAN_DATE'],
        how='left',
        indicator=True
    )['_merge'] == 'both'

    df_tc6['GD Rate Request'] = np.where(cond_a | cond_b, 'X', '')

    df_tc6['GD CASH'] = df_tc6['Transaction_type'].str.upper().apply(lambda x: 'X' if x == 'CASH' else '')

    df_tc6['DEAL_DATE'] = pd.to_datetime(df_tc6['DEAL_DATE'])
    df_tc6['DUE_DATE'] = pd.to_datetime(df_tc6['DUE_DATE'])

    df_tc6['GD SPOT T0'] = df_tc6.apply(
        lambda row: 'X'
        if row['Transaction_type'].upper() == 'SPOT'
        and (row['DUE_DATE'] - row['DEAL_DATE']).days == 0
        else '',
        axis=1
    )

    # ---------------- EXPORT FILE ----------------
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_tc5.to_excel(writer, sheet_name='tieuchi5', index=False)
        df_tc6.to_excel(writer, sheet_name='tieuchi6', index=False)

    st.success("🎉 Xử lý hoàn tất!")

    st.download_button(
        label="📥 Tải xuống báo cáo Excel",
        data=output.getvalue(),
        file_name="bao_cao_ngoai_te_TC56.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("Vui lòng upload đủ 3 file MUC19, MUC20 và MUC21 để xử lý.")
