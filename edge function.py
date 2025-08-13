import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { GoogleGenerativeAI } from 'https://esm.sh/@google/generative-ai';
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};
// --- 환경 변수 유효성 검사 ---
const GOOGLE_API_KEY = Deno.env.get('GOOGLE_API_KEY');
const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
if (!GOOGLE_API_KEY || !SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY) {
  console.error("Missing required environment variables/secrets.");
  Deno.serve(async (req)=>{
    return new Response(JSON.stringify({
      error: "Missing required environment variables. Please check your Supabase project's secrets."
    }), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      },
      status: 500
    });
  });
} else {
  const genAI = new GoogleGenerativeAI(GOOGLE_API_KEY);
  const embeddingModel = genAI.getGenerativeModel({
    model: "embedding-001"
  });
  const generativeModel = genAI.getGenerativeModel({
    model: "gemini-1.5-flash-latest"
  });
  Deno.serve(async (req)=>{
    if (req.method === 'OPTIONS') {
      return new Response('ok', {
        headers: corsHeaders
      });
    }
    try {
      const { query } = await req.json();
      if (!query) throw new Error('"query" is required.');
      console.log(`[1/7] Received query: "${query}"`);
      // --- [신규 기능] 1. 지역명 추출 ---
      const locationExtractorPrompt = `
        다음 문장에서 군산시의 '동' 또는 '면' 단위의 지역명을 하나만 추출하세요.
        만약 지역명이 없다면 '없음'이라고만 답하세요.
        예시: "수송동 맛집 알려줘" -> "수송동"
        예시: "군산시 소식 알려줘" -> "없음"
        
        문장: "${query}"
        지역명:
      `;
      const locationResult = await generativeModel.generateContent(locationExtractorPrompt);
      let locationName = locationResult.response.text().trim();
      if (locationName === '없음') {
        locationName = null;
      }
      console.log(`[2/7] Extracted location: "${locationName}"`);
      // --- 2. 질의 라우팅 ---
      const routerPrompt = `
        사용자의 질문을 분석하여 'facility' 또는 'news' 중 하나로 분류하세요.
        - 장소, 위치, 운영 시간, 주소, 연락처 등에 대한 질문은 'facility'입니다.
        - 사건, 소식, 이벤트, 정책, 최신 정보 등에 대한 질문은 'news'입니다.
        
        질문: "${query}"
        분류:
      `;
      const routeResult = await generativeModel.generateContent(routerPrompt);
      const route = routeResult.response.text().trim().toLowerCase();
      console.log(`[3/7] Query routed as: "${route}"`);
      // --- 3. 임베딩 생성 ---
      const embeddingResult = await embeddingModel.embedContent(query);
      const query_embedding = embeddingResult.embedding.values;
      console.log(`[4/7] Embedding created with dimension: ${query_embedding.length}`);
      // --- 4. Supabase 클라이언트 생성 ---
      const supabaseClient = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
      let searchResults;
      // --- 5. 라우팅 결과에 따라 적절한 함수 호출 ---
      if (route.includes('news')) {
        const { data, error } = await supabaseClient.rpc('hybrid_search_news', {
          query_text: query,
          query_embedding: query_embedding,
          match_count: 5
        });
        if (error) throw error;
        searchResults = data;
      } else {
        const { data, error } = await supabaseClient.rpc('hybrid_search', {
          query_text: query,
          query_embedding: query_embedding,
          match_count: 5
        });
        if (error) throw error;
        searchResults = data;
      }
      console.log(`[6/7] Search completed. Found ${searchResults?.length || 0} results.`);
      // --- [신규 기능] 6. 지역 좌표 조회 ---
      let locationData = null;
      if (locationName) {
        const { data: coords, error: coordsError } = await supabaseClient.from('publicFacilities').select('latitude, longitude').eq('spot', locationName).limit(1).single(); // 단일 결과를 객체로 받음
        if (coords) {
          locationData = {
            name: locationName,
            latitude: coords.latitude,
            longitude: coords.longitude
          };
        }
      }
      console.log(`[7/7] Location data found:`, locationData);
      // --- 7. 사용자 질의 로그 저장 (비동기) ---
      supabaseClient.from('query_logs').insert({
        query: query,
        route: route,
        search_result_count: searchResults?.length || 0
      }).then(({ error })=>{
        if (error) console.error("Error logging user query:", error);
      });
      // --- 8. 검색 결과와 위치 정보를 함께 반환 ---
      return new Response(JSON.stringify({
        data: searchResults,
        location: locationData
      }), {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        },
        status: 200
      });
    } catch (err) {
      console.error("Error inside Deno.serve:", err);
      return new Response(String(err?.message ?? err), {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        },
        status: 500
      });
    }
  });
}
