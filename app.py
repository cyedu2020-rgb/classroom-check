import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import sqlite3

# ---------------------------------------------------------
# 1. 페이지 및 SQLite 데이터베이스 설정
# ---------------------------------------------------------
st.set_page_config(page_title="강의실 중복 체크 시스템", page_icon="🏫", layout="wide")

st.title("🏫 사회복지현장실습 강의실 중복 체크 시스템")
st.caption("등록·수정·삭제한 모든 일정 데이터가 자동으로 저장되어 세션이 끊겨도 데이터가 유지됩니다.")

DB_FILE = "schedules.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            institution TEXT,
            class_name TEXT,
            wed_date TEXT,
            weekend_day TEXT,
            start_time TEXT,
            end_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

# DB 초기화 실행
init_db()

# ---------------------------------------------------------
# 2. 핵심 로직 함수
# ---------------------------------------------------------
def get_attendance_dates(wed_date, weekend_day):
    offset = 3 if weekend_day == '토' else 4
    first_weekend = wed_date + timedelta(days=offset)
    return {
        "1주차": first_weekend,
        "9주차": first_weekend + timedelta(weeks=8),
        "14주차": first_weekend + timedelta(weeks=13)
    }

def load_schedules_from_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, institution, class_name, wed_date, weekend_day, start_time, end_time FROM schedules")
    rows = c.fetchall()
    conn.close()

    schedules = []
    for r in rows:
        db_id, inst, c_name, w_date_str, w_day, s_time_str, e_time_str = r
        w_date = datetime.strptime(w_date_str, "%Y-%m-%d").date()
        s_time = datetime.strptime(s_time_str, "%H:%M").time()
        e_time = datetime.strptime(e_time_str, "%H:%M").time()

        schedules.append({
            "id": db_id,
            "institution": inst,
            "class_name": c_name,
            "wed_date": w_date,
            "weekend_day": w_day,
            "start_time": s_time,
            "end_time": e_time,
            "dates": get_attendance_dates(w_date, w_day)
        })
    return schedules

def add_schedule_to_db(inst, c_name, w_date, w_day, s_time, e_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO schedules (institution, class_name, wed_date, weekend_day, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (inst, c_name, w_date.strftime("%Y-%m-%d"), w_day, s_time.strftime("%H:%M"), e_time.strftime("%H:%M")))
    conn.commit()
    conn.close()

def update_schedule_in_db(db_id, inst, c_name, w_date, w_day, s_time, e_time):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE schedules
        SET institution=?, class_name=?, wed_date=?, weekend_day=?, start_time=?, end_time=?
        WHERE id=?
    ''', (inst, c_name, w_date.strftime("%Y-%m-%d"), w_day, s_time.strftime("%H:%M"), e_time.strftime("%H:%M"), db_id))
    conn.commit()
    conn.close()

def delete_schedule_from_db(db_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE id=?", (db_id,))
    conn.commit()
    conn.close()

def clear_all_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM schedules")
    conn.commit()
    conn.close()

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

# DB에서 최신 데이터 불러오기
st.session_state.schedules = load_schedules_from_db()

# ---------------------------------------------------------
# 3. 사이드바: 신규 수업 등록
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

if submit_button:
    if not class_name.strip():
        st.sidebar.error("수업 이름을 입력해 주세요.")
    elif wed_date.weekday() != 2:
        st.sidebar.error("❌ 선택한 날짜가 수요일이 아닙니다.")
    elif start_time >= end_time:
        st.sidebar.error("❌ 종료 시간은 시작 시간보다 뒤여야 합니다.")
    else:
        add_schedule_to_db(institution, class_name, wed_date, weekend_day, start_time, end_time)
        st.sidebar.success(f"[{institution}] '{class_name}' 일정이 저장되었습니다!")
        st.rerun()

# ---------------------------------------------------------
# 4. 메인 화면 Display 및 중복 체크
# ---------------------------------------------------------
if not st.session_state.schedules:
    st.info("👈 현재 등록된 일정이 없습니다. 사이드바에서 일정을 추가해 주세요.")
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

    # ---------------------------------------------------------
    # 5. 등록 일정 수정 및 삭제 구역
    # ---------------------------------------------------------
    st.divider()
    st.subheader("✏️ 등록 일정 수정 및 삭제")
    
    options = [f"{i+1}. [{s['institution']}] {s['class_name']}" for i, s in enumerate(st.session_state.schedules)]
    selected_option = st.selectbox("수정 또는 삭제할 수업을 선택하세요", options)
    
    selected_idx = int(selected_option.split(".")[0]) - 1
    target_schedule = st.session_state.schedules[selected_idx]

    with st.expander(f"📌 '{target_schedule['class_name']}' 상세 정보 수정", expanded=True):
        with st.form("edit_form"):
            edit_inst = st.selectbox("기관 선택", ["사이에듀", "마이에듀원격"], index=0 if target_schedule["institution"] == "사이에듀" else 1)
            edit_class_name = st.text_input("수업/분반 이름", value=target_schedule["class_name"])
            edit_wed_date = st.date_input("개강일 선택 (수요일)", value=target_schedule["wed_date"])
            edit_weekend_day = st.radio("출석 요일", ["토", "일"], index=0 if target_schedule["weekend_day"] == "토" else 1, horizontal=True)
            
            c1, c2 = st.columns(2)
            with c1:
                edit_start_time = st.time_input("시작 시간", value=target_schedule["start_time"])
            with c2:
                edit_end_time = st.time_input("종료 시간", value=target_schedule["end_time"])

            col_sub1, col_sub2 = st.columns([1, 1])
            with col_sub1:
                update_btn = st.form_submit_button("💾 수정사항 저장")
            with col_sub2:
                delete_btn = st.form_submit_button("🗑️ 해당 수업 삭제", type="primary")

        if update_btn:
            if not edit_class_name.strip():
                st.error("수업 이름을 입력해 주세요.")
            elif edit_wed_date.weekday() != 2:
                st.error("❌ 개강일은 수요일이어야 합니다.")
            elif edit_start_time >= edit_end_time:
                st.error("❌ 종료 시간은 시작 시간보다 뒤여야 합니다.")
            else:
                update_schedule_in_db(
                    target_schedule["id"],
                    edit_inst,
                    edit_class_name,
                    edit_wed_date,
                    edit_weekend_day,
                    edit_start_time,
                    edit_end_time
                )
                st.success("수정사항이 저장되었습니다!")
                st.rerun()

        if delete_btn:
            delete_schedule_from_db(target_schedule["id"])
            st.success("수업이 삭제되었습니다.")
            st.rerun()

    st.write("")
    if st.button("🚨 전체 일정 초기화"):
        clear_all_db()
        st.rerun()
