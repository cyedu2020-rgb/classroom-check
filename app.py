import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import io

# ---------------------------------------------------------
# 1. 페이지 설정 및 초기화
# ---------------------------------------------------------
st.set_page_config(page_title="강의실 중복 체크 시스템", page_icon="🏫", layout="wide")

st.title("🏫 사회복지현장실습 강의실 중복 체크 시스템")
st.caption("수요일 개강 기준 (1주, 9주, 14주차 주말 출석) - 엑셀/CSV 일괄 업로드 지원")

if "schedules" not in st.session_state:
    st.session_state.schedules = []

# ---------------------------------------------------------
# 2. 핵심 알고리즘 함수
# ---------------------------------------------------------
def get_attendance_dates(wed_date, weekend_day):
    offset = 3 if weekend_day == '토' else 4
    first_weekend = wed_date + timedelta(days=offset)
    return {
        "1주차": first_weekend,
        "9주차": first_weekend + timedelta(weeks=8),
        "14주차": first_weekend + timedelta(weeks=13)
    }

def check_conflicts(schedules):
    conflicts = []
    conflicted_weeks = {i: set() for i in range(len(schedules))}
    num_schedules = len(schedules)

    for i in range(num_schedules):
        for j in range(i + 1, num_schedules):
            sch1 = schedules[i]
            sch2 = schedules[j]

            for week_label1, date1 in sch1["dates"].items():
                for week_label2, date2 in sch2["dates"].items():
                    if date1 == date2:
                        latest_start = max(sch1["start_time"], sch2["start_time"])
                        earliest_end = min(sch1["end_time"], sch2["end_time"])

                        if latest_start < earliest_end:
                            conflicted_weeks[i].add(week_label1)
                            conflicted_weeks[j].add(week_label2)
                            conflicts.append({
                                "date": date1.strftime("%Y-%m-%d (%a)"),
                                "inst1": sch1["institution"],
                                "class1": sch1["class_name"],
                                "week1": week_label1,
                                "time1": f"{sch1['start_time'].strftime('%H:%M')} ~ {sch1['end_time'].strftime('%H:%M')}",
                                "inst2": sch2["institution"],
                                "class2": sch2["class_name"],
                                "week2": week_label2,
                                "time2": f"{sch2['start_time'].strftime('%H:%M')} ~ {sch2['end_time'].strftime('%H:%M')}"
                            })
    return conflicts, conflicted_weeks

# ---------------------------------------------------------
# 3. 사이드바: 파일 일괄 업로드 & 샘플 양식 다운로드
# ---------------------------------------------------------
st.sidebar.header("📂 일정 파일 일괄 등록")

# 샘플 CSV 다운로드 제공
sample_df = pd.DataFrame([
    {"기관": "사이에듀", "수업명": "실습 A반", "개강일": "2026-09-02", "출석요일": "토", "시작시간": "09:00", "종료시간": "13:00"},
    {"기관": "마이에듀원격", "수업명": "실습 1반", "개강일": "2026-09-02", "출석요일": "토", "시작시간": "12:00", "종료시간": "16:00"}
])
sample_csv = sample_df.to_csv(index=False).encode('utf-8-sig')

st.sidebar.download_button(
    label="📄 엑셀 작성용 샘플 양식 다운로드",
    data=sample_csv,
    file_name="강의실일정_샘플양식.csv",
    mime="text/csv"
)

st.sidebar.divider()

