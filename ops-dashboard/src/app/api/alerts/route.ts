import { INSTANCES } from "@/lib/config";
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal, cache: "no-store" });
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchAlerts(params: URLSearchParams) {
  // Try each instance until one responds
  for (const instance of INSTANCES) {
    try {
      const res = await fetchWithTimeout(`${instance.url}/alerts?${params}`);
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Try next instance
    }
  }
  return [];
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;

  const params = new URLSearchParams();
  const status = searchParams.get("status");
  const severity = searchParams.get("severity");
  if (status) params.set("status", status);
  if (severity) params.set("severity", severity);

  const data = await fetchAlerts(params);
  return Response.json(data);
}

export async function POST(request: NextRequest) {
  const instanceId = request.nextUrl.searchParams.get("instance");
  const instance = INSTANCES.find((i) => i.id === instanceId) || INSTANCES[0];
  const body = await request.json();

  try {
    const res = await fetchWithTimeout(`${instance.url}/alerts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch (err) {
    return Response.json(
      { error: err instanceof Error ? err.message : "Flask unreachable" },
      { status: 502 }
    );
  }
}
