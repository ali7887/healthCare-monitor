/** Global search API (Ctrl+K palette). */

import { apiGet } from "@/lib/api/client";
import type { SearchResponse } from "@/lib/api/types";

export async function searchRuns(query: string, limit = 10): Promise<SearchResponse> {
  return apiGet<SearchResponse>("/search", { q: query, limit });
}
