# Holidays-API

import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime

# --- API 키 로드 (Streamlit Secrets 사용) ---
try:
    # st.secrets에서 키를 불러옵니다.
    # 배포 시 Streamlit Cloud의 'Secrets'에 "CALENDARIFIC_API_KEY = '여러분의키'" 형식으로 저장해야 합니다.
    API_KEY = st.secrets["CALENDARIFIC_API_KEY"]
except (KeyError, FileNotFoundError):
    st.error("Streamlit Secrets에 'CALENDARIFIC_API_KEY'가 설정되지 않았습니다.")
    st.error("Streamlit Cloud의 Settings > Secrets에 API 키를 추가해주세요.")
    st.stop() # 키가 없으면 앱 실행 중지

# --- 상수 정의 ---
# Nominatim (OpenStreetMap) 리버스 지오코딩 API (위도/경도 -> 국가 코드)
REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"

# Calendarific API
CALENDARIFIC_API_URL = "https://calendarific.com/api/v2/holidays"

# --- 세션 상태 초기화 ---
if "center" not in st.session_state:
    st.session_state.center = [37.5665, 126.9780] # 기본 중심 (서울)
if "zoom" not in st.session_state:
    st.session_state.zoom = 4 # 기본 줌 레벨
if "clicked_location" not in st.session_state:
    st.session_state.clicked_location = None

# --- Streamlit 앱 UI ---
st.set_page_config(page_title="세계 공휴일 캘린더", layout="wide")
st.title("🗺️ 세계 공휴일 캘린더 (지도 클릭)")
st.markdown("지도에서 원하는 국가의 위치를 클릭하면 해당 국가의 올해 공휴일 정보를 보여줍니다.")

# --- 지도 표시 ---
# Folium 지도 객체 생성
m = folium.Map(location=st.session_state.center, zoom_start=st.session_state.zoom)

# 마지막으로 클릭한 위치에 마커 추가
if st.session_state.clicked_location:
    lat, lon = st.session_state.clicked_location
    folium.Marker(
        [lat, lon],
        popup="선택한 위치",
        tooltip="선택한 위치",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

# streamlit-folium을 사용해 지도 표시 및 클릭 이벤트 받기
map_data = st_folium(
    m,
    center=st.session_state.center,
    zoom=st.session_state.zoom,
    width="100%",
    height=400,
)

# --- 지도 클릭 이벤트 처리 ---
if map_data and map_data.get("last_clicked"):
    # 클릭한 위치의 위도/경도 가져오기
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    # 세션 상태 업데이트 (클릭 위치 저장 및 지도 중심 이동)
    st.session_state.clicked_location = [lat, lon]
    st.session_state.center = [lat, lon]
    st.session_state.zoom = 6 # 클릭 시 줌 레벨 변경

    # Nominatim API로 국가 코드 조회
    try:
        nominatim_params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "accept-language": "en" # 국가 코드를 영어(en)로 받기 위해
        }
        headers = {
            "User-Agent": "Streamlit Holiday App (user@example.com)" # Nominatim은 User-Agent 헤더가 필요합니다.
        }
        
        response = requests.get(REVERSE_GEOCODING_URL, params=nominatim_params, headers=headers)
        response.raise_for_status() # 오류 발생 시 예외 처리
        
        geo_data = response.json()
        
        if "address" in geo_data and "country_code" in geo_data["address"]:
            country_code = geo_data["address"]["country_code"].upper()
            country_name = geo_data["address"].get("country", country_code)
            
            st.session_state.country_code = country_code
            st.session_state.country_name = country_name
            
            # 클릭 이벤트 처리 후 앱을 다시 실행하여 지도에 마커를 즉시 표시
            st.rerun()

        else:
            st.warning("선택한 위치의 국가 정보를 찾을 수 없습니다. 다른 위치를 클릭해 주세요.")
            st.session_state.country_code = None
            st.session_state.country_name = None

    except requests.exceptions.RequestException as e:
        st.error(f"국가 정보 조회 중 오류가 발생했습니다: {e}")
        st.session_state.country_code = None
        st.session_state.country_name = None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생 (국가 조회): {e}")
        st.session_state.country_code = None
        st.session_state.country_name = None


# --- 공휴일 정보 표시 ---
if st.session_state.get("country_code"):
    country_code = st.session_state.country_code
    country_name = st.session_state.country_name
    current_year = datetime.now().year

    st.subheader(f"📅 {country_name} ({country_code})의 {current_year}년 공휴일")

    try:
        # Calendarific API 호출
        calendarific_params = {
            "api_key": API_KEY,
            "country": country_code,
            "year": current_year
        }
        
        response = requests.get(CALENDARIFIC_API_URL, params=calendarific_params)
        response.raise_for_status() # 오류 발생 시 예외 처리
        
        holiday_data = response.json()

        if "response" in holiday_data and "holidays" in holiday_data["response"]:
            holidays = holiday_data["response"]["holidays"]
            
            if holidays:
                # pandas DataFrame으로 변환
                df = pd.DataFrame(holidays)
                
                # 날짜(date)에서 iso 형식만 추출
                df['날짜'] = df['date'].apply(lambda x: x['iso'])
                
                # 필요한 열만 선택
                df_display = df[['날짜', 'name', 'description']]
                df_display.columns = ['날짜', '공휴일 이름', '설명']
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            else:
                st.info(f"{country_name} 국가의 공휴일 정보를 찾을 수 없습니다.")

        else:
            st.error("API 응답 형식이 올바르지 않습니다.")
            st.json(holiday_data) # 디버깅을 위해 전체 응답 출력

    except requests.exceptions.RequestException as e:
        st.error(f"Calendarific API 호출 중 오류가 발생했습니다: {e}")
        # 오류 응답이 JSON 형식일 경우, 상세 메시지 표시
        try:
            error_json = response.json()
            if "response" in error_json and "error" in error_json["response"]:
                st.error(f"API 서버 메시지: {error_json['response']['error']}")
        except Exception:
            pass # JSON 파싱 실패 시 무시

    except Exception as e:
        st.error(f"알 수 없는 오류 발생 (공휴일 조회): {e}")

else:
    st.info("지도를 클릭하여 공휴일을 확인할 국가를 선택해 주세요.")

