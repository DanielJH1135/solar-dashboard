import streamlit as st
import requests
import xml.etree.ElementTree as ET

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

# 2. 메인 타이틀
st.title("☀️ 태양광 발전부지 1차 분석 대시보드")
st.caption("주소 입력 한 번으로 한전 연계용량과 건축물대장 기반 발전용량을 동시 분석합니다.")
st.markdown("---")

# 3. 상단 주소 입력창
address = st.text_input(
    "🔍 분석할 지번 또는 도로명 주소를 입력하세요", 
    placeholder="예: 대구 수성구 범어동1"
)

# --- 헬퍼 함수: 건축물대장 면적 조회 ---
def get_building_data(addr, kakao_key):
    if not kakao_key:
        return None, "카카오 REST API 키 설정이 누락되었습니다."
    
    headers = {"Authorization": f"KakaoAK {kakao_key}"}
    kakao_url = "https://dapi.kakao.com/v2/local/search/address.json"
    
    try:
        res = requests.get(kakao_url, headers=headers, params={"query": addr}, timeout=5)
        
        if res.status_code != 200:
            return None, f"카카오 API 서버 인증 실패 (코드 {res.status_code}): {res.text}"
            
        res_data = res.json()
        documents = res_data.get('documents', [])
        
        if not documents:
            return None, f"카카오 결과 없음: 입력하신 주소('{addr}')를 인식하지 못했습니다. 주소를 다시 확인해주세요."
        
        document = documents[0]
        addr_info = document.get('address') or document.get('road_address')
        
        b_code = addr_info.get('b_code') if addr_info else None
        if not b_code and document.get('address'):
            b_code = document['address'].get('b_code')
            
        if not b_code:
            return None, "해당 주소에서 법정동코드(b_code)를 추출할 수 없습니다."
            
        sigungu_cd = b_code[:5]
        bjdong_cd = b_code[5:]
        
        main_no = document['address'].get('main_address_no', '') if document.get('address') else addr_info.get('main_address_no', '')
        sub_no = document['address'].get('sub_address_no', '') if document.get('address') else addr_info.get('sub_address_no', '')
            
        if not main_no:
            return None, "건축물대장 조회를 위한 지번(본번) 정보가 부족합니다."
            
        bun = main_no.zfill(4)
        ji = sub_no.zfill(4) if sub_no else '0000'
        
        bld_url = "https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
        params = {
            'serviceKey': requests.utils.unquote(DATA_GO_KR_KEY),
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'numOfRows': '1',
            'pageNo': '1'
        }
        
        bld_res = requests.get(bld_url, params=params, timeout=10)
        
        if bld_res.status_code != 200:
            return None, f"정부 서버 연결 실패 (상태 코드 {bld_res.status_code}): {bld_res.text[:100]}"
        
        try:
            root = ET.fromstring(bld_res.text)
        except ET.ParseError:
            return None, "정부 서버 응답 데이터 해석 실패(XML 형식 오류)"
        
        result_code = root.find('.//resultCode')
        if result_code is not None and result_code.text != '00':
            result_msg = root.find('.//resultMsg')
            return None, f"건축HUB 시스템 오류: {result_msg.text if result_msg is not None else '인증키 에러'}"
        
        plat_area_elem = root.find('.//platArea')
        arch_area_elem = root.find('.//archArea')
        
        plat_area = float(plat_area_elem.text) if (plat_area_elem is not None and plat_area_elem.text) else 0.0
        arch_area = float(arch_area_elem.text) if (arch_area_elem is not None and arch_area_elem.text) else 0.0
        
        return {"plat_area": plat_area, "arch_area": arch_area}, None
        
    except Exception as e:
        return None, f"시스템 연동 중 오류 발생: {str(e)}"

