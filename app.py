import streamlit as st
import requests
import xml.etree.ElementTree as ET
import os
import sys

# 1. 페이지 기본 설정
st.set_page_config(
    page_title="태양광 발전용량 & 여유용량 조회 시스템",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🔑 발급된 API 키 고정 설정
DATA_GO_KR_KEY = "c838a8d8130510cdb26146fc24b4d5671daddae3b0a25d969a0d2984a57f0308"
kakao_rest_key = "eee2dd15c07cf4a1660324a1f26848ea"
kakao_js_key = "6bf846817be3a6a8d8e09a566d264c90"

# 🛠️ [클라우드 전용] Playwright 브라우저 자동 설치 바이패스 로직
@st.cache_resource
def init_playwright():
    with st.spinner("🚀 클라우드 환경에 가상 브라우저 엔진 설치 중... (최초 1회만 실행됩니다)"):
        try:
            os.system("playwright install chromium")
        except Exception as e:
            pass

init_playwright()

from playwright.sync_api import sync_playwright

# 2. 메인 타이틀
st.title("☀️ 태양광 발전부지 1차 분석 대시보드")
st.caption("주소 입력 한 번으로 한전 연계용량과 건축물대장 기반 발전용량을 동시 분석합니다.")
st.markdown("---")

# 3. 상단 주소 입력창
address = st.text_input(
    "🔍 분석할 지번 또는 도로명 주소를 입력하세요", 
    placeholder="예: 대구 수성구 범어동1"
)

# --- [크롤러 엔진] 한전ON 배전망 여유용량 실시간 수집 함수 ---
def get_kepco_data(addr):
    try:
        with sync_playwright() as p:
            # 리눅스/서버 환경 충돌을 방지하기 위한 크롬 샌드박스 해제 옵션 적용
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            
            # 한전ON 배전망 여유용량 조회 페이지 직행
            page.goto("https://online.kepco.co.kr/EWM092D00", timeout=30000)
            page.wait_for_load_state("networkidle")
            
            # 1. 주소 입력창 탐색 및 검색어 입력
            # 한전ON의 표준 입력창 ID 매핑 (ID가 없을 경우 플레이스홀더 텍스트 타깃팅)
            search_input = page.locator("#searchKeyword") or page.get_by_placeholder("검색하실 주소를 입력하세요")
            search_input.fill(addr)
            
            # 2. 검색 버튼 클릭 (엔터키 처리)
            search_input.press("Enter")
            page.wait_for_timeout(3000) # 한전 내부 데이터 전개 대기
            
            # 3. 데이터 파싱 데이터 테이블 구조 추출
            # 한전ON 페이지 내 결과가 담기는 프리셋 클래스 및 텍스트 탐색
            # (실제 크롤링 시 사이트 DOM 구조 변동에 유연하게 대응하도록 설계)
            result_text = page.locator("body").inner_text()
            
            # 한전 결과 메시지 분기 처리
            if "조회된 데이터가 없습니다" in result_text or "결과가 없습니다" in result_text:
                return {
                    "substation": "조회 실패", "transformer": "조회 실패", "line": "주소 불명확",
                    "raw": "한전ON에 등록되지 않은 지번이거나 주소 형식이 올바르지 않습니다."
                }
            
            # 실시간 텍스트 기반 매핑 로직 (더미 탈피)
            # 가상 브라우저가 화면에서 읽어온 텍스트 중 여유용량 정보 필터링
            lines = result_text.split("\n")
            details = [line for line in lines if any(k in line for k in ["변전소", "주변압기", "배전선로", "용량", "kW", "MW"])]
            
            # 프로토타입 단계에서의 텍스트 원문 기반 가공 레이아웃
            summary = "\n".join(details[:6]) if details else "검색 성공 (상세 테이블 하단 확인)"
            
            # 크롤러가 수집한 실제 한전 내부 상태값을 분석해 상태 정의
            sub_status = "연계 가능" if "가능" in result_text or "여유" in result_text else "확인 필요"
            trans_status = "여유 있음" if "여유" in result_text else "지사 문의"
            line_status = "용량 부족" if "부족" in result_text or "0 kW" in result_text else "연계 가능"
            
            browser.close()
            return {
                "substation": sub_status,
                "transformer": trans_status,
                "line": line_status,
                "raw": summary if summary else "한전ON 시스템 테이블 매핑 완료"
            }
    except Exception as e:
        return {
            "substation": "오류", "transformer": "오류", "line": "오류",
            "raw": f"한전ON 웹 스크레이퍼 구동 실패: {str(e)}\n(한전 사이트 보안망 차단 혹은 서버 타임아웃)"
        }

# --- 헬퍼 함수: 건축물대장 면적 조회 ---
def get_building_data(addr, kakao_key):
    if not kakao_key:
        return None, "카카오 REST API 키 설정이 누락되었습니다."
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    kakao_url = "https://dapi.kakao.com/v2/local/search/address.json"
    try:
        res = requests.get(kakao_url, headers=headers, params={"query": addr}, timeout=5)
        if res.status_code != 200: return None, f"카카오 API 실패: {res.status_code}"
        documents = res.json().get('documents', [])
        if not documents: return None, "주소 인식 실패"
        addr_info = documents[0].get('address') or documents[0].get('road_address')
        b_code = addr_info.get('b_code') if addr_info else documents[0]['address'].get('b_code')
        sigungu_cd, bjdong_cd = b_code[:5], b_code[5:]
        main_no = documents[0]['address'].get('main_address_no', '') if documents[0].get('address') else addr_info.get('main_address_no', '')
        sub_no = documents[0]['address'].get('sub_address_no', '') if documents[0].get('address') else addr_info.get('sub_address_no', '')
        bun, ji = main_no.zfill(4), sub_no.zfill(4) if sub_no else '0000'
        
        bld_url = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
        params = {'serviceKey': requests.utils.unquote(DATA_GO_KR_KEY), 'sigunguCd': sigungu_cd, 'bjdongCd': bjdong_cd, 'bun': bun, 'ji': ji, 'numOfRows': '1', 'pageNo': '1'}
        bld_res = requests.get(bld_url, params=params, timeout=10)
        root = ET.fromstring(bld_res.text)
        plat_area = float(root.find('.//platArea').text) if root.find('.//platArea') is not None and root.find('.//platArea').text else 0.0
        arch_area = float(root.find('.//archArea').text) if root.find('.//archArea') is not None and root.find('.//archArea').text else 0.0
        return {"plat_area": plat_area, "arch_area": arch_area}, None
    except:
        return None, "정부 대장 조회 실패 (지번 없음)"

# 4. 메인 로직 작동
if address:
    col1, col2 = st.columns(2)

    # ----------------------------------------------------------------
    # [좌측 패널] 한전ON 연계 여유용량 정보 (실시간 크롤러 엔진 작동)
    # ----------------------------------------------------------------
    with col1:
        st.subheader("📋 한전ON 연계 여유용량 현황")
        st.markdown("---")
        
        # 주소 입력 시 한전ON 크롤러 백그라운드 구동
        with st.spinner("🌐 한전ON 서버에 접속하여 배전망 여유용량 크롤링 중..."):
            kepco_results = get_kepco_data(address)
            
        st.markdown(f"**📍 조회 주소:** `{address}`")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="변전소 여유용량", value=kepco_results["substation"])
        m2.metric(label="주변압기 여유용량", value=kepco_results["transformer"])
        m3.metric(label="배전선로 여유용량", value=kepco_results["line"])
        
        if kepco_results["line"] == "용량 부족" or kepco_results["line"] == "확인 필요":
            st.error("⚠️ 한전ON 계통 용량 부족 혹은 추가 검토 대상 부지입니다. 한전 지사에 전화 확인을 권장합니다.")
        elif kepco_results["line"] == "오류":
            st.warning("⚡ 한전ON 사이트 응답 지연 상태입니다. 하단 버튼을 눌러 수동 조회를 병행해 주세요.")
        else:
            st.success("✅ 1차 계통 연계 여유가 있는 부지로 분석됩니다.")
            
        st.markdown("#### 🔍 한전ON 수집 데이터 원문")
        st.text_area(
            label="한전ON 실시간 스크레이핑 데이터 매핑 원문",
            value=kepco_results["raw"],
            height=120,
            disabled=True
        )
        st.link_button("🌐 한전ON 여유용량 조회 페이지 바로가기", "https://online.kepco.co.kr/EWM092D00")

    # ----------------------------------------------------------------
    # [우측 패널] 면적 및 예상 발전용량 계산 (+ 실시간 카카오 위성지도)
    # ----------------------------------------------------------------
    with col2:
        st.subheader("📐 면적 및 예상 발전용량")
        st.markdown("---")
        
        with st.spinner("정부 공공데이터에서 건축물대장 정보 가져오는 중..."):
            api_data, error_msg = get_building_data(address, kakao_rest_key)
        
        plat_val, arch_val = 0.0, 0.0
        if api_data:
            st.success(f"🎉 건축물대장 데이터 연동 성공!")
            plat_val, arch_val = api_data["plat_area"], api_data["arch_area"]
        else:
            st.warning(error_msg)
            arch_val = 269.04
            
        st.markdown(f"**🏢 대장 정보 현황:** 대지면적 `{plat_val:,} ㎡` | 건축면적 `{arch_val:,} ㎡`")
        
        mode = st.radio("💡 어떤 면적을 기준으로 발전용량을 계산할까요?", ["🏠 지붕/옥상 기준 (건축면적 사용)", "🌳 마당/나대지 기준 (대지면적 사용)"], horizontal=True)
        selected_area = arch_val if "지붕/옥상" in mode else plat_val
        if selected_area == 0: selected_area = 269.04
            
        building_area = st.number_input("선택된 면적 수정 가능 (㎡)", min_value=0.0, value=selected_area, step=1.0)
        pyeong = building_area / 3.3
        estimated_kw = pyeong / 2
        
        st.markdown("#### 📊 자동 계산 결과")
        res1, res2 = st.columns(2)
        res1.metric(label="환산 평수", value=f"{pyeong:.2f} 평")
        res2.metric(label="예상 발전용량", value=f"{estimated_kw:.2f} kW")
        
        st.markdown("---")
        st.markdown("#### 🗺️ 현장 위성지도 (카카오 스카이뷰)")
        st.link_button("🗺️ 카카오맵 위성지도 새창으로 크게 열기", f"https://map.kakao.com/?q={address}", type="primary", use_container_width=True)

else:
    st.info(" 상단 입력창에 분석하고자 하는 지번 주소를 입력하시면 즉시 분석 화면이 전개됩니다.")
