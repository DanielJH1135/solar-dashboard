# -*- coding: utf-8 -*-
import os
from flask import Flask, request, jsonify, render_template_string
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY")
KAKAO_REST_KEY = os.getenv("KAKAO_REST_KEY")
KAKAO_JS_KEY = os.getenv("KAKAO_JS_KEY")
VWORLD_API_KEY = os.getenv("VWORLD_API_KEY")
VWORLD_DOMAIN = os.getenv("VWORLD_DOMAIN", "solar-dashboard-daegu.vercel.app")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>대구지사 태양광 부지 분석 플랫폼</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { background-color: #0B0F19; font-family: 'Pretendard', sans-serif; color: #E5E7EB; }
        details > summary { list-style: none; }
        details > summary::-webkit-details-marker { display: none; }
        .map-container { min-height: 500px; height: 100%; border-radius: 1rem; }
    </style>
</head>
<body class="p-4 md:p-6 max-w-7xl mx-auto">

    <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6 border-b border-gray-800 pb-5">
        <div>
            <h1 class="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
                <i class="fa-solid fa-solar-panel text-emerald-400"></i> 대구지사 태양광 종합 관제 시스템
            </h1>
            <p class="text-xs md:text-sm text-gray-400 mt-1">면적 데이터 예외처리 방어 및 API 통합 마스터 버전</p>
        </div>
    </header>

    <div class="bg-gray-900 border border-gray-800 p-4 rounded-2xl mb-6 flex flex-col sm:flex-row gap-3 items-stretch shadow-xl">
        <div class="relative flex-grow">
            <i class="fa-solid fa-location-dot absolute left-4 top-3.5 text-gray-500"></i>
            <input type="text" id="addressInput" value="대구광역시 수성구 범어동 1" 
                   class="w-full bg-gray-950 border border-gray-800 rounded-xl pl-11 pr-4 py-3 text-white font-medium focus:outline-none focus:border-emerald-500 transition-all text-sm md:text-base"
                   placeholder="상호명, 도로명, 지번 주소를 자유롭게 입력하세요">
        </div>
        <button onclick="startAnalysis()" class="bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold px-6 py-3 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer text-sm md:text-base whitespace-nowrap">
            <i class="fa-solid fa-magnifying-glass-chart"></i> 부지 분석 조회
        </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <div class="lg:col-span-5 flex flex-col gap-4">
            
            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                <h3 class="text-xs font-bold text-blue-400 mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-map-location-dot"></i> 토지 지적 & 특성 정보
                </h3>
                <div class="bg-gray-950 p-3 rounded-xl border border-gray-850 mb-3 text-center">
                    <span class="text-[11px] text-gray-500 block mb-1">PNU 고유번호</span>
                    <span id="vwPnu" class="text-sm font-mono text-gray-300">-</span>
                </div>
                <div class="grid grid-cols-2 gap-3 text-center mb-3">
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">법정 지목</span>
                        <span id="vwJimok" class="text-base font-black text-amber-400">-</span>
                    </div>
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">토지 대장 면적</span>
                        <span id="vwArea" class="text-base font-bold text-white">0.00</span> <span class="text-[11px] text-gray-400">㎡</span>
                    </div>
                </div>
                <div class="bg-gray-950 p-3 rounded-xl border border-gray-850 flex justify-between items-center">
                    <span class="text-[11px] text-gray-500 block">개별 공시지가 (㎡당)</span>
                    <div><span id="vwJiga" class="text-sm font-bold text-white">0</span> <span class="text-[11px] text-gray-400">원</span></div>
                </div>
            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                <h3 class="text-xs font-bold text-emerald-400 mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-building"></i> 국토부 건축물대장 정보
                </h3>
                <div class="grid grid-cols-2 gap-3 text-center">
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">건축 면적</span>
                        <span id="bdArchArea" class="text-base font-bold text-white">0.00</span> <span class="text-[11px] text-gray-400">㎡</span>
                    </div>
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">연면적</span>
                        <span id="bdTotArea" class="text-base font-bold text-white">0.00</span> <span class="text-[11px] text-gray-400">㎡</span>
                    </div>
                </div>
            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 shadow-md text-center">
                <a href="https://online.kepco.co.kr/EWM092D00" target="_blank" class="block w-full bg-gray-950 hover:bg-gray-850 border border-gray-800 text-gray-300 text-xs py-2.5 rounded-xl font-medium transition-all">
                    🌐 한전ON 공식 실시간 여유 선로 용량 조회하기
                </a>
            </div>

            <details class="bg-gray-900 border border-gray-800 rounded-2xl shadow-xl group" open>
                <summary class="p-5 cursor-pointer flex justify-between items-center text-amber-400 font-bold text-sm select-none border-b border-gray-800/0 group-open:border-gray-800 transition-colors">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-calculator"></i> 간편 견적 시뮬레이터 (3평=1kW)
                    </div>
                    <i class="fa-solid fa-chevron-down transition-transform duration-300 group-open:rotate-180 text-gray-500"></i>
                </summary>
                
                <div class="p-5 flex flex-col gap-4">
                    <div class="flex gap-2">
                        <label class="flex-1 bg-gray-950 border border-gray-800 p-2 rounded-lg flex items-center justify-center gap-2 cursor-pointer hover:border-gray-700">
                            <input type="radio" name="calcMode" value="land" checked onchange="switchMode('land')" class="accent-blue-500">
                            <span class="text-xs text-gray-300">토지 기준 (나대지)</span>
                        </label>
                        <label class="flex-1 bg-gray-950 border border-gray-800 p-2 rounded-lg flex items-center justify-center gap-2 cursor-pointer hover:border-gray-700">
                            <input type="radio" name="calcMode" value="roof" onchange="switchMode('roof')" class="accent-emerald-400">
                            <span class="text-xs text-gray-300">건축물 기준 (지붕)</span>
                        </label>
                    </div>
                    
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850 flex items-center justify-between">
                        <span class="text-xs text-gray-500" id="inputLabel">가용 실측 면적 (㎡)</span>
                        <input type="number" id="customArea" oninput="calculateValues()" class="w-32 bg-gray-900 border border-gray-700 rounded px-3 py-1 text-white font-bold focus:outline-none text-right">
                    </div>

                    <div class="bg-gray-950 p-4 rounded-xl border border-gray-850 text-center flex flex-col justify-center">
                        <span class="text-[11px] text-gray-500 block mb-1">예상 설치 용량</span>
                        <div><span id="estKw" class="text-3xl font-black text-emerald-400">0.00</span> <span class="text-sm text-gray-400 font-bold">kW</span></div>
                        <div class="text-[10px] text-gray-500 mt-2">환산 평수: <span id="resPyeong">0.00</span> 평</div>
                    </div>

                    <div class="bg-gradient-to-b from-emerald-950/20 to-transparent border-2 border-emerald-500/40 rounded-xl p-4 relative">
                        <div class="absolute top-0 right-0 bg-emerald-500 text-gray-950 font-black text-[10px] px-2.5 py-1 rounded-bl-xl">자가 소유</div>
                        <h3 class="text-white font-bold text-sm mb-3 flex items-center gap-2">
                            <i class="fa-solid fa-coins text-emerald-400"></i> [1안] RPS 투자형
                        </h3>
                        
                        <div class="mb-4 bg-gray-950 p-2.5 rounded-lg border border-amber-900/30">
                            <label class="text-[10px] text-amber-400 font-semibold block mb-1">kW당 공사 단가 커스텀 (원)</label>
                            <input type="number" id="kwCostInput" value="800000" step="10000" oninput="calculateValues()" class="w-full bg-gray-900 border border-gray-800 rounded px-2 py-1 text-white font-bold text-xs focus:outline-none focus:border-amber-500">
                        </div>

                        <div class="flex flex-col gap-2">
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">총 공사비</span>
                                <span class="font-bold text-white"><span id="ownerInvest">0</span> 만원</span>
                            </div>
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">월평균 순수익</span>
                                <span class="font-bold text-emerald-400"><span id="ownerMonthlyProfit">0</span> 원</span>
                            </div>
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">단순 회수 기간</span>
                                <span id="paybackLabel" class="font-bold text-emerald-300">연산중</span>
                            </div>
                        </div>
                    </div>

                    <div class="bg-gradient-to-b from-blue-950/20 to-transparent border-2 border-blue-500/40 rounded-xl p-4 relative">
                        <div class="absolute top-0 right-0 bg-blue-500 text-white font-black text-[10px] px-2.5 py-1 rounded-bl-xl">리스크 제로</div>
                        <h3 class="text-white font-bold text-sm mb-3 flex items-center gap-2">
                            <i class="fa-solid fa-building-user text-blue-400"></i> [2안] 지붕임대(50kW이상)
                        </h3>
                        <div class="flex flex-col gap-2">
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">초기 투자비용</span>
                                <span class="font-bold text-blue-400">0원</span>
                            </div>
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">월 수령 임대료(단순/12)</span>
                                <span class="font-bold text-white"><span id="rentMonthly">0</span> 원</span>
                            </div>
                            <div class="flex justify-between items-center bg-gray-950 p-2 rounded border border-gray-850 text-xs">
                                <span class="text-gray-500">연 수령 임대료(예상)</span>
                                <span class="font-bold text-white"><span id="rentAnnual">0</span> 원</span>
                            </div>
                        </div>
                    </div>
                </div>
            </details>
        </div>

        <div class="lg:col-span-7 bg-gray-900 border border-gray-800 rounded-2xl p-2 shadow-xl flex flex-col min-h-[500px]">
            <div id="map" class="w-full map-container relative">
                <div id="loadingMsg" class="absolute inset-0 bg-gray-900/80 z-10 flex items-center justify-center hidden rounded-xl">
                    <div class="text-emerald-400 font-bold flex flex-col items-center">
                        <i class="fa-solid fa-spinner fa-spin text-3xl mb-2"></i>
                        <span>데이터 수집 및 분석 중...</span>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=""" + (KAKAO_JS_KEY if KAKAO_JS_KEY else "") + """&libraries=services"></script>
    <script>
        let map, marker, ps, geocoder;
        let rawLandArea = 0;
        let rawArchArea = 0;

        document.addEventListener("DOMContentLoaded", function() {
            const mapContainer = document.getElementById('map');
            const defaultPos = new kakao.maps.LatLng(35.8596, 128.6254); 
            
            map = new kakao.maps.Map(mapContainer, { center: defaultPos, level: 2 });
            map.setMapTypeId(kakao.maps.MapTypeId.HYBRID); 
            
            ps = new kakao.maps.services.Places(); 
            geocoder = new kakao.maps.services.Geocoder();
            marker = new kakao.maps.Marker({ map: map, position: defaultPos });
            
            startAnalysis();
        });

        function switchMode(mode) {
            let areaInput = document.getElementById('customArea');
            if (mode === 'land') {
                let netYardArea = rawLandArea - rawArchArea;
                areaInput.value = netYardArea > 0 ? netYardArea.toFixed(2) : (rawLandArea > 0 ? rawLandArea.toFixed(2) : "0.00");
                document.getElementById('inputLabel').innerText = "마당 가용 면적 (㎡)";
            } else {
                areaInput.value = rawArchArea > 0 ? rawArchArea.toFixed(2) : "0.00";
                document.getElementById('inputLabel').innerText = "지붕 가용 면적 (㎡)";
            }
            calculateValues();
        }

        function startAnalysis() {
            const addr = document.getElementById('addressInput').value;
            if(!addr) return;
            
            document.getElementById('loadingMsg').classList.remove('hidden');

            ps.keywordSearch(addr, function(data, status) {
                if (status === kakao.maps.services.Status.OK) {
                    const place = data[0];
                    const coords = new kakao.maps.LatLng(place.y, place.x);
                    marker.setPosition(coords);
                    map.setCenter(coords);
                    fetchBackendData(place.address_name || place.road_address_name);
                } else {
                    geocoder.addressSearch(addr, function(result, status) {
                        if (status === kakao.maps.services.Status.OK) {
                            const coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                            marker.setPosition(coords);
                            map.setCenter(coords);
                            fetchBackendData(addr);
                        } else {
                            fetchBackendData(addr);
                        }
                    });
                }
            });
        }

        function fetchBackendData(targetAddr) {
            fetch(`/api/analyze?address=${encodeURIComponent(targetAddr)}`)
                .then(res => res.json())
                .then(data => {
                    document.getElementById('loadingMsg').classList.add('hidden');
                    
                    // 면적 데이터 방어 코드 적용 바인딩
                    if(data.vworld_success) {
                        // 토지면적(지적)을 안전하게 수신
                        rawLandArea = data.vworld_area ? parseFloat(data.vworld_area) : 0.0;
                        document.getElementById('vwPnu').innerText = data.pnu;
                        document.getElementById('vwJimok').innerText = data.vworld_jimok;
                        document.getElementById('vwArea').innerText = rawLandArea.toLocaleString();
                        document.getElementById('vwJiga').innerText = parseInt(data.vworld_jiga).toLocaleString();
                    } else {
                        rawLandArea = 0.0;
                        document.getElementById('vwPnu').innerText = data.vworld_error_msg ? `에러: ${data.vworld_error_msg}` : `${data.pnu} (DB 없음)`;
                        document.getElementById('vwJimok').innerText = "-";
                        document.getElementById('vwArea').innerText = "0";
                        document.getElementById('vwJiga').innerText = "0";
                    }

                    if(data.building_success) {
                        // 건축면적을 안전하게 수신
                        rawArchArea = data.arch_area ? parseFloat(data.arch_area) : 0.0;
                        document.getElementById('bdArchArea').innerText = rawArchArea.toLocaleString();
                        document.getElementById('bdTotArea').innerText = data.tot_area.toLocaleString();
                    } else {
                        rawArchArea = 0.0;
                        document.getElementById('bdArchArea').innerText = "0";
                        document.getElementById('bdTotArea').innerText = "0";
                    }

                    switchMode(document.querySelector('input[name="calcMode"]:checked').value);
                }).catch(err => {
                    console.error(err);
                    document.getElementById('loadingMsg').classList.add('hidden');
                });
        }

        function calculateValues() {
            let currentArea = parseFloat(document.getElementById('customArea').value);
            if(isNaN(currentArea) || currentArea < 0) currentArea = 0.0;
            
            const pyeong = currentArea / 3.3;
            const kw = pyeong / 3.0;
            
            let kwCostInput = parseFloat(document.getElementById('kwCostInput').value);
            if (isNaN(kwCostInput) || kwCostInput <= 0) kwCostInput = 800000;
            
            const currentMode = document.querySelector('input[name="calcMode"]:checked').value;
            let unitPrice = (currentMode === 'land') ? (130 + 70 * 1.2) : (130 + 70 * 1.5);
            
            const annualGeneration = kw * 3.6 * 365;
            const annualRevenue = annualGeneration * unitPrice;
            const monthlyProfit = annualRevenue / 12;
            const estimatedCostMan = (kw * kwCostInput) / 10000; 
            
            let paybackYears = 0;
            if (annualRevenue > 0) paybackYears = (estimatedCostMan * 10000) / annualRevenue;
            
            document.getElementById('resPyeong').innerText = pyeong.toFixed(2);
            document.getElementById('estKw').innerText = kw.toFixed(2);
            document.getElementById('ownerInvest').innerText = Math.round(estimatedCostMan).toLocaleString();
            document.getElementById('ownerMonthlyProfit').innerText = Math.round(monthlyProfit).toLocaleString();
            
            if (paybackYears > 0) {
                let months = Math.round(paybackYears * 12);
                document.getElementById('paybackLabel').innerText = `${Math.floor(months / 12)}년 ${months % 12}개월`;
            } else {
                document.getElementById('paybackLabel').innerText = "-";
            }

            let rentUnitPrice = (currentMode === 'land') ? 30000 : 35000;
            document.getElementById('rentAnnual').innerText = Math.round(kw * rentUnitPrice).toLocaleString();
            document.getElementById('rentMonthly').innerText = Math.round((kw * rentUnitPrice) / 12).toLocaleString();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze')
def api_analyze():
    addr = request.args.get('address', '')
    
    out_data = {
        "vworld_success": False, "pnu": "-", "vworld_jimok": "-", "vworld_area": 0.0, "vworld_jiga": 0,
        "vworld_error_msg": "", 
        "building_success": False, "arch_area": 0.0, "tot_area": 0.0
    }
    
    if not addr:
        return jsonify(out_data)

    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}
        k_res = requests.get("https://dapi.kakao.com/v2/local/search/address.json", headers=headers, params={"query": addr}, timeout=4)
        documents = k_res.json().get('documents', [])
        
        if documents:
            addr_data = documents[0]
            jibun_info = addr_data.get('address') 
            
            if jibun_info:
                b_code = jibun_info.get('b_code', '0000000000')
                sigungu_cd = b_code[:5]
                bjdong_cd = b_code[5:]
                
                main_no = jibun_info.get('main_address_no', '')
                main_no = jibun_info.get('main_address_no', '')
                sub_no = jibun_info.get('sub_address_no', '')
                
                bun = main_no.zfill(4) if main_no else '0000'
                ji = sub_no.zfill(4) if sub_no else '0000'
                
                full_jibun_name = jibun_info.get('address_name', '')
                
                pnu_land_type = '2' if "산" in full_jibun_name else '1'
                molit_plat_gb = '1' if "산" in full_jibun_name else '0'
                
                pnu = f"{sigungu_cd}{bjdong_cd}{pnu_land_type}{bun}{ji}"
                out_data["pnu"] = pnu

                domain_clean = VWORLD_DOMAIN.replace("https://", "").replace("http://", "").rstrip("/")

                v_success_count = 0

                # [API 1] 토지특성정보 조회 API (지목, 면적 획득)
                if VWORLD_API_KEY:
                    char_url = "https://api.vworld.kr/ned/data/getLandCharacteristics"
                    char_params = {
                        "key": VWORLD_API_KEY,
                        "domain": domain_clean,
                        "pnu": pnu,
                        "format": "json"
                    }
                    char_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Referer": f"https://{domain_clean}"
                    }
                    
                    char_res = requests.get(char_url, params=char_params, headers=char_headers, timeout=5)
                    
                    if char_res.status_code == 200:
                        try:
                            char_json = char_res.json()
                            res_body = char_json.get("response", {}).get("result", {}).get("featureCollection", {}).get("features", [])
                            if res_body:
                                props = res_body[0].get("properties", {})
                                out_data["vworld_jimok"] = props.get("lndcgrCodeNm", "-")
                                
                                # 면적 데이터 추출 안전 장치
                                area_val = props.get("lndpclAr")
                                out_data["vworld_area"] = float(area_val) if area_val else 0.0
                                v_success_count += 1
                        except Exception as je:
                            print(f"Land Char JSON Parsing Error: {je}")

                # [API 2] 브이월드 연속지적도 API (공시지가 획득)
                if VWORLD_API_KEY:
                    v_params = {
                        "service": "data",
                        "version": "2.0",
                        "request": "GetFeature",
                        "format": "json",
                        "data": "LP_PA_CBND_BUBUN",
                        "geometry": "false", 
                        "attribute": "true",
                        "attrFilter": f"pnu:=:{pnu}",
                        "key": VWORLD_API_KEY,
                        "domain": domain_clean
                    }
                    
                    v_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                        "Referer": f"https://{domain_clean}"
                    }
                    
                    v_res = requests.get("https://api.vworld.kr/req/data", params=v_params, headers=v_headers, timeout=5)
                    
                    if v_res.status_code == 200:
                        try:
                            v_json = v_res.json()
                            response_block = v_json.get("response", {})
                            if response_block.get("status") != "ERROR":
                                features = response_block.get("result", {}).get("featureCollection", {}).get("features", [])
                                if features:
                                    props = features[0].get("properties", {})
                                    jiga_val = props.get("jiga", 0)
                                    out_data["vworld_jiga"] = int(jiga_val) if jiga_val else 0
                                    v_success_count += 1
                        except Exception as ve:
                            print(f"Cadastral JSON Parsing Error: {ve}")

                if v_success_count > 0:
                    out_data["vworld_success"] = True

                # [API 3] 국토부 건축물대장 호출
                if DATA_GO_KR_KEY:
                    bld_params = {
                        'serviceKey': DATA_GO_KR_KEY, 
                        'sigunguCd': sigungu_cd, 
                        'bjdongCd': bjdong_cd, 
                        'platGbCd': molit_plat_gb,
                        'bun': bun, 
                        'ji': ji,
                        'numOfRows': '1', 
                        'pageNo': '1'
                    }
                    bld_res = requests.get("https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo", params=bld_params, timeout=5)
                    
                    if bld_res.status_code == 200 and ("archArea" in bld_res.text or "archarea" in bld_res.text):
                        root = ET.fromstring(bld_res.text)
                        arch_node = root.find('.//archArea') or root.find('.//archarea')
                        tot_node = root.find('.//totArea') or root.find('.//totarea')
                        
                        arch_val = float(arch_node.text) if arch_node is not None and arch_node.text else 0.0
                        tot_val = float(tot_node.text) if tot_node is not None and tot_node.text else 0.0
                        
                        if arch_val > 0 or tot_val > 0:
                            out_data["building_success"] = True
                            out_data["arch_area"] = arch_val
                            out_data["tot_area"] = tot_val

    except Exception as e:
        print(f"API Error: {e}")

    return jsonify(out_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
