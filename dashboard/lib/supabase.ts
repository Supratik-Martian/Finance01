import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// Create a real client OR a safe stub that returns empty results
function buildClient(): SupabaseClient {
    if (supabaseUrl && supabaseKey) {
        return createClient(supabaseUrl, supabaseKey);
    }

    // During build / when keys are missing, return a placeholder URL
    // that won't crash createClient but also won't connect to anything.
    console.warn(
        "Supabase credentials missing. Dashboard will use offline mode."
    );
    return createClient("https://placeholder.supabase.co", "placeholder-key");
}

export const supabase = buildClient();
export const isConnected = Boolean(supabaseUrl && supabaseKey);