# 4. 메인 로직 작동
if address:
    col1, col2 = st.columns(2)

    # ----------------------------------------------------------------
    # [좌측 패널] 한전ON 연계 여유용량 정보
    # ----------------------------------------------------------------
    with col1:
        st.subheader("📋 한전ON 연계 여유용량 현황")
        st.markdown("---")
        st.markdown(f"**📍 조회 주소:** `{address}`")
        
        m1, m2, m3 = st.columns(3)
        m1.metric(label="변전소 여유용량", value="연계 가능", delta="정상")
        m2.metric(label="주변압기 여유용량", value="여유 있음", delta="정상")
        m3.metric(label="배전선로 여유용량", value="용량 부족", delta="-120 kW", delta_color="inverse")
        
        st.error("⚠️ 현재 배전선로 용량이 부족한 것으로 1차 조회되었습니다. 한전 지사 추가 확인이 필요합니다.")
        
        st.markdown("#### 🔍 한전 데이터 상세")
        st.text_area(
            label="한전ON 시스템 원문 매핑 데이터 (크롤러 연동 대기중)",
            value="[상세 정보]\n- 관할지사: 대구본부 직할\n- 공급변전소: 산격변전소\n- D/L명: 대학선\n- 연계가능용량: 0 kW (공사 필요)",
            height=100,
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
        
        plat_val = 0.0
        arch_val = 0.0
        
        if api_data:
            st.success(f"🎉 건축물대장 데이터 연동 성공!")
            plat_val = api_data["plat_area"]
            arch_val = api_data["arch_area"]
        else:
            st.warning(error_msg)
            
        st.markdown(f"**🏢 대장 정보 현황:** 대지면적 `{plat_val:,} ㎡` | 건축면적 `{arch_val:,} ㎡`")
        
        mode = st.radio(
            "💡 어떤 면적을 기준으로 발전용량을 계산할까요?",
            ["🏠 지붕/옥상 기준 (건축면적 사용)", "🌳 마당/나대지 기준 (대지면적 사용)"],
            horizontal=True
        )
        
        if "지붕/옥상" in mode:
            selected_area = arch_val if arch_val > 0 else 269.04
        else:
            selected_area = plat_val if plat_val > 0 else 500.0
            
        building_area = st.number_input(
            "선택된 면적 수정 가능 (㎡)", 
            min_value=0.0, 
            value=selected_area, 
            step=1.0
        )
        
        pyeong = building_area / 3.3
        estimated_kw = pyeong / 2
        
        st.markdown("#### 📊 자동 계산 결과")
        res1, res2 = st.columns(2)
        res1.metric(label="환산 평수", value=f"{pyeong:.2f} 평")
        res2.metric(label="예상 발전용량", value=f"{estimated_kw:.2f} kW")
        
        st.markdown("---")
        st.markdown("#### 🗺️ 현장 위성지도 (카카오 스카이뷰)")
        
        # 💡 [치트키 추가] 주소 기반 카카오맵 스카이뷰 직행 버튼 레이아웃 배치
        st.link_button(
            "🗺️ 카카오맵 위성지도 새창으로 크게 열기", 
            f"https://map.kakao.com/?q={address}",
            type="primary",
            use_container_width=True
        )
        
        # 임베딩용 맵 구조 (보안망에 의해 막히더라도 상단 버튼이 작동하므로 안전합니다)
        kakao_map_html = f"""
        <div id="map" style="width:100%;height:360px;border-radius:8px;background-color:#eee; display:flex; align-items:center; justify-content:center; color:#666; font-size:13px;">
            브라우저 보안으로 내장 지도가 안 보일 경우 위 [새창으로 크게 열기] 버튼을 이용하세요.
        </div>
        <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_js_key}&libraries=services&autoload=false"></script>
        <script>
            kakao.maps.load(function() {{
                var mapContainer = document.getElementById('map');
                mapContainer.innerText = ""; // 대기 문구 제거
                
                var mapOption = {{
                    center: new kakao.maps.LatLng(36.3504119, 127.3845475),
                    level: 3
                }};  
                var map = new kakao.maps.Map(mapContainer, mapOption); 
                map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
                
                var geocoder = new kakao.maps.services.Geocoder();
                geocoder.addressSearch('{address}', function(result, status) {{
                    if (status === kakao.maps.services.Status.OK) {{
                        var coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                        var marker = new kakao.maps.Marker({{
                            map: map,
                            position: coords
                        }});
                        map.setCenter(coords);
                    }}
                }});
            }});
        </script>
        """
        import streamlit.components.v1 as components
        components.html(kakao_map_html, height=370)

else:
    st.info(" 상단 입력창에 분석하고자 하는 지번 주소를 입력하시면 즉시 분석 화면이 전개됩니다.")
