import streamlit as st

# 1. 페이지 기본 설정 (전체 화면을 넓게 쓰기 위해 wide 모드 적용)
st.set_page_config(
    page_title="태양광 발전용량 & 여유용량 조회 시스템",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 대시보드 타이틀
st.title("☀️ 태양광 발전부지 1차 분석 대시보드")
st.caption("주소 입력 한 번으로 한전 연계용량과 지붕 면적당 발전용량을 동시 분석합니다.")
st.markdown("---")

# 3. 상단 주소 입력창
address = st.text_input(
    "🔍 분석할 지번 주소를 입력하세요", 
    placeholder="예: 대구광역시 북구 산격동 ... 또는 이미지 속 주소 입력"
)

# 4. 주소가 입력되었을 때 실행할 로직
if address:
    # 화면을 정확히 1:1 비율로 좌우 분할
    col1, col2 = st.columns(2)

    # ----------------------------------------------------------------
    # [좌측 패널] 한전ON 연계 여유용량 정보
    # ----------------------------------------------------------------
    with col1:
        st.subheader("📋 한전ON 연계 여유용량 현황")
        st.markdown("---")
        
        # 실시간 크롤링 연동 전, UI 확인을 위한 데모 데이터 구조
        st.markdown(f"**📍 조회 주소:** `{address}`")
        
        # 가독성을 높이기 위한 대형 메트릭 배치
        m1, m2, m3 = st.columns(3)
        m1.metric(label="변전소 여유용량", value="연계 가능", delta="정상")
        m2.metric(label="주변압기 여유용량", value="여유 있음", delta="정상")
        # 부족한 상황을 직관적으로 보여주기 위한 예시
        m3.metric(label="배전선로 여유용량", value="용량 부족", delta="-120 kW", delta_color="inverse")
        
        # 경고 및 안내 문구
        st.error("⚠️ 현재 배전선로 용량이 부족한 것으로 1차 조회되었습니다. 한전 지사 추가 확인이 필요합니다.")
        
        st.markdown("#### 🔍 한전 데이터 상세")
        st.text_area(
            label="한전ON 시스템 원문 매핑 데이터 (예시)",
            value="[상세 정보]\n- 관할지사: 대구본부 직할\n- 공급변전소: 산격변전소\n- D/L명: 대학선\n- 연계가능용량: 0 kW (공사 필요)",
            height=120,
            disabled=True
        )
        
        # 한전ON 다이렉트 링크 버튼 (크롤링 에러 시 백업용)
        st.link_button("🌐 한전ON 여유용량 조회 페이지 바로가기", "https://online.kepco.co.kr/EWM092D00")

    # ----------------------------------------------------------------
    # [우측 패널] 지붕 면적 및 발전용량 계산 (+ 지도 플레이스홀더)
    # ----------------------------------------------------------------
    with col2:
        st.subheader("📐 지붕 면적 및 예상 발전용량")
        st.markdown("---")
        
        # 면적 입력 (기본값은 제공해주신 예시 값인 269.04로 설정)
        building_area = st.number_input(
            "건물 면적 입력 (㎡)", 
            min_value=0.0, 
            value=269.04, 
            step=1.0,
            help="정확한 분석을 위해 건축물대장 상의 면적 또는 지도 측정 면적을 입력하세요."
        )
        
        # 💡 제공해주신 공식 적용: 총면적 / 3.3 / 2 = 예상발전용량
        pyeong = building_area / 3.3
        estimated_kw = pyeong / 2
        
        # 계산 결과 출력
        st.markdown("#### 📊 자동 계산 결과")
        res1, res2 = st.columns(2)
        res1.metric(label="환산 평수", value=f"{pyeong:.2f} 평")
        res2.metric(label="예상 발전용량", value=f"{estimated_kw:.2f} kW")
        
        st.markdown("---")
        st.markdown("#### 🗺️ 현장 위성지도 (스카이뷰)")
        
        # 실제 개발 시에는 카카오/네이버 지도 API JavaScript 코드가 들어갈 영역입니다.
        # 프로토타입 단계에서는 시각적 이해를 돕기 위한 플레이스홀더를 띄웁니다.
        st.info("💡 카카오 지도 API 연동 시, 주소 입력과 동시에 해당 위치의 위성지도가 자동으로 표출됩니다.")
        st.image(
            "https://images.unsplash.com/photo-1524661135-423995f22d0b?auto=format&fit=crop&w=800&q=80", 
            caption="[참고 이미지] 실제 배포 시에는 주소 기반의 네이버/카카오 위성지도가 렌더링됩니다.",
            use_container_width=True
        )

else:
    # 주소를 입력하기 전 첫 화면 안내
    st.info(" 상단 입력창에 분석하고자 하는 지번 주소를 입력하시면 즉시 분석 화면이 전개됩니다.")
