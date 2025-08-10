// supabase/functions/vector-search/index.ts
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
const supabaseUrl = Deno.env.get('SUPABASE_URL');
const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY');
const googleApiKey = Deno.env.get('GOOGLE_API_KEY');
const GOOGLE_API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models/';
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};
Deno.serve(async (req)=>{
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: corsHeaders
    });
  }
  try {
    const { query } = await req.json();
    const supabaseClient = createClient(supabaseUrl, supabaseAnonKey);
    // 1. 벡터 검색 (의미 기반 유사 문서 찾기)
    const embeddingResponse = await fetch(`${GOOGLE_API_BASE_URL}embedding-001:embedContent?key=${googleApiKey}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'models/embedding-001',
        content: {
          parts: [
            {
              text: query
            }
          ]
        }
      })
    });
    if (!embeddingResponse.ok) throw new Error(await embeddingResponse.text());
    const embeddingData = await embeddingResponse.json();
    const queryEmbedding = embeddingData.embedding.values;
    const { data: documents, error: rpcError } = await supabaseClient.rpc('match_documents', {
      query_embedding: queryEmbedding,
      match_threshold: 0.5,
      match_count: 5
    });
    if (rpcError) throw rpcError;
    const vectorContext = documents.map((doc)=>doc.content).join('\n---\n');
    // 2. 키워드 기반 SQL 검색 (개수 세기)
    let sqlContext = '';
    const { data: places } = await supabaseClient.from('administrative_welfare_centers').select('name');
    const placeNames = places?.map((p)=>p.name) || [];
    const foundPlace = placeNames.find((name)=>query.includes(name));
    if (foundPlace) {
      const { count, error: countError } = await supabaseClient.from('publicFacilities').select('*', {
        count: 'exact',
        head: true
      }).eq('spot', foundPlace);
      if (!countError && count !== null) {
        sqlContext = `참고로, ${foundPlace}에는 총 ${count}개의 공공시설이 등록되어 있습니다.`;
      }
    }
    // ✅ 3. AI에게 내리는 지시(프롬프트)를 더 구체적으로 변경했습니다.
    const prompt = `당신은 사용자를 돕는 친절한 '군산시 안내 전문가'입니다.
당신의 임무는 아래 [참고 정보]를 바탕으로 사용자의 질문에 한국어로 답변하는 것입니다.

**규칙:**
1.  답변은 반드시 [참고 정보]에 있는 내용만을 근거로 해야 합니다.
2.  질문에 대한 정보가 [참고 정보]에 없다면, 절대로 추측해서 답변하지 말고 "죄송합니다, 문의하신 내용에 대한 정보는 가지고 있지 않습니다." 라고만 말하세요.
3.  만약 '참고 정보'에서 여러 시설의 이름이 발견되면, 그 시설들의 목록을 먼저 보여주고, 사용자가 특정 시설에 대한 상세 정보를 원하면 다시 질문하도록 자연스럽게 유도하세요.

---
[참고 정보]
${sqlContext} 
${vectorContext}
---

[사용자 질문]
${query}
---

자, 이제 위의 규칙에 따라 답변을 생성하세요.`;
    const completionResponse = await fetch(`${GOOGLE_API_BASE_URL}gemini-1.5-flash-latest:generateContent?key=${googleApiKey}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              {
                text: prompt
              }
            ]
          }
        ]
      })
    });
    if (!completionResponse.ok) throw new Error(await completionResponse.text());
    const completionData = await completionResponse.json();
    const answer = completionData.candidates?.[0]?.content?.parts?.[0]?.text || "AI가 답변을 생성하는 데 실패했습니다.";
    return new Response(JSON.stringify({
      answer
    }), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      }
    });
  } catch (e) {
    console.error("An unexpected error occurred:", e);
    return new Response(JSON.stringify({
      error: e.message
    }), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      },
      status: 500
    });
  }
});