uploaded_file = st.sidebar.file_uploader("작성한 일정 파일(.csv, .xlsx) 업로드", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_upload = pd.read_csv(uploaded_file)
        else:
            df_upload = pd.read_excel(uploaded_file)

        loaded_schedules = []
        for idx, row in df_upload.iterrows():
            w_date = datetime.strptime(str(row["개강일"]).strip(), "%Y-%m-%d").date()
            
            s_str = str(row["시작시간"]).strip()
            e_str = str(row["종료시간"]).strip()
            s_time = datetime.strptime(s_str if len(s_str) > 5 else s_str + ":00", "%H:%M:%S").time()
            e_time = datetime.strptime(e_str if len(e_str) > 5 else e_str + ":00", "%H:%M:%S").time()

            loaded_schedules.append({
                "institution": str(row["기관"]).strip(),
                "class_name": str(row["수업명"]).strip(),
                "wed_date": w_date,
                "weekend_day": str(row["출석요일"]).strip(),
                "start_time": s_time,
                "end_time": e_time,
                "dates": get_attendance_dates(w_date, str(row["출석요일"]).strip())
            })

        st.session_state.schedules = loaded_schedules
        st.sidebar.success(f"총 {len(loaded_schedules)}개 일정을 성공적으로 불러왔습니다!")

    except Exception as e:
        st.sidebar.error("파일 처리 중 오류가 발생했습니다. 양식을 확인해 주세요.")

st.sidebar.divider()

# 개별 수동 등록 폼도 함께 유지
with st.sidebar.expander("➕ 수동으로 1개씩 일정 추가하기"):
    with st.form("manual_form", clear_on_submit=True):
        inst = st.selectbox("기관 선택", ["사이에듀", "마이에듀원격"])
        c_name = st.text_input("수업/분반 이름")
        w_date = st.date_input("개강일 선택 (수요일)", value=datetime.today())
        w_day = st.radio("출석 요일", ["토", "일"], horizontal=True)
        col1, col2 = st.columns(2)
        with col1:
            s_time = st.time_input("시작 시간", value=datetime.strptime("09:00", "%H:%M").time())
        with col2:
            e_time = st.time_input("종료 시간", value=datetime.strptime("13:00", "%H:%M").time())
        submit_btn = st.form_submit_button("추가")

    if submit_btn:
        if not c_name.strip():
            st.sidebar.error("수업 이름을 입력하세요.")
        elif w_date.weekday() != 2:
            st.sidebar.error("개강일은 수요일이어야 합니다.")
        elif s_time >= e_time:
            st.sidebar.error("종료 시간은 시작 시간보다 뒤여야 합니다.")
        else:
            st.session_state.schedules.append({
                "institution": inst,
                "class_name": c_name,
                "wed_date": w_date,
                "weekend_day": w_day,
                "start_time": s_time,
                "end_time": e_time,
                "dates": get_attendance_dates(w_date, w_day)
            })
            st.sidebar.success("일정이 추가되었습니다!")
            st.rerun()

# ---------------------------------------------------------
# 4. 메인 화면 Display 및 중복 체크
# ---------------------------------------------------------
if not st.session_state.schedules:
    st.info("👈 왼쪽 사이드바에서 샘플 양식을 다운로드하여 일정을 작성한 후 업로드해 주세요.")
else:
    conflicts, conflicted_weeks = check_conflicts(st.session_state.schedules)
    
    st.subheader("🚨 중복 검사 결과")
    if conflicts:
        st.error(f"총 **{len(conflicts)}건**의 강의실 시간 중복이 감지되었습니다!")
        for c in conflicts:
            st.warning(
                f"**[중복 날짜: {c['date']}]**\n\n"
                f"- **{c['inst1']}** ({c['class1']} - {c['week1']}) : {c['time1']}\n"
                f"- **{c['inst2']}** ({c['class2']} - {c['week2']}) : {c['time2']}"
            )
    else:
        st.success("✅ 강의실 중복 일정이 없습니다!")

    st.divider()

    st.subheader("📋 전체 등록 수업 및 출석일 목록")
    display_data = []
    for idx, item in enumerate(st.session_state.schedules):
        display_data.append({
            "번호": idx + 1,
            "기관": item["institution"],
            "수업명": item["class_name"],
            "개강일(수)": item["wed_date"].strftime("%Y-%m-%d"),
            "출석요일": item["weekend_day"],
            "시간대": f"{item['start_time'].strftime('%H:%M')} ~ {item['end_time'].strftime('%H:%M')}",
            "1주차 출석일": item["dates"]["1주차"].strftime("%Y-%m-%d"),
            "9주차 출석일": item["dates"]["9주차"].strftime("%Y-%m-%d"),
            "14주차 출석일": item["dates"]["14주차"].strftime("%Y-%m-%d"),
            "conflicted_weeks": list(conflicted_weeks[idx])
        })
    
    df = pd.DataFrame(display_data)

    def highlight_specific_weeks(row):
        styles = [''] * len(row)
        c_weeks = row['conflicted_weeks']
        target_cols = {"1주차": "1주차 출석일", "9주차": "9주차 출석일", "14주차": "14주차 출석일"}
        
        for w_label, col_name in target_cols.items():
            if w_label in c_weeks:
                col_idx = row.index.get_loc(col_name)
                styles[col_idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;'
        return styles

    styled_df = df.style.apply(highlight_specific_weeks, axis=1)
    st.dataframe(styled_df, column_config={"conflicted_weeks": None}, use_container_width=True)

    # 내보내기 버튼 (현재 화면 결과 다운로드)
    export_df = pd.DataFrame([{
        "기관": s["institution"],
        "수업명": s["class_name"],
        "개강일": s["wed_date"].strftime("%Y-%m-%d"),
        "출석요일": s["weekend_day"],
        "시작시간": s["start_time"].strftime("%H:%M"),
        "종료시간": s["end_time"].strftime("%H:%M")
    } for s in st.session_state.schedules])

    st.download_button(
        label="📥 현재 종합 일정 파일로 다운로드하기",
        data=export_df.to_csv(index=False).encode('utf-8-sig'),
        file_name="종합_강의실일정.csv",
        mime="text/csv"
    )

    st.write("")
    if st.button("🚨 전체 일정 초기화"):
        st.session_state.schedules = []
        st.rerun()
