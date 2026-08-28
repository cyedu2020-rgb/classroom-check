import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# ---------------------------------------------------------
# 1. 기본 페이지 설정 및 스타일
# ---------------------------------------------------------
st.set_page_config(page_title="강의실 중복 체크 시스템", page_icon="🏫", layout="wide")

st.title("🏫 사회복지현장실습 강의실 중복 체크 시스템")
st.caption("수요일 개강 기준 (1주, 9주, 14주차 주말 출석) 강의실 사용 일정 충돌을 자동 검사합니다.")

# 세션 상태(Session State) 초기화
if "schedules" not in st.session_state:
    st.session_state.schedules = []

# ---------------------------------------------------------
# 2. 로직 함수 정의
# ---------------------------------------------------------
def get_attendance_dates(wed_date, weekend_day):
    """수요일 개강일 기준으로 1주, 9주, 14주차 주말 날짜 계산"""
    offset = 3 if weekend_day == '토' else 4
    first_weekend = wed_date + timedelta(days=offset)
    
    week_1 = first_weekend
    week_9 = first_weekend + timedelta(weeks=8)
    week_14 = first_weekend + timedelta(weeks=13)
    
    return [week_1, week_9, week_14]

def check_conflicts(schedules):
    """일정 간 중복 검사 로직"""
    conflicts = []
    num_schedules = len(schedules)

    for i in range(num_schedules):
        for j in range(i + 1, num_schedules):
            sch1 = schedules[i]
            sch2 = schedules[j]

            # 날짜 교집합 확인
            common_dates = set(sch1["dates"]).intersection(set(sch2["dates"]))

            for common_date in common_dates:
                # 시간 교집합 확인: Max(Start1, Start2) < Min(End1, End2)
                latest_start = max(sch1["start_time"], sch2["start_time"])
                earliest_end = min(sch1["end_time"], sch2["end_time"])

                if latest_start < earliest_end:
                    conflicts.append({
                        "date": common_date.strftime("%Y-%m-%d (%a)"),
                        "inst1": sch1["institution"],
                        "class1": sch1["class_name"],
                        "time1": f"{sch1['start_time'].strftime('%H:%M')} ~ {sch1['end_time'].strftime('%H:%M')}",
                        "inst2": sch2["institution"],
                        "class2": sch2["class_name"],
                        "time2": f"{sch2['start_time'].strftime('%H:%M')} ~ {sch2['end_time'].strftime('%H:%M')}"
                    })
    return conflicts

# ---------------------------------------------------------
# 3. 사이드바: 일정 등록 폼
# ---------------------------------------------------------
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

# 폼 제출 시 유효성 검사 및 저장
if submit_button:
    if not class_name.strip():
        st.sidebar.error("수업 이름을 입력해 주세요.")
    elif wed_date.weekday() != 2: # 2 = 수요일
        st.sidebar.error("❌ 선택한 날짜가 수요일이 아닙니다. 개강일은 수요일이어야 합니다.")
    elif start_time >= end_time:
        st.sidebar.error("❌ 종료 시간은 시작 시간보다 뒤여야 합니다.")
    else:
        dates = get_attendance_dates(wed_date, weekend_day)
        st.session_state.schedules.append({
            "institution": institution,
            "class_name": class_name,
            "wed_date": wed_date,
            "weekend_day": weekend_day,
            "start_time": start_time,
            "end_time": end_time,
            "dates": dates
        })
        st.sidebar.success(f"'{class_name}' 일정이 추가되었습니다!")

# ---------------------------------------------------------
# 4. 메인 화면 Display
# ---------------------------------------------------------
if not st.session_state.schedules:
    st.info("👈 왼쪽 사이드바에서 개강일과 수업 시간을 등록해 주세요.")
else:
    # 4-1. 중복 검사 수행 및 결과 표시
    conflicts = check_conflicts(st.session_state.schedules)
    
    st.subheader("🚨 중복 검사 결과")
    if conflicts:
        st.error(f"총 **{len(conflicts)}건**의 강의실 시간 중복이 감지되었습니다!")
        for c in conflicts:
            st.warning(
                f"**[중복 날짜: {c['date']}]**\n\n"
                f"- **{c['inst1']}** ({c['class1']}) : {c['time1']}\n"
                f"- **{c['inst2']}** ({c['class2']}) : {c['time2']}"
            )
    else:
        st.success("✅ 강의실 중복 일정이 없습니다! 모든 수업이 안전하게 배치되었습니다.")

    st.divider()

    # 4-2. 전체 등록 목록 보기 (테이블 변환)
    st.subheader("📋 전체 등록 수업 및 출석일 목록")
    
    display_data = []
    for idx, item in enumerate(st.session_state.schedules):
        dates_str = ", ".join([d.strftime("%Y-%m-%d") for d in item["dates"]])
        display_data.append({
            "번호": idx + 1,
            "기관": item["institution"],
            "수업명": item["class_name"],
            "개강일(수)": item["wed_date"].strftime("%Y-%m-%d"),
            "출석요일": item["weekend_day"],
            "시간대": f"{item['start_time'].strftime('%H:%M')} ~ {item['end_time'].strftime('%H:%M')}",
            "실습 출석일 (1주, 9주, 14주)": dates_str
        })
    
    df = pd.DataFrame(display_data)
    st.dataframe(df, use_container_width=True)

    # 목록 초기화 버튼
    if st.button("전체 일정 초기화"):
        st.session_state.schedules = []
        st.rerun()
