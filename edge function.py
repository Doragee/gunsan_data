import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { GoogleGenerativeAI } from 'https://esm.sh/@google/generative-ai';
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
    // [진단용 로그 추가] Edge Function이 실제로 받은 질문을 출력합니다.
    console.log(`Edge Function received query: "${query}"`);
    if (!query) {
      throw new Error('"query" is required in the request body.');
    }
    const genAI = new GoogleGenerativeAI(Deno.env.get('GOOGLE_API_KEY'));
    const embeddingModel = genAI.getGenerativeModel({
      model: "embedding-001"
    });
    const embeddingResult = await embeddingModel.embedContent(query);
    const query_embedding = embeddingResult.embedding.values;
    const supabaseClient = createClient(Deno.env.get('SUPABASE_URL'), Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'));
    // [수정] 이제 최종 버전인 'hybrid_search' 함수를 호출합니다.
    const { data, error } = await supabaseClient.rpc('hybrid_search', {
      query_text: query,
      query_embedding: query_embedding,
      match_threshold: 0.1,
      match_count: 5
    });
    if (error) {
      console.error('Supabase RPC error:', error);
      throw error;
    }
    return new Response(JSON.stringify({
      data
    }), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      },
      status: 200
    });
  } catch (err) {
    return new Response(String(err?.message ?? err), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      },
      status: 500
    });
  }
});
