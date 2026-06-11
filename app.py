# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template_string
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)

# 🔑 API 키 설정 (VWORLD_API_KEY와 VWORLD_DOMAIN을 대표님 정보로 채워주세요)
DATA_GO_KR_KEY = "c838a8d8130510cdb26146fc24b4d5671daddae3b0a25d969a0d2984a57f0308"
kakao_rest_key = "eee2dd15c07cf4a1660324a1f26848ea"
kakao_js_key = "6bf846817be3a6a8d8e09a566d264c90"

VWORLD_API_KEY = "2175D91D-18D8-3F33-80D1-6A75013C849C"
VWORLD_DOMAIN = "https://solar-dashboard-daegu.vercel.app/" # 나중에 Vercel 도메인(https://xxx.vercel.app)으로 변경하세요

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
        .map-container { min-height: 400px; height: 50vh; }
        @media (min-width: 1024px) { .map-container { height: 100%; min-height: 600px; } }
    </style>
</head>
<body class="p-4 md:p-6 max-w-7xl mx-auto">

    <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6 border-b border-gray-800 pb-5">
        <div>
            <h1 class="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
                <i class="fa-solid fa-solar-panel text-emerald-400"></i> 대구지사 태양광 종합 분석 관제 시스템
            </h1>
            <p class="text-xs md:text-sm text-gray-400 mt-1">VWorld 지적도 폴리곤 및 국토부 건축물대장 통합 엔진</p>
        </div>
    </header>

    <div class="bg-gray-900 border border-gray-800 p-4 rounded-2xl mb-6 flex flex-col sm:flex-row gap-3 items-stretch shadow-xl">
        <div class="relative flex-grow">
            <i class="fa-solid fa-location-dot absolute left-4 top-3.5 text-gray-500"></i>
            <input type="text" id="addressInput" value="대구광역시 수성구 범어동 1" 
                   class="w-full bg-gray-950 border border-gray-800 rounded-xl pl-11 pr-4 py-3 text-white font-medium focus:outline-none focus:border-emerald-500 transition-all text-sm md:text-base">
        </div>
        <button onclick="startAnalysis()" class="bg-emerald-500 hover:bg-emerald-600 text-gray-950 font-bold px-6 py-3 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer text-sm md:text-base whitespace-nowrap">
            <i class="fa-solid fa-magnifying-glass-chart"></i> 통합 부지 분석
        </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <div class="lg:col-span-5 flex flex-col gap-4">
            
            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-xl">
                <h3 class="text-xs font-bold text-blue-400 mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-map-location-dot"></i> VWorld 토지 지적 정보
                </h3>
                <div class="grid grid-cols-2 gap-3 text-center mb-3">
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">법정 지목</span>
                        <span id="vwJimok" class="text-base font-black text-amber-400">-</span>
                    </div>
                    <div class="bg-gray-950 p-3 rounded-xl border border-gray-850">
                        <span class="text-[11px] text-gray-500 block mb-1">토지 면적</span>
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

            <div class="bg-gray-900 border-2 border-amber-900/40 rounded-2xl p-5 shadow-xl">
                <h3 class="text-xs font-bold text-amber-400 mb-3 flex items-center gap-2">
                    <i class="fa-solid fa-bolt"></i> 태양광 실무 용량 시뮬레이터 (3평 = 1kW)
                </h3>
                <div class="flex gap-2 mb-4">
                    <label class="flex-1 bg-gray-950 border border-gray-800 p-2 rounded-lg flex items-center justify-center gap-2 cursor-pointer hover:border-gray-700">
                        <input type="radio" name="calcMode" value="land" checked onchange="calcCapacity()" class="accent-blue-500">
                        <span class="text-xs text-gray-300">토지 기준 (나대지)</span>
                    </label>
                    <label class="flex-1 bg-gray-950 border border-gray-800 p-2 rounded-lg flex items-center justify-center gap-2 cursor-pointer hover:border-gray-700">
                        <input type="radio" name="calcMode" value="roof" onchange="calcCapacity()" class="accent-emerald-400">
                        <span class="text-xs text-gray-300">건축물 기준 (지붕)</span>
                    </label>
                </div>
                
                <div class="bg-gray-950 p-4 rounded-xl border border-gray-850 text-center">
                    <span class="text-[11px] text-gray-500 block mb-1">예상 설치 가능 용량</span>
                    <span id="estKw" class="text-3xl font-black text-emerald-400">0.00</span> <span class="text-sm text-gray-400 font-bold">kW</span>
                </div>
            </div>

        </div>

        <div class="lg:col-span-7 bg-gray-900 border border-gray-800 rounded-2xl p-2 shadow-xl flex flex-col">
            <div id="map" class="w-full map-container rounded-xl flex-grow relative">
                <div id="loadingOverlay" class="absolute inset-0 bg-gray-900/80 z-10 flex items-center justify-center hidden rounded-xl">
                    <div class="text-emerald-400 font-bold flex flex-col items-center">
                        <i class="fa-solid fa-spinner fa-spin text-3xl mb-2"></i>
                        <span>지적도 및 건축물대장 수집 중...</span>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <script type="text/javascript" src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=""" + kakao_js_key + """&libraries=services"></script>
    <script>
        let map, marker, ps;
        let currentPolygon = null;
        let rawLandArea = 0;
        let rawArchArea = 0;

        document.addEventListener("DOMContentLoaded", function() {
            const mapContainer = document.getElementById('map');
            const defaultPos = new kakao.maps.LatLng(35.8596, 128.6254); 
            
            map = new kakao.maps.Map(mapContainer, { center: defaultPos, level: 2 });
            map.setMapTypeId(kakao.maps.MapTypeId.HYBRID); // 스카이뷰(위성)
            
            ps = new kakao.maps.services.Places(); 
            marker = new kakao.maps.Marker({ map: map, position: defaultPos });
        });

        function startAnalysis() {
            const addr = document.getElementById('addressInput').value;
            if(!addr) return;
            
            document.getElementById('loadingOverlay').classList.remove('hidden');

            ps.keywordSearch(addr, function(data, status) {
                if (status === kakao.maps.services.Status.OK) {
                    const place = data[0];
                    const coords = new kakao.maps.LatLng(place.y, place.x);
                    marker.setPosition(coords);
                    map.setCenter(coords);
                    fetchBackendData(place.address_name || place.road_address_name);
                } else {
                    const geocoder = new kakao.maps.services.Geocoder();
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
                    document.getElementById('loadingOverlay').classList.add('hidden');
                    
                    // VWorld 데이터 매핑
                    if(data.vworld_success) {
                        rawLandArea = data.vworld_area;
                        document.getElementById('vwJimok').innerText = data.vworld_jimok;
                        document.getElementById('vwArea').innerText = rawLandArea.toLocaleString();
                        document.getElementById('vwJiga').innerText = parseInt(data.vworld_jiga).toLocaleString();
                        
                        // 폴리곤 그리기
                        drawPolygon(data.vworld_geom);
                    } else {
                        rawLandArea = 0;
                        document.getElementById('vwJimok').innerText = "조회 실패";
                        document.getElementById('vwArea').innerText = "0";
                        document.getElementById('vwJiga').innerText = "0";
                        if(currentPolygon) currentPolygon.setMap(null);
                    }

                    // 국토부 건축물 데이터 매핑
                    if(data.building_success) {
                        rawArchArea = data.arch_area;
                        document.getElementById('bdArchArea').innerText = rawArchArea.toLocaleString();
                        document.getElementById('bdTotArea').innerText = data.tot_area.toLocaleString();
                    } else {
                        rawArchArea = 0;
                        document.getElementById('bdArchArea').innerText = "0";
                        document.getElementById('bdTotArea').innerText = "0";
                    }

                    calcCapacity();
                }).catch(err => {
                    console.error(err);
                    document.getElementById('loadingOverlay').classList.add('hidden');
                });
        }

        function drawPolygon(geom) {
            if (currentPolygon) currentPolygon.setMap(null);
            if (!geom || !geom.coordinates) return;

            // MultiPolygon 배열 파싱
            let paths = [];
            // VWorld MultiPolygon 구조: [[[ [lon, lat], [lon, lat] ... ]]]
            const coordsArray = geom.coordinates[0][0]; 

            for (let i = 0; i < coordsArray.length; i++) {
                paths.push(new kakao.maps.LatLng(coordsArray[i][1], coordsArray[i][0])); // 위도, 경도 순서 주의
            }

            currentPolygon = new kakao.maps.Polygon({
                path: paths,
                strokeWeight: 3,
                strokeColor: '#FF0000', // 빨간색 선
                strokeOpacity: 0.9,
                fillColor: '#FF8C00',   // 주황색 채우기
                fillOpacity: 0.3
            });

            currentPolygon.setMap(map);
        }

        function calcCapacity() {
            const mode = document.querySelector('input[name="calcMode"]:checked').value;
            let targetArea = mode === 'land' ? rawLandArea : rawArchArea;
            
            // 토지 기준일 경우, 대지면적에서 건축면적을 빼서 실제 가용 마당 면적 도출
            if (mode === 'land' && rawArchArea > 0 && rawLandArea > rawArchArea) {
                targetArea = rawLandArea - rawArchArea;
            }

            // 3.0평(9.9㎡) 당 1kW 기준
            const pyeong = targetArea / 3.3;
            const kw = pyeong / 3.0;
            
            document.getElementById('estKw').innerText = kw.toFixed(2);
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
        "vworld_success": False, "vworld_jimok": "-", "vworld_area": 0.0, "vworld_jiga": 0, "vworld_geom": None,
        "building_success": False, "arch_area": 0.0, "tot_area": 0.0
    }
    
    if not addr:
        return jsonify(out_data)

    try:
        # 1. 카카오 주소 검색을 통한 PNU 부품 추출
        headers = {"Authorization": f"KakaoAK {kakao_rest_key}"}
        k_res = requests.get("https://dapi.kakao.com/v2/local/search/address.json", headers=headers, params={"query": addr}, timeout=4)
        documents = k_res.json().get('documents', [])
        
        if documents:
            addr_info = documents[0].get('address') or documents[0].get('road_address')
            if addr_info:
                # b_code가 시군구(5자리) + 법정동(5자리) = 10자리
                b_code = addr_info.get('b_code', '0000000000')
                sigungu_cd = b_code[:5]
                bjdong_cd = b_code[5:]
                
                main_no = addr_info.get('main_address_no', '')
                sub_no = addr_info.get('sub_address_no', '')
                
                bun = main_no.zfill(4)
                ji = sub_no.zfill(4) if sub_no else '0000'
                
                # ⛰️ 산 여부에 따라 대지구분코드 1(일반) 또는 2(산) 설정
                land_type = '2' if "산" in addr else '1'
                
                # 🔑 PNU 조립 (19자리)
                pnu = f"{sigungu_cd}{bjdong_cd}{land_type}{bun}{ji}"

                # 2. VWorld API 호출 (지목, 토지면적, 공시지가, 폴리곤)
                v_params = {
                    "service": "data",
                    "version": "2.0",
                    "request": "GetFeature",
                    "data": "LP_PA_CBND_BUBUN",
                    "key": VWORLD_API_KEY,
                    "domain": VWORLD_DOMAIN,
                    "attrFilter": f"pnu:=:{pnu}",
                    "geometry": "true",
                    "crs": "EPSG:4326"
                }
                
                if "여기에_발급받은" not in VWORLD_API_KEY:
                    v_res = requests.get("https://api.vworld.kr/req/data", params=v_params, timeout=5)
                    if v_res.status_code == 200:
                        v_json = v_res.json()
                        features = v_json.get("response", {}).get("result", {}).get("featureCollection", {}).get("features", [])
                        if features:
                            props = features[0].get("properties", {})
                            geom = features[0].get("geometry", {})
                            
                            out_data["vworld_success"] = True
                            out_data["vworld_jimok"] = props.get("jimok", "-")
                            out_data["vworld_area"] = float(props.get("parea", 0.0))
                            out_data["vworld_jiga"] = int(props.get("jiga", 0))
                            out_data["vworld_geom"] = geom

                # 3. 국토부 건축물대장 호출 (건축면적, 연면적)
                bld_params = {
                    'serviceKey': requests.utils.unquote(DATA_GO_KR_KEY),
                    'sigunguCd': sigungu_cd, 'bjdongCd': bjdong_cd, 'bun': bun, 'ji': ji,
                    'numOfRows': '1', 'pageNo': '1'
                }
                bld_res = requests.get("https://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo", params=bld_params, timeout=5)
                if bld_res.status_code == 200 and "<archArea>" in bld_res.text:
                    root = ET.fromstring(bld_res.text)
                    arch_node = root.find('.//archArea')
                    tot_node = root.find('.//totArea')
                    
                    arch_val = float(arch_node.text) if arch_node is not None and arch_node.text else 0.0
                    tot_val = float(tot_node.text) if tot_node is not None and tot_node.text else 0.0
                    
                    if arch_val > 0 or tot_val > 0:
                        out_data["building_success"] = True
                        out_data["arch_area"] = arch_val
                        out_data["tot_area"] = tot_val

    except Exception as e:
        print(f"API Error: {e}")
        pass

    return jsonify(out_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
