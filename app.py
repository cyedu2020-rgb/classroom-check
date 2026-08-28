import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="강의실 중복 체크 시스템", page_icon="🏫", layout="wide")

st.title("🏫 사회복지현장실습 강의실 중복 체크 시스템")
st.caption("수요일 개강 기준 (1주, 9주, 14주차 주말 출석) 강의실 사용 일정 충돌을 자동 검사합니다.")

# 세션 상태 초기화
if "schedules" not in st.session_state:
    st.session_state.schedules = []

# 출석일 계산 함수
def get_attendance_dates(wed_date, weekend_day):
    offset = 3 if weekend_day == '토' else 4
    first_weekend = wed_date + timedelta(days=offset)
    week_1 = first_weekend
    week_9 = first_weekend + timedelta(weeks=8)
    week_14 = first_weekend + timedelta(weeks=13)
    return {
        "1주차": week_1,
        "9주차": week_9,
        "14주차": week_14
    }

# 중복 검사 함수 (각 인덱스별 중복되는 주차 정보 추적)
def check_conflicts(schedules):
    conflicts = []
    # 예: {0: {'1주차'}, 1: {'9주차'}}
    conflicted_weeks = {i: set() for i in range(len(schedules))}
    num_schedules = len(schedules)

    for i in range(num_schedules):
        for j in range(i + 1, num_schedules):
            sch1 = schedules[i]
            sch2 = schedules[j]

            # 두 수강 건의 각 주차별 날짜 비교
            for week_label1, date1 in sch1["dates"].items():
                for week_label2, date2 in sch2["dates"].items():
                    if date1 == date2:
                        # 날짜가 동일할 때 시간대 교집합 체크
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

# 사이드바 입력 폼
st.sidebar.header("📝 새 수업 일정 등록")

with st.sidebar.form("schedule_form", clear_on_submit=True):
    institution = st.selectbox("기관 선택", ["사이에듀", "마이에듀원격"])
    class_name = st.text_input("수업/분반 이름", placeholder="예: 실습 1반")
    wed_date = st.date_input("개강일 선택 (수요일)", value=datetime.today())
    weekend_day = st.radio("출석 요일", ["토", "일"], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.time_input("시작 시간", value=datetime.strptime("09:00", "%H:%M").time())
    with col2:
        end_time = st.time_input("종료 시간", value=datetime.strptime("13:00", "%H:%M").time())

    submit_button = st.form_submit_button("일정 추가하기")

if submit_button:
    if not class_name.strip():
        st.sidebar.error("수업 이름을 입력해 주세요.")
    elif wed_date.weekday() != 2:
        st.sidebar.error("❌ 선택한 날짜가 수요일이 아닙니다.")
    elif start_time >= end_time:
        st.sidebar.error("❌ 종료 시간은 시작 시간보다 뒤여야 합니다.")
    else:
        dates_dict = get_attendance_dates(wed_date, weekend_day)
        st.session_state.schedules.append({
            "institution": institution,
            "class_name": class_name,
            "wed_date": wed_date,
            "weekend_day": weekend_day,
            "start_time": start_time,
            "end_time": end_time,
            "dates": dates_dict
        })
        st.sidebar.success(f"[{institution}] '{class_name}' 일정이 추가되었습니다!")

# 메인 화면
if not st.session_state.schedules:
    st.info("👈 왼쪽 사이드바에서 개강일과 수업 시간을 등록해 주세요.")
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
            "conflicted_weeks": list(conflicted_weeks[idx])  # 해당 행의 중복 주차 리스트
        })
    
    df = pd.DataFrame(display_data)

    # 중복되는 주차의 칸에만 빨간색 하이라이트 적용
    def highlight_specific_weeks(row):
        styles = [''] * len(row)
        c_weeks = row['conflicted_weeks']
        
        target_cols = {
            "1주차": "1주차 출석일",
            "9주차": "9주차 출석일",
            "14주차": "14주차 출석일"
        }
        
        for w_label, col_name in target_cols.items():
            if w_label in c_weeks:
                col_idx = row.index.get_loc(col_name)
                styles[col_idx] = 'background-color: #ff4b4b; color: white; font-weight: bold;'
                
        return styles

    styled_df = df.style.apply(highlight_specific_weeks, axis=1)

    # 화면에 출력 (내부 판별용 conflicted_weeks 열은 숨김)
    st.dataframe(styled_df, column_config={"conflicted_weeks": None}, use_container_width=True)

    if st.button("전체 일정 초기화"):
        st.session_state.schedules = []
        st.rerun()
