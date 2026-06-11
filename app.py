from flask import Flask, request, jsonify, render_template_string
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 🔑 정부 API 및 카카오 키 고정
DATA_GO_KR_KEY = "c838a8d8130510cdb26146fc24b4d5671daddae3b0a25d969a0d2984a57f0308"
kakao_rest_key = "eee2dd15c07cf4a1660324a1f26848ea"
kakao_js_key = "6bf846817be3a6a8d8e09a566d264c90"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>대구지사 태양광 부지 분석 플랫폼</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        body { background-color: #0B0F19; font-family: 'Pretendard', sans-serif; color: #E5E7EB; }
        .map-container { min-height: 350px; height: 45vh; }
        @media (min-width: 1024px) { .map-container { height: 100%; min-height: 620px; } }
    </style>
</head>
<body class="p-4 md:p-6 max-w-7xl mx-auto">

    <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6 border-b border-gray-800 pb-5">
        <div>
            <h1 class="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
                <i class="fa-solid fa-chart-pie text-emerald-400"></i> 대구지사 태양광 수익방식 비교 관제시스템
            </h1>
            <p class="text-xs md:text-sm text-gray-400 mt-1">대장 미등록/나대지 수동 입력 완전 보정 에디션</p>
        </div>
    </header>

    <div class="bg-gray-900 border border-gray-800 p-4 rounded-2xl mb-6 flex flex-col sm:flex-row gap-3 items-stretch shadow-xl">
        <div class="relative flex-grow">
            <i class="fa-solid fa-location-dot absolute left-4 top-3.5 text-gray-500"></i>
            <input type="text" id="addressInput" value="대구광역시 수성구 범어동 1" 
                   class="w-full bg-gray-950 border border-gray-800 rounded-xl pl-11 pr-4 py-3 text-white font-medium focus:outline-none focus:border-emerald-500 transition-all text-sm md:text-base">
        </div>
        <button id="btnAnalyze" onclick="startAnalysis()" class="bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold px-6 py-3 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer text-sm md:text-base whitespace-nowrap">
            <i class="fa-solid fa-magnifying-glass-chart"></i> 통합 부지 분석
        </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <div class="lg:col-span-5 flex flex-col gap-6">
            
            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 md:p-5 shadow-xl">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-gray-400 text-xs font-semibold tracking-wider uppercase flex items-center gap-2">
                        <i class="fa-solid fa-calculator text-emerald-400"></i> 1단계: 부지 기본 정보
                    </h2>
                    <span id="apiStatusBadge" class="text-[10px] px-2 py-0.5 rounded font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">대기중</span>
                </div>

                <div class="grid grid-cols-2 gap-3 mb-4">
                    <div class="bg-gray-950 border border-gray-800 p-3 rounded-xl border-l-4 border-l-blue-500">
                        <span class="text-[11px] text-gray-500 block">🌳 공식 대지면적</span>
                        <span id="platArea" class="text-base font-bold text-white">0.00</span> <span class="text-xs text-gray-400">㎡</span>
                    </div>
                    <div class="bg-gray-950 border border-gray-800 p-3 rounded-xl border-l-4 border-l-emerald-500">
                        <span class="text-[11px] text-gray-500 block">🏢 공식 건축면적</span>
                        <span id="archArea" class="text-base font-bold text-white">0.00</span> <span class="text-xs text-gray-400">㎡</span>
                    </div>
                </div>

                <div class="flex gap-2.5 mb-4">
                    <label class="flex-1 bg-gray-950 border border-gray-800 p-3 rounded-xl flex items-center gap-2 cursor-pointer hover:border-gray-700">
                        <input type="radio" name="calcMode" value="plat" checked onchange="switchMode('plat')" class="accent-blue-500">
                        <span class="text-xs text-gray-300 font-medium">🌳 나대지/마당 기준</span>
                    </label>
                    <label class="flex-1 bg-gray-950 border border-gray-800 p-3 rounded-xl flex items-center gap-2 cursor-pointer hover:border-gray-700">
                        <input type="radio" name="calcMode" value="arch" onchange="switchMode('arch')" class="accent-emerald-400">
                        <span class="text-xs text-gray-300 font-medium">🏢 지붕/옥상 기준</span>
                    </label>
                </div>

                <div class="mb-4">
                    <label class="text-xs text-gray-500 block mb-1.5" id="inputLabel">가용 면적 수정 (㎡) <span class="text-amber-400 text-[11px] font-normal">(조회 실패시 수동 입력 가능)</span></label>
                    <input type="number" id="customArea" oninput="calculateValues()" class="w-full bg-gray-950 border-2 border-gray-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-white font-bold focus:outline-none text-sm">
                </div>

                <div class="grid grid-cols-2 gap-3 bg-gray-950 p-3 rounded-xl border border-gray-850 text-center">
                    <div>
                        <span class="text-gray-500 text-[10px] block">📐 환산 평수</span>
                        <span class="text-sm font-bold text-gray-300" id="resPyeong">0.00 평</span>
                    </div>
                    <div>
                        <span class="text-gray-500 text-[10px] block">⚡ 실무 가용 용량</span>
                        <span class="text-sm font-black text-emerald-400" id="resKw">0.00 kW</span>
                    </div>
                </div>
            </div>

            <div class="bg-gradient-to-br from-gray-900 to-slate-900 border border-gray-800 rounded-2xl p-4 shadow-xl">
                <div class="flex items-center gap-3">
                    <div class="bg-amber-950/50 border border-amber-800/60 p-2.5 rounded-xl text-amber-400">
                        <i class="fa-solid fa-building-shield text-base"></i>
                    </div>
                    <div>
                        <h3 class="text-xs font-bold text-white">⚙️ 리스 금융 방식 (소유권 이전형)</h3>
                        <p class="text-[11px] text-gray-400 mt-0.5">초기 대출 한도 심사 및 SPC 조달 조건 조율 필요</p>
                    </div>
                </div>
                <div class="mt-3 bg-gray-950/60 border border-gray-850 px-3 py-2 rounded-lg text-center text-amber-500 text-xs font-bold">
                    ⚠️ 리스 금융 조달은 본사 대출 심사팀 별도 문의 필수
                </div>
            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 shadow-md text-center">
                <a href="https://online.kepco.co.kr/EWM092D00" target="_blank" class="block w-full bg-gray-950 hover:bg-gray-850 border border-gray-800 text-gray-300 text-xs py-3 rounded-xl font-medium transition-all">
                    <i class="fa-solid fa-arrow-up-right-from-square mr-1 text-blue-400"></i> 한전ON 선로 용량 수동 검증 사이트 열기
                </a>
            </div>

        </div>

        <div class="lg:col-span-7 flex flex-col gap-6">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                <div class="bg-gray-900 border-2 border-emerald-500/40 rounded-2xl p-5 shadow-2xl relative overflow-hidden bg-gradient-to-b from-emerald-950/10 to-transparent">
                    <div class="absolute top-0 right-0 bg-emerald-500 text-gray-950 font-black text-[10px] px-2.5 py-1 rounded-bl-xl uppercase tracking-wider">인기 제안</div>
                    <h3 class="text-white font-bold text-sm mb-3 flex items-center gap-2">
                        <i class="fa-solid fa-coins text-emerald-400"></i> [1안] 자가발전 투자형
                    </h3>
                    <div class="flex flex-col gap-2.5">
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850">
                            <span class="text-gray-500 text-[10px] block">🛠️ 예상 총공사비 (스타타워 단가 기준)</span>
                            <span id="ownerInvest" class="text-sm font-bold text-white">0</span> <span class="text-xs text-gray-400">만 원</span>
                        </div>
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850">
                            <span class="text-gray-500 text-[10px] block">☀️ 월평균 예상 순수익</span>
                            <span id="ownerMonthlyProfit" class="text-base font-black text-emerald-400">0</span> <span class="text-xs text-emerald-400">원 / 월</span>
                        </div>
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850 flex justify-between items-center">
                            <span class="text-gray-500 text-[10px]">⏳ 원금 회수 소요기간</span>
                            <span class="text-xs font-bold text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-900/50">약 2년 7개월</span>
                        </div>
                    </div>
                </div>

                <div class="bg-gray-900 border-2 border-blue-500/40 rounded-2xl p-5 shadow-2xl relative overflow-hidden bg-gradient-to-b from-blue-950/10 to-transparent">
                    <div class="absolute top-0 right-0 bg-blue-500 text-white font-black text-[10px] px-2.5 py-1 rounded-bl-xl uppercase tracking-wider">리스크 제로</div>
                    <h3 class="text-white font-bold text-sm mb-3 flex items-center gap-2">
                        <i class="fa-solid fa-building-user text-blue-400"></i> [2안] 부지 임대 대여형
                    </h3>
                    <div class="flex flex-col gap-2.5">
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850">
                            <span class="text-gray-500 text-[10px] block">📉 소유주 초기 투자 비용</span>
                            <span class="text-sm font-bold text-blue-400">0원 (전액 본사 자부담)</span>
                        </div>
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850">
                            <span class="text-gray-500 text-[10px] block">💰 소유주 수령 임대료 (월)</span>
                            <span id="rentMonthly" class="text-base font-black text-blue-400">0</span> <span class="text-xs text-blue-400">원 / 월</span>
                        </div>
                        <div class="bg-gray-950 p-2.5 rounded-lg border border-gray-850">
                            <span class="text-gray-500 text-[10px] block">🗓️ 소유주 수령 임대료 (연간 고정)</span>
                            <span id="rentAnnual" class="text-sm font-bold text-white">0</span> <span class="text-xs text-gray-400">원 / 년</span>
                        </div>
                    </div>
                </div>

            </div>

            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-2 shadow-xl flex-grow">
                <div id="map" class="w-full map-container rounded-xl"></div>
            </div>

        </div>

    </div>

    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=""" + kakao_js_key + """&libraries=services"></script>
    <script>
        let map, marker, geocoder;
        let globalPlatArea = 0, globalArchArea = 0;

        document.addEventListener("DOMContentLoaded", function() {
            const mapContainer = document.getElementById('map');
            map = new kakao.maps.Map(mapContainer, { center: new kakao.maps.LatLng(35.8596, 128.6254), level: 2 });
            map.setMapTypeId(kakao.maps.MapTypeId.HYBRID);
            geocoder = new kakao.maps.services.Geocoder();
            marker = new kakao.maps.Marker({ map: map });
            startAnalysis();
        });

        function switchMode(mode) {
            if (mode === 'plat') {
                let netYardArea = globalPlatArea - globalArchArea;
                document.getElementById('customArea').value = netYardArea > 0 ? netYardArea.toFixed(2) : globalPlatArea.toFixed(2);
                document.getElementById('inputLabel').innerText = "실측 반영 마당 면적 수정 (㎡)";
            } else {
                document.getElementById('customArea').value = globalArchArea.toFixed(2);
                document.getElementById('inputLabel').innerText = "실측 반영 옥상 면적 수정 (㎡)";
            }
            calculateValues();
        }

        function startAnalysis() {
            const addr = document.getElementById('addressInput').value;
            if(!addr) return;
            
            document.getElementById('apiStatusBadge').innerText = "대장 조회중...";
            document.getElementById('apiStatusBadge').className = "text-[10px] px-2 py-0.5 rounded font-bold bg-amber-950 text-amber-400 border border-amber-800";

            geocoder.addressSearch(addr, function(result, status) {
                if (status === kakao.maps.services.Status.OK) {
                    const coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                    marker.setPosition(coords);
                    map.setCenter(coords);
                }
            });

            fetch(`/api/analyze?address=${encodeURIComponent(addr)}`)
                .then(res => res.json())
                .then(data => {
                    if(data.success && data.official_exists) {
                        globalPlatArea = data.plat_area;
                        globalArchArea = data.arch_area;
                        document.getElementById('platArea').innerText = globalPlatArea.toLocaleString(undefined, {maximumFractionDigits:2});
                        document.getElementById('archArea').innerText = globalArchArea.toLocaleString(undefined, {maximumFractionDigits:2});
                        
                        document.getElementById('apiStatusBadge').innerText = "연동 성공";
                        document.getElementById('apiStatusBadge').className = "text-[10px] px-2 py-0.5 rounded font-bold bg-emerald-950 text-emerald-400 border border-emerald-800";
                    } else {
                        // 🛠️ 핵심 보정 파트: 대장이 조회 안되면 0으로 밀고 경고 표기 후 수동 입력창을 열어둠
                        globalPlatArea = 0;
                        globalArchArea = 0;
                        document.getElementById('platArea').innerText = "대장 없음";
                        document.getElementById('archArea').innerText = "나대지 지역";
                        
                        document.getElementById('apiStatusBadge').innerText = "수동 입력 대기";
                        document.getElementById('apiStatusBadge').className = "text-[10px] px-2 py-0.5 rounded font-bold bg-red-950 text-red-400 border border-red-800";
                    }
                    
                    const currentMode = document.querySelector('input[name="calcMode"]:checked').value;
                    if(currentMode === 'plat') {
                        let netYardArea = globalPlatArea - globalArchArea;
                        document.getElementById('customArea').value = netYardArea > 0 ? netYardArea.toFixed(2) : 0;
                    } else {
                        document.getElementById('customArea').value = globalArchArea > 0 ? globalArchArea.toFixed(2) : 0;
                    }
                    calculateValues();
                }).catch(err => {
                    console.error(err);
                    document.getElementById('apiStatusBadge').innerText = "통신 에러 / 수동 모드";
                });
        }

        function calculateValues() {
            let currentArea = parseFloat(document.getElementById('customArea').value);
            if(isNaN(currentArea) || currentArea < 0) currentArea = 0;
            
            const pyeong = currentArea / 3.3;
            const kw = pyeong / 3.8;
            
            const currentMode = document.querySelector('input[name="calcMode"]:checked').value;
            let unitPrice = (currentMode === 'plat') ? (130 + 70 * 1.2) : (130 + 70 * 1.5);
            
            const annualGeneration = kw * 3.6 * 365;
            const annualRevenue = annualGeneration * unitPrice;
            const monthlyProfit = annualRevenue / 12;
            const estimatedCost = kw * 88; 

            document.getElementById('resPyeong').innerText = pyeong.toFixed(2) + " 평";
            document.getElementById('resKw').innerText = kw.toFixed(2) + " kW";
            document.getElementById('ownerInvest').innerText = Math.round(estimatedCost).toLocaleString();
            document.getElementById('ownerMonthlyProfit').innerText = Math.round(monthlyProfit).toLocaleString();

            let rentUnitPrice = (currentMode === 'plat') ? 30000 : 35000;
            const rentAnnualProfit = kw * rentUnitPrice;
            const rentMonthlyProfit = rentAnnualProfit / 12;

            document.getElementById('rentAnnual').innerText = Math.round(rentAnnualProfit).toLocaleString();
            document.getElementById('rentMonthly').innerText = Math.round(rentMonthlyProfit).toLocaleString();
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analyze
